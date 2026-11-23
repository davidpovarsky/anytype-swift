package localstorewitness

import (
	"context"

	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage"
)

// NativeOwnedStoreAuthority proves only the current native service/handle
// lifetime for this local read. It is not account, session, ACL, semantic
// completeness, file-payload completeness, or destination-write authorization.
const NativeOwnedStoreAuthority = "heart-owned-local-store-v1"

// CaptureNativeOwned is the single reviewed production consumer of the native
// lease in this slice. That consumer restriction is source admission, not a Go
// type-system guarantee. No caller-supplied owner, storage, or callback is used.
func CaptureNativeOwned(ctx context.Context, capability *anystorage.LocalSnapshotCapability, limits Limits) (*Witness, error) {
	if ctx == nil || capability == nil || !limits.valid() {
		return nil, ErrOwnership
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	lease, err := capability.AcquireWitnessLease(ctx)
	if err != nil {
		return nil, err
	}
	return captureLease(lease.Context(), &nativeSnapshotLease{lease: lease}, limits, NativeOwnedStoreAuthority)
}

type nativeSnapshotLease struct {
	lease *anystorage.LocalSnapshotLease
}

func (*nativeSnapshotLease) localStoreWitnessLease() {}

func (l *nativeSnapshotLease) Binding() Binding {
	b := l.lease.Binding()
	return Binding{Authority: NativeOwnedStoreAuthority, OwnerNonce: b.OwnerNonce, Generation: b.Generation, SpaceID: b.SpaceID}
}

func (l *nativeSnapshotLease) Storage() spacestorage.SpaceStorage {
	return l.lease.Storage()
}

func (l *nativeSnapshotLease) CheckCurrent(ctx context.Context) error {
	return l.lease.CheckCurrent(ctx)
}

func (l *nativeSnapshotLease) Close() error {
	return l.lease.Close()
}
