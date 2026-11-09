import Foundation
import PinkhaKit
import Services
import AnytypeCore
import Factory
import OSLog
import SwiftProtobuf
import ProtobufMessages

private let logger = Logger(subsystem: "com.anytype.pinkha", category: "TorahNativeCatalog")

public enum NativePropertyLookupFailureReason: Equatable, Sendable {
    case runtimeDisabled
    case emptySpaceId
    case targetIneligible
    case notFoundInIndex
    case ambiguousDuplicateRecords(count: Int)
    case invalidDescriptor(String)
    case searchError(String)
}

public struct TorahTypeRelationIds: Equatable, Sendable {
    public let recommended: [String]
    public let featured: [String]
    public let hidden: [String]

    public init(recommended: [String], featured: [String], hidden: [String]) {
        self.recommended = recommended
        self.featured = featured
        self.hidden = hidden
    }
}

public final class PinkhaTorahNativePropertyCatalog: Sendable {
    public static let shared = PinkhaTorahNativePropertyCatalog()

    private final class CacheBox: @unchecked Sendable {
        private let lock = NSLock()
        private var cache: [String: [PropertyDetails]] = [:]
        private var diagnostics: [String: [String: NativePropertyLookupFailureReason]] = [:]
        private var typeRelations: [String: [String: TorahTypeRelationIds]] = [:]

        func get(spaceId: String) -> [PropertyDetails]? {
            lock.lock()
            defer { lock.unlock() }
            return cache[spaceId]
        }

        func set(spaceId: String, properties: [PropertyDetails]) {
            lock.lock()
            defer { lock.unlock() }
            cache[spaceId] = properties
        }

        func setDiagnostics(spaceId: String, reasons: [String: NativePropertyLookupFailureReason]) {
            lock.lock()
            defer { lock.unlock() }
            diagnostics[spaceId] = reasons
        }

        func getDiagnostics(spaceId: String) -> [String: NativePropertyLookupFailureReason] {
            lock.lock()
            defer { lock.unlock() }
            return diagnostics[spaceId] ?? [:]
        }

        func getTypeRelations(spaceId: String, typeId: String) -> TorahTypeRelationIds? {
            lock.lock()
            defer { lock.unlock() }
            return typeRelations[spaceId]?[typeId]
        }

        @discardableResult
        func setTypeRelations(spaceId: String, typeId: String, relations: TorahTypeRelationIds) -> Bool {
            lock.lock()
            defer { lock.unlock() }
            var spaceMap = typeRelations[spaceId] ?? [:]
            let changed = spaceMap[typeId] != relations
            spaceMap[typeId] = relations
            typeRelations[spaceId] = spaceMap
            return changed
        }

        func invalidate(spaceId: String) {
            lock.lock()
            defer { lock.unlock() }
            cache.removeValue(forKey: spaceId)
            diagnostics.removeValue(forKey: spaceId)
            typeRelations.removeValue(forKey: spaceId)
        }

        func clear() {
            lock.lock()
            defer { lock.unlock() }
            cache.removeAll()
            diagnostics.removeAll()
            typeRelations.removeAll()
        }
    }

    private let cache = CacheBox()
    private let policy: PinkhaTorahPropertyPolicy
    private let searchOverride: (any SearchMiddleServiceProtocol)?
    private let storageOverride: (any PropertyDetailsStorageProtocol)?

    @Injected(\.searchMiddleService)
    private var defaultSearch: any SearchMiddleServiceProtocol

    @Injected(\.propertyDetailsStorage)
    private var defaultStorage: any PropertyDetailsStorageProtocol

    private var search: any SearchMiddleServiceProtocol {
        searchOverride ?? defaultSearch
    }

    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol {
        storageOverride ?? defaultStorage
    }

    init(
        policy: PinkhaTorahPropertyPolicy = .shared,
        searchService: (any SearchMiddleServiceProtocol)? = nil,
        propertyDetailsStorage: (any PropertyDetailsStorageProtocol)? = nil
    ) {
        self.policy = policy
        self.searchOverride = searchService
        self.storageOverride = propertyDetailsStorage
    }

    public func invalidate(spaceId: String? = nil) {
        if let spaceId {
            cache.invalidate(spaceId: spaceId)
        } else {
            cache.clear()
        }
    }

    public func lastLookupDiagnostics(spaceId: String) -> [String: NativePropertyLookupFailureReason] {
        cache.getDiagnostics(spaceId: spaceId)
    }

