import Foundation
import Combine
import Services
import PinkhaKit
import Testing
@testable import Anytype

@MainActor
@Suite("Property picker request ownership")
struct PropertyCreationSearchTests {
    @Test("An older query cannot replace newer rows or publish its catalog error")
    func latestQueryOwnsRowsAndErrors() async {
        let loader = SuspendedPropertyPickerLoader()
        let model = makeModel(loader)
        let first = Task { await model.search(text: "first") }
        await loader.waitForRequest("first")
        let latest = Task { await model.search(text: "latest") }
        await loader.waitForRequest("latest")

        loader.finish("latest", properties: [property("latest")])
        await latest.value
        loader.finish("first", properties: [property("first")], nativeFailed: true)
        await first.value

        #expect(existingIDs(model) == ["latest"])
        #expect(!model.hasLookupFailure)
        #expect(!model.isSearching)
    }

    @Test("Cancellation is not a failed lookup, even if the provider returns late")
    func cancelledRequestDoesNotPublish() async {
        let loader = SuspendedPropertyPickerLoader()
        let model = makeModel(loader)
        let task = Task { await model.search(text: "cancelled") }
        await loader.waitForRequest("cancelled")
        task.cancel()
        loader.finish("cancelled", properties: [property("forbidden")], nativeFailed: true)
        await task.value

        #expect(existingIDs(model).isEmpty)
        #expect(!model.hasLookupFailure)
        #expect(model.isSearching) // No completed empty result.
    }

    @Test("A pre-cancelled request does not start catalog work")
    func preCancelledRequestDoesNotLoad() async {
        let loader = SuspendedPropertyPickerLoader()
        let model = makeModel(loader)
        let task = Task { await model.search(text: "cancelled") }
        task.cancel()
        await task.value
        #expect(loader.calls.isEmpty)
    }

