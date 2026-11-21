package torahopsobject

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"slices"
	"sync"
	"sync/atomic"
	"time"
	"unicode/utf8"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/net/peer"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
)

// One request gets one bounded preload window, not a new timeout per target.
const operationTargetLoadTimeout = 15 * time.Second
const maxOperationTargetGraphNodes = 100000

func operationTargetText(value string) bool {
	return value != "" && len(value) <= 1024 && utf8.ValidString(value) && !bytes.ContainsRune([]byte(value), 0)
}

func operationAuthorityField(out *bytes.Buffer, value []byte) {
	_ = binary.Write(out, binary.BigEndian, uint32(len(value)))
	_, _ = out.Write(value)
}

// AcquireNativeOperationTargetsLease loads all distinct documents before any
// cross-object lock. It then owns settings once, sorted document locks, and
// retains them through the caller's private-tree/current-ACL read. It cannot be
// nested into the single-target write lease. The complete target set is always
// acquired by this one call, never by recursively acquiring per-target leases.
func AcquireNativeOperationTargetsLease(ctx context.Context, space smartblock.Space, privateID string,
	targets []torahops.Target) (torahops.OperationTargetLease, error) {
	empty := torahops.OperationTargetLease{}
	if ctx == nil {
		return empty, torahops.ErrInvalid
	}
	if err := ctx.Err(); err != nil {
		return empty, err
	}
	if space == nil || !operationTargetText(privateID) || len(targets) > torahops.MaxVariants ||
		ctx.Value(targetLeaseKey{}) != nil {
		return empty, ErrTargetUnavailable
	}
	loader, ok := space.(nativeTargetSpace)
	if !ok {
		return empty, ErrTargetUnavailable
	}
	requested := make(map[torahops.Target]bool, len(targets))
	byObject := map[string][]torahops.Target{}
	for _, target := range targets {
		if !operationTargetText(target.ObjectID) || target.ObjectID == privateID ||
			(target.BlockID != "" && !operationTargetText(target.BlockID)) || requested[target] {
			return empty, ErrTargetUnavailable
		}
		requested[target] = true
		byObject[target.ObjectID] = append(byObject[target.ObjectID], target)
	}
	ids := make([]string, 0, len(byObject))
	for id := range byObject {
		ids = append(ids, id)
	}
	slices.Sort(ids)
	loadCtx, cancel := context.WithTimeout(ctx, operationTargetLoadTimeout)
	defer cancel()
	if _, err := peer.CtxPeerId(loadCtx); errors.Is(err, peer.ErrPeerIdNotFoundInContext) {
		loadCtx = peer.CtxWithPeerId(loadCtx, peer.CtxResponsiblePeers)
	}
	objects := make([]smartblock.SmartBlock, 0, len(ids))
	for _, id := range ids {
		object, err := loader.GetObject(loadCtx, id)
		if err != nil {
			return empty, errors.Join(ErrTargetUnavailable, err)
		}
		if object == nil || object.Id() != id {
			return empty, ErrTargetUnavailable
		}
		objects = append(objects, object)
	}
	settings, err := loader.PinkhaTorahSettingsTree(loadCtx)
	if err != nil {
		return empty, err
	}
	if settings == nil || settings.Id() == privateID || settings.AclList() == nil {
		return empty, ErrTargetUnavailable
	}
	for _, id := range ids {
		if id == settings.Id() {
			return empty, ErrTargetUnavailable
		}
	}
	if err = ctx.Err(); err != nil {
		return empty, err
	}
	settings.Lock()
	locked := 0
	var once sync.Once
	var active atomic.Bool
	active.Store(true)
	release := func() {
		once.Do(func() {
			active.Store(false)
			for index := locked - 1; index >= 0; index-- {
				objects[index].Unlock()
			}
			settings.Unlock()
		})
	}
	keep := false
	defer func() {
		if !keep {
			release()
		}
	}()
	if err = ctx.Err(); err != nil {
		return empty, err
	}
	// Reconstruct signed genesis history once for the whole target set. A
	// snapshot-only deletion set is not sufficient authority for this read.
	if err = rejectDeletedOperationTargets(ctx, settings, byObject); err != nil {
		return empty, err
	}
	for _, object := range objects {
		object.Lock()
		locked++
		if err = ctx.Err(); err != nil {
			return empty, err
		}
	}
	result := torahops.OperationTargetLease{ACL: settings.AclList(),
		Reachability: make(map[torahops.Target]torahops.OperationTargetReachability, len(targets)), Release: release}
	authority := bytes.NewBufferString(torahops.AuthorizedOperationReadContract + "\x00heart-targets\x00")
	operationAuthorityField(authority, []byte(space.Id()))
	operationAuthorityField(authority, []byte(settings.Id()))
	if err = appendOperationAuthorityHeads(authority, settings); err != nil {
		return empty, err
	}
	for _, object := range objects {
		id := object.Id()
		if !loader.PinkhaTorahTargetIsCurrent(object) {
			return empty, ErrTargetUnavailable
		}
		// Whole missing/deleted/uninstalled/non-document objects cannot supply
		// historical eligibility. This check intentionally uses a document target
		// so an absent block can be classified only after validating its graph.
		if err = validateNativeSmartblock(ctx, space, torahops.Target{ObjectID: id}, object); err != nil {
			return empty, err
		}
		tree := object.Tree()
		if tree == nil || tree.Id() != id || tree.AclList() != settings.AclList() {
			return empty, ErrTargetUnavailable
		}
		operationAuthorityField(authority, []byte(id))
		if err = appendOperationAuthorityHeads(authority, tree); err != nil {
			return empty, err
		}
		reachable, graphErr := validateOperationDocumentGraph(ctx, object, object.RootId(), nil)
		if graphErr != nil {
			return empty, graphErr
		}
		objectTargets := slices.Clone(byObject[id])
		slices.SortFunc(objectTargets, func(a, b torahops.Target) int {
			if a.BlockID < b.BlockID {
				return -1
			}
			if a.BlockID > b.BlockID {
				return 1
			}
			return 0
		})
		for _, target := range objectTargets {
			status := torahops.OperationLiveDocument
			if target.BlockID != "" {
				status = torahops.OperationUnreachableBlock
				if reachable[target.BlockID] {
					status = torahops.OperationLiveBlock
				} else if object.Pick(target.BlockID) != nil {
					// Inspect only a requested orphan component, never unrelated
					// orphan history. A malformed/cyclic requested component is not
					// evidence of safe historical reachability.
					if _, graphErr = validateOperationDocumentGraph(ctx, object, target.BlockID, reachable); graphErr != nil {
						return empty, graphErr
					}
				}
			}
			result.Reachability[target] = status
			operationAuthorityField(authority, []byte(target.BlockID))
			operationAuthorityField(authority, []byte(status))
		}
	}
	result.Validate = func(check context.Context) error {
		if check == nil {
			return torahops.ErrInvalid
		}
		if err := check.Err(); err != nil {
			return err
		}
		if !active.Load() {
			return ErrTargetUnavailable
		}
		for _, object := range objects {
			if !loader.PinkhaTorahTargetIsCurrent(object) {
				return ErrTargetUnavailable
			}
		}
		return nil
	}
	if err = result.Validate(ctx); err != nil {
		return empty, err
	}
	digest := sha256.Sum256(authority.Bytes())
	result.SnapshotToken = hex.EncodeToString(digest[:])
	keep = true
	return result, nil
}

