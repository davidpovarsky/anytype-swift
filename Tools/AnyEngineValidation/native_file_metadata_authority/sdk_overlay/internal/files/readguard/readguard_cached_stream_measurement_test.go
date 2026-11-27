package readguard

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"runtime"
	"testing"
	"time"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/stretchr/testify/require"
)

const measuredCachedBytes int64 = 64 * 1024 * 1024
const measuredCachedBuffer = 64 * 1024
const measuredCachedSHA256 = "9b586ad8ac9a1e0a79d2cab4ff1f9d2671ed3d0434d8e068eebcb09330171ca9"

// measurementCachedReader is a deterministic in-memory cached source. It
// creates no account, file store or network connection. A 4KiB repeating
// pattern represents exactly64MiB without allocating a64MiB payload.
type measurementCachedReader struct {
	pattern        [4096]byte
	offset         int64
	delivered      int64
	reads          int
	largestRequest int
	closed         bool
}

func newMeasurementCachedReader() *measurementCachedReader {
	r := new(measurementCachedReader)
	for i := range r.pattern {
		r.pattern[i] = byte((i*37 + i/31) % 251)
	}
	return r
}

func (r *measurementCachedReader) Read(p []byte) (int, error) {
	if r.closed {
		return 0, io.ErrClosedPipe
	}
	if len(p) > r.largestRequest {
		r.largestRequest = len(p)
	}
	r.reads++
	if r.offset == measuredCachedBytes {
		return 0, io.EOF
	}
	n := min(len(p), int(measuredCachedBytes-r.offset))
	for done := 0; done < n; {
		start := int(r.offset % int64(len(r.pattern)))
		copied := copy(p[done:n], r.pattern[start:])
		done += copied
		r.offset += int64(copied)
	}
	r.delivered += int64(n)
	return n, nil
}

func (r *measurementCachedReader) Seek(offset int64, whence int) (int64, error) {
	if r.closed {
		return 0, io.ErrClosedPipe
	}
	position := offset
	switch whence {
	case io.SeekStart:
	case io.SeekCurrent:
		position += r.offset
	case io.SeekEnd:
		position += measuredCachedBytes
	default:
		return 0, errors.New("invalid synthetic seek origin")
	}
	if position < 0 || position > measuredCachedBytes {
		return 0, errors.New("invalid synthetic seek position")
	}
	r.offset = position
	return position, nil
}

func (r *measurementCachedReader) Size() int64  { return measuredCachedBytes }
func (r *measurementCachedReader) Close() error { r.closed = true; return nil }

type cachedStreamMeasurement struct {
	Path                       string  `json:"path"`
	Bytes                      int64   `json:"bytes"`
	SHA256                     string  `json:"sha256"`
	Reads                      int     `json:"reads"`
	LargestInnerRequest        int     `json:"largestInnerRequest"`
	CallerBufferBytes          int     `json:"callerBufferBytes"`
	ElapsedNanoseconds         int64   `json:"elapsedNanoseconds"`
	ProcessTotalAllocatedBytes uint64  `json:"processTotalAllocatedBytes"`
	ProcessAllocationCount     uint64  `json:"processAllocationCount"`
	MiBPerSecond               float64 `json:"mibPerSecond"`
}

