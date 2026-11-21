package torahops

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
	"github.com/anyproto/any-sync/commonspace/object/accountdata"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/synctree"
	treeresponse "github.com/anyproto/any-sync/commonspace/object/tree/synctree/response"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	"github.com/anyproto/any-sync/commonspace/spacepayloads"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/commonspace/sync/objectsync/objectmessages"
	"github.com/anyproto/any-sync/commonspace/sync/syncdeps"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/stretchr/testify/require"
	"google.golang.org/protobuf/proto"
	"storj.io/drpc/drpcconn"
	"storj.io/drpc/drpcmux"
	"storj.io/drpc/drpcserver"

	"github.com/anyproto/anytype-heart/core/block/editor/storestate"
)

// These fixtures run real native SyncTrees, generated SpaceSync DRPC streaming
// messages and verified encrypted changes over loopback TCP in separate OS
// processes. Only head-advertisement scheduling is suppressed to model offline
// partitions; each explicit pull still uses the upstream request factory,
// response producer, response collector and SyncTree update listener.
// There is no production peer authentication/coordinator or application registry
// in this fixture. Those acceptance gates remain open.
const processEventPrefix = "PINKHA_T2_PROCESS "
const processConfigEnv = "PINKHA_T2_NATIVE_PROCESS_CONFIG"

type nativeFixtureConfig struct {
	Dir         string
	Projection  string
	Space       spacestorage.SpaceStorageCreatePayload
	PeerPrivate []byte
	SignPrivate []byte
	TargetRoots []*treechangeproto.RawTreeChangeWithId
}

type protocolStats struct {
	Requests        atomic.Uint64
	Responses       atomic.Uint64
	Bytes           atomic.Uint64
	Changes         atomic.Uint64
	DroppedHeads    atomic.Uint64
	CounterRequests atomic.Uint64
}

type nativeStats struct {
	PID             int
	TreeChanges     int
	Requests        uint64
	Responses       uint64
	Bytes           uint64
	Changes         uint64
	DroppedHeads    uint64
	CounterRequests uint64
}

type fixtureSyncClient struct {
	synctree.RequestFactory
	address string // test-control address, always loopback
	spaceID string
	stats   *protocolStats
}

func (c *fixtureSyncClient) Broadcast(context.Context, *objectmessages.HeadUpdate) error {
	c.stats.DroppedHeads.Add(1)
	return nil // explicitly partitioned advertisement channel; full sync is real
}

func (c *fixtureSyncClient) QueueRequest(context.Context, syncdeps.Request) error {
	return errors.New("fixture schedules both full-sync directions explicitly")
}

func (c *fixtureSyncClient) SendTreeRequest(ctx context.Context, req syncdeps.Request, collector syncdeps.ResponseCollector) error {
	host, _, err := net.SplitHostPort(c.address)
	if err != nil || !net.ParseIP(host).IsLoopback() {
		return errors.New("fixture refuses non-loopback transport")
	}
	message, err := req.(*objectmessages.Request).Proto()
	if err != nil {
		return err
	}
	connection, err := (&net.Dialer{}).DialContext(ctx, "tcp", c.address)
	if err != nil {
		return err
	}
	conn := drpcconn.New(connection)
	defer conn.Close()
	stream, err := spacesyncproto.NewDRPCSpaceSyncClient(conn).ObjectSyncRequestStream(ctx, message.(*spacesyncproto.ObjectSyncMessage))
	if err != nil {
		return err
	}
	defer stream.Close()
	c.stats.Requests.Add(1)
	for {
		message, err := stream.Recv()
		if errors.Is(err, io.EOF) {
			return nil
		}
		if err != nil {
			return err
		}
		if message.SpaceId != c.spaceID || message.ObjectId != req.ObjectId() {
			return ErrInvalid
		}
		response := collector.NewResponse().(*treeresponse.Response)
		if err = response.SetProtoMessage(message); err != nil {
			return err
		}
		c.stats.Responses.Add(1)
		c.stats.Bytes.Add(uint64(len(message.Payload)))
		c.stats.Changes.Add(uint64(len(response.Changes)))
		if err = collector.CollectResponse(ctx, req.PeerId(), req.ObjectId(), response); err != nil {
			return err
		}
	}
}

type fixtureStatus struct{}

