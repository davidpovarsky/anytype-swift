"""Prepare an isolated lifetime unit closure, without running Go or any test.

The two new product files and selected original lifecycle functions are copied
exactly. Processor Execute, dependency construction, app components, wallet and
account-directory lease are explicit controlled fixtures. They are not native
execution or evidence of account, storage, importer, schema, body or ACK success.
"""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]
ROOT = HERE.parent
MODULE = HERE / "module"
MODULE.mkdir(exist_ok=False)
whole_files = []
fragments = []


def write(relative, content):
    path = MODULE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode())


def actual(source, relative, kind="product"):
    raw = source.read_bytes()
    path = MODULE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    whole_files.append(dict(source=str(source.relative_to(WORK)), compiled_path=relative,
                           bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), kind=kind))


def fragment(source, start, end):
    raw = source.read_bytes()
    text = raw.decode()
    assert text.count(start) == 1, (str(source), start)
    selected = text[text.index(start):]
    if end:
        assert selected.count(end) == 1, (str(source), end)
        selected = selected[:selected.index(end)]
    encoded = selected.encode()
    fragments.append(dict(source=str(source.relative_to(WORK)), source_bytes=len(raw),
                          source_sha256=hashlib.sha256(raw).hexdigest(), start=start, end=end,
                          bytes=len(encoded), fragment_sha256=hashlib.sha256(encoded).hexdigest()))
    return selected


write("go.mod", """module github.com/anyproto/anytype-heart
go 1.25.0
require github.com/anyproto/any-sync v0.0.0
replace github.com/anyproto/any-sync => ./fixture-modules/any-sync
""")
write("fixture-modules/any-sync/go.mod", "module github.com/anyproto/any-sync\ngo 1.25.0\n")
write("fixture-modules/any-sync/app/fixture.go", """package app
// Explicit immutable component lookup fixture; no any-sync initialization/run.
type App struct { Components map[string]any }
func (a *App) Component(name string) any { return a.Components[name] }
""")
write("core/wallet/fixture.go", """package wallet
const CName = "wallet"
type PublicKey struct { AccountID string }
func (p PublicKey) Account() string { return p.AccountID }
type PrivateKey struct { AccountID string }
func (p PrivateKey) GetPublic() PublicKey { return PublicKey{p.AccountID} }
type Wallet interface { GetAccountPrivkey() PrivateKey; RootPath() string }
type Fixture struct { AccountID, Root string }
func (w *Fixture) GetAccountPrivkey() PrivateKey { return PrivateKey{w.AccountID} }
func (w *Fixture) RootPath() string { return w.Root }
""")
write("core/application/accountdirlock/fixture.go", """package accountdirlock
// In-memory lease ABI fixture. No filesystem lock, acquisition or erasure.
type Lease struct { Root, AccountID string; IsUsable bool; Releases int; ReleaseError error }
func (l *Lease) Matches(root, account string) bool { return l.Root == root && l.AccountID == account }
func (l *Lease) Usable() bool { return l.IsUsable }
func (l *Lease) Release() error { l.Releases++; return l.ReleaseError }
""")
write("pb/fixture.go", """package pb
type RpcObjectImportRequest struct { SpaceId string }
type RpcAccountStopRequest struct { RemoveData bool }
""")
write("core/domain/objectorigin/fixture.go", "package objectorigin\ntype ObjectOrigin struct{}\n")
write("core/block/process/fixture.go", "package process\ntype Progress interface{}\n")
write("pkg/lib/pb/model/fixture.go", "package model\ntype BlockContentWidgetLayout int32\n")
write("core/files/fileuploader/fixture.go", "package fileuploader\ntype OwnedUpload struct{}\n")
write("core/pushnotification/fixture.go", """package pushnotification
import "context"
const CName = "pushnotification"
type Service interface { RevokeToken(context.Context) error }
""")
write("util/anyerror/fixture.go", "package anyerror\nfunc CleanupError(err error) error { return err }\n")

actual(ROOT / "candidate/native/core/block/import/owned_import_operation.go", "core/block/import/owned_import_operation.go")
actual(ROOT / "candidate/native/core/application/owned_import_admission.go", "core/application/owned_import_admission.go")
actual(WORK / "native-import-request-compat/candidate/native/core/block/import/mapping_observation.go",
       "core/block/import/mapping_observation.go", "unchanged_prior_product")
