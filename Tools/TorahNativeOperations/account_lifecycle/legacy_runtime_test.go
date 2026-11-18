package service

import (
	"context"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/space/spacecore/typeprovider"
	"github.com/stretchr/testify/require"
)

// This file deliberately imports no T2 package. The legacy binary is exactly
// d984+r14 and cannot recognize, decode, migrate or rewrite the private type.
func t2ExerciseRuntime(t *testing.T, state *t2AccountState, create bool) (map[string]any, func(), func()) {
	t.Helper()
	require.False(t, create)
	require.Equal(t, "none", t2AccountRegistrationSHA)
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	spc := t2Space(t, state.SpaceID)
	object, err := spc.GetObject(ctx, state.RootID)
	require.ErrorIs(t, err, typeprovider.ErrUnknownChangeType, "legacy registry must reject the unrecognized namespace")
	require.Nil(t, object)
	notApplicable := func() { t.Fatal("legacy phase cannot claim new-registry lifecycle acceptance") }
	return map[string]any{"private_registry": "UNKNOWN_CHANGE_TYPE_REJECTED", "private_read": "NOT_AVAILABLE_ON_LEGACY"},
		notApplicable, notApplicable
}

// The old binary cannot call the new typed boundary and must not claim it did.
func t2RecordStoppedRuntime(_ *testing.T, _ *t2AccountState, observation map[string]any) {
	observation["handler_boundary"] = map[string]any{"scope": "UNSUPPORTED_LEGACY"}
}