// measureCachedPath reports an end-to-end read+SHA measurement. Allocations are
// the process TotalAlloc/Mallocs deltas, not a claim of isolated allocator
// attribution. Fixture creation, Open, buffers, GC and Close are outside the
// measured region. There are no warm-up reads or repeated benchmark rounds.
func measureCachedPath(t *testing.T, ctx context.Context, name string, reader Reader, inner *measurementCachedReader) cachedStreamMeasurement {
	t.Helper()
	buffer := make([]byte, measuredCachedBuffer)
	digest := sha256.New()
	runtime.GC()
	var before, after runtime.MemStats
	runtime.ReadMemStats(&before)
	started := time.Now()
	deadline := started.Add(10 * time.Second)
	var count int64
	for count < measuredCachedBytes {
		if ctx.Err() != nil || !time.Now().Before(deadline) {
			t.Fatalf("%s exceeded the fixed stream deadline", name)
		}
		n, err := reader.Read(buffer)
		if err != nil || n <= 0 || n > len(buffer) || count+int64(n) > measuredCachedBytes {
			t.Fatalf("%s invalid synthetic read: n=%d error=%v", name, n, err)
		}
		if written, writeErr := digest.Write(buffer[:n]); writeErr != nil || written != n {
			t.Fatalf("%s did not hash the entire returned byte range", name)
		}
		count += int64(n)
	}
	elapsed := time.Since(started)
	runtime.ReadMemStats(&after)
	require.Less(t, elapsed, 10*time.Second, "bounded measurement, not a throughput acceptance threshold")
	require.GreaterOrEqual(t, after.TotalAlloc, before.TotalAlloc)
	require.GreaterOrEqual(t, after.Mallocs, before.Mallocs)
	require.Equal(t, measuredCachedBytes, count)
	require.Equal(t, measuredCachedBytes, inner.delivered)
	require.Equal(t, int(measuredCachedBytes/int64(measuredCachedBuffer)), inner.reads)
	require.LessOrEqual(t, inner.largestRequest, measuredCachedBuffer)
	sum := hex.EncodeToString(digest.Sum(nil))
	require.Equal(t, measuredCachedSHA256, sum)
	return cachedStreamMeasurement{
		Path: name, Bytes: count, SHA256: sum, Reads: inner.reads,
		LargestInnerRequest: inner.largestRequest, CallerBufferBytes: len(buffer),
		ElapsedNanoseconds:         elapsed.Nanoseconds(),
		ProcessTotalAllocatedBytes: after.TotalAlloc - before.TotalAlloc,
		ProcessAllocationCount:     after.Mallocs - before.Mallocs,
		MiBPerSecond:               float64(count) / (1024 * 1024) / elapsed.Seconds(),
	}
}

// TestReadGuardFreshCachedStreamMeasurement64MiB measures only the added
// guard boundary over the same in-memory cached source. It is not a disk,
// network, Apple, full SDK Files.Open or throughput-nonregression proof.
func TestReadGuardFreshCachedStreamMeasurement64MiB(t *testing.T) {
	f := newSignedFixture(t, list.AclPermissionsReader)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	f.local.RLock()
	beforeHead := f.local.Head().Id
	f.local.RUnlock()
	unwrapped := newMeasurementCachedReader()
	t.Cleanup(func() { require.NoError(t, unwrapped.Close()) })
	baseline := measureCachedPath(t, ctx, "original-unwrapped-memory-reader", unwrapped, unwrapped)
	require.NoError(t, unwrapped.Close())

	inner := newMeasurementCachedReader()
	guarded, err := Open(ctx, f.load, func() (Reader, error) { return inner, nil })
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, guarded.Close()) })
	current := measureCachedPath(t, ctx, "current-signed-lifetime-guard", guarded, inner)
	require.NoError(t, guarded.Close())
	f.local.RLock()
	afterHead := f.local.Head().Id
	f.local.RUnlock()
	require.Equal(t, beforeHead, afterHead)
	require.Equal(t, baseline.Bytes, current.Bytes)
	require.Equal(t, baseline.SHA256, current.SHA256)

	record := struct {
		Protocol                      string                    `json:"protocol"`
		Measurements                  []cachedStreamMeasurement `json:"measurements"`
		Order                         []string                  `json:"order"`
		ElapsedRatio                  float64                   `json:"elapsedRatioGuardToOriginal"`
		AllocationDeltaBytes          int64                     `json:"allocationDeltaGuardMinusOriginalBytes"`
		NativeSDKOrStorageThroughput  bool                      `json:"nativeSDKOrStorageThroughput"`
		ThroughputAcceptanceThreshold bool                      `json:"throughputAcceptanceThreshold"`
		RetainedAccountInputs         int                       `json:"retainedAccountInputs"`
	}{
		Protocol:             "pinkha-fresh-cached-stream-measurement-v1",
		Measurements:         []cachedStreamMeasurement{baseline, current},
		Order:                []string{baseline.Path, current.Path},
		ElapsedRatio:         float64(current.ElapsedNanoseconds) / float64(baseline.ElapsedNanoseconds),
		AllocationDeltaBytes: int64(current.ProcessTotalAllocatedBytes) - int64(baseline.ProcessTotalAllocatedBytes),
	}
	raw, err := json.Marshal(record)
	require.NoError(t, err)
	t.Logf("READGUARD_CACHED_MEASUREMENT %s", raw)
}
