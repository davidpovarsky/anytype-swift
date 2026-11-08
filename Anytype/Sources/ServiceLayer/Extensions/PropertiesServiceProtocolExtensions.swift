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
    }
    
    func addTypeRecommendedProperty(details: ObjectDetails, property: PropertyDetails) async throws {
        try await addTypeRecommendedProperty(type: ObjectType(details: details), property: property)
    }
    
    func addTypeRecommendedProperty(type: ObjectType, property: PropertyDetails) async throws {
        var recommendedPropertiesDetails = type.recommendedRelationsDetails.filter { $0.id != property.id }
        recommendedPropertiesDetails.insert(property, at: 0)
        let recommendedFeaturedPropertiesDetails = type.recommendedFeaturedRelationsDetails.filter { $0.id != property.id }
        let recommendedHiddenPropertiesDetails = type.recommendedHiddenRelationsDetails.filter { $0.id != property.id }
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
        let recommendedPropertiesDetails = type.recommendedRelationsDetails.filter { $0.id != property.id }
        var recommendedFeaturedPropertiesDetails = type.recommendedFeaturedRelationsDetails.filter { $0.id != property.id }
        recommendedFeaturedPropertiesDetails.insert(property, at: 0)
        let recommendedHiddenPropertiesDetails = type.recommendedHiddenRelationsDetails.filter { $0.id != property.id }
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
        let recommendedPropertiesDetails = type.recommendedRelationsDetails.filter { $0.id != property.id }
        let recommendedFeaturedPropertiesDetails = type.recommendedFeaturedRelationsDetails.filter { $0.id != property.id }
        var recommendedHiddenPropertiesDetails = type.recommendedHiddenRelationsDetails.filter { $0.id != property.id }
        recommendedHiddenPropertiesDetails.insert(property, at: 0)
        try await updateTypeProperties(
            typeId: type.id,
            recommendedProperties: recommendedPropertiesDetails,
            recommendedFeaturedProperties: recommendedFeaturedPropertiesDetails,
            recommendedHiddenProperties: recommendedHiddenPropertiesDetails
        )
    }
        
    func removeTypeProperty(details: ObjectDetails, propertyId: String) async throws {
        let recommendedProperties = details.recommendedRelationsDetails.filter({ propertyId != $0.id })
        let recommendedFeaturedProperties = details.recommendedFeaturedRelationsDetails.filter({ propertyId != $0.id })
        let recommendedHiddenProperties = details.recommendedHiddenRelationsDetails.filter({ propertyId != $0.id })
        try await updateTypeProperties(
            typeId: details.id,
            recommendedProperties: recommendedProperties,
            recommendedFeaturedProperties: recommendedFeaturedProperties,
            recommendedHiddenProperties: recommendedHiddenProperties
        )
    }
}
