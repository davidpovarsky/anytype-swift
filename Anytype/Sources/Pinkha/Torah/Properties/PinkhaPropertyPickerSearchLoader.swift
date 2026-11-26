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
    @Injected(\.searchService)
    private var searchService: any SearchServiceProtocol

    func invalidate(spaceId: String) {
        PinkhaTorahNativePropertyCatalog.shared.invalidate(spaceId: spaceId)
    }

    func load(text: String, data: PropertiesSearchData) async throws -> PinkhaPropertyPickerSearchResult {
        try Task.checkCancellation()
        let excluded = data.excludedRelationsIds.filter { !data.hiddenRelationsIds.contains($0) }
        let policy = PinkhaTorahPropertyPolicy.shared
        let catalog = PinkhaTorahNativePropertyCatalog.shared
        let identity = await policy.awaitInternalIdentity(spaceId: data.spaceId)
        try Task.checkCancellation()

        let eligible = await policy.canAddPropertyAsync(
            propertyId: "", key: TorahNativePropertyDefinition.all[0].key,
            target: data.target, spaceId: data.spaceId
        )
        try Task.checkCancellation()

        var existing: [PropertyDetails] = []
        var existingFailed = false
        do {
            let found = try await searchService.searchRelations(
                text: text, excludedIds: excluded, spaceId: data.spaceId
            )
            try Task.checkCancellation()
            // A failed manifest read cannot expose canonical/order rows whose
            // real IDs have not been resolved. Native format creation stays usable.
            if case .known(let identities) = identity {
                existing = found.filter {
                    !identities.isInternal(propertyId: $0.id, key: $0.key)
                        && TorahNativePropertyDefinition.definition(for: $0.key) == nil
                }
            } else if !PinkhaRuntime.enabled {
                existing = found
            }
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            try Task.checkCancellation()
            existingFailed = true
        }

        let native: [PropertyDetails]
        if eligible {
            native = await catalog.searchNativeProperties(
                text: text, excludedIds: excluded, target: data.target, spaceId: data.spaceId
            )
        } else {
            native = []
        }
        try Task.checkCancellation()

        let identityUnavailable: Bool
        switch identity {
        case .known: identityUnavailable = false
        case .loading, .unavailable: identityUnavailable = PinkhaRuntime.enabled
        }
        let nativeFailed = identityUnavailable
            || (eligible && !catalog.lastLookupDiagnostics(spaceId: data.spaceId).isEmpty)

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