    @Test("A Torah catalog failure preserves ordinary properties and native formats")
    func nativeFailurePreservesOrdinaryChoices() async {
        let loader = SuspendedPropertyPickerLoader()
        let model = makeModel(loader)
        let task = Task { await model.search(text: "") }
        await loader.waitForRequest("")
        loader.finish("", properties: [property("ordinary-tag")], nativeFailed: true)
        await task.value

        #expect(model.nativeLookupFailed)
        #expect(!model.existingLookupFailed)
        #expect(existingIDs(model) == ["ordinary-tag"])
        #expect(model.rows.flatMap(\.searchData).contains {
            if case .new = $0 { return true }
            return false
        })
    }

    @Test("An existing-property search failure is explicit rather than an empty result")
    func existingSearchFailureIsVisible() async {
        let loader = SuspendedPropertyPickerLoader()
        let model = makeModel(loader)
        let task = Task { await model.search(text: "missing") }
        await loader.waitForRequest("missing")
        loader.fail("missing")
        await task.value

        #expect(model.existingLookupFailed)
        #expect(model.hasLookupFailure)
        #expect(!model.nativeLookupFailed)
        #expect(!model.isSearching)
    }

    @Test("Retry invalidates only the current Space and keeps the current query")
    func retryKeepsQueryAndSpace() async {
        let loader = SuspendedPropertyPickerLoader()
        let model = makeModel(loader)
        let first = Task { await model.search(text: "source") }
        await loader.waitForRequest("source")
        loader.finish("source", nativeFailed: true)
        await first.value

        let retry = Task { await model.retryNativeLookup() }
        await loader.waitForRequest("source")
        loader.finish("source", properties: [property("source")])
        await retry.value

        #expect(loader.calls == ["source", "source"])
        #expect(loader.invalidatedSpaces == ["picker-space"])
        #expect(existingIDs(model) == ["source"])
        #expect(!model.hasLookupFailure)
    }

    @Test("Cancelled native catalog requests do not publish errors or retry provisioning")
    func catalogCancellationStopsAtTheSearchBoundary() async {
        let search = CancelledCatalogSearch()
        let catalog = PinkhaTorahNativePropertyCatalog(
            searchService: search, propertyDetailsStorage: EmptyPickerPropertyStorage()
        )
        let properties = await catalog.nativeProperties(spaceId: "cancelled-catalog-space")
        let calls = await search.calls
        #expect(properties.isEmpty)
        #expect(calls == 1)
        #expect(catalog.lastLookupDiagnostics(spaceId: "cancelled-catalog-space").isEmpty)
    }

    @Test("Pre-cancelled native catalog requests issue no search")
    func preCancelledCatalogDoesNotSearch() async {
        let search = CancelledCatalogSearch()
        let catalog = PinkhaTorahNativePropertyCatalog(
            searchService: search, propertyDetailsStorage: EmptyPickerPropertyStorage()
        )
        let task = Task { await catalog.nativeProperties(spaceId: "pre-cancelled-catalog-space") }
        task.cancel()
        let properties = await task.value
        let calls = await search.calls
        #expect(properties.isEmpty)
        #expect(calls == 0)
        #expect(catalog.lastLookupDiagnostics(spaceId: "pre-cancelled-catalog-space").isEmpty)
    }

    @Test("Provider cancellation cannot complete the real loader and picker with empty results")
    func providerCancellationPropagatesThroughLoaderAndPicker() async {
        let manifest = PinkhaSpaceManifest(
            spaceId: "picker-space", orderPropertyId: "order-id", orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "canonical-id", documentAssociationsPropertyKey: "canonical-key"
        )
        let policy = PinkhaTorahPropertyPolicy(bootstrapService: PickerBootstrapProbe(manifest: manifest))
        let search = CancelledCatalogSearch()
        let catalog = PinkhaTorahNativePropertyCatalog(
            policy: policy, searchService: search, propertyDetailsStorage: EmptyPickerPropertyStorage()
        )
        let loader = PinkhaPropertyPickerSearchLoader(policy: policy, catalog: catalog,
                                                      existingSearch: { _, _, _ in [] })
        let model = PropertyCreationViewModel(data: .init(
            objectId: "picker-object", spaceId: "picker-space", excludedRelationsIds: [],
            target: .library, onRelationSelect: { _, _ in }
        ), searchLoader: loader)

        #expect(!Task.isCancelled)
        await model.search(text: "source")
        #expect(!Task.isCancelled)
        #expect(await search.calls == 1)
        #expect(existingIDs(model).isEmpty)
        #expect(!model.hasLookupFailure)
        #expect(model.isSearching) // Cancellation cannot authorize an empty-state completion.
        #expect(catalog.lastLookupDiagnostics(spaceId: "picker-space").isEmpty)
    }

    private func makeModel(_ loader: SuspendedPropertyPickerLoader) -> PropertyCreationViewModel {
        PropertyCreationViewModel(data: .init(
            objectId: "picker-object", spaceId: "picker-space", excludedRelationsIds: [],
            target: .object(objectId: "picker-object"), onRelationSelect: { _, _ in }
        ), searchLoader: loader)
    }

    private func existingIDs(_ model: PropertyCreationViewModel) -> [String] {
        model.rows.flatMap(\.searchData).compactMap {
            if case .existing(let property) = $0 { return property.id }
            return nil
        }
    }

    private func property(_ id: String) -> PropertyDetails {
        .init(id: id, key: id, name: id, format: .tag, isHidden: false,
              isReadOnly: false, isReadOnlyValue: false, objectTypes: [],
              maxCount: 0, sourceObject: "", isDeleted: false, spaceId: "picker-space")
    }
}

@MainActor
private final class SuspendedPropertyPickerLoader: PinkhaPropertyPickerSearchLoading {
    private(set) var calls: [String] = []
    private(set) var invalidatedSpaces: [String] = []
    private var pending: [String: CheckedContinuation<PinkhaPropertyPickerSearchResult, any Error>] = [:]
    private var observers: [String: CheckedContinuation<Void, Never>] = [:]

    func invalidate(spaceId: String) { invalidatedSpaces.append(spaceId) }

    func load(text: String, data: PropertiesSearchData) async throws -> PinkhaPropertyPickerSearchResult {
        calls.append(text)
        return try await withCheckedThrowingContinuation { continuation in
            pending[text] = continuation
            observers.removeValue(forKey: text)?.resume()
        }
    }

    func waitForRequest(_ text: String) async {
        guard pending[text] == nil else { return }
        await withCheckedContinuation { observers[text] = $0 }
    }

