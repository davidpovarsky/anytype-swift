import Foundation

/// Moves an existing app-owned settings directory out of user-visible Documents.
/// The move preserves every original file and never overwrites an existing
/// private destination. A failed upgrade leaves the source available for repair.
public enum PinkhaPrivateDirectoryMigration {
    public enum Failure: Error, Equatable, Sendable {
        case invalidPath, invalidDirectory, unsupportedEntry, destinationConflict, sourceChanged
    }
    public struct Receipt: Equatable, Sendable {
        public let moved: Bool
        public let fileCount: Int
    }

    public static func prepare(legacy: URL, destination: URL) throws -> Receipt {
        let manager = FileManager.default
        guard legacy.isFileURL, destination.isFileURL,
              legacy.path != destination.path,
              legacy.standardizedFileURL.path == legacy.path,
              destination.standardizedFileURL.path == destination.path,
              legacy.resolvingSymlinksInPath().path == legacy.path,
              destination.resolvingSymlinksInPath().path == destination.path else {
            throw Failure.invalidPath
        }
        let container = try commonContainer(legacy, destination)
        try requireNoSymlinkAncestors(legacy, through: container)
        try requireNoSymlinkAncestors(destination, through: container)
        let sourceExists = manager.fileExists(atPath: legacy.path)
        let destinationExists = manager.fileExists(atPath: destination.path)
        // No silent merge or preference between two different settings stores.
        // In particular, the active custom network must not be reset to default.
        guard !(sourceExists && destinationExists) else { throw Failure.destinationConflict }
        let before = sourceExists ? try inventory(legacy) : []
        if destinationExists {
            let existing = try inventory(destination)
            try makePrivate(destination, files: existing)
            return .init(moved: false, fileCount: existing.count)
        }
        let parent = destination.deletingLastPathComponent()
        try manager.createDirectory(at: parent, withIntermediateDirectories: true,
                                    attributes: [.posixPermissions: 0o700])
        guard parent.resolvingSymlinksInPath().path == parent.path else { throw Failure.invalidPath }
        if sourceExists {
            // Both URLs are within the same application container. Foundation
            // refuses an existing destination; the complete directory is moved.
            try manager.moveItem(at: legacy, to: destination)
            let after = try inventory(destination)
            guard before == after, !manager.fileExists(atPath: legacy.path) else {
                throw Failure.sourceChanged
            }
            try makePrivate(destination, files: after)
            return .init(moved: true, fileCount: after.count)
        }
        try manager.createDirectory(at: destination, withIntermediateDirectories: false,
                                    attributes: [.posixPermissions: 0o700])
        return .init(moved: false, fileCount: 0)
    }

    private static func commonContainer(_ first: URL, _ second: URL) throws -> URL {
        let firstParts = first.pathComponents
        let secondParts = second.pathComponents
        let count = zip(firstParts, secondParts).prefix { $0 == $1 }.count
        guard count > 1 else { throw Failure.invalidPath }
        let common = URL(fileURLWithPath: NSString.path(withComponents: Array(firstParts.prefix(count))),
                         isDirectory: true)
        // Both inputs belong to one existing app container. Foundation keeps
        // system aliases such as /var canonical on Darwin, while resolving
        // ordinary symlinks inside that container. Validate this existing root
        // before inspecting every descendant, including nonexistent suffixes.
        let attributes = try FileManager.default.attributesOfItem(atPath: common.path)
        guard attributes[.type] as? FileAttributeType == .typeDirectory,
              common.resolvingSymlinksInPath().path == common.path else {
            throw Failure.invalidPath
        }
        return common
    }

    private static func requireNoSymlinkAncestors(_ url: URL, through container: URL) throws {
        // Foundation may leave a nonexistent suffix unresolved. Inspect each
        // component below the already verified app container before creating it.
        var cursor = url
        while true {
            do {
                let attributes = try FileManager.default.attributesOfItem(atPath: cursor.path)
                guard attributes[.type] as? FileAttributeType != .typeSymbolicLink else {
                    throw Failure.invalidPath
                }
            } catch let error as NSError where error.domain == NSCocoaErrorDomain &&
                [NSFileNoSuchFileError, NSFileReadNoSuchFileError].contains(error.code) {
                // This descendant will be created only after all its existing
                // parents have been checked. Other filesystem errors propagate.
            }
            if cursor.path == container.path { break }
            guard cursor.path != "/" else { throw Failure.invalidPath }
            cursor.deleteLastPathComponent()
        }
    }

    private struct FileIdentity: Equatable {
        let name: String
        let inode: UInt64
        let size: UInt64
        let modification: Date
    }

    private static func inventory(_ directory: URL) throws -> [FileIdentity] {
        let manager = FileManager.default
        let root = try manager.attributesOfItem(atPath: directory.path)
        guard root[.type] as? FileAttributeType == .typeDirectory else { throw Failure.invalidDirectory }
        return try manager.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            .sorted { $0.lastPathComponent < $1.lastPathComponent }.map { file in
                let attributes = try manager.attributesOfItem(atPath: file.path)
                guard attributes[.type] as? FileAttributeType == .typeRegular,
                      (attributes[.referenceCount] as? NSNumber)?.uint64Value == 1,
                      let inode = (attributes[.systemFileNumber] as? NSNumber)?.uint64Value,
                      let size = (attributes[.size] as? NSNumber)?.uint64Value,
                      let modification = attributes[.modificationDate] as? Date else {
                    throw Failure.unsupportedEntry
                }
                return FileIdentity(name: file.lastPathComponent, inode: inode, size: size,
                                    modification: modification)
            }
    }

    private static func makePrivate(_ directory: URL, files: [FileIdentity]) throws {
        let manager = FileManager.default
        try manager.setAttributes([.posixPermissions: 0o700], ofItemAtPath: directory.path)
        for file in files {
            try manager.setAttributes([.posixPermissions: 0o600],
                                      ofItemAtPath: directory.appendingPathComponent(file.name).path)
        }
    }
}