func (fixtureStatus) Init(*app.App) error                       { return nil }
func (fixtureStatus) Name() string                              { return "pinkha.t2.fixture-status" }
func (fixtureStatus) HeadsChange(string, []string)              {}
func (fixtureStatus) HeadsReceive(string, string, []string)     {}
func (fixtureStatus) ObjectReceive(string, string, []string)    {}
func (fixtureStatus) HeadsApply(string, string, []string, bool) {}
func (fixtureStatus) UpdateQueueSize(uint64, int, bool)         {}

type fixtureServer struct {
	spacesyncproto.DRPCSpaceSyncUnimplementedServer
	tree    synctree.SyncTree
	spaceID string
	stats   *protocolStats
	tamper  atomic.Bool
}

func (s *fixtureServer) ObjectSyncRequestStream(message *spacesyncproto.ObjectSyncMessage, stream spacesyncproto.DRPCSpaceSync_ObjectSyncRequestStreamStream) error {
	if message.SpaceId != s.spaceID || message.ObjectId != s.tree.Id() {
		return ErrInvalid
	}
	request := objectmessages.NewByteRequest("loopback-fixture-peer", message.SpaceId, message.ObjectId, message.Payload)
	counter, err := s.tree.HandleStreamRequest(stream.Context(), request, fixtureStatus{}, func(response proto.Message) error {
		message := response.(*spacesyncproto.ObjectSyncMessage)
		if s.tamper.Load() {
			message = proto.Clone(message).(*spacesyncproto.ObjectSyncMessage)
			wrapped := &treechangeproto.TreeSyncMessage{}
			if err := wrapped.UnmarshalVT(message.Payload); err != nil {
				return err
			}
			changes := wrapped.GetContent().GetFullSyncResponse().Changes
			if len(changes) != 0 {
				last := len(changes[0].RawChange) - 1
				changes[0].RawChange[last] ^= 1 // real wire corruption, original CID retained
				payload, marshalErr := wrapped.MarshalVT()
				if marshalErr != nil {
					return marshalErr
				}
				message.Payload = payload
			}
		}
		return stream.Send(message)
	})
	if counter != nil {
		s.stats.CounterRequests.Add(1)
	}
	return err
}

type nativeFixture struct {
	config       nativeFixtureConfig
	keys         *accountdata.AccountKeys
	spaceDB      anystore.DB
	projectionDB anystore.DB
	space        spacestorage.SpaceStorage
	acl          list.AclList
	tree         synctree.SyncTree
	host         *NativeHost
	client       *fixtureSyncClient
	server       *fixtureServer
	listener     net.Listener
	cancel       context.CancelFunc
	serverDone   chan error
}

