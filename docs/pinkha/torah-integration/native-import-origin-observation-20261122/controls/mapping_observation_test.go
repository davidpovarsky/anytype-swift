package importer

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"reflect"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/block/import/common"
	creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/import/common/workerpool"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func sourceRecord(sourceID, converterID string) nativeProtobufSourceRecord {
	return nativeProtobufSourceRecord{archivePath: "actual-capture.zip", memberPath: "objects/" + sourceID + ".pb", sourceSpaceID: "source-space", sourceObjectID: sourceID, converterID: converterID, encoding: ".pb", selected: true}
}

func simpleBuilder() *nativeMappingBuilder {
	return newNativeMappingBuilder([]nativeProtobufSourceRecord{sourceRecord("source-one", "converted-one")}, nil, nil, []string{"converted-one"}, false)
}

func expectUnproven(t *testing.T, b *nativeMappingBuilder) {
	t.Helper()
	for id := range b.selected {
		if _, exists := b.assignments[id]; !exists {
			b.recordAssignment(id, "native-"+id)
		}
	}
	o, problems := b.finish("trace", "process", "target", true)
	if o.CompleteForSelectedSnapshots() || len(problems) == 0 {
		t.Fatalf("incomplete observation became complete: %#v / %v", o, problems)
	}
}

func TestSourceChainKeepsAllDomainsDistinct(t *testing.T) {
	selected := sourceRecord("source-one", "converted-one")
	filtered := sourceRecord("filtered-widget", "converted-widget")
	filtered.selected = false
	b := newNativeMappingBuilder([]nativeProtobufSourceRecord{selected, filtered}, []string{"generated-collection"}, []string{"kept-deleted"}, []string{"converted-one", "generated-collection"}, false)
	b.recordAssignment("converted-one", "native-one")
	b.recordAssignment("generated-collection", "native-collection")
	b.recordAlias("converted-one", "original-relation-key", "native-relation-key")
	o, problems := b.finish("actual-trace", "actual-process", "target-space", true)
	if !o.CompleteForSelectedSnapshots() || len(problems) != 0 || o.TraceID() != "actual-trace" || o.ProcessID() != "actual-process" || o.TargetSpaceID() != "target-space" {
		t.Fatalf("expected one complete historical observation: %#v / %v", o, problems)
	}
	rows := o.SourceAssignments()
	if len(rows) != 1 || rows[0].SourceObjectID != selected.sourceObjectID || rows[0].ConverterID != selected.converterID || rows[0].NativeID != "native-one" || rows[0].ArchivePath != selected.archivePath || rows[0].MemberPath != selected.memberPath || rows[0].SourceSpaceID != selected.sourceSpaceID {
		t.Fatalf("lost identity stage: %#v", rows)
	}
	if len(o.FilteredSources()) != 1 || o.FilteredSources()[0].SourceObjectID != "filtered-widget" || len(o.GeneratedAssignments()) != 1 || len(o.InternalKeyAliases()) != 1 || !reflect.DeepEqual(o.KeptReferenceIDs(), []string{"kept-deleted"}) {
		t.Fatalf("collapsed filtered/generated/kept/alias domains: %#v", o)
	}
	if o.NonInjectiveDestinations() {
		t.Fatal("injective fixture unexpectedly marked non-injective")
	}
}

func TestManyToOneRetainsBothSourceRows(t *testing.T) {
	b := newNativeMappingBuilder([]nativeProtobufSourceRecord{sourceRecord("s1", "c1"), sourceRecord("s2", "c2")}, nil, nil, []string{"c1", "c2"}, false)
	b.recordAssignment("c1", "existing-native")
	b.recordAssignment("c2", "existing-native")
	o, problems := b.finish("t", "p", "space", true)
	if len(problems) != 0 || !o.CompleteForSelectedSnapshots() || !o.NonInjectiveDestinations() || len(o.SourceAssignments()) != 2 {
		t.Fatalf("native reuse was collapsed or mislabeled: %#v / %v", o, problems)
	}
}

func TestDestinationReuseOfKeptIDIsExplicit(t *testing.T) {
	b := newNativeMappingBuilder([]nativeProtobufSourceRecord{sourceRecord("s1", "c1")}, nil, []string{"kept-id"}, []string{"c1"}, false)
	b.recordAssignment("c1", "kept-id")
	o, _ := b.finish("t", "p", "space", true)
	if !o.CompleteForSelectedSnapshots() || !o.NonInjectiveDestinations() {
		t.Fatal("kept identity mapping collision was not labeled")
	}
}