    func finish(_ text: String, properties: [PropertyDetails] = [], nativeFailed: Bool = false) {
        pending.removeValue(forKey: text)?.resume(returning: .init(
            properties: properties, nativeLookupFailed: nativeFailed, existingLookupFailed: false
        ))
    }

    func fail(_ text: String) {
        pending.removeValue(forKey: text)?.resume(throwing: PickerProbeFailure.lookup)
    }
}

private enum PickerProbeFailure: Error { case lookup }

private actor CancelledCatalogSearch: SearchMiddleServiceProtocol {
    private(set) var calls = 0
    func search(data: SearchRequest) async throws -> [ObjectDetails] {
        calls += 1
        throw CancellationError()
    }
}

private final class EmptyPickerPropertyStorage: PropertyDetailsStorageProtocol, @unchecked Sendable {
    var syncPublisher: AnyPublisher<Void, Never> { Empty().eraseToAnyPublisher() }
    func relationsDetails(keys: [String], spaceId: String) -> [PropertyDetails] { [] }
    func relationsDetails(key: String, spaceId: String) throws -> PropertyDetails { throw PickerProbeFailure.lookup }
    func relationsDetails(bundledKey: BundledPropertyKey, spaceId: String) throws -> PropertyDetails { throw PickerProbeFailure.lookup }
    func relationsDetails(ids: [String], spaceId: String) -> [PropertyDetails] { [] }
    func relationsDetails(spaceId: String) -> [PropertyDetails] { [] }
    func startSubscription(spaceId: String) async {}
    func stopSubscription() async {}
    func prepareData(spaceId: String) async {}
}

private struct PickerBootstrapProbe: PinkhaSpaceBootstrapServiceProtocol {
    let manifest: PinkhaSpaceManifest
    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest { manifest }
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? {
        manifest.spaceId == spaceId ? manifest : nil
    }
    func isBootstrapped(spaceId: String) -> Bool { manifest.spaceId == spaceId }
}

@MainActor
@Suite("Property picker read-only production lookup")
struct PropertyPickerReadOnlyLookupTests {
    @Test("Native-only failure keeps verified ordinary choices during typing and Retry without bootstrap", arguments: [false, true])
    func ordinaryChoicesSurviveNativeFailureWithoutProvisioning(nativeSearchFails: Bool) async throws {
        let probe = ReadOnlyPickerProbe()
        let manifest = makeManifest()
        let policy = PinkhaTorahPropertyPolicy(
            bootstrapService: PickerBootstrapMustStayIdle(probe: probe),
            pickerManifestLoader: { _ in await probe.didReadManifest(); return manifest }
        )
        let nativeSearch = ReadOnlyPickerNativeSearch(fails: nativeSearchFails)
        let catalog = PinkhaTorahNativePropertyCatalog(policy: policy,
            searchService: nativeSearch, propertyDetailsStorage: EmptyPickerPropertyStorage(),
            bootstrapSpace: { _ in await probe.didBootstrap(); throw PickerProbeFailure.lookup })
        let ordinary = property("ordinary", key: "ordinary-key", name: "הקשר תורני")
        let candidates = [ordinary,
            property("canonical-id", key: "canonical-key"),
            property("order-id", key: "order-key"),
            property("foreign", key: "foreign-key", space: "other-space")]
        var queries: [String] = []
        let loader = PinkhaPropertyPickerSearchLoader(policy: policy, catalog: catalog,
            existingSearch: { text, _, space in
                #expect(space == "picker-space")
                queries.append(text)
                return candidates
            })
        let data = makeData()
        for query in ["", "מקור", "source"] {
            let result = try await loader.load(text: query, data: data)
            #expect(result.properties.map(\.id) == [ordinary.id])
            #expect(result.nativeLookupFailed)
            #expect(!result.existingLookupFailed)
        }
        loader.invalidate(spaceId: data.spaceId)
        let retried = try await loader.load(text: "source", data: data)
        #expect(retried.properties.map(\.id) == [ordinary.id])
        #expect(retried.nativeLookupFailed)
        #expect(!retried.existingLookupFailed)

        let ordinaryAllowed = try await policy.canAddPropertyFromPicker(
            propertyId: ordinary.id, key: ordinary.key, target: data.target, spaceId: data.spaceId)
        let canonicalAllowed = try await policy.canAddPropertyFromPicker(
            propertyId: "canonical-id", key: "canonical-key", target: data.target, spaceId: data.spaceId)
        let orderAllowed = try await policy.canAddPropertyFromPicker(
            propertyId: "order-id", key: "order-key", target: data.target, spaceId: data.spaceId)
        #expect(ordinaryAllowed)
        #expect(!canonicalAllowed && !orderAllowed)
        #expect(queries == ["", "מקור", "source", "source"])
        #expect(await probe.manifestReads == 7)
        #expect(await probe.bootstrapCalls == 0)
        #expect(await nativeSearch.calls == 12)
    }