func openNativeFixture(ctx context.Context, config nativeFixtureConfig) (_ *nativeFixture, err error) {
	f := &nativeFixture{config: config}
	defer func() {
		if err != nil {
			_ = f.Close()
		}
	}()
	peerKey, err := crypto.UnmarshalEd25519PrivateKeyProto(config.PeerPrivate)
	if err != nil {
		return nil, err
	}
	signKey, err := crypto.UnmarshalEd25519PrivateKeyProto(config.SignPrivate)
	if err != nil {
		return nil, err
	}
	f.keys = accountdata.New(peerKey, signKey)
	if err = spacepayloads.ValidateSpaceStorageCreatePayload(config.Space); err != nil {
		return nil, err
	}
	spacePath := filepath.Join(config.Dir, "space.db")
	_, statErr := os.Stat(spacePath)
	f.spaceDB, err = anystore.Open(ctx, spacePath, &anystore.Config{ReadConnections: 1})
	if err != nil {
		return nil, err
	}
	if errors.Is(statErr, os.ErrNotExist) {
		f.space, err = spacestorage.Create(ctx, f.spaceDB, config.Space)
	} else {
		f.space, err = spacestorage.New(ctx, config.Space.SpaceHeaderWithId.Id, f.spaceDB)
	}
	if err != nil {
		return nil, err
	}
	aclStorage, err := f.space.AclStorage()
	if err != nil {
		return nil, err
	}
	// This is a real signed owner ACL root. Full validation verifies its contents;
	// no network acceptor records are fabricated or claimed in this fixture.
	f.acl, err = list.BuildAclListWithIdentity(f.keys, aclStorage, recordverifier.NewValidateFull())
	if err != nil {
		return nil, err
	}
	for _, target := range config.TargetRoots {
		_, err = f.space.TreeStorage(ctx, target.Id)
		if errors.Is(err, treestorage.ErrUnknownTreeId) {
			_, err = f.space.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: target, Heads: []string{target.Id}})
		}
		if err != nil {
			return nil, err
		}
	}
	root, err := NativeRoot(f.space.Id())
	if err != nil {
		return nil, err
	}
	stats := &protocolStats{}
	f.client = &fixtureSyncClient{RequestFactory: synctree.NewRequestFactory(f.space.Id()), spaceID: f.space.Id(), stats: stats}
	deps := synctree.BuildDeps{SpaceId: f.space.Id(), SyncClient: f.client, AclList: f.acl,
		SpaceStorage: f.space, OnClose: func(string) {}, SyncStatus: fixtureStatus{}, BuildObjectTree: NativeTreeBuilder(f.space.Id())}
	_, err = f.space.TreeStorage(ctx, root.Id)
	if errors.Is(err, treestorage.ErrUnknownTreeId) {
		f.tree, err = synctree.PutSyncTree(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root, Heads: []string{root.Id}}, deps)
	} else if err == nil {
		f.tree, err = synctree.BuildSyncTreeOrGetRemote(ctx, root.Id, deps)
	}
	if err != nil {
		return nil, err
	}
	name := config.Projection
	if name == "" {
		name = "projection.db"
	}
	f.projectionDB, err = anystore.Open(ctx, filepath.Join(config.Dir, name), &anystore.Config{ReadConnections: 1})
	if err != nil {
		return nil, err
	}
	f.host, err = OpenNativeHost(ctx, f.projectionDB, f.space.Id(), f.tree, signKey, f.acquireTarget)
	if err != nil {
		return nil, err
	}
	f.server = &fixtureServer{tree: f.tree, spaceID: f.space.Id(), stats: stats}
	mux := drpcmux.New()
	if err = spacesyncproto.DRPCRegisterSpaceSync(mux, f.server); err != nil {
		return nil, err
	}
	f.listener, err = net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return nil, err
	}
	serverCtx, cancel := context.WithCancel(context.Background())
	f.cancel = cancel
	f.serverDone = make(chan error, 1)
	go func() { f.serverDone <- drpcserver.New(mux).Serve(serverCtx, f.listener) }()
	return f, nil
}

// This transport fixture has immutable disposable target roots. Full target
// lifecycle exclusion is exercised separately by the native registry fixtures.
func (f *nativeFixture) acquireTarget(ctx context.Context, target Target) (func(), error) {
	if err := f.validateTarget(ctx, target); err != nil {
		return nil, err
	}
	return func() {}, nil
}

func (f *nativeFixture) validateTarget(ctx context.Context, target Target) error {
	if target.BlockID != "" {
		return errors.New("fixture only validates native object roots; block contract is not bound")
	}
	allowed := false
	for _, root := range f.config.TargetRoots {
		allowed = allowed || target.ObjectID == root.Id
	}
	if !allowed {
		return ErrInvalid
	}
	entry, err := f.space.HeadStorage().GetEntry(ctx, target.ObjectID)
	if err != nil {
		return err
	}
	if entry.DeletedStatus != headstorage.DeletedStatusNotDeleted {
		return ErrInvalid
	}
	return nil
}

func (f *nativeFixture) Close() error {
	if f.cancel != nil {
		f.cancel()
	}
	if f.listener != nil {
		_ = f.listener.Close()
	}
	if f.serverDone != nil {
		<-f.serverDone
		f.serverDone = nil
	}
	var err error
	if f.tree != nil {
		err = errors.Join(err, f.tree.Close())
		f.tree = nil
	}
	if f.projectionDB != nil {
		err = errors.Join(err, f.projectionDB.Close())
		f.projectionDB = nil
	}
	if f.spaceDB != nil {
		err = errors.Join(err, f.spaceDB.Close())
		f.spaceDB = nil
	}
	return err
}

