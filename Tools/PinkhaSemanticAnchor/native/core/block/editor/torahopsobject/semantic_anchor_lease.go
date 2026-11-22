package torahopsobject

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"slices"
	"sync"
	"sync/atomic"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/net/peer"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
)

type semanticAnchorLeaseKey struct{}

// A semantic capture mutates this document itself. Unlike the private-journal
// lease it never releases the document lock at AddAll: Apply's undo, projection
// and the exact post-read must finish under the same native document mutex.
type semanticAnchorLease struct {
	space    smartblock.Space
	loader   nativeTargetSpace
	object   smartblock.SmartBlock
	tree     objecttree.ObjectTree
	author   crypto.PubKey
	request  semanticanchor.CaptureRequest
	active   atomic.Bool
	borrowed atomic.Bool
	validate func(context.Context) error
}

// AcquireNativeSemanticAnchorLease follows the existing writer lock order:
// application lifetime (owned by the native entry) -> settings -> document.
// Loading happens before settings/document locks. It is not a publication
// lease; the caller must retain and release its outer application write scope.
func AcquireNativeSemanticAnchorLease(ctx context.Context, space smartblock.Space, author crypto.PubKey,
	request semanticanchor.CaptureRequest) (context.Context, smartblock.SmartBlock, func(), error) {
	if ctx == nil {
		return nil, nil, nil, semanticanchor.ErrInvalid
	}
	if err := ctx.Err(); err != nil {
		return nil, nil, nil, err
	}
	marker, err := request.Validate()
	if err != nil {
		return nil, nil, nil, err
	}
	if space == nil || author == nil || space.Id() != request.SpaceID || ctx.Value(semanticAnchorLeaseKey{}) != nil || ctx.Value(targetLeaseKey{}) != nil {
		return nil, nil, nil, semanticanchor.ErrUnavailable
	}
	loader, ok := space.(nativeTargetSpace)
	if !ok {
		return nil, nil, nil, semanticanchor.ErrUnavailable
	}
	loadCtx, cancel := context.WithTimeout(ctx, operationTargetLoadTimeout)
	defer cancel()
	if _, err = peer.CtxPeerId(loadCtx); errors.Is(err, peer.ErrPeerIdNotFoundInContext) {
		loadCtx = peer.CtxWithPeerId(loadCtx, peer.CtxResponsiblePeers)
	}
	object, err := loader.GetObject(loadCtx, request.ObjectID)
	if err != nil {
		return nil, nil, nil, errors.Join(semanticanchor.ErrUnavailable, err)
	}
	settings, err := loader.PinkhaTorahSettingsTree(loadCtx)
	if err != nil {
		return nil, nil, nil, errors.Join(semanticanchor.ErrUnavailable, err)
	}
	if object == nil || settings == nil || object.Id() != request.ObjectID || settings.Id() == request.ObjectID {
		return nil, nil, nil, semanticanchor.ErrUnavailable
	}
	settings.Lock()
	if err = ctx.Err(); err == nil {
		err = rejectDeletedNativeTarget(ctx, settings, request.ObjectID)
	}
	if err != nil {
		settings.Unlock()
		return nil, nil, nil, errors.Join(semanticanchor.ErrUnavailable, err)
	}
	object.Lock()
	lease := &semanticAnchorLease{space: space, loader: loader, object: object, tree: object.Tree(), author: author, request: request}
	lease.request.Expected.Marks = slices.Clone(request.Expected.Marks)
	lease.active.Store(true)
	var once sync.Once
	release := func() {
		once.Do(func() {
			lease.active.Store(false)
			object.Unlock()
			settings.Unlock()
		})
	}
	keep := false
	defer func() {
		if !keep {
			release()
		}
	}()
	lease.validate = func(check context.Context) error {
		if check == nil {
			return semanticanchor.ErrInvalid
		}
		if err := check.Err(); err != nil {
			return err
		}
		if !lease.active.Load() || !loader.PinkhaTorahTargetIsCurrent(object) || object.Tree() != lease.tree ||
			lease.tree == nil || lease.tree.Id() != request.ObjectID || lease.tree.AclList() == nil ||
			lease.tree.AclList() != settings.AclList() {
			return semanticanchor.ErrUnavailable
		}
		if err := validateNativeSmartblock(check, space, torahops.Target{ObjectID: request.ObjectID, BlockID: request.BlockID}, object); err != nil {
			return errors.Join(semanticanchor.ErrUnavailable, err)
		}
		acl := lease.tree.AclList()
		acl.RLock()
		allowed := acl.AclState().Permissions(author).CanWrite()
		acl.RUnlock()
		if !allowed {
			return errors.Join(semanticanchor.ErrUnavailable, list.ErrInsufficientPermissions)
		}
		// Recheck the live graph after native NewState/Apply hooks too. A hook
		// cannot add another copy elsewhere while this capture acknowledges one
		// unique marker in the target block. The initial acquisition below still
		// requires zero copies; later validation permits only our one target mark.
		reachable, graphErr := validateOperationDocumentGraph(check, object, object.RootId(), nil)
		if graphErr != nil || !reachable[request.BlockID] {
			return errors.Join(semanticanchor.ErrUnavailable, graphErr)
		}
		if len(reachable) > semanticanchor.MaxDocumentBlocks {
			return semanticanchor.ErrLimit
		}
		copies := 0
		for id := range reachable {
			if err := check.Err(); err != nil {
				return err
			}
			marks := object.Pick(id).Model().GetText().GetMarks().GetMarks()
			if len(marks) > semanticanchor.MaxMarks {
				return semanticanchor.ErrLimit
			}
			for _, mark := range marks {
				if mark != nil && mark.Param == marker {
					copies++
					if id != request.BlockID || copies > 1 {
						return semanticanchor.ErrDuplicate
					}
				}
			}
		}
		return nil
	}
	if err = lease.validate(ctx); err != nil {
		return nil, nil, nil, err
	}
	// Capture requires a live reachable native block, not an orphan retained in
	// document storage. Check uniqueness in the complete current document too.
	reachable, err := validateOperationDocumentGraph(ctx, object, object.RootId(), nil)
	if err != nil || !reachable[request.BlockID] {
		return nil, nil, nil, errors.Join(semanticanchor.ErrUnavailable, err)
	}
	if len(reachable) > semanticanchor.MaxDocumentBlocks {
		return nil, nil, nil, semanticanchor.ErrLimit
	}
	for id := range reachable {
		if err = ctx.Err(); err != nil {
			return nil, nil, nil, err
		}
		content := object.Pick(id).Model().GetText()
		if content == nil {
			continue
		}
		for _, mark := range content.GetMarks().GetMarks() {
			if mark != nil && mark.Param == marker {
				return nil, nil, nil, semanticanchor.ErrDuplicate
			}
		}
	}
	keep = true
	return context.WithValue(ctx, semanticAnchorLeaseKey{}, lease), object, release, nil
}

