package torahopsobject

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"slices"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/objecttreebuilder"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/cidutil"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock/smarttest"
	"github.com/anyproto/anytype-heart/core/block/simple"
	"github.com/anyproto/anytype-heart/core/block/simple/text"
	"github.com/anyproto/anytype-heart/internal/pinkhat2test"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
	"github.com/stretchr/testify/require"
)

// Native ACL, signed tree storage and the new lease/witness are real. The loaded
// SmartBlock/cache adapter is controlled, so these tests do not claim a complete
// production Page Apply, account-stop, wire or Apple journey.
type semanticLeaseBlock struct {
	*smarttest.SmartTest
	tree objecttree.ObjectTree
}

func (block *semanticLeaseBlock) Lock()   { block.tree.Lock() }
func (block *semanticLeaseBlock) Unlock() { block.tree.Unlock() }

type semanticLeaseSpace struct {
	smartblock.Space
	id       string
	target   *semanticLeaseBlock
	settings objecttree.ObjectTree
	current  bool
}

func (space *semanticLeaseSpace) Id() string { return space.id }
func (space *semanticLeaseSpace) GetObject(ctx context.Context, id string) (smartblock.SmartBlock, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if id != space.target.Id() {
		return nil, semanticanchor.ErrUnavailable
	}
	return space.target, nil
}
func (space *semanticLeaseSpace) PinkhaTorahSettingsTree(context.Context) (objecttree.ObjectTree, error) {
	return space.settings, nil
}
func (space *semanticLeaseSpace) PinkhaTorahTargetIsCurrent(block smartblock.SmartBlock) bool {
	return space.current && block == space.target
}

func newSemanticLeaseFixture(t *testing.T) (*pinkhat2test.Fixture, *semanticLeaseSpace, semanticanchor.CaptureRequest) {
	t.Helper()
	f := pinkhat2test.NewWithoutPrivateRoot(t)
	ctx := context.Background()
	root, err := objecttree.CreateObjectTreeRoot(objecttree.ObjectTreeCreatePayload{PrivKey: f.Keys.SignKey,
		ChangeType: "semantic-anchor-controlled-target", SpaceId: f.Space.Id(), IsEncrypted: true,
		Seed: []byte("disposable-semantic-anchor-target"), Timestamp: 1}, f.ACL)
	require.NoError(t, err)
	_, err = f.Space.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}})
	require.NoError(t, err)
	tree, err := f.Builder.BuildTree(ctx, root.Id, objecttreebuilder.BuildTreeOpts{TreeBuilder: objecttree.BuildObjectTree})
	require.NoError(t, err)
	sb := smarttest.NewWithTree(root.Id, tree)
	sb.SetSpaceId(f.Space.Id())
	sb.AddBlock(simple.New(&model.Block{Id: root.Id, ChildrenIds: []string{"paragraph"}}))
	sb.AddBlock(text.NewText(&model.Block{Id: "paragraph", Content: &model.BlockContentOfText{Text: &model.BlockContentText{Text: "אבג 😀 text"}}}))
	space := &semanticLeaseSpace{id: f.Space.Id(), target: &semanticLeaseBlock{SmartTest: sb, tree: tree}, settings: f.Settings, current: true}
	request := semanticanchor.CaptureRequest{Version: 1, SpaceID: space.Id(), ObjectID: root.Id, BlockID: "paragraph",
		AnchorID: "00112233-4455-6677-8899-aabbccddeeff", From: 4, To: 6, Expected: semanticanchor.Snapshot{Text: "אבג 😀 text"}}
	return f, space, request
}

func assertSemanticLeaseUnlocked(t *testing.T, space *semanticLeaseSpace) {
	t.Helper()
	require.True(t, space.target.tree.TryLock(), "native document mutex must be released")
	space.target.tree.Unlock()
	require.True(t, space.settings.TryLock(), "native settings mutex must be released")
	space.settings.Unlock()
}

func semanticStoredChange(t *testing.T, f *pinkhat2test.Fixture, space *semanticLeaseSpace) string {
	t.Helper()
	// Caller holds the actual object-tree lock. This is storage witness input,
	// not a substitute for the separate real Page Apply acceptance requirement.
	result, err := space.target.tree.AddContent(context.Background(), objecttree.SignableChangeContent{
		Data: []byte("controlled native signed storage witness"), Key: f.Keys.SignKey, ShouldBeEncrypted: true})
	require.NoError(t, err)
	require.Len(t, result.Heads, 1)
	return result.Heads[0]
}

