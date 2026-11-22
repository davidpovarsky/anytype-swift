package importer
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
