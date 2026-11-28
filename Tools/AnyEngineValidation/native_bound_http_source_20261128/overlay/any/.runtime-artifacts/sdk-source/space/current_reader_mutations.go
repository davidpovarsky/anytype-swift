package space

import "context"

// CurrentReaderAuthority is an optional loaded signed-ACL and account/Space
// lifetime admission. Cached role/member tables are not authority. A successful
// check is a point-in-time observation, not a lease for an unrelated later call.
type CurrentReaderAuthority interface {
	CheckCurrentReader(ctx context.Context) error
}

// CurrentReaderSettings is the explicitly bound account-private settings route.
// It accepts a currently readable live Space, rejects deleted/unknown rows and
// writes the original tech-space settings CRDT. It does not grant shared WRITE.
type CurrentReaderSettings interface {
	SetSettingsCurrentReader(ctx context.Context, spaceID string, set map[string]any, unset []string) error
}

// CurrentReaderLocalProperties is the explicitly bound device-local route.
// The only supported owner is the compiled immutable native "any" schema.
// Every key must be declared LOCAL; the target's existence and deletion state
// are checked under its original write lock. Readers may update their own local
// values. Mutable type/collection owners are explicitly unsupported: this route
// makes no cross-definition atomicity claim. Shared/account properties and
// definitions cannot use this route.
type CurrentReaderLocalProperties interface {
	SetLocalCurrentReader(ctx context.Context, objectID, ownerID string, patch map[string]any) (ModifyResult, error)
}
