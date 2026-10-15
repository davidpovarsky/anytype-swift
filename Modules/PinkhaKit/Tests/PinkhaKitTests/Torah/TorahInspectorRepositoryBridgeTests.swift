import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

private actor BridgeFetchRecorder {
    private var references: [String] = []

    func record(_ reference: String) {
        references.append(reference)
    }

    func values() -> [String] { references }
}

private struct BridgeFixtureProvider:
    ReferenceProvider,
    TopicProvider,
    LexicalProvider,
    TextProvider,
    RelationshipProvider,
    TorahHierarchyProvider {
    let providerID = "bridge-fixture"
    let recorder: BridgeFetchRecorder

    func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate] {
        query.isEmpty ? [] : [ReferenceCandidate(id: "Genesis 1:1", label: "בראשית א׳:א׳")]
    }

    func resolveReference(_ input: String) async throws -> ResolvedReference {
        ResolvedReference(canonical: "Genesis 1:1", labelHe: "בראשית א׳:א׳", labelEn: "Genesis 1:1")
    }

    func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate] {
        [TopicCandidate(id: "creation", labelHe: "בריאה", labelEn: "Creation")]
    }

    func resolveTopic(id: String) async throws -> ResolvedTopic {
        ResolvedTopic(slug: id, labelHe: "בריאה", labelEn: "Creation")
    }

    func refreshTopicIndexIfNeeded() async throws {}

    func suggestWords(prefix: String, context: TorahLexicalContext?) async throws -> [WordCandidate] {
        [WordCandidate(id: "BDB|word|1", surface: prefix, headword: prefix, lexicon: "BDB")]
    }

    func resolveWord(surface: String, context: TorahLexicalContext?) async throws -> [ResolvedWord] {
        try await suggestWords(prefix: surface, context: context).map { ResolvedWord(candidate: $0) }
    }

    func fetchText(reference: String, request: TorahTextRequest) async throws -> TorahTextDocument {
        await recorder.record(reference)
        try await Task.sleep(for: .milliseconds(20))
        try Task.checkCancellation()
        if reference == "Genesis 1:1" {
            return sampleDocument(
                providerID: providerID,
                requestedRef: reference,
                canonicalRef: reference,
                sectionRef: "Genesis 1"
            )
        }
        return sampleDocument(
            providerID: providerID,
            requestedRef: reference,
            canonicalRef: "Genesis 1",
            sectionRef: "Genesis 1"
        )
    }

    func links(for reference: String) async throws -> [TorahLinkedSource] {
        [TorahLinkedSource(
            sourceRef: "Rashi on \(reference)",
            category: "Commentary",
            type: "commentary",
            collectiveTitle: "Rashi",
            canonicalBookID: "Rashi",
            anchorRefs: [reference]
        )]
    }

    func topics(for reference: String) async throws -> [TorahLinkedTopic] {
        [TorahLinkedTopic(slug: "creation", titleHe: "בריאה", titleEn: "Creation")]
    }

    func fetchHierarchy() async throws -> TorahSourceHierarchy {
        TorahSourceHierarchy(
            roots: [TorahSourceNode(
                id: "Genesis",
                labelHe: "בראשית",
                labelEn: "Genesis",
                canonicalKey: "Genesis"
            )],
            providerID: providerID
        )
    }
}