func TestObservationCopiesInputAndAllReturnedRows(t *testing.T) {
	rows := []nativeProtobufSourceRecord{sourceRecord("s", "c"), sourceRecord("filtered", "cf")}
	rows[1].selected = false
	generated, kept := []string{"g"}, []string{"k"}
	b := newNativeMappingBuilder(rows, generated, kept, []string{"c", "g"}, false)
	rows[0].sourceObjectID, generated[0], kept[0] = "forged", "forged", "forged"
	b.recordAssignment("c", "n")
	b.recordAssignment("g", "ng")
	b.recordAlias("c", "old-key", "new-key")
	o, problems := b.finish("t", "p", "space", true)
	if len(problems) != 0 {
		t.Fatal(problems)
	}
	o.SourceAssignments()[0].NativeID = "forged"
	o.FilteredSources()[0].SourceObjectID = "forged"
	o.GeneratedAssignments()[0].NativeID = "forged"
	o.InternalKeyAliases()[0].NativeKey = "forged"
	o.KeptReferenceIDs()[0] = "forged"
	r := &ImportResponse{nativeMapping: &o}
	copy, ok := r.NativeMappingObservation()
	if !ok {
		t.Fatal("complete result absent")
	}
	copy.sources[0].NativeID = "forged"
	copy.filtered[0].SourceObjectID = "forged"
	copy.generated[0].NativeID = "forged"
	copy.aliases[0].NativeKey = "forged"
	copy.keptReferenceIDs[0] = "forged"
	after, _ := r.NativeMappingObservation()
	if after.SourceAssignments()[0].SourceObjectID != "s" || after.SourceAssignments()[0].NativeID != "n" || after.FilteredSources()[0].SourceObjectID != "filtered" || after.GeneratedAssignments()[0].NativeID != "ng" || after.InternalKeyAliases()[0].NativeKey != "new-key" || after.KeptReferenceIDs()[0] != "k" {
		t.Fatal("mutable input or a returned slice changed retained observation")
	}
	r.nativeMappingProblems = []string{"retained"}
	r.NativeMappingProblems()[0] = "forged"
	if r.NativeMappingProblems()[0] != "retained" {
		t.Fatal("problem list is mutable")
	}
}

func TestUnsupportedSourceRecordsStayUnproven(t *testing.T) {
	cases := map[string]func(*nativeProtobufSourceRecord){
		"missing archive":       func(r *nativeProtobufSourceRecord) { r.archivePath = "" },
		"missing member":        func(r *nativeProtobufSourceRecord) { r.memberPath = "" },
		"missing source space":  func(r *nativeProtobufSourceRecord) { r.sourceSpaceID = "" },
		"missing source object": func(r *nativeProtobufSourceRecord) { r.sourceObjectID = "" },
		"missing converter id":  func(r *nativeProtobufSourceRecord) { r.converterID = "" },
		"legacy JSON encoding":  func(r *nativeProtobufSourceRecord) { r.encoding = ".json" },
	}
	for name, change := range cases {
		t.Run(name, func(t *testing.T) {
			r := sourceRecord("s", "c")
			change(&r)
			expectUnproven(t, newNativeMappingBuilder([]nativeProtobufSourceRecord{r}, nil, nil, []string{r.converterID}, false))
		})
	}
}

func TestCollisionAndCoverageFailuresStayUnproven(t *testing.T) {
	for _, name := range []string{"duplicate source", "duplicate converter", "generated collision", "kept converter collision", "kept source collision", "duplicate kept", "missing selected snapshot", "extra selected snapshot", "duplicate selected snapshot", "only filtered and generated", "truncated source observation", "too many source records"} {
		t.Run(name, func(t *testing.T) {
			rows := []nativeProtobufSourceRecord{sourceRecord("s1", "c1")}
			var generated, kept []string
			ids := []string{"c1"}
			incomplete := false
			switch name {
			case "duplicate source":
				rows = append(rows, sourceRecord("s1", "c2"))
				ids = append(ids, "c2")
			case "duplicate converter":
				rows = append(rows, sourceRecord("s2", "c1"))
			case "generated collision":
				generated = []string{"c1"}
			case "kept converter collision":
				kept = []string{"c1"}
			case "kept source collision":
				kept = []string{"s1"}
			case "duplicate kept":
				kept = []string{"k", "k"}
			case "missing selected snapshot":
				ids = nil
			case "extra selected snapshot":
				ids = append(ids, "unobserved")
			case "duplicate selected snapshot":
				ids = append(ids, "c1")
			case "only filtered and generated":
				rows[0].selected = false
				generated = []string{"g"}
				ids = []string{"g"}
			case "truncated source observation":
				incomplete = true
			case "too many source records":
				for i := 1; i <= nativeMappingFactLimit; i++ {
					rows = append(rows, sourceRecord(fmt.Sprint("s", i+1), fmt.Sprint("c", i+1)))
				}
			}
			expectUnproven(t, newNativeMappingBuilder(rows, generated, kept, ids, incomplete))
		})
	}
}

