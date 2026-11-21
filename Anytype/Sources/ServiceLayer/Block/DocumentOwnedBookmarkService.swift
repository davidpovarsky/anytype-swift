import Foundation
import Services
import AnytypeCore

/// The existing bookmark implementation remains the only executor. The owner
/// checks the exact original document or Space and the shared RPC dispatch fence
/// rechecks authority after any await inside that implementation.
final class DocumentOwnedBookmarkService: BookmarkServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: any BookmarkServiceProtocol

    init(owner: EditorDocumentWriteOwner, service: any BookmarkServiceProtocol) {
        self.owner = owner
        self.service = service
    }

    func fetchBookmark(objectId: String, blockID: String, url: AnytypeURL) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.fetchBookmark(objectId: objectId, blockID: blockID, url: url)
        }
    }

    func createAndFetchBookmark(objectId: String, targetID: String,
                                position: BlockPosition, url: AnytypeURL) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.createAndFetchBookmark(objectId: objectId, targetID: targetID,
                position: position, url: url)
        }
    }

    func createBookmarkObject(spaceId: String, url: AnytypeURL, templateId: String?,
                              origin: ObjectOrigin, createdInContext: String,
                              createdInContextRef: String) async throws -> ObjectDetails {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.createBookmarkObject(spaceId: spaceId, url: url, templateId: templateId,
                origin: origin, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        }
    }

    func fetchBookmarkContent(bookmarkId: String, url: AnytypeURL) async throws {
        try await owner.performMutation(contextId: bookmarkId) { [service] in
            try await service.fetchBookmarkContent(bookmarkId: bookmarkId, url: url)
        }
    }

    func fetchLinkPreview(url: AnytypeURL) async throws -> LinkPreview {
        try await owner.performRead(rpcNames: ["LinkPreview"]) { [service] in
            try await service.fetchLinkPreview(url: url)
        }
    }
}
