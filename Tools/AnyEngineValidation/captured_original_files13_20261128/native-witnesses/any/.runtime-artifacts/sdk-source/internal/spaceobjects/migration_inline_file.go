package spaceobjects

import (
	"bytes"
	"context"
	"errors"
	"slices"
	"time"

	"github.com/anyproto/any-sync-sdk/internal/commitguard"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
	"github.com/anyproto/any-sync-sdk/internal/object"
	"github.com/anyproto/any-sync-sdk/internal/payloads"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/util/crypto"
)

func inlineSameHeads(a, b []string) bool {
	a, b = slices.Clone(a), slices.Clone(b)
	slices.Sort(a)
	slices.Sort(b)
	return slices.Equal(a, b)
}

// Load before taking any tree lock, then lock owner/carrier in native stable
// ID order. An ordinary attach may create a missing carrier concurrently;
// that race refuses and is reconciled on the next explicit call.
func (s *Store) withInlineFileObjects(ctx context.Context, ownerID, payloadID string, action func(*object.Object, *object.Object) error) error {
	if err := s.CheckMigrationWriter(ctx); err != nil {
		return err
	}
	head, err := s.TreeEntry(ctx, ownerID)
	if err != nil {
		return err
	}
	if !head.Present || head.Deleted || head.Derived {
		return migrationintent.ErrObsolete
	}
	owner, err := s.Get(ctx, ownerID)
	if err != nil {
		return err
	}
	root, err := parseVerifiedRoot(owner.Tree().Header())
	if err != nil {
		return err
	}
	if root.IsDerived || root.ChangeType != "object" {
		return commitguard.ErrNativeCommitGuard
	}
	objects := map[string]*object.Object{ownerID: owner}
	carrierHead, err := s.TreeEntry(ctx, payloadID)
	if err != nil {
		return err
	}
	if carrierHead.Deleted {
		return migrationintent.ErrObsolete
	}
	var carrier *object.Object
	if carrierHead.Present {
		carrier, err = s.Get(ctx, payloadID)
		if err != nil {
			return err
		}
		objects[payloadID] = carrier
	}
	_, unlock, err := s.lockPreparedNativeObjects(ctx, objects, carrier)
	if err != nil {
		return err
	}
	defer unlock()
	// Loading or waiting for a native tree lock may overlap a settings-tree
	// deletion being queued. That head status precedes the tree's own deleted
	// flag and materialized-row purge, so re-read the actual owner entry here.
	currentOwner, err := s.TreeEntry(ctx, ownerID)
	if err != nil {
		return err
	}
	if !currentOwner.Present || currentOwner.Deleted || currentOwner.Derived {
		return migrationintent.ErrObsolete
	}
	if err = commitguard.CheckCurrentWrite(ctx, owner.Tree(), s.signKey.GetPublic()); err != nil {
		return err
	}
	row, err := owner.Controller().GuardLookup(ctx, "objects", ownerID)
	if err != nil {
		return err
	}
	if row == nil || row.Get(crdt.DeletedAtField) != nil {
		return migrationintent.ErrObsolete
	}
	current, err := s.TreeEntry(ctx, payloadID)
	if err != nil {
		return err
	}
	if current.Deleted || current.Present != carrierHead.Present {
		return migrationintent.ErrObsolete
	}
	return action(owner, carrier)
}

