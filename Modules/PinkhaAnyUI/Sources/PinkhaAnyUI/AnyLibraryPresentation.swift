#if canImport(SwiftUI)
import Foundation
import Observation
import SwiftUI
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

private enum AnyLibraryOpenError: Error { case setupMissing }

public struct AnyLibraryDocument: Identifiable, Sendable, Equatable {
    public let id: String
    public let title: String
    public let isNote: Bool
    public let snippet: String?
}

public struct AnyLibraryPendingCreation: Identifiable, Sendable {
    public var id: String { plan.mutationID }
    public let plan: AnyHierarchyCreationPlan
    public let isNote: Bool
    public var error: String?
    public var confirmedObjectID: String?
}

@MainActor @Observable
public final class AnyLibraryPresentation {
    public private(set) var hierarchyPresentation: AnyHierarchyPresentationState
    public var hierarchy: AnyHierarchySnapshot? { hierarchyPresentation.snapshot }
    public private(set) var allDocuments: [AnyLibraryDocument] = []
    public private(set) var searchResults: [AnyLibraryDocument] = []
    public private(set) var pendingCreations: [AnyLibraryPendingCreation] = []
    public private(set) var pendingMoves: Set<String> = []
    public private(set) var isLoading = false
    public private(set) var isSearching = false
    public private(set) var requiresSetup = false
    public private(set) var canWrite = false
    public var message: String?
    public var searchQuery = ""
    public var onOpenDocument: ((String, String?) -> Void)?
    public var isReady: Bool { hierarchy != nil && marker != nil && operations != nil }
    @ObservationIgnored public let client: AnyHTTPClient
    @ObservationIgnored public let session: AnyApplicationSession
    @ObservationIgnored public let objects: AnyNativeObjectCreator
    @ObservationIgnored public let blocks: AnyNativeBlockCreator
    @ObservationIgnored public let capabilities: AnyUIFoundationCapabilities
    @ObservationIgnored public let lifetime: AnyUIPresentationLifetime
    @ObservationIgnored public let recovery: AnyNativeLibraryRecovery
    @ObservationIgnored private var repository: AnyHierarchyRepository?
    @ObservationIgnored private var store: AnyGuardedHTTPHierarchyRecordStore?
    @ObservationIgnored private var operations: AnyGuardedTorahOperationStore?
    @ObservationIgnored private var marker: AnyNativeNoteMarker?
    @ObservationIgnored private var propertyCatalogStore: AnyNativePropertyStore?
    @ObservationIgnored private var creationWorkflow: AnyNativeWorkflowBindings?
    @ObservationIgnored private var eligibleDocumentTypeIDs: Set<String> = []
    @ObservationIgnored private var knownDocumentTypeIDs: Set<String> = []
    @ObservationIgnored private var editors: [String: AnyDocumentPresentation] = [:]
    @ObservationIgnored private var streamSession: AnyStreamSession?
    @ObservationIgnored private var observation: Task<Void, Never>?
    @ObservationIgnored private var searchTask: Task<Void, Never>?
    @ObservationIgnored private var catalogRefreshTask: Task<Void, Never>?
    @ObservationIgnored private var searchEpoch: UInt64 = 0
    @ObservationIgnored private var documentsReadEpoch: UInt64 = 0
    @ObservationIgnored private var closingObservations: [Task<Void, Never>] = []
    @ObservationIgnored private var epoch = UUID()
    @ObservationIgnored private var registration: UUID?

    public init(client: AnyHTTPClient, session: AnyApplicationSession,
                objects: AnyNativeObjectCreator, blocks: AnyNativeBlockCreator,
                capabilities: AnyUIFoundationCapabilities, lifetime: AnyUIPresentationLifetime,
                recovery: AnyNativeLibraryRecovery) {
        self.client = client; self.session = session; self.objects = objects; self.blocks = blocks
        self.capabilities = capabilities; self.lifetime = lifetime; self.recovery = recovery
        self.hierarchyPresentation = .init(workspace: session.workspace)
        registration = try? lifetime.register(revoke: { [weak self] in self?.revoke() },
                                              drain: { [weak self] in await self?.drain() })
    }

