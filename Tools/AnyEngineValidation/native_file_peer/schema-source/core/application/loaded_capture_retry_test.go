//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance

package application

import (
	"context"
	"errors"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
)

const loadedNativeCaptureAttemptLimit = 3

type loadedNativeCaptureAttempt struct {
	Attempt int
	Outcome string
	Error   string
}

// This is fixture scheduling only, not source admission. Each call starts a
// complete new authorized capture. Rejected material is never returned or reused.
func loadedCaptureFreshAttempts(ctx context.Context,
	capture func() (*LoadedAccountSpaceWitness, error),
	observe func(loadedNativeCaptureAttempt),
) (*LoadedAccountSpaceWitness, error) {
	if ctx == nil || capture == nil || observe == nil {
		return nil, ErrLoadedAccountSpaceWitness
	}
	var last error
	for attempt := 1; attempt <= loadedNativeCaptureAttemptLimit; attempt++ {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		value, err := capture()
		note := loadedNativeCaptureAttempt{Attempt: attempt, Outcome: "capture-returned"}
		if err != nil {
			note.Outcome, note.Error = "refused", err.Error()
			if _, exact := err.(loadedAccountSpaceWitnessCheckpointChangedError); exact {
				note.Outcome = "checkpoint-changed"
			}
		}
		observe(note)
		if contextErr := ctx.Err(); contextErr != nil {
			return nil, contextErr
		}
		if err == nil {
			if value == nil {
				return nil, ErrLoadedAccountSpaceWitness
			}
			return value, nil
		}
		// The production entry point emits exactly this typed refusal only after
		// complete inventory parsing and the final account/session checks. Do not
		// retry a wrapped/composite error or any rejected partial return value.
		if _, exact := err.(loadedAccountSpaceWitnessCheckpointChangedError); !exact || value != nil {
			return nil, err
		}
		last = err
	}
	return nil, last
}

// Pure fixture-controller controls. The inert return value below is only an
// identity token for scheduling; it is never a native witness or acceptance proof.
func TestLoadedAccountCaptureRetryBoundary(t *testing.T) {
	changed := loadedAccountSpaceWitnessCheckpointChangedError{}
	observe := func(notes *[]loadedNativeCaptureAttempt) func(loadedNativeCaptureAttempt) {
		return func(note loadedNativeCaptureAttempt) { *notes = append(*notes, note) }
	}
	t.Run("typed-change-starts-fresh-attempt", func(t *testing.T) {
		var notes []loadedNativeCaptureAttempt
		calls := 0
		fresh := new(LoadedAccountSpaceWitness)
		actual, err := loadedCaptureFreshAttempts(context.Background(), func() (*LoadedAccountSpaceWitness, error) {
			calls++
			if calls == 1 {
				return nil, changed
			}
			return fresh, nil
		}, observe(&notes))
		require.NoError(t, err)
		require.Same(t, fresh, actual)
		require.Equal(t, 2, calls)
		require.Equal(t, []loadedNativeCaptureAttempt{
			{Attempt: 1, Outcome: "checkpoint-changed", Error: changed.Error()},
			{Attempt: 2, Outcome: "capture-returned"},
		}, notes)
		require.ErrorIs(t, changed, ErrLoadedAccountSpaceWitnessCheckpointChanged)
		require.ErrorIs(t, changed, ErrLoadedAccountSpaceWitness)
		require.ErrorIs(t, changed, localstorewitness.ErrNativeTreeInventory)
	})
	t.Run("authority-census-path-payload-errors-stop", func(t *testing.T) {
		for _, failure := range []error{localstorewitness.ErrOwnership,
			localstorewitness.ErrNativeTreeInventory, os.ErrPermission,
			errors.New("native schema refused"), errors.New("native payload refused")} {
			calls := 0
			var notes []loadedNativeCaptureAttempt
			actual, err := loadedCaptureFreshAttempts(context.Background(), func() (*LoadedAccountSpaceWitness, error) {
				calls++
				return nil, failure
			}, observe(&notes))
			require.Nil(t, actual)
			require.ErrorIs(t, err, failure)
			require.Equal(t, 1, calls)
			require.Len(t, notes, 1)
			require.Equal(t, "refused", notes[0].Outcome)
		}
	})
	t.Run("matching-error-text-does-not-retry", func(t *testing.T) {
		calls := 0
		failure := errors.New(changed.Error())
		actual, err := loadedCaptureFreshAttempts(context.Background(), func() (*LoadedAccountSpaceWitness, error) {
			calls++
			return nil, failure
		}, func(loadedNativeCaptureAttempt) {})
		require.Nil(t, actual)
		require.ErrorIs(t, err, failure)
		require.Equal(t, 1, calls)
	})
	t.Run("wrapped-or-composite-marker-does-not-retry", func(t *testing.T) {
		for _, failure := range []error{fmt.Errorf("outer refusal: %w", changed),
			errors.Join(changed, localstorewitness.ErrOwnership)} {
			calls := 0
			actual, err := loadedCaptureFreshAttempts(context.Background(), func() (*LoadedAccountSpaceWitness, error) {
				calls++
				return nil, failure
			}, func(loadedNativeCaptureAttempt) {})
			require.Nil(t, actual)
			require.ErrorIs(t, err, failure)
			require.Equal(t, 1, calls)
		}
	})
	t.Run("rejected-partial-value-does-not-retry", func(t *testing.T) {
		calls := 0
		actual, err := loadedCaptureFreshAttempts(context.Background(), func() (*LoadedAccountSpaceWitness, error) {
			calls++
			return new(LoadedAccountSpaceWitness), changed
		}, func(loadedNativeCaptureAttempt) {})
		require.Nil(t, actual)
		require.ErrorIs(t, err, ErrLoadedAccountSpaceWitnessCheckpointChanged)
		require.Equal(t, 1, calls)
	})
	t.Run("attempt-cap-remains-terminal", func(t *testing.T) {
		calls := 0
		var notes []loadedNativeCaptureAttempt
		actual, err := loadedCaptureFreshAttempts(context.Background(), func() (*LoadedAccountSpaceWitness, error) {
			calls++
			return nil, changed
		}, observe(&notes))
		require.Nil(t, actual)
		require.ErrorIs(t, err, ErrLoadedAccountSpaceWitnessCheckpointChanged)
		require.Equal(t, loadedNativeCaptureAttemptLimit, calls)
		require.Len(t, notes, loadedNativeCaptureAttemptLimit)
	})
	t.Run("expired-original-deadline-starts-no-attempt", func(t *testing.T) {
		ctx, cancel := context.WithDeadline(context.Background(), time.Unix(1, 0))
		defer cancel()
		calls := 0
		actual, err := loadedCaptureFreshAttempts(ctx, func() (*LoadedAccountSpaceWitness, error) {
			calls++
			return new(LoadedAccountSpaceWitness), nil
		}, func(loadedNativeCaptureAttempt) {})
		require.Nil(t, actual)
		require.ErrorIs(t, err, context.DeadlineExceeded)
		require.Zero(t, calls)
	})
	t.Run("cancellation-prevents-next-attempt", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()
		calls := 0
		var notes []loadedNativeCaptureAttempt
		actual, err := loadedCaptureFreshAttempts(ctx, func() (*LoadedAccountSpaceWitness, error) {
			calls++
			cancel()
			return nil, changed
		}, observe(&notes))
		require.Nil(t, actual)
		require.ErrorIs(t, err, context.Canceled)
		require.Equal(t, 1, calls)
		require.Len(t, notes, 1)
	})
}