    /// Synchronously returns verified native PropertyDetails cached for `spaceId` or present in `propertyDetailsStorage`.
    public func cachedNativeProperties(spaceId: String) -> [PropertyDetails] {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return [] }
        if let cached = cache.get(spaceId: spaceId) {
            let valid = cached.filter { prop in
                guard let def = TorahNativePropertyDefinition.definition(for: prop.key) else { return false }
                return Self.isVerifiedNativeDescriptor(prop, definition: def, spaceId: spaceId)
            }
            if !valid.isEmpty {
                return valid
            }
        }
        let storageCandidates = propertyDetailsStorage.relationsDetails(spaceId: spaceId)
        var found: [PropertyDetails] = []
        for def in TorahNativePropertyDefinition.all {
            let matching = storageCandidates.filter {
                Self.isVerifiedNativeDescriptor($0, definition: def, spaceId: spaceId)
            }
            if matching.count == 1, let prop = matching.first {
                found.append(prop)
            }
        }
        if found.count == TorahNativePropertyDefinition.all.count {
            cache.set(spaceId: spaceId, properties: found)
        }
        return found
    }

    /// Called after `PinkhaSpaceBootstrapService.bootstrapSpace` finishes provisioning native properties.
    /// Populates the verified native property cache and live Type relation lists for all 3 writing Types,
    /// then notifies open documents and property sheets.
    public func refreshAfterBootstrap(manifest: PinkhaSpaceManifest) async {
        guard PinkhaRuntime.enabled, !manifest.spaceId.isEmpty else { return }
        let resolved = await resolveNativePropertiesOnce(spaceId: manifest.spaceId)
        if !resolved.properties.isEmpty {
            cache.set(spaceId: manifest.spaceId, properties: resolved.properties)
            cache.setDiagnostics(spaceId: manifest.spaceId, reasons: resolved.failures)
        }
        for typeId in manifest.registeredDocumentTypes.values where !typeId.isEmpty {
            if let liveDetails = await fetchLiveObjectDetails(id: typeId, spaceId: manifest.spaceId) {
                cache.setTypeRelations(
                    spaceId: manifest.spaceId,
                    typeId: typeId,
                    relations: TorahTypeRelationIds(
                        recommended: liveDetails.recommendedRelations,
                        featured: liveDetails.recommendedFeaturedRelations,
                        hidden: liveDetails.recommendedHiddenRelations
                    )
                )
            }
        }
        NotificationCenter.default.post(
            name: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            userInfo: ["spaceId": manifest.spaceId]
        )
    }

    /// Ensures the Space's native properties are provisioned/cached and the target Type's live relation lists
    /// are loaded, notifying observers if anything changed.
    public func ensureSpaceAndTypeReady(spaceId: String, typeId: String?) async {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return }
        let bootstrapService = Container.shared.pinkhaBootstrapService()
        var didChange = false

        if !bootstrapService.isNativeSchemaProvisioned(spaceId: spaceId) {
            if (try? await bootstrapService.bootstrapSpace(spaceId: spaceId)) != nil {
                didChange = true
            }
        }

        let beforeCount = cache.get(spaceId: spaceId)?.count ?? 0
        let props = await nativeProperties(spaceId: spaceId)
        if props.count != beforeCount && !props.isEmpty {
            didChange = true
        }

        if let typeId, !typeId.isEmpty, cache.getTypeRelations(spaceId: spaceId, typeId: typeId) == nil {
            if let liveDetails = await fetchLiveObjectDetails(id: typeId, spaceId: spaceId),
               liveDetails.isObjectType || policy.isTargetEligibleForNativeProperties(typeId: typeId, spaceId: spaceId) {
                let changed = cache.setTypeRelations(
                    spaceId: spaceId,
                    typeId: typeId,
                    relations: TorahTypeRelationIds(
                        recommended: liveDetails.recommendedRelations,
                        featured: liveDetails.recommendedFeaturedRelations,
                        hidden: liveDetails.recommendedHiddenRelations
                    )
                )
                if changed {
                    didChange = true
                }
            }
        }

        if didChange {
            NotificationCenter.default.post(
                name: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
                object: nil,
                userInfo: ["spaceId": spaceId]
            )
        }
    }

    /// Records updated Type relation lists immediately after `PropertiesService.updateTypeProperties` succeeds
    /// (bypassing `ObjectTypeSubscriptionDataBuilder`'s `noDepSubscription: true` lag) and notifies open documents/views.
    public func recordUpdatedTypeRelations(
        typeId: String,
        spaceId: String,
        recommendedIds: [String],
        featuredIds: [String],
        hiddenIds: [String]
    ) {
        guard !spaceId.isEmpty, !typeId.isEmpty else { return }
        cache.setTypeRelations(
            spaceId: spaceId,
            typeId: typeId,
            relations: TorahTypeRelationIds(
                recommended: recommendedIds,
                featured: featuredIds,
                hidden: hiddenIds
            )
        )
        NotificationCenter.default.post(
            name: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            userInfo: ["spaceId": spaceId, "typeId": typeId]
        )
    }

    /// Returns the best known relation ID lists (`recommended`, `featured`, `hidden`) for `typeId`.
    /// Uses cached live Type relations when available; otherwise falls back to the caller's lists and
    /// synthesizes missing attached native property IDs if `ObjectTypeProvider` still holds the pre-provision snapshot.
    public func resolvedTypeRelationIds(
        typeId: String,
        fallbackRecommended: [String],
        fallbackFeatured: [String],
        fallbackHidden: [String],
        spaceId: String
    ) -> TorahTypeRelationIds {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty, !typeId.isEmpty else {
            return TorahTypeRelationIds(
                recommended: fallbackRecommended,
                featured: fallbackFeatured,
                hidden: fallbackHidden
            )
        }
        if let cached = cache.getTypeRelations(spaceId: spaceId, typeId: typeId) {
            return cached
        }
        var recommended = fallbackRecommended
        let featured = fallbackFeatured
        let hidden = fallbackHidden
        if policy.isTargetEligibleForNativeProperties(typeId: typeId, spaceId: spaceId) {
            let nativeProps = cachedNativeProperties(spaceId: spaceId)
            let allExisting = Set(recommended + featured + hidden)
            // If ObjectTypeProvider still holds the Step-7 snapshot before native properties were attached,
            // none of the native properties will be in recommended/featured/hidden yet.
            let anyNativePresent = nativeProps.contains { allExisting.contains($0.id) }
            if !anyNativePresent {
                for prop in nativeProps where !allExisting.contains(prop.id) {
                    recommended.append(prop.id)
                }
            }
        }
        return TorahTypeRelationIds(recommended: recommended, featured: featured, hidden: hidden)
    }

    /// Resolves `[PropertyDetails]` for `ids` using `storage` with fallback to cached verified native properties,
    /// so `PropertyDetailsStorage` subscription lag never drops native Torah properties.
    public func resolveRelationDetails(
        ids: [String],
        from storage: any PropertyDetailsStorageProtocol,
        spaceId: String
    ) -> [PropertyDetails] {
        guard !ids.isEmpty else { return [] }
        var resolved = storage.relationsDetails(ids: ids, spaceId: spaceId)
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return resolved }
        let nativeById = Dictionary(uniqueKeysWithValues: cachedNativeProperties(spaceId: spaceId).map { ($0.id, $0) })
        guard !nativeById.isEmpty else { return resolved }
        let existingIds = Set(resolved.map(\.id))
        for id in ids where !existingIds.contains(id) {
            if let nativeProp = nativeById[id] {
                resolved.append(nativeProp)
            }
        }
        return resolved
    }

    /// Resolves a single `PropertyDetails` by `id` or `key` from `storage` or verified native catalog.
    public func resolvePropertyDetails(
        id: String,
        key: String,
        from storage: any PropertyDetailsStorageProtocol,
        spaceId: String
    ) async -> PropertyDetails? {
        if !key.isEmpty, let found = try? storage.relationsDetails(key: key, spaceId: spaceId) {
            return found
        }
        if !id.isEmpty, let found = storage.relationsDetails(ids: [id], spaceId: spaceId).first {
            return found
        }
        let syncCached = cachedNativeProperties(spaceId: spaceId)
        if let found = syncCached.first(where: { (!id.isEmpty && $0.id == id) || (!key.isEmpty && $0.key == key) }) {
            return found
        }
        if TorahNativePropertyDefinition.definition(for: key) != nil {
            let asyncProps = await nativeProperties(spaceId: spaceId)
            return asyncProps.first(where: { (!id.isEmpty && $0.id == id) || (!key.isEmpty && $0.key == key) })
        }
        return nil
    }

    /// Fetches live `ObjectDetails` for `id` in `spaceId` via `ClientCommands.objectShow`, returning nil when unavailable/mocked.
    public func fetchLiveObjectDetails(id: String, spaceId: String) async -> ObjectDetails? {
        guard !id.isEmpty, !spaceId.isEmpty else { return nil }
        guard let response = try? await ClientCommands.objectShow(.with {
            $0.contextID = id
            $0.objectID = id
            $0.spaceID = spaceId
        }).invoke(qos: .userInitiated),
              let value = response.objectView.details.first(where: { $0.id == id })?.details,
              let details = try? ObjectDetails(protobufStruct: value),
              details.id == id,
              details.spaceId == spaceId else {
            return nil
        }
        return details
    }

    /// Resolves the freshest `[PropertyDetails]` lists for a Type before mutating its recommended/featured/hidden properties.
    public func resolveCurrentTypeProperties(
        typeId: String,
        spaceId: String,
        fallbackRecommendedIds: [String],
        fallbackFeaturedIds: [String],
        fallbackHiddenIds: [String],
        fallbackRecommendedDetails: [PropertyDetails],
        fallbackFeaturedDetails: [PropertyDetails],
        fallbackHiddenDetails: [PropertyDetails]
    ) async -> (recommended: [PropertyDetails], featured: [PropertyDetails], hidden: [PropertyDetails], resolvedSpaceId: String) {
        var resolvedSpaceId = spaceId
        var recIds = fallbackRecommendedIds
        var featIds = fallbackFeaturedIds
        var hidIds = fallbackHiddenIds

        if let liveDetails = await fetchLiveObjectDetails(id: typeId, spaceId: spaceId) {
            resolvedSpaceId = liveDetails.spaceId
            recIds = liveDetails.recommendedRelations
            featIds = liveDetails.recommendedFeaturedRelations
            hidIds = liveDetails.recommendedHiddenRelations
            cache.setTypeRelations(
                spaceId: resolvedSpaceId,
                typeId: typeId,
                relations: TorahTypeRelationIds(recommended: recIds, featured: featIds, hidden: hidIds)
            )
        } else if !resolvedSpaceId.isEmpty, let cached = cache.getTypeRelations(spaceId: resolvedSpaceId, typeId: typeId) {
            recIds = cached.recommended
            featIds = cached.featured
            hidIds = cached.hidden
        }

        if !resolvedSpaceId.isEmpty {
            _ = await nativeProperties(spaceId: resolvedSpaceId)
        }

        let storage = propertyDetailsStorage
        func mergeDetails(ids: [String], fallback: [PropertyDetails]) -> [PropertyDetails] {
            var list = resolveRelationDetails(ids: ids, from: storage, spaceId: resolvedSpaceId)
            let byFallbackId = Dictionary(uniqueKeysWithValues: fallback.map { ($0.id, $0) })
            let existing = Set(list.map(\.id))
            for id in ids where !existing.contains(id) {
                if let fb = byFallbackId[id] {
                    list.append(fb)
                }
            }
            if list.isEmpty && !fallback.isEmpty && ids == fallback.map(\.id) {
                return fallback
            }
            return list
        }

        return (
            recommended: mergeDetails(ids: recIds, fallback: fallbackRecommendedDetails),
            featured: mergeDetails(ids: featIds, fallback: fallbackFeaturedDetails),
            hidden: mergeDetails(ids: hidIds, fallback: fallbackHiddenDetails),
            resolvedSpaceId: resolvedSpaceId
        )
    }

    /// Builds `ParsedProperties` for a Type document using live/cached Type relation IDs and verified native fallbacks.
    func buildParsedPropertiesForType(document: any BaseDocumentProtocol) -> ParsedProperties {
        guard let details = document.details else { return .empty }
        let storage = propertyDetailsStorage
        let relIds = resolvedTypeRelationIds(
            typeId: details.id,
            fallbackRecommended: details.recommendedRelations,
            fallbackFeatured: details.recommendedFeaturedRelations,
            fallbackHidden: details.recommendedHiddenRelations,
            spaceId: document.spaceId
        )
        let recommendedRelations = resolveRelationDetails(ids: relIds.recommended, from: storage, spaceId: document.spaceId)
            .filter { $0.key != BundledPropertyKey.description.rawValue }
        let recommendedFeaturedRelations = resolveRelationDetails(ids: relIds.featured, from: storage, spaceId: document.spaceId)
            .filter { $0.key != BundledPropertyKey.description.rawValue }
        let recommendedHiddenRelations = resolveRelationDetails(ids: relIds.hidden, from: storage, spaceId: document.spaceId)
            .filter { $0.key != BundledPropertyKey.description.rawValue }

        return Container.shared.propertiesBuilder().parsedProperties(
            objectProperties: [],
            objectFeaturedProperties: [],
            recommendedProperties: recommendedRelations,
            recommendedFeaturedProperties: recommendedFeaturedRelations,
            recommendedHiddenProperties: recommendedHiddenRelations,
            objectId: document.objectId,
            propertyValuesIsLocked: !document.permissions.canEditRelationValues,
            storage: document.detailsStorage
        )
    }

    /// Resolves verified native PropertyDetails descriptors for the given Space.
    /// Strictly queries fixed native definitions, checks identity sourceObject, wireFormat=11, and readOnlyValue=true.
    public func nativeProperties(spaceId: String) async -> [PropertyDetails] {
        guard PinkhaRuntime.enabled else {
            return []
        }
        guard !spaceId.isEmpty else {
            return []
        }
        if let cached = cache.get(spaceId: spaceId) {
            let valid = cached.filter {
                $0.spaceId == spaceId &&
                !$0.isDeleted &&
                $0.isReadOnlyValue &&
                $0.format == .tag &&
                $0.sourceObject == "_br" + $0.key
            }
            if valid.count == TorahNativePropertyDefinition.all.count {
                cache.setDiagnostics(spaceId: spaceId, reasons: [:])
                return valid
            } else {
                cache.invalidate(spaceId: spaceId)
            }
        }

        let firstAttempt = await resolveNativePropertiesOnce(spaceId: spaceId)
        if firstAttempt.failures.isEmpty && firstAttempt.properties.count == TorahNativePropertyDefinition.all.count {
            cache.set(spaceId: spaceId, properties: firstAttempt.properties)
            cache.setDiagnostics(spaceId: spaceId, reasons: [:])
            return firstAttempt.properties
        }

        // Do not retry or override if failure was due to ambiguous duplicate records
        let hasAmbiguousDuplicates = firstAttempt.failures.values.contains {
            if case .ambiguousDuplicateRecords = $0 { return true }
            return false
        }

        if !hasAmbiguousDuplicates && firstAttempt.properties.count < TorahNativePropertyDefinition.all.count {
            if (try? await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceId)) != nil {
                let retryAttempt = await resolveNativePropertiesOnce(spaceId: spaceId)
                cache.setDiagnostics(spaceId: spaceId, reasons: retryAttempt.failures)
                if retryAttempt.failures.isEmpty && retryAttempt.properties.count == TorahNativePropertyDefinition.all.count {
                    cache.set(spaceId: spaceId, properties: retryAttempt.properties)
                    return retryAttempt.properties
                }
                if retryAttempt.properties.isNotEmpty {
                    return retryAttempt.properties
                }
            }
        }

        cache.setDiagnostics(spaceId: spaceId, reasons: firstAttempt.failures)
        return firstAttempt.properties
    }

    private func resolveNativePropertiesOnce(
        spaceId: String
    ) async -> (properties: [PropertyDetails], failures: [String: NativePropertyLookupFailureReason]) {
        var results: [PropertyDetails] = []
        var failures: [String: NativePropertyLookupFailureReason] = [:]
        let storageCandidates = propertyDetailsStorage.relationsDetails(spaceId: spaceId)

        for definition in TorahNativePropertyDefinition.all {
            do {
                let records = try await search.search(
                    spaceId: spaceId,
                    filters: [.with {
                        $0.relationKey = BundledPropertyKey.relationKey.rawValue
                        $0.condition = .equal
                        $0.value = definition.key.protobufValue
                    }],
                    keys: PropertyDetails.subscriptionKeys.map(\.rawValue),
                    limit: 0
                )
                var candidates = records
                    .map { PropertyDetails(details: $0) }
                    .filter { $0.key == definition.key && $0.spaceId == spaceId && !$0.isDeleted }

                if candidates.isEmpty {
                    candidates = storageCandidates.filter {
                        $0.key == definition.key && $0.spaceId == spaceId && !$0.isDeleted
                    }
                }

                let verified = candidates.filter { property in
                    Self.isVerifiedNativeDescriptor(property, definition: definition, spaceId: spaceId)
                }

                // Deduplicate identical property IDs if search + storage returned the same record
                var uniqueById: [PropertyDetails] = []
                var seenIds = Set<String>()
                for prop in verified {
                    if seenIds.insert(prop.id).inserted {
                        uniqueById.append(prop)
                    }
                }

                if uniqueById.count > 1 {
                    logger.error("Ambiguous duplicate records (\(uniqueById.count)) for native property \(definition.key) in space \(spaceId). Refusing to select arbitrarily.")
                    failures[definition.key] = .ambiguousDuplicateRecords(count: uniqueById.count)
                    continue
                }

                if let found = uniqueById.first {
                    results.append(found)
                } else if let invalid = candidates.first {
                    let reason = "id=\(invalid.id) format=\(invalid.format) readOnlyValue=\(invalid.isReadOnlyValue) source=\(invalid.sourceObject)"
                    logger.error("Rejected unverified native property candidate for \(definition.key) in space \(spaceId): \(reason)")
                    failures[definition.key] = .invalidDescriptor(reason)
                } else {
                    failures[definition.key] = .notFoundInIndex
                }
            } catch {
                logger.error("Failed to query native property \(definition.key) in space \(spaceId): \(error.localizedDescription)")
                failures[definition.key] = .searchError(error.localizedDescription)
            }
        }

        return (results, failures)
    }

    public static func isVerifiedNativeDescriptor(
        _ property: PropertyDetails,
        definition: TorahNativePropertyDefinition,
        spaceId: String
    ) -> Bool {
        property.key == definition.key &&
        property.spaceId == spaceId &&
        !property.id.isEmpty &&
        !property.isDeleted &&
        property.sourceObject == "_br" + definition.key &&
        property.format == .tag &&
        property.isReadOnlyValue
    }

    /// Searches verified native properties for the given query, respecting target eligibility and exclusions.
    /// Internal access modifier: uses internal `PropertiesModuleTarget`.
    func searchNativeProperties(
        text: String,
        excludedIds: [String],
        target: PropertiesModuleTarget,
        spaceId: String
    ) async -> [PropertyDetails] {
        guard PinkhaRuntime.enabled else { return [] }
        guard !spaceId.isEmpty else { return [] }

        // Only eligible targets (writing types / eligible Sets) may receive native properties
        guard await policy.canAddPropertyAsync(
            propertyId: "", key: TorahNativePropertyDefinition.all[0].key, target: target, spaceId: spaceId
        ) else {
            var targetFailures: [String: NativePropertyLookupFailureReason] = [:]
            for def in TorahNativePropertyDefinition.all {
                targetFailures[def.key] = .targetIneligible
            }
            cache.setDiagnostics(spaceId: spaceId, reasons: targetFailures)
            return []
        }

        let allNative = await nativeProperties(spaceId: spaceId)
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)

        return allNative.filter { property in
            guard !excludedIds.contains(property.id) else { return false }
            guard !trimmed.isEmpty else { return true }
            return Self.matchesSearchQuery(property: property, query: trimmed)
        }
    }

    public static func matchesSearchQuery(property: PropertyDetails, query: String) -> Bool {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return true }
        guard let definition = TorahNativePropertyDefinition.definition(for: property.key) else {
            return property.name.localizedCaseInsensitiveContains(trimmed)
        }

        let candidates = searchTerms(for: definition, storedName: property.name)
        let normalizedQuery = normalizeSearchToken(trimmed)

        for candidate in candidates {
            if candidate.localizedCaseInsensitiveContains(trimmed) {
                return true
            }
            if !normalizedQuery.isEmpty && normalizeSearchToken(candidate).localizedCaseInsensitiveContains(normalizedQuery) {
                return true
            }
        }
        return false
    }

    private static func searchTerms(for definition: TorahNativePropertyDefinition, storedName: String) -> [String] {
        var terms: [String] = [storedName, definition.name, definition.englishName, definition.key]
        switch definition.kind {
        case .ref:
            terms.append(contentsOf: ["מקור/ות", "מקורות", "מקור", "Source(s)", "Sources", "Source"])
        case .topic:
            terms.append(contentsOf: ["נושא", "נושאים", "Topic(s)", "Topics", "Topic"])
        case .word:
            terms.append(contentsOf: [
                "מילה / ערך", "מילים / ערכים", "מילה", "מילים", "ערך", "ערכים",
                "Word / entry", "Words / entries", "Word", "Words", "Entry", "Entries"
            ])
        }
        return terms
    }

    private static func normalizeSearchToken(_ text: String) -> String {
        text
            .replacingOccurrences(of: "/", with: "")
            .replacingOccurrences(of: "(", with: "")
            .replacingOccurrences(of: ")", with: "")
            .components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }
            .joined(separator: " ")
    }
}
