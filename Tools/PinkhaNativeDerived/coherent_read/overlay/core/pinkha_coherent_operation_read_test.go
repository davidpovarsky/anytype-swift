package core

import (
	"bytes"
	"context"
	"errors"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/stretchr/testify/require"
)

// These are finalization component checks. The publisher double supplies an
// outcome; it does not prove native ACL or Space retirement. Those are bound to
// the unchanged native publication-lock proof and the separate real account run.
type coherentReadPublication struct {
	acquire func(context.Context) (func(), error)
	calls   int
}

func (p *coherentReadPublication) acquirePublication(ctx context.Context) (func(), error) {
	p.calls++
	return p.acquire(ctx)
}

func coherentPreparedRead(t *testing.T, publication pinkhaOperationReadPublication) pinkhaPreparedOperationRead {
	t.Helper()
	return pinkhaPreparedOperationRead{value: authorizedRPCSnapshot(t), readOwner: &pinkhaTorahScope{}, publication: publication}
}

func TestCoherentAuthorizedReadFinalizationReleasesNoRetiredPayload(t *testing.T) {
	for _, entry := range []string{"native", "wire"} {
		for _, outcome := range []string{"denied", "retired", "cancelled-after-wait"} {
			t.Run(entry+"-"+outcome, func(t *testing.T) {
				ctx, cancel := context.WithCancel(context.Background())
				defer cancel()
				released := 0
				publication := &coherentReadPublication{acquire: func(context.Context) (func(), error) {
					switch outcome {
					case "denied":
						return nil, errPinkhaCurrentReadDenied
					case "retired":
						return nil, errPinkhaCurrentReadInvalidated
					default:
						cancel()
						return func() { released++ }, nil
					}
				}}
				prepared := coherentPreparedRead(t, publication)
				code, expected := int32(4), error(list.ErrInsufficientPermissions)
				if outcome == "retired" {
					code, expected = 9, torahops.ErrOperationSnapshotChanged
				} else if outcome == "cancelled-after-wait" {
					code, expected = 12, context.Canceled
				}
				if entry == "native" {
					value, err := prepared.snapshot(ctx)
					require.ErrorIs(t, err, expected)
					require.Equal(t, torahops.AuthorizedOperationSnapshot{}, value)
				} else {
					response := prepared.wire(ctx)
					require.Equal(t, code, int32(response.Error.Code))
					require.Nil(t, response.Snapshot)
					raw, err := response.Marshal()
					require.NoError(t, err)
					require.False(t, bytes.Contains(raw, prepared.value.Variants[0].CanonicalBytes))
					require.False(t, bytes.Contains(raw, []byte(prepared.value.Variants[0].ClaimID)))
				}
				require.Equal(t, 1, publication.calls)
				if outcome == "cancelled-after-wait" {
					require.Equal(t, 1, released)
				} else {
					require.Zero(t, released)
				}
			})
		}
	}
}

func TestCoherentAuthorizedReadBuildsWireBeforePublication(t *testing.T) {
	publication := &coherentReadPublication{}
	prepared := coherentPreparedRead(t, publication)
	expected := append([]byte{}, prepared.value.Variants[0].CanonicalBytes...)
	released := 0
	publication.acquire = func(context.Context) (func(), error) {
		// The response must already own its copy before the publication lock is
		// requested. This changes the prepared source only, never wire output.
		prepared.value.Variants[0].CanonicalBytes[0] ^= 0xff
		return func() { released++ }, nil
	}
	response := prepared.wire(context.Background())
	require.Equal(t, pb.PinkhaTorahAuthorizedOperationReadResponseError_NULL, response.Error.Code)
	require.Equal(t, expected, response.Snapshot.Variants[0].CanonicalBytes)
	require.NotEqual(t, expected, prepared.value.Variants[0].CanonicalBytes)
	require.Equal(t, 1, publication.calls)
	require.Equal(t, 1, released)
}

func TestCoherentAuthorizedReadRejectsActiveReadLeaseBeforePublication(t *testing.T) {
	appReleased, finalReleased := 0, 0
	owner := &pinkhaTorahScope{releaseApp: func() { appReleased++ }}
	owner.leaseActive.Store(true)
	publication := &coherentReadPublication{acquire: func(context.Context) (func(), error) {
		require.False(t, owner.leaseActive.Load(), "never recursively acquire App while the old lease is active")
		require.Equal(t, 1, appReleased)
		return func() { finalReleased++ }, nil
	}}
	prepared := coherentPreparedRead(t, publication)
	prepared.readOwner = owner
	denied := prepared.wire(context.Background())
	require.Equal(t, int32(9), int32(denied.Error.Code))
	require.Nil(t, denied.Snapshot)
	require.Zero(t, publication.calls)
	owner.close()
	response := prepared.wire(context.Background())
	require.Equal(t, int32(0), int32(response.Error.Code))
	require.NotNil(t, response.Snapshot)
	require.Equal(t, 1, publication.calls)
	require.Equal(t, 1, finalReleased)
}

func TestCoherentAuthorizedReadMissingOwnershipFailsClosed(t *testing.T) {
	for _, scenario := range []string{"missing-read-owner", "missing-publication", "missing-release"} {
		t.Run(scenario, func(t *testing.T) {
			publication := &coherentReadPublication{acquire: func(context.Context) (func(), error) { return nil, nil }}
			prepared := coherentPreparedRead(t, publication)
			if scenario == "missing-read-owner" {
				prepared.readOwner = nil
			} else if scenario == "missing-publication" {
				prepared.publication = nil
			}
			response := prepared.wire(context.Background())
			require.Equal(t, int32(9), int32(response.Error.Code))
			require.Nil(t, response.Snapshot)
			if scenario == "missing-release" {
				require.Equal(t, 1, publication.calls)
			} else {
				require.Zero(t, publication.calls)
			}
		})
	}
}

func TestCoherentAuthorizedReadNativeSuccessReleasesPublication(t *testing.T) {
	released := 0
	publication := &coherentReadPublication{acquire: func(context.Context) (func(), error) {
		return func() { released++ }, nil
	}}
	prepared := coherentPreparedRead(t, publication)
	value, err := prepared.snapshot(context.Background())
	require.NoError(t, err)
	require.Equal(t, prepared.value, value)
	require.Equal(t, 1, publication.calls)
	require.Equal(t, 1, released)
	transient := errors.New("PINKHA_CURRENT_SPACE_READ_DENIED_V1")
	require.Same(t, transient, pinkhaOperationPublicationError(transient), "description alone must not become permission evidence")
	require.False(t, errors.Is(pinkhaOperationPublicationError(transient), list.ErrInsufficientPermissions))
}
