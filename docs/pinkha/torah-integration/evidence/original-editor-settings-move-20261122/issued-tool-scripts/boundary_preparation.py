import pathlib,subprocess,json,hashlib,os,datetime,re
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-settings-move-compile-20261122")
package=out/"boundary-package"
assert not package.exists(), "Preparation already exists; inspect before replay"
manifest=json.loads((out/"CANDIDATE_PROVENANCE.json").read_text(encoding="utf-8"))
for item in manifest["candidates"]:
 data=(out/(pathlib.Path(item["path"]).stem+".candidate.swift")).read_bytes()
 assert hashlib.sha256(data).hexdigest()==item["candidate_sha256"]
for item in manifest["dependencies"]:
 assert hashlib.sha256((out/item["snapshot"]).read_bytes()).hexdigest()==item["sha256"]
settings=(out/"SETTINGS_PROPERTIES.swift.txt").read_text(encoding="utf-8")
publishing=(out/"PUBLISHING_PROPERTIES.swift.txt").read_text(encoding="utf-8")
move=(out/"TypePropertiesMoveHandler.candidate.swift").read_text(encoding="utf-8")
start=move.index("        if let originalEditorScope {")
end=move.index("        guard let fromRow",start)
move_prefix=move[start:end]
scope=(out/"DEPENDENCY_0.swift").read_text(encoding="utf-8")
start=scope.index("    func withCurrent<Value>(")
end=scope.index("    /// The original callback",start)
scope_method=scope[start:end]
prepare_type="(@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?"
publication_type="(@MainActor (@MainActor () -> Void) throws -> Void)?"
for name in ["DEPENDENCY_6.swift","DEPENDENCY_7.swift"]:
 data=(out/name).read_text(encoding="utf-8")
 assert "prepareAction: "+prepare_type in data
 assert "publish: "+publication_type in data