func (f *nativeFixture) stats() nativeStats {
	f.tree.Lock()
	count := f.tree.Len()
	f.tree.Unlock()
	s := f.client.stats
	return nativeStats{PID: os.Getpid(), TreeChanges: count, Requests: s.Requests.Load(), Responses: s.Responses.Load(),
		Bytes: s.Bytes.Load(), Changes: s.Changes.Load(), DroppedHeads: s.DroppedHeads.Load(), CounterRequests: s.CounterRequests.Load()}
}

type processCommand struct {
	Action    string
	Operation Operation
	Target    Target
	Address   string
	PeerID    string
	Tamper    bool
}

type processEvent struct {
	Error    string
	PID      int
	PeerID   string
	Address  string
	Append   NativeAppendResult
	Snapshot NativeSnapshot
	Stats    nativeStats
	Receipts []Receipt
}

func emitProcessEvent(event processEvent) {
	data, err := json.Marshal(event)
	if err != nil {
		panic(err)
	}
	fmt.Println(processEventPrefix + string(data))
}

func TestNativeTreeProcessHelper(t *testing.T) {
	path := os.Getenv(processConfigEnv)
	if path == "" {
		t.Skip("only executed by the separate-process transport test")
	}
	data, err := os.ReadFile(path)
	require.NoError(t, err)
	var config nativeFixtureConfig
	require.NoError(t, json.Unmarshal(data, &config))
	f, err := openNativeFixture(context.Background(), config)
	require.NoError(t, err)
	emitProcessEvent(processEvent{PID: os.Getpid(), PeerID: f.keys.PeerId, Address: f.listener.Addr().String()})
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 4096), 1024*1024)
	for scanner.Scan() {
		var command processCommand
		event := processEvent{}
		err := json.Unmarshal(scanner.Bytes(), &command)
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		if err == nil {
			switch command.Action {
			case "append", "append-then-exit":
				event.Append, err = f.host.Append(ctx, command.Operation)
				if err == nil && command.Action == "append-then-exit" {
					os.Exit(17)
				}
			case "query":
				event.Snapshot, err = f.host.ReadTarget(ctx, command.Target, 10000)
			case "pull":
				f.client.address = command.Address
				f.tree.Lock()
				request, requestErr := f.client.CreateFullSyncRequest(command.PeerID, f.tree)
				f.tree.Unlock()
				err = requestErr
				if err == nil {
					err = f.client.SendTreeRequest(ctx, request, f.tree.ResponseCollector())
				}
			case "tamper":
				f.server.tamper.Store(command.Tamper)
			case "receipts":
				claim, _, claimErr := makeClaim(command.Operation)
				err = claimErr
				if err == nil {
					event.Receipts, err = f.host.store.Receipts(ctx, claim.ID)
				}
			case "stats":
			case "stop":
				cancel()
				require.NoError(t, f.Close())
				return
			default:
				err = ErrInvalid
			}
		}
		cancel()
		if err != nil {
			event.Error = err.Error()
		}
		event.Stats = f.stats()
		emitProcessEvent(event)
	}
	require.NoError(t, scanner.Err())
	require.NoError(t, f.Close())
}

type nativeProcess struct {
	command *exec.Cmd
	input   io.WriteCloser
	events  chan processEvent
	done    chan error
	ready   processEvent
	logs    bytes.Buffer
	output  strings.Builder
	stopped bool
}

func startNativeProcess(t *testing.T, config nativeFixtureConfig) *nativeProcess {
	t.Helper()
	path := filepath.Join(config.Dir, "fixture-config.json")
	data, err := json.Marshal(config)
	require.NoError(t, err)
	require.NoError(t, os.WriteFile(path, data, 0600)) // disposable fixture keys; never published
	command := exec.Command(os.Args[0], "-test.run=^TestNativeTreeProcessHelper$", "-test.timeout=90s")
	command.Env = append(os.Environ(), processConfigEnv+"="+path)
	p := &nativeProcess{command: command, events: make(chan processEvent, 2), done: make(chan error, 1)}
	command.Stderr = &p.logs
	p.input, err = command.StdinPipe()
	require.NoError(t, err)
	output, err := command.StdoutPipe()
	require.NoError(t, err)
	require.NoError(t, command.Start())
	go func() {
		scanner := bufio.NewScanner(output)
		scanner.Buffer(make([]byte, 4096), 2*1024*1024)
		for scanner.Scan() {
			line := scanner.Text()
			if !strings.HasPrefix(line, processEventPrefix) {
				p.output.WriteString(line + "\n")
				continue
			}
			var event processEvent
			if json.Unmarshal([]byte(strings.TrimPrefix(line, processEventPrefix)), &event) == nil {
				p.events <- event
			}
		}
		close(p.events)
	}()
	go func() { p.done <- command.Wait() }()
	t.Cleanup(func() {
		if !p.stopped {
			_ = command.Process.Kill()
			<-p.done
			p.stopped = true
		}
	})
	p.ready = p.receive(t)
	require.NotZero(t, p.ready.PID)
	return p
}