func TestInvalidAssignmentAndAliasFactsStayUnproven(t *testing.T) {
	for _, name := range []string{"missing assignment", "duplicate assignment", "unknown assignment", "empty native destination", "alias overwrites converter", "duplicate alias", "empty alias destination", "alias overwrites kept"} {
		t.Run(name, func(t *testing.T) {
			b := newNativeMappingBuilder([]nativeProtobufSourceRecord{sourceRecord("s1", "c1")}, nil, []string{"k"}, []string{"c1"}, false)
			if name != "missing assignment" && name != "empty native destination" {
				b.recordAssignment("c1", "n1")
			}
			switch name {
			case "duplicate assignment":
				b.recordAssignment("c1", "n2")
			case "unknown assignment":
				b.recordAssignment("unknown", "n2")
			case "empty native destination":
				b.recordAssignment("c1", "")
			case "alias overwrites converter":
				b.recordAlias("c1", "c1", "key")
			case "duplicate alias":
				b.recordAlias("c1", "old", "new")
				b.recordAlias("c1", "old", "newer")
			case "empty alias destination":
				b.recordAlias("c1", "old", "")
			case "alias overwrites kept":
				b.recordAlias("c1", "k", "key")
			}
			o, problems := b.finish("trace", "process", "space", true)
			if o.CompleteForSelectedSnapshots() || len(problems) == 0 {
				t.Fatalf("invalid fact was accepted: %s", name)
			}
		})
	}
}

type controlledProgress struct{ step func(int64) error }

func (p controlledProgress) TryStep(n int64) error {
	if p.step != nil {
		return p.step(n)
	}
	return nil
}

func readyProcessor() *importProcessor {
	b := simpleBuilder()
	b.recordAssignment("converted-one", "native-one")
	return &importProcessor{request: &ImportRequest{RpcObjectImportRequest: &pb.RpcObjectImportRequest{SpaceId: "target", Type: model.Import_Pb}, CaptureMappingObservation: true, Progress: controlledProgress{}}, response: &ImportResponse{ProcessId: "process"}, errors: &common.ConvertError{}, nativeMapping: b, nativeMappingTraceID: "trace", nativeMappingSpaceID: "target", nativeMappingAssignmentsFinished: true, nativeMappingCreationReturned: true, nativeMappingBatchesStarted: 1, nativeMappingBatchesDrained: 1}
}

func TestActualCompletionGateRequiresEveryLifecycleCondition(t *testing.T) {
	for _, name := range []string{"assignment unfinished", "creation not returned", "no started batches", "unmatched drain", "legacy error", "missing error accumulator", "ignored task error", "context canceled", "target changed", "missing trace", "missing process"} {
		t.Run(name, func(t *testing.T) {
			p := readyProcessor()
			ctx := context.Background()
			switch name {
			case "assignment unfinished":
				p.nativeMappingAssignmentsFinished = false
			case "creation not returned":
				p.nativeMappingCreationReturned = false
			case "no started batches":
				p.nativeMappingBatchesStarted = 0
				p.nativeMappingBatchesDrained = 0
			case "unmatched drain":
				p.nativeMappingBatchesDrained = 0
			case "legacy error":
				p.response.Err = errors.New("legacy failure")
			case "missing error accumulator":
				p.errors = nil
			case "ignored task error":
				p.errors.Add(errors.New("ignored task failure"))
			case "context canceled":
				var cancel context.CancelFunc
				ctx, cancel = context.WithCancel(ctx)
				cancel()
			case "target changed":
				p.request.SpaceId = "other"
			case "missing trace":
				p.nativeMappingTraceID = ""
			case "missing process":
				p.response.ProcessId = ""
			}
			p.retainNativeMappingObservation(ctx)
			if _, ok := p.response.NativeMappingObservation(); ok || len(p.response.NativeMappingProblems()) == 0 {
				t.Fatal("completion gate admitted incomplete lifecycle")
			}
		})
	}
}

