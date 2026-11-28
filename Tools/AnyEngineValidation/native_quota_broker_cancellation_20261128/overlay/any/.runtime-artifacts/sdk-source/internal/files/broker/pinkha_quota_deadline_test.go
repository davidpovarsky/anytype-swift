package broker

import (
	"context"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any-sync/commonfile/fileproto/fileprotov2"
)

// An already-cancelled lookup must not launch even a cooperative peer.
func TestPinkhaQuotaHedgePreCancelledSkipsFleet(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	var calls atomic.Int32

	quota, peer, err := hedgeQuota(ctx, []string{"a", "b"}, time.Hour,
		func(ctx context.Context, _ string) (*fileprotov2.SpaceQuota, error) {
			calls.Add(1)
			return nil, ctx.Err()
		},
		func(q *fileprotov2.SpaceQuota) bool { return q != nil })

	if err != context.Canceled || quota != nil || peer != "" {
		t.Fatalf("cancelled lookup returned quota=%v peer=%q err=%v", quota, peer, err)
	}
	if got := calls.Load(); got != 0 {
		t.Fatalf("cancelled lookup started %d peer calls", got)
	}
}

// Cancelling the coordinator does not terminate an arbitrary callback. This
// test holds that callback explicitly, checks the coordinator first, and then
// releases the callback and joins the coordinator. Cleanup observes callback
// return if callback entry was seen; early entry failures make that observation
// conditional. It does not observe the private sender's final instruction. The
// original len(peers)-buffered channel has room for every late answer.
func TestPinkhaQuotaHedgeEndsBeforeBlockedPeerReturns(t *testing.T) {
	for _, tc := range []struct {
		name     string
		deadline bool
		want     error
	}{
		{name: "cancel", want: context.Canceled},
		{name: "deadline", deadline: true, want: context.DeadlineExceeded},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var ctx context.Context
			var cancel context.CancelFunc
			if tc.deadline {
				ctx, cancel = context.WithTimeout(context.Background(), 5*time.Second)
			} else {
				ctx, cancel = context.WithCancel(context.Background())
			}
			entered := make(chan struct{})
			release := make(chan struct{})
			peerReturned := make(chan struct{})
			coordinatorDone := make(chan struct{})
			var releaseOnce sync.Once
			type answer struct {
				quota *fileprotov2.SpaceQuota
				peer  string
				err   error
			}
			result := make(chan answer, 1)

			t.Cleanup(func() {
				cancel()
				releaseOnce.Do(func() { close(release) })
				select {
				case <-coordinatorDone:
				case <-time.After(2 * time.Second):
					t.Error("test-owned coordinator did not stop after peer release")
				}
				select {
				case <-entered:
					select {
					case <-peerReturned:
					case <-time.After(2 * time.Second):
						t.Error("test-owned peer did not return after release")
					}
				default:
				}
			})

			go func() {
				defer close(coordinatorDone)
				quota, peer, err := hedgeQuota(ctx, []string{"held-peer"}, time.Hour,
					func(context.Context, string) (*fileprotov2.SpaceQuota, error) {
						close(entered)
						defer close(peerReturned)
						<-release
						return &fileprotov2.SpaceQuota{AccountLimitBytes: 123}, nil
					},
					func(q *fileprotov2.SpaceQuota) bool { return q != nil })
				result <- answer{quota, peer, err}
			}()

			select {
			case <-entered:
			case <-time.After(2 * time.Second):
				t.Fatal("peer callback did not start")
			}
			if !tc.deadline {
				cancel()
			}
			select {
			case <-ctx.Done():
			case <-time.After(7 * time.Second):
				t.Fatal("test context did not end")
			}
			select {
			case got := <-result:
				if got.err != tc.want || got.quota != nil || got.peer != "" {
					t.Fatalf("ended lookup returned quota=%v peer=%q err=%v", got.quota, got.peer, got.err)
				}
			case <-time.After(2 * time.Second):
				t.Fatal("quota coordinator waited for a peer after its context ended")
			}
			select {
			case <-peerReturned:
				t.Fatal("callback returned before its independent release")
			default:
			}
		})
	}
}
