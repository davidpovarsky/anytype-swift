import Foundation
import PinkhaKit
import Services
import Factory
import OSLog
import SwiftProtobuf

private let logger = Logger(subsystem: "com.anytype.pinkha", category: "TorahNativeCatalog")

public final class PinkhaTorahNativePropertyCatalog: Sendable {
    public static let shared = PinkhaTorahNativePropertyCatalog()

    private final class CacheBox: @unchecked Sendable {
        private let lock = NSLock()
        private var cache: [String: [PropertyDetails]] = [:]

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

        func invalidate(spaceId: String) {
            lock.lock()
            defer { lock.unlock() }
            cache.removeValue(forKey: spaceId)
        }

        func clear() {
            lock.lock()
            defer { lock.unlock() }
            cache.removeAll()
        }
    }

    private let cache = CacheBox()
    private let policy: PinkhaTorahPropertyPolicy

    @Injected(\.searchMiddleService)
    private var search: any SearchMiddleServiceProtocol

    public init(policy: PinkhaTorahPropertyPolicy = .shared) {
        self.policy = policy
    }

    public func invalidate(spaceId: String? = nil) {
        if let spaceId {
            cache.invalidate(spaceId: spaceId)
        } else {
            cache.clear()
        }
    }

    /// Resolves verified native PropertyDetails descriptors for the given Space.
    /// Strictly queries fixed native definitions, checks identity sourceObject, wireFormat=11, and readOnlyValue=true.
    public func nativeProperties(spaceId: String) async -> [PropertyDetails] {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return [] }
        if let cached = cache.get(spaceId: spaceId) {
            let valid = cached.filter {
                $0.spaceId == spaceId && !$0.isDeleted && $0.isReadOnlyValue && $0.format == .tag
            }
            if valid.count == TorahNativePropertyDefinition.all.count {
                return valid
            } else {
                cache.invalidate(spaceId: spaceId)
            }
        }

        var results: [PropertyDetails] = []
        var queryFailed = false

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
                let matching = records
                    .map { PropertyDetails(details: $0) }
                    .filter { property in
                        property.key == definition.key &&
                        property.spaceId == spaceId &&
                        !property.isDeleted &&
                        property.sourceObject == "_br" + definition.key &&
                        property.format == .tag &&
                        property.isReadOnlyValue
                    }

                if matching.count > 1 {
                    logger.error("Ambiguous duplicate records for native property \(definition.key) in space \(spaceId). Refusing to select arbitrarily.")
                    continue
                }

                if let found = matching.first {
                    results.append(found)
                }
            } catch {
                queryFailed = true
                logger.error("Failed to query native property \(definition.key) in space \(spaceId): \(error.localizedDescription)")
            }
        }

        if !queryFailed && results.count == TorahNativePropertyDefinition.all.count {
            cache.set(spaceId: spaceId, properties: results)
            return results
        }

        // If not all 3 properties were found in index (e.g. unprovisioned space or cold start),
        // ensure space is bootstrapped to provision native schema, then retry lookup once.
        if results.count < TorahNativePropertyDefinition.all.count {
            if (try? await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceId)) != nil {
                var retryResults: [PropertyDetails] = []
                var retryFailed = false
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
                        let matching = records
                            .map { PropertyDetails(details: $0) }
                            .filter { property in
                                property.key == definition.key &&
                                property.spaceId == spaceId &&
                                !property.isDeleted &&
                                property.sourceObject == "_br" + definition.key &&
                                property.format == .tag &&
                                property.isReadOnlyValue
                            }
                        if let found = matching.first {
                            retryResults.append(found)
                        }
                    } catch {
                        retryFailed = true
                    }
                }
                if !retryFailed && retryResults.count == TorahNativePropertyDefinition.all.count {
                    cache.set(spaceId: spaceId, properties: retryResults)
                    return retryResults
                }
                if retryResults.isNotEmpty {
                    return retryResults
                }
            }
        }

        return results
    }

    /// Searches verified native properties for the given query, respecting target eligibility and exclusions.
    /// Internal access modifier: uses internal `PropertiesModuleTarget`.
    func searchNativeProperties(
        text: String,
        excludedIds: [String],
        target: PropertiesModuleTarget,
        spaceId: String
    ) async -> [PropertyDetails] {
        // Only eligible targets (writing types) may receive native properties
        guard await policy.canAddPropertyAsync(
            propertyId: "", key: TorahNativePropertyDefinition.all[0].key, target: target, spaceId: spaceId
        ) else {
            return []
        }

        let allNative = await nativeProperties(spaceId: spaceId)
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)

        return allNative.filter { property in
            guard !excludedIds.contains(property.id) else { return false }
            guard !trimmed.isEmpty else { return true }

            let definition = TorahNativePropertyDefinition.definition(for: property.key)
            let hebrewMatch = property.name.localizedCaseInsensitiveContains(trimmed) ||
                (definition?.name.localizedCaseInsensitiveContains(trimmed) ?? false)
            let englishMatch = definition?.englishName.localizedCaseInsensitiveContains(trimmed) ?? false
            let keyMatch = property.key.localizedCaseInsensitiveContains(trimmed)

            return hebrewMatch || englishMatch || keyMatch
        }
    }
}
