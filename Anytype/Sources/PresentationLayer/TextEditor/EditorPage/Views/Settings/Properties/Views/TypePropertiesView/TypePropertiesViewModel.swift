import Foundation
import Services
import SwiftProtobuf
import AnytypeCore
import SwiftUI
import PinkhaKit


@MainActor
@Observable
final class TypePropertiesViewModel {

    var canEditPropertiesList = false
    var showConflictingInfo = false
    var relationRows = [TypePropertiesRow]()
    var relationsSearchData: PropertiesSearchData?
    var propertyData: PropertyInfoData?
    var conflictRelations = [PropertyDetails]()

    // MARK: - Private variables

    let document: any BaseDocumentProtocol
    @ObservationIgnored
    private let fieldsDataBuilder = TypePropertiesRowBuilder()
    @ObservationIgnored
    private let moveHandler = TypePropertiesMoveHandler()

    @ObservationIgnored
    private var parsedProperties = ParsedProperties.empty

    @ObservationIgnored @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol
    @ObservationIgnored @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    @ObservationIgnored @Injected(\.singlePropertyBuilder)
    private var relationsBuilder: any SinglePropertyBuilderProtocol
    
    
    // MARK: - Initializers
    
    convenience init(data: EditorTypeObject) {
        let document = Container.shared.openedDocumentProvider().document(objectId: data.objectId, spaceId: data.spaceId)
        self.init(document: document)
    }
    
    init(document: some BaseDocumentProtocol) {
        self.document = document
        if document.details != nil {
            rebuildTypeProperties(animate: false)
        }
    }
    
    func setupSubscriptions() async {
        if !document.isOpened {
            try? await document.open()
        }
        rebuildTypeProperties(animate: false)

        Task { [document] in
            await PinkhaTorahNativePropertyCatalog.shared.ensureSpaceAndTypeReady(
                spaceId: document.spaceId,
                typeId: document.objectId
            )
        }

        NotificationCenter.default.addObserver(
            forName: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self else { return }
            let notificationSpaceId = notification.userInfo?["spaceId"] as? String
            if notificationSpaceId == nil || notificationSpaceId == self.document.spaceId {
                self.rebuildTypeProperties(animate: self.relationRows.isNotEmpty)
            }
        }

        async let relationsSubscription: () = setupRelationsSubscription()
        async let permissionSubscription: () = setupPermissionSubscription()
        async let detailsSubscription: () = setupDetailsSubscription()
        
        (_, _, _) = await (relationsSubscription, permissionSubscription, detailsSubscription)
    }

    private func rebuildTypeProperties(fallback: ParsedProperties? = nil, animate: Bool = true) {
        let catalogBuilt = PinkhaTorahNativePropertyCatalog.shared.buildParsedPropertiesForType(document: document)
        let effective: ParsedProperties
        if !catalogBuilt.installed.isEmpty {
            effective = catalogBuilt
        } else if let fallback, !fallback.installed.isEmpty {
            effective = fallback
        } else {
            effective = catalogBuilt
        }
        parsedProperties = effective
        let newRows = fieldsDataBuilder.build(
            relations: filterProperties(effective.sidebarProperties),
            featured: filterProperties(effective.featuredProperties),
            hidden: filterProperties(effective.hiddenProperties)
        )
        withAnimation(animate && relationRows.isNotEmpty ? .default : nil) {
            relationRows = newRows
        }
    }
    
