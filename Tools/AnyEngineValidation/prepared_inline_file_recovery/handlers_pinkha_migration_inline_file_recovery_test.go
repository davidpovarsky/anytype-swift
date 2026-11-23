//go:build linux && pinkha_inline_recovery

package server

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptrace"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sync/atomic"
	"syscall"
	"testing"
	"time"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/anyproto/any/internal/api"
	"github.com/stretchr/testify/require"
)

const inlineRecoveryProtocol = "pinkha-inline-native-process-recovery-v1"

type inlineRecoveryLaunch struct {
	Protocol  string `json:"protocol"`
	Nonce     string `json:"nonce"`
	Directory string `json:"directory"`
	Child     int    `json:"child"`
	ParentPID int    `json:"parentPID"`
}

type inlineRecoveryReady struct {
	URL           string                              `json:"url"`
	Owner         string                              `json:"owner"`
	Capability    api.MigrationInlineFileCapabilities `json:"capability"`
	WalletCreated bool                                `json:"walletCreated"`
}

type inlineRecoveryObservation struct {
	Receipt       space.MigrationInlineFileReceipt `json:"receipt"`
	Stats         space.FileStats                  `json:"stats"`
	Files         []space.FileInfo                 `json:"files"`
	Info          *space.FileInfo                  `json:"info,omitempty"`
	Content       []byte                           `json:"content,omitempty"`
	ContentSHA256 string                           `json:"contentSHA256,omitempty"`
}

type inlineRecoveryDrop struct {
	RequestSHA256        string                    `json:"requestSHA256"`
	ResponseSHA256       string                    `json:"responseSHA256"`
	ResponseStatus       int                       `json:"responseStatus"`
	ResponseBytes        int                       `json:"responseBytes"`
	ForwardedBytes       int                       `json:"forwardedBytes"`
	NetworkBufferedBytes int                       `json:"networkBufferedBytes"`
	TargetRequests       int                       `json:"targetRequests"`
	Hijacked             bool                      `json:"hijacked"`
	ConnectionClosed     bool                      `json:"connectionClosed"`
	Observation          inlineRecoveryObservation `json:"observation"`
}

type inlineRecoveryFrame struct {
	Protocol    string                     `json:"protocol"`
	Nonce       string                     `json:"nonce"`
	PID         int                        `json:"pid"`
	PGID        int                        `json:"pgid"`
	Sequence    int                        `json:"sequence"`
	Kind        string                     `json:"kind"`
	Error       string                     `json:"error,omitempty"`
	Ready       *inlineRecoveryReady       `json:"ready,omitempty"`
	Observation *inlineRecoveryObservation `json:"observation,omitempty"`
	Drop        *inlineRecoveryDrop        `json:"drop,omitempty"`
}

type inlineRecoveryCommand struct {
	Protocol      string                           `json:"protocol"`
	Nonce         string                           `json:"nonce"`
	Sequence      int                              `json:"sequence"`
	Kind          string                           `json:"kind"`
	Receipt       space.MigrationInlineFileReceipt `json:"receipt"`
	Path          string                           `json:"path,omitempty"`
	RequestSHA256 string                           `json:"requestSHA256,omitempty"`
}

type inlineRecoveryRead struct {
	frame inlineRecoveryFrame
	err   error
}

type inlineRecoverySession struct {
	t                          *testing.T
	directory, evidence, nonce string
	sequence                   int
	pids                       map[int]bool
	children                   int
}

type inlineRecoveryProcess struct {
	session  *inlineRecoverySession
	number   int
	cmd      *exec.Cmd
	input    *os.File
	encoder  *json.Encoder
	frames   chan inlineRecoveryRead
	wait     chan error
	logPath  string
	alive    bool
	sequence int
	ready    inlineRecoveryReady
}

func inlineRecoveryWrite(path string, value any) error {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err = encoder.Encode(value); err == nil {
		err = file.Sync()
	}
	closeErr := file.Close()
	if err == nil {
		err = closeErr
	}
	return err
}