assert "prepareAction: "+prepare_type in (out/"DEPENDENCY_8.swift").read_text(encoding="utf-8")
probe=r'''import Foundation
import Testing

private enum BoundaryProbeError: Error, Equatable { case rejected, wrongDocument }

@MainActor
private final class BoundaryEvents {
    var prepared: [String] = []
    var executed: [String] = []
    var publications = 0
}

@MainActor
private final class SettingsSourceProbe {
    var hasPreparedSource = false
    var acceptsPublication = true
    let events: BoundaryEvents
    init(events: BoundaryEvents) { self.events = events }
    func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        guard acceptsPublication else { throw BoundaryProbeError.rejected }
        events.publications += 1
        return try operation()
    }
}

@MainActor
private final class SettingsModelProbe {
    let viewModel: SettingsSourceProbe
    init(events: BoundaryEvents) { viewModel = SettingsSourceProbe(events: events) }
    func prepareConflictReset() -> @MainActor @Sendable () async throws -> Void {
        viewModel.events.prepared.append("conflict")
        return { self.viewModel.events.executed.append("conflict") }
    }
    func prepareArchiveConfirmation() -> @MainActor @Sendable () async throws -> Void {
        viewModel.events.prepared.append("archive")
        return { self.viewModel.events.executed.append("archive") }
    }
}

@MainActor
private struct SettingsExtraction {
    let viewModel: SettingsModelProbe
''' + settings + r'''
    var preparations: [('''+prepare_type+r''')] { [conflictResetPreparation, archiveConfirmationPreparation] }
    var publication: '''+publication_type+r''' { currentSourcePublication }
}

private enum PublishAction: Sendable { case create, update }

@MainActor
private final class PublishingModelProbe {
    var hasPreparedSource = false
    let events: BoundaryEvents
    init(events: BoundaryEvents) { self.events = events }
    func prepareUnpublish() -> @MainActor @Sendable () async throws -> Void {
        events.prepared.append("unpublish")
        return { self.events.executed.append("unpublish") }
    }
    func preparePublish(action: PublishAction) -> @MainActor @Sendable () async throws -> Void {
        let label = action == .update ? "update" : "create"
        events.prepared.append(label)
        return { self.events.executed.append(label) }
    }
}

@MainActor
private struct PublishingExtraction {
    let model: PublishingModelProbe
''' + publishing + r'''
    var preparations: [('''+prepare_type+r''')] { [unpublishPreparation, updatePreparation, publishPreparation] }
}

private protocol BaseDocumentProtocol: AnyObject, Sendable {}
private final class DocumentBoundaryProbe: BaseDocumentProtocol {}

private enum EditorDocumentWritePermission: Hashable, Sendable {
    case editDetails, editPropertiesList
}

@MainActor
private final class OwnerBoundaryProbe {
    let expected: any BaseDocumentProtocol
    var permits = true
    var entries = 0
    var validatedDocuments: [ObjectIdentifier] = []
    init(expected: any BaseDocumentProtocol) { self.expected = expected }
    func performSynchronousOperation<Value>(
        contextId: String, spaceId: String, requiresEditing: Bool,
        requiredPermissions: Set<EditorDocumentWritePermission>,
        _ operation: () throws -> Value
    ) throws -> Value {
        MainActor.preconditionIsolated()
        #expect(contextId == "original-type" && spaceId == "original-space")
        #expect(!requiresEditing)
        #expect(requiredPermissions == [.editDetails, .editPropertiesList])
        entries += 1
        guard permits else { throw BoundaryProbeError.rejected }
        return try operation()
    }
    func validateDocument(_ candidate: any BaseDocumentProtocol) throws {
        MainActor.preconditionIsolated()
        validatedDocuments.append(ObjectIdentifier(candidate))
        guard candidate === expected else { throw BoundaryProbeError.wrongDocument }
    }
}

@MainActor
private final class OriginalEditorPropertyScope {
    static let listPermissions: Set<EditorDocumentWritePermission> = [.editDetails, .editPropertiesList]
    let objectId = "original-type"
    let spaceId = "original-space"
    private let document: any BaseDocumentProtocol
    let owner: OwnerBoundaryProbe
    init(document: any BaseDocumentProtocol, owner: OwnerBoundaryProbe) {
        self.document = document
        self.owner = owner
    }
''' + scope_method + r'''
}

private final class MoveBoundaryExtraction: Sendable {
    private let originalEditorScope: OriginalEditorPropertyScope?
    init(originalEditorScope: OriginalEditorPropertyScope?) { self.originalEditorScope = originalEditorScope }
    func observe(document: any BaseDocumentProtocol) async throws {
''' + move_prefix + r'''
    }
}

@Suite(.serialized)
private struct OriginalSettingsMoveBoundaryProbes {
    @Test @MainActor
    func deferredPreparationAtExactlyFiveSites() async throws {
        let events = BoundaryEvents()
        let settingsModel = SettingsModelProbe(events: events)
        let publishingModel = PublishingModelProbe(events: events)
        let settings = SettingsExtraction(viewModel: settingsModel)
        let publishing = PublishingExtraction(model: publishingModel)
        #expect((settings.preparations + publishing.preparations).allSatisfy { $0 == nil })
        #expect(events.prepared.isEmpty && events.executed.isEmpty)
        settingsModel.viewModel.hasPreparedSource = true
        publishingModel.hasPreparedSource = true
        let factories = settings.preparations + publishing.preparations
        #expect(factories.count == 5)
        #expect(events.prepared.isEmpty && events.executed.isEmpty)
        var operations: [@MainActor @Sendable () async throws -> Void] = []
        for factory in factories {
            let actual = try #require(factory)
            operations.append(actual())
        }
        #expect(events.prepared == ["conflict", "archive", "unpublish", "update", "create"])
        #expect(events.executed.isEmpty)
        for operation in operations { try await operation() }
        #expect(events.executed == events.prepared)
    }

    @Test @MainActor
    func exactPublicationTypeRetainsDeferredGateAndThrow() throws {
        let events = BoundaryEvents()
        let model = SettingsModelProbe(events: events)
        let extraction = SettingsExtraction(viewModel: model)
        #expect(extraction.publication == nil)
        #expect(events.publications == 0)
        model.viewModel.hasPreparedSource = true
        let publish = try #require(extraction.publication)
        #expect(events.publications == 0)
        var count = 0
        try publish { count += 1 }
        #expect(count == 1 && events.publications == 1)
        model.viewModel.acceptsPublication = false
        do {
            try publish { count += 1 }
            Issue.record("Rejected publication unexpectedly returned")
        } catch {
            #expect(error as? BoundaryProbeError == .rejected)
        }
        #expect(count == 1 && events.publications == 1)
    }

    @Test @MainActor
    func exactMovePrefixUsesCapturedScopeOnMainActor() async throws {
        let document = DocumentBoundaryProbe()
        let owner = OwnerBoundaryProbe(expected: document)
        let scope = OriginalEditorPropertyScope(document: document, owner: owner)
        let extraction = MoveBoundaryExtraction(originalEditorScope: scope)
        try await Task.detached { try await extraction.observe(document: document) }.value
        #expect(owner.entries == 1)
        #expect(owner.validatedDocuments == [ObjectIdentifier(document), ObjectIdentifier(document)])
        let wrongDocument = DocumentBoundaryProbe()
        do {
            try await Task.detached { try await extraction.observe(document: wrongDocument) }.value
            Issue.record("Different document unexpectedly accepted")
        } catch {
            #expect(error as? BoundaryProbeError == .wrongDocument)
        }
        #expect(owner.entries == 2)
        owner.permits = false
        let previousValidations = owner.validatedDocuments
        do {
            try await Task.detached { try await extraction.observe(document: document) }.value
            Issue.record("Rejected original scope unexpectedly accepted")
        } catch {
            #expect(error as? BoundaryProbeError == .rejected)
        }
        #expect(owner.entries == 3)
        #expect(owner.validatedDocuments == previousValidations)
        let legacy = MoveBoundaryExtraction(originalEditorScope: nil)
        try await Task.detached { try await legacy.observe(document: wrongDocument) }.value
        #expect(owner.entries == 3)
    }
}
'''
(package/"Tests"/"OriginalBoundaryProbes").mkdir(parents=True)
(package/"Package.swift").write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "OriginalSettingsMoveBoundary",
    targets: [.testTarget(name: "OriginalBoundaryProbes")],
    swiftLanguageModes: [.v6]
)
''',encoding="utf-8")
probe_path=package/"Tests"/"OriginalBoundaryProbes"/"BoundaryProbes.swift"
probe_path.write_bytes(probe.encode())
inputs={"schema":1,"source_head":manifest["source_head"],"candidate_provenance_sha256":hashlib.sha256((out/"CANDIDATE_PROVENANCE.json").read_bytes()).hexdigest(),"candidates":[{k:v for k,v in x.items() if k!="patch"} for x in manifest["candidates"]],"probe_sha256":hashlib.sha256(probe.encode()).hexdigest(),"settings_properties_sha256":hashlib.sha256(settings.encode()).hexdigest(),"publishing_properties_sha256":hashlib.sha256(publishing.encode()).hexdigest(),"move_prefix_sha256":hashlib.sha256(move_prefix.encode()).hexdigest(),"scope_withCurrent_method_sha256":hashlib.sha256(scope_method.encode()).hexdigest(),"prepare_type":prepare_type,"publication_type":publication_type,"new_tests":3,"limits":"Exact extracted changed properties and MainActor.run prefix plus original scope.withCurrent method, with explicit model/owner/document interface probes. Genuine installed Swift Testing. No SwiftUI, original Owner implementation, native RPC, original button tap body, engine, runtime, or UI acceptance; full-file parse is syntax only. Existing passing suites are not included."}
(out/"BOUNDARY_INPUTS.json").write_text(json.dumps(inputs,indent=2)+"\n",encoding="utf-8")
print(json.dumps(inputs))
