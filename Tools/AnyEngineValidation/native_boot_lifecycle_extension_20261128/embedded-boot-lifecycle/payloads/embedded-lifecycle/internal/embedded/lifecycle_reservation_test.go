package embedded

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"runtime/debug"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/anyproto/any/internal/config"
	"github.com/anyproto/any/internal/server"
)

// These controlled runners exercise the production lifecycle state machine.
// Only TestConcurrentLegacyAndBoundStartsShareOneManagedRuntime below uses
// real exported Start/StartBound and canonical server.RunWith.
type lifecycleOutcome struct {
	address string
	binding BoundStartResult
	err     error
}

type lifecycleGate struct {
	done chan struct{}
	once sync.Once
}

func newLifecycleGate(t *testing.T) *lifecycleGate {
	t.Helper()
	g := &lifecycleGate{done: make(chan struct{})}
	t.Cleanup(g.release)
	return g
}

func (g *lifecycleGate) release() { g.once.Do(func() { close(g.done) }) }

func setupLifecycle(t *testing.T) {
	t.Helper()
	resetState(t)
	previousLimit := debug.SetMemoryLimit(-1)
	// Later cleanup gates run first, so a failed assertion cannot leave a
	// controlled runner blocked while the final graceful stop is draining.
	t.Cleanup(func() {
		Stop(true)
		debug.SetMemoryLimit(previousLimit)
		current, _, drain := lifecycleState()
		if current != nil || drain != nil {
			t.Error("lifecycle cleanup retained ownership or a drain")
		}
	})
}

func lifecycleOptions(t *testing.T, name string) Options {
	t.Helper()
	return lifecycleOptionsAt(t.TempDir(), name)
}

func lifecycleOptionsAt(root, name string) Options {
	disabled := false
	return Options{
		DataDir: filepath.Join(root, name), ListenAddr: "127.0.0.1:0",
		NodeconfYAML: "networkId: pinkha-lifecycle-fence\nnodes: []\n",
		Mode:         "managed", ControlToken: "lifecycle-test-capability",
		LocalDiscovery: &disabled, GlobalP2PEnabled: &disabled,
	}
}

func lifecycleState() (*serverHandle, string, chan struct{}) {
	handleMu.Lock()
	defer handleMu.Unlock()
	address := ""
	if handle != nil {
		address = handle.addr
	}
	return handle, address, stopping
}

func callLifecycleCore(opts Options, bound bool, run embeddedRunFunc) lifecycleOutcome {
	var outcome lifecycleOutcome
	var requested *BoundStartResult
	if bound {
		requested = &outcome.binding
	}
	outcome.address, outcome.err = startEmbeddedWithRunner(opts, requested, run)
	return outcome
}

func startLifecycleCore(opts Options, bound bool, run embeddedRunFunc) <-chan lifecycleOutcome {
	result := make(chan lifecycleOutcome, 1)
	go func() { result <- callLifecycleCore(opts, bound, run) }()
	return result
}

func awaitLifecycleSignal(t *testing.T, signal <-chan struct{}, description string) {
	t.Helper()
	select {
	case <-signal:
	case <-time.After(5 * time.Second):
		t.Fatal("timed out: " + description)
	}
}

func awaitLifecycleOutcome(t *testing.T, result <-chan lifecycleOutcome) lifecycleOutcome {
	t.Helper()
	select {
	case value := <-result:
		return value
	case <-time.After(20 * time.Second):
		t.Fatal("lifecycle caller did not return")
		return lifecycleOutcome{}
	}
}

func awaitLifecycleReservation(t *testing.T, previous *serverHandle) *serverHandle {
	t.Helper()
	deadline := time.NewTimer(5 * time.Second)
	defer deadline.Stop()
	tick := time.NewTicker(time.Millisecond)
	defer tick.Stop()
	for {
		current, address, _ := lifecycleState()
		if current != nil && current != previous {
			if address != "" {
				t.Fatal("pending restart published an address before its predecessor drained")
			}
			return current
		}
		select {
		case <-deadline.C:
			t.Fatal("new start did not reserve its generation")
		case <-tick.C:
		}
	}
}

func requireLifecycleHeld(t *testing.T, returned <-chan struct{}, description string) {
	t.Helper()
	select {
	case <-returned:
		t.Fatal("returned before the controlled drain: " + description)
	case <-time.After(25 * time.Millisecond):
	}
}

