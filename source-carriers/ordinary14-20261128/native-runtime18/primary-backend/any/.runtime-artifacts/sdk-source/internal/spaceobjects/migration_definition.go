package spaceobjects

import (
	"bytes"
	"context"
	"crypto/rand"
	"errors"
	"github.com/anyproto/any-sync-sdk/internal/commitguard"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"time"
)

func (s *Store) PrepareMigrationDefinitionRoot(ctx context.Context, journal *migrationintent.Store, entry *migrationintent.Prepared) (*migrationintent.Prepared, error) {
	if err := s.CheckMigrationWriter(ctx); err != nil {
		return nil, err
	}
	if journal == nil || entry == nil || migrationintent.DefinitionChangeType(entry.Kind) == "" || entry.Stage != migrationintent.DefinitionRoot {
		return nil, migrationintent.ErrScope
	}
	if old, err := journal.LoadDefinition(ctx, entry.Binding.IntentID, migrationintent.DefinitionRoot); err == nil {
		if old.Binding != entry.Binding || old.Fingerprint != entry.Fingerprint {
			return nil, migrationintent.ErrCollision
		}
		return old, nil
	} else if !errors.Is(err, migrationintent.ErrNotFound) {
		return nil, err
	}
	handle, err := s.app.GetSpace(ctx, s.spaceId)
	if err != nil {
		return nil, err
	}
	seed := make([]byte, 32)
	if _, err := rand.Read(seed); err != nil {
		return nil, err
	}
	payload, err := handle.Inner().TreeBuilder().CreateTree(ctx, objecttree.ObjectTreeCreatePayload{PrivKey: s.signKey, ChangeType: migrationintent.DefinitionChangeType(entry.Kind), SpaceId: s.spaceId, IsEncrypted: true, Seed: seed, Timestamp: time.Now().Unix()})
	if err != nil {
		return nil, err
	}
	copy := *entry
	copy.ObjectID, copy.ChangeID, copy.Raw = payload.RootRawChange.Id, payload.RootRawChange.Id, bytes.Clone(payload.RootRawChange.RawChange)
	// No tree registration or append has happened. Reserve includes a required
	// native database checkpoint and must succeed before CommitMigrationDefinitionRoot.
	return journal.ReserveDefinition(ctx, &copy)
}

// MigrationDefinitionRootState looks up the known immutable ID, never a name or a host
// acknowledgement. A purged/deleted tree always halts; it is not re-created.
func (s *Store) MigrationDefinitionRootState(ctx context.Context, entry *migrationintent.Prepared) (string, error) {
	if err := s.CheckMigrationWriter(ctx); err != nil {
		return "", err
	}
	head, err := s.TreeEntry(ctx, entry.ObjectID)
	if err != nil {
		return "", err
	}
	if head.Deleted {
		return "deleted", nil
	}
	handle, err := s.app.GetSpace(ctx, s.spaceId)
	if err != nil {
		return "", err
	}
	if !head.Present {
		err := commitguard.CheckPreparedDefinitionRoot(ctx, handle.Inner().Storage(), handle.Inner().Acl(), s.signKey.GetPublic(), &treechangeproto.RawTreeChangeWithId{Id: entry.ChangeID, RawChange: entry.Raw}, migrationintent.DefinitionChangeType(entry.Kind))
		if errors.Is(err, commitguard.ErrNativeACLChanged) {
			return "obsolete", nil
		}
		if err != nil {
			return "", err
		}
		return "prepared", nil
	}
	storage, err := handle.Inner().Storage().TreeStorage(ctx, entry.ObjectID)
	if err != nil {
		return "", err
	}
	root, err := storage.Root(ctx)
	if err != nil {
		return "", err
	}
	if root.Id != entry.ObjectID || !bytes.Equal(root.RawChange, entry.Raw) {
		return "", migrationintent.ErrCollision
	}
	return "committed", nil
}

func (s *Store) CommitMigrationDefinitionRoot(ctx context.Context, entry *migrationintent.Prepared) error {
	state, err := s.MigrationDefinitionRootState(ctx, entry)
	if err != nil {
		return err
	}
	if state == "deleted" || state == "obsolete" {
		return migrationintent.ErrObsolete
	}
	if state == "committed" {
		return nil
	}
	handle, err := s.app.GetSpace(ctx, s.spaceId)
	if err != nil {
		return err
	}
	raw := &treechangeproto.RawTreeChangeWithId{Id: entry.ChangeID, RawChange: bytes.Clone(entry.Raw)}
	_, _, err = commitguard.StoreCurrentRoot(ctx, handle.Inner().Storage(), handle.Inner().Acl(), s.signKey.GetPublic(), treestorage.TreeStorageCreatePayload{RootRawChange: raw, Changes: []*treechangeproto.RawTreeChangeWithId{raw}, Heads: []string{raw.Id}})
	if errors.Is(err, treestorage.ErrTreeExists) {
		state, readErr := s.MigrationDefinitionRootState(ctx, entry)
		if readErr == nil && state == "committed" {
			return nil
		}
	}
	return err
}
