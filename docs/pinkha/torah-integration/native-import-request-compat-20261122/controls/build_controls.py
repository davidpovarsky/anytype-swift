from pathlib import Path
import json,hashlib,base64,gzip,shutil
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'candidate/native'
OLD=ROOT.parent/'native-map-audit'
MOD=ROOT/'controls/module'
rows=[]
def extracted(path,start,end=None):
 text=(BASE/path).read_text();part=text[text.index(start):]
 if end:part=part[:part.index(end)]
 rows.append(dict(path=path,start=start,end=end,source_sha256=hashlib.sha256(text.encode()).hexdigest(),fragment_sha256=hashlib.sha256(part.encode()).hexdigest(),bytes=len(part.encode())))
 return part

def write(path,text):
 p=MOD/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)

for rel in ['go.mod','pb/fixture.go','pkg/lib/pb/model/fixture.go','core/block/process/fixture.go','core/domain/fixture.go','core/domain/objectorigin/fixture.go','core/block/import/common/actual_source_fragments.go']:
 write(rel,(OLD/'controls/module'/rel).read_text())
write('core/block/import/mapping_observation.go',extracted('core/block/import/mapping_observation.go','package importer'))
write('core/block/import/mapping_observation_processor.go',extracted('core/block/import/mapping_observation_processor.go','package importer'))
request=extracted('core/block/import/types.go','type ImportRequest struct {','\ntype Dependencies')
old=(OLD/'original/core/block/import/types.go').read_text();original_request=old[old.index('type ImportRequest struct {'):old.index('\ntype ImportResponse')]
assert request[:request.index('\ntype ImportResponse')]==original_request
write('core/block/import/actual_types.go','''package importer
import (
 "github.com/anyproto/anytype-heart/core/block/process"
 "github.com/anyproto/anytype-heart/core/domain/objectorigin"
 "github.com/anyproto/anytype-heart/pb"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)
'''+request+'\n'+original_request.replace('type ImportRequest struct {','type originalFiveFieldRequest struct {'))
constructor=extracted('core/block/import/processor.go','func NewProcessor(','\ntype importProcessor')
old_processor=(OLD/'composition/r14/native/core/block/import/processor.go').read_text();assert constructor==old_processor[old_processor.index('func NewProcessor('):old_processor.index('\ntype importProcessor')]
context=extracted('core/block/import/processor.go','\tconversionContext := ctx','\tresponse, convErr := converter.GetSnapshots')
write('core/block/import/actual_constructor_and_explicit_dependencies.go','''package importer
import (
 "context"
 "github.com/anyproto/anytype-heart/core/block/import/common"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)
// These dependencies and the narrowed interface are explicit unit fixtures.
// Actual constructor and conversion-context statements below are extracted.
type Dependencies struct{}
type ImportProcessor interface{}
type importProcessor struct {
 deps *Dependencies
 request *ImportRequest
 response *ImportResponse
 errors *common.ConvertError
 captureMappingObservation bool
 nativeMapping *nativeMappingBuilder
 nativeMappingTraceID, nativeMappingSpaceID string
 nativeMappingAssignmentsFinished, nativeMappingCreationReturned bool
 nativeMappingBatchesStarted, nativeMappingBatchesDrained int
}
'''+constructor+'\nfunc actualConversionContext(p *importProcessor, ctx context.Context) context.Context {\n'+context+'\treturn conversionContext\n}\n')
write('core/block/import/compatibility_test.go',(ROOT/'controls/compatibility_test.go').read_text())
files=[];packet=[]
for p in sorted(MOD.rglob('*')):
 if p.is_file():
  raw=p.read_bytes();r=dict(path=p.relative_to(MOD).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());files.append(r);packet.append(dict(**r,gzip_b64=base64.b64encode(gzip.compress(raw,mtime=0)).decode()))
source=dict(scope='Seven new request layout, default-off and explicit PB opt-in controls over exact changed source fragments, with declared dependency fixtures. No original tests or prior50 controls replayed; no native import.',native_executions=0,prior_suites_replayed=0,actual_source_fragments=rows,explicit_fixture_files=['Dependencies','ImportProcessor narrowed interface','importProcessor dependency fields','core/block/import/common/actual_source_fragments.go original unit closure fixtures','pb/fixture.go','pkg/lib/pb/model/fixture.go','core/block/process/fixture.go','core/domain/fixture.go','core/domain/objectorigin/fixture.go'],module_files=files,original_request_declaration_sha256=hashlib.sha256(original_request.encode()).hexdigest(),legacy_constructor_byte_identical=True)
(ROOT/'controls/SOURCE.json').write_text(json.dumps(source,indent=2)+'\n')
(ROOT/'controls/INPUT_PACKET.json').write_text(json.dumps(dict(files=packet,source_manifest=source,product_files=json.loads((ROOT/'candidate/SOURCE_MANIFEST.json').read_text())),separators=(',',':')))
runner=(OLD/'controls/run_windows_controls.py').read_text().replace('otzaria-native-import-origin-controls-20261122-v1','otzaria-native-import-request-compat-20261122-v1').replace('"expected_leaf_controls": 50','"expected_leaf_controls": 7').replace('PASS_NATIVE_IMPORT_ORIGIN_UNIT_CONTROLS','PASS_REQUEST_COMPATIBILITY_CONTROLS').replace('new observation unit closure','new request compatibility unit closure')
(ROOT/'controls/run_windows_controls.py').write_text(runner)
print(json.dumps({'module_files':len(files),'actual_fragments':len(rows),'controls':7,'original_request_restored':True,'legacy_constructor_unchanged':True}))
