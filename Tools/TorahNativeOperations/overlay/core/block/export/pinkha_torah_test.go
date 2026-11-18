package export

import (
	"context"
	"errors"
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block/cache"
	editorsb "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/state"
	"github.com/anyproto/anytype-heart/core/block/export/collect"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
)

type pinkhaExportBlock struct {
	editorsb.SmartBlock
	kind       smartblock.SmartBlockType
	stateReads int
	locks      int
}

func (b *pinkhaExportBlock) Type() smartblock.SmartBlockType { return b.kind }
func (b *pinkhaExportBlock) Lock()                           { b.locks++ }
func (*pinkhaExportBlock) Unlock()                           {}
func (b *pinkhaExportBlock) NewState() *state.State {
	b.stateReads++
	panic("private export reached NewState")
}

type pinkhaExportGetter struct {
	cache.CachedObjectGetter
	object       editorsb.SmartBlock
	err          error
	getCalls     int
	fullCalls    int
	removeCalls  int
	lastContext  context.Context
	lastObjectID string
	lastFullID   domain.FullID
	removeResult bool
	removeErr    error
}

func (g *pinkhaExportGetter) GetObject(ctx context.Context, id string) (editorsb.SmartBlock, error) {
	g.getCalls++
	g.lastContext, g.lastObjectID = ctx, id
	return g.object, g.err
}

func (g *pinkhaExportGetter) GetObjectByFullID(ctx context.Context, id domain.FullID) (editorsb.SmartBlock, error) {
	g.fullCalls++
	g.lastContext, g.lastFullID = ctx, id
	return g.object, g.err
}

func (g *pinkhaExportGetter) TryRemoveFromCache(ctx context.Context, id string) (bool, error) {
	g.removeCalls++
	g.lastContext, g.lastObjectID = ctx, id
	return g.removeResult, g.removeErr
}

func TestPinkhaExportGetterPreservesNativeTypeAndCacheLifecycle(t *testing.T) {
	for _, fullID := range []bool{false, true} {
		for _, scenario := range []string{"private", "ordinary", "lookup_error", "nil_result"} {
			name := "id/" + scenario
			if fullID {
				name = "full_id/" + scenario
			}
			t.Run(name, func(t *testing.T) {
				ctx, cancel := context.WithCancel(context.Background())
				defer cancel()
				block := &pinkhaExportBlock{kind: smartblock.SmartBlockTypePage}
				lookupErr := errors.New("original lookup error")
				removeErr := errors.New("original cache removal error")
				getter := &pinkhaExportGetter{object: block, removeErr: removeErr}
				switch scenario {
				case "private":
					block.kind = smartblock.SmartBlockTypePinkhaTorahOperations
				case "lookup_error":
					getter.object, getter.err = nil, lookupErr
				case "nil_result":
					getter.object = nil
				}
				guard := privateTorahExportGetter{CachedObjectGetter: getter}
				id := domain.FullID{SpaceID: "export-test-space", ObjectID: "export-test-object"}
				var got editorsb.SmartBlock
				var err error
				if fullID {
					got, err = guard.GetObjectByFullID(ctx, id)
					require.Equal(t, 1, getter.fullCalls)
					require.Zero(t, getter.getCalls)
					require.Equal(t, id, getter.lastFullID)
				} else {
					got, err = guard.GetObject(ctx, id.ObjectID)
					require.Equal(t, 1, getter.getCalls)
					require.Zero(t, getter.fullCalls)
					require.Equal(t, id.ObjectID, getter.lastObjectID)
				}
				require.Same(t, ctx, getter.lastContext)
				if scenario == "private" {
					require.Nil(t, got)
					require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
				} else {
					require.Equal(t, getter.object, got)
					if getter.err == nil {
						require.NoError(t, err)
					} else {
						require.Same(t, getter.err, err)
					}
				}
				require.Zero(t, block.stateReads)
				require.Zero(t, block.locks)
				removed, err := guard.TryRemoveFromCache(ctx, id.ObjectID)
				require.False(t, removed)
				require.Same(t, removeErr, err)
				require.Equal(t, 1, getter.removeCalls)
				require.Same(t, ctx, getter.lastContext)
				require.Equal(t, id.ObjectID, getter.lastObjectID)
			})
		}
	}
}

