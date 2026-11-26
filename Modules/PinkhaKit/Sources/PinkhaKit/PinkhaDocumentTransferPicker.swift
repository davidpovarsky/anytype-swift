#if canImport(UIKit) && canImport(SwiftUI)
import Foundation
import UIKit
import SwiftUI
import UniformTypeIdentifiers

/// The retained source lives only in a fresh private staging directory. The
/// system document picker copies it to the destination explicitly chosen by the
/// user; only that original delegate URL may be reported as an exported file.
@MainActor
public final class PinkhaDocumentExportSource: Identifiable {
    public let id = UUID()
    public let fileURL: URL
    private let directory: URL

    public init(data: Data, filename: String) throws {
        guard !filename.isEmpty, filename != ".", filename != "..", filename.utf8.count <= 240,
              !filename.contains("/"), !filename.contains("\\"), !filename.contains("\0") else {
            throw CocoaError(.fileWriteInvalidFileName)
        }
        let base = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
        let directory = base.appendingPathComponent("PinkhaExport-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700,
                         .protectionKey: FileProtectionType.completeUntilFirstUserAuthentication])
        let file = directory.appendingPathComponent(filename, isDirectory: false)
        do {
            try data.write(to: file, options: [.withoutOverwriting, .completeFileProtectionUntilFirstUserAuthentication])
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
        } catch {
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
        self.directory = directory
        self.fileURL = file
    }

    deinit {
        // Only this fresh owned directory is removed. User-selected exports,
        // native stores and archive input files never belong to this cleanup.
        try? FileManager.default.removeItem(at: directory)
    }
}

/// One common UIKit file-provider boundary for both native engine adapters.
@MainActor
public struct PinkhaDocumentTransferPicker: UIViewControllerRepresentable {
    public enum Operation {
        case export(URL)
        case open([UTType])
    }

    private let operation: Operation
    private let initialDirectory: URL
    private let completion: @MainActor (Result<URL?, any Error>) -> Void

    public init(operation: Operation, initialDirectory: URL,
                completion: @escaping @MainActor (Result<URL?, any Error>) -> Void) {
        self.operation = operation
        self.initialDirectory = initialDirectory
        self.completion = completion
    }

    public func makeCoordinator() -> Coordinator { Coordinator(completion: completion) }

    public func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let picker: UIDocumentPickerViewController
        switch operation {
        case .export(let url): picker = UIDocumentPickerViewController(forExporting: [url], asCopy: true)
        case .open(let types): picker = UIDocumentPickerViewController(forOpeningContentTypes: types, asCopy: false)
        }
        // Apply the real starting directory to the actual picker before it is
        // presented, rather than relying on a SwiftUI environment preference.
        picker.directoryURL = initialDirectory
        picker.allowsMultipleSelection = false
        picker.delegate = context.coordinator
        return picker
    }

    public func updateUIViewController(_ controller: UIDocumentPickerViewController, context: Context) {}

    public final class Coordinator: NSObject, UIDocumentPickerDelegate {
        private let completion: @MainActor (Result<URL?, any Error>) -> Void
        private var finished = false
        fileprivate init(completion: @escaping @MainActor (Result<URL?, any Error>) -> Void) {
            self.completion = completion
        }

        public func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            guard !finished else { return }
            finished = true
            guard urls.count == 1, let url = urls.first, url.isFileURL else {
                completion(.failure(CocoaError(.fileReadInvalidFileName)))
                return
            }
            completion(.success(url))
        }

        public func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
            guard !finished else { return }
            finished = true
            completion(.success(nil))
        }
    }
}
#endif
