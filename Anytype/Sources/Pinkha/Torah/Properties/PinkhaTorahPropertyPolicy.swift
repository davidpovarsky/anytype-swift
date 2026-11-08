import Foundation
import PinkhaKit
import Services
import Factory
import OSLog

private let logger = Logger(subsystem: "com.anytype.pinkha", category: "TorahPropertyPolicy")

public struct PinkhaInternalPropertyIdentities: Equatable, Sendable {
    public let canonicalPropertyId: String
    public let canonicalPropertyKey: String
    public let orderPropertyId: String
    public let orderPropertyKey: String

    public init(
        canonicalPropertyId: String,
        canonicalPropertyKey: String,
        orderPropertyId: String = "",
        orderPropertyKey: String = ""
    ) {
        self.canonicalPropertyId = canonicalPropertyId
        self.canonicalPropertyKey = canonicalPropertyKey
        self.orderPropertyId = orderPropertyId
        self.orderPropertyKey = orderPropertyKey
    }

    public init?(manifest: PinkhaSpaceManifest) {
        let cId = manifest.documentAssociationsPropertyId.trimmingCharacters(in: .whitespacesAndNewlines)
        let cKey = manifest.documentAssociationsPropertyKey.trimmingCharacters(in: .whitespacesAndNewlines)
        let oId = manifest.orderPropertyId.trimmingCharacters(in: .whitespacesAndNewlines)
        let oKey = manifest.orderPropertyKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cId.isEmpty || !cKey.isEmpty || !oId.isEmpty || !oKey.isEmpty else {
            return nil
        }
        self.init(
            canonicalPropertyId: cId,
            canonicalPropertyKey: cKey,
            orderPropertyId: oId,
            orderPropertyKey: oKey
        )
    }

    public func isCanonical(propertyId: String, key: String) -> Bool {
        (!canonicalPropertyId.isEmpty && propertyId == canonicalPropertyId) ||
        (!canonicalPropertyKey.isEmpty && key == canonicalPropertyKey)
    }

    public func isOrder(propertyId: String, key: String) -> Bool {
        (!orderPropertyId.isEmpty && propertyId == orderPropertyId) ||
        (!orderPropertyKey.isEmpty && key == orderPropertyKey)
    }

    public func isInternal(propertyId: String, key: String) -> Bool {
        isCanonical(propertyId: propertyId, key: key) || isOrder(propertyId: propertyId, key: key)
    }
}

public enum InternalIdentityStatus: Equatable, Sendable {
    case known(PinkhaInternalPropertyIdentities)
    case loading
    case unavailable(String)
}

public enum CanonicalIdentityStatus: Equatable, Sendable {
    case known(propertyId: String, propertyKey: String)
    case loading
    case unavailable(String)
}

/// Downstream policy distinguishing internal Pinkha storage (canonical Torah JSON + hierarchy order)
/// from user-facing native and custom properties.
/// Enforces fail-closed rules, space isolation, target eligibility, and action permissions.
public final class PinkhaTorahPropertyPolicy: Sendable {
    public static let shared = PinkhaTorahPropertyPolicy()
    public static let canonicalIdentityDidChangeNotification = Notification.Name("PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification")

    private final class IdentityStore: @unchecked Sendable {
        private let lock = NSLock()
        private var statuses: [String: InternalIdentityStatus] = [:]
        private var inFlightTasks: [String: Task<InternalIdentityStatus, Never>] = [:]

        func getStatus(_ spaceId: String) -> InternalIdentityStatus? {
            lock.lock()
            defer { lock.unlock() }
            return statuses[spaceId]
        }

        func setStatus(_ spaceId: String, status: InternalIdentityStatus) {
            lock.lock()
            defer { lock.unlock() }
            statuses[spaceId] = status
        }

        func invalidate(_ spaceId: String?) {
            lock.lock()
            defer { lock.unlock() }
            if let spaceId {
                statuses.removeValue(forKey: spaceId)
                inFlightTasks.removeValue(forKey: spaceId)
            } else {
                statuses.removeAll()
                inFlightTasks.removeAll()
            }
        }

        func getOrStartTask(spaceId: String, work: @escaping () async -> InternalIdentityStatus) -> Task<InternalIdentityStatus, Never> {
            lock.lock()
            defer { lock.unlock() }
            if let existing = inFlightTasks[spaceId] {
                return existing
            }
            let task = Task {
                let result = await work()
                lock.lock()
                statuses[spaceId] = result
                inFlightTasks.removeValue(forKey: spaceId)
                lock.unlock()
                NotificationCenter.default.post(
                    name: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
                    object: nil,
                    userInfo: ["spaceId": spaceId]
                )
                return result
            }
            inFlightTasks[spaceId] = task
            statuses[spaceId] = .loading
            return task
        }
    }

