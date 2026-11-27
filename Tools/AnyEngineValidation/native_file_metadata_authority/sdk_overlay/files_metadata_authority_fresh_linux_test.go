//go:build linux

package anysyncsdk

import (
	"bytes"
	"sync"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/any-sync-sdk/internal/files/status"
	"github.com/anyproto/any-sync-sdk/internal/payloads"
	"github.com/anyproto/any-sync-sdk/space"
)

// This one new integration method reuses only the qualified fresh-fixture
// constructor source. It creates a NEW isolated SDK/account/Space/file and
// applies its own signed removal; neither older Files.Open method runs and no
// original account, saved key, database or signed private-store record is read.
func TestFilesMetadataFreshGetListStatusAndStatsStopAtSignedRemoval(t *testing.T) {
	f := newFreshFilesFixture(t, true)
	files := f.space.Files()
	before, err := files.Get(f.ctx, f.fileID)
	require.NoError(t, err)
	require.Equal(t, f.fileID, before.FileId)
	require.Equal(t, f.space.SpaceIndexObjectId(), before.ObjectId)
	require.Equal(t, "new-synthetic-reader.bin", before.Name)
	require.Equal(t, "application/octet-stream", before.Mime)
	require.EqualValues(t, len(f.plain), before.Size)
	require.True(t, before.Cached)
	require.False(t, before.Durable)
	objectFiles, err := files.List(f.ctx, space.FileListOpts{ObjectId: before.ObjectId})
	require.NoError(t, err)
	require.Equal(t, []space.FileInfo{before}, objectFiles)
	allFiles, err := files.List(f.ctx, space.FileListOpts{})
	require.NoError(t, err)
	require.Equal(t, []space.FileInfo{before}, allFiles)
	beforeStatus, err := files.Status(f.ctx, f.fileID)
	require.NoError(t, err)
	require.Equal(t, space.FileStatus{FileId: f.fileID, ObjectId: before.ObjectId,
		State: space.FileStateInFlight, Cached: true}, beforeStatus)
	beforeStats, err := files.Stats(f.ctx)
	require.NoError(t, err)
	require.Equal(t, space.FileStats{Total: 1, InFlight: 1}, beforeStats)

	var eventsMu sync.Mutex
	var events []space.FileStatus
	unsub := files.SubscribeStatus(func(st space.FileStatus) {
		eventsMu.Lock()
		events = append(events, st)
		eventsMu.Unlock()
	})
	t.Cleanup(unsub)
	job := status.Job{SpaceId: f.space.Id(), FileId: f.fileID, Kind: status.KindDurable}
	// Use the actual production queue-to-status hook on this new fixture. Its
	// original fanout is synchronous and remains unchanged by the guard.
	f.sdk.spaces.OnFileJobChange(job, false)
	eventsMu.Lock()
	beforeEvents := append([]space.FileStatus(nil), events...)
	eventsMu.Unlock()
	require.Equal(t, []space.FileStatus{beforeStatus}, beforeEvents)

	// The separate, explicitly node-readable raw query remains sealed. It is
	// not the member-only FileInfo API and is not claimed to erase broker data.
	rawQuery, err := files.Query(before.ObjectId)
	require.NoError(t, err)
	rawBefore, err := rawQuery.All(f.ctx)
	require.NoError(t, err)
	require.Len(t, rawBefore, 1)
	require.Equal(t, before.RootCid, rawBefore[0].GetString(payloads.FieldRootCid))
	ciphertext := bytes.Clone(rawBefore[0].GetBytes(payloads.FieldEnc, payloads.EncKeyCiphertext))
	require.NotEmpty(t, ciphertext)
	for _, secret := range []string{"name", "mime", "key", "sha256", "inline", "variant", "variantOf"} {
		require.Nil(t, rawBefore[0].Get(secret), "member-only metadata stays sealed in the raw query")
	}

	f.revoke(t)
	got, err := files.Get(f.ctx, f.fileID)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, got)
	objectFiles, err = files.List(f.ctx, space.FileListOpts{ObjectId: before.ObjectId})
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Nil(t, objectFiles)
	allFiles, err = files.List(f.ctx, space.FileListOpts{})
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Nil(t, allFiles)
	gotStatus, err := files.Status(f.ctx, f.fileID)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, gotStatus)
	gotStats, err := files.Stats(f.ctx)
	require.ErrorIs(t, err, list.ErrInsufficientPermissions)
	require.Zero(t, gotStats)

	f.sdk.spaces.OnFileJobChange(job, false)
	lateUnsub := files.SubscribeStatus(func(st space.FileStatus) {
		eventsMu.Lock()
		events = append(events, st)
		eventsMu.Unlock()
	})
	t.Cleanup(lateUnsub)
	f.sdk.spaces.OnFileJobChange(job, false)
	eventsMu.Lock()
	afterEvents := append([]space.FileStatus(nil), events...)
	eventsMu.Unlock()
	require.Equal(t, beforeEvents, afterEvents, "existing and late subscriptions release no removed-member diagnostics")

	rawAfter, err := rawQuery.All(f.ctx)
	require.NoError(t, err)
	require.Len(t, rawAfter, 1)
	require.Equal(t, before.RootCid, rawAfter[0].GetString(payloads.FieldRootCid))
	require.Equal(t, ciphertext, rawAfter[0].GetBytes(payloads.FieldEnc, payloads.EncKeyCiphertext))
	for _, secret := range []string{"name", "mime", "key", "sha256", "inline", "variant", "variantOf"} {
		require.Nil(t, rawAfter[0].Get(secret))
	}
	require.Zero(t, f.baseURLCalls.Load())
}