// BorrowNativeSemanticAnchorLease admits exactly one matching editor call. The
// token is native-only and bound to the exact loaded/cache-current object/tree;
// RPC callers cannot supply an authority flag, document pointer or callback.
func BorrowNativeSemanticAnchorLease(ctx context.Context, tree objecttree.ObjectTree,
	request semanticanchor.CaptureRequest) (func() error, error) {
	if ctx == nil {
		return nil, semanticanchor.ErrInvalid
	}
	lease, _ := ctx.Value(semanticAnchorLeaseKey{}).(*semanticAnchorLease)
	if lease == nil || tree == nil || lease.tree != tree || !sameSemanticCapture(lease.request, request) {
		return nil, semanticanchor.ErrUnavailable
	}
	if err := lease.validate(ctx); err != nil {
		return nil, err
	}
	if !lease.borrowed.CompareAndSwap(false, true) {
		return nil, semanticanchor.ErrUnavailable
	}
	return func() error { return lease.validate(ctx) }, nil
}

func sameSemanticCapture(a, b semanticanchor.CaptureRequest) bool {
	return a.Version == b.Version && a.SpaceID == b.SpaceID && a.ObjectID == b.ObjectID && a.BlockID == b.BlockID &&
		a.AnchorID == b.AnchorID && a.From == b.From && a.To == b.To && a.Expected.Exact(b.Expected)
}

