package torahops

import (
	"context"
	"errors"
	"fmt"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/pb"
	cutover "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutovercontract"
	cutoverroot "github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahcutoverroot"
	"github.com/golang/snappy"
)

const maxCutoverNativeBytes = cutover.MaxWireBytes + 4096

// This is a different native root and content validator. V1's root, wire
// validator and ordinary operation tree remain exactly v1-compatible. Both
// hosts reuse the same mandatory signed-native storage commit guard.
func CutoverNativeTreeBuilder(spaceID string) objecttree.BuildObjectTreeFunc {
	return func(storage objecttree.Storage, acl list.AclList) (objecttree.ObjectTree, error) {
		root, err := cutoverroot.Root(spaceID)
		if err != nil || storage.Id() != root.Id {
			return nil, errors.Join(ErrInvalid, err)
		}
		header, err := storage.Root(context.Background())
		if err != nil {
			return nil, err
		}
		if err = cutoverroot.ValidateRoot(spaceID, header.RawTreeChangeWithId()); err != nil {
			return nil, err
		}
		build := objecttree.BuildObjectTreeWithContentValidator(func(ch *objecttree.Change, acl list.AclList) error {
			if ch.IsSnapshot || ch.ReadKeyId == "" || ch.Identity == nil {
				return ErrInvalid
			}
			if cached, ok := ch.Model.(*pb.StoreChange); ok {
				return validateCutoverStoreChange(spaceID, ch, cached)
			}
			// The upstream validator already holds the ACL read lock here.
			keys, exists := acl.AclState().Keys()[ch.ReadKeyId]
			if !exists || keys.ReadKey == nil {
				return list.ErrNoReadKey
			}
			rawKey, err := keys.ReadKey.Raw()
			if err != nil {
				return err
			}
			key, err := crypto.NewKeyDeriver(fmt.Sprintf(crypto.AnysyncTreePath, root.Id)).DeriveKey(rawKey)
			if err != nil {
				return err
			}
			if len(ch.Data) > snappy.MaxEncodedLen(maxCutoverNativeBytes)+128 {
				return ErrReadLimit
			}
			data, err := key.Decrypt(ch.Data)
			if err != nil {
				return err
			}
			change, err := decodeCutoverStoreChange(ch, data)
			if err != nil {
				return err
			}
			return validateCutoverStoreChange(spaceID, ch, change)
		})
		guardedStorage, err := bindNativeCommitStorage(storage, acl, root)
		if err != nil {
			return nil, err
		}
		tree, err := build(guardedStorage, acl)
		if err == nil {
			tree.SetFlusher(objecttree.MarkNewChangeFlusher())
			return &nativeCommitTree{ObjectTree: tree, storage: guardedStorage}, nil
		}
		return tree, err
	}
}

func decodeCutoverStoreChange(ch *objecttree.Change, data []byte) (*pb.StoreChange, error) {
	if ch.DataType == nativeSnappy {
		size, err := snappy.DecodedLen(data)
		if err != nil || size > maxCutoverNativeBytes {
			return nil, errors.Join(ErrInvalid, err)
		}
		data, err = snappy.Decode(nil, data)
		if err != nil {
			return nil, err
		}
	} else if ch.DataType != "" {
		return nil, ErrUnsupportedVersion
	}
	if len(data) == 0 || len(data) > maxCutoverNativeBytes {
		return nil, ErrInvalid
	}
	change := &pb.StoreChange{}
	if err := change.Unmarshal(data); err != nil {
		return nil, err
	}
	return change, nil
}

func validateCutoverStoreChange(spaceID string, ch *objecttree.Change, change *pb.StoreChange) error {
	if ch.Identity == nil || ch.ReadKeyId == "" || ch.IsSnapshot || len(change.ChangeSet) != 1 {
		return ErrInvalid
	}
	create := change.ChangeSet[0].GetCreate()
	if create == nil || create.Collection != cutover.CollectionName {
		return ErrInvalid
	}
	claim, err := cutover.Decode(create.DocumentId, []byte(create.Value))
	if err != nil {
		return err
	}
	if claim.Record.SpaceID != spaceID || claim.Record.AuthorID != ch.Identity.Account() {
		return ErrInvalid
	}
	if claim.Record.Kind == cutover.Begin {
		return cutover.ValidateSourceCoverage(*claim.Record.Plan)
	}
	return nil
}
