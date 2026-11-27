import Foundation
import Services
import PinkhaKit
import SwiftProtobuf
import Testing
import TorahInspectorCore
@testable import Anytype

@Suite("T2-L native single-writer repository")
struct TorahAssociationNativeRepositoryTests {
    private let spaceId = "space"
    private let objectId = "document"

    @Test("Concurrent mutations in one process are serialized without lost updates")
    func concurrentMutationsRetainEveryAssociation() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["block"])
        let repository = makeRepository(store: store)

        try await withThrowingTaskGroup(of: Void.self) { group in
            for index in 0..<24 {
                group.addTask {
                    _ = try await repository.addAssociation(
                        association(index),
                        target: index.isMultiple(of: 2)
                            ? .object(objectId: objectId)
                            : .block(objectId: objectId, blockId: "block"),
                        spaceId: spaceId
                    )
                }
            }
            try await group.waitForAll()
        }

        let document = try await repository.listDocumentAssociations(objectId: objectId, spaceId: spaceId)
        let block = try await repository.listBlockAssociations(
            objectId: objectId,
            blockId: "block",
            spaceId: spaceId
        )
        #expect(document.count == 12)
        #expect(block.count == 12)
        #expect(Set(document.map(\.id) + block.map(\.id)).count == 24)
        #expect(await store.maximumConcurrentWrites() == 1)
        #expect(await store.unrelatedDetails() == ["name": "untouched", "custom": "preserved"])
        #expect(await store.blockFingerprints() == ["block": "unchanged"])
    }

    @Test("A lost acknowledgement succeeds only after exact native readback")
    func acknowledgementLossReconcilesByReadback() async throws {
        let store = NativeStoreProbe(
            spaceId: spaceId,
            objectId: objectId,
            blockIds: [],
            writeBehavior: .persistThenThrow
        )
        let repository = makeRepository(store: store)

        let stored = try await repository.addAssociation(
            association(1),
            target: .object(objectId: objectId),
            spaceId: spaceId
        )

        #expect(stored.id == "association-1")
        #expect(try await repository.listDocumentAssociations(objectId: objectId, spaceId: spaceId).map(\.id) == ["association-1"])
    }

    @Test("An unacknowledged and unpersisted write is visibly uncertain")
    func uncertainWriteIsNotReportedAsSaved() async {
        let store = NativeStoreProbe(
            spaceId: spaceId,
            objectId: objectId,
            blockIds: [],
            writeBehavior: .throwWithoutPersisting
        )
        let repository = makeRepository(store: store)

        do {
            _ = try await repository.addAssociation(
                association(2),
                target: .object(objectId: objectId),
                spaceId: spaceId
            )
            Issue.record("An uncertain write was reported as successful")
        } catch let error as TorahAssociationRepositoryError {
            guard case .writeUncertain = error else {
                Issue.record("Expected writeUncertain, got \(error)")
                return
            }
        } catch {
            Issue.record("Unexpected error: \(error)")
        }
    }

    @Test("Future and malformed native values fail closed before any write")
    func invalidNativePayloadsFailClosed() async {
        for (value, expected) in [
            (#"{"version":99,"records":[]}"#, TorahAssociationRepositoryError.unsupportedPayloadVersion(99)),
            ("{", TorahAssociationRepositoryError.malformedCanonicalData)
        ] {
            let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], value: value)
            let repository = makeRepository(store: store)
            do {
                _ = try await repository.addAssociation(
                    association(3),
                    target: .object(objectId: objectId),
                    spaceId: spaceId
                )
                Issue.record("Invalid canonical data was overwritten")
            } catch let error as TorahAssociationRepositoryError {
                #expect(error == expected)
            } catch {
                Issue.record("Unexpected error: \(error)")
            }
            #expect(await store.writeCount() == 0)
        }
    }

    @Test("A present non-string native property fails closed")
    func wrongTypedNativePropertyFailsClosed() {
        let value = Google_Protobuf_Value.with { $0.numberValue = 42 }

        do {
            _ = try TorahAssociationNativePropertyValue.decode(value)
            Issue.record("A wrong-typed native value was treated as an absent property")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == .malformedCanonicalData)
        } catch {
            Issue.record("Unexpected error: \(error)")
        }
    }

    @Test("External Torah drops copy while internal editor drags remain moves")
    func dragOperationsStaySeparated() {
        #expect(TorahEditorSafetyPolicy.dropOperation(
            containsTorahSource: true,
            canMutate: true,
            canPlace: true
        ) == .copy)
        #expect(TorahEditorSafetyPolicy.dropOperation(
            containsTorahSource: false,
            canMutate: true,
            canPlace: true
        ) == .move)
        #expect(TorahEditorSafetyPolicy.dropOperation(
            containsTorahSource: true,
            canMutate: false,
            canPlace: true
        ) == .forbidden)
        #expect(TorahEditorSafetyPolicy.dropOperation(
            containsTorahSource: false,
            canMutate: false,
            canPlace: true
        ) == .forbidden)
    }

    @Test("Document REF, TOPIC and WORD records survive a fresh repository instance")
    func documentKindsSurviveFreshRepository() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["block"])
        let first = makeRepository(store: store)
        for item in [
            association(10, kind: .ref),
            association(11, kind: .topic),
            association(12, kind: .word)
        ] {
            _ = try await first.addAssociation(
                item,
                target: .object(objectId: objectId),
                spaceId: spaceId
            )
        }

        let reopened = makeRepository(store: store)
        let items = try await reopened.listDocumentAssociations(objectId: objectId, spaceId: spaceId)
        #expect(Set(items.map(\.kind)) == Set([.ref, .topic, .word]))
        let records = try await reopened.listAssociationRecords(objectId: objectId, spaceId: spaceId)
        #expect(records.count == 3)
        #expect(records.allSatisfy { $0.blockId == nil })
    }

    @Test("Document and block targets retain identical canonical sources independently")
    func identicalSourceAcrossScopesRemainsDistinct() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["a", "b"])
        let repository = makeRepository(store: store)
        let source = association(20)
        _ = try await repository.addAssociation(source, target: .object(objectId: objectId), spaceId: spaceId)
        _ = try await repository.addAssociation(source, target: .block(objectId: objectId, blockId: "a"), spaceId: spaceId)
        _ = try await repository.addAssociation(source, target: .block(objectId: objectId, blockId: "b"), spaceId: spaceId)

        let records = try await repository.listAssociationRecords(objectId: objectId, spaceId: spaceId)
        #expect(records.count == 3)
        #expect(Set(records.map(\.blockId)) == Set<String?>([nil, "a", "b"]))
    }

    @Test("Removing one scope leaves every other scope unchanged")
    func scopedRemovalDoesNotTouchOtherTargets() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["a", "b"])
        let repository = makeRepository(store: store)
        for (index, target) in [
            (30, TorahAssociationTarget.object(objectId: objectId)),
            (31, TorahAssociationTarget.block(objectId: objectId, blockId: "a")),
            (32, TorahAssociationTarget.block(objectId: objectId, blockId: "b"))
        ] {
            _ = try await repository.addAssociation(association(index), target: target, spaceId: spaceId)
        }

        try await repository.removeAssociation(
            associationId: "association-30",
            target: .object(objectId: objectId),
            spaceId: spaceId
        )

        #expect(try await repository.listDocumentAssociations(objectId: objectId, spaceId: spaceId).isEmpty)
        #expect(try await repository.listBlockAssociations(objectId: objectId, blockId: "a", spaceId: spaceId).map(\.id) == ["association-31"])
        #expect(try await repository.listBlockAssociations(objectId: objectId, blockId: "b", spaceId: spaceId).map(\.id) == ["association-32"])
    }

    @Test("Document updates and removal preserve two independently linked blocks")
    func documentMutationPreservesTwoBlockRecords() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["a", "b"])
        let repository = makeRepository(store: store)
        let documentItem = association(33)
        let blockA = association(34)
        let blockB = association(35)
        _ = try await repository.addAssociation(documentItem, target: .object(objectId: objectId), spaceId: spaceId)
        _ = try await repository.addAssociation(blockA, target: .block(objectId: objectId, blockId: "a"), spaceId: spaceId)
        _ = try await repository.addAssociation(blockB, target: .block(objectId: objectId, blockId: "b"), spaceId: spaceId)

        var updatedDocumentItem = documentItem
        updatedDocumentItem.labelHe = "בראשית מעודכן"
        _ = try await repository.updateAssociation(
            updatedDocumentItem,
            target: .object(objectId: objectId),
            spaceId: spaceId
        )
        try await repository.removeAssociation(
            associationId: documentItem.id,
            target: .object(objectId: objectId),
            spaceId: spaceId
        )

        #expect(try await repository.listDocumentAssociations(objectId: objectId, spaceId: spaceId).isEmpty)
        #expect(try await repository.listBlockAssociations(objectId: objectId, blockId: "a", spaceId: spaceId) == [blockA])
        #expect(try await repository.listBlockAssociations(objectId: objectId, blockId: "b", spaceId: spaceId) == [blockB])
    }

    @MainActor
    @Test("A stale block refresh cannot overwrite a newer document context")
    func staleRefreshCannotReplaceDocumentAssociations() async throws {
        let documentItem = association(40)
        let blockItem = association(41)
        let probe = DelayedSessionAssociationProbe(
            responses: [
                .init(
                    delay: .milliseconds(120),
                    records: [TorahStoredAssociationRecord(
                        location: .init(spaceId: spaceId, target: .block(objectId: objectId, blockId: "block")),
                        item: blockItem
                    )]
                ),
                .init(
                    delay: .milliseconds(5),
                    records: [TorahStoredAssociationRecord(
                        location: .init(spaceId: spaceId, target: .object(objectId: objectId)),
                        item: documentItem
                    )]
                )
            ]
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: try AnytypeTorahWorkspace.sefaria(),
            associations: probe
        )

        session.presentSearch(scope: .block("block"))
        try await Task.sleep(for: .milliseconds(15))
        session.presentSearch(scope: .document)
        try await Task.sleep(for: .milliseconds(160))

        #expect(session.associationContext.scope == .document)
        #expect(session.currentAssociations.map(\.id) == [documentItem.id])
    }

    @MainActor
    @Test("Search state rejects stale query and scope responses and clears cancellation")
    func searchStateRejectsStaleResponses() async throws {
        let provider = SessionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: DelayedSessionAssociationProbe(responses: [])
        )

        session.searchScope = .words
        session.searchQuery = "old"
        let staleQuery = Task { await session.performSearch() }
        try await Task.sleep(for: .milliseconds(10))
        session.searchQuery = "new"
        await session.performSearch()
        await staleQuery.value
        #expect(session.searchState.results.map(\.providerValue) == ["new"])

        session.searchQuery = "old"
        let staleScope = Task { await session.performSearch() }
        try await Task.sleep(for: .milliseconds(10))
        session.searchScope = .topics
        session.searchQuery = "topic"
        await session.performSearch()
        await staleScope.value
        #expect(session.searchState.results.map(\.scope) == [.topics])

        session.searchScope = .words
        session.searchQuery = "none"
        await session.performSearch()
        #expect(session.searchState == .empty)
        #expect(session.message == nil)

        session.searchQuery = "failure"
        await session.performSearch()
        guard case .error(let message) = session.searchState else {
            Issue.record("A genuine provider failure must remain an inline error")
            return
        }
        #expect(!message.isEmpty)
        #expect(session.message == nil)

        session.searchQuery = "old"
        let canceled = Task { await session.performSearch() }
        try await Task.sleep(for: .milliseconds(10))
        canceled.cancel()
        await canceled.value
        #expect(session.searchState == .idle)

        session.searchQuery = "old"
        let staleAfterClear = Task { await session.performSearch() }
        try await Task.sleep(for: .milliseconds(10))
        session.searchQuery = ""
        await session.performSearch()
        await staleAfterClear.value
        #expect(session.searchState == .idle)
    }

    @MainActor
    @Test("Embedded search opens on the current Inspector stack without replacing the sheet root")
    func embeddedSearchOpenKeepsOuterSelectionAndStandaloneSheetState() async throws {
        let provider = SessionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: DelayedSessionAssociationProbe(responses: [])
        )
        let rootSelection = TorahInspectorSelection(
            providerID: provider.providerID,
            canonicalRef: "Genesis 1"
        )
        session.selection = rootSelection
        var navigatedSelection: TorahInspectorSelection?
        let presenter = TorahSourcesSearchPresenter(
            session: session,
            context: session.documentAssociationContext,
            onOpenSelection: { navigatedSelection = $0 }
        )
        presenter.searchQuery = "Exodus 1"
        await presenter.performSearch()
        let result = try #require(presenter.searchState.results.first)

        await presenter.openReference(result)

        #expect(navigatedSelection?.canonicalRef == "Exodus 1")
        #expect(session.selection == rootSelection)
        #expect(!session.isSearchPresented)
    }

    @MainActor
    @Test("Out-of-order and dismissed embedded source resolutions never navigate stale results")
    func embeddedSearchRejectsStaleSourceResolution() async throws {
        let provider = DelayedResolutionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: DelayedSessionAssociationProbe(responses: [])
        )
        var opened = [String]()
        let presenter = TorahSourcesSearchPresenter(
            session: session,
            context: session.documentAssociationContext,
            onOpenSelection: { opened.append($0.canonicalRef) }
        )
        let old = TorahEditorSession.SearchResult(
            id: "old",
            scope: .references,
            providerValue: "old",
            labelHe: nil,
            labelEn: "old",
            fallbackTitle: "old",
            fallbackSubtitle: nil
        )
        let new = TorahEditorSession.SearchResult(
            id: "new",
            scope: .references,
            providerValue: "new",
            labelHe: nil,
            labelEn: "new",
            fallbackTitle: "new",
            fallbackSubtitle: nil
        )

        presenter.searchQuery = "old"
        let stale = Task { await presenter.openReference(old) }
        try await Task.sleep(for: .milliseconds(10))
        presenter.searchQuery = "new"
        await presenter.openReference(new)
        await stale.value
        #expect(opened == ["new"])

        presenter.searchQuery = "old"
        let dismissed = Task { await presenter.openReference(old) }
        try await Task.sleep(for: .milliseconds(10))
        presenter.cancelPendingRequests()
        await dismissed.value
        #expect(opened == ["new"])

        session.deactivateDocument()
        presenter.searchQuery = "new"
        await presenter.openReference(new)
        #expect(opened == ["new"])
        #expect(await provider.resolveCount(for: "new") == 2)
    }

    @MainActor
    @Test("Embedded links freeze a document target even after a block-scoped standalone search")
    func embeddedSearchAlwaysLinksToTheDocumentContext() async throws {
        let store = NativeStoreProbe(
            spaceId: spaceId,
            objectId: objectId,
            blockIds: ["previous-block"]
        )
        let repository = makeRepository(store: store)
        let provider = SessionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let workspace = AnytypeTorahWorkspace(registry: registry)
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: workspace,
            associations: repository
        )
        session.presentSearch(scope: .block("previous-block"))
        let embedded = TorahSourcesSearchPresenter(
            session: session,
            context: session.documentAssociationContext,
            onOpenSelection: { _ in }
        )
        embedded.searchQuery = "Genesis 1:1"
        await embedded.performSearch()
        let documentResult = try #require(embedded.searchState.results.first)

        await embedded.link(documentResult)

        #expect(session.associationContext.scope == .block("previous-block"))
        #expect(try await repository.listDocumentAssociations(
            objectId: objectId,
            spaceId: spaceId
        ).count == 1)
        #expect(try await repository.listBlockAssociations(
            objectId: objectId,
            blockId: "previous-block",
            spaceId: spaceId
        ).isEmpty)

        let relaunchedSession = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: workspace,
            associations: repository
        )
        let relaunchedEmbedded = TorahSourcesSearchPresenter(
            session: relaunchedSession,
            context: relaunchedSession.documentAssociationContext,
            onOpenSelection: { _ in }
        )
        await relaunchedEmbedded.refreshAssociations()
        #expect(relaunchedEmbedded.associations.count == 1)

        relaunchedSession.presentSearch(scope: .block("previous-block"))
        let standaloneBlock = TorahSourcesSearchPresenter(
            session: relaunchedSession,
            context: relaunchedSession.associationContext,
            onOpenSelection: { _ in }
        )
        standaloneBlock.searchQuery = "Genesis 1:2"
        await standaloneBlock.performSearch()
        let blockResult = try #require(standaloneBlock.searchState.results.first)
        await standaloneBlock.link(blockResult)

        #expect(try await repository.listBlockAssociations(
            objectId: objectId,
            blockId: "previous-block",
            spaceId: spaceId
        ).count == 1)
    }

    @MainActor
    @Test("A document switch invalidates an in-flight embedded link before storage mutation")
    func inactiveDocumentCannotReceiveEmbeddedLink() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [])
        let repository = makeRepository(store: store)
        let provider = SessionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: repository
        )
        let presenter = TorahSourcesSearchPresenter(
            session: session,
            context: session.documentAssociationContext,
            onOpenSelection: { _ in }
        )
        presenter.searchQuery = "Genesis 1:3"
        await presenter.performSearch()
        let result = try #require(presenter.searchState.results.first)
        session.deactivateDocument()

        await presenter.link(result)

        #expect(await store.writeCount() == 0)
        guard case .error = presenter.persistenceState else {
            Issue.record("A stale document target must surface a visible failure")
            return
        }
    }

    @MainActor
    @Test("Embedded topic and word results remain typed document associations")
    func embeddedTopicAndWordLinksPreserveKinds() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [])
        let repository = makeRepository(store: store)
        let provider = SessionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: repository
        )
        let presenter = TorahSourcesSearchPresenter(
            session: session,
            context: session.documentAssociationContext,
            onOpenSelection: { _ in }
        )

        for scope in [TorahEditorSession.SearchScope.topics, .words] {
            presenter.searchScope = scope
            presenter.searchQuery = "typed-\(scope.rawValue)"
            await presenter.performSearch()
            let result = try #require(presenter.searchState.results.first)
            await presenter.link(result)
        }

        let values = try await repository.listDocumentAssociations(
            objectId: objectId,
            spaceId: spaceId
        )
        #expect(Set(values.map(\.kind)) == Set([.topic, .word]))
    }

    @Test("Locale changes display only and new quote bodies do not freeze a citation")
    func localeAndQuoteContentAreNonDestructive() {
        let item = TorahAssociationItem(
            id: "stable",
            kind: .ref,
            role: .sourceQuote,
            providerID: "sefaria",
            externalID: "Genesis.1.1",
            canonicalKey: "Genesis 1:1",
            labelHe: "בראשית א׳:א׳",
            labelEn: "Genesis 1:1"
        )
        #expect(TorahAssociationDisplayFormatter.label(for: item, locale: Locale(identifier: "he")) == "בראשית א׳:א׳")
        #expect(TorahAssociationDisplayFormatter.label(for: item, locale: Locale(identifier: "en")) == "Genesis 1:1")
        #expect(item.id == "stable")
        #expect(item.canonicalKey == "Genesis 1:1")

        let transfer = TorahSourceTransfer(
            providerID: "sefaria",
            canonicalRef: "Genesis 1:1",
            hebrewRef: "בראשית א׳:א׳",
            sectionRef: "Genesis 1",
            text: "בראשית ברא"
        )
        #expect(TorahQuoteContentPolicy.editableBody(for: transfer) == "בראשית ברא")
        #expect(!TorahQuoteContentPolicy.editableBody(for: transfer).contains("Genesis 1:1"))
    }

    @MainActor
    @Test("A single linked verse opens exact relationships; multiple or typed links open a chooser")
    func linkedBlockOpeningRoutesByAssociationShape() async throws {
        let verse = TorahAssociationItem(
            id: "verse",
            kind: .ref,
            role: .sourceQuote,
            providerID: "sefaria",
            externalID: "Genesis.1.1",
            canonicalKey: "Genesis 1:1",
            labelHe: "בראשית א׳:א׳",
            labelEn: "Genesis 1:1",
            customMetadata: ["sectionRef": "Genesis 1"]
        )
        let topic = TorahAssociationItem(
            id: "topic",
            kind: .topic,
            role: .context,
            providerID: "sefaria",
            externalID: "creation",
            canonicalKey: "creation",
            labelHe: "בריאה",
            labelEn: "Creation"
        )
        let probe = DelayedSessionAssociationProbe(responses: [
            .init(delay: .zero, records: [
                TorahStoredAssociationRecord(
                    location: .init(spaceId: spaceId, target: .block(objectId: objectId, blockId: "single")),
                    item: verse
                ),
                TorahStoredAssociationRecord(
                    location: .init(spaceId: spaceId, target: .block(objectId: objectId, blockId: "multiple")),
                    item: verse
                ),
                TorahStoredAssociationRecord(
                    location: .init(spaceId: spaceId, target: .block(objectId: objectId, blockId: "multiple")),
                    item: topic
                ),
                TorahStoredAssociationRecord(
                    location: .init(spaceId: spaceId, target: .block(objectId: objectId, blockId: "typed")),
                    item: topic
                )
            ])
        ])
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: try AnytypeTorahWorkspace.sefaria(),
            associations: probe
        )
        await session.refreshAssociationSnapshot()

        session.openLinkedAssociations(blockId: "single")
        #expect(session.selection == TorahInspectorSelection(
            providerID: "sefaria",
            canonicalRef: "Genesis 1",
            preferredSegmentRef: "Genesis 1:1",
            scope: .segment
        ))
        #expect(session.inspectorEntryMode == .relationships)
        #expect(!session.isSearchPresented)
        #expect(session.selection?.displayMetadata?.hebrew == "בראשית א׳:א׳")
        #expect(session.selection?.displayMetadata?.english == "Genesis 1:1")

        session.openLinkedAssociations(blockId: "multiple")
        #expect(session.selection == nil)
        #expect(!session.isSearchPresented)
        session.hostActions.onClose?()
        #expect(session.isSearchPresented)
        #expect(session.associationTargetBlockId == "multiple")

        session.isSearchPresented = false
        session.openLinkedAssociations(blockId: "typed")
        #expect(session.isSearchPresented)
        #expect(session.associationTargetBlockId == "typed")

        session.openAssociation(verse)
        #expect(!session.isSearchPresented)
        #expect(session.selection == nil)
        session.searchDidDismiss()
        #expect(session.selection?.relationshipRef == "Genesis 1:1")
    }

    @MainActor
    @Test("Resolved verses preserve section and exact-segment identity")
    func resolvedVerseSelection() throws {
        let resolved = ResolvedReference(
            canonical: "Genesis 1:1",
            labelHe: "בראשית א׳:א׳",
            nodeType: "JaggedArrayNode",
            depth: 2,
            startIndexes: [1, 1],
            firstAvailableSectionRef: "Genesis 1"
        )

        let selection = try TorahEditorSession.inspectorSelection(for: resolved)

        #expect(selection.canonicalRef == "Genesis 1")
        #expect(selection.preferredSegmentRef == "Genesis 1:1")
        #expect(selection.scope == .segment)
        #expect(selection.displayMetadata?.hebrew == "בראשית א׳:א׳")
    }

    @Test("Space, block, deletion, archive, and detail permissions are enforced")
    func targetAndPermissionGuards() async {
        let cases: [(NativeStoreProbe, TorahAssociationTarget, TorahAssociationRepositoryError)] = [
            (NativeStoreProbe(spaceId: "other", objectId: objectId, blockIds: []), .object(objectId: objectId), .targetOutsideSpace),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: []), .block(objectId: objectId, blockId: "missing"), .targetNotFound),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], isDeleted: true), .object(objectId: objectId), .targetNotFound),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], isArchived: true), .object(objectId: objectId), .targetNotFound),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], canWrite: false), .object(objectId: objectId), .permissionDenied)
        ]

        for (store, target, expected) in cases {
            let repository = makeRepository(store: store)
            do {
                _ = try await repository.addAssociation(association(4), target: target, spaceId: spaceId)
                Issue.record("Guarded mutation unexpectedly succeeded")
            } catch let error as TorahAssociationRepositoryError {
                #expect(error == expected)
            } catch {
                Issue.record("Unexpected error: \(error)")
            }
            #expect(await store.writeCount() == 0)
        }
    }

    @MainActor
    @Test("Header uses current canonical document links after block search and rejects inactive sessions")
    func documentHeaderUsesCanonicalSnapshot() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["previous-block"])
        let repository = makeRepository(store: store)
        let provider = SessionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: repository
        )
        let item = association(0)
        _ = try await repository.addAssociation(item, target: .object(objectId: objectId), spaceId: spaceId)
        _ = try await session.associationSnapshot(for: session.documentAssociationContext)
        session.presentSearch(scope: .block("previous-block"))

        var staleValue = item
        staleValue.canonicalKey = "Exodus 1:1"
        session.openDocumentAssociation(staleValue)
        session.searchDidDismiss()

        #expect(session.associationContext == session.documentAssociationContext)
        #expect(session.selection?.canonicalRef == "Genesis 1")
        #expect(session.selection?.preferredSegmentRef == "Genesis 1:1")

        session.selection = nil
        session.deactivateDocument()
        session.openDocumentAssociation(item)
        #expect(session.selection == nil)
        #expect(await store.writeCount() == 1)
    }

    @MainActor
    @Test("An unlinked header chip cannot open a stale source or change the active block target")
    func unlinkedDocumentHeaderChipIsRejected() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["previous-block"])
        let repository = makeRepository(store: store)
        let provider = SessionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId,
            objectId: objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: repository
        )
        session.presentSearch(scope: .block("previous-block"))
        session.openDocumentAssociation(association(0))

        #expect(session.associationContext.scope == .block("previous-block"))
        #expect(session.selection == nil)
        #expect(await store.writeCount() == 0)
    }

    @MainActor
    @Test("Property routes reset category and query while freezing the document target")
    func propertyRoutesResetCategoryAndTarget() throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["selected-block"])
        let session = TorahEditorSession(
            spaceId: spaceId, objectId: objectId,
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: makeRepository(store: store)
        )
        session.presentSearch(scope: .block("selected-block"))
        session.searchQuery = "old reference query"
        for category in [TorahEditorSession.SearchScope.topics, .words, .references, .topics, .references] {
            session.isSearchPresented = false
            session.presentSearch(scope: .document, initialCategory: category, host: .properties)
            let presenter = TorahSourcesSearchPresenter(
                session: session, context: session.associationContext,
                searchScope: session.searchScope, searchQuery: session.searchQuery, onOpenSelection: { _ in }
            )
            #expect(presenter.context == session.documentAssociationContext)
            #expect(presenter.searchScope == category)
            #expect(presenter.searchQuery.isEmpty)
            #expect(session.presentationHost == .properties)
            #expect(session.isSearchPresented)
            session.searchQuery = "previous category"
        }
        session.dismissPropertiesPresentation()
        #expect(session.presentationHost == .editor)
        #expect(!session.isSearchPresented)
        session.presentSearch(scope: .block("selected-block"))
        #expect(session.associationTargetBlockId == "selected-block")
        #expect(session.searchScope == .references)
    }

    @MainActor
    @Test("Read-only property actions and stale requests never mutate canonical storage")
    func propertyPermissionAndRequestGuards() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [])
        let repository = makeRepository(store: store)
        let session = TorahEditorSession(
            spaceId: spaceId, objectId: objectId,
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: repository
        )
        let item = association(0)
        _ = try await repository.addAssociation(item, target: .object(objectId: objectId), spaceId: spaceId)
        _ = try await session.associationSnapshot(for: session.documentAssociationContext)
        let result = TorahEditorSession.SearchResult(
            id: "reference", scope: .references, providerValue: "Genesis 1:1",
            labelHe: nil, labelEn: nil, fallbackTitle: "Genesis 1:1", fallbackSubtitle: nil
        )
        session.installAssociationEditingPolicy { false }
        _ = try await session.associationSnapshot(for: session.documentAssociationContext)
        #expect(session.documentPropertyProjection.sources == [item])
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            _ = try await session.unlinkAssociation(item, from: session.documentAssociationContext)
        }
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            _ = try await session.link(result, to: session.documentAssociationContext, rawQuery: "Genesis")
        }
        session.installAssociationEditingPolicy { true }
        await #expect(throws: CancellationError.self) {
            _ = try await session.link(result, to: session.documentAssociationContext, rawQuery: "Genesis", isCurrentRequest: { false })
        }
        #expect(await store.writeCount() == 1)
        session.deactivateDocument()
        session.presentSearch(scope: .document, initialCategory: .topics, host: .properties)
        #expect(!session.isSearchPresented)
        #expect(session.selection == nil)
    }

    @MainActor
    @Test("Canonical property values refresh by kind after unlink and survive a new session")
    func propertyProjectionRefreshesWithoutDuplicateStorage() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["block"])
        let repository = makeRepository(store: store)
        let session = TorahEditorSession(
            spaceId: spaceId, objectId: objectId,
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: repository
        )
        let source = association(0)
        let topic = association(1, kind: .topic)
        let word = association(2, kind: .word)
        for item in [source, topic, word] {
            _ = try await repository.addAssociation(item, target: .object(objectId: objectId), spaceId: spaceId)
        }
        _ = try await repository.addAssociation(association(3), target: .block(objectId: objectId, blockId: "block"), spaceId: spaceId)
        _ = try await session.associationSnapshot(for: session.documentAssociationContext)
        #expect(session.documentPropertyProjection.sources == [source])
        #expect(session.documentPropertyProjection.topics == [topic])
        #expect(session.documentPropertyProjection.words == [word])
        _ = try await session.unlinkAssociation(topic, from: session.documentAssociationContext)
        #expect(session.documentPropertyProjection.topics.isEmpty)
        #expect(session.documentPropertyProjection.sources == [source])
        #expect(session.linkedAssociationCount(blockId: "block") == 1)
        let reopened = TorahEditorSession(
            spaceId: spaceId, objectId: objectId,
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: repository
        )
        await reopened.refreshAssociationSnapshot()
        #expect(reopened.documentPropertyProjection == session.documentPropertyProjection)
        #expect(await store.unrelatedDetails() == ["name": "untouched", "custom": "preserved"])
    }

    @MainActor
    @Test("Dismissing during canonical resolution cancels storage and rapid taps submit once")
    func propertyPickerCancellationAndRapidTaps() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [])
        let provider = DelayedResolutionSearchProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider], topicProviders: [provider], lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let session = TorahEditorSession(
            spaceId: spaceId, objectId: objectId, workspace: AnytypeTorahWorkspace(registry: registry),
            associations: makeRepository(store: store)
        )
        let presenter = TorahSourcesSearchPresenter(
            session: session, context: session.documentAssociationContext, onOpenSelection: { _ in }
        )
        let old = TorahEditorSession.SearchResult(
            id: "old", scope: .references, providerValue: "old", labelHe: nil, labelEn: nil,
            fallbackTitle: "old", fallbackSubtitle: nil
        )
        let cancelled = Task { await presenter.link(old) }
        try await Task.sleep(for: .milliseconds(10))
        presenter.cancelPendingRequests()
        await cancelled.value
        #expect(await store.writeCount() == 0)
        let firstTap = Task { await presenter.link(old) }
        try await Task.sleep(for: .milliseconds(10))
        await presenter.link(old)
        await firstTap.value
        #expect(await provider.resolveCount(for: "old") == 2)
        #expect(await store.writeCount() == 1)
        #expect(session.documentPropertyProjection.sources.count == 1)
    }

    @MainActor
    @Test("Property composition preserves native and hidden rows and filters only canonical JSON")
    func propertyCompositionKeepsOriginalRows() throws {
        let manifest = PinkhaSpaceManifest(
            spaceId: spaceId, documentAssociationsPropertyId: "canonical-id", documentAssociationsPropertyKey: "canonical-key",
            registeredDocumentTypes: ["chiddush": "type-chiddush", "article": "type-article", "research": "type-research"]
        )
        for typeID in manifest.registeredDocumentTypes.values {
            let details = ObjectDetails(id: objectId, values: [BundledPropertyKey.type.rawValue: typeID.protobufValue])
            let document = MockBaseDocument(objectId: objectId, details: details)
            document.mockSpaceId = spaceId
            let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [])
            let session = TorahEditorSession(
                spaceId: spaceId, objectId: objectId, workspace: try AnytypeTorahWorkspace.sefaria(),
                associations: makeRepository(store: store)
            )
            let model = PinkhaTorahPropertiesModel(
                document: document, session: session, bootstrap: PropertiesBootstrapProbe(value: manifest)
            )
            #expect(model.isEligible)
            #expect(!model.canEdit)
            model.edit(.topic)
            #expect(!session.isSearchPresented)
            let originals = ["type", "tag", "links", "backlinks", "createdDate", "creator"].map { key in
                Property.text(Property.Text(
                    id: key, key: key, name: key, isFeatured: false, isEditable: true,
                    canBeRemovedFromObject: false, isDeleted: false, value: key
                ))
            }
            let raw = Property.text(Property.Text(
                id: "canonical-id", key: "canonical-key", name: "הקשר תורני", isFeatured: false,
                isEditable: true, canBeRemovedFromObject: false, isDeleted: false, value: "{\"version\":2,\"records\":[]}"
            ))
            let sections = [
                PropertiesSection(id: "normal", title: "normal", relations: originals, isMissingFields: false, isExpandable: false),
                PropertiesSection(id: "hidden", title: "hidden", relations: [raw, originals[0]], isMissingFields: false, isExpandable: true)
            ]
            let displayed = model.visibleSections(sections)
            #expect(displayed[0].relations == originals)
            #expect(displayed[1].relations == [originals[0]])
            #expect(sections[1].relations == [raw, originals[0]])
            document.mockPermissions.canEditRelationValues = true
            model.edit(.topic)
            #expect(session.isSearchPresented)
            #expect(session.searchScope == .topics)
            #expect(session.associationContext == session.documentAssociationContext)
        }
    }

    private func makeRepository(store: NativeStoreProbe) -> AnytypeTorahAssociationRepository {
        AnytypeTorahAssociationRepository(
            nativeStore: store,
            manifestProvider: ManifestProbe(spaceId: spaceId),
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter()
        )
    }

    private func association(
        _ index: Int,
        kind: TorahAssociationKind = .ref
    ) -> TorahAssociationItem {
        TorahAssociationItem(
            id: "association-\(index)",
            kind: kind,
            role: .context,
            providerID: "sefaria",
            externalID: "Genesis.1.\(index + 1)",
            canonicalKey: "Genesis 1:\(index + 1)",
            labelHe: "בראשית א",
            labelEn: "Genesis 1:\(index + 1)"
        )
    }
}

