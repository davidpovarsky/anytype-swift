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
            target: .object("picker-object"), onRelationSelect: { _, _ in }
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
