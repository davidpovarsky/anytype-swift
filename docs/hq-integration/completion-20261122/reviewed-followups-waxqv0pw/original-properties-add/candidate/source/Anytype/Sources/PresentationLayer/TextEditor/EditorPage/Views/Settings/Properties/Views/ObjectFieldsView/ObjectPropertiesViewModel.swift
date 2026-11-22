import Foundation
import Services
import SwiftProtobuf
import UIKit
import AnytypeCore
import SwiftUI
import PinkhaKit

@MainActor
@Observable
final class ObjectPropertiesViewModel {
    var sections = [PropertiesSection]()
    var showConflictingInfo = false
    var expandedSections = Set<String>()
    var typeId: String?
    var relationsSearchData: PropertiesSearchData?

    var canAddProperty: Bool {
        if let scope = originalEditorScope {
            guard let subscriptionID = preparedSubscriptionID,
                  isPreparedSubscriptionCurrent(subscriptionID),
                  let hint = preparedAddHint else { return false }
            // Only a display hint. A tap performs a new canonical read with
            // its own scope; no manifest or identity survives in this state.
            return (try? scope.withCurrent {
                PinkhaRuntime.enabled && hint == preparedPropertyState
            }) == true
        }
        return document.permissions.canEditRelationValues && document.details?.isReadonly == false &&
            PinkhaTorahPropertyPolicy.shared.isNormalDocument(document.details, spaceId: document.spaceId)
    }

    var hasOutput: Bool { output != nil }

    var shouldShowEmptyState: Bool {
        guard let firstSection = sections.first else { return true }
        return firstSection.id != PropertiesSection.Constants.featuredPropertiesSectionId
    }

    // MARK: - Private variables

    private struct PreparedPropertyState: Equatable {
        let details: ObjectDetails?
        let properties: ParsedProperties
        let permissions: ObjectPermissions
    }

    private var preparedAddHint: PreparedPropertyState?
    @ObservationIgnored
    private let document: any BaseDocumentProtocol
    @ObservationIgnored
    private let preparedSession: PreparedEditorPageSession?
    @ObservationIgnored
    private let sectionsBuilder = PropertiesSectionBuilder()
    @ObservationIgnored
    private var latestParsedProperties = ParsedProperties.empty
    @ObservationIgnored
    private var preparedSectionsTask: Task<Void, Never>?
    @ObservationIgnored
    private var preparedSubscriptionID: UUID?
    @ObservationIgnored
    private var preparedSubscriptionTask: Task<Void, Never>?
    @ObservationIgnored
    private var preparedSectionsInput: PreparedPropertyState?
    @ObservationIgnored
    private var preparedAddTask: Task<Void, Never>?
    @ObservationIgnored
    private var preparedAddRequestID: UUID?

    @ObservationIgnored
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol
    @ObservationIgnored
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    @ObservationIgnored
    @Injected(\.documentsProvider)
    private var documentsProvider: any DocumentsProviderProtocol

    @ObservationIgnored
    private weak var output: (any PropertiesListModuleOutput)?
    
    // MARK: - Initializers
    
    init(
        document: some BaseDocumentProtocol,
        output: (any PropertiesListModuleOutput)?,
        preparedSession: PreparedEditorPageSession? = nil
    ) {
        self.document = document
        self.output = output
        self.preparedSession = preparedSession
        self.latestParsedProperties = document.parsedProperties
        self.typeId = Self.resolvedTypeId(for: document.details)
        if preparedSession == nil && document.details != nil {
            rebuildSections(from: document.parsedProperties)
        }
    }