types = fragment(WORK / "native-import-request-compat/candidate/native/core/block/import/types.go",
                 "type ImportRequest struct {", "\ntype Dependencies struct {")
write("core/block/import/actual_types.go", """package importer
import "github.com/anyproto/anytype-heart/pb"
import "github.com/anyproto/anytype-heart/core/domain/objectorigin"
import "github.com/anyproto/anytype-heart/core/block/process"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
""" + types)
files_source = WORK / "native-owned-import-audit/import-layer/candidate/native/core/block/import/owned_import_files.go"
owned_types = fragment(files_source, "type ownedImportFileResult struct {", "\nfunc (o *ownedImportExecution) beginRun()")
owned_constructor = fragment(files_source, "func newOwnedImportExecution(", "\nfunc (o *ownedImportExecution) beginFile(")
write("core/block/import/actual_owned_context.go", """package importer
import "context"
import "sync"
import "github.com/anyproto/anytype-heart/core/files/fileuploader"
""" + owned_types + "\n" + owned_constructor)
write("core/block/import/fixture.go", """package importer
import "context"
import "errors"
import "sync"
import "sync/atomic"
import "github.com/anyproto/any-sync/app"

// Explicit processor/constructor fixture. Execute is held at a controlled
// callback, then returns one predeclared response. It runs no native importer,
// converter, worker, finalizer, upload, storage, schema or account operation.
const FixtureComponentName = "fixture.import-lifetime"
type FixtureExecution struct {
 Entered chan context.Context
 Release chan struct{}
 release sync.Once
 ExecuteCalls atomic.Int32
 Response *ImportResponse
 EnterHook func(context.Context)
 Files []OwnedImportFileObservation
 MutateTarget string
}
func NewFixtureExecution() *FixtureExecution {
 return &FixtureExecution{Entered:make(chan context.Context,1), Release:make(chan struct{}), Response:&ImportResponse{ProcessId:"fixture-process",RootCollectionId:"fixture-root",ObjectsCount:2}}
}
func (f *FixtureExecution) Finish() { f.release.Do(func(){close(f.Release)}) }
type FixtureController struct {
 mu sync.Mutex
 Plans []*FixtureExecution
 PrepareCalls int
 PreparedContexts []context.Context
 PrepareError error
}
func (f *FixtureController) Calls() int { f.mu.Lock(); defer f.mu.Unlock(); return f.PrepareCalls }
type importProcessor struct { request *ImportRequest; owned *ownedImportExecution; execution *FixtureExecution }
func newOwnedImportProcessor(a *app.App, owned *ownedImportExecution, request *ImportRequest) (*importProcessor,error) {
 f,ok:=a.Component(FixtureComponentName).(*FixtureController)
 if !ok { return nil,errors.New("declared fixture controller missing") }
 f.mu.Lock(); defer f.mu.Unlock()
 f.PrepareCalls++
 f.PreparedContexts=append(f.PreparedContexts,owned.ctx)
 if f.PrepareError!=nil { return nil,f.PrepareError }
 if request==nil || request.RpcObjectImportRequest==nil || len(f.Plans)==0 { return nil,errors.New("declared fixture input missing") }
 plan:=f.Plans[0]; f.Plans=f.Plans[1:]
 // Declared constructor copy fixture, not the real protobuf clone/dependency constructor.
 cloned:=*request; rpc:=*request.RpcObjectImportRequest; cloned.RpcObjectImportRequest=&rpc
 return &importProcessor{request:&cloned,owned:owned,execution:plan},nil
}
func (p *importProcessor) Execute(ctx context.Context) *ImportResponse {
 f:=p.execution; f.ExecuteCalls.Add(1); f.Entered<-ctx
 if f.EnterHook!=nil { f.EnterHook(ctx) }
 <-f.Release
 if f.MutateTarget!="" { p.request.SpaceId=f.MutateTarget }
 for _,file:=range f.Files { p.owned.fileResults=append(p.owned.fileResults,ownedImportFileResult{Kind:file.Kind,ObjectID:file.ObjectID,BlockID:file.BlockID,FileObjectID:file.FileObjectID,Err:file.Err}) }
 return f.Response
}
""")