    private let identityStore = IdentityStore()
    private let bootstrapService: any PinkhaSpaceBootstrapServiceProtocol

    public init(bootstrapService: any PinkhaSpaceBootstrapServiceProtocol = Container.shared.pinkhaBootstrapService()) {
        self.bootstrapService = bootstrapService
    }

    // MARK: - Invalidation & Retry

    public func invalidateCache(spaceId: String? = nil) {
        identityStore.invalidate(spaceId)
        NotificationCenter.default.post(
            name: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            userInfo: spaceId.map { ["spaceId": $0] }
        )
    }

    public func retryIdentityResolution(spaceId: String) {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return }
        identityStore.invalidate(spaceId)
        _ = resolveInternalIdentityTask(spaceId: spaceId)
    }

    // MARK: - Internal & Canonical Identity Tri-State Status

    /// Synchronously returns current internal identity status (canonical + order) for space.
    /// If uninitialized, triggers a deduplicated async task and returns .loading.
    public func internalIdentityStatus(spaceId: String) -> InternalIdentityStatus {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else {
            return .unavailable("Pinkha disabled or empty spaceId")
        }

        if let manifest = bootstrapService.manifest(forSpaceId: spaceId),
           manifest.spaceId == spaceId,
           let identities = PinkhaInternalPropertyIdentities(manifest: manifest) {
            let status = InternalIdentityStatus.known(identities)
            let previous = identityStore.getStatus(spaceId)
            identityStore.setStatus(spaceId, status: status)
            if previous != status, previous != nil {
                NotificationCenter.default.post(
                    name: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
                    object: nil,
                    userInfo: ["spaceId": spaceId]
                )
            }
            return status
        }

        if let cached = identityStore.getStatus(spaceId) {
            return cached
        }

        _ = resolveInternalIdentityTask(spaceId: spaceId)
        return .loading
    }

    /// Asynchronously awaits settled internal identity resolution.
    /// Retries automatically if a previous attempt ended in `.unavailable`.
    public func awaitInternalIdentity(spaceId: String) async -> InternalIdentityStatus {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else {
            return .unavailable("Pinkha disabled or empty spaceId")
        }

        if let manifest = bootstrapService.manifest(forSpaceId: spaceId),
           manifest.spaceId == spaceId,
           let identities = PinkhaInternalPropertyIdentities(manifest: manifest) {
            let status = InternalIdentityStatus.known(identities)
            identityStore.setStatus(spaceId, status: status)
            return status
        }

        if case .unavailable = identityStore.getStatus(spaceId) {
            identityStore.invalidate(spaceId)
        }

        let task = resolveInternalIdentityTask(spaceId: spaceId)
        return await task.value
    }

    /// Synchronously returns current canonical identity status for space.
    public func canonicalIdentityStatus(spaceId: String) -> CanonicalIdentityStatus {
        switch internalIdentityStatus(spaceId: spaceId) {
        case .known(let ids):
            if !ids.canonicalPropertyId.isEmpty || !ids.canonicalPropertyKey.isEmpty {
                return .known(propertyId: ids.canonicalPropertyId, propertyKey: ids.canonicalPropertyKey)
            }
            return .unavailable("Manifest has empty canonical association IDs")
        case .loading:
            return .loading
        case .unavailable(let reason):
            return .unavailable(reason)
        }
    }

    /// Asynchronously awaits settled canonical identity resolution.
    public func awaitCanonicalIdentity(spaceId: String) async -> CanonicalIdentityStatus {
        switch await awaitInternalIdentity(spaceId: spaceId) {
        case .known(let ids):
            if !ids.canonicalPropertyId.isEmpty || !ids.canonicalPropertyKey.isEmpty {
                return .known(propertyId: ids.canonicalPropertyId, propertyKey: ids.canonicalPropertyKey)
            }
            return .unavailable("Manifest has empty canonical association IDs")
        case .loading:
            return .loading
        case .unavailable(let reason):
            return .unavailable(reason)
        }
    }

    private func resolveInternalIdentityTask(spaceId: String) -> Task<InternalIdentityStatus, Never> {
        identityStore.getOrStartTask(spaceId: spaceId) { [weak self] in
            guard let self else { return .unavailable("Deallocated") }
            do {
                let manifest: PinkhaSpaceManifest?
                if let cached = self.bootstrapService.manifest(forSpaceId: spaceId), cached.spaceId == spaceId {
                    manifest = cached
                } else {
                    manifest = try await self.bootstrapService.bootstrapCanonicalSpace(spaceId: spaceId)
                }

                guard let manifest, manifest.spaceId == spaceId else {
                    return .unavailable("Manifest not found or space mismatch for \(spaceId)")
                }
                if let identities = PinkhaInternalPropertyIdentities(manifest: manifest) {
                    return .known(identities)
                } else {
                    return .unavailable("Manifest has empty internal property IDs")
                }
            } catch {
                logger.error("Failed to resolve canonical manifest for \(spaceId): \(error.localizedDescription)")
                return .unavailable(error.localizedDescription)
            }
        }
    }

    // MARK: - Canonical, Order & Internal Storage Identification

    /// Synchronously checks if a property is the internal canonical Torah association storage relation.
    /// Strictly matches verified manifest property ID or Key within the same Space.
    /// Never matches purely by Hebrew/English display name.
    public func isCanonicalStorage(propertyId: String, key: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        switch internalIdentityStatus(spaceId: spaceId) {
        case .known(let identities):
            let matches = identities.isCanonical(propertyId: propertyId, key: key)
            if matches {
                logger.debug("Identified canonical storage relation: id=\(propertyId), key=\(key), spaceId=\(spaceId)")
            }
            return matches
        case .loading, .unavailable:
            return false
        }
    }

    /// Asynchronously resolves the space manifest if needed and evaluates canonical storage.
    public func isCanonicalStorageAsync(propertyId: String, key: String, spaceId: String) async -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        switch await awaitInternalIdentity(spaceId: spaceId) {
        case .known(let identities):
            return identities.isCanonical(propertyId: propertyId, key: key)
        case .loading, .unavailable:
            return false
        }
    }

    /// Synchronously checks if a property is the internal hierarchy order (`סדר`) storage relation.
    public func isOrderStorage(propertyId: String, key: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        switch internalIdentityStatus(spaceId: spaceId) {
        case .known(let identities):
            let matches = identities.isOrder(propertyId: propertyId, key: key)
            if matches {
                logger.debug("Identified internal order relation: id=\(propertyId), key=\(key), spaceId=\(spaceId)")
            }
            return matches
        case .loading, .unavailable:
            return false
        }
    }

    /// Asynchronously resolves the space manifest if needed and evaluates order storage.
    public func isOrderStorageAsync(propertyId: String, key: String, spaceId: String) async -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        switch await awaitInternalIdentity(spaceId: spaceId) {
        case .known(let identities):
            return identities.isOrder(propertyId: propertyId, key: key)
        case .loading, .unavailable:
            return false
        }
    }

    /// Synchronously checks if a property is ANY internal Pinkha storage relation
    /// (canonical Torah association storage OR internal hierarchy order storage).
    /// Strictly matches verified manifest IDs/Keys within the same Space; never matches by display name.
    public func isInternalProperty(propertyId: String, key: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        switch internalIdentityStatus(spaceId: spaceId) {
        case .known(let identities):
            let matches = identities.isInternal(propertyId: propertyId, key: key)
            if matches {
                logger.debug("Identified internal Pinkha relation: id=\(propertyId), key=\(key), spaceId=\(spaceId)")
            }
            return matches
        case .loading, .unavailable:
            return false
        }
    }

    /// Asynchronously resolves the space manifest if needed and evaluates internal property status.
    public func isInternalPropertyAsync(propertyId: String, key: String, spaceId: String) async -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        switch await awaitInternalIdentity(spaceId: spaceId) {
        case .known(let identities):
            return identities.isInternal(propertyId: propertyId, key: key)
        case .loading, .unavailable:
            return false
        }
    }

    // MARK: - Native Derived Properties

    /// Checks if a property key is one of the three fixed native derived properties.
    public func isNativeDerived(key: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        guard TorahNativePropertyDefinition.definition(for: key) != nil else { return false }
        guard let manifest = bootstrapService.manifest(forSpaceId: spaceId), manifest.isComplete else {
            return false
        }
        return true
    }

    public func isNativeDerivedAsync(key: String, spaceId: String) async -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return false }
        guard TorahNativePropertyDefinition.definition(for: key) != nil else { return false }
        guard let manifest = await resolveManifest(spaceId: spaceId), manifest.isComplete else {
            return false
        }
        return true
    }

    // MARK: - Target Eligibility

    /// Checks if a type ID in the given space is eligible for native derived properties
    /// (strictly limited to the 3 writing types: chiddush, article, research).
    public func isTargetEligibleForNativeProperties(typeId: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty, !typeId.isEmpty else { return false }
        let manifest = bootstrapService.manifest(forSpaceId: spaceId)
        return TorahDocumentPropertyEligibility.includes(typeId: typeId, spaceId: spaceId, manifest: manifest)
    }

    public func isTargetEligibleForNativePropertiesAsync(typeId: String, spaceId: String) async -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty, !typeId.isEmpty else { return false }
        let manifest = await resolveManifest(spaceId: spaceId)
        return TorahDocumentPropertyEligibility.includes(typeId: typeId, spaceId: spaceId, manifest: manifest)
    }

    // MARK: - Operation Permissions

    /// Determines if adding this property to the given target is permitted.
    /// Internal access modifier: uses internal `PropertiesModuleTarget`.
    func canAddProperty(propertyId: String, key: String, target: PropertiesModuleTarget, spaceId: String) -> Bool {
        let status = internalIdentityStatus(spaceId: spaceId)
        switch status {
        case .loading, .unavailable:
            return false
        case .known(let identities):
            if identities.isInternal(propertyId: propertyId, key: key) {
                return false
            }
        }
        if TorahNativePropertyDefinition.definition(for: key) != nil {
            return isTargetEligible(target: target, spaceId: spaceId)
        }
        return true
    }

    func canAddPropertyAsync(propertyId: String, key: String, target: PropertiesModuleTarget, spaceId: String) async -> Bool {
        let status = await awaitInternalIdentity(spaceId: spaceId)
        switch status {
        case .loading, .unavailable:
            return false
        case .known(let identities):
            if identities.isInternal(propertyId: propertyId, key: key) {
                return false
            }
        }
        if TorahNativePropertyDefinition.definition(for: key) != nil {
            return await isTargetEligibleAsync(target: target, spaceId: spaceId)
        }
        return true
    }

    /// Determines if editing the value of this property through generic Anytype text editors is permitted.
    public func canEditGenericPropertyValue(propertyId: String, key: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return true }
        let status = internalIdentityStatus(spaceId: spaceId)
        switch status {
        case .loading, .unavailable:
            return false
        case .known(let identities):
            if identities.isInternal(propertyId: propertyId, key: key) {
                return false
            }
            if TorahNativePropertyDefinition.definition(for: key) != nil {
                return false
            }
            return true
        }
    }

    /// Determines if editing the definition of this property (rename, change format) is permitted.
    public func canEditPropertyDefinition(propertyId: String, key: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return true }
        let status = internalIdentityStatus(spaceId: spaceId)
        switch status {
        case .loading, .unavailable:
            return false
        case .known(let identities):
            if identities.isInternal(propertyId: propertyId, key: key) {
                return false
            }
            if TorahNativePropertyDefinition.definition(for: key) != nil {
                return false
            }
            return true
        }
    }

    /// Determines if deleting the property definition is permitted.
    public func canDeletePropertyDefinition(propertyId: String, key: String, spaceId: String) -> Bool {
        guard PinkhaRuntime.enabled, !spaceId.isEmpty else { return true }
        let status = internalIdentityStatus(spaceId: spaceId)
        switch status {
        case .loading, .unavailable:
            return false
        case .known(let identities):
            if identities.isInternal(propertyId: propertyId, key: key) {
                return false
            }
            if TorahNativePropertyDefinition.definition(for: key) != nil {
                return false
            }
            return true
        }
    }

    /// Determines if the property should be rendered in the document header.
    public func shouldRenderInHeader(propertyId: String, key: String, spaceId: String) -> Bool {
        if isInternalProperty(propertyId: propertyId, key: key, spaceId: spaceId) {
            return false
        }
        return true
    }

    /// Determines if the property should be displayed in the property picker for `target`.
    /// Internal access modifier: uses internal `PropertiesModuleTarget`.
    func shouldDisplayInPicker(propertyId: String, key: String, target: PropertiesModuleTarget, spaceId: String) -> Bool {
        if isInternalProperty(propertyId: propertyId, key: key, spaceId: spaceId) {
            return false
        }
        if TorahNativePropertyDefinition.definition(for: key) != nil {
            return isTargetEligible(target: target, spaceId: spaceId)
        }
        return true
    }

    // MARK: - Manifest Resolution

    public func resolveManifest(spaceId: String) async -> PinkhaSpaceManifest? {
        if let cached = bootstrapService.manifest(forSpaceId: spaceId) {
            return cached
        }
        return try? await bootstrapService.bootstrapSpace(spaceId: spaceId)
    }

    // MARK: - Private Target Inspection

    public func isTargetEligible(target: PropertiesModuleTarget, spaceId: String) -> Bool {
        switch target {
        case .type(let typeData):
            let typeId: String
            switch typeData {
            case .recommendedFeaturedRelations(let t): typeId = t.id
            case .recommendedRelations(let t): typeId = t.id
            }
            return isTargetEligibleForNativeProperties(typeId: typeId, spaceId: spaceId)
        case let .dataview(objectId, _, typeDetails):
            return isDataviewTargetEligible(objectId: objectId, typeDetails: typeDetails, spaceId: spaceId)
        case .object(let objectId):
            let doc = Container.shared.openedDocumentProvider().document(objectId: objectId, spaceId: spaceId)
            guard let details = doc.details, details.spaceId == spaceId, !details.type.isEmpty else { return false }
            return isTargetEligibleForNativeProperties(typeId: details.type, spaceId: spaceId)
        case .library:
            return false
        }
    }

    public func isTargetEligibleAsync(target: PropertiesModuleTarget, spaceId: String) async -> Bool {
        switch target {
        case .type(let typeData):
            let typeId: String
            switch typeData {
            case .recommendedFeaturedRelations(let t): typeId = t.id
            case .recommendedRelations(let t): typeId = t.id
            }
            return await isTargetEligibleForNativePropertiesAsync(typeId: typeId, spaceId: spaceId)
        case let .dataview(objectId, _, typeDetails):
            return await isDataviewTargetEligibleAsync(objectId: objectId, typeDetails: typeDetails, spaceId: spaceId)
        case .object(let objectId):
            let doc = Container.shared.openedDocumentProvider().document(objectId: objectId, spaceId: spaceId)
            if let details = doc.details, details.spaceId == spaceId, !details.type.isEmpty {
                return await isTargetEligibleForNativePropertiesAsync(typeId: details.type, spaceId: spaceId)
            }
            try? await doc.open()
            if let details = doc.details, details.spaceId == spaceId, !details.type.isEmpty {
                return await isTargetEligibleForNativePropertiesAsync(typeId: details.type, spaceId: spaceId)
            }
            return false
        case .library:
            return false
        }
    }

    public func isDataviewEligible(typeDetails: ObjectDetails?, filteredSetOf: [String], spaceId: String) -> Bool {
        if let typeDetails, !typeDetails.id.isEmpty {
            guard typeDetails.spaceId == spaceId else { return false }
            return isTargetEligibleForNativeProperties(typeId: typeDetails.id, spaceId: spaceId)
        }
        let sources = filteredSetOf.filter { !$0.isEmpty }
        guard !sources.isEmpty else { return false }
        for sourceTypeId in sources {
            guard isTargetEligibleForNativeProperties(typeId: sourceTypeId, spaceId: spaceId) else {
                return false
            }
        }
        return true
    }

    func isDataviewTargetEligible(objectId: String, typeDetails: ObjectDetails?, spaceId: String) -> Bool {
        if let typeDetails, !typeDetails.id.isEmpty {
            guard typeDetails.spaceId == spaceId else { return false }
            return isTargetEligibleForNativeProperties(typeId: typeDetails.id, spaceId: spaceId)
        }
        guard !objectId.isEmpty else { return false }
        let setDetails = Container.shared.openedDocumentProvider().document(objectId: objectId, spaceId: spaceId).details
            ?? ObjectDetailsStorage.instance().objectDetails(for: objectId)
        guard let setDetails, setDetails.spaceId == spaceId else { return false }
        return isDataviewEligible(typeDetails: nil, filteredSetOf: setDetails.filteredSetOf, spaceId: spaceId)
    }

    func isDataviewTargetEligibleAsync(objectId: String, typeDetails: ObjectDetails?, spaceId: String) async -> Bool {
        if let typeDetails, !typeDetails.id.isEmpty {
            guard typeDetails.spaceId == spaceId else { return false }
            return await isTargetEligibleForNativePropertiesAsync(typeId: typeDetails.id, spaceId: spaceId)
        }
        guard !objectId.isEmpty else { return false }
        let doc = Container.shared.openedDocumentProvider().document(objectId: objectId, spaceId: spaceId)
        var setDetails = doc.details ?? ObjectDetailsStorage.instance().objectDetails(for: objectId)
        if setDetails == nil {
            try? await doc.open()
            setDetails = doc.details
        }
        guard let setDetails, setDetails.spaceId == spaceId else { return false }
        let sources = setDetails.filteredSetOf.filter { !$0.isEmpty }
        guard !sources.isEmpty else { return false }
        for sourceTypeId in sources {
            guard await isTargetEligibleForNativePropertiesAsync(typeId: sourceTypeId, spaceId: spaceId) else {
                return false
            }
        }
        return true
    }
}
