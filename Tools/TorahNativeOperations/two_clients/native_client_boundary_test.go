package service

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/pb"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

type t2ClientByteReply struct {
	data     []byte
	panicked bool
}

type t2ClientByteResult struct {
	data             []byte
	failure          string
	originalReturned bool
	stopRequested    bool
	stopReturned     bool
	stopData         []byte
	stopPanicked     bool
}

// Workers only invoke the byte API and send an owned result. They never call
// testing.T methods, decode protobufs, write receipts, or interpret authority.
func t2ClientByteWorker(entry func([]byte) []byte, request []byte) <-chan t2ClientByteReply {
	done := make(chan t2ClientByteReply, 1)
	ownedRequest := append([]byte(nil), request...)
	go func() {
		defer func() {
			if recover() != nil {
				done <- t2ClientByteReply{panicked: true}
			}
		}()
		done <- t2ClientByteReply{data: entry(ownedRequest)}
	}()
	return done
}

func t2AwaitClientBytes(ctx context.Context, entry func([]byte) []byte, request []byte,
	stop func([]byte) []byte, stopRequest []byte, grace time.Duration) t2ClientByteResult {
	done := t2ClientByteWorker(entry, request)
	result := t2ClientByteResult{}
	select {
	case reply := <-done:
		result.originalReturned = true
		if !reply.panicked && ctx.Err() == nil {
			result.data = reply.data
			return result
		}
		if reply.panicked {
			result.failure = "CALL_PANIC"
		}
	case <-ctx.Done():
	}
	if result.failure == "" {
		if ctx.Err() == context.DeadlineExceeded {
			result.failure = "CALL_DEADLINE"
		} else {
			result.failure = "CALL_CANCELLED"
		}
	}
	var stopped <-chan t2ClientByteReply
	if stop != nil {
		result.stopRequested = true
		stopped = t2ClientByteWorker(stop, stopRequest)
	}
	if result.originalReturned {
		done = nil
	}
	deadline := time.NewTimer(grace)
	defer deadline.Stop()
	for !result.originalReturned || (result.stopRequested && !result.stopReturned) {
		select {
		case <-done:
			result.originalReturned = true
			done = nil
		case reply := <-stopped:
			result.stopReturned = true
			result.stopData, result.stopPanicked = reply.data, reply.panicked
			stopped = nil
		case <-deadline.C:
			return result
		}
	}
	return result
}

type t2NativeClientCaller struct {
	t              *testing.T
	rpc            *t2AccountRPC
	role           string
	nonce          string
	startRequested bool
	stopAttempted  bool
	closed         bool
	returnedCalls  map[string]int
}

func (c *t2NativeClientCaller) raw(name string, entry func([]byte) []byte, request, response proto.Message, limit time.Duration) {
	c.t.Helper()
	c.rpc.raw(func(data []byte) []byte {
		ctx, cancel := context.WithTimeout(context.Background(), limit)
		defer cancel()
		stopRequest, err := proto.Marshal(&pb.RpcAccountStopRequest{RemoveData: false})
		require.NoError(c.t, err)
		var stop func([]byte) []byte
		if name != "AccountStop" && !c.stopAttempted {
			stop = AccountStop
		}
		result := t2AwaitClientBytes(ctx, entry, data, stop, stopRequest, 15*time.Second)
		if result.failure == "" {
			c.returnedCalls[name]++
			return result.data
		}
		if result.stopRequested {
			c.stopAttempted = true
		}
		stopCode := int32(-1)
		if result.stopReturned && !result.stopPanicked {
			stopped := &pb.RpcAccountStopResponse{}
			if proto.Unmarshal(result.stopData, stopped) == nil && stopped.Error != nil {
				stopCode = int32(stopped.Error.Code)
				c.closed = stopped.Error.Code == pb.RpcAccountStopResponseError_NULL && result.originalReturned
			}
		}
		receipt := map[string]any{"protocol": t2NativeClientProtocol, "role": c.role, "nonce": c.nonce,
			"status": result.failure, "call": name, "limit_ms": limit.Milliseconds(),
			"original_call_joined": result.originalReturned, "native_stop_requested": result.stopRequested,
			"native_stop_joined": result.stopReturned, "native_stop_error_code": stopCode,
			"owned_container_termination_required": !c.closed, "returned_byte_calls": c.returnedCalls,
			"request_or_response_bytes_in_receipt": false, "test_passed": false,
			"finished_at": time.Now().UTC().Format(time.RFC3339Nano)}
		path := filepath.Join("/private", "cancel.json")
		if _, statErr := os.Lstat(path); os.IsNotExist(statErr) {
			encoded, marshalErr := json.MarshalIndent(receipt, "", "  ")
			require.NoError(c.t, marshalErr)
			t2NativeClientReport(c.t, path, encoded)
		}
		c.t.Fatalf("bounded native byte call failed: %s/%s; private bytes withheld", name, result.failure)
		return nil
	}, request, response)
}