    @Test("Unresolved or foreign internal identity stays explicit and never guesses ordinary safety", arguments: ["unavailable", "wrong-space", "missing-canonical", "missing-order"])
    func unresolvedIdentityKeepsInternalFieldsClosed(mode: String) async throws {
        let probe = ReadOnlyPickerProbe()
        var prepared = makeManifest()
        if mode == "wrong-space" { prepared.spaceId = "other-space" }
        if mode == "missing-canonical" { prepared.documentAssociationsPropertyKey = "" }
        if mode == "missing-order" { prepared.orderPropertyId = "" }
        let captured = prepared
        let policy = PinkhaTorahPropertyPolicy(
            bootstrapService: PickerBootstrapMustStayIdle(probe: probe),
            pickerManifestLoader: { _ in
                await probe.didReadManifest()
                if mode == "unavailable" { throw PickerProbeFailure.lookup }
                return captured
            }
        )
        let nativeSearch = ReadOnlyPickerNativeSearch(fails: false)
        let catalog = PinkhaTorahNativePropertyCatalog(policy: policy,
            searchService: nativeSearch, propertyDetailsStorage: EmptyPickerPropertyStorage(),
            bootstrapSpace: { _ in await probe.didBootstrap(); throw PickerProbeFailure.lookup })
        let ordinary = property("ordinary", key: "ordinary-key")
        let loader = PinkhaPropertyPickerSearchLoader(policy: policy, catalog: catalog,
            existingSearch: { _, _, _ in [ordinary] })
        let data = makeData()
        let result = try await loader.load(text: "", data: data)
        #expect(result.properties.isEmpty)
        #expect(result.nativeLookupFailed)
        #expect(!result.existingLookupFailed)
        do {
            let allowed = try await policy.canAddPropertyFromPicker(
                propertyId: ordinary.id, key: ordinary.key, target: data.target, spaceId: data.spaceId)
            #expect(!allowed)
        } catch PickerProbeFailure.lookup {
            #expect(mode == "unavailable")
        } catch {
            Issue.record("Unexpected manifest selection error")
        }
        #expect(await probe.manifestReads == 2)
        #expect(await probe.bootstrapCalls == 0)
        #expect(await nativeSearch.calls == 0)
    }

    @Test("Cancellation from the read-only manifest is not an empty or failed completed lookup")
    func readOnlyManifestCancellationPropagates() async {
        let probe = ReadOnlyPickerProbe()
        let policy = PinkhaTorahPropertyPolicy(
            bootstrapService: PickerBootstrapMustStayIdle(probe: probe),
            pickerManifestLoader: { _ in await probe.didReadManifest(); throw CancellationError() }
        )
        let nativeSearch = ReadOnlyPickerNativeSearch(fails: false)
        let catalog = PinkhaTorahNativePropertyCatalog(policy: policy,
            searchService: nativeSearch, propertyDetailsStorage: EmptyPickerPropertyStorage(),
            bootstrapSpace: { _ in await probe.didBootstrap(); throw PickerProbeFailure.lookup })
        var existingInvoked = false
        let loader = PinkhaPropertyPickerSearchLoader(policy: policy, catalog: catalog,
            existingSearch: { _, _, _ in existingInvoked = true; return [] })
        do {
            _ = try await loader.load(text: "source", data: makeData())
            Issue.record("Provider cancellation must propagate from the actual loader")
        } catch is CancellationError {
            // Expected: the unchanged VM keeps this distinct from completed empty results.
        } catch {
            Issue.record("Unexpected non-cancellation error")
        }
        #expect(!existingInvoked)
        #expect(await probe.manifestReads == 1)
        #expect(await probe.bootstrapCalls == 0)
        #expect(await nativeSearch.calls == 0)
    }

