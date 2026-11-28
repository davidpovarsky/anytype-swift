package spaceobjects

import (
	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
	collectiontype "github.com/anyproto/any-sync-sdk/internal/types/collection"
	typetype "github.com/anyproto/any-sync-sdk/internal/types/type"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/util/crypto"
)

// This local-only policy is separate from NativeObjectPolicy. The latter
// continues to reject every metatype. Only the prepared definition entrypoint
// may reach this policy, after binding a closed definition specification.
func (v lockedReadView) ValidateNativeDefinitionChange(ch *crdt.Change) error {
	if ch == nil || ch.NativeObjectPolicy || !migrationintent.IsDefinition(ch.NativeDefinitionPolicy) || v.store == nil || v.carrier == nil || (len(ch.Records) == 0 || (ch.NativeDefinitionPolicy != migrationintent.PartDefinition && len(ch.Records) != 1)) {
		return crdt.ErrValidation
	}
	carrier := v.carrier
	if v.store.staticOwnerKind(carrier.Id()) != "" {
		return crdt.ErrValidation
	}
	r := ch.Records[0]
	if !r.Upsert || len(r.Ops) != 1 || r.Ops[0].Type != crdt.OpSet || len(r.Ops[0].Path) != 0 || r.Ops[0].Payload == nil || r.Ops[0].Payload.Type() != anyenc.TypeObject {
		return crdt.ErrValidation
	}
	raw := carrier.Tree().Header()
	root, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), raw).Unmarshall(raw, true)
	if err != nil {
		return err
	}
	envelope := &treechangeproto.RawTreeChange{}
	info := &treechangeproto.RootChange{}
	if envelope.UnmarshalVT(raw.RawChange) != nil || info.UnmarshalVT(envelope.Payload) != nil || info.SpaceId != v.store.spaceId || info.IsDerived || root.IsDerived || info.ParentId != "" {
		return crdt.ErrValidation
	}
	if ch.NativeDefinitionPolicy == migrationintent.PartDefinition {
		return v.validateNativePartChange(ch, info.ChangeType)
	}
	if ch.NativeDefinitionPolicy == migrationintent.PropertyDefinition {
		if ch.Dataset != typetype.DatasetPropertyDefs || r.Id != "" {
			return crdt.ErrValidation
		}
		kind, err := v.definitionKind(carrier.Id())
		if err != nil {
			return err
		}
		if (kind != "type" && kind != "collection") || kind != info.ChangeType {
			return crdt.ErrValidation
		}
		return nil // ordinary property-definition schema preflight follows
	}
	if ch.Dataset != "objects" || r.Id != carrier.Id() || info.ChangeType != migrationintent.DefinitionChangeType(ch.NativeDefinitionPolicy) {
		return crdt.ErrValidation
	}
	marker := typetype.MetaTypeMarker
	if ch.NativeDefinitionPolicy == migrationintent.CollectionDefinition {
		marker = collectiontype.MetaMarker
	}
	if r.Ops[0].Payload.GetString("any.type") != marker {
		return crdt.ErrValidation
	}
	row, err := carrier.Controller().GuardLookup(v.ctx, "objects", carrier.Id())
	if err != nil {
		return err
	}
	if row != nil {
		return migrationintent.ErrCollision
	}
	return nil
}
