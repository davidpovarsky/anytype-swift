package core

import (
	"context"
	"errors"
	"sync"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/util/crypto"

	"github.com/anyproto/anytype-heart/core/block/object/idresolver"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/addr"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// These exact descriptions accompany the existing BAD_INPUT wire code. They
// identify native current authority, not a client-side access flag. Keep them
// distinct from an ordinary unavailable provider/query error.
var (
	errPinkhaCurrentReadDenied      = errors.New("PINKHA_CURRENT_SPACE_READ_DENIED_V1")
	errPinkhaCurrentReadInvalidated = errors.New("PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1")
)

type pinkhaCurrentReadScope struct {
	middleware  *Middleware
	application *app.App
	spaces      space.Service
	space       clientspace.Space
	spaceID     string
	acl         list.AclList
	identity    crypto.PubKey
	head        string
	marketplace bool
}

func (mw *Middleware) pinkhaBeginCurrentSpaceRead(ctx context.Context, application *app.App, spaceID, objectID string) (*pinkhaCurrentReadScope, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if application == nil {
		return nil, errPinkhaCurrentReadInvalidated
	}
	spaces, err := app.GetComponent[space.Service](application)
	if err != nil {
		return nil, errPinkhaCurrentReadInvalidated
	}
	// ObjectShow historically permits an omitted Space ID. Resolve it with the
	// existing native resolver; never infer authority from an arbitrary ID.
	if spaceID == "" {
		if objectID == "" {
			return nil, errPinkhaCurrentReadInvalidated
		}
		resolver, resolveErr := app.GetComponent[idresolver.Resolver](application)
		if resolveErr != nil {
			return nil, errPinkhaCurrentReadInvalidated
		}
		spaceID, err = resolver.ResolveSpaceID(objectID)
		if err != nil || spaceID == "" {
			return nil, errPinkhaCurrentReadInvalidated
		}
	}
	spc, err := spaces.Get(ctx, spaceID)
	if err != nil || spc == nil || spc.Id() != spaceID || spc.CommonSpace() == nil {
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		return nil, errPinkhaCurrentReadInvalidated
	}
	scope := &pinkhaCurrentReadScope{middleware: mw, application: application, spaces: spaces, space: spc, spaceID: spaceID}
	// The registered native marketplace is an explicitly public, immutable
	// virtual Space. This concrete native type/ID exception is not a generic
	// nil-ACL bypass for a private or partially loaded Space.
	if _, virtual := spc.(*clientspace.VirtualSpace); virtual && spaceID == addr.AnytypeMarketplaceWorkspace && spc.CommonSpace().Acl() == nil {
		scope.marketplace = true
		return scope, nil
	}
	scope.acl, scope.identity = spc.CommonSpace().Acl(), spc.GetAclIdentity()
	if scope.acl == nil || scope.identity == nil {
		return nil, errPinkhaCurrentReadInvalidated
	}
	scope.acl.RLock()
	defer scope.acl.RUnlock()
	if scope.acl.AclState() == nil || scope.acl.Head() == nil || scope.acl.Head().Id == "" {
		return nil, errPinkhaCurrentReadInvalidated
	}
	if !pinkhaCurrentReadPermission(scope.acl.AclState().Permissions(scope.identity)) {
		return nil, errPinkhaCurrentReadDenied
	}
	scope.head = scope.acl.Head().Id
	return scope, nil
}

// The predicate is identical to the retained current-read rule used by native
// Torah operations. Historical membership/decryption keys never grant access.
func pinkhaCurrentReadPermission(permission list.AclPermissions) bool {
	switch permission {
	case list.AclPermissionsReader, list.AclPermissionsGuest, list.AclPermissionsWriter,
		list.AclPermissionsAdmin, list.AclPermissionsOwner:
		return true
	default:
		return false
	}
}

// acquirePublication runs only after the query/ShowBlock has finished and its
// result is ready. No object/index/Space wait occurs under the ACL lock. Thus
// existing object->ACL write ordering is preserved. The unchanged signed head
// bridges the unlocked read phase; any intervening ACL change invalidates it.
// The returned lease holds app-lifecycle->Space-publication->ACL locks until the
// response is constructed. Callers must not invoke native services while held.
func (s *pinkhaCurrentReadScope) acquirePublication(ctx context.Context) (func(), error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	current, err := s.spaces.Get(ctx, s.spaceID)
	if err != nil || current == nil || current != s.space || current.Id() != s.spaceID || current.CommonSpace() == nil {
		return nil, errPinkhaCurrentReadInvalidated
	}
	releaseApp, currentApp := s.middleware.applicationService.AcquireCurrentAppRead(s.application)
	if !currentApp {
		return nil, errPinkhaCurrentReadInvalidated
	}
	publicationOwner, nativeOwner := current.(interface {
		AcquireCurrentReadPublication() (func(), bool)
	})
	if !nativeOwner {
		releaseApp()
		return nil, errPinkhaCurrentReadInvalidated
	}
	releaseSpace, currentSpace := publicationOwner.AcquireCurrentReadPublication()
	if !currentSpace {
		releaseApp()
		return nil, errPinkhaCurrentReadInvalidated
	}
	releaseOwners := func() { releaseSpace(); releaseApp() }
	if err := ctx.Err(); err != nil {
		releaseOwners()
		return nil, err
	}
	if s.marketplace {
		if _, virtual := current.(*clientspace.VirtualSpace); !virtual || current.CommonSpace().Acl() != nil || s.spaceID != addr.AnytypeMarketplaceWorkspace {
			releaseOwners()
			return nil, errPinkhaCurrentReadInvalidated
		}
		return releaseOwners, nil
	}
	if current.CommonSpace().Acl() != s.acl || current.GetAclIdentity() == nil || !current.GetAclIdentity().Equals(s.identity) {
		releaseOwners()
		return nil, errPinkhaCurrentReadInvalidated
	}
	s.acl.RLock()
	release := func() { s.acl.RUnlock(); releaseOwners() }
	if s.acl.AclState() == nil || s.acl.Head() == nil {
		release()
		return nil, errPinkhaCurrentReadInvalidated
	}
	if !pinkhaCurrentReadPermission(s.acl.AclState().Permissions(s.identity)) {
		release()
		return nil, errPinkhaCurrentReadDenied
	}
	if s.acl.Head().Id != s.head {
		release()
		return nil, errPinkhaCurrentReadInvalidated
	}
	if err := ctx.Err(); err != nil {
		release()
		return nil, err
	}
	var once sync.Once
	return func() { once.Do(release) }, nil
}
