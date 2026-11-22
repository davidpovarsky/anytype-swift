package importer
import "context"
import "github.com/anyproto/anytype-heart/core/block/import/common"
import creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
import "github.com/anyproto/anytype-heart/core/block/import/common/workerpool"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
type progressFixture struct{}
func (progressFixture) TryStep(int)error{return nil}
type requestFixture struct {Progress progressFixture; Type model.ImportType}
type responseFixture struct {Err error}
type dependencyFixture struct {objectCreator creator.Service}
const workerPoolSize=32
type importProcessor struct {
 owned *ownedImportExecution
 errors *common.ConvertError
 deps *dependencyFixture
 request *requestFixture
 response *responseFixture
 nativeMapping *struct{}
 nativeMappingBatchesDrained int
 widgetCalls,finishCalls,eventCalls int
}
func (p *importProcessor) addRootCollectionWidget(context.Context){p.widgetCalls++}
func (p *importProcessor) finishImportProcess(){p.finishCalls++}
func (p *importProcessor) sendImportFinishEvent(){p.eventCalls++}
func recordEvent(any){}
func (p *importProcessor) addWork(snapshots []*common.Snapshot, pool *workerpool.WorkerPool) {
	for _, snapshot := range snapshots {
		t := creator.NewTask(snapshot, p.deps.objectCreator)
		stop := pool.AddWork(t)
		if stop {
			break
		}
	}
	pool.CloseTask()
}
