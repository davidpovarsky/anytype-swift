package importer

// These copied facts describe ID choices made by one original import execution.
// They do not prove account lifetime, archive binding, applied body, complete file
// effects, atomicity, durable mapping, or acknowledgment authority.

const nativeMappingFactLimit = 512

type NativeProtobufSourceAssignment struct {
	ArchivePath    string
	MemberPath     string
	SourceSpaceID  string
	SourceObjectID string
	ConverterID    string
	NativeID       string
}

type NativeProtobufFilteredSource struct {
	ArchivePath    string
	MemberPath     string
	SourceSpaceID  string
	SourceObjectID string
	ConverterID    string
}

type NativeProtobufGeneratedAssignment struct {
	ConverterID string
	NativeID    string
}

type NativeProtobufInternalKeyAlias struct {
	ConverterID string
	SourceKey   string
	NativeKey   string
}

// NativeProtobufImportMappingObservation has no exported constructor or writable
// fields. Its zero value is incomplete. Its copied rows remain evidence data,
// not admission tokens. Only the original processor can install a complete value
// in ImportResponse after every started batch has successfully drained.
type NativeProtobufImportMappingObservation struct {
	complete                 bool
	traceID                  string
	processID                string
	targetSpaceID            string
	sources                  []NativeProtobufSourceAssignment
	filtered                 []NativeProtobufFilteredSource
	generated                []NativeProtobufGeneratedAssignment
	aliases                  []NativeProtobufInternalKeyAlias
	keptReferenceIDs         []string
	nonInjectiveDestinations bool
}

func (o NativeProtobufImportMappingObservation) CompleteForSelectedSnapshots() bool {
	return o.complete
}
func (o NativeProtobufImportMappingObservation) TraceID() string       { return o.traceID }
func (o NativeProtobufImportMappingObservation) ProcessID() string     { return o.processID }
func (o NativeProtobufImportMappingObservation) TargetSpaceID() string { return o.targetSpaceID }
func (o NativeProtobufImportMappingObservation) SourceAssignments() []NativeProtobufSourceAssignment {
	return append([]NativeProtobufSourceAssignment(nil), o.sources...)
}
func (o NativeProtobufImportMappingObservation) FilteredSources() []NativeProtobufFilteredSource {
	return append([]NativeProtobufFilteredSource(nil), o.filtered...)
}
func (o NativeProtobufImportMappingObservation) GeneratedAssignments() []NativeProtobufGeneratedAssignment {
	return append([]NativeProtobufGeneratedAssignment(nil), o.generated...)
}
func (o NativeProtobufImportMappingObservation) InternalKeyAliases() []NativeProtobufInternalKeyAlias {
	return append([]NativeProtobufInternalKeyAlias(nil), o.aliases...)
}
func (o NativeProtobufImportMappingObservation) KeptReferenceIDs() []string {
	return append([]string(nil), o.keptReferenceIDs...)
}

// NonInjectiveDestinations includes kept reference IDs, which the original
// processor seeds as identity mappings, as well as selected/generated rows.
func (o NativeProtobufImportMappingObservation) NonInjectiveDestinations() bool {
	return o.nonInjectiveDestinations
}

func (o NativeProtobufImportMappingObservation) copy() NativeProtobufImportMappingObservation {
	o.sources = o.SourceAssignments()
	o.filtered = o.FilteredSources()
	o.generated = o.GeneratedAssignments()
	o.aliases = o.InternalKeyAliases()
	o.keptReferenceIDs = o.KeptReferenceIDs()
	return o
}

type nativeProtobufSourceRecord struct {
	archivePath, memberPath, sourceSpaceID, sourceObjectID, converterID, encoding string
	selected                                                                      bool
}

type nativeMappingBuilder struct {
	sources         []nativeProtobufSourceRecord
	selected        map[string]bool
	generatedIDs    []string
	keptIDs         []string
	assignments     map[string]string
	assignmentOrder []string
	aliases         []NativeProtobufInternalKeyAlias
	aliasKeys       map[string]bool
	problems        []string
}