func (p *nativeProcess) receive(t *testing.T) processEvent {
	t.Helper()
	select {
	case event, ok := <-p.events:
		if !ok {
			t.Fatalf("native child exited before response:\n%s", p.output.String())
		}
		return event
	case <-time.After(30 * time.Second):
		t.Fatal("native child response timed out")
		return processEvent{}
	}
}

func (p *nativeProcess) issue(t *testing.T, command processCommand) processEvent {
	t.Helper()
	require.NoError(t, json.NewEncoder(p.input).Encode(command))
	return p.receive(t)
}

func (p *nativeProcess) ok(t *testing.T, command processCommand) processEvent {
	t.Helper()
	event := p.issue(t, command)
	require.Empty(t, event.Error)
	return event
}

func (p *nativeProcess) stop(t *testing.T, exitCode int) {
	t.Helper()
	if exitCode == 0 {
		require.NoError(t, json.NewEncoder(p.input).Encode(processCommand{Action: "stop"}))
	}
	select {
	case err := <-p.done:
		p.stopped = true
		if exitCode == 0 {
			require.NoError(t, err, p.logs.String())
		} else {
			var exited *exec.ExitError
			require.ErrorAs(t, err, &exited)
			require.Equal(t, exitCode, exited.ExitCode())
		}
	case <-time.After(30 * time.Second):
		t.Fatal("native child did not stop")
	}
}

func makeNativeConfigs(t *testing.T) (nativeFixtureConfig, nativeFixtureConfig, string) {
	t.Helper()
	keys, err := accountdata.NewRandom()
	require.NoError(t, err)
	master, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	metadata, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	space, err := spacepayloads.StoragePayloadForSpaceCreate(spacepayloads.SpaceCreatePayload{
		SigningKey: keys.SignKey, SpaceType: "space", ReplicationKey: 10, MasterKey: master,
		ReadKey: crypto.NewAES(), MetadataKey: metadata, Metadata: []byte("disposable T2 native fixture"),
	})
	require.NoError(t, err)
	// Independent device peer keys; same account identity as an actual second
	// device of one account. This fixture does not claim multi-user ACL sync.
	peerB, _, err := crypto.GenerateRandomEd25519KeyPair()
	require.NoError(t, err)
	peerABytes, err := keys.PeerKey.Marshall()
	require.NoError(t, err)
	peerBBytes, err := peerB.Marshall()
	require.NoError(t, err)
	signBytes, err := keys.SignKey.Marshall()
	require.NoError(t, err)
	var targets []*treechangeproto.RawTreeChangeWithId
	for i := 0; i < 6; i++ {
		_, root, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), nil).BuildRoot(objecttree.InitialContent{
			PrivKey: keys.SignKey, AclHeadId: space.AclWithId.Id, SpaceId: space.SpaceHeaderWithId.Id,
			ChangeType: "pinkha.disposable.native-target", Seed: []byte(fmt.Sprintf("target-%d", i)),
		})
		require.NoError(t, err)
		targets = append(targets, root)
	}
	a := nativeFixtureConfig{Dir: t.TempDir(), Space: space, PeerPrivate: peerABytes, SignPrivate: signBytes, TargetRoots: targets}
	b := a
	b.Dir, b.PeerPrivate = t.TempDir(), peerBBytes
	return a, b, keys.SignKey.GetPublic().Account()
}