func stopLifecycleNow(t *testing.T) {
	t.Helper()
	returned := make(chan struct{})
	go func() { StopNow(); close(returned) }()
	select {
	case <-returned:
	case <-time.After(time.Second):
		t.Fatal("StopNow waited for a controlled startup or drain")
	}
}

func TestLifecycleReservationCoversPendingLegacyAndBoundStarts(t *testing.T) {
	for _, firstBound := range []bool{false, true} {
		name := "legacy-core"
		if firstBound {
			name = "bound-core"
		}
		t.Run(name, func(t *testing.T) {
			setupLifecycle(t)
			ready := newLifecycleGate(t)
			entered := make(chan struct{})
			var calls atomic.Int32
			runner := func(ctx context.Context, _ config.Config, options server.RunOptions) error {
				if calls.Add(1) != 1 {
					return errors.New("an overlapping caller launched a second runner")
				}
				close(entered)
				<-ready.done
				options.Ready("127.0.0.1:41001")
				<-ctx.Done()
				return ctx.Err()
			}
			first := startLifecycleCore(lifecycleOptions(t, "first"), firstBound, runner)
			awaitLifecycleSignal(t, entered, "first runner entered before Ready")
			reserved, address, _ := lifecycleState()
			if reserved == nil || address != "" || Address() != "" {
				t.Fatal("pending startup was not reserved without an address")
			}
			for _, competingBound := range []bool{false, true} {
				opts := lifecycleOptions(t, "refused")
				outcome := awaitLifecycleOutcome(t, startLifecycleCore(opts, competingBound, runner))
				if !errors.Is(outcome.err, ErrAlreadyRunning) || outcome.address != "" {
					t.Fatalf("pending double start: address %q, error %v", outcome.address, outcome.err)
				}
				if _, err := os.Lstat(opts.DataDir); !errors.Is(err, os.ErrNotExist) {
					t.Fatalf("refused start touched its data directory: %v", err)
				}
			}
			if calls.Load() != 1 {
				t.Fatal("the singleton guard admitted another runner")
			}
			ready.release()
			outcome := awaitLifecycleOutcome(t, first)
			if outcome.err != nil || outcome.address != "127.0.0.1:41001" || Address() != outcome.address {
				t.Fatalf("first reservation failed: %#v", outcome)
			}
			Stop(true)
		})
	}
}

func TestLifecycleCancelledPendingStartCannotSkipPreviousDrain(t *testing.T) {
	setupLifecycle(t)
	drain := newLifecycleGate(t)
	cancelled := make(chan struct{})
	first := startLifecycleCore(lifecycleOptions(t, "first"), false,
		func(ctx context.Context, _ config.Config, options server.RunOptions) error {
			options.Ready("127.0.0.1:41011")
			<-ctx.Done()
			close(cancelled)
			<-drain.done
			return ctx.Err()
		})
	if value := awaitLifecycleOutcome(t, first); value.err != nil {
		t.Fatal(value.err)
	}
	firstHandle, _, _ := lifecycleState()
	stopLifecycleNow(t)
	awaitLifecycleSignal(t, cancelled, "first cancellation")
	var secondRuns atomic.Int32
	second := startLifecycleCore(lifecycleOptions(t, "cancelled-pending"), true,
		func(context.Context, config.Config, server.RunOptions) error {
			secondRuns.Add(1)
			return errors.New("cancelled pending start reached its runner")
		})
	secondHandle := awaitLifecycleReservation(t, firstHandle)
	stopLifecycleNow(t)
	thirdEntered := make(chan struct{})
	third := startLifecycleCore(lifecycleOptions(t, "third"), false,
		func(ctx context.Context, _ config.Config, options server.RunOptions) error {
			close(thirdEntered)
			select {
			case <-firstHandle.done:
			default:
				return errors.New("third generation bypassed the original drain")
			}
			select {
			case <-secondHandle.done:
			default:
				return errors.New("third generation bypassed its cancelled predecessor")
			}
			options.Ready("127.0.0.1:41013")
			<-ctx.Done()
			return ctx.Err()
		})
	thirdHandle := awaitLifecycleReservation(t, secondHandle)
	_, _, pendingDrain := lifecycleState()
	if pendingDrain != secondHandle.done || thirdHandle == firstHandle {
		t.Fatal("cancelled-start drain chain lost its generation")
	}
	requireLifecycleHeld(t, secondHandle.done, "cancelled pending start")
	requireLifecycleHeld(t, thirdEntered, "third runner")
	drain.release()
	secondResult := awaitLifecycleOutcome(t, second)
	if !errors.Is(secondResult.err, context.Canceled) || secondResult.address != "" || secondRuns.Load() != 0 {
		t.Fatalf("cancelled predecessor ran or succeeded: %#v, runners %d", secondResult, secondRuns.Load())
	}
	thirdResult := awaitLifecycleOutcome(t, third)
	if thirdResult.err != nil || thirdResult.address != "127.0.0.1:41013" || Address() != thirdResult.address {
		t.Fatalf("safe later generation failed: %#v", thirdResult)
	}
	Stop(true)
}

