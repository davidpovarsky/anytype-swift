import Foundation
import Darwin

enum DocumentOwnedFileActionsError: Error, Sendable, Equatable {
    case unsupportedOriginalDelegate
    case requiresMainActor
    case invalidInputFile
    case fileSystemFailure(Int32)
}

/// Private recovery files for one original prepared document. This capability
/// cannot point at a caller-supplied directory and never clears another session.
/// Its files survive a late RPC completion, rejected save and process restart.
final class DocumentOwnedFileStaging: Sendable {
    let directory: URL
    private let owner: EditorDocumentWriteOwner
    private let device: dev_t
    private let inode: ino_t

    @MainActor
    init(owner: EditorDocumentWriteOwner) throws {
        try owner.validateOwnership()
        let support = try FileManager.default.url(
            for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true
        ).resolvingSymlinksInPath().standardizedFileURL
        let parent = support.appendingPathComponent("AnytypeOriginalEditorRecovery", isDirectory: true)
        if Darwin.mkdir(parent.path, 0o700) != 0 && errno != EEXIST {
            throw DocumentOwnedFileActionsError.fileSystemFailure(errno)
        }
        var parentInfo = stat()
        guard Darwin.lstat(parent.path, &parentInfo) == 0,
              parentInfo.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              parent.resolvingSymlinksInPath().path.utf8.elementsEqual(parent.path.utf8) else {
            throw DocumentOwnedFileActionsError.invalidInputFile
        }
        let owned = parent.appendingPathComponent(UUID().uuidString, isDirectory: true)
        guard Darwin.mkdir(owned.path, 0o700) == 0 else {
            throw DocumentOwnedFileActionsError.fileSystemFailure(errno)
        }
        var identity = stat()
        guard Darwin.lstat(owned.path, &identity) == 0,
              identity.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR) else {
            throw DocumentOwnedFileActionsError.invalidInputFile
        }
        self.owner = owner
        directory = owned
        device = identity.st_dev
        inode = identity.st_ino
        // Retirement does not delete a directory or input already created.
        try owner.validateOwnership()
    }

    @MainActor
    func requireOwner(_ expected: EditorDocumentWriteOwner) throws {
        guard owner === expected else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
    }

    func containsRegularFile(path: String) throws -> Bool {
        try requireRootIdentity()
        let url = URL(fileURLWithPath: path).standardizedFileURL
        let resolved = url.resolvingSymlinksInPath()
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true,
              resolved.path.utf8.elementsEqual(url.path.utf8) else { return false }
        let root = Array((directory.path + "/").utf8)
        return Array(url.path.utf8).starts(with: root)
    }

    /// Each conversion or provider load gets its own exclusive child, so two
    /// inputs with the same last path component cannot replace each other.
    func makeExclusiveDirectory() throws -> URL {
        try requireRootIdentity()
        let descriptor = Darwin.open(directory.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard descriptor >= 0 else { throw DocumentOwnedFileActionsError.fileSystemFailure(errno) }
        defer { Darwin.close(descriptor) }
        var actual = stat()
        guard Darwin.fstat(descriptor, &actual) == 0,
              actual.st_dev == device, actual.st_ino == inode else {
            throw DocumentOwnedFileActionsError.invalidInputFile
        }
        let name = UUID().uuidString
        guard Darwin.mkdirat(descriptor, name, 0o700) == 0 else {
            throw DocumentOwnedFileActionsError.fileSystemFailure(errno)
        }
        try requireRootIdentity()
        let child = directory.appendingPathComponent(name, isDirectory: true)
        var childInfo = stat()
        guard Darwin.lstat(child.path, &childInfo) == 0,
              childInfo.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              child.resolvingSymlinksInPath().path.utf8.elementsEqual(child.path.utf8) else {
            throw DocumentOwnedFileActionsError.invalidInputFile
        }
        return child
    }

    private func requireRootIdentity() throws {
        var actual = stat()
        guard Darwin.lstat(directory.path, &actual) == 0,
              actual.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              actual.st_dev == device, actual.st_ino == inode,
              directory.resolvingSymlinksInPath().path.utf8.elementsEqual(directory.path.utf8) else {
            throw DocumentOwnedFileActionsError.invalidInputFile
        }
    }

    static func requireRegularInput(_ url: URL) throws {
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
        guard url.isFileURL, values.isRegularFile == true, values.isSymbolicLink != true else {
            throw DocumentOwnedFileActionsError.invalidInputFile
        }
    }
}
