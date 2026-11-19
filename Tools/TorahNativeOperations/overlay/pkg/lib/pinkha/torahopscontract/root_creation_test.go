package torahopscontract

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestPinkhaRootCreationGuardRejectsMissingForeignUsedAndCancelled(t *testing.T) {
	for _, scenario := range []string{"missing", "foreign_space", "foreign_root", "cancelled", "reused", "denied_at_storage_boundary"} {
		t.Run(scenario, func(t *testing.T) {
			calls, checks := 0, 0
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			denied := errors.New("authority changed before native root transaction")
			guarded := WithRootCreationGuard(ctx, "space", "root", func(create func() error) error {
				checks++
				if scenario == "denied_at_storage_boundary" {
					return denied
				}
				return create()
			})
			create := func() error { calls++; return nil }
			space, root := "space", "root"
			want := ErrPrivateOperation
			switch scenario {
			case "missing":
				guarded = ctx
			case "foreign_space":
				space = "other"
			case "foreign_root":
				root = "other"
			case "cancelled":
				cancel()
				want = context.Canceled
			case "reused":
				require.NoError(t, CreateRootWithGuard(guarded, space, root, create))
			case "denied_at_storage_boundary":
				want = denied
			}
			err := CreateRootWithGuard(guarded, space, root, create)
			require.ErrorIs(t, err, want)
			if scenario == "reused" {
				require.Equal(t, 1, calls)
				require.Equal(t, 1, checks)
			} else {
				require.Zero(t, calls, "rejected authority must not invoke native storage")
				if scenario != "denied_at_storage_boundary" {
					require.Zero(t, checks)
				}
			}
		})
	}
}