func (c *t2NativeClientCaller) invoke(name string, entry func([]byte) []byte, request, response proto.Message, limit time.Duration) {
	c.t.Helper()
	c.raw(name, entry, request, response, limit)
	c.rpc.check(response)
}

func TestT2NativeClientByteBoundaryControls(t *testing.T) {
	t.Run("success_owns_request_and_does_not_stop", func(t *testing.T) {
		input := []byte("synthetic-input")
		result := t2AwaitClientBytes(context.Background(), func(value []byte) []byte {
			value[0] = 'X'
			return []byte("synthetic-output")
		}, input, func([]byte) []byte { panic("stop must not run") }, nil, time.Second)
		require.Empty(t, result.failure)
		require.Equal(t, []byte("synthetic-output"), result.data)
		require.Equal(t, []byte("synthetic-input"), input)
		require.True(t, result.originalReturned)
		require.False(t, result.stopRequested)
	})
	t.Run("panic_is_redacted_and_native_stop_joins", func(t *testing.T) {
		result := t2AwaitClientBytes(context.Background(), func([]byte) []byte { panic("synthetic-private-panic") }, nil,
			func([]byte) []byte { return []byte("stop-response") }, nil, time.Second)
		require.Equal(t, "CALL_PANIC", result.failure)
		require.Nil(t, result.data)
		require.True(t, result.originalReturned && result.stopRequested && result.stopReturned)
		require.False(t, result.stopPanicked)
	})
	t.Run("cancel_calls_stop_then_joins_original", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()
		started, released := make(chan struct{}), make(chan struct{})
		go func() { <-started; cancel() }()
		result := t2AwaitClientBytes(ctx, func([]byte) []byte { close(started); <-released; return []byte("late-private-response") }, nil,
			func([]byte) []byte { close(released); return []byte("stop-response") }, nil, time.Second)
		require.Equal(t, "CALL_CANCELLED", result.failure)
		require.Nil(t, result.data, "late response after cancellation must not become success")
		require.True(t, result.originalReturned && result.stopRequested && result.stopReturned)
	})
	t.Run("stuck_stop_and_call_leave_explicit_unjoined_failure", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()
		started, released := make(chan struct{}), make(chan struct{})
		var workers sync.WaitGroup
		workers.Add(2)
		go func() { <-started; cancel() }()
		result := t2AwaitClientBytes(ctx, func([]byte) []byte { defer workers.Done(); close(started); <-released; return nil }, nil,
			func([]byte) []byte { defer workers.Done(); <-released; return nil }, nil, 25*time.Millisecond)
		close(released)
		joined := make(chan struct{})
		go func() { workers.Wait(); close(joined) }()
		select {
		case <-joined:
		case <-time.After(time.Second):
			t.Fatal("owned control workers did not join")
		}
		require.Equal(t, "CALL_CANCELLED", result.failure)
		require.False(t, result.originalReturned)
		require.True(t, result.stopRequested)
		require.False(t, result.stopReturned)
	})
}