application_source = ROOT / "candidate/native/core/application/application.go"
get_app = fragment(application_source, "func (s *Service) GetApp()", "\nfunc (s *Service) requireClientWithVersion()")
stop = fragment(application_source, "func (s *Service) Stop()", "\n// closeApp closes")
account_stop = fragment(ROOT / "candidate/native/core/application/account_stop.go",
                        "func (s *Service) AccountStop(", "\nfunc (s *Service) AccountChangeNetworkConfigAndRestart(")
start = fragment(WORK / "native-owned-import-audit/original/anytype-heart/core/application/app_start.go",
                 "type startRun struct {", "\n// startNewApp is where")
release_lease = fragment(ROOT / "original/core/application/account_lock.go", "func (s *Service) releaseAccountLease()", None)
write("core/application/actual_lifecycle.go", """package application
import "context"
import "errors"
import "runtime"
import "github.com/anyproto/any-sync/app"
import "github.com/anyproto/anytype-heart/core/pushnotification"
import "github.com/anyproto/anytype-heart/pb"
import "github.com/anyproto/anytype-heart/util/anyerror"
""" + get_app + "\n" + stop + "\n" + account_stop + "\n" + start + "\n" + release_lease)
write("core/application/fixture.go", """package application
import "errors"
import "sync"
import "github.com/anyproto/any-sync/app"
import "github.com/anyproto/anytype-heart/core/application/accountdirlock"
// Minimal Service storage ABI plus explicit close/remove dispatch fixtures.
// They do not close a real application, release an OS lock or delete files.
type Service struct {
 lock sync.RWMutex
 ownedImports ownedImportRegistry
 app *app.App
 accountLease *accountdirlock.Lease
 startMu sync.Mutex
 starting *startRun
 closeCalls,removeCalls int
}
var ErrFailedToRemoveAccountData=errors.New("fixture remove failed")
var ErrApplicationIsNotRunning=errors.New("fixture app not running")
var ErrFailedToStopApplication=errors.New("fixture stop failed")
type logger struct{}
func (logger) Info(string){}
var log logger
func (s *Service) closeApp() error { s.closeCalls++; s.app=nil; return nil }
func (s *Service) accountRemoveLocalData() error { s.removeCalls++; return s.stop() }
""")

for package, name in [("core/block/import", "owned_operation_test.go"), ("core/application", "owned_admission_test.go")]:
    actual(HERE / name, package + "/" + name, "new_unit_control")

expected = []
for path in sorted(MODULE.rglob("*_test.go")):
    names = re.findall(r"^func (Test\w+)\(", path.read_text(), re.M)
    assert len(names) == len(set(names))
    expected.extend(dict(package="github.com/anyproto/anytype-heart/" + path.parent.relative_to(MODULE).as_posix(), name=name) for name in names)
files, payload = [], []
for path in sorted(MODULE.rglob("*")):
    if path.is_file():
        raw = path.read_bytes()
        row = dict(path=path.relative_to(MODULE).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        files.append(row)
        payload.append(dict(**row, gzip_b64=base64.b64encode(gzip.compress(raw, mtime=0)).decode()))
source = dict(
    scope="New operation completion, application registration/retirement and legacy start/stop boundary unit controls; explicit controlled dependency fixtures only.",
    full_actual_source_files=whole_files, actual_source_fragments=fragments, module_files=files,
    fixture_scope="All fixture.go files and the replacement any-sync module are explicit ABI/callback fixtures. Execute, dependency construction/protobuf clone, component lookup, wallet keys, account lease, closeApp and accountRemoveLocalData are fixtures. No native module/account/storage/worker/upload/body/ACK qualification; prior 50/7/26 and native lifecycle controls are not executed.",
    expected_tests=expected, prior_controls_replayed=0, native_executions=0,
    product_manifest_sha256=hashlib.sha256((ROOT / "candidate/SOURCE_MANIFEST.json").read_bytes()).hexdigest())
(HERE / "SOURCE.json").write_text(json.dumps(source, indent=2) + "\n")
(HERE / "INPUT_PACKET.json").write_text(json.dumps(dict(files=payload, source_manifest=source), separators=(",", ":")))
print(json.dumps(dict(module_files=len(files), full_files=len(whole_files), fragments=len(fragments), new_controls=len(expected), executed_tests=0)))