func TestLifecycleGracefulStopFencesNextGeneration(t *testing.T) {
	setupLifecycle(t)
	drain := newLifecycleGate(t)
	cancelled := make(chan struct{})
	first := startLifecycleCore(lifecycleOptions(t, "first"), true,
		func(ctx context.Context, _ config.Config, options server.RunOptions) error {
			options.Ready("127.0.0.1:41021")
			<-ctx.Done()
			close(cancelled)
			<-drain.done
			return ctx.Err()
		})
	if value := awaitLifecycleOutcome(t, first); value.err != nil {
		t.Fatal(value.err)
	}
	firstHandle, _, _ := lifecycleState()
	stopped := make(chan struct{})
	go func() { Stop(true); close(stopped) }()
	awaitLifecycleSignal(t, cancelled, "graceful cancellation")
	current, address, barrier := lifecycleState()
	if current != nil || address != "" || barrier != firstHandle.done {
		t.Fatal("graceful Stop cleared ownership without retaining its drain")
	}
	secondEntered := make(chan struct{})
	second := startLifecycleCore(lifecycleOptions(t, "second"), false,
		func(ctx context.Context, _ config.Config, options server.RunOptions) error {
			close(secondEntered)
			select {
			case <-firstHandle.done:
			default:
				return errors.New("restart overlapped a graceful drain")
			}
			options.Ready("127.0.0.1:41022")
			<-ctx.Done()
			return ctx.Err()
		})
	secondHandle := awaitLifecycleReservation(t, firstHandle)
	requireLifecycleHeld(t, stopped, "graceful caller")
	requireLifecycleHeld(t, secondEntered, "restart during graceful drain")
	drain.release()
	awaitLifecycleSignal(t, stopped, "graceful Stop completed")
	secondResult := awaitLifecycleOutcome(t, second)
	current, address, _ = lifecycleState()
	if secondResult.err != nil || current != secondHandle || address != "127.0.0.1:41022" || Address() != address {
		t.Fatalf("old completion cleared a later generation: %#v", secondResult)
	}
	Stop(true)
}

func TestLifecycleGracefulStopWaitsAfterStopNow(t *testing.T) {
	setupLifecycle(t)
	drain := newLifecycleGate(t)
	cancelled := make(chan struct{})
	first := startLifecycleCore(lifecycleOptions(t, "first"), false,
		func(ctx context.Context, _ config.Config, options server.RunOptions) error {
			options.Ready("127.0.0.1:41025")
			<-ctx.Done()
			close(cancelled)
			<-drain.done
			return ctx.Err()
		})
	if value := awaitLifecycleOutcome(t, first); value.err != nil {
		t.Fatal(value.err)
	}
	stopLifecycleNow(t)
	awaitLifecycleSignal(t, cancelled, "hard-stop cancellation")
	current, _, barrier := lifecycleState()
	if current != nil || barrier == nil {
		t.Fatal("hard-stop drain was not retained")
	}
	entered, stopped := make(chan struct{}), make(chan struct{})
	go func() { close(entered); Stop(true); close(stopped) }()
	awaitLifecycleSignal(t, entered, "graceful caller entered")
	requireLifecycleHeld(t, stopped, "graceful observer of hard-stop drain")
	drain.release()
	awaitLifecycleSignal(t, stopped, "graceful observer completed")
	if current, _, barrier := lifecycleState(); current != nil || barrier != nil {
		t.Fatal("completed hard-stop drain retained global state")
	}
}