func (s *inlineRecoverySession) record(kind string, value any) {
	s.t.Helper()
	s.sequence++
	path := filepath.Join(s.evidence, fmt.Sprintf("%03d-%s.json", s.sequence, kind))
	require.NoError(s.t, inlineRecoveryWrite(path, map[string]any{
		"protocol": inlineRecoveryProtocol, "nonce": s.nonce, "test": s.t.Name(),
		"parentPID": os.Getpid(), "timeUTC": time.Now().UTC(), "value": value,
	}))
}

func inlineRecoveryNew(t *testing.T) *inlineRecoverySession {
	t.Helper()
	privateRoot, evidenceRoot := os.Getenv("PINKHA_INLINE_RECOVERY_PRIVATE"), os.Getenv("PINKHA_INLINE_RECOVERY_EVIDENCE")
	require.True(t, filepath.IsAbs(privateRoot) && filepath.IsAbs(evidenceRoot) && privateRoot != evidenceRoot)
	for _, root := range []string{privateRoot, evidenceRoot} {
		info, err := os.Lstat(root)
		require.NoError(t, err)
		require.True(t, info.IsDir() && info.Mode().Perm() == 0700, "explicit private owned roots required")
	}
	s := &inlineRecoverySession{t: t, directory: filepath.Join(privateRoot, t.Name()),
		evidence: filepath.Join(evidenceRoot, t.Name()), pids: make(map[int]bool)}
	require.NoError(t, os.Mkdir(s.directory, 0700), "refuse an existing test store")
	require.NoError(t, os.Mkdir(s.evidence, 0700), "refuse existing evidence")
	nonce := make([]byte, 16)
	_, err := rand.Read(nonce)
	require.NoError(t, err)
	s.nonce = hex.EncodeToString(nonce)
	t.Cleanup(func() {
		s.record("terminal", map[string]any{"failed": t.Failed(), "children": s.children,
			"distinctChildPIDs": len(s.pids), "privateStorePreserved": true,
			"powerLossProven": false, "networkProven": false, "swiftClientProven": false,
			"notificationOutboxProven": false, "fullMigrationProven": false})
	})
	s.record("begin", map[string]any{"freshStore": true, "freshEvidence": true})
	return s
}