func (s *Store) PrepareMigrationInlineFile(ctx context.Context, journal *migrationintent.Store, proposed *migrationintent.InlineFile, spec migrationintent.InlineFileSpec) (*migrationintent.InlineFile, error) {
	if journal == nil || proposed == nil || spec.Validate() != nil {
		return nil, migrationintent.ErrScope
	}
	root, err := commitguard.InlineFileRoot(s.spaceId, spec.OwnerObjectID)
	if err != nil {
		return nil, err
	}
	var result *migrationintent.InlineFile
	err = s.withInlineFileObjects(ctx, spec.OwnerObjectID, root.Id, func(owner, carrier *object.Object) error {
		heads := []string{root.Id}
		if carrier != nil {
			if !bytes.Equal(carrier.Tree().Header().RawChange, root.RawChange) {
				return migrationintent.ErrCollision
			}
			heads = slices.Clone(carrier.Tree().Heads())
		}
		acl := owner.Tree().AclList()
		var raw *treechangeproto.RawTreeChangeWithId
		entry := *proposed
		entry.ObjectID, entry.RootRaw, entry.OwnerObjectID = root.Id, bytes.Clone(root.RawChange), spec.OwnerObjectID
		entry.ContentSHA256, entry.Size, entry.Timestamp = spec.ContentSHA256, int64(len(spec.Content)), time.Now().Unix()
		// No registration, append, watcher or publish callback is invoked here.
		err := func() error {
			acl.RLock()
			defer acl.RUnlock()
			if err := ctx.Err(); err != nil {
				return err
			}
			if !acl.AclState().Permissions(s.signKey.GetPublic()).CanWrite() {
				return list.ErrInsufficientPermissions
			}
			if acl.Head() == nil {
				return commitguard.ErrNativeCommitGuard
			}
			entry.ReadKeyID, entry.ACLHeadID = acl.AclState().CurrentReadKeyId(), acl.Head().Id
			readKey, err := acl.AclState().CurrentReadKey()
			if err != nil {
				return err
			}
			key, err := payloads.DeriveEncKey(readKey)
			if err != nil {
				return err
			}
			entry.Payload, err = object.BuildMigrationInlinePayload(spec, entry.ReadKeyID, key)
			if err != nil {
				return err
			}
			_, raw, err = objecttree.NewChangeBuilder(crypto.NewKeyStorage(), root).Build(objecttree.BuilderContent{
				TreeHeadIds: heads, AclHeadId: entry.ACLHeadID, SnapshotBaseId: root.Id,
				Unencrypted: true, PrivKey: s.signKey, Content: entry.Payload, Timestamp: entry.Timestamp, DataType: payloads.Dataset,
			})
			return err
		}()
		if err != nil {
			return err
		}
		entry.ChangeID, entry.Raw = raw.Id, bytes.Clone(raw.RawChange)
		ch, err := object.NewCodec().Decode(entry.Payload)
		if err != nil {
			return err
		}
		ch.ChangeId = entry.ChangeID
		entry.RecordIDs, err = crdt.ResolveRecordIds(ch)
		if err != nil {
			return err
		}
		entry.Dependencies = map[string][]string{spec.OwnerObjectID: slices.Clone(owner.Tree().Heads()), root.Id: heads}
		if _, err = object.CheckMigrationInlineFile(ctx, acl, s.signKey.GetPublic(), &entry, true); err != nil {
			return err
		}
		if carrier != nil {
			row, err := carrier.Controller().GuardLookup(ctx, payloads.Dataset, entry.RecordIDs[0])
			if err != nil {
				return err
			}
			if row != nil {
				return migrationintent.ErrCollision
			}
		}
		result, err = journal.ReserveInlineFile(ctx, &entry)
		return err
	})
	return result, err
}

// MigrationInlineFileState advances at most one native durable stage. Native
// CID/history and materialized row determine recovery; a host receipt does not.
func (s *Store) MigrationInlineFileState(ctx context.Context, e *migrationintent.InlineFile, commit bool) (stage, outcome string, err error) {
	if e == nil {
		return "", "", migrationintent.ErrCorrupt
	}
	stage, outcome = "file-prepared", "prepared"
	err = s.withInlineFileObjects(ctx, e.OwnerObjectID, e.ObjectID, func(owner, carrier *object.Object) error {
		if carrier != nil {
			stage = "file-root-committed"
			var err error
			outcome, err = carrier.MigrationInlineFileLocked(ctx, e, false)
			if err != nil {
				return err
			}
			if outcome != "prepared" {
				if outcome == "committed" || outcome == "committed_deleted" || outcome == "committed_modified" {
					stage = "complete"
				}
				return nil
			}
		} else {
			if _, err := object.CheckMigrationInlineFile(ctx, owner.Tree().AclList(), s.signKey.GetPublic(), e, true); err != nil {
				return err
			}
		}
		if !inlineSameHeads(owner.Tree().Heads(), e.Dependencies[e.OwnerObjectID]) {
			return migrationintent.ErrObsolete
		}
		if !commit {
			return nil
		}
		if carrier != nil {
			outcome, err = carrier.MigrationInlineFileLocked(ctx, e, true)
			if err == nil && outcome != "obsolete" {
				stage = "complete"
			}
			return err
		}
		if !inlineSameHeads(e.Dependencies[e.ObjectID], []string{e.ObjectID}) {
			return migrationintent.ErrObsolete
		}
		if _, err := s.CheckDeriveParent(ctx, e.ObjectID, e.OwnerObjectID); err != nil {
			return err
		}
		handle, err := s.app.GetSpace(ctx, s.spaceId)
		if err != nil {
			return err
		}
		err = commitguard.StorePreparedInlineRoot(ctx, handle.Inner().Storage(), owner.Tree().AclList(), s.signKey.GetPublic(),
			&treechangeproto.RawTreeChangeWithId{Id: e.ObjectID, RawChange: e.RootRaw}, &treechangeproto.RawTreeChangeWithId{Id: e.ChangeID, RawChange: e.Raw}, object.MigrationInlineProof(e))
		if errors.Is(err, treestorage.ErrTreeExists) {
			return migrationintent.ErrObsolete
		}
		if err != nil {
			return err
		}
		stage = "file-root-committed"
		return nil
	})
	if errors.Is(err, migrationintent.ErrObsolete) || errors.Is(err, commitguard.ErrNativeACLChanged) {
		return stage, "obsolete", nil
	}
	return stage, outcome, err
}
