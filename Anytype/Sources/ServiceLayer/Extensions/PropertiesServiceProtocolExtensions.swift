import Services

extension PropertiesServiceProtocol {
    func updateTypeProperties(
        typeId: String,
        recommendedProperties: [PropertyDetails],
        recommendedFeaturedProperties: [PropertyDetails],
        recommendedHiddenProperties: [PropertyDetails]
    ) async throws {
        try await updateTypeProperties(
            typeId: typeId,
            dataviewId: SetConstants.dataviewBlockId,
            recommendedProperties: recommendedProperties,
            recommendedFeaturedProperties: recommendedFeaturedProperties,
            recommendedHiddenProperties: recommendedHiddenProperties
        )
        let spaceId = recommendedProperties.first?.spaceId
            ?? recommendedFeaturedProperties.first?.spaceId
            ?? recommendedHiddenProperties.first?.spaceId
            ?? (try? Container.shared.objectTypeProvider().objectType(id: typeId).spaceId)
            ?? ""
        if !spaceId.isEmpty {
            PinkhaTorahNativePropertyCatalog.shared.recordUpdatedTypeRelations(
                typeId: typeId,
                spaceId: spaceId,
                recommendedIds: recommendedProperties.map(\.id),
                featuredIds: recommendedFeaturedProperties.map(\.id),
                hiddenIds: recommendedHiddenProperties.map(\.id)
            )
        }
    }
    
    func addTypeRecommendedProperty(details: ObjectDetails, property: PropertyDetails) async throws {
        try await addTypeRecommendedProperty(type: ObjectType(details: details), property: property)
    }
    
    func addTypeRecommendedProperty(type: ObjectType, property: PropertyDetails) async throws {
        let current = await PinkhaTorahNativePropertyCatalog.shared.resolveCurrentTypeProperties(
            typeId: type.id,
            spaceId: type.spaceId.isEmpty ? property.spaceId : type.spaceId,
            fallbackRecommendedIds: type.recommendedRelations,
            fallbackFeaturedIds: type.recommendedFeaturedRelations,
            fallbackHiddenIds: type.recommendedHiddenRelations,
            fallbackRecommendedDetails: type.recommendedRelationsDetails,
            fallbackFeaturedDetails: type.recommendedFeaturedRelationsDetails,
            fallbackHiddenDetails: type.recommendedHiddenRelationsDetails
        )
        var recommendedPropertiesDetails = current.recommended.filter { $0.id != property.id }
        recommendedPropertiesDetails.insert(property, at: 0)
        let recommendedFeaturedPropertiesDetails = current.featured.filter { $0.id != property.id }
        let recommendedHiddenPropertiesDetails = current.hidden.filter { $0.id != property.id }
        try await updateTypeProperties(
            typeId: type.id,
            recommendedProperties: recommendedPropertiesDetails,
            recommendedFeaturedProperties: recommendedFeaturedPropertiesDetails,
            recommendedHiddenProperties: recommendedHiddenPropertiesDetails
        )
    }
    
    func addTypeFeaturedRecommendedProperty(details: ObjectDetails, property: PropertyDetails) async throws {
        try await addTypeFeaturedRecommendedProperty(type: ObjectType(details: details), property: property)
    }
    
    func addTypeFeaturedRecommendedProperty(type: ObjectType, property: PropertyDetails) async throws {
        let current = await PinkhaTorahNativePropertyCatalog.shared.resolveCurrentTypeProperties(
            typeId: type.id,
            spaceId: type.spaceId.isEmpty ? property.spaceId : type.spaceId,
            fallbackRecommendedIds: type.recommendedRelations,
            fallbackFeaturedIds: type.recommendedFeaturedRelations,
            fallbackHiddenIds: type.recommendedHiddenRelations,
            fallbackRecommendedDetails: type.recommendedRelationsDetails,
            fallbackFeaturedDetails: type.recommendedFeaturedRelationsDetails,
            fallbackHiddenDetails: type.recommendedHiddenRelationsDetails
        )
        let recommendedPropertiesDetails = current.recommended.filter { $0.id != property.id }
        var recommendedFeaturedPropertiesDetails = current.featured.filter { $0.id != property.id }
        recommendedFeaturedPropertiesDetails.insert(property, at: 0)
        let recommendedHiddenPropertiesDetails = current.hidden.filter { $0.id != property.id }
        try await updateTypeProperties(
            typeId: type.id,
            recommendedProperties: recommendedPropertiesDetails,
            recommendedFeaturedProperties: recommendedFeaturedPropertiesDetails,
            recommendedHiddenProperties: recommendedHiddenPropertiesDetails
        )
    }