private actor DelayedSessionAssociationProbe: AnytypeTorahAssociationSnapshotRepository {
    struct Response: Sendable {
        let delay: Duration
        let records: [TorahStoredAssociationRecord]
    }

    private var responses: [Response]

    init(responses: [Response]) {
        self.responses = responses
    }

    func listAssociationRecords(
        objectId: String,
        spaceId: String
    ) async throws -> [TorahStoredAssociationRecord] {
        guard !responses.isEmpty else { return [] }
        let response = responses.removeFirst()
        try await Task.sleep(for: response.delay)
        return response.records
    }

    func listDocumentAssociations(
        objectId: String,
        spaceId: String
    ) async throws -> [TorahAssociationItem] {
        try await listAssociationRecords(objectId: objectId, spaceId: spaceId)
            .filter { $0.blockId == nil }
            .map(\.item)
    }

    func listBlockAssociations(
        objectId: String,
        blockId: String,
        spaceId: String
    ) async throws -> [TorahAssociationItem] {
        try await listAssociationRecords(objectId: objectId, spaceId: spaceId)
            .filter { $0.blockId == blockId }
            .map(\.item)
    }

    func addAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem {
        throw TorahAssociationRepositoryError.backendFailure("Unexpected mutation")
    }

    func addAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String,
        authorize: @escaping TorahAssociationWriteAuthorization
    ) async throws -> TorahAssociationItem {
        try await authorize()
        return try await addAssociation(item, target: target, spaceId: spaceId)
    }

    func upsertAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem {
        throw TorahAssociationRepositoryError.backendFailure("Unexpected mutation")
    }

    func updateAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem {
        throw TorahAssociationRepositoryError.backendFailure("Unexpected mutation")
    }

    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String,
                           authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        try await authorize()
        try await removeAssociation(associationId: associationId, target: target, spaceId: spaceId)
    }

    func removeAssociation(
        associationId: String,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws {
        throw TorahAssociationRepositoryError.backendFailure("Unexpected mutation")
    }
}

