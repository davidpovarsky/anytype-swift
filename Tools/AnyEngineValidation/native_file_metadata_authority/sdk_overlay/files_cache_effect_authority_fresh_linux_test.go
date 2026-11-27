//go:build linux

package anysyncsdk

import (
	"context"
	"crypto/sha256"
	"errors"
	"io"
	"sync/atomic"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/ipfs/go-cid"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/any-sync-sdk/internal/files/fetch"
	"github.com/anyproto/any-sync-sdk/internal/files/status"
	filestore "github.com/anyproto/any-sync-sdk/internal/files/store"
	"github.com/anyproto/any-sync-sdk/internal/payloads"
	"github.com/anyproto/any-sync-sdk/internal/spaceimpl"
	"github.com/anyproto/any-sync-sdk/space"
)

// One new fixture exercises the real Files facade and persistent queue. It
// configures that queue before any new Space exists and never calls Queue.Run:
// this is a dispatch-authority proof, not a background job or cloud claim.
func TestFilesCacheEffectsFreshReaderAdmissionAndSignedRemoval(t *testing.T) {
	var queue *status.Queue
	var store *filestore.Store
	var workerCalls atomic.Int32
	var inlineID string
	f := newFreshFilesFixtureWithPreparation(t, true,
		func(f *freshFilesFixture, fetcher *fetch.Service, destination *filestore.Store) {
			var err error
			store = destination
			queue, err = status.NewQueue(f.ctx, f.metadataDBs[len(f.metadataDBs)-1],
				func(context.Context, status.Job) error {
					workerCalls.Add(1)
					return errors.New("fresh dispatch fixture never starts a worker")
				}, f.sdk.spaces.OnFileJobChange)
			require.NoError(t, err)
			t.Cleanup(queue.Close)
			f.sdk.spaces.SetFiles(nil, fetcher, destination, queue)
		},
		func(f *freshFilesFixture) {
			registrar, ok := f.space.(interface{ PayloadsInternal() *spaceimpl.PayloadsAPI })
			require.True(t, ok)
			inline := []byte("new inline cache authority fixture")
			var err error
			inlineID, _, err = registrar.PayloadsInternal().RegisterFile(f.ctx, f.space.SpaceIndexObjectId(), spaceimpl.RegisterFileOpts{
				Size: int64(len(inline)),
				Enc:  payloads.EncPayload{Name: "new-inline-cache.txt", Mime: "text/plain", Inline: inline},
			})
			require.NoError(t, err)
		})
	f.requireLocalPermission(t, list.AclPermissionsReader)
	files := f.space.Files()
	inlineInfo, err := files.Get(f.ctx, inlineID)
	require.NoError(t, err)
	require.True(t, inlineInfo.Inline)
	fullInfo, err := files.Get(f.ctx, f.fileID)
	require.NoError(t, err)
	require.True(t, fullInfo.Cached)
	require.False(t, fullInfo.Durable)
	root, err := cid.Decode(fullInfo.RootCid)
	require.NoError(t, err)
	carDigest := func() [32]byte {
		info, infoErr := store.Info(f.ctx, f.space.Id(), root)
		require.NoError(t, infoErr)
		require.Equal(t, filestore.StateComplete, info.State)
		handle, openErr := store.Open(f.ctx, f.space.Id(), root)
		require.NoError(t, openErr)
		digest := sha256.New()
		n, readErr := io.CopyBuffer(digest, io.NewSectionReader(handle, 0, info.Size), make([]byte, 64*1024))
		closeErr := handle.Close()
		require.NoError(t, readErr)
		require.NoError(t, closeErr)
		require.Equal(t, info.Size, n)
		var sum [32]byte
		copy(sum[:], digest.Sum(nil))
		return sum
	}
	beforeCAR := carDigest()

	// Readers can manage their own local cache. Inline no-ops retain the same
	// authority requirement, and unsigned full content is never offloaded.
	require.NoError(t, files.Pin(f.ctx, inlineID))
	require.NoError(t, files.Retry(f.ctx, inlineID))
	require.NoError(t, files.Offload(f.ctx, inlineID))
	beforeJobs, err := queue.ListSpace(f.ctx, f.space.Id())
	require.NoError(t, err)
	require.Empty(t, beforeJobs)
	require.NoError(t, files.Pin(f.ctx, f.fileID))
	require.NoError(t, files.Retry(f.ctx, f.fileID))
	require.ErrorIs(t, files.Offload(f.ctx, f.fileID), space.ErrFileNotBackedUp)
	admittedJobs, err := queue.ListSpace(f.ctx, f.space.Id())
	require.NoError(t, err)
	require.Len(t, admittedJobs, 2)
	kinds := make([]string, 0, len(admittedJobs))
	for _, job := range admittedJobs {
		require.Equal(t, f.space.Id(), job.SpaceId)
		require.Equal(t, f.fileID, job.FileId)
		kinds = append(kinds, job.Kind)
	}
	require.ElementsMatch(t, []string{status.KindPin, status.KindDurable}, kinds)

	f.revoke(t)
	for _, operation := range []struct {
		name string
		call func(context.Context, string) error
	}{{"pin", files.Pin}, {"retry", files.Retry}, {"offload", files.Offload}} {
		for _, id := range []string{f.fileID, inlineID, "new-fixture-nonexistent-file"} {
			require.ErrorIs(t, operation.call(f.ctx, id), list.ErrInsufficientPermissions,
				"%s refuses removed-member full/inline/missing routes before any effect", operation.name)
		}
	}
	afterJobs, err := queue.ListSpace(f.ctx, f.space.Id())
	require.NoError(t, err)
	require.ElementsMatch(t, admittedJobs, afterJobs,
		"new refused dispatches neither change nor cancel previously admitted jobs")
	require.Equal(t, beforeCAR, carDigest(), "unsigned original fixture bytes remain intact")
	require.Zero(t, workerCalls.Load())
	require.Zero(t, f.baseURLCalls.Load())
}
