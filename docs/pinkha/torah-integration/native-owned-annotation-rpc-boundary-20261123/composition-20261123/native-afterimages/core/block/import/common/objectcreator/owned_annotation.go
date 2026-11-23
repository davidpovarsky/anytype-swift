// Narrow additive entry on the original creator. It accepts no success flag,
// caller callback, alternate executor or reuse/update policy.
package objectcreator

import (
	"errors"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/import/common"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/relationutils"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
)

var errOwnedAnnotationFreshPayload = errors.New("owned annotation requires a fresh original page payload")
var errOwnedAnnotationUnresolvedFile = errors.New("owned annotation contains an unresolved file or fetch")

// This private value is minted only from the original DataObject populated by
// the original ID provider. It is not a caller-supplied import policy.
type ownedAnnotationCreate struct {
	data     *DataObject
	targetID string
}

// CreateOwnedAnnotationFresh shares the ordinary creator's state transforms and
// real Space.CreateTreeObjectWithPayload call. It never resets or opens an
// existing page as create success. The importer retains the actual account and
// repeats current native writer/graph admission before reaching this method.
func (oc *ObjectCreator) CreateOwnedAnnotationFresh(data *DataObject, sn *common.Snapshot) (*domain.Details, string, error) {
	if oc == nil || data == nil || data.ctx == nil || data.spaceID == "" || sn == nil ||
		sn.Id == "" || sn.Snapshot == nil || sn.Snapshot.Data == nil || sn.Snapshot.Data.Details == nil ||
		sn.Snapshot.SbType != coresb.SmartBlockTypePage || len(sn.Snapshot.FileKeys) != 0 ||
		sn.Snapshot.Data.Key != "" || sn.Snapshot.Data.FileInfo != nil {
		return nil, "", errOwnedAnnotationFreshPayload
	}
	if err := data.ctx.Err(); err != nil {
		return nil, "", err
	}
	target := data.oldIDtoNew[sn.Id]
	payload := data.createPayloads[target]
	details := sn.Snapshot.Data.Details
	if target == "" || target == sn.Id || payload.RootRawChange == nil || payload.RootRawChange.Id != target ||
		details.GetString(bundle.RelationKeyUniqueKey) != "" ||
		details.GetBool(bundle.RelationKeyIsFavorite) || details.GetBool(bundle.RelationKeyIsArchived) {
		return nil, "", errOwnedAnnotationFreshPayload
	}
	admitted := &ownedAnnotationCreate{data: data, targetID: target}
	return oc.create(data, sn, admitted)
}

// All binary objects have already passed the original synchronous uploader and
// exact owned-body admission. An unresolved file/icon/bookmark must not start an
// additional fetch, shared-key preload, legacy migration or metadata sync here.
// This validation observes the state AFTER the original typed remappers.
func (a *ownedAnnotationCreate) validatePreparedState(st *state.State, formats relationutils.RelationFormatFetcher) error {
	if a == nil || a.data == nil || st == nil || st.RootId() != a.targetID {
		return errOwnedAnnotationFreshPayload
	}
	if err := a.data.ctx.Err(); err != nil {
		return err
	}
	resolved := func(id string) bool { _, ok := a.data.newIdsSet[id]; return id != "" && ok }
	var failure error
	st.ModifyLinkedFilesInDetails(formats, func(id string) string {
		if !resolved(id) {
			failure = errOwnedAnnotationUnresolvedFile
		}
		return id
	})
	if err := st.Iterate(func(b simple.Block) bool {
		m := b.Model()
		if f := m.GetFile(); f != nil && !resolved(f.TargetObjectId) {
			failure = errOwnedAnnotationUnresolvedFile
		}
		if t := m.GetText(); t != nil && t.IconImage != "" && !resolved(t.IconImage) {
			failure = errOwnedAnnotationUnresolvedFile
		}
		if v := m.GetBookmark(); v != nil && v.Url != "" && !resolved(v.TargetObjectId) {
			failure = errOwnedAnnotationUnresolvedFile
		}
		return failure == nil
	}); err != nil {
		return err
	}
	return failure
}