    func revealTypeHiddenProperty(type: ObjectType, property: PropertyDetails, featured: Bool = false) async throws {
        if featured {
            try await addTypeFeaturedRecommendedProperty(type: type, property: property)
        } else {
            try await addTypeRecommendedProperty(type: type, property: property)
        }
    }

    func hideTypeProperty(type: ObjectType, property: PropertyDetails) async throws {
        let current = await PinkhaTorahNativePropertyCatalog.shared.resolveCurrentTypeProperties(
            typeId: type.id,
            spaceId: type.spaceId.isEmpty ? property.spaceId : type.spaceId,
            fallbackRecommendedIds: type.recommendedRelations,
            fallbackFeaturedIds: type.recommendedFeaturedRelations,
            fallbackHiddenIds: type.recommendedHiddenRelations,
            fallbackRecommendedDetails: type.recommendedRelationsDetails,
            fallbackFeaturedDetails: type.recommendedFeaturedRelationsDetails,
            fallbackHiddenDetails: type.recommendedHiddenRelationsDetails
        )
        let recommendedPropertiesDetails = current.recommended.filter { $0.id != property.id }
        let recommendedFeaturedPropertiesDetails = current.featured.filter { $0.id != property.id }
        var recommendedHiddenPropertiesDetails = current.hidden.filter { $0.id != property.id }
        recommendedHiddenPropertiesDetails.insert(property, at: 0)
        try await updateTypeProperties(
            typeId: type.id,
            recommendedProperties: recommendedPropertiesDetails,
            recommendedFeaturedProperties: recommendedFeaturedPropertiesDetails,
            recommendedHiddenProperties: recommendedHiddenPropertiesDetails
        )
    }
        
    func removeTypeProperty(details: ObjectDetails, propertyId: String) async throws {
        let current = await PinkhaTorahNativePropertyCatalog.shared.resolveCurrentTypeProperties(
            typeId: details.id,
            spaceId: details.spaceId,
            fallbackRecommendedIds: details.recommendedRelations,
            fallbackFeaturedIds: details.recommendedFeaturedRelations,
            fallbackHiddenIds: details.recommendedHiddenRelations,
            fallbackRecommendedDetails: details.recommendedRelationsDetails,
            fallbackFeaturedDetails: details.recommendedFeaturedRelationsDetails,
            fallbackHiddenDetails: details.recommendedHiddenRelationsDetails
        )
        let recommendedProperties = current.recommended.filter({ propertyId != $0.id })
        let recommendedFeaturedProperties = current.featured.filter({ propertyId != $0.id })
        let recommendedHiddenProperties = current.hidden.filter({ propertyId != $0.id })
        try await updateTypeProperties(
            typeId: details.id,
            recommendedProperties: recommendedProperties,
            recommendedFeaturedProperties: recommendedFeaturedProperties,
            recommendedHiddenProperties: recommendedHiddenProperties
        )
        if !current.resolvedSpaceId.isEmpty {
            PinkhaTorahNativePropertyCatalog.shared.recordUpdatedTypeRelations(
                typeId: details.id,
                spaceId: current.resolvedSpaceId,
                recommendedIds: recommendedProperties.map(\.id),
                featuredIds: recommendedFeaturedProperties.map(\.id),
                hiddenIds: recommendedHiddenProperties.map(\.id)
            )
        }
    }
}