func TestPinkhaSemanticAnchorLeaseRetainsNativeLocksAndOneCallStoredWitness(t *testing.T) {
	f, space, request := newSemanticLeaseFixture(t)
	ctx, loaded, release, err := AcquireNativeSemanticAnchorLease(context.Background(), space, f.Keys.SignKey.GetPublic(), request)
	require.NoError(t, err)
	defer release()
	require.Same(t, space.target, loaded)
	require.False(t, space.settings.TryLock())
	require.False(t, space.target.tree.TryLock())
	before := slices.Clone(space.target.tree.Heads())
	_, err = VerifySemanticAnchorNativeChange(ctx, space.target.tree, before[0], "not-a-write", before)
	require.ErrorIs(t, err, semanticanchor.ErrUnavailable, "unborrowed lease must not acknowledge writes")
	wrong := request
	wrong.Expected.Text = "other native text"
	_, err = BorrowNativeSemanticAnchorLease(ctx, space.target.tree, wrong)
	require.ErrorIs(t, err, semanticanchor.ErrUnavailable)
	validate, err := BorrowNativeSemanticAnchorLease(ctx, space.target.tree, request)
	require.NoError(t, err)
	require.NoError(t, validate())
	_, err = BorrowNativeSemanticAnchorLease(ctx, space.target.tree, request)
	require.ErrorIs(t, err, semanticanchor.ErrUnavailable)
	changeID := semanticStoredChange(t, f, space)
	actual, err := VerifySemanticAnchorNativeChange(ctx, space.target.tree, before[0], changeID, before)
	require.NoError(t, err)
	stored, err := space.target.tree.Storage().Get(context.Background(), changeID)
	require.NoError(t, err)
	hash := sha256.Sum256(stored.RawChange)
	require.Equal(t, hex.EncodeToString(hash[:]), actual)
	require.False(t, space.settings.TryLock(), "durable write must not release this document's settings lease early")
	require.False(t, space.target.tree.TryLock(), "Apply/post-read still owns the actual document mutex")
	_, err = VerifySemanticAnchorNativeChange(ctx, space.target.tree, before[0], changeID, []string{"different-parent"})
	require.ErrorIs(t, err, semanticanchor.ErrUncertain)
	release()
	release()
	assertSemanticLeaseUnlocked(t, space)
	require.ErrorIs(t, validate(), semanticanchor.ErrUnavailable)
	// The real storage above deliberately returns an unhydrated TreeId. These
	// controlled faults keep that compatibility fix from admitting a different
	// native storage handle, conflicting metadata or changed signed bytes.
	assertSemanticWitnessStorageBindings(t)
}

type semanticWitnessStorage struct {
	objecttree.Storage
	fault string
}

func (storage *semanticWitnessStorage) Id() string {
	if storage.fault == "foreign-storage" {
		return "another-native-tree"
	}
	return storage.Storage.Id()
}

func (storage *semanticWitnessStorage) Get(ctx context.Context, id string) (objecttree.StorageChange, error) {
	stored, err := storage.Storage.Get(ctx, id)
	if err != nil {
		return stored, err
	}
	stored.RawChange = slices.Clone(stored.RawChange)
	switch storage.fault {
	case "foreign-record-tree":
		stored.TreeId = "another-native-tree"
	case "foreign-change-id":
		stored.Id = "another-native-change"
	case "changed-signed-bytes":
		stored.RawChange[len(stored.RawChange)-1] ^= 1
	}
	return stored, nil
}

func (storage *semanticWitnessStorage) Heads(ctx context.Context) ([]string, error) {
	if storage.fault == "foreign-storage-heads" {
		return []string{"another-native-change"}, nil
	}
	return storage.Storage.Heads(ctx)
}

type semanticWitnessTree struct {
	objecttree.ObjectTree
	storage objecttree.Storage
}

func (tree *semanticWitnessTree) Storage() objecttree.Storage { return tree.storage }

type semanticWitnessBlock struct {
	*semanticLeaseBlock
	witnessTree objecttree.ObjectTree
}

func (block *semanticWitnessBlock) Tree() objecttree.ObjectTree { return block.witnessTree }

type semanticWitnessSpace struct {
	*semanticLeaseSpace
	witnessBlock *semanticWitnessBlock
}

