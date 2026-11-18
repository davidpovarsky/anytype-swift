package sourceimpl

import (
	"context"

	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/source"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

// torahOperationsSource exposes only local object metadata to the cache. Its
// signed immutable operations are read/applied exclusively by NativeHost, which
// owns the SyncTree listener. It never uses treeSource.buildState or source.Store.
type torahOperationsSource struct{ *treeSource }

var _ source.Source = (*torahOperationsSource)(nil)

func (s *torahOperationsSource) ReadDoc(ctx context.Context, _ source.ChangeReceiver, _ bool) (state.Doc, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	doc := state.NewDocWithInternalKey(s.Id(), nil, torahopscontract.UniqueKeyVersion).(*state.State)
	doc.SetDetailAndBundledRelation(bundle.RelationKeyId, domain.String(s.Id()))
	doc.SetDetailAndBundledRelation(bundle.RelationKeySpaceId, domain.String(s.SpaceID()))
	doc.SetDetailAndBundledRelation(bundle.RelationKeyIsHidden, domain.Bool(true))
	return doc, nil
}

func (*torahOperationsSource) PushChange(source.PushChangeParams) (string, error) {
	return "", torahopscontract.ErrPrivateOperation
}

func (*torahOperationsSource) ReadOnly() bool                            { return true }
func (*torahOperationsSource) GetFileKeysSnapshot() []*pb.ChangeFileKeys { return nil }
func (*torahOperationsSource) GetCreationInfo() (string, int64, error)   { return "", 0, nil }
