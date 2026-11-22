package common
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
type Snapshot struct {
	Id       string
	FileName string
	Snapshot *SnapshotModel
	// Parsed source facts only. Other converters leave these empty. They are
	// captured by the protobuf reader before normalization, never indexed proof.
	ProtobufSourceObjectID string `json:"-"`
	ProtobufSourceSpaceID  string `json:"-"`
}
type ProtobufSourceObservation struct {
	ArchivePath, MemberPath, SourceSpaceID, SourceObjectID, ConverterID, Encoding string
	Selected                                                                      bool
}

type protobufSourceObservationKey struct{}

// This requests diagnostic parsing facts; it does not create any receipt or
// permission. The existing wire ObjectImport route never sets this context.
func WithProtobufSourceObservation(ctx context.Context) context.Context {
	return context.WithValue(ctx, protobufSourceObservationKey{}, true)
}

func ProtobufSourceObservationRequested(ctx context.Context) bool {
	requested, _ := ctx.Value(protobufSourceObservationKey{}).(bool)
	return requested
}
type Response struct {
	Snapshots            []*Snapshot
	RootObjectID         string
	RootObjectWidgetType model.BlockContentWidgetLayout
	TypesCreated         []domain.TypeKey
	// KeptIDs are referenced ids the converter has decided to keep VERBATIM
	// rather than remap or rewrite to the missing-object sentinel: the ids an
	// AnyBlock bundle declares its source space DELETED (SPEC §2c). The
	// creation stage maps each to itself and writes a tombstone for it, so a
	// link to a deleted object restores as a link to a deleted object.
	KeptIDs                             []string
	ProtobufSources                     []ProtobufSourceObservation `json:"-"`
	ProtobufGeneratedIDs                []string                    `json:"-"`
	ProtobufSourceObservationIncomplete bool                        `json:"-"`
}
type SnapshotContext struct {
	snapshots                 []*Snapshot
	widget, workspace         *Snapshot
	protobufSources           []ProtobufSourceObservation
	protobufSourcesIncomplete bool
}

// Recording is bounded and never changes converter behavior on incomplete
// evidence. The original importer still decides all creation/error semantics.
func (sl *SnapshotContext) RecordProtobufSource(source ProtobufSourceObservation) {
	if len(sl.protobufSources) >= 512 {
		sl.protobufSourcesIncomplete = true
		return
	}
	sl.protobufSources = append(sl.protobufSources, source)
}

func (sl *SnapshotContext) ProtobufSources() ([]ProtobufSourceObservation, bool) {
	return append([]ProtobufSourceObservation(nil), sl.protobufSources...), sl.protobufSourcesIncomplete
}

func NewSnapshotContext() *SnapshotContext {
	return &SnapshotContext{
		snapshots: []*Snapshot{},
	}
}

func (sl *SnapshotContext) List() []*Snapshot {
	if sl == nil {
		return nil
	}
	return sl.snapshots
}

func (sl *SnapshotContext) Len() int {
	if sl == nil {
		return 0
	}
	return len(sl.snapshots)
}

func (sl *SnapshotContext) Add(snapshots ...*Snapshot) *SnapshotContext {
	sl.snapshots = append(sl.snapshots, snapshots...)
	return sl
}

func (sl *SnapshotContext) GetWorkspace() *Snapshot {
	if sl == nil {
		return nil
	}
	return sl.workspace
}

func (sl *SnapshotContext) SetWorkspace(w *Snapshot) *SnapshotContext {
	sl.workspace = w
	return sl
}

func (sl *SnapshotContext) GetWidget() *Snapshot {
	if sl == nil {
		return nil
	}
	return sl.widget
}

func (sl *SnapshotContext) SetWidget(w *Snapshot) *SnapshotContext {
	sl.widget = w
	return sl
}

func (sl *SnapshotContext) Merge(sl2 *SnapshotContext) {
	sl.snapshots = append(sl.snapshots, sl2.snapshots...)
	for _, source := range sl2.protobufSources {
		sl.RecordProtobufSource(source)
	}
	sl.protobufSourcesIncomplete = sl.protobufSourcesIncomplete || sl2.protobufSourcesIncomplete
	if sl2.widget != nil {
		sl.widget = sl2.widget
	}
	if sl2.workspace != nil {
		sl.workspace = sl2.workspace
	}
}