private struct ManifestProbe: TorahAssociationManifestProvider {
    let spaceId: String

    func manifest(spaceId requestedSpaceId: String) async throws -> PinkhaSpaceManifest {
        PinkhaSpaceManifest(
            spaceId: requestedSpaceId,
            parentPropertyId: "parent-id",
            parentPropertyKey: "parent-key",
            orderPropertyId: "order-id",
            orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "associations-id",
            documentAssociationsPropertyKey: "pinkha-associations",
            folderTypeId: "folder-id",
            bookFolderTypeId: "book-folder-id",
            registeredDocumentTypes: [
                PinkhaSchemaRoles.chiddushKey: "chiddush-id",
                PinkhaSchemaRoles.articleKey: "article-id",
                PinkhaSchemaRoles.researchKey: "research-id"
            ],
            defaultTemplateIds: [
                PinkhaSchemaRoles.chiddushKey: "chiddush-template",
                PinkhaSchemaRoles.articleKey: "article-template",
                PinkhaSchemaRoles.researchKey: "research-template"
            ]
        )
    }
}

private actor NativeStoreProbe: TorahAssociationNativeStore {
    enum WriteBehavior: Sendable {
        case succeed
        case persistThenThrow
        case throwWithoutPersisting
    }

    private let spaceId: String
    private let objectId: String
    private let blockIds: Set<String>
    private let isDeleted: Bool
    private let isArchived: Bool
    private let canWrite: Bool
    private let writeBehavior: WriteBehavior
    private var value: String?
    private var writes = 0
    private var concurrentWrites = 0
    private var maxConcurrentWrites = 0
    private let otherDetails = ["name": "untouched", "custom": "preserved"]
    private let blocks = ["block": "unchanged"]

    init(
        spaceId: String,
        objectId: String,
        blockIds: Set<String>,
        value: String? = nil,
        isDeleted: Bool = false,
        isArchived: Bool = false,
        canWrite: Bool = true,
        writeBehavior: WriteBehavior = .succeed
    ) {
        self.spaceId = spaceId
        self.objectId = objectId
        self.blockIds = blockIds
        self.value = value
        self.isDeleted = isDeleted
        self.isArchived = isArchived
        self.canWrite = canWrite
        self.writeBehavior = writeBehavior
    }

    func readDocument(
        spaceId: String,
        objectId: String,
        propertyKey: String
    ) async throws -> TorahAssociationNativeDocumentSnapshot {
        TorahAssociationNativeDocumentSnapshot(
            spaceId: self.spaceId,
            objectId: self.objectId,
            isDeleted: isDeleted,
            isArchived: isArchived,
            canWriteDetails: canWrite,
            blockIds: blockIds,
            propertyValue: value
        )
    }

    func writeDocumentProperty(objectId: String, propertyKey: String, value: String) async throws {
        writes += 1
        concurrentWrites += 1
        maxConcurrentWrites = max(maxConcurrentWrites, concurrentWrites)
        defer { concurrentWrites -= 1 }
        try await Task.sleep(for: .milliseconds(2))
        switch writeBehavior {
        case .succeed:
            self.value = value
        case .persistThenThrow:
            self.value = value
            throw ProbeError.lostAcknowledgement
        case .throwWithoutPersisting:
            throw ProbeError.lostAcknowledgement
        }
    }

    func writeCount() -> Int { writes }
    func maximumConcurrentWrites() -> Int { maxConcurrentWrites }
    func unrelatedDetails() -> [String: String] { otherDetails }
    func blockFingerprints() -> [String: String] { blocks }
}

