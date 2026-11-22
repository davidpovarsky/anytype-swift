import ProtobufMessages
import SwiftProtobuf
import AnytypeCore

public protocol TemplatesServiceProtocol: Sendable {
    func cloneTemplate(blockId: String) async throws
    func createTemplateFromObjectType(objectTypeId: String, spaceId: String) async throws -> String
    func createTemplateFromObject(objectId: String) async throws -> String
    func deleteTemplate(templateId: String) async throws
    func setTemplateAsDefaultForType(objectTypeId: String, templateId: String) async throws
}

public enum OriginalTemplatesServiceBindingError: Error, Sendable {
    case unsupportedOriginalDelegate
    case invalidSpace
    case wrongReturnedObject
    case wrongReturnedSpace
    case wrongObjectKind
    case wrongTemplateTarget
}

/// The concrete original implementation remains internal to Services. This
/// narrow factory admits only that implementation and adds a response-Space
/// check; document/account ownership is supplied by its original editor owner.
public enum OriginalTemplatesServiceSpaceBinding {
    public static func bind(_ service: any TemplatesServiceProtocol,
                            spaceId: String) throws -> any TemplatesServiceProtocol {
        guard !spaceId.isEmpty, !spaceId.utf8.contains(0) else {
            throw OriginalTemplatesServiceBindingError.invalidSpace
        }
        guard let original = service as? TemplatesService else {
            throw OriginalTemplatesServiceBindingError.unsupportedOriginalDelegate
        }
        if let required = original.requiredSpaceId,
           !required.utf8.elementsEqual(spaceId.utf8) {
            throw OriginalTemplatesServiceBindingError.invalidSpace
        }
        return TemplatesService(requiredSpaceId: spaceId)
    }
}

final class TemplatesService: TemplatesServiceProtocol {
    fileprivate let requiredSpaceId: String?

    init(requiredSpaceId: String? = nil) {
        self.requiredSpaceId = requiredSpaceId
    }
    
    public func cloneTemplate(blockId: String) async throws {
        if let requiredSpaceId {
            let details = try await objectDetails(objectId: blockId, spaceId: requiredSpaceId)
            guard details.isTemplate else { throw OriginalTemplatesServiceBindingError.wrongObjectKind }
        }
        _ = try await ClientCommands.objectListDuplicate(.with {
            $0.objectIds = [blockId]
        }).invoke()
    }
    
    public func createTemplateFromObjectType(objectTypeId: String, spaceId: String) async throws -> String {
        let objectDetails = try await objectDetails(objectId: objectTypeId, spaceId: spaceId)
        if requiredSpaceId != nil, !objectDetails.isObjectType {
            throw OriginalTemplatesServiceBindingError.wrongObjectKind
        }
        
        let response = try await ClientCommands.objectCreate(.with {
            $0.details = .with {
                var fields = [String: Google_Protobuf_Value]()
                fields[BundledPropertyKey.targetObjectType.rawValue] = objectTypeId.protobufValue
                fields[BundledPropertyKey.resolvedLayout.rawValue] = objectDetails.recommendedLayout?.protobufValue ?? DetailsLayout.note.rawValue.protobufValue
                $0.fields = fields
            }
            $0.spaceID = objectDetails.spaceId
            $0.objectTypeUniqueKey = ObjectTypeUniqueKey.template.value
        }).invoke()
        
        return response.objectID
    }
    
    public func createTemplateFromObject(objectId: String) async throws -> String {
        let response = try await ClientCommands.templateCreateFromObject(.with {
            $0.contextID = objectId
        }).invoke()
        
        return response.id
    }
    
    public func deleteTemplate(templateId: String) async throws {
        if let requiredSpaceId {
            let details = try await objectDetails(objectId: templateId, spaceId: requiredSpaceId)
            guard details.isTemplate else { throw OriginalTemplatesServiceBindingError.wrongObjectKind }
        }
        _ = try await ClientCommands.objectSetIsArchived(.with {
            $0.contextID = templateId
            $0.isArchived = true
        }).invoke()
    }
    
    public func setTemplateAsDefaultForType(objectTypeId: String, templateId: String) async throws {
        if let requiredSpaceId {
            let type = try await objectDetails(objectId: objectTypeId, spaceId: requiredSpaceId)
            guard type.isObjectType else { throw OriginalTemplatesServiceBindingError.wrongObjectKind }
            if !templateId.isEmpty {
                // Read and verify the actual selected template; its owner and
                // the target type owner remain retained by the caller.
                let template = try await objectDetails(objectId: templateId, spaceId: requiredSpaceId)
                guard template.isTemplate else { throw OriginalTemplatesServiceBindingError.wrongObjectKind }
                guard template.targetObjectType.utf8.elementsEqual(objectTypeId.utf8) else {
                    throw OriginalTemplatesServiceBindingError.wrongTemplateTarget
                }
            }
        }
        _ = try await ClientCommands.objectSetDetails(.with {
            $0.contextID = objectTypeId
            
            $0.details = [
                Anytype_Model_Detail.with {
                    $0.key = BundledPropertyKey.defaultTemplateId.rawValue
                    $0.value = templateId.protobufValue
                }
            ]
        }).invoke()
    }
    
    // MARK: - Private
    
    private func objectDetails(objectId: String, spaceId: String) async throws -> ObjectDetails {
        if let requiredSpaceId, !spaceId.utf8.elementsEqual(requiredSpaceId.utf8) {
            throw OriginalTemplatesServiceBindingError.invalidSpace
        }
        let objectShow = try await ClientCommands.objectShow(.with {
            $0.contextID = objectId
            $0.objectID = objectId
            $0.spaceID = spaceId
        }).invoke()

        let details: Google_Protobuf_Struct?
        if requiredSpaceId != nil {
            let matchingDetails = objectShow.objectView.details.filter {
                $0.id.utf8.elementsEqual(objectId.utf8)
            }
            guard objectShow.hasObjectView,
                  objectShow.objectView.rootID.utf8.elementsEqual(objectId.utf8),
                  matchingDetails.count == 1, matchingDetails[0].hasDetails else {
                throw OriginalTemplatesServiceBindingError.wrongReturnedObject
            }
            details = matchingDetails[0].details
        } else {
            details = objectShow.objectView.details.first(where: { $0.id == objectId })?.details
        }
        
        guard let details,
              let objectDetails = try? ObjectDetails(protobufStruct: details) else {
            throw AnyUnpackError.typeMismatch
        }
        
        if let requiredSpaceId {
            guard objectDetails.id.utf8.elementsEqual(objectId.utf8) else {
                throw OriginalTemplatesServiceBindingError.wrongReturnedObject
            }
            guard objectDetails.spaceId.utf8.elementsEqual(requiredSpaceId.utf8) else {
                throw OriginalTemplatesServiceBindingError.wrongReturnedSpace
            }
        }
        return objectDetails
    }
}
