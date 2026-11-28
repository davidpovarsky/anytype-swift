package spaceimpl

import (
	"context"
	"errors"
	"fmt"

	"github.com/anyproto/any-store/v2/anyenc"

	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/files/readguard"
	"github.com/anyproto/any-sync-sdk/internal/properties"
	"github.com/anyproto/any-sync-sdk/internal/schema"
	"github.com/anyproto/any-sync-sdk/internal/techspace"
	anytype "github.com/anyproto/any-sync-sdk/internal/types/any"
	"github.com/anyproto/any-sync-sdk/space"
)

// CheckCurrentReader is a short current signed-ACL/lifetime admission. It does
// not consult the cached role or hold a lease for a later unrelated operation.
func (s *spaceImpl) CheckCurrentReader(ctx context.Context) error {
	return readguard.Effect(ctx, s.fileReadACL, func() (func() error, error) { return nil, nil })
}

func (s *Service) SetSettingsCurrentReader(ctx context.Context, spaceID string, set map[string]any, unset []string) error {
	current, err := s.Get(ctx, spaceID)
	if err != nil {
		return err
	}
	loaded, ok := current.(*spaceImpl)
	if !ok || loaded.id != spaceID {
		return space.ErrUnsupported
	}
	return readguard.Effect(ctx, loaded.fileReadACL, func() (func() error, error) {
		// Validation and metadata inspection are outside ACL/lifetime locks.
		arena := &anyenc.Arena{}
		if _, err := techspace.SettingsOps(arena, set, unset); err != nil {
			return nil, err
		}
		return func() error {
			_, err := s.tsp.SetSettingsForLiveSpace(ctx, spaceID, set, unset, MaterializeBlock)
			return err
		}, nil
	})
}

// SetLocalCurrentReader adds current READ admission to the original local
// property route for the immutable native any namespace only. Mutable type or
// collection owners are explicitly unsupported until a definition-owner lock
// can be held through the local apply. It never falls back to account/synced
// writes. The final short
// readguard check admits the effect; a subsequent ACL/account retirement does
// not replace the original operation result or invite another dispatch.
func (p *propertiesAPI) SetLocalCurrentReader(ctx context.Context, objectID, ownerID string, patch map[string]any) (space.ModifyResult, error) {
	var result space.ModifyResult
	err := readguard.Effect(ctx, p.parent.fileReadACL, func() (func() error, error) {
		if objectID == "" || ownerID == "" {
			return nil, errors.New("propertiesAPI: objectId and typeId required")
		}
		if ownerID != anytype.TypeId {
			return nil, fmt.Errorf("%w: bound local properties require immutable native any owner", space.ErrUnsupported)
		}
		if len(patch) == 0 {
			return nil, errors.New("propertiesAPI: empty patch")
		}
		props, _ := p.parent.store.Registry().PropsOf(ownerID)
		if err := validateRoutedPatch(ownerID, patch, props, schema.ScopeLocal); err != nil {
			return nil, err
		}
		arena := &anyenc.Arena{}
		ops, err := patchOps(arena, ownerID, patch)
		if err != nil {
			return nil, err
		}
		obj, err := p.parent.store.Get(ctx, objectID)
		if err != nil {
			return nil, err
		}
		if obj.Id() != objectID {
			return nil, fmt.Errorf("%w: local property target identity differs", crdt.ErrValidation)
		}
		change := crdt.Change{
			Dataset: properties.Dataset, DataVersion: properties.HandlerVersion,
			Records: []crdt.RecordChange{{Id: objectID, Ops: ops}},
		}
		return func() error {
			written, err := obj.LocalSetWithLocalCheck(ctx, change, func(ctx context.Context, controller *crdt.Controller) error {
				// The any namespace is a compiled immutable schema. Recheck
				// its LOCAL kind at the target serialization point; no mutable
				// definition-owner atomicity is asserted by this route.
				currentProps, _ := p.parent.store.Registry().PropsOf(ownerID)
				if err := validateRoutedPatch(ownerID, patch, currentProps, schema.ScopeLocal); err != nil {
					return err
				}
				row, err := controller.Lookup(ctx, properties.Dataset, objectID)
				if err != nil {
					return err
				}
				if row == nil {
					return space.ErrObjectNotFound
				}
				if row.Get(crdt.DeletedAtField) != nil {
					return space.ErrObjectDeleted
				}
				if row.GetString(crdt.IdField) != objectID {
					return fmt.Errorf("%w: local property row identity differs", crdt.ErrValidation)
				}
				return nil
			})
			if err != nil {
				return err
			}
			for _, rejection := range written.Rejections {
				if errors.Is(rejection.Err, crdt.ErrStrictSkipAbsent) {
					return fmt.Errorf("propertiesAPI: object %s has no property record (not created in this space?)", objectID)
				}
			}
			result = modifyResultFromWrite(written)
			return nil
		}, nil
	})
	return result, err
}

var _ space.CurrentReaderAuthority = (*spaceImpl)(nil)
var _ space.CurrentReaderSettings = (*Service)(nil)
var _ space.CurrentReaderLocalProperties = (*propertiesAPI)(nil)
