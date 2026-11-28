package techspace

import (
	"context"
	"errors"
	"fmt"

	"github.com/anyproto/any-store/v2/anyenc"

	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/object"
	"github.com/anyproto/any-sync-sdk/space"
)

// SetSettingsForLiveSpace is the narrow opt-in settings write. The original
// SetSettings continues to support tombstones. Here the row is checked under
// the resident index object's write lock, together with the original append.
// check is an SDK-internal pure classification of the decoded local row.
func (s *Service) SetSettingsForLiveSpace(ctx context.Context, spaceID string, set map[string]any, unset []string,
	check func(SpaceIndexRecord) error) (object.WriteResult, error) {
	if !s.open.Load() {
		return object.WriteResult{}, errors.New("techspace: service not open")
	}
	if spaceID == "" || check == nil {
		return object.WriteResult{}, fmt.Errorf("%w: live settings require an explicit space and local predicate", crdt.ErrValidation)
	}
	arena := &anyenc.Arena{}
	ops, err := SettingsOps(arena, set, unset)
	if err != nil {
		return object.WriteResult{}, err
	}
	obj, err := s.indexObj(ctx)
	if err != nil {
		return object.WriteResult{}, err
	}
	change := crdt.Change{
		Dataset: SpaceIndexDataset, DataVersion: HandlerVersion,
		Records: []crdt.RecordChange{{Id: spaceID, Ops: ops}},
	}
	return obj.LocalWriteWithLocalCheck(ctx, change, func(ctx context.Context, controller *crdt.Controller) error {
		value, err := controller.Lookup(ctx, SpaceIndexDataset, spaceID)
		if err != nil {
			return err
		}
		if value == nil || value.Get(crdt.DeletedAtField) != nil {
			return fmt.Errorf("%w: live settings target is absent", space.ErrSpaceUnknown)
		}
		row := DecodeSpaceIndexRecord(value)
		if row.Id != spaceID {
			return fmt.Errorf("%w: live settings row identity differs", crdt.ErrValidation)
		}
		if row.IsDeleted() {
			return space.ErrSpaceDeleted
		}
		return check(row)
	})
}
