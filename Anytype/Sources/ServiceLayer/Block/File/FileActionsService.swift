import Foundation
import Combine
import Services
import ProtobufMessages
import AnytypeCore
import UniformTypeIdentifiers
import PhotosUI
import SwiftUI

final class FileActionsService: FileActionsServiceProtocol, Sendable {
    
    private enum FileServiceError: Error {
        case undefiled
    }
    
    private enum Constants {
        static let filesDirectory = "fileServiceCache"
        static let supportedUploadedTypes: [UTType] = [
            // We are don't support heic and other platform specific types
            // Picture
            UTType.image,
            UTType.ico,
            UTType.icns,
            UTType.png,
            UTType.jpeg,
            UTType.webP,
            UTType.tiff,
            UTType.bmp,
            UTType.svg,
            UTType.rawImage,
            // Video
            UTType.movie,
            UTType.video,
            UTType.quickTimeMovie,
            UTType.mpeg,
            UTType.mpeg2Video,
            UTType.mpeg2TransportStream,
            UTType.mpeg4Movie,
            UTType.appleProtectedMPEG4Video,
            UTType.avi,
            // Audio
            UTType.audio,
            // Other Files
            UTType.item
        ]
    }
    
    // Clear file cache once for app launch. Should be as singletone in DI.
    private let cacheCleared = AtomicStorage(false)
    private let fileService: any FileServiceProtocol
    private let ownedStaging: DocumentOwnedFileStaging?
    
    private let dateTimeFormatter = DateFormatter.photoDateTimeFormatter
    
    init() {
        fileService = Container.shared.fileService()
        ownedStaging = nil
        if !cacheCleared.value {
            clearFileCache()
            cacheCleared.value = true
        }
    }

    /// An explicitly bound original service never clears the application-wide
    /// temporary cache and never removes an input during an uncertain RPC.
    private init(fileService: any FileServiceProtocol, ownedStaging: DocumentOwnedFileStaging) {
        self.fileService = fileService
        self.ownedStaging = ownedStaging
    }

    @MainActor
    func documentOwned(owner: EditorDocumentWriteOwner, preloads: DocumentOwnedFilePreloads,
                       staging: DocumentOwnedFileStaging) throws -> any FileActionsServiceProtocol {
        try owner.validateOwnership()
        try staging.requireOwner(owner)
        let lower = try DocumentOwnedFileService(owner: owner, service: fileService, preloads: preloads)
        let original = FileActionsService(fileService: lower, ownedStaging: staging)
        return try DocumentOwnedFileActionsService(owner: owner, service: original, staging: staging)
    }
    
    func createFileData(source: FileUploadingSource) async throws -> FileData {
        switch source {
        case .path(let path):
            return try retainedInput(FileData(path: path, type: .data, sizeInBytes: nil, isTemporary: false))
        case .itemProvider(let itemProvider):
            let typeIdentifier = itemProvider.registeredTypeIdentifiers.compactMap { typeId in
                Constants.supportedUploadedTypes.first { $0.identifier == typeId }
            }.first
            
            if let typeIdentifier {
                return try await loadData(itemProvider: itemProvider, type: typeIdentifier)
            } else {
                // Try to represent in data format
                return try await loadData(itemProvider: itemProvider, type: UTType.data)
            }
        }
    }
 
    func createFileData(photoItem: PhotosPickerItem) async throws -> FileData {
        do {
            let typeIdentifier = photoItem.supportedContentTypes.first {
                Constants.supportedUploadedTypes.contains($0)
            }
            guard let typeIdentifier else {
                throw FileServiceError.undefiled
            }
            guard let data = try await photoItem.loadTransferable(type: MediaFileUrl.self) else {
                throw FileServiceError.undefiled
            }
            if ownedStaging != nil { try DocumentOwnedFileStaging.requireRegularInput(data.url) }
            let newPath = try makeDataDirectory()
            
            let newFilePath = newPath.appendingPathComponent(data.url.lastPathComponent, isDirectory: false)
            try FileManager.default.moveItem(at: data.url, to: newFilePath)
            
            let resources = try newFilePath.resourceValues(forKeys: [.fileSizeKey])
            return FileData(path: newFilePath.relativePath, type: typeIdentifier, sizeInBytes: resources.fileSize, isTemporary: true)
        } catch {
            anytypeAssertionFailure(error.localizedDescription)
            throw error
        }
    }
    
    func createFileData(image: UIImage, type: String) throws -> FileData {
        do {
            guard let typeIdentifier = UTType(type), Constants.supportedUploadedTypes.contains(typeIdentifier) else {
                throw FileServiceError.undefiled
            }
            guard let data = image.jpegData(compressionQuality: 1) else {
                throw FileServiceError.undefiled
            }
            
            let path = try makeDataDirectory()
            
            let nowDateString = dateTimeFormatter.string(from: Date())
            let imageName = "IMG_\(nowDateString).jpg"
            let newFilePath = path.appendingPathComponent(imageName, isDirectory: false)
            
            try data.write(to: newFilePath)
            
            let resources = try newFilePath.resourceValues(forKeys: [.fileSizeKey])
            
            return FileData(path: newFilePath.relativePath, type: typeIdentifier, sizeInBytes: resources.fileSize, isTemporary: true)
        } catch {
            anytypeAssertionFailure(error.localizedDescription)
            throw error
        }
    }
    
