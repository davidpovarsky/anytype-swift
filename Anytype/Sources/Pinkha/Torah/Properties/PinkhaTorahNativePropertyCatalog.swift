import Foundation
import PinkhaKit
import Services
import Factory
import OSLog
import SwiftProtobuf

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

public final class PinkhaTorahNativePropertyCatalog: Sendable {
    public static let shared = PinkhaTorahNativePropertyCatalog()

    private final class CacheBox: @unchecked Sendable {
        private let lock = NSLock()
        private var cache: [String: [PropertyDetails]] = [:]
        private var diagnostics: [String: [String: NativePropertyLookupFailureReason]] = [:]

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

        func invalidate(spaceId: String) {
            lock.lock()
            defer { lock.unlock() }
            cache.removeValue(forKey: spaceId)
            diagnostics.removeValue(forKey: spaceId)
        }

        func clear() {
            lock.lock()
            defer { lock.unlock() }
            cache.removeAll()
            diagnostics.removeAll()
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

    public init(
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