private struct PropertiesBootstrapProbe: PinkhaSpaceBootstrapServiceProtocol {
    let value: PinkhaSpaceManifest

    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest { value }
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? { value.spaceId == spaceId ? value : nil }
    func isBootstrapped(spaceId: String) -> Bool { value.spaceId == spaceId }
}

private enum ProbeError: Error {
    case lostAcknowledgement
}

private enum SessionSearchProbeError: Error {
    case backendFailure
}

private struct SessionSearchProvider: ReferenceProvider, TopicProvider, LexicalProvider {
    let providerID = "session-search-probe"

    func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate] {
        [ReferenceCandidate(id: query, label: query)]
    }

    func resolveReference(_ input: String) async throws -> ResolvedReference {
        ResolvedReference(canonical: input, labelHe: input)
    }

    func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate] {
        [TopicCandidate(id: query, displayTitle: query)]
    }

    func resolveTopic(id: String) async throws -> ResolvedTopic {
        ResolvedTopic(slug: id, displayTitle: id)
    }

    func refreshTopicIndexIfNeeded() async throws {}

    func suggestWords(prefix: String, context: TorahLexicalContext?) async throws -> [WordCandidate] {
        if prefix == "old" {
            try await Task.sleep(for: .milliseconds(80))
        }
        if prefix == "none" { throw TorahError.noResults }
        if prefix == "failure" { throw SessionSearchProbeError.backendFailure }
        return [WordCandidate(id: prefix, surface: prefix, headword: prefix, lexicon: "fixture")]
    }

    func resolveWord(surface: String, context: TorahLexicalContext?) async throws -> [ResolvedWord] {
        try await suggestWords(prefix: surface, context: context).map { ResolvedWord(candidate: $0) }
    }
}

