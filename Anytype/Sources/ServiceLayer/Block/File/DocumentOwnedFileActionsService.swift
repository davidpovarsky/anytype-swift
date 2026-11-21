import Foundation
import Services
import AnytypeCore
import PhotosUI
import SwiftUI

/// The higher file API actually injected into both original block-action sites.
/// It runs the original FileActionsService, configured with the same owner at
/// its lower RPC boundary and with private retained input staging.
final class DocumentOwnedFileActionsService: FileActionsServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: FileActionsService

    @MainActor
    init(owner: EditorDocumentWriteOwner, service: FileActionsService,
         staging: DocumentOwnedFileStaging) throws {
        try staging.requireOwner(owner)
        self.owner = owner
        self.service = service
    }

    @MainActor
    static func bindOriginal(_ service: any FileActionsServiceProtocol,
                             owner: EditorDocumentWriteOwner,
                             preloads: DocumentOwnedFilePreloads,
                             staging: DocumentOwnedFileStaging) throws -> any FileActionsServiceProtocol {
        guard let original = service as? FileActionsService else {
            throw DocumentOwnedFileActionsError.unsupportedOriginalDelegate
        }
        return try original.documentOwned(owner: owner, preloads: preloads, staging: staging)
    }

    func createFileData(source: FileUploadingSource) async throws -> FileData {
        try await owner.performRead(rpcNames: []) { [service] in
            try await service.createFileData(source: source)
        }
    }

    func createFileData(photoItem: PhotosPickerItem) async throws -> FileData {
        try await owner.performRead(rpcNames: []) { [service] in
            try await service.createFileData(photoItem: photoItem)
        }
    }

    func createFileData(image: UIImage, type: String) throws -> FileData {
        try prepareSynchronously { try service.createFileData(image: image, type: type) }
    }

    func createFileData(fileUrl: URL) throws -> FileData {
        try prepareSynchronously { try service.createFileData(fileUrl: fileUrl) }
    }

    func uploadDataAt(data: FileData, contextID: String, blockID: String) async throws {
        try await owner.performMutation(contextId: contextID) { [service] in
            try await service.uploadDataAt(data: data, contextID: contextID, blockID: blockID)
        }
    }

    func uploadFileObject(spaceId: String, data: FileData, origin: ObjectOrigin,
                          createdInContext: String, createdInContextRef: String) async throws -> FileDetails {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.uploadFileObject(spaceId: spaceId, data: data, origin: origin,
                createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        }
    }

    func preloadFileObject(spaceId: String, data: FileData, origin: ObjectOrigin,
                           createdInContext: String, createdInContextRef: String) async throws -> String {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.preloadFileObject(spaceId: spaceId, data: data, origin: origin,
                createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        }
    }

    func uploadPreloadedFileObject(fileId: String, spaceId: String, data: FileData,
                                   origin: ObjectOrigin, createdInContext: String,
                                   createdInContextRef: String) async throws -> FileDetails {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.uploadPreloadedFileObject(fileId: fileId, spaceId: spaceId, data: data,
                origin: origin, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        }
    }

    func discardPreloadFile(fileId: String, spaceId: String) async throws {
        try await owner.performMutation(spaceId: spaceId, createdInContext: "") { [service] in
            try await service.discardPreloadFile(fileId: fileId, spaceId: spaceId)
        }
    }

    func uploadDataAt(source: FileUploadingSource, contextID: String, blockID: String) async throws {
        try await owner.performMutation(contextId: contextID) { [service] in
            try await service.uploadDataAt(source: source, contextID: contextID, blockID: blockID)
        }
    }

    func uploadImage(spaceId: String, source: FileUploadingSource, origin: ObjectOrigin,
                      createdInContext: String, createdInContextRef: String) async throws -> FileDetails {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.uploadImage(spaceId: spaceId, source: source, origin: origin,
                createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        }
    }

    func nodeUsage() async throws -> NodeUsageInfo {
        try await owner.performRead(rpcNames: ["FileNodeUsage"]) { [service] in
            try await service.nodeUsage()
        }
    }

    func clearCache() async throws {
        try await owner.validateOwnership()
        throw EditorDocumentWriteError.rejected(.wrongContext)
    }

    private func prepareSynchronously<Value: Sendable>(_ operation: () throws -> Value) throws -> Value {
        guard Thread.isMainThread else { throw DocumentOwnedFileActionsError.requiresMainActor }
        return try MainActor.assumeIsolated {
            try owner.performSynchronousOperation(requiresEditing: false, operation: operation)
        }
    }
}
