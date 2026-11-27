import Foundation
import PinkhaKit
import Testing
import TorahInspectorCore
@testable import Anytype

@Suite("Inspector reference resolution error ownership")
@MainActor
struct TorahSearchResolutionPublicationTests {
    @Test("A failed reference resolution only reports to its original search", arguments: [false, true])
    func referenceResolutionErrorBelongsToTheCurrentQuery(replaceQuery: Bool) async throws {
        let gate = SearchResolutionFailureGate()
        let provider = SearchResolutionFailureProvider(gate: gate)
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: "space",
            objectId: "document",
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: SearchResolutionAssociationProbe()
        )
        var opened = [TorahInspectorSelection]()
        let presenter = TorahSourcesSearchPresenter(
            session: session,
            context: session.documentAssociationContext,
            onOpenSelection: { opened.append($0) }
        )
        presenter.searchQuery = "Genesis 1:1"
        let result = TorahEditorSession.SearchResult(
            id: "genesis",
            scope: .references,
            providerValue: "Genesis 1:1",
            labelHe: nil,
            labelEn: "Genesis 1:1",
            fallbackTitle: "Genesis 1:1",
            fallbackSubtitle: nil
        )

        let request = Task { await presenter.openReference(result) }
        do {
            try await gate.waitUntilHeld()
        } catch {
            request.cancel()
            await gate.release()
            throw error
        }
        if replaceQuery {
            // Typing a new query does not require another result-open request.
            presenter.searchQuery = "Exodus 1:1"
        }
        session.message = "Current search message"
        await gate.release()
        await request.value

        #expect(opened.isEmpty)
        if replaceQuery {
            #expect(session.message == "Current search message")
        } else {
            #expect(session.message != nil)
            #expect(session.message != "Current search message")
        }
        #expect(await provider.resolveCount() == 1)
    }
}

private actor SearchResolutionFailureGate {
    private var held = false
    private var released = false
    private var continuation: CheckedContinuation<Void, Never>?

    func hold() async {
        guard !released else { return }
        await withCheckedContinuation {
            continuation = $0
            held = true
        }
    }

    func waitUntilHeld() async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(2))
        while !held {
            guard clock.now < deadline else {
                throw SearchResolutionProbeError.providerDidNotStart
            }
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    func release() {
        released = true
        continuation?.resume()
        continuation = nil
    }
}

private actor SearchResolutionFailureProvider: ReferenceProvider, TopicProvider, LexicalProvider {
    nonisolated let providerID = "search-resolution-publication"
    private let gate: SearchResolutionFailureGate
    private var calls = 0

    init(gate: SearchResolutionFailureGate) { self.gate = gate }

    func resolveReference(_ input: String) async throws -> ResolvedReference {
        calls += 1
        await gate.hold()
        throw SearchResolutionProbeError.providerFailure
    }

    func resolveCount() -> Int { calls }
    func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate] { [] }
    func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate] { [] }
    func resolveTopic(id: String) async throws -> ResolvedTopic {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func refreshTopicIndexIfNeeded() async throws {}
    func suggestWords(prefix: String, context: TorahLexicalContext?) async throws -> [WordCandidate] { [] }
    func resolveWord(surface: String, context: TorahLexicalContext?) async throws -> [ResolvedWord] { [] }
}

private enum SearchResolutionProbeError: Error {
    case providerFailure
    case unexpectedOperation
    case providerDidNotStart
}

/// Controlled presenter dependency only; this fixture performs no native reads or writes.
private actor SearchResolutionAssociationProbe: AnytypeTorahAssociationSnapshotRepository {
    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String,
                        authorize: @escaping TorahAssociationWriteAuthorization) async throws -> TorahAssociationItem {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        throw SearchResolutionProbeError.unexpectedOperation
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String,
                           authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        throw SearchResolutionProbeError.unexpectedOperation
    }
}