private actor DelayedResolutionSearchProvider: ReferenceProvider, TopicProvider, LexicalProvider {
    nonisolated let providerID = "delayed-resolution-probe"
    private var resolveCounts = [String: Int]()

    func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate] {
        [ReferenceCandidate(id: query, label: query)]
    }

    func resolveReference(_ input: String) async throws -> ResolvedReference {
        resolveCounts[input, default: 0] += 1
        if input == "old" {
            try await Task.sleep(for: .milliseconds(80))
        }
        return ResolvedReference(canonical: input, labelHe: input, labelEn: input)
    }

    func resolveCount(for input: String) -> Int { resolveCounts[input, default: 0] }

    func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate] { [] }
    func resolveTopic(id: String) async throws -> ResolvedTopic {
        ResolvedTopic(slug: id, displayTitle: id)
    }
    func refreshTopicIndexIfNeeded() async throws {}
    func suggestWords(prefix: String, context: TorahLexicalContext?) async throws -> [WordCandidate] { [] }
    func resolveWord(surface: String, context: TorahLexicalContext?) async throws -> [ResolvedWord] { [] }
}


@Suite("Canonical Torah manifest is independent of native derived registration")
struct TorahCanonicalManifestIsolationTests {
    @Test("A broken native Property provisioner cannot block canonical source linking")
    func canonicalLookupIgnoresUnrelatedNativeSchemaFailure() async throws {
        let manifest = PinkhaSpaceManifest(
            spaceId: "space", manifestObjectId: "manifest",
            parentPropertyId: "parent", parentPropertyKey: "parent-key",
            orderPropertyId: "order", orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "canonical", documentAssociationsPropertyKey: "canonical-key",
            folderTypeId: "folder", bookFolderTypeId: "book",
            registeredDocumentTypes: ["chiddush": "chiddush-id", "article": "article-id", "research": "research-id"],
            defaultTemplateIds: ["chiddush": "chiddush-template", "article": "article-template", "research": "research-template"]
        )
        let provider = BootstrapTorahAssociationManifestProvider(
            bootstrapService: FailedNativeSchemaBootstrapProbe(manifest: manifest)
        )
        let result = try await provider.manifest(spaceId: "space")
        #expect(result == manifest)
        #expect(result.isFullyProvisioned)
        #expect(result.documentAssociationsPropertyKey == "canonical-key")
        let store = NativeStoreProbe(spaceId: "space", objectId: "document", blockIds: [])
        let repository = AnytypeTorahAssociationRepository(
            nativeStore: store, manifestProvider: provider,
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter()
        )
        let source = TorahAssociationItem(
            id: "canonical-after-native-schema-error", kind: .ref, role: .context,
            providerID: "sefaria", externalID: "Genesis.1.1",
            canonicalKey: "Genesis 1:1", labelHe: "בראשית א"
        )
        _ = try await repository.addAssociation(
            source, target: .object(objectId: "document"), spaceId: "space"
        )
        #expect(try await repository.listDocumentAssociations(
            objectId: "document", spaceId: "space"
        ).map(\.id) == [source.id])
    }

    @Test("Canonical lookup still rejects a foreign Space")
    func canonicalLookupRejectsOtherSpace() async {
        let bootstrap = FailedNativeSchemaBootstrapProbe(manifest: PinkhaSpaceManifest(
            spaceId: "other", manifestObjectId: "manifest",
            parentPropertyId: "parent", parentPropertyKey: "parent-key",
            orderPropertyId: "order", orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "canonical", documentAssociationsPropertyKey: "canonical-key",
            folderTypeId: "folder", bookFolderTypeId: "book",
            registeredDocumentTypes: ["chiddush": "chiddush-id", "article": "article-id", "research": "research-id"],
            defaultTemplateIds: ["chiddush": "chiddush-template", "article": "article-template", "research": "research-template"]
        ))
        do {
            _ = try await BootstrapTorahAssociationManifestProvider(bootstrapService: bootstrap)
                .manifest(spaceId: "space")
            Issue.record("Wrong-Space canonical bootstrap was incorrectly accepted")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == .targetOutsideSpace)
        } catch {
            Issue.record("Unexpected wrong-Space error: \(error)")
        }
    }

    @Test("Canonical linking works for source, topic, and word targets despite native schema failure")
    func canonicalLinkingAllKindsSucceeds() async throws {
        let manifest = PinkhaSpaceManifest(
            spaceId: "space", manifestObjectId: "manifest",
            parentPropertyId: "parent", parentPropertyKey: "parent-key",
            orderPropertyId: "order", orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "canonical", documentAssociationsPropertyKey: "canonical-key",
            folderTypeId: "folder", bookFolderTypeId: "book",
            registeredDocumentTypes: ["chiddush": "chiddush-id", "article": "article-id", "research": "research-id"],
            defaultTemplateIds: ["chiddush": "chiddush-template", "article": "article-template", "research": "research-template"]
        )
        let provider = BootstrapTorahAssociationManifestProvider(
            bootstrapService: FailedNativeSchemaBootstrapProbe(manifest: manifest)
        )
        let store = NativeStoreProbe(spaceId: "space", objectId: "document", blockIds: ["block-1"])
        let repository = AnytypeTorahAssociationRepository(
            nativeStore: store, manifestProvider: provider,
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter()
        )
        let source = TorahAssociationItem(
            id: "canon-src", kind: .ref, role: .context,
            providerID: "sefaria", externalID: "Genesis.1.1",
            canonicalKey: "Genesis 1:1", labelHe: "בראשית א:א"
        )
        let topic = TorahAssociationItem(
            id: "canon-top", kind: .topic, role: .context,
            providerID: "sefaria", externalID: "creation",
            canonicalKey: "creation", labelHe: "בריאה"
        )
        let word = TorahAssociationItem(
            id: "canon-wrd", kind: .word, role: .context,
            providerID: "sefaria", externalID: "בראשית",
            canonicalKey: "בראשית", labelHe: "בראשית"
        )

        // Document target
        _ = try await repository.addAssociation(source, target: .object(objectId: "document"), spaceId: "space")
        _ = try await repository.addAssociation(topic, target: .object(objectId: "document"), spaceId: "space")
        _ = try await repository.addAssociation(word, target: .object(objectId: "document"), spaceId: "space")

        let docItems = try await repository.listDocumentAssociations(objectId: "document", spaceId: "space")
        #expect(docItems.count == 3)
        #expect(Set(docItems.map(\.id)) == ["canon-src", "canon-top", "canon-wrd"])

        // Block target
        let blockItem = TorahAssociationItem(
            id: "canon-blk", kind: .ref, role: .sourceQuote,
            providerID: "sefaria", externalID: "Exodus.1.1",
            canonicalKey: "Exodus 1:1", labelHe: "שמות א:א"
        )
        _ = try await repository.addAssociation(blockItem, target: .block(objectId: "document", blockId: "block-1"), spaceId: "space")
        let blkItems = try await repository.listBlockAssociations(objectId: "document", blockId: "block-1", spaceId: "space")
        #expect(blkItems.map(\.id) == ["canon-blk"])

        // Unlink and relink
        try await repository.removeAssociation(associationId: "canon-top", target: .object(objectId: "document"), spaceId: "space")
        let afterRemove = try await repository.listDocumentAssociations(objectId: "document", spaceId: "space")
        #expect(Set(afterRemove.map(\.id)) == ["canon-src", "canon-wrd"])

        _ = try await repository.addAssociation(topic, target: .object(objectId: "document"), spaceId: "space")
        let afterRelink = try await repository.listDocumentAssociations(objectId: "document", spaceId: "space")
        #expect(Set(afterRelink.map(\.id)) == ["canon-src", "canon-wrd", "canon-top"])
    }

    @Test("Protocol extension default implementation delegates to bootstrapSpace")
    func protocolExtensionDefaultDelegates() async throws {
        struct LegacyBootstrapProbe: PinkhaSpaceBootstrapServiceProtocol {
            let manifest: PinkhaSpaceManifest
            func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest { manifest }
            func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? { manifest }
            func isBootstrapped(spaceId: String) -> Bool { true }
        }
        let manifest = PinkhaSpaceManifest(
            spaceId: "space", manifestObjectId: "manifest",
            parentPropertyId: "parent", parentPropertyKey: "parent-key",
            orderPropertyId: "order", orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "canonical", documentAssociationsPropertyKey: "canonical-key",
            folderTypeId: "folder", bookFolderTypeId: "book",
            registeredDocumentTypes: ["chiddush": "chiddush-id", "article": "article-id", "research": "research-id"],
            defaultTemplateIds: ["chiddush": "chiddush-template", "article": "article-template", "research": "research-template"]
        )
        let probe = LegacyBootstrapProbe(manifest: manifest)
        let result = try await probe.bootstrapCanonicalSpace(spaceId: "space")
        #expect(result == manifest)
    }

    @Test("Canonical repository linking operations succeed while UI generic editing is rejected")
    func canonicalRepositoryOperationsSucceedWhileUIEditingBlocked() async throws {
        struct LocalBootstrapProbe: PinkhaSpaceBootstrapServiceProtocol {
            let manifest: PinkhaSpaceManifest
            func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest { manifest }
            func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? { manifest }
            func isBootstrapped(spaceId: String) -> Bool { true }
        }
        let manifest = PinkhaSpaceManifest(
            spaceId: "space", manifestObjectId: "manifest",
            parentPropertyId: "parent", parentPropertyKey: "parent-key",
            orderPropertyId: "order", orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "canonical-prop-id", documentAssociationsPropertyKey: "canonical-prop-key",
            folderTypeId: "folder", bookFolderTypeId: "book",
            registeredDocumentTypes: ["chiddush": "chiddush-id", "article": "article-id", "research": "research-id"],
            defaultTemplateIds: ["chiddush": "chiddush-template", "article": "article-template", "research": "research-template"]
        )
        let probe = LocalBootstrapProbe(manifest: manifest)
        let policy = PinkhaTorahPropertyPolicy(bootstrapService: probe)

        // UI generic text editing is blocked on canonical storage (H08)
        #expect(!policy.canEditGenericPropertyValue(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space"))
        #expect(policy.isCanonicalStorage(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space"))

        // Legitimate repository linking paths continue to operate without interference (H15)
        let store = NativeStoreProbe(spaceId: "space", objectId: "doc-1", blockIds: [])
        let repository = AnytypeTorahAssociationRepository(
            nativeStore: store,
            manifestProvider: BootstrapTorahAssociationManifestProvider(bootstrapService: probe),
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter()
        )

        let item = TorahAssociationItem(
            id: "canon-test-item",
            kind: .ref,
            role: .context,
            providerID: "sefaria",
            externalID: "Genesis.1.1",
            canonicalKey: "Genesis 1:1",
            labelHe: "בראשית א:א"
        )

        // Adding association via canonical repository succeeds
        let stored = try await repository.addAssociation(item, target: .object(objectId: "doc-1"), spaceId: "space")
        #expect(stored.id == "canon-test-item")

        // Reading association returns item
        let list = try await repository.listDocumentAssociations(objectId: "doc-1", spaceId: "space")
        #expect(list.map(\.id) == ["canon-test-item"])

        // Removing association succeeds
        try await repository.removeAssociation(associationId: "canon-test-item", target: .object(objectId: "doc-1"), spaceId: "space")
        let emptyList = try await repository.listDocumentAssociations(objectId: "doc-1", spaceId: "space")
        #expect(emptyList.isEmpty)
    }

}