    public func open() async {
        guard lifetime.isActive, !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        let expected = epoch, feed = replaceObservationFeed()
        do {
            try recovery.requireWorkspace(session.workspace)
            let client = client, session = session
            let configuration = try await session.perform { lease in
                let schema: AnyHierarchySchema
                let marker: AnyNativeNoteMarker
                do {
                    schema = try await AnyHTTPHierarchyRecordStore.readSchema(client: client, workspace: lease.workspace)
                    marker = try await AnyNoteBootstrap.read(client: client, session: session)
                } catch AnyEngineError.http(let status, _) where status == 404 {
                    throw AnyLibraryOpenError.setupMissing
                }
                let operations = try AnyGuardedTorahOperationStore(client: client, workspace: lease.workspace)
                _ = try await operations.repository.verifyCapabilities()
                // Reader opening validates native installation; it never installs.
                let member = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", lease.workspace.spaceID, "members", "me"])
                try AnyHTTPTorahTargetAccess.validateMember(member, workspace: lease.workspace, intent: .read)
                try await lease.validate()
                return (schema, marker, operations,
                        ["owner", "admin", "writer"].contains(member["permission"]?.string ?? ""))
            }
            try validate(expected)
            let store = try AnyGuardedHTTPHierarchyRecordStore(client: client, workspace: session.workspace,
                schema: configuration.0, engineStartedAt: session.engineStartedAt)
            try await store.verifyCapabilities()
            let workflow = try AnyNativeWorkflowBindings(client: client, session: session,
                objects: objects, blocks: blocks, noteMarker: configuration.1)
            let properties = try AnyNativePropertyStore(client: client, workspace: session.workspace,
                policy: AnyNativePropertyPolicies.workspace(schema: configuration.0, noteMarker: configuration.1))
            let catalog = try await session.perform { lease in try await properties.catalog(lease: lease) }
            try validate(expected)
            let eligible = Set(catalog.types.filter(\.documentEligible).map(\.id))
            guard !eligible.isEmpty else { throw AnyNativePropertyError.unavailableDocumentType }
            let repository = try AnyHierarchyRepository(workspace: session.workspace, store: store,
                creator: workflow, allowedTypeIDs: eligible)
            let snapshot = try await session.perform { lease in
                let value = try await repository.snapshot()
                try await lease.validate(); return value
            }
            try validate(expected)
            self.store = store; self.repository = repository
            self.propertyCatalogStore = properties; self.creationWorkflow = workflow
            self.eligibleDocumentTypeIDs = eligible
            self.knownDocumentTypeIDs = Set(catalog.types.map(\.id))
                .union(snapshot.nativeRows.values.compactMap { $0["any"]?["type"]?.string })
            marker = configuration.1; operations = configuration.2; canWrite = configuration.3
            guard hierarchyPresentation.isCurrent(feed) else { return }
            try acceptHierarchy(snapshot, feed: feed); requiresSetup = false
            startObservation(repository, feed: feed)
            try await refreshAllDocuments(expected: expected, feed: feed)
        } catch AnyLibraryOpenError.setupMissing {
            guard epoch == expected, lifetime.isActive else { return }
            requiresSetup = true
        } catch {
            guard epoch == expected, lifetime.isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    /// Explicit setup is a user action. A normal reader never repairs schemas.
    public func installWorkspace() async {
        guard lifetime.isActive, !isLoading else { return }
        isLoading = true
        let expected = epoch
        do {
            let client = client, session = session
            let authorize = authorization(expected)
            _ = try await session.perform { lease in
                try await AnyHTTPHierarchyRecordStore.installWiki(client: client, workspace: lease.workspace) {
                    try await lease.validate(); try await authorize()
                }
            }
            try validate(expected)
            _ = try await AnyNoteBootstrap.install(client: client, session: session)
            let operations = try AnyGuardedTorahOperationStore(client: client, workspace: session.workspace)
            try await session.perform { lease in
                try await operations.repository.install {
                    try await lease.validate(); try await authorize()
                }
            }
            try validate(expected)
            requiresSetup = false
        } catch { message = AnyUIErrorText.describe(error) }
        isLoading = false
        if !requiresSetup { await open() }
    }

    public func document(_ id: String) throws -> AnyDocumentPresentation {
        try lifetime.requireActive()
        if let existing = editors[id] { return existing }
        guard let marker, let operations else { throw AnyHostError.incompleteDocument }
        let model = try AnyDocumentPresentation(client: client, session: session,
            objects: objects, blocks: blocks, capabilities: capabilities, operations: operations,
            noteMarker: marker, objectID: id, lifetime: lifetime, recovery: recovery, hierarchySchema: hierarchy?.schema)
        model.onOpenObject = { [weak self] objectID, blockID in self?.onOpenDocument?(objectID, blockID) }
        editors[id] = model
        return model
    }

    public func create(title: String, kind: PinkhaHierarchyNodeKind, parentID: String?, isNote: Bool = false) async {
        guard canWrite, let repository else { return }
        let expected = epoch
        do {
            let plan = try await session.perform { lease in
                let value = try await repository.prepareCreation(typeID: "page", title: title,
                                                                  kind: kind, parentID: parentID)
                try await lease.validate(); return value
            }
            try validate(expected)
            pendingCreations.append(.init(plan: plan, isNote: isNote))
            await retryCreation(plan.mutationID)
        } catch { message = AnyUIErrorText.describe(error) }
    }

    public func retryCreation(_ id: String) async {
        guard canWrite, let repository,
              let pending = pendingCreations.first(where: { $0.id == id }) else { return }
        let expected = epoch, authorize = authorization(epoch)
        do {
            let result: AnyHierarchyItem
            if pending.isNote {
                guard let marker else { throw AnyHostError.incompleteDocument }
                let objects = objects, client = client
                let intent = try AnyNativeObjectCreationIntent(workspace: session.workspace,
                    mutationID: pending.plan.mutationID, typeID: pending.plan.typeID,
                    collections: pending.plan.collections + [marker.collectionID],
                    initialProperties: pending.plan.initialProperties)
                result = try await session.perform { lease in
                    _ = try await AnyNativeNoteMarker.verify(client: client, workspace: lease.workspace,
                                                              collectionID: marker.collectionID)
                    let id = try await objects.ensureObject(intent) {
                        try await lease.validate(); try await authorize()
                    }
                    let snapshot = try await repository.snapshot()
                    guard let item = snapshot.itemsByID[id], item.title == pending.plan.title,
                          item.parentID == pending.plan.parentID, item.position == pending.plan.position,
                          item.kind == pending.plan.kind else { throw AnyHostError.writeUncertain }
                    try await lease.validate(); return item
                }
            } else {
                result = try await session.perform { lease in
                    try await repository.create(pending.plan) { try await lease.validate(); try await authorize() }
                }
            }
            try validate(expected)
            if let offset = pendingCreations.firstIndex(where: { $0.id == id }) {
                pendingCreations[offset].confirmedObjectID = result.objectID
            }
            _ = try await refreshHierarchy(expected: expected)
            try validate(expected)
            if result.kind == .writingDocument { onOpenDocument?(result.objectID, nil) }
        } catch {
            guard epoch == expected, lifetime.isActive else { return }
            if let offset = pendingCreations.firstIndex(where: { $0.id == id }) {
                pendingCreations[offset].error = AnyUIErrorText.describe(error)
            }
        }
    }

    public func rename(_ item: AnyHierarchyItem, title: String) async {
        guard canWrite, let repository, !pendingMoves.contains(item.objectID),
              !hierarchyPresentation.hasPending(item.objectID) else { return }
        let expected = epoch, authorize = authorization(epoch)
        pendingMoves.insert(item.objectID)
        defer { pendingMoves.remove(item.objectID) }
        do {
            try hierarchyPresentation.rename(objectID: item.objectID, title: title)
            _ = try await session.perform { lease in
                try await repository.rename(objectID: item.objectID, expectedTitle: item.title, newTitle: title) {
                    try await lease.validate(); try await authorize()
                }
            }
            try validate(expected)
            hierarchyPresentation.settleAfterFeedReplacement(item.objectID)
            _ = try await refreshHierarchy(expected: expected)
        } catch {
            guard expected == epoch, lifetime.isActive else { return }
            hierarchyPresentation.settleAfterFeedReplacement(item.objectID)
            _ = try? await refreshHierarchy(expected: expected)
            guard expected == epoch, lifetime.isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    public func move(objectID: String, parentID: String?, beforeSiblingID: String? = nil) async {
        guard canWrite, let repository, !pendingMoves.contains(objectID),
              !hierarchyPresentation.hasPending(objectID) else { return }
        let expected = epoch, authorize = authorization(epoch)
        pendingMoves.insert(objectID)
        defer { pendingMoves.remove(objectID) }
        do {
            let plan = try await session.perform { lease in
                let value = try await repository.prepareMove(objectID: objectID, parentID: parentID,
                                                              beforeSiblingID: beforeSiblingID)
                try await lease.validate(); return value
            }
            try validate(expected)
            try hierarchyPresentation.place(plan)
            _ = try await session.perform { lease in
                try await repository.commitPlacement(plan) { try await lease.validate(); try await authorize() }
            }
            try validate(expected)
            hierarchyPresentation.settleAfterFeedReplacement(objectID)
            _ = try await refreshHierarchy(expected: expected)
        } catch {
            guard expected == epoch, lifetime.isActive else { return }
            hierarchyPresentation.settleAfterFeedReplacement(objectID)
            _ = try? await refreshHierarchy(expected: expected)
            guard expected == epoch, lifetime.isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    public func remove(_ item: AnyHierarchyItem) async {
        guard canWrite, let repository, let store else { return }
        let expected = epoch, authorize = authorization(epoch)
        do {
            if item.kind == .folder {
                let receipt = try await session.perform { lease in
                    try await repository.removeFolderSafely(objectID: item.objectID) {
                        try await lease.validate(); try await authorize()
                    }
                }
                try validate(expected)
                if !receipt.complete {
                    message = AnyUIErrorText.text(
                        "הסרת התיקייה הושלמה חלקית. התוכן שכבר הועבר נשמר. רענן לפני ניסיון נוסף.",
                        "Folder removal completed partially. Moved contents were preserved. Refresh before retrying.")
                }
            } else {
                try await session.perform { lease in
                    try await store.setArchived(objectID: item.objectID, archived: true) {
                        try await lease.validate(); try await authorize()
                    }
                }
            }
            try validate(expected); await refresh()
        } catch { message = AnyUIErrorText.describe(error) }
    }

    public func refresh() async {
        guard repository != nil else { await open(); return }
        let expected = epoch
        do { _ = try await refreshHierarchy(expected: expected) }
        catch {
            guard expected == epoch, lifetime.isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    /// A completed write is followed by a fresh native read and a new subscription.
    /// Buffered frames from the previous feed can never replace that read.
    @discardableResult
    private func refreshHierarchy(expected: UUID) async throws -> AnyHierarchySnapshot? {
        guard let properties = propertyCatalogStore, let store, let workflow = creationWorkflow else {
            throw AnyHostError.incompleteDocument
        }
        let feed = replaceObservationFeed()
        let catalog = try await session.perform { lease in try await properties.catalog(lease: lease) }
        try validate(expected)
        guard hierarchyPresentation.isCurrent(feed) else { return nil }
        let eligible = Set(catalog.types.filter(\.documentEligible).map(\.id))
        guard !eligible.isEmpty else { throw AnyNativePropertyError.unavailableDocumentType }
        let repository = try AnyHierarchyRepository(workspace: session.workspace, store: store,
                                                    creator: workflow, allowedTypeIDs: eligible)
        let snapshot = try await session.perform { lease in
            let value = try await repository.snapshot()
            try await lease.validate(); return value
        }
        try validate(expected)
        guard hierarchyPresentation.isCurrent(feed) else { return nil }
        self.repository = repository
        eligibleDocumentTypeIDs = eligible
        knownDocumentTypeIDs = Set(catalog.types.map(\.id))
            .union(snapshot.nativeRows.values.compactMap { $0["any"]?["type"]?.string })
        try acceptHierarchy(snapshot, feed: feed)
        startObservation(repository, feed: feed)
        try await refreshAllDocuments(expected: expected, feed: feed)
        return snapshot
    }

    private func acceptHierarchy(_ snapshot: AnyHierarchySnapshot, feed: UUID) throws {
        guard try hierarchyPresentation.receive(snapshot, feed: feed) else { return }
        pendingCreations.removeAll {
            $0.confirmedObjectID.map { snapshot.itemsByID[$0] != nil } ?? false
        }
    }

    private func refreshAllDocuments(expected: UUID, feed: UUID) async throws {
        documentsReadEpoch &+= 1
        let request = documentsReadEpoch
        guard let marker else { return }
        let client = client, allowed = eligibleDocumentTypeIDs
        let documents = try await session.perform { lease in
            let response = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", lease.workspace.spaceID, "objects", "query"],
                body: .object(["filter": .object(["$and": .array([
                    .object(["any.type": .object(["$in": .array(allowed.sorted().map(AnyJSON.string))])]),
                    .object(["any.collections": .object(["$nin": .array([.string("bin"), .string("template")])])])
                ])]), "limit": .integer(10_001), "includeTotal": .bool(true)]))
            guard let rows = response["records"]?.array, response["total"]?.integer == rows.count,
                  rows.count <= 10_000, response["hasNext"]?.bool == false else { throw AnyEngineError.readLimit }
            var seen = Set<String>()
            let result = try rows.map { row -> AnyLibraryDocument in
                guard let id = row["id"]?.string, !id.isEmpty, seen.insert(id).inserted,
                      row["spaceId"]?.string == lease.workspace.spaceID,
                      let type = row["any"]?["type"]?.string, allowed.contains(type),
                      row["any"]?["name"] == nil || row["any"]?["name"]?.string != nil else {
                    throw AnyHostError.invalidDocument("native library record")
                }
                let collections = row["any"]?["collections"]?.array ?? []
                return .init(id: id, title: row["any"]?["name"]?.string ?? "", isNote: collections.contains(.string(marker.collectionID)), snippet: nil)
            }
            try await lease.validate(); return result
        }
        try validate(expected)
        guard hierarchyPresentation.isCurrent(feed), request == documentsReadEpoch else { return }
        let folders = Set(hierarchy?.items.filter { $0.kind == .folder }.map(\.objectID) ?? [])
        allDocuments = documents.filter { !folders.contains($0.id) }.sorted {
            $0.title.localizedStandardCompare($1.title) == .orderedAscending
        }
    }

    public func searchChanged() {
        searchTask?.cancel(); searchEpoch &+= 1
        let request = searchEpoch, expected = epoch
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { searchResults = []; isSearching = false; return }
        isSearching = true
        searchTask = Task { [weak self] in
            do { try await Task.sleep(for: .milliseconds(300)) } catch { return }
            guard let self else { return }
            defer { if request == searchEpoch { isSearching = false } }
            do {
                let client = client, marker = marker, allowed = eligibleDocumentTypeIDs
                let rows = try await session.perform { lease in
                    let output = try await client.requestJSON(method: "POST",
                        path: ["v1", "spaces", lease.workspace.spaceID, "search"],
                        body: .object(["query": .string(query), "mode": .string("fts"),
                                       "limit": .integer(100), "maxData": .integer(512),
                                       "filter": .object(["any.collections":
                                            .object(["$nin": .array([.string("bin"), .string("template")])])])]))
                    guard let hits = output["hits"]?.array, hits.count <= 100 else { throw AnyEngineError.readLimit }
                    let reader = try AnyHTTPTorahRelatedDocumentReader(client: client, workspace: lease.workspace,
                        allowedTypeIDs: allowed, noteCollectionIDs: marker.map { [$0.collectionID] } ?? [],
                        documentTypePolicy: .nativeCanonicalEditorV1)
                    var seen = Set<String>(), result: [AnyLibraryDocument] = []
                    for hit in hits {
                        guard let id = hit["objectId"]?.string, !id.isEmpty else { throw AnyHostError.incompleteDocument }
                        guard seen.insert(id).inserted else { continue }
                        do {
                            let metadata = try await reader.metadata(objectID: id)
                            result.append(.init(id: id, title: metadata.title, isNote: metadata.isNote,
                                                snippet: hit["data"]?.string))
                        } catch TorahAssociationRepositoryError.targetNotFound { continue }
                    }
                    try await lease.validate(); return result
                }
                try validate(expected)
                guard request == searchEpoch else { return }
                searchResults = rows
            } catch {
                guard request == searchEpoch, expected == epoch, lifetime.isActive, !Task.isCancelled else { return }
                message = AnyUIErrorText.describe(error)
            }
        }
    }

    private func replaceObservationFeed() -> UUID {
        let feed = hierarchyPresentation.beginFeed()
        let previousStream = streamSession; streamSession = nil
        let previous = observation; observation = nil
        previous?.cancel()
        if previous != nil || previousStream != nil {
            closingObservations.append(Task {
                await previousStream?.invalidate()
                await previous?.value
            })
        }
        return feed
    }

    private func startObservation(_ repository: AnyHierarchyRepository, feed: UUID) {
        guard hierarchyPresentation.isCurrent(feed), observation == nil else { return }
        let stream = AnyStreamSession(generation: feed)
        streamSession = stream
        let expected = epoch
        observation = Task { [weak self] in
            guard let self else { return }
            do {
                let updates = try await repository.watch(session: stream)
                for try await update in updates {
                    try await stream.requireActive(generation: update.generation)
                    try validate(expected)
                    guard hierarchyPresentation.isCurrent(feed) else { return }
                    let observedTypes = Set(update.snapshot.nativeRows.values.compactMap { $0["any"]?["type"]?.string })
                    if !observedTypes.isSubset(of: knownDocumentTypeIDs) {
                        // A newly synced Type is discovered by its native proof
                        // before the library admits its document rows.
                        catalogRefreshTask?.cancel()
                        catalogRefreshTask = Task { [weak self] in
                            guard let self, epoch == expected, lifetime.isActive else { return }
                            await refresh()
                        }
                        return
                    }
                    try acceptHierarchy(update.snapshot, feed: feed)
                    try await refreshAllDocuments(expected: expected, feed: feed)
                }
            } catch {
                guard expected == epoch, hierarchyPresentation.isCurrent(feed),
                      lifetime.isActive, !Task.isCancelled else { return }
                message = AnyUIErrorText.describe(error)
            }
        }
    }

    private func authorization(_ expected: UUID) -> @Sendable () async throws -> Void {
        { [weak self] in
            guard let self else { throw AnyHostError.sessionClosed }
            try await self.validate(expected)
        }
    }

    private func validate(_ expected: UUID) throws {
        try lifetime.requireActive()
        guard expected == epoch else { throw AnyHostError.sessionClosed }
    }

    public func revoke() {
        epoch = UUID(); canWrite = false
        _ = replaceObservationFeed(); searchTask?.cancel(); catalogRefreshTask?.cancel()
        for editor in editors.values { editor.revoke() }
    }

    public func drain() async {
        revoke()
        let stream = streamSession; streamSession = nil
        await stream?.invalidate()
        await observation?.value; observation = nil
        let closing = closingObservations; closingObservations = []
        for task in closing { await task.value }
        await searchTask?.value; searchTask = nil
        await catalogRefreshTask?.value; catalogRefreshTask = nil
        for editor in editors.values { await editor.drain() }
    }
}
#endif
