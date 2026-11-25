import Foundation
import XCTest
@testable import PinkhaKit

final class PinkhaPrivateDirectoryMigrationTests: XCTestCase {
    private func fixture() throws -> (URL, URL, URL) {
        let root = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("PinkhaPrivateMigration-" + UUID().uuidString, isDirectory: true)
        let legacy = root.appendingPathComponent("Documents/Servers", isDirectory: true)
        let destination = root.appendingPathComponent("Library/Application Support/Pinkha/Network/Servers", isDirectory: true)
        try FileManager.default.createDirectory(at: legacy.deletingLastPathComponent(), withIntermediateDirectories: true)
        return (root, legacy, destination)
    }

    func testMovesExactOriginalSettingsAndFileIdentityToPrivateStorage() throws {
        let (root, legacy, destination) = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: legacy, withIntermediateDirectories: false)
        let name = "רשת.yml", bytes = Data("nodes:\n  - id: exact-original-node\n".utf8)
        let original = legacy.appendingPathComponent(name)
        try bytes.write(to: original)
        let inode = try FileManager.default.attributesOfItem(atPath: original.path)[.systemFileNumber] as? NSNumber
        let result = try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination)
        XCTAssertTrue(result.moved)
        XCTAssertEqual(result.fileCount, 1)
        XCTAssertFalse(FileManager.default.fileExists(atPath: legacy.path))
        let current = destination.appendingPathComponent(name)
        XCTAssertEqual(try Data(contentsOf: current), bytes)
        XCTAssertEqual(try FileManager.default.attributesOfItem(atPath: current.path)[.systemFileNumber] as? NSNumber, inode)
        XCTAssertEqual(try permissions(destination), 0o700)
        XCTAssertEqual(try permissions(current), 0o600)
    }

    func testRepeatedOpenKeepsTheAlreadyMovedBytesAndFilename() throws {
        let (root, legacy, destination) = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: legacy, withIntermediateDirectories: false)
        try Data("original".utf8).write(to: legacy.appendingPathComponent("selected.yaml"))
        _ = try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination)
        let before = try Data(contentsOf: destination.appendingPathComponent("selected.yaml"))
        let reopened = try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination)
        XCTAssertFalse(reopened.moved)
        XCTAssertEqual(reopened.fileCount, 1)
        XCTAssertEqual(try Data(contentsOf: destination.appendingPathComponent("selected.yaml")), before)
    }

    func testConflictingDestinationPreservesBothOriginalSettingsStores() throws {
        let (root, legacy, destination) = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: legacy, withIntermediateDirectories: false)
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
        try Data("active-old".utf8).write(to: legacy.appendingPathComponent("selected.yml"))
        try Data("existing-private".utf8).write(to: destination.appendingPathComponent("selected.yml"))
        XCTAssertThrowsError(try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination)) {
            XCTAssertEqual($0 as? PinkhaPrivateDirectoryMigration.Failure, .destinationConflict)
        }
        XCTAssertEqual(try Data(contentsOf: legacy.appendingPathComponent("selected.yml")), Data("active-old".utf8))
        XCTAssertEqual(try Data(contentsOf: destination.appendingPathComponent("selected.yml")), Data("existing-private".utf8))
    }

    func testSourceSymlinkIsRefusedWithoutMovingItsTarget() throws {
        let (root, legacy, destination) = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let target = root.appendingPathComponent("original-target", isDirectory: true)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: false)
        try Data("unchanged".utf8).write(to: target.appendingPathComponent("net.yml"))
        try FileManager.default.createSymbolicLink(at: legacy, withDestinationURL: target)
        XCTAssertThrowsError(try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination))
        XCTAssertEqual(try Data(contentsOf: target.appendingPathComponent("net.yml")), Data("unchanged".utf8))
        XCTAssertFalse(FileManager.default.fileExists(atPath: destination.path))
    }

    func testPrivateParentSymlinkIsRefusedBeforeAnyMove() throws {
        let (root, legacy, destination) = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: legacy, withIntermediateDirectories: false)
        try Data("unchanged".utf8).write(to: legacy.appendingPathComponent("net.yml"))
        let external = root.appendingPathComponent("different-target", isDirectory: true)
        try FileManager.default.createDirectory(at: external, withIntermediateDirectories: false)
        try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("Library"), withDestinationURL: external)
        XCTAssertThrowsError(try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination))
        XCTAssertEqual(try Data(contentsOf: legacy.appendingPathComponent("net.yml")), Data("unchanged".utf8))
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: external.path), [])
    }

    func testUnexpectedNestedDirectoryKeepsOriginalTreeIntact() throws {
        let (root, legacy, destination) = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: legacy.appendingPathComponent("unexpected"), withIntermediateDirectories: true)
        try Data("original".utf8).write(to: legacy.appendingPathComponent("net.yml"))
        XCTAssertThrowsError(try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination)) {
            XCTAssertEqual($0 as? PinkhaPrivateDirectoryMigration.Failure, .unsupportedEntry)
        }
        XCTAssertTrue(FileManager.default.fileExists(atPath: legacy.appendingPathComponent("unexpected").path))
        XCTAssertEqual(try Data(contentsOf: legacy.appendingPathComponent("net.yml")), Data("original".utf8))
        XCTAssertFalse(FileManager.default.fileExists(atPath: destination.path))
    }

    func testNewInstallationCreatesOnlyThePrivateSettingsDirectory() throws {
        let (root, legacy, destination) = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let result = try PinkhaPrivateDirectoryMigration.prepare(legacy: legacy, destination: destination)
        XCTAssertFalse(result.moved)
        XCTAssertEqual(result.fileCount, 0)
        XCTAssertFalse(FileManager.default.fileExists(atPath: legacy.path))
        XCTAssertEqual(try permissions(destination), 0o700)
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: destination.path), [])
    }

    private func permissions(_ url: URL) throws -> Int? {
        (try FileManager.default.attributesOfItem(atPath: url.path)[.posixPermissions] as? NSNumber)?.intValue
    }
}