private struct FailedNativeSchemaBootstrapProbe: PinkhaSpaceBootstrapServiceProtocol {
    let manifestValue: PinkhaSpaceManifest

    init(manifest: PinkhaSpaceManifest) { self.manifestValue = manifest }

    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        throw TorahNativeSchemaError.invalidProperty("pinkhaTorahSources")
    }

    func bootstrapCanonicalSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        manifestValue
    }

    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? { manifestValue }
    func isBootstrapped(spaceId: String) -> Bool { true }
}

extension TorahAssociationNativeRepositoryTests {
    @Test("Source drop previews respect native property restrictions without changing internal moves")
    @MainActor
    func sourceDropPreviewHonorsNativePropertyRestrictions() {
        let details = ObjectDetails(id: objectId, values: [:])
        let cases: [(restrictions: [ObjectRestriction], blocks: Bool, relations: Bool)] = [
            ([], true, true),
            ([.details], true, false),
            ([.blocks], false, true),
            ([.details, .blocks], false, false)
        ]

        for item in cases {
            let permissions = ObjectPermissions(
                details: details,
                isLocked: false,
                participantCanEdit: true,
                isVersionMode: false,
                objectRestrictions: item.restrictions
            )
            #expect(permissions.canEditBlocks == item.blocks)
            #expect(permissions.canEditRelationValues == item.relations)
            #expect(!details.isReadonly)

            let source = TorahEditorSafetyPolicy.dropOperation(
                containsTorahSource: true,
                canEditBlocks: permissions.canEditBlocks,
                canEditRelationValues: permissions.canEditRelationValues,
                isReadonly: details.isReadonly,
                canPlace: true
            )
            #expect(source == (item.restrictions.isEmpty ? .copy : .forbidden))
            #expect(TorahEditorSafetyPolicy.canInsertSource(
                canEditBlocks: permissions.canEditBlocks,
                canEditRelationValues: permissions.canEditRelationValues,
                isReadonly: details.isReadonly
            ) == item.restrictions.isEmpty)
            #expect(TorahEditorSafetyPolicy.dropOperation(
                containsTorahSource: false,
                canEditBlocks: permissions.canEditBlocks,
                canEditRelationValues: permissions.canEditRelationValues,
                isReadonly: details.isReadonly,
                canPlace: true
            ) == (item.blocks ? .move : .forbidden))
        }
    }

    @Test("Source drop previews require explicitly writable document details")
    @MainActor
    func sourceDropPreviewRequiresExplicitWritableDetails() {
        let writable = ObjectDetails(id: objectId, values: [
            BundledPropertyKey.isReadonly.rawValue: Google_Protobuf_Value.with { $0.boolValue = false }
        ])
        let readonly = ObjectDetails(id: objectId, values: [
            BundledPropertyKey.isReadonly.rawValue: Google_Protobuf_Value.with { $0.boolValue = true }
        ])
        let permissions = ObjectPermissions(
            details: writable,
            isLocked: false,
            participantCanEdit: true,
            isVersionMode: false,
            objectRestrictions: []
        )
        #expect(permissions.canEditBlocks && permissions.canEditRelationValues)
        #expect(!writable.isReadonly && readonly.isReadonly)
        let cases: [(details: ObjectDetails?, canInsert: Bool)] = [
            (writable, true), (readonly, false), (nil, false)
        ]

        for item in cases {
            #expect(TorahEditorSafetyPolicy.dropOperation(
                containsTorahSource: true,
                canEditBlocks: permissions.canEditBlocks,
                canEditRelationValues: permissions.canEditRelationValues,
                isReadonly: item.details?.isReadonly,
                canPlace: true
            ) == (item.canInsert ? .copy : .forbidden))
            #expect(TorahEditorSafetyPolicy.canInsertSource(
                canEditBlocks: permissions.canEditBlocks,
                canEditRelationValues: permissions.canEditRelationValues,
                isReadonly: item.details?.isReadonly
            ) == item.canInsert)
            #expect(TorahEditorSafetyPolicy.dropOperation(
                containsTorahSource: false,
                canEditBlocks: permissions.canEditBlocks,
                canEditRelationValues: permissions.canEditRelationValues,
                isReadonly: item.details?.isReadonly,
                canPlace: true
            ) == .move)
            for containsSource in [false, true] {
                #expect(TorahEditorSafetyPolicy.dropOperation(
                    containsTorahSource: containsSource,
                    canEditBlocks: permissions.canEditBlocks,
                    canEditRelationValues: permissions.canEditRelationValues,
                    isReadonly: item.details?.isReadonly,
                    canPlace: false
                ) == .forbidden)
            }
        }
    }
}

// These tests exercise the actual Heart service and canonical repository. Only
// the native store and the unrelated object/block creation services are controlled.
// Select this suite alone: .serialized does not serialize unrelated test suites.
import Factory
import AnytypeCore
import ProtobufMessages
import protocol PinkhaTorahPresentation.TorahEditorNotesService