func (space *semanticWitnessSpace) GetObject(ctx context.Context, id string) (smartblock.SmartBlock, error) {
	if _, err := space.semanticLeaseSpace.GetObject(ctx, id); err != nil {
		return nil, err
	}
	return space.witnessBlock, nil
}

func (space *semanticWitnessSpace) PinkhaTorahTargetIsCurrent(block smartblock.SmartBlock) bool {
	return space.current && block == space.witnessBlock
}

func assertSemanticWitnessStorageBindings(t *testing.T) {
	t.Helper()
	for _, fault := range []string{"foreign-storage", "foreign-record-tree", "foreign-change-id", "changed-signed-bytes", "foreign-storage-heads"} {
		f, original, request := newSemanticLeaseFixture(t)
		storage := &semanticWitnessStorage{Storage: original.target.tree.Storage(), fault: fault}
		tree := &semanticWitnessTree{ObjectTree: original.target.tree, storage: storage}
		block := &semanticWitnessBlock{semanticLeaseBlock: original.target, witnessTree: tree}
		space := &semanticWitnessSpace{semanticLeaseSpace: original, witnessBlock: block}
		ctx, _, release, err := AcquireNativeSemanticAnchorLease(context.Background(), space, f.Keys.SignKey.GetPublic(), request)
		require.NoError(t, err, fault)
		defer release()
		_, err = BorrowNativeSemanticAnchorLease(ctx, tree, request)
		require.NoError(t, err, fault)
		before := slices.Clone(tree.Heads())
		changeID := semanticStoredChange(t, f, original)
		actual, err := VerifySemanticAnchorNativeChange(ctx, tree, before[0], changeID, before)
		require.ErrorIs(t, err, semanticanchor.ErrUncertain, fault)
		require.Empty(t, actual, fault)
		release()
		assertSemanticLeaseUnlocked(t, original)
	}
}

func TestPinkhaSemanticAnchorLeaseRejectsStaleDeletedOrphanAndDuplicateTargets(t *testing.T) {
	for _, scenario := range []string{"stale-cache", "native-deleted", "signed-settings-deleted", "orphan-block", "missing-block", "duplicate-marker"} {
		t.Run(scenario, func(t *testing.T) {
			f, space, request := newSemanticLeaseFixture(t)
			want := semanticanchor.ErrUnavailable
			switch scenario {
			case "stale-cache":
				space.current = false
			case "native-deleted":
				space.target.SetIsDeleted()
			case "signed-settings-deleted":
				wire, err := (&spacesyncproto.SettingsData{Content: []*spacesyncproto.SpaceSettingsContent{
					{Value: &spacesyncproto.SpaceSettingsContent_ObjectDelete{ObjectDelete: &spacesyncproto.ObjectDelete{Id: request.ObjectID}}}}}).MarshalVT()
				require.NoError(t, err)
				space.settings.Lock()
				_, err = space.settings.AddContent(context.Background(), objecttree.SignableChangeContent{Data: wire, Key: f.Keys.SignKey})
				space.settings.Unlock()
				require.NoError(t, err)
			case "orphan-block":
				space.target.Pick(request.ObjectID).Model().ChildrenIds = nil
			case "missing-block":
				request.BlockID = "missing"
			case "duplicate-marker":
				marker, err := request.Validate()
				require.NoError(t, err)
				space.target.Pick(request.BlockID).Model().GetText().Marks = &model.BlockContentTextMarks{Marks: []*model.BlockContentTextMark{
					{Range: &model.Range{From: 7, To: 11}, Type: model.BlockContentTextMark_Link, Param: marker}}}
				want = semanticanchor.ErrDuplicate
			}
			ctx, loaded, release, err := AcquireNativeSemanticAnchorLease(context.Background(), space, f.Keys.SignKey.GetPublic(), request)
			require.ErrorIs(t, err, want)
			require.Nil(t, ctx)
			require.Nil(t, loaded)
			require.Nil(t, release)
			assertSemanticLeaseUnlocked(t, space)
		})
	}
}

func semanticApplyACL(t *testing.T, acl list.AclList, raw *consensusproto.RawRecord) {
	t.Helper()
	require.NoError(t, acl.ValidateRawRecord(raw, nil))
	data, err := raw.MarshalVT()
	require.NoError(t, err)
	id, err := cidutil.NewCidFromBytes(data)
	require.NoError(t, err)
	require.NoError(t, acl.AddRawRecord(&consensusproto.RawRecordWithId{Id: id, Payload: data}))
	require.Equal(t, id, acl.Head().Id)
}