    private func makeManifest() -> PinkhaSpaceManifest {
        .init(spaceId: "picker-space", orderPropertyId: "order-id", orderPropertyKey: "order-key",
              documentAssociationsPropertyId: "canonical-id", documentAssociationsPropertyKey: "canonical-key")
    }

    private func makeData() -> PropertiesSearchData {
        .init(objectId: "picker-object", spaceId: "picker-space", excludedRelationsIds: [],
              target: .library, onRelationSelect: { _, _ in })
    }

    private func property(_ id: String, key: String, name: String = "Property", space: String = "picker-space") -> PropertyDetails {
        .init(id: id, key: key, name: name, format: .tag, isHidden: false,
              isReadOnly: false, isReadOnlyValue: false, objectTypes: [],
              maxCount: 0, sourceObject: "", isDeleted: false, spaceId: space)
    }
}

private actor ReadOnlyPickerProbe {
    private(set) var manifestReads = 0
    private(set) var bootstrapCalls = 0
    func didReadManifest() { manifestReads += 1 }
    func didBootstrap() { bootstrapCalls += 1 }
}

private struct PickerBootstrapMustStayIdle: PinkhaSpaceBootstrapServiceProtocol {
    let probe: ReadOnlyPickerProbe
    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        await probe.didBootstrap()
        throw PickerProbeFailure.lookup
    }
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? { nil }
    func isBootstrapped(spaceId: String) -> Bool { false }
}

private actor ReadOnlyPickerNativeSearch: SearchMiddleServiceProtocol {
    let fails: Bool
    private(set) var calls = 0
    init(fails: Bool) { self.fails = fails }
    func search(data: SearchRequest) async throws -> [ObjectDetails] {
        calls += 1
        if fails { throw PickerProbeFailure.lookup }
        return []
    }
}

import SwiftProtobuf

@MainActor
@Suite("Property picker native lookup invalidation", .timeLimit(.minutes(1)))
struct PropertyPickerNativeLookupRevisionTests {
    @Test("A late native read cannot replace a retry's descriptors or diagnostics", arguments: [
        "space-success", "space-failure", "all-success", "all-failure"
    ])
    func invalidatedNativeReadCannotCompleteTheProductionLoader(mode: String) async throws {
        let search = ControlledPickerNativeSearch(olderFails: mode.hasSuffix("failure"))
        let bootstrap = ReadOnlyPickerProbe()
        let policy = PinkhaTorahPropertyPolicy(bootstrapService: PickerBootstrapProbe(manifest: manifest()))
        let catalog = makeCatalog(policy: policy, search: search, bootstrap: bootstrap)
        let loader = PinkhaPropertyPickerSearchLoader(policy: policy, catalog: catalog,
                                                      existingSearch: { _, _, _ in [] })
        let data = PropertiesSearchData(objectId: "picker-object", spaceId: "picker-space",
            excludedRelationsIds: [], target: .library, onRelationSelect: { _, _ in })
        let older = Task { try await loader.load(text: "", data: data) }
        defer { older.cancel(); search.cancelOutstanding() }
        try await search.waitUntilOlderStarted()

        if mode.hasPrefix("all") { catalog.invalidate() }
        else { loader.invalidate(spaceId: data.spaceId) }
        let current = try await loader.load(text: "", data: data)
        #expect(current.properties.map(\.id) == freshIDs)
        #expect(!current.nativeLookupFailed && !current.existingLookupFailed)
        let accepted = try await catalog.nativePropertyLookupForReadOnlyPicker(spaceId: data.spaceId)
        #expect(accepted.properties.map(\.id) == freshIDs)
        #expect(accepted.failures.isEmpty)

        // The old provider is deliberately not cancelled. Its completed values
        // must be rejected by the catalog revision, not by the VM's query guard.
        #expect(!older.isCancelled)
        try search.completeOlder()
        do {
            _ = try await older.value
            Issue.record("An invalidated native read completed the actual picker loader")
        } catch is CancellationError {
            #expect(!older.isCancelled)
        } catch {
            Issue.record("Unexpected error from the invalidated picker lookup")
        }
        #expect(catalog.cachedNativeProperties(spaceId: data.spaceId).map(\.id) == freshIDs)
        #expect(catalog.lastLookupDiagnostics(spaceId: data.spaceId).isEmpty)
        #expect(accepted.properties.map(\.id) == freshIDs && accepted.failures.isEmpty)
        #expect(search.calls == 6)
        #expect(await bootstrap.bootstrapCalls == 0)
    }