    func createFileData(fileUrl: URL) throws -> FileData {
        do {
            if ownedStaging != nil { try DocumentOwnedFileStaging.requireRegularInput(fileUrl) }
            let newPath = try makeDataDirectory()
            
            let newFilePath = newPath.appendingPathComponent(fileUrl.lastPathComponent, isDirectory: false)
            try FileManager.default.copyItem(at: fileUrl, to: newFilePath)
            
            let resources = try fileUrl.resourceValues(forKeys: [.fileSizeKey])
            
            return FileData(path: newFilePath.relativePath, type: getUTType(for: newFilePath) ?? .data, sizeInBytes: resources.fileSize, isTemporary: true)
        } catch {
            anytypeAssertionFailure(error.localizedDescription)
            throw error
        }
    }
    
    func uploadDataAt(data: FileData, contextID: String, blockID: String) async throws {
        let input = try retainedInput(data)
        defer {
            if ownedStaging == nil && data.isTemporary {
                try? FileManager.default.removeItem(atPath: data.path)
            }
        }
        try await fileService.uploadFileBlock(path: input.path, contextID: contextID, blockID: blockID)
    }
    
    func uploadFileObject(spaceId: String, data: FileData, origin: ObjectOrigin, createdInContext: String, createdInContextRef: String) async throws -> FileDetails {
        let input = try retainedInput(data)
        defer {
            if ownedStaging == nil && data.isTemporary {
                try? FileManager.default.removeItem(atPath: data.path)
            }
        }

        return try await fileService.uploadFileObject(path: input.path, spaceId: spaceId, origin: origin, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
    }

    func preloadFileObject(spaceId: String, data: FileData, origin: ObjectOrigin, createdInContext: String, createdInContextRef: String) async throws -> String {
        let input = try retainedInput(data)
        return try await fileService.preloadFileObject(path: input.path, spaceId: spaceId, origin: origin, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
    }

    func uploadPreloadedFileObject(fileId: String, spaceId: String, data: FileData, origin: ObjectOrigin, createdInContext: String, createdInContextRef: String) async throws -> FileDetails {
        defer {
            if ownedStaging == nil && data.isTemporary {
                try? FileManager.default.removeItem(atPath: data.path)
            }
        }

        return try await fileService.uploadPreloadedFileObject(fileId: fileId, spaceId: spaceId, origin: origin, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
    }

    func discardPreloadFile(fileId: String, spaceId: String) async throws {
        try await fileService.discardPreloadFile(fileId: fileId, spaceId: spaceId)
    }
    
    func uploadDataAt(source: FileUploadingSource, contextID: String, blockID: String) async throws {
        let data = try await createFileData(source: source)
        try await uploadDataAt(data: data, contextID: contextID, blockID: blockID)
    }
    
    func uploadImage(spaceId: String, source: FileUploadingSource, origin: ObjectOrigin, createdInContext: String, createdInContextRef: String) async throws -> FileDetails {
        let data = try await createFileData(source: source)
        return try await uploadFileObject(spaceId: spaceId, data: data, origin: origin, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
    }
    
    func clearCache() async throws {
        try await fileService.clearCache()
    }
    
    func nodeUsage() async throws -> NodeUsageInfo {
        return try await fileService.nodeUsage()
    }
    
    // MARK: - Private
    
    private func tempDirectoryPath() -> URL {
        if let ownedStaging { return ownedStaging.directory }
        return FileManager.default.temporaryDirectory.appendingPathComponent(Constants.filesDirectory, isDirectory: true)
    }

    private func makeDataDirectory() throws -> URL {
        if let ownedStaging { return try ownedStaging.makeExclusiveDirectory() }
        let path = tempDirectoryPath().appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: path, withIntermediateDirectories: true)
        return path
    }

    /// Pin borrowed inputs through the same original file-copy method before a
    /// native upload can outlive its caller. Existing unbound callers keep their
    /// exact input path and cleanup behavior. Bound inputs are retained intact.
    private func retainedInput(_ data: FileData) throws -> FileData {
        guard let ownedStaging else { return data }
        if try ownedStaging.containsRegularFile(path: data.path) { return data }
        let source = URL(fileURLWithPath: data.path)
        try DocumentOwnedFileStaging.requireRegularInput(source)
        let copied = try createFileData(fileUrl: source)
        guard try ownedStaging.containsRegularFile(path: copied.path) else {
            throw DocumentOwnedFileActionsError.invalidInputFile
        }
        return copied
    }
    
    private func clearFileCache() {
        
        let fileManager = FileManager.default
        
        guard let paths = try? fileManager.contentsOfDirectory(at: tempDirectoryPath(), includingPropertiesForKeys: nil) else { return }
        
        for path in paths {
            try? fileManager.removeItem(at: path)
        }
    }
    
    private func getUTType(for fileURL: URL) -> UTType? {
        do {
            let resourceValues = try fileURL.resourceValues(forKeys: [.typeIdentifierKey])
            if let typeIdentifier = resourceValues.typeIdentifier {
                return UTType(typeIdentifier)
            }
        } catch {}
        
        return nil
    }
    
    private func loadData(itemProvider: NSItemProvider, type: UTType) async throws -> FileData {
        let url = try await itemProvider.loadFileRepresentation(forTypeIdentifier: type.identifier,
            directory: tempDirectoryPath(), ownedStaging: ownedStaging)
        let resources = try url.resourceValues(forKeys: [.fileSizeKey])
        return FileData(path: url.relativePath, type: type, sizeInBytes: resources.fileSize, isTemporary: true)
    }

}
