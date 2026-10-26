import Foundation
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
