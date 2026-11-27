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