@Suite("Heart Note repository dispatch authority", .serialized)
@MainActor
struct TorahNoteRepositoryAuthorityTests {
    enum CreationPhase: String, CaseIterable, Sendable { case source, origin }
    enum UnlinkPhase: String, CaseIterable, Sendable { case noteSource, noteOrigin, related }
    enum Retirement: String, CaseIterable, Sendable { case inspectorReopen, documentReopen }

    @Test("Create-note metadata rechecks the original presentation after the repository read",
          arguments: CreationPhase.allCases, Retirement.allCases)
    func noteCreationRejectsRetiredRepositoryDispatch(
        phase: CreationPhase, retirement: Retirement
    ) async throws {
        let fixture = try HeartNoteAuthorityFixture(
            seededNote: false, heldObjectID: phase == .source ? "note" : "origin", heldRead: 1)
        let protectedBefore = try await fixture.store.protectedRecords()
        fixture.startCreation()
        do {
            try await fixture.store.waitUntilHeld()
            let beforeRetirement = await fixture.store.rawValues()
            let writesBeforeRetirement = await fixture.store.writtenObjects()
            #expect(writesBeforeRetirement == (phase == .source ? [] : ["note"]))
            fixture.retire(retirement)
            await fixture.store.release()
            try await fixture.waitForCreationCompletion(1)

            // A successful earlier phase remains intact; this is not rollback.
            #expect(await fixture.store.rawValues() == beforeRetirement)
            #expect(await fixture.store.writtenObjects() == writesBeforeRetirement)
            #expect(fixture.didChange == 0)
            #expect(fixture.opened.isEmpty)
            #expect(fixture.session.message == HeartNoteAuthorityFixture.currentMessage)
            #expect(fixture.observedNotes.lastCreationRecoveryError is CancellationError)
            let partial = await fixture.services.counts()
            #expect(partial.created == 1 && partial.deleted == 0)
            #expect(partial.lines == (phase == .source ? 0 : 1))

            // A deliberate current action resumes the original pending Note.
            fixture.startCreation()
            try await fixture.waitForCreationCompletion(2)
            try await fixture.waitForOpenedNote()
            #expect(fixture.didChange == 1)
            #expect(fixture.opened == ["note"])
            #expect(fixture.openedBlocks == [nil])
            #expect(fixture.observedNotes.lastCreationRecoveryError == nil)
            let completed = await fixture.services.counts()
            #expect(completed.created == 1 && completed.lines == 1 && completed.deleted == 0)
            let note = try await fixture.repository.listDocumentAssociations(objectId: "note", spaceId: "space")
            let origin = try await fixture.repository.listDocumentAssociations(objectId: "origin", spaceId: "space")
            #expect(note.filter(fixture.source.matches).count == 1)
            #expect(origin.filter { $0.customMetadata?["anytypeNoteObjectId"] == "note" &&
                $0.customMetadata?["torahSelectionId"] == fixture.selection.id }.count == 1)
            #expect(try await fixture.store.protectedRecords() == protectedBefore)
        } catch let firstFailure {
            // Retire before sampling actual service entries, so a queued old
            // action cannot enter later. This drains entered service calls only;
            // a refresh already entered after service return is not a Task join.
            fixture.session.deactivateDocument()
            let entered = fixture.observedNotes.creationsEntered
            await fixture.store.release()
            do {
                try await fixture.waitForCreationCompletion(entered)
            } catch let cleanupFailure {
                Issue.record("Secondary creation-service cleanup failure: entered=\(entered), completed=\(fixture.observedNotes.creationsCompleted), error=\(String(describing: cleanupFailure)); the first failure is rethrown.")
            }
            throw firstFailure
        }
    }

    @Test("Note and related-document unlink recheck authority inside their canonical write",
          arguments: UnlinkPhase.allCases, Retirement.allCases)
    func unlinkRejectsRetiredRepositoryDispatch(
        phase: UnlinkPhase, retirement: Retirement
    ) async throws {
        let fixture = try HeartNoteAuthorityFixture(
            seededNote: true, heldObjectID: phase == .noteOrigin ? "origin" : "note", heldRead: 2)
        let protectedBefore = try await fixture.store.protectedRecords()
        let request = Task { @MainActor in await fixture.unlink(phase) }
        do {
            try await fixture.store.waitUntilHeld()
            let beforeRetirement = await fixture.store.rawValues()
            let writesBeforeRetirement = await fixture.store.writtenObjects()
            #expect(writesBeforeRetirement == (phase == .noteOrigin ? ["note"] : []))
            fixture.retire(retirement)
            await fixture.store.release()
            await request.value

            #expect(await fixture.store.rawValues() == beforeRetirement)
            #expect(await fixture.store.writtenObjects() == writesBeforeRetirement)
            #expect(fixture.didChange == 0)
            #expect(fixture.session.message == HeartNoteAuthorityFixture.currentMessage)
            #expect(try await fixture.store.protectedRecords() == protectedBefore)

            // The current retry completes only the remaining selected links.
            await fixture.unlink(phase)
            #expect(fixture.didChange == 1)
            let note = try await fixture.repository.listDocumentAssociations(objectId: "note", spaceId: "space")
            let origin = try await fixture.repository.listDocumentAssociations(objectId: "origin", spaceId: "space")
            #expect(!note.contains(where: fixture.source.matches))
            #expect(origin.contains { $0.id == "origin-note" } == (phase == .related))
            #expect(try await fixture.store.protectedRecords() == protectedBefore)
            let counts = await fixture.services.counts()
            #expect(counts.created == 0 && counts.lines == 0 && counts.deleted == 0)
        } catch {
            request.cancel()
            fixture.session.deactivateDocument()
            await fixture.store.release()
            await request.value
            throw error
        }
    }
}

@MainActor
private final class HeartNoteAuthorityFixture {
    static let currentMessage = "Current reopened presentation"
    let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")
    let selection: TorahInspectorSelection
    let store: HeartNoteAuthorityStore
    let repository: AnytypeTorahAssociationRepository
    let services: HeartNoteCreationServices
    let observedNotes: HeartNoteObservedService
    let session: TorahEditorSession
    var didChange = 0
    var opened: [String] = []
    var openedBlocks: [String?] = []

    init(seededNote: Bool, heldObjectID: String, heldRead: Int) throws {
        let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3:3")
        let services = HeartNoteCreationServices()
        let store = try HeartNoteAuthorityStore(
            seededNote: seededNote, selectionID: selection.id,
            heldObjectID: heldObjectID, heldRead: heldRead)
        let repository = AnytypeTorahAssociationRepository(
            nativeStore: store, manifestProvider: ManifestProbe(spaceId: "space"),
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter())
        // Exact pinned Factory 2.3.1 resolves @Injected eagerly. Restore the
        // complete prior registration/cache state before the first await.
        let service: AnytypeTorahNotesService = {
            Container.shared.manager.push()
            defer { Container.shared.manager.pop() }
            Container.shared.objectActionsService.register { services }
            Container.shared.blockService.register { services }
            return AnytypeTorahNotesService(spaceId: "space", objectId: "origin", associations: repository)
        }()
        let observedNotes = HeartNoteObservedService(service)
        let session = TorahEditorSession(spaceId: "space", objectId: "origin",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: repository,
            notesService: observedNotes)
        self.selection = selection
        self.services = services
        self.store = store
        self.repository = repository
        self.observedNotes = observedNotes
        self.session = session
        session.installOpenObjectHandler { [weak self] object, block in
            self?.opened.append(object); self?.openedBlocks.append(block)
        }
        session.openResolvedReferenceFromStandaloneSearch(selection)
    }

    func retire(_ kind: TorahNoteRepositoryAuthorityTests.Retirement) {
        switch kind {
        case .inspectorReopen: session.hostActions.onClose?()
        case .documentReopen:
            session.deactivateDocument()
            session.activateDocument()
        }
        session.openResolvedReferenceFromStandaloneSearch(selection)
        session.message = Self.currentMessage
    }

    func startCreation() {
        guard let action = session.hostActions.onAddNote else {
            Issue.record("The original Add Note action is missing"); return
        }
        action(selection) { [weak self] in self?.didChange += 1 }
    }