@Suite("Inspector queued request presentation ownership")
@MainActor
struct TorahSearchQueuedRequestTests {
    @Test("A queued picker action cannot acquire a retired or reopened presentation",
          arguments: SearchQueuedOperation.allCases, [false, true])
    func queuedActionIsRetiredBeforeRepositoryEntry(
        operation: SearchQueuedOperation, reopenDocument: Bool
    ) async throws {
        let provider = SearchQueuedProviderProbe()
        let item = existingItem()
        let repository = SearchQueuedAssociationProbe(item: item)
        let session = try makeSession(provider: provider, repository: repository)
        var opened = [TorahInspectorSelection]()
        var selected = [TorahAssociationItem]()
        let onSelect: ((TorahAssociationItem) -> Void)? = operation == .select
            ? { selected.append($0) } : nil
        let presenter = TorahSourcesSearchPresenter(
            session: session, context: session.documentAssociationContext,
            searchQuery: "Genesis 1:1", associations: [item],
            onSelectValue: onSelect, onOpenSelection: { opened.append($0) }
        )

        // Match the real UI boundary: capture synchronously, enqueue, then
        // close before yielding MainActor. No sleep or scheduler timing is used.
        let oldAction = request(operation, presenter: presenter, item: item)
        let queued = Task { await oldAction() }
        presenter.cancelPendingRequests()
        if reopenDocument {
            session.deactivateDocument()
            session.activateDocument()
        }
        await queued.value

        let staleProviderCalls = await provider.recordedCalls()
        let staleRepositoryCalls = await repository.recordedCalls()
        #expect(staleProviderCalls.isEmpty)
        #expect(staleRepositoryCalls.isEmpty)
        #expect(opened.isEmpty)
        #expect(selected.isEmpty)
        #expect(presenter.searchState == .idle)
        #expect(presenter.persistenceState == nil)
        #expect(presenter.associations == [item])

        // A deliberate current action still enters the original session and
        // repository, including dispatch authorization and canonical readback.
        let currentAction = request(operation, presenter: presenter, item: item)
        await currentAction()
        let providerCalls = await provider.recordedCalls()
        let repositoryCalls = await repository.recordedCalls()
        switch operation {
        case .search:
            #expect(providerCalls == ["suggest:Genesis 1:1"])
            #expect(repositoryCalls.isEmpty)
            #expect(presenter.searchState.results.map(\.providerValue) == ["Genesis 1:1"])
        case .refresh:
            #expect(providerCalls.isEmpty)
            #expect(repositoryCalls == ["read:space/document"])
            #expect(presenter.associations == [item])
        case .open:
            #expect(providerCalls == ["resolve:Genesis 1:1"])
            #expect(repositoryCalls.isEmpty)
            #expect(opened.count == 1)
            #expect(opened.first?.canonicalRef == "Genesis 1")
            #expect(opened.first?.preferredSegmentRef == "Genesis 1:1")
        case .link:
            #expect(providerCalls == ["resolve:Genesis 1:1"])
            #expect(repositoryCalls == ["authorized-add:space/document", "read:space/document"])
            #expect(presenter.persistenceState == .saved)
            #expect(presenter.associations.map(\.canonicalKey).sorted() == ["Exodus 2:2", "Genesis 1:1"])
        case .unlink:
            #expect(providerCalls.isEmpty)
            #expect(repositoryCalls == ["authorized-remove:space/document", "read:space/document"])
            #expect(presenter.persistenceState == .saved)
            #expect(presenter.associations.isEmpty)
        case .select:
            #expect(providerCalls == ["resolve:Genesis 1:1"])
            #expect(repositoryCalls.isEmpty)
            #expect(selected.count == 1)
            #expect(selected.first?.canonicalKey == "Genesis 1:1")
        }
    }

    @Test("An awaited SwiftUI read retains caller cancellation before entry",
          arguments: [SearchQueuedOperation.search, .refresh])
    func cancelledStructuredReadDoesNotEnterProvider(operation: SearchQueuedOperation) async throws {
        let provider = SearchQueuedProviderProbe()
        let item = existingItem()
        let repository = SearchQueuedAssociationProbe(item: item)
        let session = try makeSession(provider: provider, repository: repository)
        let presenter = TorahSourcesSearchPresenter(
            session: session, context: session.documentAssociationContext,
            searchQuery: "Genesis 1:1", associations: [item], onOpenSelection: { _ in }
        )
        let action = request(operation, presenter: presenter, item: item)
        let task = Task { await action() }
        task.cancel()
        await task.value
        let providerCalls = await provider.recordedCalls()
        let repositoryCalls = await repository.recordedCalls()
        #expect(providerCalls.isEmpty)
        #expect(repositoryCalls.isEmpty)
        #expect(presenter.searchState == .idle)
        #expect(presenter.associations == [item])
    }