// VerifySemanticAnchorNativeChange reads the actual native storage after Apply.
// It does not infer persistence from a local marker or a nil Apply return. The
// document mutex remains held through the storage/head/signature checks.
func VerifySemanticAnchorNativeChange(ctx context.Context, tree objecttree.ObjectTree,
	beforeChangeID, changeID string, beforeHeads []string) (string, error) {
	if ctx == nil {
		return "", semanticanchor.ErrInvalid
	}
	lease, _ := ctx.Value(semanticAnchorLeaseKey{}).(*semanticAnchorLease)
	if lease == nil || tree == nil || lease.tree != tree || !lease.borrowed.Load() {
		return "", semanticanchor.ErrUnavailable
	}
	if err := lease.validate(ctx); err != nil {
		return "", err
	}
	storage := tree.Storage()
	if !semanticanchor.ValidIdentity(changeID) || changeID == beforeChangeID || len(beforeHeads) == 0 ||
		slices.Contains(beforeHeads, changeID) || !slices.Equal(tree.Heads(), []string{changeID}) ||
		storage == nil || storage.Id() != tree.Id() {
		return "", semanticanchor.ErrUncertain
	}
	stored, err := storage.Get(ctx, changeID)
	if err != nil {
		return "", errors.Join(semanticanchor.ErrUncertain, err)
	}
	storedHeads, err := storage.Heads(ctx)
	// any-sync v0.13.8 stores the tree ID but does not hydrate TreeId in
	// storage.changeFromDoc/Get. Bind the actual storage handle above instead;
	// a populated conflicting field remains invalid. Signed parents, current
	// storage heads and the immutable change bytes are still checked below.
	if err != nil || !slices.Equal(storedHeads, []string{changeID}) || stored.Id != changeID ||
		(stored.TreeId != "" && stored.TreeId != tree.Id()) || len(stored.RawChange) == 0 {
		return "", errors.Join(semanticanchor.ErrUncertain, err)
	}
	change, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), tree.Header()).Unmarshall(stored.RawTreeChangeWithId(), true)
	if err != nil || change == nil || change.Id != changeID || change.Identity == nil ||
		!change.Identity.Equals(lease.author) || change.ReadKeyId == "" || change.AclHeadId == "" {
		return "", errors.Join(semanticanchor.ErrUncertain, err)
	}
	expectedParents, actualParents := slices.Clone(beforeHeads), slices.Clone(change.PreviousIds)
	slices.Sort(expectedParents)
	slices.Sort(actualParents)
	if !slices.Equal(expectedParents, actualParents) {
		return "", semanticanchor.ErrUncertain
	}
	// The ordinary native writer still performs its own signed-ACL checks.
	// This final acknowledgement check fails closed on a locally received ACL
	// update; it does not claim knowledge of unseen offline revocations.
	acl := tree.AclList()
	acl.RLock()
	allowed := acl.AclState().Permissions(lease.author).CanWrite()
	head := acl.Head()
	sameACL := head != nil && head.Id == change.AclHeadId
	acl.RUnlock()
	if !allowed {
		return "", errors.Join(semanticanchor.ErrUncertain, list.ErrInsufficientPermissions)
	}
	if !sameACL {
		return "", semanticanchor.ErrUncertain
	}
	if err = lease.validate(ctx); err != nil {
		return "", errors.Join(semanticanchor.ErrUncertain, err)
	}
	digest := sha256.Sum256(stored.RawChange)
	return hex.EncodeToString(digest[:]), nil
}
