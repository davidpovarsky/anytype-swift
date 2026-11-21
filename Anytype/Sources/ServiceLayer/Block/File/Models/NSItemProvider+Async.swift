import Foundation

extension NSItemProvider {
    
    private enum LoadFileRepresentationError: Error {
        case undefined
    }
    
    func loadFileRepresentation(
        forTypeIdentifier typeIdentifier: String,
        directory: URL,
        ownedStaging: DocumentOwnedFileStaging? = nil
    ) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            loadFileRepresentation(forTypeIdentifier: typeIdentifier) { url, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else if let url = url {
                    do {
                        let destination: URL
                        if let ownedStaging {
                            try DocumentOwnedFileStaging.requireRegularInput(url)
                            let exclusive = try ownedStaging.makeExclusiveDirectory()
                            destination = exclusive.appendingPathComponent(url.lastPathComponent, isDirectory: false)
                        } else {
                            destination = directory.appendingPathComponent(url.lastPathComponent, isDirectory: false)
                            try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
                            try? FileManager.default.removeItem(at: destination)
                        }
                        try FileManager.default.copyItem(at: url, to: destination)
                        if let ownedStaging, try !ownedStaging.containsRegularFile(path: destination.path) {
                            throw DocumentOwnedFileActionsError.invalidInputFile
                        }
                        continuation.resume(returning: destination)
                    } catch {
                        continuation.resume(throwing: error)
                    }
                } else {
                    continuation.resume(throwing: LoadFileRepresentationError.undefined)
                }
            }
        }
    }
}
