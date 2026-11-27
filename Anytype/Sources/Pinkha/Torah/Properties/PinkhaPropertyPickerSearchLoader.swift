import Foundation
import Services
import Factory
import PinkhaKit

struct PinkhaPropertyPickerSearchResult {
    let properties: [PropertyDetails]
    let nativeLookupFailed: Bool
    let existingLookupFailed: Bool
}

/// Keeps downstream catalog work out of the native picker and lets cancellation
/// terminate a lookup without publishing a failure for a later query.
@MainActor
protocol PinkhaPropertyPickerSearchLoading {
    func load(text: String, data: PropertiesSearchData) async throws -> PinkhaPropertyPickerSearchResult
    func invalidate(spaceId: String)
}

@MainActor
final class PinkhaPropertyPickerSearchLoader: PinkhaPropertyPickerSearchLoading {
    typealias ExistingSearch = @MainActor (String, [String], String) async throws -> [PropertyDetails]

    @Injected(\.searchService)
    private var searchService: any SearchServiceProtocol

    private let policy: PinkhaTorahPropertyPolicy
    private let catalog: PinkhaTorahNativePropertyCatalog
    private let existingSearch: ExistingSearch?

    init(policy: PinkhaTorahPropertyPolicy = .shared,
         catalog: PinkhaTorahNativePropertyCatalog = .shared,
         existingSearch: ExistingSearch? = nil) {
        self.policy = policy
        self.catalog = catalog
        self.existingSearch = existingSearch
    }

    func invalidate(spaceId: String) {
        catalog.invalidate(spaceId: spaceId)
    }

    func load(text: String, data: PropertiesSearchData) async throws -> PinkhaPropertyPickerSearchResult {
        try Task.checkCancellation()
        let excluded = data.excludedRelationsIds.filter { !data.hiddenRelationsIds.contains($0) }
        let manifest: PinkhaSpaceManifest?
        do {
            manifest = try await policy.loadPickerManifest(spaceId: data.spaceId)
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            try Task.checkCancellation()
            manifest = nil
        }
        try Task.checkCancellation()
        let identities = manifest.flatMap { PinkhaInternalPropertyIdentities(manifest: $0) }

        let eligible: Bool
        if PinkhaRuntime.enabled {
            eligible = await policy.canAddPropertyInPicker(
                propertyId: "", key: TorahNativePropertyDefinition.all[0].key,
                target: data.target, spaceId: data.spaceId, manifest: manifest
            )
        } else {
            eligible = false
        }
        try Task.checkCancellation()

        var existing: [PropertyDetails] = []
        var existingFailed = false
        do {
            let found: [PropertyDetails]
            if let existingSearch {
                found = try await existingSearch(text, excluded, data.spaceId)
            } else {
                found = try await searchService.searchRelations(
                    text: text, excludedIds: excluded, spaceId: data.spaceId
                )
            }
            try Task.checkCancellation()
            // A failed manifest read cannot expose canonical/order rows whose
            // real IDs have not been resolved. Native format creation stays usable.
            if let identities {
                existing = found.filter {
                    $0.spaceId == data.spaceId && !$0.isDeleted && !$0.id.isEmpty
                        && !identities.isInternal(propertyId: $0.id, key: $0.key)
                        && TorahNativePropertyDefinition.definition(for: $0.key) == nil
                }
            } else if !PinkhaRuntime.enabled {
                existing = found.filter { $0.spaceId == data.spaceId && !$0.isDeleted && !$0.id.isEmpty }
            }
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            try Task.checkCancellation()
            existingFailed = true
        }

        let native: [PropertyDetails]
        let nativeLookupFailed: Bool
        if eligible {
            let lookup = try await catalog.nativePropertyLookupForReadOnlyPicker(spaceId: data.spaceId)
            native = lookup.properties.filter {
                !excluded.contains($0.id) && PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: $0, query: text)
            }
            nativeLookupFailed = !lookup.failures.isEmpty
        } else {
            native = []
            nativeLookupFailed = false
        }
        try Task.checkCancellation()

        let identityUnavailable = PinkhaRuntime.enabled && identities == nil
        let nativeFailed = identityUnavailable || nativeLookupFailed

        var ids = Set<String>()
        var keys = Set<String>()
        let properties = (native + existing).filter {
            guard !ids.contains($0.id), $0.key.isEmpty || !keys.contains($0.key) else { return false }
            ids.insert($0.id)
            if !$0.key.isEmpty { keys.insert($0.key) }
            return true
        }
        return .init(properties: properties, nativeLookupFailed: nativeFailed,
                     existingLookupFailed: existingFailed)
    }
}