func appendOperationAuthorityHeads(out *bytes.Buffer, tree objecttree.ObjectTree) error {
	heads := slices.Clone(tree.Heads())
	slices.Sort(heads)
	if len(heads) == 0 || len(heads) > 10000 {
		return torahops.ErrReadLimit
	}
	_ = binary.Write(out, binary.BigEndian, uint32(len(heads)))
	for _, head := range heads {
		if !operationTargetText(head) {
			return ErrTargetUnavailable
		}
		operationAuthorityField(out, []byte(head))
	}
	return nil
}

// Do not call State.Blocks or State.Iterate here: Blocks has no cycle bound and
// Iterate silently skips missing children. This traversal rejects an ambiguous
// requested graph while preserving all native State without modifying it.
func validateOperationDocumentGraph(ctx context.Context, object smartblock.SmartBlock, root string,
	forbidden map[string]bool) (map[string]bool, error) {
	if !operationTargetText(root) || object.RootId() != object.Id() {
		return nil, ErrTargetUnavailable
	}
	seen := map[string]bool{root: true}
	queue := []string{root}
	for index := 0; index < len(queue); index++ {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		id := queue[index]
		if forbidden[id] {
			return nil, ErrTargetUnavailable
		}
		block := object.Pick(id)
		if block == nil || block.Model() == nil || block.Model().Id != id {
			return nil, ErrTargetUnavailable
		}
		for _, child := range block.Model().ChildrenIds {
			if !operationTargetText(child) || seen[child] || forbidden[child] {
				return nil, ErrTargetUnavailable
			}
			if len(seen) == maxOperationTargetGraphNodes {
				return nil, torahops.ErrReadLimit
			}
			seen[child] = true
			queue = append(queue, child)
		}
	}
	return seen, nil
}

// Caller holds the actual live settings lock. This is the same signed genesis
// deletion predicate as the single-target write lease, evaluated once for the
// complete read closure (including a SpaceDelete when the closure is empty).
func rejectDeletedOperationTargets(ctx context.Context, settings objecttree.ObjectTree, targets map[string][]torahops.Target) error {
	history, err := objecttree.BuildHistoryTree(objecttree.HistoryTreeParams{Storage: settings.Storage(), AclList: settings.AclList()})
	if err != nil {
		return err
	}
	if history.Root().Id != settings.Id() {
		return torahops.ErrInvalid
	}
	var iterErr error
	err = history.IterateRoot(func(_ *objecttree.Change, data []byte) (any, error) {
		value := &spacesyncproto.SettingsData{}
		if err := value.UnmarshalVT(data); err != nil {
			return nil, err
		}
		return value, nil
	}, func(change *objecttree.Change) bool {
		if iterErr = ctx.Err(); iterErr != nil {
			return false
		}
		if len(change.PreviousIds) == 0 {
			return true
		}
		data, ok := change.Model.(*spacesyncproto.SettingsData)
		if !ok || data == nil {
			iterErr = torahops.ErrInvalid
			return false
		}
		for _, content := range data.GetContent() {
			_, deleted := targets[content.GetObjectDelete().GetId()]
			if deleted || content.GetSpaceDelete() != nil {
				iterErr = ErrTargetUnavailable
				return false
			}
		}
		return true
	})
	return errors.Join(err, iterErr, ctx.Err())
}
