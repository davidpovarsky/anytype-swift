#!/usr/bin/env python3
"""Stage an isolated stdlib-only unit closure; never claim full native execution."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "candidate/native"
MODULE = ROOT / "controls/module"
MANIFEST = []


def source(path):
    return (NATIVE / path).read_text()


def fragment(path, start, end=None):
    data = source(path)
    a = data.index(start)
    z = data.index(end, a) if end else len(data)
    text = data[a:z]
    MANIFEST.append({"path": path, "start": start, "end": end,
                     "source_sha256": hashlib.sha256(data.encode()).hexdigest(),
                     "fragment_sha256": hashlib.sha256(text.encode()).hexdigest(),
                     "bytes": len(text.encode())})
    return text


def write(path, text):
    p = MODULE / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


write("go.mod", "module github.com/anyproto/anytype-heart\n\ngo 1.25.6\n")
base = "core/block/import/"
for path in [base + "mapping_observation.go", base + "mapping_observation_processor.go"]:
    write(path, fragment(path, "package importer"))

common_path = base + "common/types.go"
common = '''package common
import (
 "context"
 "errors"
 "github.com/anyproto/anytype-heart/core/domain"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)
// Explicit test fixtures for unrelated original dependencies; not native state.
type SnapshotModel struct{}
type ConvertError struct { Values []error }
func (e *ConvertError) IsEmpty() bool { return e == nil || len(e.Values) == 0 }
func (e *ConvertError) Add(err error) { if err != nil { e.Values = append(e.Values, err) } }
var ErrCancel = errors.New("controlled import cancellation")
'''
common += fragment(common_path, "type Snapshot struct {", "\n// ProtobufSourceObservation")
common += fragment(common_path, "type ProtobufSourceObservation struct {", "\ntype SnapshotModel")
common += fragment(common_path, "type Response struct {", "\ntype SnapshotContext")
common += fragment(common_path, "type SnapshotContext struct {")
write(base + "common/actual_source_fragments.go", common)

types_path = base + "types.go"
types = '''package importer
import (
 "github.com/anyproto/anytype-heart/core/block/process"
 "github.com/anyproto/anytype-heart/core/domain/objectorigin"
 "github.com/anyproto/anytype-heart/pb"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)
'''
types += fragment(types_path, "type ImportRequest struct {", "\ntype Dependencies")
write(base + "actual_response_fragments.go", types)

processor = '''package importer
import (
 "fmt"
 "github.com/anyproto/anytype-heart/core/block/import/common"
 creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
 "github.com/anyproto/anytype-heart/core/block/import/common/workerpool"
 "github.com/anyproto/anytype-heart/core/domain"
 "github.com/anyproto/anytype-heart/pb"
)
// Explicit processor dependency fixture. All executed diagnostic methods and
// readResults below are byte-exact extracted production source, not reimplemented.
type importProcessor struct {
 request *ImportRequest
 response *ImportResponse
 errors *common.ConvertError
 nativeMapping *nativeMappingBuilder
 nativeMappingTraceID, nativeMappingSpaceID string
 nativeMappingAssignmentsFinished, nativeMappingCreationReturned bool
 nativeMappingBatchesStarted, nativeMappingBatchesDrained int
}
'''
processor += fragment(base + "processor.go", "func (p *importProcessor) readResults(", "\nfunc (p *importProcessor) finalize")
write(base + "actual_drain_fragment.go", processor)

worker = ROOT / "original/core/block/import/common/workerpool/workerpool.go"
write(base + "common/workerpool/workerpool.go", worker.read_text())
MANIFEST.append({"path": "original/core/block/import/common/workerpool/workerpool.go",
                 "full_file_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
                 "original_revision": "d98420b1113536afd08cde6de9a5816f6d27ffff"})

fixtures = {
 "core/domain/fixture.go": "package domain\ntype Details struct { Value string }\ntype TypeKey string\n",
 "core/domain/objectorigin/fixture.go": "package objectorigin\ntype ObjectOrigin string\n",
 "core/block/process/fixture.go": "package process\ntype Progress interface { TryStep(int64) error }\n",
 "pkg/lib/pb/model/fixture.go": "package model\ntype Import int\nconst Import_Pb Import = 1\ntype BlockContentWidgetLayout int\n",
 "pb/fixture.go": '''package pb
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
type RpcObjectImportRequest struct { SpaceId string; Type model.Import; Mode int }
const RpcObjectImportRequest_ALL_OR_NOTHING = 1
const RpcObjectImportRequest_IGNORE_ERRORS = 2
''',
 base + "common/objectcreator/fixture.go": '''package objectcreator
import "github.com/anyproto/anytype-heart/core/domain"
type Result struct { NewID string; Details *domain.Details; Err error }
''',
}
for path, content in fixtures.items():
    write(path, content)
for path in ["mapping_observation_test.go", "mapping_observation_external_test.go"]:
    write(base + path, (ROOT / "controls" / path).read_text())
closure = []
for p in sorted(MODULE.rglob("*")):
    if p.is_file():
        data = p.read_bytes()
        closure.append({"path": p.relative_to(MODULE).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
(ROOT / "controls/SOURCE.json").write_text(json.dumps({
    "scope": "Actual new pure observation helper, processor glue, response accessors, source recorder and original workerpool/readResults with explicit controlled dependencies. No protobuf reader/native engine/side-effect execution or import authority.",
    "native_executions": 0, "prior_suites_replayed": 0,
    "actual_source_fragments": MANIFEST,
    "explicit_fixture_files": list(fixtures),
    "additional_inline_fixtures": ["SnapshotModel", "ConvertError", "ErrCancel", "importProcessor dependency fields"],
    "module_files": closure,
}, indent=2) + "\n")
print(json.dumps({"module_files": len(closure), "actual_source_fragments": len(MANIFEST), "native_executions": 0}))
