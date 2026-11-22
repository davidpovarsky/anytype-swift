import Foundation
import Services
import AnytypeCore

enum PropertiesInteractorError: Error {
    case documentRequired
}

protocol PropertiesInteractorProtocol: Sendable {
    func createProperty(spaceId: String, relation: PropertyDetails) async throws -> PropertyDetails
    func updateProperty(spaceId: String, relation: PropertyDetails) async throws
    func addPropertyToType(relation: PropertyDetails, isFeatured: Bool) async throws
    func addPropertyToDataview(objectId: String, relation: PropertyDetails, activeViewId: String, typeDetails: ObjectDetails?) async throws
    func addPropertyToObject(objectId: String, relation: PropertyDetails) async throws
}

final class PropertiesInteractor: PropertiesInteractorProtocol, Sendable {
    
    private let propertiesService: any PropertiesServiceProtocol = Container.shared.propertiesService()
    private let dataviewService: any DataviewServiceProtocol = Container.shared.dataviewService()
    private let propertyDetailsStorage: any PropertyDetailsStorageProtocol = Container.shared.propertyDetailsStorage()
    
    private let document: (any BaseDocumentProtocol)?
    let originalEditorScope: OriginalEditorPropertyScope?
    
    init(objectId: String?, spaceId: String, originalEditorScope: OriginalEditorPropertyScope? = nil) {
        self.originalEditorScope = originalEditorScope
        if originalEditorScope != nil {
            // objectId is historically a type ID on the slash route. The
            // scope retains the actual target; never fetch a type as its proxy.
            document = nil
        } else if let objectId = objectId, objectId.isNotEmpty {
            let documentsProvider = Container.shared.openedDocumentProvider()
            document = documentsProvider.document(objectId: objectId, spaceId: spaceId)
        } else {
            document = nil
        }
    }
    
    func createProperty(spaceId: String, relation: PropertyDetails) async throws -> PropertyDetails {
        if let scope = originalEditorScope {
            let identity = try await scope.loadModalPropertyIdentity()
            try await scope.requireNewModalProperty(relation, spaceId: spaceId, identity: identity)
            let original = try await scope.originalProperties(propertiesService)
            let created = try await scope.owner.performMutation(
                spaceId: spaceId, requiredPermissions: OriginalEditorPropertyScope.listPermissions
            ) {
                try await original.createProperty(spaceId: spaceId, propertyDetails: relation)
            }
            // The actual native result supplies identity. A rejection after
            // creation is a partial outcome; this does not delete or roll back.
            try await scope.requireModalProperty(created, identity: identity)
            return created
        }
        return try await propertiesService.createProperty(spaceId: spaceId, propertyDetails: relation)
    }
    
    func updateProperty(spaceId: String, relation: PropertyDetails) async throws {
        if originalEditorScope != nil {
            _ = try await updateOriginalProperty(spaceId: spaceId, relation: relation)
            return
        }
        try await propertiesService.updateProperty(objectId: relation.id, fields: relation.fields)
    }

    /// Return metadata read from the retained original property document after
    /// the real update/event delivery, not a fabricated replacement row.
    func updateOriginalProperty(spaceId: String, relation: PropertyDetails) async throws -> PropertyDetails {
        guard let scope = originalEditorScope else {
            throw OriginalEditorPropertyModalError.unsupportedOriginalDelegate
        }
        try await scope.withCurrent {
            guard scope.spaceId.utf8.elementsEqual(spaceId.utf8) else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
        }
        let original = try await scope.originalProperties(propertiesService)
        return try await scope.withSelectedModalProperty(id: relation.id, requiredPermissions: [.editDetails]) { child, actual, identity in
            guard relation.id.utf8.elementsEqual(actual.id.utf8),
                  relation.key.isEmpty || relation.key.utf8.elementsEqual(actual.key.utf8),
                  relation.spaceId.isEmpty || relation.spaceId.utf8.elementsEqual(actual.spaceId.utf8),
                  !relation.name.isEmpty, relation.format == actual.format,
                  relation.objectTypes.count == actual.objectTypes.count,
                  zip(relation.objectTypes, actual.objectTypes).allSatisfy({ pair in pair.0.utf8.elementsEqual(pair.1.utf8) }) else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
            try await original.updateProperty(objectId: actual.id, fields: relation.fields)
            let updated = try OriginalEditorPropertyScope.modalPropertySnapshot(
                child: child, id: actual.id, identity: identity, requiredPermissions: [.editDetails]
            )
            guard updated.key.utf8.elementsEqual(actual.key.utf8),
                  updated.name.utf8.elementsEqual(relation.name.utf8), updated.format == actual.format else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
            return updated
        }
    }
    
    func addPropertyToType(relation: PropertyDetails, isFeatured: Bool) async throws {
        guard originalEditorScope == nil else { throw OriginalEditorPropertyModalError.unsupportedTarget }
        guard let document = document else { 
            throw PropertiesInteractorError.documentRequired 
        }
        guard let details = document.details else { return }
        
        if isFeatured {
            try await propertiesService.addTypeFeaturedRecommendedProperty(details: details, property: relation)
        } else {
            try await propertiesService.addTypeRecommendedProperty(details: details, property: relation)
        }
    }
    
    func addPropertyToDataview(objectId: String, relation: PropertyDetails, activeViewId: String, typeDetails: ObjectDetails?) async throws {
        guard originalEditorScope == nil else { throw OriginalEditorPropertyModalError.unsupportedTarget }
        if let typeDetails {
            try await addPropertyToType(relation: relation, details: typeDetails)
        } else {
            try await dataviewService.addRelation(objectId: objectId, blockId: SetConstants.dataviewBlockId, relationDetails: relation)
        }

        let newOption = DataviewRelationOption(key: relation.key, isVisible: true)
        try await dataviewService.addViewRelation(objectId: objectId, blockId: SetConstants.dataviewBlockId, relation: newOption.asMiddleware, viewId: activeViewId)
    }
    
    private func addPropertyToType(relation: PropertyDetails, details: ObjectDetails) async throws {
        try await propertiesService.addTypeRecommendedProperty(details: details, property: relation)
    }
    
    func addPropertyToObject(objectId: String, relation: PropertyDetails) async throws {
        if let scope = originalEditorScope {
            try await scope.requireModalTarget(.object(objectId: objectId), spaceId: scope.spaceId)
            let identity = try await scope.loadModalPropertyIdentity()
            try await scope.requireModalProperty(relation, identity: identity)
            let original = try await scope.originalProperties(propertiesService)
            return try await scope.perform(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                try await original.addProperties(objectId: objectId, propertiesDetails: [relation])
            }
        }
        try await propertiesService.addProperties(objectId: objectId, propertiesDetails: [relation])
    }
}