    private func request(
        _ operation: SearchQueuedOperation, presenter: TorahSourcesSearchPresenter,
        item: TorahAssociationItem
    ) -> @MainActor () async -> Void {
        let result = TorahEditorSession.SearchResult(
            id: "genesis", scope: .references, providerValue: "Genesis 1:1",
            labelHe: nil, labelEn: "Genesis 1:1", fallbackTitle: "Genesis 1:1",
            fallbackSubtitle: nil
        )
        switch operation {
        case .search: return presenter.makeSearchRequest()
        case .refresh: return presenter.makeAssociationRefreshRequest()
        case .open: return presenter.makeOpenReferenceRequest(result)
        case .link, .select: return presenter.makeLinkRequest(result)
        case .unlink: return presenter.makeUnlinkRequest(item)
        }
    }

    private func makeSession(
        provider: SearchQueuedProviderProbe, repository: SearchQueuedAssociationProbe
    ) throws -> TorahEditorSession {
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider], topicProviders: [provider],
            lexicalProviders: [provider], defaultProviderID: provider.providerID
        )
        return TorahEditorSession(
            spaceId: "space", objectId: "document",
            workspace: AnytypeTorahWorkspace(registry: registry), associations: repository
        )
    }

    private func existingItem() -> TorahAssociationItem {
        TorahAssociationItem(
            id: "existing", kind: .ref, role: .context, providerID: "sefaria",
            externalID: "Exodus 2:2", canonicalKey: "Exodus 2:2",
            labelHe: "שמות ב:ב", labelEn: "Exodus 2:2"
        )
    }
}

enum SearchQueuedOperation: CaseIterable, Sendable {
    case search, refresh, open, link, unlink, select
}

private actor SearchQueuedProviderProbe: ReferenceProvider, TopicProvider, LexicalProvider {
    nonisolated let providerID = "search-queued-presentation"
    private var calls = [String]()

    func recordedCalls() -> [String] { calls }
    func resolveReference(_ input: String) async throws -> ResolvedReference {
        calls.append("resolve:\(input)")
        return ResolvedReference(canonical: "Genesis 1:1", labelHe: "בראשית א:א", labelEn: "Genesis 1:1")
    }
    func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate] {
        calls.append("suggest:\(query)")
        return [ReferenceCandidate(id: "Genesis 1:1", label: "Genesis 1:1")]
    }
    func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate] {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func resolveTopic(id: String) async throws -> ResolvedTopic {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func refreshTopicIndexIfNeeded() async throws {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func suggestWords(prefix: String, context: TorahLexicalContext?) async throws -> [WordCandidate] {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func resolveWord(surface: String, context: TorahLexicalContext?) async throws -> [ResolvedWord] {
        throw SearchQueuedProbeError.unexpectedOperation
    }
}

/// Controlled protocol implementation; the production session still supplies
/// and executes its real write authorization and reads back these actual records.
/// This component fixture performs no Native operation or account/Space setup.
private actor SearchQueuedAssociationProbe: AnytypeTorahAssociationSnapshotRepository {
    private var records: [TorahStoredAssociationRecord]
    private var calls = [String]()

    init(item: TorahAssociationItem) {
        records = [.init(location: .init(spaceId: "space", target: .object(objectId: "document")), item: item)]
    }

    func recordedCalls() -> [String] { calls }
    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        guard objectId == "document", spaceId == "space" else { throw SearchQueuedProbeError.wrongScope }
        calls.append("read:\(spaceId)/\(objectId)")
        return records
    }
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String,
                        authorize: @escaping TorahAssociationWriteAuthorization) async throws -> TorahAssociationItem {
        guard target == .object(objectId: "document"), spaceId == "space" else { throw SearchQueuedProbeError.wrongScope }
        try await authorize()
        calls.append("authorized-add:space/document")
        records.append(.init(location: .init(spaceId: spaceId, target: target), item: item))
        return item
    }
    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        throw SearchQueuedProbeError.unexpectedOperation
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String,
                           authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        guard target == .object(objectId: "document"), spaceId == "space" else { throw SearchQueuedProbeError.wrongScope }
        try await authorize()
        calls.append("authorized-remove:space/document")
        records.removeAll { $0.item.id == associationId }
    }
}

private enum SearchQueuedProbeError: Error {
    case unexpectedOperation
    case wrongScope
}
