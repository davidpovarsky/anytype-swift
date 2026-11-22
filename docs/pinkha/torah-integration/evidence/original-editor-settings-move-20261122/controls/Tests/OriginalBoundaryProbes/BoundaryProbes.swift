import Foundation
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
    private var conflictResetPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard viewModel.viewModel.hasPreparedSource else { return nil }
        return { viewModel.prepareConflictReset() }
    }

    private var archiveConfirmationPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard viewModel.viewModel.hasPreparedSource else { return nil }
        return { viewModel.prepareArchiveConfirmation() }
    }

    private var currentSourcePublication: (@MainActor (@MainActor () -> Void) throws -> Void)? {
        guard viewModel.viewModel.hasPreparedSource else { return nil }
        return { action in
            try viewModel.viewModel.withCurrentSource(action)
        }
    }


    var preparations: [((@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?)] { [conflictResetPreparation, archiveConfirmationPreparation] }
    var publication: (@MainActor (@MainActor () -> Void) throws -> Void)? { currentSourcePublication }
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
    private var unpublishPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasPreparedSource else { return nil }
        return { model.prepareUnpublish() }
    }

    private var updatePreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasPreparedSource else { return nil }
        return { model.preparePublish(action: .update) }
    }

    private var publishPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasPreparedSource else { return nil }
        return { model.preparePublish(action: .create) }
    }


    var preparations: [((@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?)] { [unpublishPreparation, updatePreparation, publishPreparation] }
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
    func withCurrent<Value>(
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        _ operation: () throws -> Value
    ) throws -> Value {
        try owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false,
            requiredPermissions: requiredPermissions
        ) {
            try owner.validateDocument(document)
            return try operation()
        }
    }


}

private final class MoveBoundaryExtraction: Sendable {
    private let originalEditorScope: OriginalEditorPropertyScope?
    init(originalEditorScope: OriginalEditorPropertyScope?) { self.originalEditorScope = originalEditorScope }
    func observe(document: any BaseDocumentProtocol) async throws {
        if let originalEditorScope {
            try await MainActor.run {
                try originalEditorScope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                    try originalEditorScope.owner.validateDocument(document)
                }
            }
        }

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