    func waitForCreationCompletion(_ count: Int) async throws {
        let clock = ContinuousClock()
        let end = clock.now.advanced(by: .seconds(3))
        while observedNotes.creationsCompleted < count {
            guard clock.now < end else { throw HeartNoteAuthorityFailure.deadline }
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    func waitForOpenedNote() async throws {
        let clock = ContinuousClock()
        let end = clock.now.advanced(by: .seconds(3))
        while opened.isEmpty {
            guard clock.now < end else { throw HeartNoteAuthorityFailure.deadline }
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    func unlink(_ phase: TorahNoteRepositoryAuthorityTests.UnlinkPhase) async {
        if phase == .related {
            let row = TorahRelatedDocument(id: "related-note", spaceID: "space", objectID: "note",
                title: "Note", sourceReference: source.canonicalReference, canUnlink: true)
            await session.unlink(document: row, for: selection) { [weak self] in self?.didChange += 1 }
        } else {
            let note = TorahInspectorNote(id: "origin-note", selectedText: source.canonicalReference,
                                           note: "Note", tag: "Anytype")
            await session.unlink(note: note, for: selection) { [weak self] in self?.didChange += 1 }
        }
    }
}

// This observer delegates every operation to the production Heart service. Its
// counters permit bounded observation of every service call that entered. They
// do not prove completion of the original UI action's later refresh continuation.
@MainActor
private final class HeartNoteObservedService: TorahEditorNotesService {
    let original: AnytypeTorahNotesService
    var creationsEntered = 0
    var creationsCompleted = 0
    var lastCreationRecoveryError: (any Error)?
    init(_ original: AnytypeTorahNotesService) { self.original = original }
    func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] {
        try await original.notes(for: selection)
    }
    func relatedDocuments(for selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot {
        try await original.relatedDocuments(for: selection)
    }
    func createNote(for selection: TorahInspectorSelection,
                    authorize: @escaping TorahAssociationWriteAuthorization) async throws -> T5NoteCreationOutcome {
        creationsEntered += 1
        defer { creationsCompleted += 1 }
        let outcome = try await original.createNote(for: selection, authorize: authorize)
        lastCreationRecoveryError = outcome.recoveryError
        return outcome
    }
    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? {
        try await original.noteObjectId(noteId: noteId, for: selection)
    }
    func unlink(noteId: String, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        try await original.unlink(noteId: noteId, for: selection, authorize: authorize)
    }
    func unlink(document: TorahRelatedDocument, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        try await original.unlink(document: document, for: selection, authorize: authorize)
    }
}

private enum HeartNoteAuthorityFailure: Error { case deadline, unexpectedCall, invalidFixture }

private actor HeartNoteAuthorityStore: TorahAssociationNativeStore {
    private var values: [String: String] = [:]
    private var reads: [String: Int] = [:]
    private var writes: [String] = []
    private let heldObjectID: String
    private let heldRead: Int
    private var held = false
    private var released = false
    private var continuation: CheckedContinuation<Void, Never>?

    init(seededNote: Bool, selectionID: String, heldObjectID: String, heldRead: Int) throws {
        self.heldObjectID = heldObjectID; self.heldRead = heldRead
        let codec = TorahAssociationPayloadCodec()
        for objectID in ["origin", "note"] {
            let location = TorahAssociationLocation(spaceId: "space", target: .object(objectId: objectID))
            let anchor = try PinkhaSemanticTextAnchor(spaceID: "space", objectID: objectID)
            var kept = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Exodus 1:1").item
            kept.id = "keep-semantic-" + objectID
            kept = try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: kept, location: location)
            var quote = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3").item
            quote.id = "keep-quote-" + objectID; quote.role = .sourceQuote
            quote.customMetadata = ["snapshotText": "Original quoted text"]
            var records = [TorahStoredAssociationRecord(location: location, item: kept),
                TorahStoredAssociationRecord(location: .init(spaceId: "space",
                    target: .block(objectId: objectID, blockId: "quote-block")), item: quote)]
            if seededNote {
                let item: TorahAssociationItem
                if objectID == "note" {
                    var source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3").item
                    source.id = "selected-source"; item = source
                } else {
                    item = TorahAssociationItem(id: "origin-note", kind: .ref, role: .context,
                        providerID: "sefaria", externalID: "note", canonicalKey: "anytype-note:note",
                        labelHe: "Note", customMetadata: ["anytypeNoteObjectId": "note", "torahSelectionId": selectionID])
                }
                records.append(.init(location: location, item: item))
            }
            let data = try codec.encodeCanonicalDocument(.init(records: records,
                unknownFields: ["unrelated-native-field": .string("preserved-" + objectID)]))
            guard let raw = String(data: data, encoding: .utf8) else { throw HeartNoteAuthorityFailure.invalidFixture }
            values[objectID] = raw
        }
    }

    func readDocument(spaceId: String, objectId: String,
                      propertyKey: String) async throws -> TorahAssociationNativeDocumentSnapshot {
        guard spaceId == "space", propertyKey == "pinkha-associations", let value = values[objectId] else {
            throw HeartNoteAuthorityFailure.invalidFixture
        }
        reads[objectId, default: 0] += 1
        if objectId == heldObjectID, reads[objectId] == heldRead {
            held = true
            if !released { await withCheckedContinuation { continuation = $0 } }
            // Intentionally non-cooperative: the real repository must perform
            // its original post-read caller-authorization check.
        }
        return .init(spaceId: "space", objectId: objectId, isDeleted: false, isArchived: false,
            canWriteDetails: true, blockIds: ["quote-block"], propertyValue: value)
    }

    func writeDocumentProperty(objectId: String, propertyKey: String, value: String) throws {
        guard values[objectId] != nil, propertyKey == "pinkha-associations" else {
            throw HeartNoteAuthorityFailure.invalidFixture
        }
        writes.append(objectId); values[objectId] = value
    }
    func rawValues() -> [String: Data] { values.mapValues { Data($0.utf8) } }
    func writtenObjects() -> [String] { writes }
    func release() { released = true; continuation?.resume(); continuation = nil }
    func waitUntilHeld() async throws {
        let clock = ContinuousClock()
        let end = clock.now.advanced(by: .seconds(3))
        while !held {
            guard clock.now < end else { throw HeartNoteAuthorityFailure.deadline }
            try await Task.sleep(for: .milliseconds(5))
        }
    }
    func protectedRecords() throws -> [String: Data] {
        let codec = TorahAssociationPayloadCodec()
        var result: [String: Data] = [:]
        for (objectID, raw) in values {
            let payload = try codec.decodeCanonicalDocument(raw,
                legacyLocation: .init(spaceId: "space", target: .object(objectId: objectID)))
            result[objectID] = try codec.encodeCanonicalDocument(.init(
                records: payload.records.filter { $0.item.id.hasPrefix("keep-") },
                unknownFields: payload.unknownFields))
        }
        return result
    }
}

// The production service still chooses .note and invokes the original source
// line phase. No native object/HTTP/engine acceptance is inferred from this stub.
private actor HeartNoteCreationServices: ObjectActionsServiceProtocol, BlockServiceProtocol {
    struct Counts: Sendable { let created: Int; let lines: Int; let deleted: Int }
    private var created = 0
    private var lines = 0
    private var deleted = 0
    func counts() -> Counts { .init(created: created, lines: lines, deleted: deleted) }
    func createObject(name: String, typeUniqueKey: ObjectTypeUniqueKey,
        shouldDeleteEmptyObject: Bool, shouldSelectType: Bool, shouldSelectTemplate: Bool,
        spaceId: String, origin: ObjectOrigin, templateId: String?, createdInContext: String,
        createdInContextRef: String, additionalDetails: [BundledDetails]) async throws -> ObjectDetails {
        guard typeUniqueKey == .note, spaceId == "space", !shouldDeleteEmptyObject,
              !shouldSelectType, !shouldSelectTemplate, templateId == nil,
              createdInContext.isEmpty, createdInContextRef.isEmpty, additionalDetails.isEmpty else {
            throw HeartNoteAuthorityFailure.unexpectedCall
        }
        created += 1
        return ObjectDetails(id: "note", values: [BundledPropertyKey.name.rawValue: name.protobufValue])
    }
    func lastBlockId(from objectId: String, spaceId: String) async throws -> String {
        guard objectId == "note", spaceId == "space" else { throw HeartNoteAuthorityFailure.unexpectedCall }
        return "note-header"
    }
    func add(contextId: String, targetId: String, info: BlockInformation, position: BlockPosition) async throws -> String {
        guard contextId == "note", targetId == "note-header", position == .bottom else {
            throw HeartNoteAuthorityFailure.unexpectedCall
        }
        lines += 1; return "note-source-line"
    }
    func delete(objectIds: [String]) async throws { deleted += 1; throw HeartNoteAuthorityFailure.unexpectedCall }
    func setArchive(objectIds: [String], _ isArchived: Bool) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setPin(objectIds: [String], _ isPinned: Bool) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setLocked(_ isLocked: Bool, objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func updateLayout(contextID: String, value: Int) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func duplicate(objectId: String) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
    func applyTemplate(objectId: String, templateId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func updateBundledDetails(contextID: String, details: [BundledDetails]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func updateDetails(contextId: String, relationKey: String, value: DataviewGroupValue) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setInternalFlags(contextId: String, internalFlags: [Int]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func addObjectsToCollection(contextId: String, objectIds: [String]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setObjectType(objectId: String, typeUniqueKey: ObjectTypeUniqueKey) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setObjectSetType(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setObjectCollectionType(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setSource(objectId: String, source: [String]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func undo(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func redo(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func move(dashboadId: String, blockId: String, dropPositionblockId: String, position: Anytype_Model_Block.Position) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func createSet(name: String, iconEmoji: Emoji?, setOfObjectType: String, spaceId: String) async throws -> ObjectDetails { throw HeartNoteAuthorityFailure.unexpectedCall }
    func addFirstBlock(contextId: String, info: BlockInformation) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
    func delete(contextId: String, blockIds: [String]) async throws { deleted += 1; throw HeartNoteAuthorityFailure.unexpectedCall }
    func duplicate(contextId: String, targetId: String, blockIds: [String], position: BlockPosition) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func move(contextId: String, blockIds: [String], targetContextID: String, dropTargetID: String, position: BlockPosition) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setAlign(objectId: String, blockIds: [String], alignment: LayoutAlignment) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setBackgroundColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setFields(objectId: String, blockId: String, fields: BlockFields) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setBlockColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func replace(objectId: String, blockIds: [String], targetId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func replaceBlock(contextId: String, blockId: String, info: BlockInformation) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
    func move(objectId: String, blockId: String, targetId: String, position: Anytype_Model_Block.Position) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func moveToPage(objectId: String, blockIds: [String], pageId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setLinkAppearance(objectId: String, blockIds: [String], appearance: BlockLink.Appearance) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func changeMarkup(objectId: String, blockIds: [String], markType: MarkupType) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func convertChildrenToObjects(contextId: String, blocksIds: [String], typeUniqueKey: ObjectTypeUniqueKey, templateId: String) async throws -> [String] { throw HeartNoteAuthorityFailure.unexpectedCall }
    func createBlockLink(contextId: String, targetId: String, spaceId: String, details: [BundledDetails], typeUniqueKey: ObjectTypeUniqueKey, position: BlockPosition, templateId: String) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
}
