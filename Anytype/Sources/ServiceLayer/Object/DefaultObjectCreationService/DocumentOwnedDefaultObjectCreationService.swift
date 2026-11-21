import Services

enum DocumentOwnedDefaultObjectCreationError: Error, Sendable {
    case unsupportedOriginalDelegate
}

/// The original default-type lookup, subscription and ObjectCreate remain one
/// original operation. The same owner reaches actual Invocation dispatch after
/// the type-provider await; no template/type IDs or defaults are rewritten.
final class DocumentOwnedDefaultObjectCreationService: DefaultObjectCreationServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: DefaultObjectCreationService

    private init(owner: EditorDocumentWriteOwner, service: DefaultObjectCreationService) {
        self.owner = owner
        self.service = service
    }

    @MainActor
    static func bindOriginal(_ service: any DefaultObjectCreationServiceProtocol,
                             owner: EditorDocumentWriteOwner) throws -> any DefaultObjectCreationServiceProtocol {
        try owner.validateOwnership()
        guard let original = service as? DefaultObjectCreationService else {
            throw DocumentOwnedDefaultObjectCreationError.unsupportedOriginalDelegate
        }
        return DocumentOwnedDefaultObjectCreationService(owner: owner, service: original)
    }

    func createDefaultObject(name: String, shouldDeleteEmptyObject: Bool,
                             spaceId: String) async throws -> ObjectDetails {
        try await owner.performMutation(spaceId: spaceId) { [service] in
            try await service.createDefaultObject(name: name,
                shouldDeleteEmptyObject: shouldDeleteEmptyObject, spaceId: spaceId)
        }
    }
}