func TestPinkhaExportContextGuardIsScopedAndCopied(t *testing.T) {
	block := &pinkhaExportBlock{kind: smartblock.SmartBlockTypePinkhaTorahOperations}
	getter := &pinkhaExportGetter{object: block}
	service := &export{picker: getter}
	ec := newExportContext(service, pb.RpcObjectListExportRequest{})
	require.Same(t, getter, service.picker, "shared service must remain unchanged")
	require.NotSame(t, service, ec.export)
	require.Same(t, ec.export, withPrivateTorahExportGuard(ec.export), "do not stack wrappers")
	for _, current := range []*exportContext{ec, ec.copy()} {
		object, err := current.picker.GetObject(context.Background(), "private-root")
		require.Nil(t, object)
		require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	}
	require.Equal(t, 2, getter.getCalls)
	require.Zero(t, block.stateReads)
}

func pinkhaPrivateExportFixture(t *testing.T, hidden bool) (*fixture, *pinkhaExportBlock, *pinkhaExportGetter) {
	t.Helper()
	fx := newFixture(t)
	block := &pinkhaExportBlock{kind: smartblock.SmartBlockTypePinkhaTorahOperations}
	getter := &pinkhaExportGetter{object: block}
	fx.export.picker = getter
	// An indexed envelope is intentionally supplied: denial must come from the
	// actual native type, even if an index is stale or advertises a public page.
	fx.store.AddObjects(t, spaceId, []spaceindex.TestObject{{
		bundle.RelationKeyId:             domain.String("private-root"),
		bundle.RelationKeySpaceId:        domain.String(spaceId),
		bundle.RelationKeyName:           domain.String("private envelope"),
		bundle.RelationKeyResolvedLayout: domain.Int64(int64(model.ObjectType_basic)),
		bundle.RelationKeyIsHidden:       domain.Bool(hidden),
	}})
	return fx, block, getter
}

func TestPinkhaPrivateObjectSingleExportDenied(t *testing.T) {
	for _, format := range []model.ExportFormat{model.Export_Protobuf, model.Export_JSON, model.Export_Markdown, model.Export_AnyBlockV2} {
		t.Run(format.String(), func(t *testing.T) {
			fx, block, getter := pinkhaPrivateExportFixture(t, true)
			result, diagnostics, err := fx.ExportSingleInMemory(context.Background(), spaceId, "private-root", format)
			require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
			require.Empty(t, result)
			require.NotNil(t, diagnostics)
			require.Equal(t, model.ExportReport_FAILED, diagnostics.Status)
			require.Zero(t, diagnostics.Succeed)
			require.GreaterOrEqual(t, diagnostics.ObjectErrors, int32(1))
			require.GreaterOrEqual(t, getter.getCalls, 1)
			require.Zero(t, block.stateReads)
			require.Zero(t, block.locks)
		})
	}
}

func TestPinkhaPrivateObjectListAndCollectDenied(t *testing.T) {
	t.Run("Collect", func(t *testing.T) {
		fx, block, getter := pinkhaPrivateExportFixture(t, false)
		docs, err := fx.Collect(context.Background(), collect.Request{
			SpaceId: spaceId, Ids: []string{"private-root"}, Closure: collect.ClosureDerived,
		})
		require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
		require.Empty(t, docs)
		require.GreaterOrEqual(t, getter.getCalls, 1)
		require.Zero(t, block.stateReads)
		require.Zero(t, block.locks)
	})
	for _, format := range []model.ExportFormat{model.Export_Protobuf, model.Export_AnyBlockV2} {
		t.Run("List/"+format.String(), func(t *testing.T) {
			fx, block, getter := pinkhaPrivateExportFixture(t, false)
			fx.sender.EXPECT().Broadcast(mock.Anything).Return().Maybe()
			notified := setupNotificationsMock(fx.notifications)
			directory := t.TempDir()
			path, diagnostics, err := fx.Export(context.Background(), pb.RpcObjectListExportRequest{
				SpaceId: spaceId, ObjectIds: []string{"private-root"}, Format: format,
				Path: directory, Zip: true, NoProgress: true,
			})
			require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
			require.Empty(t, path)
			require.NotNil(t, diagnostics)
			require.Equal(t, model.ExportReport_FAILED, diagnostics.Status)
			require.Zero(t, diagnostics.Succeed)
			require.GreaterOrEqual(t, getter.getCalls, 1)
			require.Zero(t, block.stateReads)
			require.Zero(t, block.locks)
			entries, err := os.ReadDir(directory)
			require.NoError(t, err)
			require.Empty(t, entries, "no private export file may be created")
			select {
			case <-notified:
			case <-time.After(5 * time.Second):
				t.Fatal("export completion notification did not finish")
			}
		})
	}
}
