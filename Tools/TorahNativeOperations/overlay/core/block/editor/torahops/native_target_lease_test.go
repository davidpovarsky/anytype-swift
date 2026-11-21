package torahops

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/stretchr/testify/require"
)

func nativeMutexAvailable(mu *sync.Mutex) bool {
	if !mu.TryLock() {
		return false
	}
	mu.Unlock()
	return true
}

func TestNativeTargetLeaseCoversDurableCommitAndReleasesBeforeHeadUpdate(t *testing.T) {
	f, op := nativeFixtureWithPopulatedProjection(t)
	var settings, target sync.Mutex
	acquired, released := 0, 0
	leaser := func(ctx context.Context, current Target) (func(), error) {
		if err := f.validateTarget(ctx, current); err != nil {
			return nil, err
		}
		// Acquiring settings/target from beneath the private tree would reverse
		// the native deletion order. Make that inversion observable here.
		privateAvailable := f.tree.TryLock()
		if privateAvailable {
			f.tree.Unlock()
		}
		require.True(t, privateAvailable)
		settings.Lock()
		target.Lock()
		acquired++
		return func() { released++; target.Unlock(); settings.Unlock() }, nil
	}
	host, err := OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), f.tree, f.keys.SignKey, leaser)
	require.NoError(t, err)
	storage, err := boundNativeCommitStorage(f.tree)
	require.NoError(t, err)
	originalStorage, originalFactory := storage.Storage, f.client.RequestFactory
	t.Cleanup(func() { storage.Storage, f.client.RequestFactory = originalStorage, originalFactory })
	checkHeld := func() {
		require.False(t, nativeMutexAvailable(&settings))
		require.False(t, nativeMutexAvailable(&target))
		require.Zero(t, released)
	}
	storage.Storage = &nativeCommitStorageObserver{Storage: originalStorage, before: checkHeld, after: checkHeld}
	postCommit := errors.New("head update failed after target lease released")
	f.client.RequestFactory = &nativeFailingHeadUpdate{RequestFactory: originalFactory, failure: postCommit, observe: func() {
		require.Equal(t, 1, acquired)
		require.Equal(t, 1, released)
		require.True(t, nativeMutexAvailable(&settings))
		require.True(t, nativeMutexAvailable(&target))
		require.True(t, nativeACLWriteLockAvailable(t, f.acl))
	}}
	op.OperationID = fmt.Sprintf("%032x", 2)
	result, err := host.Append(context.Background(), op)
	require.ErrorIs(t, err, postCommit)
	require.Equal(t, Created, result.Disposition)
	require.NotEmpty(t, result.ChangeID)
	require.Equal(t, 1, released, "outer defers must not release the same lease twice")
	stored, err := f.tree.Storage().Has(context.Background(), result.ChangeID)
	require.NoError(t, err)
	require.True(t, stored)
	storage.Storage, f.client.RequestFactory = originalStorage, originalFactory
	retry, err := host.Append(context.Background(), op)
	require.NoError(t, err)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.Equal(t, 2, acquired)
	require.Equal(t, 2, released)
	op.Payload = []byte("collision must preserve the signed operation")
	collision, err := host.Append(context.Background(), op)
	require.NoError(t, err)
	require.Equal(t, CollisionDifferentPayload, collision.Disposition)
	require.Equal(t, 3, acquired)
	require.Equal(t, 3, released)
}

func TestNativeTargetLeaseReleasesOnCancelledPreparedAppend(t *testing.T) {
	f, op := nativeFixtureWithPopulatedProjection(t)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var settings, target sync.Mutex
	released := 0
	leaser := func(context.Context, Target) (func(), error) {
		settings.Lock()
		target.Lock()
		return func() { released++; target.Unlock(); settings.Unlock() }, nil
	}
	var prepared string
	wrapped := &nativePreparedBoundaryTree{SyncTree: f.tree, afterPrepared: func(change objecttree.StorageChange) error {
		prepared = change.Id
		cancel()
		return nil
	}}
	host, err := OpenNativeHost(context.Background(), f.projectionDB, f.space.Id(), wrapped, f.keys.SignKey, leaser)
	require.NoError(t, err)
	op.OperationID = fmt.Sprintf("%032x", 2)
	result, err := host.Append(ctx, op)
	require.ErrorIs(t, err, context.Canceled)
	require.Equal(t, NativeAppendResult{}, result)
	require.NotEmpty(t, prepared)
	stored, err := f.tree.Storage().Has(context.Background(), prepared)
	require.NoError(t, err)
	require.False(t, stored)
	require.Equal(t, 1, released)
	require.True(t, nativeMutexAvailable(&settings))
	require.True(t, nativeMutexAvailable(&target))
}