func newNativeMappingBuilder(sources []nativeProtobufSourceRecord, generatedIDs, keptIDs, snapshotIDs []string, incomplete bool) *nativeMappingBuilder {
	b := &nativeMappingBuilder{selected: map[string]bool{}, assignments: map[string]string{}, aliasKeys: map[string]bool{}}
	if incomplete {
		b.problem("source-observation-incomplete")
	}
	if len(sources) == 0 || len(sources) > nativeMappingFactLimit || len(generatedIDs) > nativeMappingFactLimit || len(keptIDs) > nativeMappingFactLimit || len(snapshotIDs) > nativeMappingFactLimit {
		b.problem("source-observation-count")
		return b
	}
	sourceIDs, converterIDs := map[string]bool{}, map[string]bool{}
	selectedOriginals := 0
	for _, row := range sources {
		if row.sourceObjectID == "" || row.converterID == "" || row.sourceSpaceID == "" || row.archivePath == "" || row.memberPath == "" || row.encoding != ".pb" {
			b.problem("unsupported-source-record")
		}
		if sourceIDs[row.sourceObjectID] || converterIDs[row.converterID] {
			b.problem("duplicate-source-or-converter-id")
		}
		sourceIDs[row.sourceObjectID], converterIDs[row.converterID] = true, true
		b.sources = append(b.sources, row)
		if row.selected {
			b.selected[row.converterID] = true
			selectedOriginals++
		}
	}
	if selectedOriginals == 0 {
		b.problem("no-selected-original-source")
	}
	for _, id := range generatedIDs {
		if id == "" || converterIDs[id] {
			b.problem("generated-id-collision")
		}
		converterIDs[id] = true
		b.selected[id] = true
		b.generatedIDs = append(b.generatedIDs, id)
	}
	seenSnapshots := map[string]bool{}
	for _, id := range snapshotIDs {
		if id == "" || seenSnapshots[id] || !b.selected[id] {
			b.problem("selected-snapshot-coverage")
		}
		seenSnapshots[id] = true
	}
	if len(seenSnapshots) != len(b.selected) || len(b.selected) == 0 {
		b.problem("selected-snapshot-coverage")
	}
	seenKept := map[string]bool{}
	for _, id := range keptIDs {
		if id == "" || seenKept[id] || converterIDs[id] || sourceIDs[id] {
			b.problem("kept-reference-collision")
		}
		seenKept[id] = true
		b.keptIDs = append(b.keptIDs, id)
	}
	return b
}

func (b *nativeMappingBuilder) problem(code string) {
	if len(b.problems) < 16 {
		b.problems = append(b.problems, code)
	}
}

// Called immediately beside the actual oldIDToNew[snapshot.Id] = id write.
func (b *nativeMappingBuilder) recordAssignment(converterID, nativeID string) {
	if len(b.assignmentOrder) >= nativeMappingFactLimit {
		b.problem("assignment-count")
		return
	}
	if !b.selected[converterID] || nativeID == "" || b.aliasKeys[converterID] {
		b.problem("invalid-assignment")
	}
	if _, exists := b.assignments[converterID]; exists {
		b.problem("duplicate-assignment")
		return
	}
	b.assignments[converterID] = nativeID
	b.assignmentOrder = append(b.assignmentOrder, converterID)
}

// The original local newUniqueKey is passed here; evidence never re-reads the
// shared provider's mutable GetInternalKey value.
func (b *nativeMappingBuilder) recordAlias(converterID, sourceKey, nativeKey string) {
	if len(b.aliases) >= nativeMappingFactLimit {
		b.problem("alias-count")
		return
	}
	if sourceKey == "" || nativeKey == "" || !b.selected[converterID] || b.selected[sourceKey] || b.aliasKeys[sourceKey] {
		b.problem("alias-domain-collision")
	}
	for _, id := range b.keptIDs {
		if id == sourceKey {
			b.problem("alias-kept-reference-collision")
		}
	}
	b.aliasKeys[sourceKey] = true
	b.aliases = append(b.aliases, NativeProtobufInternalKeyAlias{ConverterID: converterID, SourceKey: sourceKey, NativeKey: nativeKey})
}

func (b *nativeMappingBuilder) finish(traceID, processID, targetSpaceID string, eligible bool) (NativeProtobufImportMappingObservation, []string) {
	if !eligible || traceID == "" || processID == "" || targetSpaceID == "" {
		b.problem("execution-not-eligible")
	}
	if len(b.assignments) != len(b.selected) {
		b.problem("assignment-coverage")
	}
	for id := range b.selected {
		if b.assignments[id] == "" {
			b.problem("missing-assignment")
		}
	}
	if len(b.problems) != 0 {
		return NativeProtobufImportMappingObservation{}, append([]string(nil), b.problems...)
	}
	o := NativeProtobufImportMappingObservation{complete: true, traceID: traceID, processID: processID, targetSpaceID: targetSpaceID,
		aliases: append([]NativeProtobufInternalKeyAlias(nil), b.aliases...), keptReferenceIDs: append([]string(nil), b.keptIDs...)}
	for _, row := range b.sources {
		if row.selected {
			o.sources = append(o.sources, NativeProtobufSourceAssignment{ArchivePath: row.archivePath, MemberPath: row.memberPath,
				SourceSpaceID: row.sourceSpaceID, SourceObjectID: row.sourceObjectID, ConverterID: row.converterID, NativeID: b.assignments[row.converterID]})
		} else {
			o.filtered = append(o.filtered, NativeProtobufFilteredSource{ArchivePath: row.archivePath, MemberPath: row.memberPath,
				SourceSpaceID: row.sourceSpaceID, SourceObjectID: row.sourceObjectID, ConverterID: row.converterID})
		}
	}
	for _, id := range b.generatedIDs {
		o.generated = append(o.generated, NativeProtobufGeneratedAssignment{ConverterID: id, NativeID: b.assignments[id]})
	}
	destinations := map[string]bool{}
	for _, id := range b.keptIDs {
		destinations[id] = true
	}
	for _, id := range b.assignmentOrder {
		destination := b.assignments[id]
		if destinations[destination] {
			o.nonInjectiveDestinations = true
		}
		destinations[destination] = true
	}
	return o, nil
}
