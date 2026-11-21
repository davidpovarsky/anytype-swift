import Foundation
import Services

/// Delegates to the original file service through the prepared document owner.
/// Both file-service injection sites share one DocumentOwnedFilePreloads ledger.
final class DocumentOwnedFileService: FileServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: any FileServiceProtocol
    private let preloads: DocumentOwnedFilePreloads

    @MainActor
    init(owner: EditorDocumentWriteOwner, service: any FileServiceProtocol,
         preloads: DocumentOwnedFilePreloads) throws {
        try preloads.requireOwner(owner)
        self.owner = owner
        self.service = service
        self.preloads = preloads
    }

    func uploadFileBlock(path: String, contextID: String, blockID: String) async throws {
        try await owner.performMutation(contextId: contextID) { [service] in
            try await service.uploadFileBlock(path: path, contextID: contextID, blockID: blockID)
        }
    }

    func uploadFileObject(path: String, spaceId: String, origin: ObjectOrigin,
                          createdInContext: String, createdInContextRef: String) async throws -> FileDetails {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.uploadFileObject(path: path, spaceId: spaceId, origin: origin,
                createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        }
    }

    func preloadFileObject(path: String, spaceId: String, origin: ObjectOrigin,
                           createdInContext: String, createdInContextRef: String) async throws -> String {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service, preloads, owner] in
            let fileID = try await service.preloadFileObject(path: path, spaceId: spaceId, origin: origin,
                createdInContext: createdInContext, createdInContextRef: createdInContextRef)
            try await preloads.remember(fileID: fileID, spaceID: spaceId, owner: owner)
            return fileID
        }
    }

    func uploadPreloadedFileObject(fileId: String, spaceId: String, origin: ObjectOrigin,
                                   createdInContext: String, createdInContextRef: String) async throws -> FileDetails {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service, preloads, owner] in
            let claim = try await preloads.claim(fileID: fileId, spaceID: spaceId, owner: owner)
            let details = try await service.uploadPreloadedFileObject(fileId: fileId, spaceId: spaceId,
                origin: origin, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
            try await preloads.completed(claim, owner: owner)
            return details
        }
    }

    func discardPreloadFile(fileId: String, spaceId: String) async throws {
        try await owner.performMutation(spaceId: spaceId, createdInContext: "") { [service, preloads, owner] in
            let claim = try await preloads.claim(fileID: fileId, spaceID: spaceId, owner: owner)
            try await service.discardPreloadFile(fileId: fileId, spaceId: spaceId)
            try await preloads.completed(claim, owner: owner)
        }
    }

    func nodeUsage() async throws -> NodeUsageInfo {
        try await owner.performRead(rpcNames: ["FileNodeUsage"]) { [service] in
            try await service.nodeUsage()
        }
    }

    // These original operations have no document/Space ownership argument.
    // A document editor cannot acquire global cache/settings authority by using
    // its own context as a placeholder. Unbound original callers are unchanged.
    func clearCache() async throws { try await rejectUnscopedMutation() }
    func scheduleCacheDownload(fileObjectId: String) async throws { try await rejectUnscopedMutation() }
    func cancelCacheDownload(fileObjectId: String) async throws { try await rejectUnscopedMutation() }
    func setAutoDownload(enabled: Bool, wifiOnly: Bool) async throws { try await rejectUnscopedMutation() }
    func setAutoDownloadSizeLimit(mebibytes: Int64) async throws { try await rejectUnscopedMutation() }

    private func rejectUnscopedMutation() async throws -> Never {
        try await owner.validateOwnership()
        throw EditorDocumentWriteError.rejected(.wrongContext)
    }
}
