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
        document.permissions.canEditRelationValues && document.details?.isReadonly == false &&
            PinkhaTorahPropertyPolicy.shared.isNormalDocument(document.details, spaceId: document.spaceId)
    }

    var hasOutput: Bool { output != nil }

    var shouldShowEmptyState: Bool {
        guard let firstSection = sections.first else { return true }
        return firstSection.id != PropertiesSection.Constants.featuredPropertiesSectionId
    }

    // MARK: - Private variables

    @ObservationIgnored
    private let document: any BaseDocumentProtocol
    @ObservationIgnored
    private let preparedSession: PreparedEditorPageSession?
    @ObservationIgnored
    private let sectionsBuilder = PropertiesSectionBuilder()
    @ObservationIgnored
    private var latestParsedProperties = ParsedProperties.empty

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
        if document.details != nil {
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