    private func filterProperties(_ properties: [Property]) -> [Property] {
        let isEligibleType = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
            typeId: document.objectId, spaceId: document.spaceId
        )
        return properties.filter {
            if PinkhaTorahPropertyPolicy.shared.isInternalProperty(propertyId: $0.id, key: $0.key, spaceId: document.spaceId) {
                return false
            }
            if TorahNativePropertyDefinition.definition(for: $0.key) != nil && !isEligibleType {
                return false
            }
            return true
        }
    }

    func isRelationHidden(_ row: TypePropertiesRelationRow) -> Bool {
        parsedProperties.hiddenProperties.contains { $0.id == row.relation.id }
    }

    func canInspectRelation(_ row: TypePropertiesRelationRow) -> Bool {
        guard canEditPropertiesList else { return false }
        if TorahNativePropertyDefinition.definition(for: row.relation.key) != nil {
            return true
        }
        return row.relation.isEditable
    }

    func canRemoveRelation(_ row: TypePropertiesRelationRow) -> Bool {
        guard canEditPropertiesList else { return false }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: row.relation.id, key: row.relation.key, spaceId: document.spaceId
        ) else { return false }
        let isNative = TorahNativePropertyDefinition.definition(for: row.relation.key) != nil
        let isEligibleType = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
            typeId: document.objectId, spaceId: document.spaceId
        )
        return !(isNative && isEligibleType)
    }

    private func setupRelationsSubscription() async {
        for await properties in document.parsedPropertiesPublisherForType.values {
            rebuildTypeProperties(fallback: properties, animate: relationRows.isNotEmpty)
        }
    }
    
    private func setupPermissionSubscription() async {
        for await permissions in document.permissionsPublisher.values {
            canEditPropertiesList = permissions.canEditPropertiesList
        }
    }
    
    func setupDetailsSubscription() async {
        for await details in document.detailsPublisher.values {
            try? await updateConflictRelations(details: details)
        }
    }
    
    func onRelationTap(_ data: TypePropertiesRelationRow) {
        guard let details = document.details else { return }
        guard let format = data.relation.format else { return }
        
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: data.relation.id, key: data.relation.key, spaceId: document.spaceId
        ) else { return }

        let isNative = TorahNativePropertyDefinition.definition(for: data.relation.key) != nil
        let type = ObjectType(details: details)
        
        let typeData: PropertiesModuleTypeData = data.relation.isFeatured ? .recommendedFeaturedRelations(type) : .recommendedRelations(type)
        
        propertyData = PropertyInfoData(
            name: data.relation.name,
            objectId: document.objectId,
            spaceId: document.spaceId,
            target: .type(typeData),
            mode: .edit(relationId: data.relation.id, format: format, limitedObjectTypes: data.relation.limitedObjectTypes),
            isReadOnly: isNative || !data.relation.isEditable
        )
    }
    
    func onAddRelationTap(section: TypePropertiesSectionRow) {
        guard let details = document.details else { return }
        let type = ObjectType(details: details)
        let typeData: PropertiesModuleTypeData = section.isFeatured ? .recommendedFeaturedRelations(type) : .recommendedRelations(type)
        let visibleRelationIds = (filterProperties(parsedProperties.featuredProperties) + filterProperties(parsedProperties.sidebarProperties)).map(\.id)
        let hiddenIds = Set(filterProperties(parsedProperties.hiddenProperties).map(\.id))
        
        relationsSearchData = PropertiesSearchData(
            objectId: document.objectId,
            spaceId: document.spaceId,
            excludedRelationsIds: visibleRelationIds,
            hiddenRelationsIds: hiddenIds,
            target: .type(typeData),
            onRelationSelect: { details, isNew in
                AnytypeAnalytics.instance().logAddExistingOrCreateRelation(
                    format: details.format, isNew: isNew, type: .type, key: details.analyticsKey
                )
            }
        )
    }
    
    func onConflictingInfoTap() {
        AnytypeAnalytics.instance().logConflictFieldHelp()
        showConflictingInfo.toggle()
    }

    func onRelationReveal(_ row: TypePropertiesRelationRow, featured: Bool = false) {
        guard let details = document.details else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: row.relation.id, key: row.relation.key, spaceId: document.spaceId
        ) else { return }
        let type = ObjectType(details: details)
        Task {
            guard let relationDetails = await PinkhaTorahNativePropertyCatalog.shared.resolvePropertyDetails(
                id: row.relation.id,
                key: row.relation.key,
                from: propertyDetailsStorage,
                spaceId: document.spaceId
            ) else {
                return
            }
            try? await propertiesService.revealTypeHiddenProperty(type: type, property: relationDetails, featured: featured)
        }
    }

    func onRelationHide(_ row: TypePropertiesRelationRow) {
        guard let details = document.details else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: row.relation.id, key: row.relation.key, spaceId: document.spaceId
        ) else { return }
        let type = ObjectType(details: details)
        Task {
            guard let relationDetails = await PinkhaTorahNativePropertyCatalog.shared.resolvePropertyDetails(
                id: row.relation.id,
                key: row.relation.key,
                from: propertyDetailsStorage,
                spaceId: document.spaceId
            ) else {
                return
            }
            try? await propertiesService.hideTypeProperty(type: type, property: relationDetails)
        }
    }

    func onRelationRemove(_ row: TypePropertiesRelationRow) {
        guard let details = document.details else { return }
        guard canRemoveRelation(row) else { return }

        Task {
            try await propertiesService.removeTypeProperty(details: details, propertyId: row.relation.id)
            
            guard let format = row.relation.format?.format else {
                anytypeAssertionFailure("Empty relation format for onRelationRemove")
                return
            }
            AnytypeAnalytics.instance().logDeleteRelation(format: format, route: .type)
        }
    }
    
    func onAddConflictRelation(_ relation: PropertyDetails) {
        guard let details = document.details else { return }
        let type = ObjectType(details: details)
        let target = PropertiesModuleTarget.type(.recommendedRelations(type))
        guard PinkhaTorahPropertyPolicy.shared.canAddProperty(
            propertyId: relation.id, key: relation.key, target: target, spaceId: document.spaceId
        ) else { return }

        AnytypeAnalytics.instance().logAddConflictRelation()
        
        Task {
            try await propertiesService.addTypeRecommendedProperty(details: details, property: relation)    
            if let details = document.details { try await updateConflictRelations(details: details) }
        }
    }
    
    private func updateConflictRelations(details: ObjectDetails) async throws {
        let isEligibleType = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
            typeId: document.objectId, spaceId: document.spaceId
        )
        let releationKeys = try await propertiesService.getConflictPropertiesForType(typeId: document.objectId, spaceId: document.spaceId)
        conflictRelations = propertyDetailsStorage
            .relationsDetails(ids: releationKeys, spaceId: document.spaceId)
            .filter {
                !$0.isHidden &&
                !$0.isDeleted &&
                !PinkhaTorahPropertyPolicy.shared.isInternalProperty(propertyId: $0.id, key: $0.key, spaceId: document.spaceId) &&
                (TorahNativePropertyDefinition.definition(for: $0.key) == nil || isEligibleType)
            }
        
        rebuildTypeProperties(animate: relationRows.isNotEmpty)
    }
}
