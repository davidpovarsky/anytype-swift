import Foundation

public struct UnsplashItem: Sendable {
    public let id: String
    public let url: URL
    public let artistName: String
    public let artistURL: URL
}

public protocol UnsplashServiceProtocol: Sendable {
    func searchUnsplashImages(query: String) async throws -> [UnsplashItem]
    func downloadImage(spaceId: String, id: String, createdInContext: String, createdInContextRef: String) async throws -> ObjectId
}

public extension UnsplashServiceProtocol {
    func downloadImage(spaceId: String, id: String) async throws -> ObjectId {
        try await downloadImage(spaceId: spaceId, id: id, createdInContext: "", createdInContextRef: "")
    }
}


/// The original service still performs UnsplashSearch/UnsplashDownload. The
/// owner also governs their actual Invocation dispatch and late completion.
struct DocumentOwnedUnsplashService: UnsplashServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: any UnsplashServiceProtocol

    init(owner: EditorDocumentWriteOwner, service: any UnsplashServiceProtocol) {
        self.owner = owner
        self.service = service
    }

    func searchUnsplashImages(query: String) async throws -> [UnsplashItem] {
        try await owner.performRead(rpcNames: ["UnsplashSearch"]) { [service] in
            try await service.searchUnsplashImages(query: query)
        }
    }

    func downloadImage(spaceId: String, id: String, createdInContext: String,
                       createdInContextRef: String) async throws -> ObjectId {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.downloadImage(spaceId: spaceId, id: id,
                createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        }
    }
}