func TestNativeTwoProcessTreeSync(t *testing.T) {
	aConfig, bConfig, author := makeNativeConfigs(t)
	a, b := startNativeProcess(t, aConfig), startNativeProcess(t, bConfig)
	require.NotEqual(t, a.ready.PID, b.ready.PID)
	require.NotEqual(t, a.ready.PeerID, b.ready.PeerID)
	require.NotEqual(t, aConfig.Dir, bConfig.Dir)
	t.Logf("transport=generated ObjectSyncRequestStream/TreeSync over loopback TCP; clients=%d,%d; independent native SQLite and projection databases; no shared store", a.ready.PID, b.ready.PID)
	operation := func(id int, target int, body string) Operation {
		return Operation{Version: Version, SpaceID: aConfig.Space.SpaceHeaderWithId.Id, OperationID: fmt.Sprintf("%032x", id),
			AuthorID: author, Kind: Add, Target: Target{ObjectID: aConfig.TargetRoots[target].Id},
			Source: Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte(body)}
	}
	pull := func(dst, src *nativeProcess) processEvent {
		return dst.ok(t, processCommand{Action: "pull", Address: src.ready.Address, PeerID: src.ready.PeerID})
	}
	syncBoth := func() { pull(a, b); pull(b, a) }
	query := func(p *nativeProcess, target int) NativeSnapshot {
		return p.ok(t, processCommand{Action: "query", Target: Target{ObjectID: aConfig.TargetRoots[target].Id}}).Snapshot
	}
	appendOp := func(p *nativeProcess, op Operation) NativeAppendResult {
		return p.ok(t, processCommand{Action: "append", Operation: op}).Append
	}

	// AB01 native transport subset: disconnected writes, union, replay, both restarts.
	x, y := operation(1, 0, "offline A"), operation(2, 0, "offline B")
	require.Equal(t, Created, appendOp(a, x).Disposition)
	require.Equal(t, Created, appendOp(b, y).Disposition)
	require.Len(t, query(a, 0).Projection.Live, 1)
	require.Len(t, query(b, 0).Projection.Live, 1)
	syncBoth()
	left, right := query(a, 0), query(b, 0)
	require.Equal(t, left.Projection, right.Projection)
	require.Len(t, left.Projection.Live, 2)
	require.Equal(t, left.Heads, right.Heads)
	require.NotZero(t, left.AppliedSeq)
	syncBoth() // duplicate protocol delivery does not duplicate immutable claims
	require.Equal(t, left.Projection, query(a, 0).Projection)
	oldA, oldB := a.ready.PID, b.ready.PID
	a.stop(t, 0)
	b.stop(t, 0)
	a, b = startNativeProcess(t, aConfig), startNativeProcess(t, bConfig)
	require.NotEqual(t, oldA, a.ready.PID)
	require.NotEqual(t, oldB, b.ready.PID)
	require.Equal(t, left.Projection, query(a, 0).Projection)
	require.Equal(t, left.Projection, query(b, 0).Projection)
	t.Log("AB01 transport subset: offline union and independent process restarts passed")

	// AB03: offline reuse retains both versions; a later ordered mismatch cannot overwrite.
	c1, c2 := operation(3, 1, "variant A"), operation(3, 1, "variant B")
	appendOp(a, c1)
	appendOp(b, c2)
	syncBoth()
	conflictA, conflictB := query(a, 1), query(b, 1)
	require.Equal(t, conflictA.Projection, conflictB.Projection)
	require.Empty(t, conflictA.Projection.Live)
	require.Len(t, conflictA.Projection.Conflicts, 1)
	require.Len(t, conflictA.Projection.Conflicts[0].Claims, 2)
	ordered := c1
	ordered.Payload = []byte("ordered overwrite rejected")
	before := a.ok(t, processCommand{Action: "stats"}).Stats.TreeChanges
	require.Equal(t, CollisionDifferentPayload, appendOp(a, ordered).Disposition)
	retry := appendOp(a, c1)
	require.Equal(t, AlreadyExistsSamePayload, retry.Disposition)
	require.True(t, retry.Resolution.Conflict)
	require.Equal(t, before, a.ok(t, processCommand{Action: "stats"}).Stats.TreeChanges)
	t.Log("AB03 transport subset: concurrent variants retained, ordered collision rejected, no silent winner")

	// AB04: a remove observes only the initial claim; a disconnected add survives.
	initial := operation(4, 2, "observed initial")
	initialID := appendOp(a, initial).ClaimID
	syncBoth()
	remove := operation(5, 2, "")
	remove.Kind = Remove
	remove.Source = Source{}
	remove.Observed = []string{initialID}
	appendOp(a, remove)
	unseen := operation(6, 2, "unseen add survives")
	appendOp(b, unseen)
	syncBoth()
	removed := query(a, 2)
	require.Equal(t, removed.Projection, query(b, 2).Projection)
	require.Len(t, removed.Projection.Live, 1)
	require.Equal(t, unseen.OperationID, removed.Projection.Live[0].Operation.OperationID)

	// AB05: two offline replacements of the same predecessor both remain live.
	predecessor := operation(7, 3, "predecessor")
	predecessorID := appendOp(a, predecessor).ClaimID
	syncBoth()
	r1, r2 := operation(8, 3, "replacement A"), operation(9, 3, "replacement B")
	r1.Kind, r2.Kind = Replace, Replace
	r1.Observed, r2.Observed = []string{predecessorID}, []string{predecessorID}
	appendOp(a, r1)
	appendOp(b, r2)
	syncBoth()
	replacements := query(a, 3)
	require.Equal(t, replacements.Projection, query(b, 3).Projection)
	require.Len(t, replacements.Projection.Live, 2)
	t.Log("AB04/AB05 transport subsets: observed remove preserves unseen add; concurrent replacements retained")

	// AB02: child exits after native + projection commit and before replying.
	lost := operation(10, 4, "committed response was lost")
	require.NoError(t, json.NewEncoder(a.input).Encode(processCommand{Action: "append-then-exit", Operation: lost}))
	a.stop(t, 17)
	a = startNativeProcess(t, aConfig)
	count := a.ok(t, processCommand{Action: "stats"}).Stats.TreeChanges
	require.Equal(t, AlreadyExistsSamePayload, appendOp(a, lost).Disposition)
	require.Equal(t, count, a.ok(t, processCommand{Action: "stats"}).Stats.TreeChanges)
	syncBoth()
	require.Equal(t, AlreadyExistsSamePayload, appendOp(b, lost).Disposition)
	for _, process := range []*nativeProcess{a, b} {
		event := process.ok(t, processCommand{Action: "receipts", Operation: lost})
		require.Len(t, event.Receipts, 1)
		require.Equal(t, author, event.Receipts[0].Creator)
		require.Equal(t, aConfig.Space.AclWithId.Id, event.Receipts[0].ACLHeadID)
	}
	t.Log("AB02 transport subset: post-commit process exit, retry on both clients, one native provenance receipt")

	// Wire corruption must be rejected by the real native verifier.
	corruptTarget := operation(11, 5, "verified ciphertext only")
	appendOp(a, corruptTarget)
	a.ok(t, processCommand{Action: "tamper", Tamper: true})
	corrupt := b.issue(t, processCommand{Action: "pull", Address: a.ready.Address, PeerID: a.ready.PeerID})
	require.NotEmpty(t, corrupt.Error)
	require.Empty(t, query(b, 5).Projection.Live)
	a.ok(t, processCommand{Action: "tamper", Tamper: false})
	pull(b, a)
	require.Len(t, query(b, 5).Projection.Live, 1)
	t.Logf("corrupted native wire rejected: %s", corrupt.Error)

	// Rebuild into a new projection DB from the signed durable tree alone.
	previous := query(a, 3)
	a.stop(t, 0)
	aConfig.Projection = "projection-rebuilt.db"
	a = startNativeProcess(t, aConfig)
	rebuilt := query(a, 3)
	require.Equal(t, previous.Projection, rebuilt.Projection)
	require.Equal(t, previous.Heads, rebuilt.Heads)
	statsA, statsB := a.ok(t, processCommand{Action: "stats"}).Stats, b.ok(t, processCommand{Action: "stats"}).Stats
	require.Greater(t, statsB.Requests, uint64(0))
	require.Greater(t, statsB.Bytes, uint64(0))
	require.Greater(t, statsB.Changes, uint64(0))
	t.Logf("native proof: projection rebuilt from signed history; final change counts A=%d B=%d; B DRPC requests=%d responses=%d raw bytes=%d signed changes received=%d", statsA.TreeChanges, statsB.TreeChanges, statsB.Requests, statsB.Responses, statsB.Bytes, statsB.Changes)
	a.stop(t, 0)
	b.stop(t, 0)
}