func TestLifecycleLateReadyCannotRepublishStoppedGeneration(t *testing.T) {
	setupLifecycle(t)
	drain := newLifecycleGate(t)
	entered, lateReady := make(chan struct{}), make(chan struct{})
	first := startLifecycleCore(lifecycleOptions(t, "cancel-before-ready"), true,
		func(ctx context.Context, _ config.Config, options server.RunOptions) error {
			close(entered)
			<-ctx.Done()
			options.Ready("127.0.0.1:41031")
			close(lateReady)
			<-drain.done
			return ctx.Err()
		})
	awaitLifecycleSignal(t, entered, "pending runner")
	firstHandle, _, _ := lifecycleState()
	stopLifecycleNow(t)
	awaitLifecycleSignal(t, lateReady, "stale Ready callback after cancellation")
	second := startLifecycleCore(lifecycleOptions(t, "replacement"), false,
		func(ctx context.Context, _ config.Config, options server.RunOptions) error {
			select {
			case <-firstHandle.done:
			default:
				return errors.New("replacement booted before stale runner drained")
			}
			options.Ready("127.0.0.1:41032")
			<-ctx.Done()
			return ctx.Err()
		})
	secondHandle := awaitLifecycleReservation(t, firstHandle)
	if Address() != "" {
		t.Fatal("stale Ready was published during replacement admission")
	}
	drain.release()
	firstResult := awaitLifecycleOutcome(t, first)
	if firstResult.address != "" || !errors.Is(firstResult.err, context.Canceled) {
		t.Fatalf("cancelled start returned its stale listener: %#v", firstResult)
	}
	secondResult := awaitLifecycleOutcome(t, second)
	current, address, _ := lifecycleState()
	if secondResult.err != nil || current != secondHandle || address != "127.0.0.1:41032" {
		t.Fatalf("stale completion replaced the new reservation: %#v", secondResult)
	}
	Stop(true)
}

func TestLifecycleFailedStartReleasesReservation(t *testing.T) {
	bootFailure := errors.New("controlled pre-Ready boot failure")
	for _, name := range []string{"empty-directory", "invalid-mode", "bound-network", "runner-failure"} {
		t.Run(name, func(t *testing.T) {
			setupLifecycle(t)
			opts := lifecycleOptions(t, name)
			bound, wanted := false, ErrBadOptions
			switch name {
			case "empty-directory":
				opts.DataDir = ""
				wanted = ErrBadDataDir
			case "invalid-mode":
				opts.Mode = "unsupported-mode"
			case "bound-network":
				bound = true
				opts.NodeconfYAML = "networkId: \"contains a space\"\nnodes: []\n"
			case "runner-failure":
				bound, wanted = true, bootFailure
			}
			var runs atomic.Int32
			result := callLifecycleCore(opts, bound,
				func(context.Context, config.Config, server.RunOptions) error {
					runs.Add(1)
					return bootFailure
				})
			expectedRuns := int32(0)
			if name == "runner-failure" {
				expectedRuns = 1
			}
			if result.address != "" || !errors.Is(result.err, wanted) || runs.Load() != expectedRuns {
				t.Fatalf("wrong startup failure or runner admission: %#v, runners %d", result, runs.Load())
			}
			if current, _, drain := lifecycleState(); current != nil || drain != nil {
				t.Fatal("failed start retained its reservation")
			}
			next := startLifecycleCore(lifecycleOptions(t, "after-failure"), true,
				func(ctx context.Context, _ config.Config, options server.RunOptions) error {
					options.Ready("127.0.0.1:41041")
					<-ctx.Done()
					return ctx.Err()
				})
			if value := awaitLifecycleOutcome(t, next); value.err != nil || value.address != "127.0.0.1:41041" {
				t.Fatalf("failed attempt blocked a valid successor: %#v", value)
			}
			Stop(true)
		})
	}
}