func semanticDowngradeOwner(t *testing.T, f *pinkhat2test.Fixture) {
	t.Helper()
	member, err := accountdata.NewRandom()
	require.NoError(t, err)
	f.ACL.Lock()
	defer f.ACL.Unlock()
	raw, err := f.ACL.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{
		{Identity: member.SignKey.GetPublic(), Permissions: list.AclPermissionsWriter, Metadata: []byte("disposable semantic control member")}}})
	require.NoError(t, err)
	semanticApplyACL(t, f.ACL, raw)
	raw, err = f.ACL.RecordBuilder().BuildOwnershipChange(list.OwnershipChangePayload{
		NewOwner: member.SignKey.GetPublic(), OldOwnerPermissions: list.AclPermissionsReader})
	require.NoError(t, err)
	semanticApplyACL(t, f.ACL, raw)
	require.Equal(t, list.AclPermissionsReader, f.ACL.AclState().Permissions(f.Keys.SignKey.GetPublic()))
}

func TestPinkhaSemanticAnchorLeaseRechecksSignedWriteAuthorityBeforeAndAfterCommit(t *testing.T) {
	for _, committed := range []bool{false, true} {
		t.Run(map[bool]string{false: "before-native-write", true: "after-native-write"}[committed], func(t *testing.T) {
			f, space, request := newSemanticLeaseFixture(t)
			ctx, _, release, err := AcquireNativeSemanticAnchorLease(context.Background(), space, f.Keys.SignKey.GetPublic(), request)
			require.NoError(t, err)
			defer release()
			before := slices.Clone(space.target.tree.Heads())
			changeID := ""
			if committed {
				_, err = BorrowNativeSemanticAnchorLease(ctx, space.target.tree, request)
				require.NoError(t, err)
				changeID = semanticStoredChange(t, f, space)
			}
			semanticDowngradeOwner(t, f)
			if committed {
				value, err := VerifySemanticAnchorNativeChange(ctx, space.target.tree, before[0], changeID, before)
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
				require.Empty(t, value, "known changed authority cannot acknowledge the stored change")
				require.Equal(t, []string{changeID}, space.target.tree.Heads(), "a committed uncertain result is not rolled back")
			} else {
				_, err = BorrowNativeSemanticAnchorLease(ctx, space.target.tree, request)
				require.ErrorIs(t, err, list.ErrInsufficientPermissions)
				require.Equal(t, before, space.target.tree.Heads())
			}
		})
	}
}

func TestPinkhaSemanticAnchorLeaseRechecksHookGraphAndCancellation(t *testing.T) {
	for _, scenario := range []string{"duplicate-other-block", "stale-cache-after-borrow", "context-cancelled"} {
		t.Run(scenario, func(t *testing.T) {
			f, space, request := newSemanticLeaseFixture(t)
			parent, cancel := context.WithCancel(context.Background())
			defer cancel()
			ctx, _, release, err := AcquireNativeSemanticAnchorLease(parent, space, f.Keys.SignKey.GetPublic(), request)
			require.NoError(t, err)
			defer release()
			validate, err := BorrowNativeSemanticAnchorLease(ctx, space.target.tree, request)
			require.NoError(t, err)
			want := semanticanchor.ErrUnavailable
			switch scenario {
			case "duplicate-other-block":
				marker, err := request.Validate()
				require.NoError(t, err)
				space.target.Pick(request.ObjectID).Model().ChildrenIds = append(space.target.Pick(request.ObjectID).Model().ChildrenIds, "another")
				space.target.AddBlock(text.NewText(&model.Block{Id: "another", Content: &model.BlockContentOfText{Text: &model.BlockContentText{
					Text: "another", Marks: &model.BlockContentTextMarks{Marks: []*model.BlockContentTextMark{
						{Range: &model.Range{From: 0, To: 3}, Type: model.BlockContentTextMark_Link, Param: marker}}}}}}))
				want = semanticanchor.ErrDuplicate
			case "stale-cache-after-borrow":
				space.current = false
			case "context-cancelled":
				cancel()
				want = context.Canceled
			}
			require.ErrorIs(t, validate(), want)
			release()
			assertSemanticLeaseUnlocked(t, space)
		})
	}
}