func TestNativeHostRejectsUnboundAuthorityAndInvalidHistory(t *testing.T) {
	config, _, author := makeNativeConfigs(t)
	f, err := openNativeFixture(context.Background(), config)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, f.Close()) })
	op := Operation{Version: Version, SpaceID: config.Space.SpaceHeaderWithId.Id, OperationID: fmt.Sprintf("%032x", 1),
		AuthorID: author, Kind: Add, Target: Target{ObjectID: config.TargetRoots[0].Id},
		Source: Source{ProviderID: "fixture", CanonicalRef: "fixture:1"}, Payload: []byte("protected operation")}
	before := f.stats().TreeChanges
	for _, test := range []string{"caller author", "foreign space", "missing target", "unbound block", "cancelled"} {
		t.Run(test, func(t *testing.T) {
			bad := op
			ctx := context.Background()
			switch test {
			case "caller author":
				bad.AuthorID = "forged-account"
			case "foreign space":
				bad.SpaceID = "foreign-space"
			case "missing target":
				bad.Target.ObjectID = "missing-native-root"
			case "unbound block":
				bad.Target.BlockID = "unverified-block"
			case "cancelled":
				cancelled, cancel := context.WithCancel(ctx)
				cancel()
				ctx = cancelled
			}
			_, err := f.host.Append(ctx, bad)
			require.Error(t, err)
			require.Equal(t, before, f.stats().TreeChanges)
		})
	}
	t.Run("native ACL rejects other writer", func(t *testing.T) {
		outsider, _, err := crypto.GenerateRandomEd25519KeyPair()
		require.NoError(t, err)
		oldKey := f.host.key
		f.host.key = outsider
		defer func() { f.host.key = oldKey }()
		bad := op
		bad.AuthorID = outsider.GetPublic().Account()
		_, err = f.host.Append(context.Background(), bad)
		require.ErrorIs(t, err, list.ErrInsufficientPermissions)
		require.Equal(t, before, f.stats().TreeChanges)
	})
	for _, test := range []string{"plaintext", "forged payload author", "snapshot", "foreign collection"} {
		t.Run(test, func(t *testing.T) {
			bad := op
			if test == "forged payload author" {
				bad.AuthorID = "forged-account"
			}
			claim, wire, err := makeClaim(bad)
			require.NoError(t, err)
			build := &storestate.Builder{}
			collection := CollectionName
			if test == "foreign collection" {
				collection = "unregistered-collection"
			}
			require.NoError(t, build.Create(collection, claim.ID, string(wire)))
			data, err := build.StoreChange.Marshal()
			require.NoError(t, err)
			f.tree.Lock()
			ctx, _, guardErr := nativeCommitContext(context.Background(), f.tree, f.keys.SignKey.GetPublic(), func() {})
			if guardErr == nil {
				_, err = f.tree.AddContent(ctx, objecttree.SignableChangeContent{Data: data, Key: f.keys.SignKey, ShouldBeEncrypted: test != "plaintext", IsSnapshot: test == "snapshot"})
			}
			f.tree.Unlock()
			require.NoError(t, guardErr)
			require.Error(t, err)
			require.NotErrorIs(t, err, ErrNativeCommitGuard)
			require.Equal(t, before, f.stats().TreeChanges)
		})
	}
	valid, err := f.host.Append(context.Background(), op)
	require.NoError(t, err)
	require.NotEmpty(t, valid.ChangeID)
	f.tree.Lock()
	stored, err := f.tree.Storage().Get(context.Background(), valid.ChangeID)
	f.tree.Unlock()
	require.NoError(t, err)
	decoded, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), f.tree.Header()).Unmarshall(stored.RawTreeChangeWithId(), true)
	require.NoError(t, err)
	require.NotEmpty(t, decoded.ReadKeyId)
	require.NotEmpty(t, decoded.Signature)
	require.False(t, bytes.Contains(stored.RawChange, op.Payload))
	require.True(t, slices.Equal([]string{f.tree.Id()}, decoded.PreviousIds))
	other, err := NativeRoot(op.SpaceID + "-other")
	require.NoError(t, err)
	require.NotEqual(t, f.tree.Id(), other.Id)
}