func TestSuccessfulCompletionAndDiagnosticReset(t *testing.T) {
	p := readyProcessor()
	p.retainNativeMappingObservation(context.Background())
	if _, ok := p.response.NativeMappingObservation(); !ok {
		t.Fatal("successful drained observation missing")
	}
	p.response.ObjectsCount = 91
	p.response.RootCollectionId = "legacy-root"
	p.response.Err = errors.New("legacy response")
	p.resetNativeMappingObservation()
	if _, ok := p.response.NativeMappingObservation(); ok || p.nativeMapping != nil || p.nativeMappingAssignmentsFinished || p.nativeMappingCreationReturned || p.nativeMappingBatchesStarted != 0 || p.nativeMappingBatchesDrained != 0 || p.nativeMappingTraceID != "" || p.nativeMappingSpaceID != "" {
		t.Fatal("sequential reuse retained diagnostic authority")
	}
	if p.response.ObjectsCount != 91 || p.response.RootCollectionId != "legacy-root" || p.response.Err == nil || p.response.ProcessId != "process" {
		t.Fatal("diagnostic reset changed legacy response")
	}
}

func TestInitializationRequiresExplicitProtobufOptIn(t *testing.T) {
	r := &common.Response{Snapshots: []*common.Snapshot{{Id: "c"}}, ProtobufSources: []common.ProtobufSourceObservation{{ArchivePath: "a", MemberPath: "s.pb", SourceSpaceID: "space", SourceObjectID: "s", ConverterID: "c", Encoding: ".pb", Selected: true}}}
	p := readyProcessor()
	p.resetNativeMappingObservation()
	p.request.CaptureMappingObservation = false
	p.initializeNativeMappingObservation(r)
	if p.nativeMapping != nil {
		t.Fatal("ordinary import captured diagnostics")
	}
	p.request.CaptureMappingObservation = true
	p.request.Type = model.Import(2)
	p.initializeNativeMappingObservation(r)
	if p.nativeMapping != nil {
		t.Fatal("other converter captured protobuf diagnostics")
	}
	p.request.Type = model.Import_Pb
	p.initializeNativeMappingObservation(r)
	if p.nativeMapping == nil {
		t.Fatal("explicit protobuf observation not initialized")
	}
}

func TestSourceRecorderBoundAndMergePreserveLegacySnapshots(t *testing.T) {
	left, right := common.NewSnapshotContext(), common.NewSnapshotContext()
	a, b := &common.Snapshot{Id: "legacy-a"}, &common.Snapshot{Id: "legacy-b"}
	left.Add(a)
	right.Add(b)
	for i := 0; i <= nativeMappingFactLimit; i++ {
		right.RecordProtobufSource(common.ProtobufSourceObservation{SourceObjectID: fmt.Sprint(i)})
	}
	left.Merge(right)
	rows, incomplete := left.ProtobufSources()
	if len(rows) != nativeMappingFactLimit || !incomplete || !reflect.DeepEqual(left.List(), []*common.Snapshot{a, b}) {
		t.Fatal("bounded recording changed legacy merge or hid truncation")
	}
	rows[0].SourceObjectID = "forged"
	again, _ := left.ProtobufSources()
	if again[0].SourceObjectID == "forged" {
		t.Fatal("source recorder returns aliased rows")
	}
	ctx := context.Background()
	if common.ProtobufSourceObservationRequested(ctx) || !common.ProtobufSourceObservationRequested(common.WithProtobufSourceObservation(ctx)) {
		t.Fatal("source recorder opt-in changed")
	}
}

func TestDiagnosticFieldsPreserveImplicitJSONShape(t *testing.T) {
	s := common.Snapshot{Id: "s", FileName: "s.pb"}
	before, err := json.Marshal(s)
	if err != nil {
		t.Fatal(err)
	}
	s.ProtobufSourceObjectID, s.ProtobufSourceSpaceID = "secret-source", "source-space"
	after, _ := json.Marshal(s)
	if string(before) != string(after) {
		t.Fatal("Snapshot JSON changed for diagnostic fields")
	}
	r := common.Response{RootObjectID: "root"}
	before, _ = json.Marshal(r)
	r.ProtobufSources = []common.ProtobufSourceObservation{{SourceObjectID: "s"}}
	r.ProtobufGeneratedIDs = []string{"g"}
	r.ProtobufSourceObservationIncomplete = true
	after, _ = json.Marshal(r)
	if string(before) != string(after) {
		t.Fatal("Response JSON changed for diagnostic fields")
	}
	p := ImportRequest{RpcObjectImportRequest: &pb.RpcObjectImportRequest{SpaceId: "target"}}
	before, _ = json.Marshal(p)
	p.CaptureMappingObservation = true
	after, _ = json.Marshal(p)
	if string(before) != string(after) {
		t.Fatal("internal opt-in changed request JSON")
	}
}

