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
    }
    
    func setupSubscriptions() async {
        NotificationCenter.default.addObserver(
            forName: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self else { return }
            let notificationSpaceId = notification.userInfo?["spaceId"] as? String
            if notificationSpaceId == nil || notificationSpaceId == self.document.spaceId {
                let newRows = self.fieldsDataBuilder.build(
                    relations: self.filterProperties(self.parsedProperties.sidebarProperties),
                    featured: self.filterProperties(self.parsedProperties.featuredProperties),
                    hidden: self.filterProperties(self.parsedProperties.hiddenProperties)
                )
                withAnimation {
                    self.relationRows = newRows
                }
            }
        }

        async let relationsSubscription: () = setupRelationsSubscription()
        async let permissionSubscription: () = setupPermissionSubscription()
        async let detailsSubscription: () = setupDetailsSubscription()
        
        (_, _, _) = await (relationsSubscription, permissionSubscription, detailsSubscription)
    }
    
    private func filterProperties(_ properties: [Property]) -> [Property] {
        properties.filter {
            !PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(propertyId: $0.id, key: $0.key, spaceId: document.spaceId)
        }
    }

    private func setupRelationsSubscription() async {
        for await properties in document.parsedPropertiesPublisherForType.values {
            parsedProperties = properties
            let newRows = fieldsDataBuilder.build(
                relations: filterProperties(properties.sidebarProperties),
                featured: filterProperties(properties.featuredProperties),
                hidden: filterProperties(properties.hiddenProperties)
            )
            
            // do not animate on 1st appearance
            withAnimation(relationRows.isNotEmpty ? .default : nil) {
                relationRows = newRows
            }
            
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
        
        guard !PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(
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
        
        relationsSearchData = PropertiesSearchData(
            objectId: document.objectId,
            spaceId: document.spaceId,
            excludedRelationsIds: relationRows.compactMap(\.relationId),
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
    
    func onRelationRemove(_ row: TypePropertiesRelationRow) {
        guard let details = document.details else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(
            propertyId: row.relation.id, key: row.relation.key, spaceId: document.spaceId
        ) else { return }

        let isNative = TorahNativePropertyDefinition.definition(for: row.relation.key) != nil
        let isEligibleType = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
            typeId: details.id, spaceId: document.spaceId
        )
        guard !(isNative && isEligibleType) else { return }

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
        let releationKeys = try await propertiesService.getConflictPropertiesForType(typeId: document.objectId, spaceId: document.spaceId)
        conflictRelations = propertyDetailsStorage
            .relationsDetails(ids: releationKeys, spaceId: document.spaceId)
            .filter {
                !$0.isHidden &&
                !$0.isDeleted &&
                !PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(propertyId: $0.id, key: $0.key, spaceId: document.spaceId)
            }
        
        let newRows = fieldsDataBuilder.build(
            relations: filterProperties(parsedProperties.sidebarProperties),
            featured: filterProperties(parsedProperties.featuredProperties),
            hidden: filterProperties(parsedProperties.hiddenProperties)
        )
        
        // do not animate on 1st appearance
        withAnimation(relationRows.isNotEmpty ? .default : nil) {
            relationRows = newRows
        }
    }
}