    private var originalEditorScope: OriginalEditorPropertyScope? {
        preparedSession.map {
            OriginalEditorPropertyScope(preparedSession: $0, objectId: document.objectId,
                                        spaceId: document.spaceId, document: document)
        }
    }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withCurrent(operation) }
        return try operation()
    }

    private func requireQualifiedSchemaRoute() throws {
        guard let scope = originalEditorScope else { return }
        try scope.withCurrent { throw EditorDocumentWriteError.rejected(.unqualifiedDispatch) }
    }
    
    func setupSubscriptions() async {
        if let scope = originalEditorScope {
            await setupPreparedSubscriptions(scope: scope)
            return
        }
        guard (try? withCurrentSource {}) != nil else { return }
        if preparedSession == nil && !document.isOpened {
            try? await document.open()
        }
        guard (try? withCurrentSource {
            latestParsedProperties = document.parsedProperties
            rebuildSections(from: document.parsedProperties)
        }) != nil else { return }

        if preparedSession == nil {
            Task { [document] in
                await PinkhaTorahNativePropertyCatalog.shared.ensureSpaceAndTypeReady(
                    spaceId: document.spaceId,
                    typeId: Self.resolvedTypeId(for: document.details)
                )
            }
        }

        NotificationCenter.default.addObserver(
            forName: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self else { return }
            let notifiedSpace = notification.userInfo?["spaceId"] as? String
            if notifiedSpace == nil || notifiedSpace == self.document.spaceId {
                try? self.withCurrentSource {
                    self.latestParsedProperties = self.document.parsedProperties
                    self.rebuildSections(from: self.latestParsedProperties)
                }
            }
        }

        for await properties in document.parsedPropertiesPublisher.values {
            guard (try? withCurrentSource {
                latestParsedProperties = properties
                rebuildSections(from: properties)
            }) != nil else { return }
        }
    }

    private func setupPreparedSubscriptions(scope: OriginalEditorPropertyScope) async {
        guard !Task.isCancelled,
              (try? scope.withCurrent {}) != nil else { return }
        // This identifies only the view subscription, never source authority.
        // A new .task can start before its cancelled predecessor unwinds.
        let subscriptionID = UUID()
        preparedSubscriptionTask?.cancel()
        preparedSectionsTask?.cancel()
        cancelPreparedAdd()
        preparedAddHint = nil
        preparedSectionsInput = nil
        relationsSearchData = nil
        preparedSubscriptionID = subscriptionID
        let subscriptionTask = Task { @MainActor [weak self] in
            guard let self else { return }
            await self.observePreparedUpdates(scope: scope, subscriptionID: subscriptionID)
        }
        // Assignment happens on MainActor before the first await. The handle
        // is this real subscription task, never a source/permission token.
        preparedSubscriptionTask = subscriptionTask
        defer {
            if preparedSubscriptionID == subscriptionID {
                preparedSubscriptionID = nil
                preparedSubscriptionTask = nil
                preparedSectionsTask?.cancel()
                preparedSectionsTask = nil
                preparedSectionsInput = nil
                preparedAddHint = nil
                cancelPreparedAdd()
                relationsSearchData = nil
            }
        }
        await withTaskCancellationHandler {
            await subscriptionTask.value
        } onCancel: {
            // Cancellation is visible to a pending Add even before this
            // outer task resumes its MainActor cleanup.
            subscriptionTask.cancel()
        }
    }

    private func observePreparedUpdates(scope: OriginalEditorPropertyScope, subscriptionID: UUID) async {
        let observer = NotificationCenter.default.addObserver(
            forName: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            let notifiedSpace = notification.userInfo?["spaceId"] as? String
            Task { @MainActor [weak self] in
                guard let self, self.isPreparedSubscriptionCurrent(subscriptionID),
                      notifiedSpace == nil || notifiedSpace?.utf8.elementsEqual(self.document.spaceId.utf8) == true else { return }
                self.schedulePreparedSectionsRebuild(scope: scope, subscriptionID: subscriptionID, force: true)
            }
        }
        defer { NotificationCenter.default.removeObserver(observer) }

        // Start the asynchronous read only after the temporary read admission
        // above has returned; no task inherits a completed scope lease.
        guard schedulePreparedSectionsRebuild(scope: scope, subscriptionID: subscriptionID) else { return }
        for await _ in document.subscibeFor(update: [.relations, .details(id: document.objectId), .permissions]).values {
            guard !Task.isCancelled,
                  schedulePreparedSectionsRebuild(scope: scope, subscriptionID: subscriptionID) else { return }
        }
    }

    private var preparedPropertyState: PreparedPropertyState {
        .init(details: document.details, properties: document.parsedProperties, permissions: document.permissions)
    }

    private func isPreparedSubscriptionCurrent(_ subscriptionID: UUID) -> Bool {
        preparedSubscriptionID == subscriptionID && preparedSubscriptionTask?.isCancelled == false
    }

    private func cancelPreparedAdd() {
        preparedAddTask?.cancel()
        preparedAddTask = nil
        preparedAddRequestID = nil
    }

    @discardableResult
    private func schedulePreparedSectionsRebuild(
        scope: OriginalEditorPropertyScope, subscriptionID: UUID, force: Bool = false
    ) -> Bool {
        guard isPreparedSubscriptionCurrent(subscriptionID) else { return false }
        let input: PreparedPropertyState
        do { input = try scope.withCurrent { preparedPropertyState } }
        catch { return false }
        // The initial/general update or an unrelated document event must not
        // launch a second identical canonical read.
        guard force || preparedSectionsInput != input else { return true }
        preparedSectionsTask?.cancel()
        cancelPreparedAdd()
        preparedAddHint = nil
        preparedSectionsInput = input
        let properties: ParsedProperties
        do {
            properties = try scope.withCurrent {
                latestParsedProperties = document.parsedProperties
                // No internal row is displayed while its current account's
                // canonical identity is unresolved or has been invalidated.
                sections = []
                return document.parsedProperties
            }
        } catch { return false }

        preparedSectionsTask = Task { [weak self] in
            guard let self else { return }
            do {
                try Task.checkCancellation()
                let identity = try await scope.loadModalPropertyIdentity()
                try Task.checkCancellation()
                let current: PreparedPropertyState? = try scope.withCurrent {
                    guard self.isPreparedSubscriptionCurrent(subscriptionID),
                          self.document.parsedProperties == properties else { return nil }
                    let rawSections = self.sectionsBuilder.buildObjectSections(parsedProperties: properties)
                    self.sections = rawSections.compactMap { section in
                        let filtered = section.relations.filter { relation in
                            (try? scope.requireOriginalPropertyValue(
                                propertyId: relation.id, key: relation.key, identity: identity
                            )) != nil
                        }
                        guard !filtered.isEmpty else { return nil }
                        return PropertiesSection(
                            id: section.id, title: section.title, relations: filtered,
                            isMissingFields: section.isMissingFields, isExpandable: section.isExpandable
                        )
                    }
                    self.typeId = Self.resolvedTypeId(for: self.document.details)
                    // Keep the original row behavior: properties are captured
                    // before the read, while details/permissions are live here.
                    let current = self.preparedPropertyState
                    self.preparedSectionsInput = current
                    return current
                }
                guard let current, self.isPreparedSubscriptionCurrent(subscriptionID) else { return }
                // Type classification is another real account-bound read.
                // It does not delay or replace the original row projection.
                let canAdd = try await scope.canAddOriginalProperty(identity: identity)
                try Task.checkCancellation()
                try scope.withCurrent {
                    guard self.isPreparedSubscriptionCurrent(subscriptionID),
                          self.preparedPropertyState == current,
                          PinkhaRuntime.enabled else { return }
                    self.preparedAddHint = canAdd ? current : nil
                }
            } catch {
                // A failed canonical read leaves rows cleared. Missing type
                // identity or a retired source never publishes an Add hint;
                // neither original read bootstraps the Space.
            }
        }
        return true
    }

    private static func resolvedTypeId(for details: ObjectDetails?) -> String? {
        guard let details else { return nil }
        if !details.type.isEmpty {
            return details.type
        }
        let objectTypeId = details.objectType.id
        return objectTypeId.isEmpty ? nil : objectTypeId
    }

    private func rebuildSections(from properties: ParsedProperties) {
        let currentTypeId = Self.resolvedTypeId(for: document.details)
        typeId = currentTypeId
        let isEligible = PinkhaTorahPropertyPolicy.shared.isNormalDocument(document.details, spaceId: document.spaceId)
        let rawSections = sectionsBuilder.buildObjectSections(parsedProperties: properties)
        sections = rawSections.compactMap { section in
            let filtered = section.relations.filter { relation in
                if PinkhaTorahPropertyPolicy.shared.isInternalProperty(
                    propertyId: relation.id, key: relation.key, spaceId: document.spaceId
                ) {
                    return false
                }
                if TorahNativePropertyDefinition.definition(for: relation.key) != nil && !isEligible {
                    return false
                }
                return true
            }
            guard !filtered.isEmpty else { return nil }
            return PropertiesSection(
                id: section.id,
                title: section.title,
                relations: filtered,
                isMissingFields: section.isMissingFields,
                isExpandable: section.isExpandable
            )
        }
    }
    
    func handleTapOnRelation(_ relation: Property) {
        if let scope = originalEditorScope {
            do {
                let coordinator = try scope.withCurrent {
                    try scope.owner.validateDocument(document)
                    guard let preparedSession,
                          let original = output as? PropertiesListCoordinatorViewModel,
                          original.preparedSession === preparedSession,
                          original.document === document,
                          let current = document.parsedProperties.installed.first(where: {
                              $0.key.utf8.elementsEqual(relation.key.utf8)
                          }), current.id.utf8.elementsEqual(relation.id.utf8), current == relation else {
                        throw EditorDocumentWriteError.rejected(.wrongContext)
                    }
                    return original
                }
                // The real coordinator reserves checkbox writes before Task.
                // A read task must not inherit this completed temporary lease.
                coordinator.editRelationValueAction(document: document, relationKey: relation.key)
            } catch { return }
            return
        }
        guard (try? withCurrentSource {}) != nil else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: document.spaceId
        ) else { return }
        if case .checkbox = relation, relation.isEditable, let scope = originalEditorScope {
            try? scope.withActionCallback {
                output?.editRelationValueAction(document: document, relationKey: relation.key)
            }
        } else {
            try? withCurrentSource { output?.editRelationValueAction(document: document, relationKey: relation.key) }
        }
    }
    
    func removeRelation(_ relation: Property) {
        if let scope = originalEditorScope {
            // Reserve this actual UI write before the manifest read or Task.
            scope.schedule(requiredPermissions: OriginalEditorPropertyScope.listPermissions) { [self] in
                let identity = try await scope.loadModalPropertyIdentity()
                let service = try scope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                    guard document.permissions.canEditRelationValues, document.details?.isReadonly == false,
                          relation.canBeRemovedFromObject,
                          let current = document.parsedProperties.installed.first(where: {
                              $0.key.utf8.elementsEqual(relation.key.utf8)
                          }), current.id.utf8.elementsEqual(relation.id.utf8), current == relation else {
                        throw EditorDocumentWriteError.rejected(.wrongContext)
                    }
                    try scope.requireOriginalPropertyValue(propertyId: relation.id, key: relation.key, identity: identity)
                    return try scope.originalProperties(propertiesService)
                }
                try await service.removeProperty(objectId: document.objectId, propertyKey: relation.key)
                try scope.withCurrent {
                    let relationDetails = try propertyDetailsStorage.relationsDetails(key: relation.key, spaceId: document.spaceId)
                    AnytypeAnalytics.instance().logDeleteRelation(format: relationDetails.format, key: relationDetails.analyticsKey, route: .object)
                }
            }
            return
        }
        guard document.permissions.canEditRelationValues, document.details?.isReadonly == false else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: document.spaceId
        ) else { return }
        let operation: @MainActor @Sendable () async throws -> Void = { [self] in
            let service = try originalEditorScope?.originalProperties(propertiesService) ?? propertiesService
            try await service.removeProperty(objectId: document.objectId, propertyKey: relation.key)
            try withCurrentSource {
                let relationDetails = try propertyDetailsStorage.relationsDetails(key: relation.key, spaceId: document.spaceId)
                AnytypeAnalytics.instance().logDeleteRelation(format: relationDetails.format, key: relationDetails.analyticsKey, route: .object)
            }
        }
        if let scope = originalEditorScope {
            scope.schedule(requiredPermissions: OriginalEditorPropertyScope.listPermissions, operation: operation)
        } else { Task { try await operation() } }
    }

    func isObjectAttachedNative(_ relation: Property) -> Bool {
        canAddProperty && TorahNativePropertyDefinition.definition(for: relation.key) != nil &&
            document.details?.stringArrayValue(for: TorahNativePropertyDefinition.attachedPropertiesKey).contains(relation.key) == true
    }
    
    func onEditTap() {
        guard (try? requireQualifiedSchemaRoute()) != nil else { return }
        guard let typeId else { return }
        try? withCurrentSource { output?.showTypeRelationsView(typeId: typeId) }
    }

    func onAddPropertyTap() {
        if let scope = originalEditorScope {
            schedulePreparedAdd(scope: scope)
            return
        }
        guard (try? requireQualifiedSchemaRoute()) != nil else { return }
        guard canAddProperty else { return }
        let properties = document.parsedProperties
        relationsSearchData = PropertiesSearchData(
            objectId: document.objectId, spaceId: document.spaceId,
            excludedRelationsIds: (properties.featuredProperties + properties.sidebarProperties + properties.conflictedProperties + properties.legacyFeaturedProperties).map(\.id),
            hiddenRelationsIds: Set(properties.hiddenProperties.map(\.id)),
            target: .object(objectId: document.objectId),
            onRelationSelect: { _, _ in }
        )
    }

    private func schedulePreparedAdd(scope: OriginalEditorPropertyScope) {
        guard let subscriptionID = preparedSubscriptionID,
              isPreparedSubscriptionCurrent(subscriptionID),
              preparedAddTask == nil, relationsSearchData == nil else { return }
        let input: PreparedPropertyState
        do {
            input = try scope.withCurrent {
                guard PinkhaRuntime.enabled, let hint = preparedAddHint,
                      hint == preparedPropertyState else {
                    throw EditorDocumentWriteError.rejected(.documentChanged)
                }
                return preparedPropertyState
            }
        } catch { return }

        let requestID = UUID()
        preparedAddRequestID = requestID
        // Opening the original modal is a read/presentation operation. Its
        // actual selection/save already reserves the named list write before
        // Task creation. Start this read after the temporary lease returned.
        preparedAddTask = Task { @MainActor [weak self] in
            guard let self else { return }
            defer {
                if self.preparedAddRequestID == requestID {
                    self.preparedAddTask = nil
                    self.preparedAddRequestID = nil
                }
            }
            do {
                try Task.checkCancellation()
                guard self.isPreparedSubscriptionCurrent(subscriptionID),
                      self.preparedAddRequestID == requestID else { return }
                let identity = try await scope.loadModalPropertyIdentity()
                try Task.checkCancellation()
                guard self.isPreparedSubscriptionCurrent(subscriptionID),
                      self.preparedAddRequestID == requestID,
                      self.preparedPropertyState == input else { return }
                let canAdd = try await scope.canAddOriginalProperty(identity: identity)
                try Task.checkCancellation()
                let data = try scope.withCurrent {
                    guard self.isPreparedSubscriptionCurrent(subscriptionID),
                          self.preparedAddRequestID == requestID,
                          self.relationsSearchData == nil,
                          self.preparedPropertyState == input,
                          PinkhaRuntime.enabled, canAdd else {
                        throw EditorDocumentWriteError.rejected(.documentChanged)
                    }
                    let properties = self.document.parsedProperties
                    return PropertiesSearchData(
                        objectId: self.document.objectId, spaceId: self.document.spaceId,
                        excludedRelationsIds: (properties.featuredProperties + properties.sidebarProperties + properties.conflictedProperties + properties.legacyFeaturedProperties).map(\.id),
                        hiddenRelationsIds: Set(properties.hiddenProperties.map(\.id)),
                        target: .object(objectId: self.document.objectId),
                        originalEditorScope: scope,
                        onRelationSelect: { _, _ in }
                    )
                }
                // SwiftUI's modal work must not inherit the finished read
                // lease. There is no await between validation and publication.
                guard !Task.isCancelled, self.isPreparedSubscriptionCurrent(subscriptionID),
                      self.preparedAddRequestID == requestID else { return }
                self.relationsSearchData = data
            } catch {
                // Missing current identity, changed input, cancellation or a
                // retired source leaves the original modal closed.
            }
        }
    }
    
    func addRelationToType(_ relation: Property) {
        guard (try? requireQualifiedSchemaRoute()) != nil else { return }
        guard let details = document.details else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: details.spaceId
        ) else { return }
        if TorahNativePropertyDefinition.definition(for: relation.key) != nil {
            guard PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(typeId: details.objectType.id, spaceId: details.spaceId) else { return }
        }

        AnytypeAnalytics.instance().logAddConflictRelation()
        
        Task {
            guard let relationsDetail = await PinkhaTorahNativePropertyCatalog.shared.resolvePropertyDetails(
                id: relation.id,
                key: relation.key,
                from: propertyDetailsStorage,
                spaceId: details.spaceId
            ) else { return }
            try await propertiesService.addTypeRecommendedProperty(type: details.objectType, property: relationsDetail)
        }
    }

    func revealHiddenRelation(_ relation: Property) {
        guard (try? requireQualifiedSchemaRoute()) != nil else { return }
        guard let details = document.details else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: details.spaceId
        ) else { return }
        if TorahNativePropertyDefinition.definition(for: relation.key) != nil {
            guard PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(typeId: details.objectType.id, spaceId: details.spaceId) else { return }
        }

        Task {
            guard let relationsDetail = await PinkhaTorahNativePropertyCatalog.shared.resolvePropertyDetails(
                id: relation.id,
                key: relation.key,
                from: propertyDetailsStorage,
                spaceId: details.spaceId
            ) else { return }
            try await propertiesService.revealTypeHiddenProperty(type: details.objectType, property: relationsDetail)
        }
    }
    
    func onConflictingInfoTap() {
        try? withCurrentSource {
            AnytypeAnalytics.instance().logConflictFieldHelp()
            showConflictingInfo.toggle()
        }
    }
    
    func toggleSectionExpansion(_ sectionId: String) {
        try? withCurrentSource {
            withAnimation(.fastSpring) {
                if expandedSections.contains(sectionId) {
                    expandedSections.remove(sectionId)
                } else {
                    expandedSections.insert(sectionId)
                }
            }
        }
    }
    
    func isSectionExpanded(_ sectionId: String) -> Bool {
        expandedSections.contains(sectionId)
    }
}