func TestConcurrentLegacyAndBoundStartsShareOneManagedRuntime(t *testing.T) {
	resetState(t)
	previousLimit := debug.SetMemoryLimit(-1)
	const count = 8
	// This root has no automatic TempDir cleanup: on a failed cohort join
	// it must remain intact for the still-owned caller and failure evidence.
	root, err := os.MkdirTemp("", "pinkha-embedded-lifecycle-")
	if err != nil {
		t.Fatal(err)
	}
	options := make([]Options, count)
	for i := range options {
		options[i] = lifecycleOptionsAt(root, fmt.Sprintf("export-%d", i))
	}
	type exportedOutcome struct {
		index int
		bound bool
		value lifecycleOutcome
	}
	results := make(chan exportedOutcome, count)
	start := &lifecycleGate{done: make(chan struct{})}
	var ready, returned sync.WaitGroup
	ready.Add(count)
	returned.Add(count)
	allReturned := make(chan struct{})
	go func() { returned.Wait(); close(allReturned) }()
	t.Cleanup(func() {
		defer debug.SetMemoryLimit(previousLimit)
		start.release()
		deadline := time.NewTimer(20 * time.Second)
		defer deadline.Stop()
		tick := time.NewTicker(10 * time.Millisecond)
		defer tick.Stop()
		// Stop may observe only one admitted generation. Keep cancelling
		// until every launched export caller has returned; none can then
		// enter Start after the final drain or after its directory is removed.
		joined := false
		for !joined {
			StopNow()
			select {
			case <-allReturned:
				joined = true
			case <-tick.C:
			case <-deadline.C:
				t.Errorf("export callers did not drain; retained root %s", root)
				panic("lifecycle caller custody incomplete")
			}
		}
		StopNow()
		_, _, drain := lifecycleState()
		if drain != nil {
			select {
			case <-drain:
			case <-deadline.C:
				t.Errorf("export engine did not drain; retained root %s", root)
				panic("lifecycle engine custody incomplete")
			}
		}
		current, address, pending := lifecycleState()
		if current != nil || address != "" || pending != nil {
			t.Errorf("joined export cohort retained state; retained root %s", root)
			panic("lifecycle final state is not closed")
		}
		if t.Failed() {
			t.Logf("retained failed export fixture after complete drain: %s", root)
			return
		}
		if err := os.RemoveAll(root); err != nil {
			t.Errorf("remove drained export fixture: %v", err)
		}
	})
	for i := 0; i < count; i++ {
		go func(index int) {
			defer returned.Done()
			ready.Done()
			<-start.done
			value := lifecycleOutcome{}
			bound := index%2 == 1
			if bound {
				value.binding, value.err = StartBound(options[index])
				value.address = value.binding.Address
			} else {
				value.address, value.err = Start(options[index])
			}
			results <- exportedOutcome{index: index, bound: bound, value: value}
		}(i)
	}
	ready.Wait()
	start.release()
	winners := 0
	var winner exportedOutcome
	timer := time.NewTimer(20 * time.Second)
	defer timer.Stop()
	for i := 0; i < count; i++ {
		var item exportedOutcome
		select {
		case item = <-results:
		case <-timer.C:
			t.Fatal("concurrent native exports did not finish")
		}
		if item.value.err == nil {
			winners++
			winner = item
		} else {
			if !errors.Is(item.value.err, ErrAlreadyRunning) || item.value.address != "" ||
				(item.bound && item.value.binding != (BoundStartResult{})) {
				t.Fatalf("losing public export returned another boot's state: %#v", item)
			}
			if _, err := os.Lstat(options[item.index].DataDir); !errors.Is(err, os.ErrNotExist) {
				t.Fatalf("losing public export touched its data root: %v", err)
			}
		}
	}
	if winners != 1 || winner.value.address == "" || Address() != winner.value.address {
		t.Fatalf("concurrent exports admitted %d running engines", winners)
	}
	if winner.bound && winner.value.binding.NetworkID != "pinkha-lifecycle-fence" {
		t.Fatal("the bound winner lost its independently expected network")
	}
	host, port, err := net.SplitHostPort(winner.value.address)
	if err != nil || host != "127.0.0.1" || port == "" || port == "0" {
		t.Fatalf("invalid real managed listener: %q, %v", winner.value.address, err)
	}
	transport := &http.Transport{Proxy: nil}
	defer transport.CloseIdleConnections()
	client := &http.Client{
		Transport: transport, Timeout: 5 * time.Second,
		CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
	}
	request, err := http.NewRequest(http.MethodGet, "http://"+winner.value.address+"/v1/health", nil)
	if err != nil {
		t.Fatal(err)
	}
	request.Header.Set("X-Any-Control-Token", options[winner.index].ControlToken)
	response, err := client.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	body, readErr := io.ReadAll(io.LimitReader(response.Body, 65537))
	closeErr := response.Body.Close()
	if response.StatusCode != http.StatusOK || readErr != nil || closeErr != nil || len(body) > 65536 {
		t.Fatalf("managed health response: status %d, read %v, close %v", response.StatusCode, readErr, closeErr)
	}
	var health map[string]any
	if err := json.Unmarshal(body, &health); err != nil {
		t.Fatal(err)
	}
	if health["networkId"] != "pinkha-lifecycle-fence" || health["account"] != "" {
		t.Fatalf("the real winner booted another network/account: %#v", health)
	}
	Stop(true)
	if Address() != "" {
		t.Fatal("real managed Stop retained a listener")
	}
}