    @Test("A bootstrap refresh already in flight cannot repopulate an invalidated native cache")
    func invalidatedBootstrapRefreshCannotReplaceTheRetry() async throws {
        let search = ControlledPickerNativeSearch(olderFails: false)
        let bootstrap = ReadOnlyPickerProbe()
        let policy = PinkhaTorahPropertyPolicy(bootstrapService: PickerBootstrapProbe(manifest: manifest()))
        let catalog = makeCatalog(policy: policy, search: search, bootstrap: bootstrap)
        let prepared = manifest()
        let older = Task { await catalog.refreshAfterBootstrap(manifest: prepared) }
        defer { older.cancel(); search.cancelOutstanding() }
        try await search.waitUntilOlderStarted()
        catalog.invalidate(spaceId: prepared.spaceId)
        let current = try await catalog.nativePropertyLookupForReadOnlyPicker(spaceId: prepared.spaceId)
        #expect(current.properties.map(\.id) == freshIDs && current.failures.isEmpty)

        try search.completeOlder()
        await older.value
        #expect(catalog.cachedNativeProperties(spaceId: prepared.spaceId).map(\.id) == freshIDs)
        #expect(catalog.lastLookupDiagnostics(spaceId: prepared.spaceId).isEmpty)
        #expect(search.calls == 6)
        #expect(await bootstrap.bootstrapCalls == 0)
    }

    @Test("Storage fallback cannot cache rows captured before a reentrant Space invalidation")
    func invalidatedSynchronousStorageReadCannotRepopulateCache() {
        let old = descriptors(prefix: "stale")
        let current = descriptors(prefix: "fresh")
        let storage = InvalidatingPickerPropertyStorage(older: old, current: current)
        let catalog = PinkhaTorahNativePropertyCatalog(propertyDetailsStorage: storage)
        storage.onFirstRead { catalog.invalidate(spaceId: "picker-space") }

        #expect(catalog.cachedNativeProperties(spaceId: "picker-space").isEmpty)
        #expect(catalog.cachedNativeProperties(spaceId: "picker-space") == current)
        #expect(catalog.cachedNativeProperties(spaceId: "picker-space") == current)
        #expect(storage.reads == 2)
        #expect(catalog.lastLookupDiagnostics(spaceId: "picker-space").isEmpty)
    }

    private var freshIDs: [String] { TorahNativePropertyDefinition.all.map { "fresh-" + $0.key } }

    private func manifest() -> PinkhaSpaceManifest {
        .init(spaceId: "picker-space", orderPropertyId: "order-id", orderPropertyKey: "order-key",
              documentAssociationsPropertyId: "canonical-id", documentAssociationsPropertyKey: "canonical-key")
    }

    private func makeCatalog(policy: PinkhaTorahPropertyPolicy, search: ControlledPickerNativeSearch,
                             bootstrap: ReadOnlyPickerProbe) -> PinkhaTorahNativePropertyCatalog {
        .init(policy: policy, searchService: search, propertyDetailsStorage: EmptyPickerPropertyStorage(),
              objectDetails: { _, _ in Issue.record("Descriptor reads must not fetch writing Types"); return nil },
              bootstrapSpace: { _ in await bootstrap.didBootstrap(); throw PickerProbeFailure.lookup })
    }

    private func descriptors(prefix: String) -> [PropertyDetails] {
        TorahNativePropertyDefinition.all.map {
            .init(id: prefix + "-" + $0.key, key: $0.key, name: $0.name, format: .tag,
                  isHidden: false, isReadOnly: false, isReadOnlyValue: true, objectTypes: [],
                  maxCount: 0, sourceObject: "_br" + $0.key, isDeleted: false, spaceId: "picker-space")
        }
    }
}

private struct PickerNativeReadDeadline: Error {}