@Suite("Torah Inspector repository bridge")
struct TorahInspectorRepositoryBridgeTests {
    @Test("Registry rejects invalid defaults and duplicate providers")
    func registryValidation() throws {
        let provider = BridgeFixtureProvider(recorder: BridgeFetchRecorder())
        #expect(throws: TorahProviderRegistryConfigurationError.defaultProviderNotRegistered("missing")) {
            _ = try TorahProviderRegistry(
                referenceProviders: [provider],
                topicProviders: [],
                lexicalProviders: [],
                defaultProviderID: "missing"
            )
        }
        #expect(throws: TorahProviderRegistryConfigurationError.duplicateProviderID(provider.providerID)) {
            _ = try TorahProviderRegistry(
                referenceProviders: [provider, provider],
                topicProviders: [],
                lexicalProviders: [],
                defaultProviderID: provider.providerID
            )
        }
    }

    @Test("Workspace routes exact provider IDs and refuses silent fallback")
    func exactProviderRouting() async throws {
        let provider = BridgeFixtureProvider(recorder: BridgeFetchRecorder())
        let workspace = AnytypeTorahWorkspace(registry: try makeRegistry(provider))
        #expect(try await workspace.fetchSourceHierarchy().providerID == provider.providerID)
        await #expect(throws: TorahError.missingProvider) {
            _ = try await workspace.fetchText(reference: "Genesis 1", providerID: "missing")
        }
        await #expect(throws: TorahError.missingProvider) {
            _ = try await workspace.links(for: "Genesis 1:1", providerID: "missing")
        }
    }

    @Test("Section loading follows provider metadata instead of trimming a reference")
    func sectionResolution() async throws {
        let recorder = BridgeFetchRecorder()
        let provider = BridgeFixtureProvider(recorder: recorder)
        let workspace = AnytypeTorahWorkspace(registry: try makeRegistry(provider))

        let document = try await workspace.fetchSectionText(
            reference: "Genesis 1:1",
            providerID: provider.providerID
        )

        #expect(document.canonicalRef == "Genesis 1")
        #expect(await recorder.values() == ["Genesis 1:1", "Genesis 1"])
    }

    @Test("Updated Core API supports explicit scope and notes-enabled repository")
    @MainActor
    func updatedCoreAPI() async throws {
        let sectionSelection = TorahInspectorSelection(
            providerID: "bridge-fixture",
            canonicalRef: "Genesis 1",
            scope: .section
        )
        let segmentSelection = TorahInspectorSelection(
            providerID: "bridge-fixture",
            canonicalRef: "Genesis 1",
            preferredSegmentRef: "Genesis 1:1",
            scope: .segment
        )
        let repository = TorahInspectorRepository(
            textFetcher: { _, _ in sampleDocument() },
            notesFetcher: { selection in
                [TorahInspectorNote(id: selection.id, selectedText: "", note: "fixture")]
            }
        )

        #expect(sectionSelection.scope == .section)
        #expect(sectionSelection.preferredSegmentRef == nil)
        #expect(segmentSelection.scope == .segment)
        #expect(try await repository.notes(for: sectionSelection).first?.note == "fixture")
    }

    @Test("Factory connects document, links, topics and explicit no-notes behavior")
    @MainActor
    func repositoryFactory() async throws {
        let recorder = BridgeFetchRecorder()
        let provider = BridgeFixtureProvider(recorder: recorder)
        let workspace = AnytypeTorahWorkspace(registry: try makeRegistry(provider))
        let repository = TorahInspectorRepositoryFactory.make(workspace: workspace)

        async let first = repository.document(for: "Genesis 1", providerID: provider.providerID)
        async let second = repository.document(for: "Genesis 1", providerID: provider.providerID)
        let documents = try await (first, second)

        #expect(documents.0.id == documents.1.id)
        #expect(await recorder.values() == ["Genesis 1"])
        #expect(try await repository.links(for: "Genesis 1:1", providerID: provider.providerID).first?.relationshipKind == .commentary)
        #expect(try await repository.topics(for: "Genesis 1:1", providerID: provider.providerID).first?.slug == "creation")
        let selection = TorahInspectorSelection(
            providerID: provider.providerID,
            canonicalRef: "Genesis 1",
            scope: .section
        )
        #expect(try await repository.notes(for: selection).isEmpty)
        await #expect(throws: TorahError.missingProvider) {
            _ = try await repository.document(for: "Genesis 1", providerID: "wrong-provider")
        }
    }

    private func makeRegistry(_ provider: BridgeFixtureProvider) throws -> TorahProviderRegistry {
        try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            textProviders: [provider],
            relationshipProviders: [provider],
            hierarchyProviders: [provider],
            defaultProviderID: provider.providerID
        )
    }
}