func TestT2NativeClientReadReadinessControls(t *testing.T) {
	state := &t2AccountState{RootID: "root", ClaimID: "claim", Heads: []string{"change"}}
	valid := func() *pb.RpcPinkhaTorahOperationsReadTargetResponse {
		return &pb.RpcPinkhaTorahOperationsReadTargetResponse{ProtocolVersion: 1,
			Error: &pb.RpcPinkhaTorahOperationsReadTargetResponseError{},
			Snapshot: &pb.RpcPinkhaTorahOperationsSnapshot{Scope: pb.RpcPinkhaTorahOperations_LOCAL_VERIFIED_TREE,
				VerifiedLocalHeads: []string{"change"}, Live: []*pb.RpcPinkhaTorahOperationsClaim{{ClaimId: "claim"}}}}
	}
	t.Run("expected_claim_and_head_ready", func(t *testing.T) {
		ready, err := t2NativeClientReadReady(state, valid())
		require.NoError(t, err)
		require.True(t, ready)
	})
	t.Run("root_only_prefix_is_not_convergence", func(t *testing.T) {
		response := valid()
		response.Snapshot.Live = nil
		response.Snapshot.VerifiedLocalHeads = []string{"root"}
		ready, err := t2NativeClientReadReady(state, response)
		require.NoError(t, err)
		require.False(t, ready)
	})
	t.Run("history_unavailable_can_wait", func(t *testing.T) {
		response := valid()
		response.Snapshot = nil
		response.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE
		response.Error.Issues = []pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_HISTORY_UNAVAILABLE}
		ready, err := t2NativeClientReadReady(state, response)
		require.NoError(t, err)
		require.False(t, ready)
	})
	t.Run("permission_denial_is_immediate_failure", func(t *testing.T) {
		response := valid()
		response.Snapshot = nil
		response.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_PERMISSION_DENIED
		ready, err := t2NativeClientReadReady(state, response)
		require.Error(t, err)
		require.False(t, ready)
	})
	t.Run("joined_denial_cannot_hide_in_transient_error", func(t *testing.T) {
		response := valid()
		response.Snapshot = nil
		response.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE
		response.Error.Issues = []pb.RpcPinkhaTorahOperationsIssue{pb.RpcPinkhaTorahOperations_ISSUE_PERMISSION_DENIED}
		ready, err := t2NativeClientReadReady(state, response)
		require.Error(t, err)
		require.False(t, ready)
	})
	t.Run("foreign_claim_is_not_eventual_readiness", func(t *testing.T) {
		response := valid()
		response.Snapshot.Live[0].ClaimId = "foreign-claim"
		ready, err := t2NativeClientReadReady(state, response)
		require.Error(t, err)
		require.False(t, ready)
	})
	t.Run("failed_read_must_not_expose_a_snapshot", func(t *testing.T) {
		response := valid()
		response.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE
		ready, err := t2NativeClientReadReady(state, response)
		require.Error(t, err)
		require.False(t, ready)
	})
}

func TestT2NativeClientReadObservationControls(t *testing.T) {
	t.Run("invalid_envelope_is_fixed", func(t *testing.T) {
		for _, response := range []*pb.RpcPinkhaTorahOperationsReadTargetResponse{nil, {}, {ProtocolVersion: 1}} {
			require.Equal(t, "T2_READ_OBSERVATION code=INVALID_ENVELOPE snapshot_present=false readiness=REJECTED",
				t2NativeClientReadObservation(response, false, context.Canceled))
		}
	})
	t.Run("known_code_and_predicate_are_observed_without_private_fields", func(t *testing.T) {
		response := &pb.RpcPinkhaTorahOperationsReadTargetResponse{ProtocolVersion: 1,
			Error: &pb.RpcPinkhaTorahOperationsReadTargetResponseError{
				Code: pb.RpcPinkhaTorahOperationsReadTargetResponseError_HISTORY_UNAVAILABLE, Description: "synthetic-private-error"},
			Snapshot: &pb.RpcPinkhaTorahOperationsSnapshot{VerifiedLocalHeads: []string{"synthetic-private-head"}}}
		before := proto.Clone(response)
		require.Equal(t, "T2_READ_OBSERVATION code=HISTORY_UNAVAILABLE snapshot_present=true readiness=WAIT",
			t2NativeClientReadObservation(response, false, nil))
		require.Equal(t, "T2_READ_OBSERVATION code=HISTORY_UNAVAILABLE snapshot_present=true readiness=REJECTED",
			t2NativeClientReadObservation(response, false, context.Canceled))
		require.Equal(t, before, response, "observation must not alter the already returned response")
		response.Error.Code = pb.RpcPinkhaTorahOperationsReadTargetResponseError_NULL
		require.Equal(t, "T2_READ_OBSERVATION code=NULL snapshot_present=true readiness=READY",
			t2NativeClientReadObservation(response, true, nil))
	})
	t.Run("unknown_code_is_not_exported", func(t *testing.T) {
		response := &pb.RpcPinkhaTorahOperationsReadTargetResponse{ProtocolVersion: 1,
			Error: &pb.RpcPinkhaTorahOperationsReadTargetResponseError{Code: 730001, Description: "synthetic-private-error"}}
		require.Equal(t, "T2_READ_OBSERVATION code=UNRECOGNIZED_CODE snapshot_present=false readiness=REJECTED",
			t2NativeClientReadObservation(response, false, context.Canceled))
	})
}