/// Only the actual SearchMiddleService read is held. The production catalog
/// still decodes and validates real ObjectDetails for each native definition.
@MainActor
private final class ControlledPickerNativeSearch: SearchMiddleServiceProtocol {
    private let olderFails: Bool
    private(set) var calls = 0
    private var olderReleased = false
    private var olderDefinition: TorahNativePropertyDefinition?
    private var pending: CheckedContinuation<[ObjectDetails], any Error>?
    private var started: CheckedContinuation<Void, any Error>?

    init(olderFails: Bool) { self.olderFails = olderFails }

    func search(data: SearchRequest) async throws -> [ObjectDetails] {
        #expect(data.spaceId == "picker-space")
        let filter = try #require(data.filters.first { $0.relationKey == "relationKey" })
        let definition = try #require(TorahNativePropertyDefinition.definition(for: filter.value.stringValue))
        calls += 1
        if calls == 1 {
            olderDefinition = definition
            return try await withCheckedThrowingContinuation { continuation in
                pending = continuation
                let waiter = started
                started = nil
                waiter?.resume(returning: ())
            }
        }
        if olderReleased && olderFails { throw PickerProbeFailure.lookup }
        return [record(definition, prefix: olderReleased ? "stale" : "fresh")]
    }

    func waitUntilOlderStarted() async throws {
        if pending != nil { return }
        // A failure deadline only; the test advances at the actual provider read.
        let deadline = Task { @MainActor [weak self] in
            do { try await Task.sleep(for: .seconds(10)) } catch { return }
            guard let self else { return }
            let waiter = self.started
            self.started = nil
            waiter?.resume(throwing: PickerNativeReadDeadline())
        }
        defer { deadline.cancel() }
        try await withCheckedThrowingContinuation { started = $0 }
    }

    func completeOlder() throws {
        let continuation = try #require(pending)
        let definition = try #require(olderDefinition)
        pending = nil
        olderReleased = true
        if olderFails { continuation.resume(throwing: PickerProbeFailure.lookup) }
        else { continuation.resume(returning: [record(definition, prefix: "stale")]) }
    }

    func cancelOutstanding() {
        let call = pending, waiter = started
        pending = nil
        started = nil
        call?.resume(throwing: CancellationError())
        waiter?.resume(throwing: CancellationError())
    }

    private func record(_ definition: TorahNativePropertyDefinition, prefix: String) -> ObjectDetails {
        .init(id: prefix + "-" + definition.key, values: [
            "spaceId": .with { $0.stringValue = "picker-space" },
            "relationKey": .with { $0.stringValue = definition.key },
            "name": .with { $0.stringValue = definition.name },
            "relationFormat": .with { $0.numberValue = Double(TorahNativePropertyDefinition.wireFormat) },
            "relationReadonlyValue": .with { $0.boolValue = true },
            "sourceObject": .with { $0.stringValue = "_br" + definition.key }
        ])
    }
}

private final class InvalidatingPickerPropertyStorage: PropertyDetailsStorageProtocol, @unchecked Sendable {
    private let lock = NSLock()
    private let older: [PropertyDetails]
    private let current: [PropertyDetails]
    private var firstRead: (@Sendable () -> Void)?
    private var readCount = 0

    init(older: [PropertyDetails], current: [PropertyDetails]) { self.older = older; self.current = current }
    var reads: Int { lock.lock(); defer { lock.unlock() }; return readCount }
    func onFirstRead(_ action: @escaping @Sendable () -> Void) {
        lock.lock(); defer { lock.unlock() }; firstRead = action
    }
    func relationsDetails(spaceId: String) -> [PropertyDetails] {
        lock.lock()
        readCount += 1
        let action = firstRead
        firstRead = nil
        let rows = action == nil ? current : older
        lock.unlock()
        action?()
        return rows
    }
    var syncPublisher: AnyPublisher<Void, Never> { Empty().eraseToAnyPublisher() }
    func relationsDetails(keys: [String], spaceId: String) -> [PropertyDetails] { [] }
    func relationsDetails(key: String, spaceId: String) throws -> PropertyDetails { throw PickerProbeFailure.lookup }
    func relationsDetails(bundledKey: BundledPropertyKey, spaceId: String) throws -> PropertyDetails { throw PickerProbeFailure.lookup }
    func relationsDetails(ids: [String], spaceId: String) -> [PropertyDetails] { [] }
    func startSubscription(spaceId: String) async {}
    func stopSubscription() async {}
    func prepareData(spaceId: String) async {}
}