type controlledTask struct{ execute func() interface{} }

func (t controlledTask) Execute(interface{}) interface{} { return t.execute() }

func waitSignal(t *testing.T, ch <-chan struct{}) {
	t.Helper()
	select {
	case <-ch:
	case <-time.After(5 * time.Second):
		t.Fatal("controlled worker did not reach expected phase")
	}
}

func TestActualWorkerDrainDistinguishesSuccessFromEarlyStop(t *testing.T) {
	for _, scenario := range []string{"success", "progress cancellation", "all-or-nothing task error", "ignored task error"} {
		t.Run(scenario, func(t *testing.T) {
			p := readyProcessor()
			p.nativeMappingBatchesDrained = 0
			p.nativeMappingCreationReturned = false
			p.nativeMapping = newNativeMappingBuilder([]nativeProtobufSourceRecord{sourceRecord("s1", "c1"), sourceRecord("s2", "c2")}, nil, nil, []string{"c1", "c2"}, false)
			p.nativeMapping.recordAssignment("c1", "n1")
			p.nativeMapping.recordAssignment("c2", "n2")
			enteredSecond, releaseSecond, firstStep, startDone := make(chan struct{}), make(chan struct{}), make(chan struct{}), make(chan struct{})
			steps := 0
			p.request.Progress = controlledProgress{step: func(int64) error {
				steps++
				if steps == 1 {
					close(firstStep)
				}
				if scenario == "progress cancellation" {
					return errors.New("controlled cancellation")
				}
				return nil
			}}
			p.request.Mode = pb.RpcObjectImportRequest_ALL_OR_NOTHING
			if scenario == "ignored task error" {
				p.request.Mode = pb.RpcObjectImportRequest_IGNORE_ERRORS
			}
			pool := workerpool.NewPool(2)
			go func() { pool.Start(nil); close(startDone) }()
			go func() {
				pool.AddWork(controlledTask{execute: func() interface{} {
					<-enteredSecond
					r := &creator.Result{NewID: "n1", Details: &domain.Details{Value: "one"}}
					if scenario == "all-or-nothing task error" || scenario == "ignored task error" {
						r.Err = errors.New("controlled task failure")
					}
					return r
				}})
				pool.AddWork(controlledTask{execute: func() interface{} {
					close(enteredSecond)
					<-releaseSecond
					return &creator.Result{NewID: "n2", Details: &domain.Details{Value: "two"}}
				}})
				pool.CloseTask()
			}()
			result := make(chan map[string]*domain.Details, 1)
			go func() { result <- p.readResults(pool) }()
			waitSignal(t, firstStep)
			if _, ok := p.response.NativeMappingObservation(); ok {
				t.Fatal("observation published before worker drain")
			}
			if scenario == "progress cancellation" || scenario == "all-or-nothing task error" {
				select {
				case got := <-result:
					if got != nil {
						t.Fatal("original early-stop result changed")
					}
				case <-time.After(5 * time.Second):
					t.Fatal("expected early stop did not return")
				}
				if p.nativeMappingBatchesDrained != 0 {
					t.Fatal("early Stop was mislabeled drained")
				}
				select {
				case <-startDone:
					t.Fatal("controlled outstanding worker unexpectedly drained")
				default:
				}
				p.retainNativeMappingObservation(context.Background())
				if _, ok := p.response.NativeMappingObservation(); ok {
					t.Fatal("undrained import supplied an observation")
				}
				close(releaseSecond)
				waitSignal(t, startDone)
				return
			}
			select {
			case <-result:
				t.Fatal("readResults returned while controlled worker still active")
			default:
			}
			close(releaseSecond)
			select {
			case got := <-result:
				if len(got) != 2 {
					t.Fatal("original result inventory changed")
				}
			case <-time.After(5 * time.Second):
				t.Fatal("successful result channel did not close")
			}
			waitSignal(t, startDone)
			if p.nativeMappingBatchesDrained != 1 {
				t.Fatal("actual successful channel drain was not recorded")
			}
			p.nativeMappingCreationReturned = true
			p.retainNativeMappingObservation(context.Background())
			_, ok := p.response.NativeMappingObservation()
			if ok != (scenario == "success") {
				t.Fatal("ignored errors became a complete observation or success was lost")
			}
		})
	}
}