func (s *inlineRecoverySession) start() *inlineRecoveryProcess {
	t := s.t
	t.Helper()
	s.children++
	number := s.children
	launch := inlineRecoveryLaunch{Protocol: inlineRecoveryProtocol, Nonce: s.nonce,
		Directory: s.directory, Child: number, ParentPID: os.Getpid()}
	launchPath := filepath.Join(s.directory, fmt.Sprintf("child-%d-launch.json", number))
	require.NoError(t, inlineRecoveryWrite(launchPath, launch))
	executable, err := os.Executable()
	require.NoError(t, err)
	commandRead, commandWrite, err := os.Pipe()
	require.NoError(t, err)
	resultRead, resultWrite, err := os.Pipe()
	require.NoError(t, err)
	logPath := filepath.Join(s.directory, fmt.Sprintf("child-%d-original.log", number))
	log, err := os.OpenFile(logPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	require.NoError(t, err)
	cmd := exec.Command(executable, "-test.run=^TestPreparedInlineFileRecoveryChild$", "-test.count=1", "-test.v", "-test.timeout=180s")
	cmd.Env = append(os.Environ(), "PINKHA_INLINE_RECOVERY_LAUNCH="+launchPath)
	cmd.ExtraFiles = []*os.File{commandRead, resultWrite}
	cmd.Stdout = log
	cmd.Stderr = log
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	err = cmd.Start()
	_ = commandRead.Close()
	_ = resultWrite.Close()
	if err != nil {
		_ = commandWrite.Close()
		_ = resultRead.Close()
		_ = log.Close()
		t.Fatal(err)
	}
	p := &inlineRecoveryProcess{session: s, number: number, cmd: cmd, input: commandWrite,
		encoder: json.NewEncoder(commandWrite), frames: make(chan inlineRecoveryRead, 8),
		wait: make(chan error, 1), logPath: logPath, alive: true}
	go func() { err := cmd.Wait(); _ = log.Sync(); _ = log.Close(); p.wait <- err }()
	go func() {
		defer resultRead.Close()
		decoder := json.NewDecoder(resultRead)
		for {
			var frame inlineRecoveryFrame
			err := decoder.Decode(&frame)
			p.frames <- inlineRecoveryRead{frame: frame, err: err}
			if err != nil {
				return
			}
		}
	}()
	t.Cleanup(func() {
		if p.alive {
			p.kill("failure-cleanup", false)
		}
		_ = p.input.Close()
	})
	require.False(t, s.pids[cmd.Process.Pid], "the new child must have a distinct actual PID")
	s.pids[cmd.Process.Pid] = true
	pgid, err := syscall.Getpgid(cmd.Process.Pid)
	require.NoError(t, err)
	require.Equal(t, cmd.Process.Pid, pgid)
	s.record("process-start", map[string]any{"child": number, "pid": cmd.Process.Pid,
		"selector": "TestPreparedInlineFileRecoveryChild", "separateProcessGroup": true, "pgid": pgid})
	frame := p.receive("ready", 0)
	require.NotNil(t, frame.Ready)
	p.ready = *frame.Ready
	u, err := url.Parse(p.ready.URL)
	require.NoError(t, err)
	require.Equal(t, "http", u.Scheme)
	require.True(t, u.Hostname() == "127.0.0.1" || u.Hostname() == "::1")
	require.Equal(t, number == 1, p.ready.WalletCreated)
	s.record("ready", frame)
	return p
}

func (p *inlineRecoveryProcess) receive(kind string, sequence int) inlineRecoveryFrame {
	t := p.session.t
	t.Helper()
	select {
	case item := <-p.frames:
		require.NoError(t, item.err, "child protocol failed; private original log is preserved")
		f := item.frame
		require.Equal(t, inlineRecoveryProtocol, f.Protocol)
		require.Equal(t, p.session.nonce, f.Nonce)
		require.Equal(t, p.cmd.Process.Pid, f.PID)
		require.Equal(t, p.cmd.Process.Pid, f.PGID)
		require.Equal(t, kind, f.Kind)
		require.Equal(t, sequence, f.Sequence)
		require.Empty(t, f.Error, "child observation failed; original failure is retained")
		return f
	case <-time.After(45 * time.Second):
		t.Fatal("owned child did not produce the expected bounded protocol frame")
	}
	return inlineRecoveryFrame{}
}

func (p *inlineRecoveryProcess) command(command inlineRecoveryCommand) inlineRecoveryFrame {
	p.session.t.Helper()
	p.sequence++
	command.Protocol = inlineRecoveryProtocol
	command.Nonce = p.session.nonce
	command.Sequence = p.sequence
	require.NoError(p.session.t, p.encoder.Encode(command))
	frame := p.receive(command.Kind, command.Sequence)
	p.session.record(command.Kind, frame)
	return frame
}

func (p *inlineRecoveryProcess) await() error {
	t := p.session.t
	t.Helper()
	select {
	case err := <-p.wait:
		p.alive = false
		return err
	case <-time.After(20 * time.Second):
		t.Fatal("owned child did not exit within the fixed deadline")
	}
	return nil
}

func (p *inlineRecoveryProcess) logDigest() string {
	raw, err := os.ReadFile(p.logPath)
	require.NoError(p.session.t, err)
	return inlineHTTPHash(raw)
}

func (p *inlineRecoveryProcess) marker(suffix string) string {
	return filepath.Join(p.session.directory, fmt.Sprintf("child-%d-%s.json", p.number, suffix))
}

func (p *inlineRecoveryProcess) kill(boundary string, deliberate bool) {
	t := p.session.t
	t.Helper()
	p.session.record("kill-intention", map[string]any{"child": p.number, "pid": p.cmd.Process.Pid,
		"boundary": boundary, "signal": "SIGKILL", "deliberate": deliberate})
	signalErr := p.cmd.Process.Signal(syscall.SIGKILL)
	if !deliberate && signalErr != nil {
		waitErr := p.await()
		p.session.record("failed-child-already-exited", map[string]any{"child": p.number, "pid": p.cmd.Process.Pid,
			"signalError": signalErr.Error(), "waitError": fmt.Sprint(waitErr), "privateOriginalLogSHA256": p.logDigest(),
			"usedAsCrashProof": false})
		return
	}
	require.NoError(t, signalErr)
	err := p.await()
	var exit *exec.ExitError
	require.ErrorAs(t, err, &exit)
	status, ok := p.cmd.ProcessState.Sys().(syscall.WaitStatus)
	require.True(t, ok)
	require.True(t, status.Signaled())
	require.Equal(t, syscall.SIGKILL, status.Signal())
	_, startErr := os.Lstat(p.marker("close-start"))
	_, doneErr := os.Lstat(p.marker("close-complete"))
	require.True(t, os.IsNotExist(startErr) && os.IsNotExist(doneErr), "a crash boundary must not invoke orderly close")
	require.ErrorIs(t, syscall.Kill(p.cmd.Process.Pid, 0), syscall.ESRCH, "the exact waited child must be gone")
	p.session.record("sigkill", map[string]any{"child": p.number, "pid": p.cmd.Process.Pid,
		"boundary": boundary, "signal": int(status.Signal()), "signaled": status.Signaled(),
		"exitCode": p.cmd.ProcessState.ExitCode(), "waitStatus": uint32(status), "waitCompleted": true, "exactPIDAbsent": true,
		"orderlyCloseStarted": false, "orderlyCloseCompleted": false, "deliberate": deliberate,
		"privateOriginalLogSHA256": p.logDigest()})
	_ = p.input.Close()
}

func (p *inlineRecoveryProcess) close() {
	t := p.session.t
	t.Helper()
	p.command(inlineRecoveryCommand{Kind: "close"})
	require.NoError(t, p.await())
	for _, suffix := range []string{"close-start", "close-complete"} {
		info, err := os.Lstat(p.marker(suffix))
		require.NoError(t, err)
		require.True(t, info.Mode().IsRegular())
	}
	p.session.record("normal-cleanup", map[string]any{"child": p.number, "pid": p.cmd.Process.Pid,
		"exitCode": p.cmd.ProcessState.ExitCode(), "privateOriginalLogSHA256": p.logDigest(),
		"usedAsCrashProof": false})
	_ = p.input.Close()
}

func inlineRecoveryHTTPClient() *http.Client {
	return &http.Client{Timeout: 20 * time.Second, Transport: &http.Transport{Proxy: nil,
		DialContext: (&net.Dialer{Timeout: 3 * time.Second}).DialContext, DisableKeepAlives: true,
		ForceAttemptHTTP2: false}, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
}

func (p *inlineRecoveryProcess) receipt(method, path string, body []byte) space.MigrationInlineFileReceipt {
	t := p.session.t
	t.Helper()
	request, err := http.NewRequest(method, p.ready.URL+path, bytes.NewReader(body))
	require.NoError(t, err)
	request.Header.Set("Content-Type", "application/json")
	client := inlineRecoveryHTTPClient()
	defer client.CloseIdleConnections()
	response, err := client.Do(request)
	require.NoError(t, err)
	defer response.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(response.Body, 65537))
	require.NoError(t, err)
	require.LessOrEqual(t, len(raw), 65536)
	require.Equal(t, http.StatusOK, response.StatusCode, string(raw))
	var receipt space.MigrationInlineFileReceipt
	require.NoError(t, json.Unmarshal(raw, &receipt))
	p.session.record("http", map[string]any{"child": p.number, "pid": p.cmd.Process.Pid,
		"method": method, "path": path, "requestSHA256": inlineHTTPHash(body),
		"responseSHA256": inlineHTTPHash(raw), "status": response.StatusCode, "receipt": receipt})
	return receipt
}

func inlineRecoveryIdentity(r space.MigrationInlineFileReceipt) space.MigrationInlineFileReceipt {
	r.Stage = ""
	r.Outcome = ""
	return r
}

func inlineRecoverySame(t *testing.T, original, current space.MigrationInlineFileReceipt, stage, outcome string) {
	t.Helper()
	require.Equal(t, inlineRecoveryIdentity(original), inlineRecoveryIdentity(current), "all reserved identities and source bindings must remain original")
	require.Equal(t, stage, current.Stage)
	require.Equal(t, outcome, current.Outcome)
}

func (p *inlineRecoveryProcess) observe(original space.MigrationInlineFileReceipt, stage string, content []byte) {
	t := p.session.t
	t.Helper()
	frame := p.command(inlineRecoveryCommand{Kind: "observe", Receipt: original})
	require.NotNil(t, frame.Observation)
	o := frame.Observation
	outcome := "prepared"
	count := 0
	if stage == "complete" {
		outcome = "committed"
		count = 1
	}
	inlineRecoverySame(t, original, o.Receipt, stage, outcome)
	require.Equal(t, count, o.Stats.Total)
	require.Len(t, o.Files, count)
	require.Equal(t, count, o.Stats.Durable)
	require.Zero(t, o.Stats.InFlight)
	require.Zero(t, o.Stats.Limited)
	if count == 0 {
		require.Nil(t, o.Info)
		return
	}
	require.NotNil(t, o.Info)
	require.Equal(t, original.FileID, o.Info.FileId)
	require.Equal(t, original.OwnerObjectID, o.Info.ObjectId)
	require.Equal(t, int64(len(content)), o.Info.Size)
	require.Equal(t, "\u05e7\u05d5\u05d1\u05e5 \U0001f9ea.bin", o.Info.Name)
	require.Equal(t, "application/octet-stream", o.Info.Mime)
	require.True(t, o.Info.Inline && o.Info.Cached && o.Info.Durable)
	require.Empty(t, o.Info.RootCid)
	require.Equal(t, content, o.Content)
	require.Equal(t, inlineHTTPHash(content), o.ContentSHA256)
	require.Equal(t, *o.Info, o.Files[0])
}

func (p *inlineRecoveryProcess) input(source string) (string, []byte, []byte, space.MigrationInlineFileReceipt) {
	t := p.session.t
	t.Helper()
	capability := p.ready.Capability
	require.Equal(t, space.PreparedMigrationContract, capability.Contract)
	require.Equal(t, 1, capability.InlineFile)
	require.Equal(t, 4095, capability.MaximumInlineBytes)
	require.Zero(t, capability.File)
	require.False(t, capability.NetworkVerified)
	content := inlineHTTPBytes(4095)
	spec := space.MigrationInlineFileSpec{OwnerObjectID: p.ready.Owner, Name: "\u05e7\u05d5\u05d1\u05e5 \U0001f9ea.bin",
		Mime: "application/octet-stream", Content: content, ContentSHA256: inlineHTTPHash(content)}
	raw, err := json.Marshal(spec)
	require.NoError(t, err)
	intent, body := inlineHTTPRequest(t, capability, source, raw)
	base := "/v1/spaces/" + capability.SpaceID + "/pinkha/migration/intents/" + intent + "/inline-file"
	prepared := p.receipt(http.MethodPut, base+"/prepare", []byte(body))
	require.Equal(t, "file-prepared", prepared.Stage)
	require.Equal(t, "prepared", prepared.Outcome)
	require.Equal(t, intent, prepared.IntentID)
	require.Equal(t, inlineHTTPHash(raw), prepared.SpecSHA256)
	require.Equal(t, spec.ContentSHA256, prepared.ContentSHA256)
	require.Equal(t, int64(len(content)), prepared.Size)
	require.Equal(t, p.ready.Owner, prepared.OwnerObjectID)
	require.Equal(t, capability.StoreID, prepared.StoreID)
	require.Equal(t, capability.AccountID, prepared.AccountID)
	require.Equal(t, capability.SpaceID, prepared.SpaceID)
	require.NotEmpty(t, prepared.ObjectID)
	require.NotEmpty(t, prepared.ChangeID)
	require.NotEmpty(t, prepared.FileID)
	require.Equal(t, []string{prepared.FileID}, prepared.RecordIDs)
	p.session.record("original-input", map[string]any{"sourceSpecification": json.RawMessage(raw),
		"specSHA256": inlineHTTPHash(raw), "prepareJSONSHA256": inlineHTTPHash([]byte(body)),
		"originalReceipt": prepared})
	return base, []byte(body), content, prepared
}

func inlineRecoveryCommit(t *testing.T, r space.MigrationInlineFileReceipt) []byte {
	t.Helper()
	raw, err := json.Marshal(space.MigrationCommit{Contract: r.Contract, StoreID: r.StoreID,
		PlanID: r.PlanID, PlanSHA256: r.PlanSHA256, Fingerprint: r.Fingerprint})
	require.NoError(t, err)
	return raw
}

func TestPreparedInlineFileActualProcessCrashRecovery(t *testing.T) {
	s := inlineRecoveryNew(t)
	first := s.start()
	base, prepare, content, original := first.input("source/file/actual-process-crash")
	commit := inlineRecoveryCommit(t, original)
	first.observe(original, "file-prepared", content)
	first.kill("native-reservation-returned-file-prepared", true)

	second := s.start()
	require.Equal(t, first.ready.Capability, second.ready.Capability)
	require.Equal(t, first.ready.Owner, second.ready.Owner)
	status := second.receipt(http.MethodGet, base, nil)
	inlineRecoverySame(t, original, status, "file-prepared", "prepared")
	reprepared := second.receipt(http.MethodPut, base+"/prepare", prepare)
	require.Equal(t, status, reprepared)
	second.observe(original, "file-prepared", content)
	root := second.receipt(http.MethodPost, base+"/commit", commit)
	inlineRecoverySame(t, original, root, "file-root-committed", "prepared")
	second.observe(original, "file-root-committed", content)
	second.kill("native-root-commit-returned-file-root-committed", true)

	third := s.start()
	require.Equal(t, first.ready.Capability, third.ready.Capability)
	require.Equal(t, first.ready.Owner, third.ready.Owner)
	status = third.receipt(http.MethodGet, base, nil)
	require.Equal(t, root, status)
	reprepared = third.receipt(http.MethodPut, base+"/prepare", prepare)
	require.Equal(t, status, reprepared)
	third.observe(original, "file-root-committed", content)
	complete := third.receipt(http.MethodPost, base+"/commit", commit)
	inlineRecoverySame(t, original, complete, "complete", "committed")
	third.observe(original, "complete", content)
	retried := third.receipt(http.MethodPost, base+"/commit", commit)
	require.Equal(t, complete, retried)
	third.observe(original, "complete", content)
	third.close()
	s.record("accepted", map[string]any{"deliberateSIGKILLs": 2, "distinctOwnedProcesses": 3,
		"reservationAndRootRecovery": true, "originalIntentAndSignedIDsRetained": true,
		"independentNativeRows": 1, "contentSHA256": inlineHTTPHash(content)})
}

func TestPreparedInlineFileActualLostHTTPAcknowledgementRecovery(t *testing.T) {
	s := inlineRecoveryNew(t)
	first := s.start()
	base, prepare, content, original := first.input("source/file/actual-lost-http-ack")
	commit := inlineRecoveryCommit(t, original)
	root := first.receipt(http.MethodPost, base+"/commit", commit)
	inlineRecoverySame(t, original, root, "file-root-committed", "prepared")
	first.observe(original, "file-root-committed", content)
	first.command(inlineRecoveryCommand{Kind: "arm-drop", Receipt: original, Path: base + "/commit",
		RequestSHA256: inlineHTTPHash(commit)})

	var connected, written, firstResponseByte atomic.Bool
	trace := &httptrace.ClientTrace{GotConn: func(httptrace.GotConnInfo) { connected.Store(true) },
		WroteRequest:         func(info httptrace.WroteRequestInfo) { written.Store(info.Err == nil) },
		GotFirstResponseByte: func() { firstResponseByte.Store(true) }}
	request, err := http.NewRequestWithContext(httptrace.WithClientTrace(context.Background(), trace),
		http.MethodPost, first.ready.URL+base+"/commit", bytes.NewReader(commit))
	require.NoError(t, err)
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("X-Pinkha-Recovery-Nonce", s.nonce)
	client := inlineRecoveryHTTPClient()
	response, transportErr := client.Do(request)
	if response != nil {
		_ = response.Body.Close()
	}
	client.CloseIdleConnections()
	s.record("client-transport", map[string]any{"child": first.number, "pid": first.cmd.Process.Pid,
		"connected": connected.Load(), "requestWritten": written.Load(), "firstResponseByte": firstResponseByte.Load(),
		"responsePresent": response != nil, "error": fmt.Sprint(transportErr), "requestSHA256": inlineHTTPHash(commit)})
	require.Nil(t, response, "no HTTP acknowledgement may be received")
	require.Error(t, transportErr)
	require.True(t, errors.Is(transportErr, io.EOF) || errors.Is(transportErr, io.ErrUnexpectedEOF) || errors.Is(transportErr, syscall.ECONNRESET),
		"require actual closed-connection EOF/reset, not a timeout or modeled result")
	require.True(t, connected.Load() && written.Load())
	require.False(t, firstResponseByte.Load())
	dropped := first.receive("dropped", 0)
	s.record("actual-ack-loss", dropped)
	require.NotNil(t, dropped.Drop)
	d := dropped.Drop
	require.Equal(t, inlineHTTPHash(commit), d.RequestSHA256)
	require.Equal(t, http.StatusOK, d.ResponseStatus)
	require.Positive(t, d.ResponseBytes)
	require.Zero(t, d.ForwardedBytes)
	require.Zero(t, d.NetworkBufferedBytes)
	require.Equal(t, 1, d.TargetRequests)
	require.True(t, d.Hijacked && d.ConnectionClosed)
	inlineRecoverySame(t, original, d.Observation.Receipt, "complete", "committed")
	require.Equal(t, 1, d.Observation.Stats.Total)
	require.Len(t, d.Observation.Files, 1)
	require.Equal(t, content, d.Observation.Content)
	first.observe(original, "complete", content)
	first.kill("native-complete-after-actual-client-EOF-before-retry", true)

	second := s.start()
	require.Equal(t, first.ready.Capability, second.ready.Capability)
	require.Equal(t, first.ready.Owner, second.ready.Owner)
	status := second.receipt(http.MethodGet, base, nil)
	require.Equal(t, d.Observation.Receipt, status)
	second.observe(original, "complete", content)
	reprepared := second.receipt(http.MethodPut, base+"/prepare", prepare)
	require.Equal(t, status, reprepared)
	retried := second.receipt(http.MethodPost, base+"/commit", commit)
	require.Equal(t, status, retried)
	second.observe(original, "complete", content)
	second.close()
	s.record("accepted", map[string]any{"deliberateSIGKILLs": 1, "distinctOwnedProcesses": 2,
		"actualClientAcknowledgementLost": true, "serverNativeCommittedBeforeConnectionClose": true,
		"originalIntentAndSignedIDsRetained": true, "independentNativeRows": 1,
		"contentSHA256": inlineHTTPHash(content)})
}

// Keep the identity comparator available to the child without assertion logging.
func inlineRecoveryIdentityEqual(a, b space.MigrationInlineFileReceipt) bool {
	return reflect.DeepEqual(inlineRecoveryIdentity(a), inlineRecoveryIdentity(b))
}
