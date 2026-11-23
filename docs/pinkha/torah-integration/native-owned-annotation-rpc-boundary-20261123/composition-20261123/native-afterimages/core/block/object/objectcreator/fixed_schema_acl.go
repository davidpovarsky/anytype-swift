package objectcreator

import (
	"bytes"
	"context"
	"fmt"

	"github.com/anyproto/any-sync/commonspace/object/acl/aclrecordproto"
	"github.com/anyproto/any-sync/commonspace/spacepayloads"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/consensus/consensusproto"
)

// Validate only copied persisted bytes, after the owned ReadTx has finished.
// This is the original Space creation-payload verifier: actual header CID,
// signature and replication key; ACL/settings root CIDs and signatures; and
// version-specific Space/ACL/settings binding. V1 embeds the exact ACL/settings
// payloads in its signed header and legitimately leaves root SpaceId empty.
// No new crypto, live DB handle, ACL lock, or Space initialization is involved.
func validateFixedSchemaSpace(ctx context.Context, scope fixedSchemaScope, stored fixedSchemaStoredSpace, acl fixedSchemaStoredACL) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if stored.state.SpaceId != scope.spaceID || stored.state.AclId != scope.aclID ||
		stored.state.SettingsId != scope.settingsID || stored.settingsRoot == nil ||
		stored.settingsRoot.Id != scope.settingsID || len(acl.root) == 0 {
		return fmt.Errorf("%w: original Space payload identity", ErrFixedSchemaStorage)
	}
	err := spacepayloads.ValidateSpaceStorageCreatePayload(spacestorage.SpaceStorageCreatePayload{
		SpaceHeaderWithId:   &spacesyncproto.RawSpaceHeaderWithId{Id: stored.state.SpaceId, RawHeader: stored.state.SpaceHeader},
		AclWithId:           &consensusproto.RawRecordWithId{Id: scope.aclID, Payload: acl.root},
		SpaceSettingsWithId: stored.settingsRoot,
	})
	if err != nil {
		return fmt.Errorf("verify original persisted Space payload: %w", err)
	}
	return ctx.Err()
}

// validateFixedSchemaACL runs only after the owned ReadTx has released its
// reader. The original RecordBuilder and its key storage are shared with native
// ACL users; signature verification can populate their in-memory key caches.
// Use the original exclusive ACL lock, as normal AddRawRecord/ACL RPC paths do.
// There are no persisted writes, no storage reads, and no role replay here.
func validateFixedSchemaACL(ctx context.Context, scope fixedSchemaScope, stored fixedSchemaStoredACL) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	scope.acl.Lock()
	defer scope.acl.Unlock()
	if err := ctx.Err(); err != nil {
		return err
	}
	current, err := scope.captureACLStateLocked()
	if err != nil {
		return err
	}
	if !scope.same(current) {
		return ErrFixedSchemaChanged
	}
	if len(stored.records) != len(scope.aclRecords) || len(stored.rows) != len(scope.aclRecords) ||
		!bytes.Equal(stored.root, scope.aclRoot) {
		return fmt.Errorf("%w: persisted ACL membership", ErrFixedSchemaStorage)
	}
	builder := scope.acl.RecordBuilder()
	if builder == nil {
		return fmt.Errorf("%w: original ACL record verifier unavailable", ErrFixedSchemaStorage)
	}
	for index, persisted := range stored.records {
		if err := ctx.Err(); err != nil {
			return err
		}
		// Actual retained verifier performs original CID, author signature, and
		// configured acceptor verification. It is not a caller-supplied verifier.
		decoded, err := builder.UnmarshallWithId(persisted.RawRecordWithId())
		if err != nil {
			return fmt.Errorf("verify original persisted ACL record: %w", err)
		}
		identity := scope.aclRecords[index]
		if decoded == nil || decoded.Id != identity.id || decoded.PrevId != identity.previousID ||
			decoded.Id != persisted.Id || decoded.PrevId != persisted.PrevId {
			return fmt.Errorf("%w: original verified ACL membership", ErrFixedSchemaStorage)
		}
		if index == 0 {
			// Space binding was already verified by the original version-aware
			// payload validator; V1 native ACL roots have no explicit SpaceId.
			root, ok := decoded.Model.(*aclrecordproto.AclRoot)
			if !ok || root == nil {
				return fmt.Errorf("%w: original ACL root model", ErrFixedSchemaStorage)
			}
		}
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	current, err = scope.captureACLStateLocked()
	if err != nil {
		return err
	}
	if !scope.same(current) {
		return ErrFixedSchemaChanged
	}
	return nil
}
