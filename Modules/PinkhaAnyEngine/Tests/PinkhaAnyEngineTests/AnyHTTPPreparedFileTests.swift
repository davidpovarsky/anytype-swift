import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyHTTPPreparedFileTests: XCTestCase {
    func testVerifiedPrivateSnapshotStreamsExactBytesAndDoesNotFollowSourceSymlink() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: directory) }
        let source = directory.appendingPathComponent("source")
        let copy = directory.appendingPathComponent("copy")
        let bytes = Data(repeating: 0xa7, count: 2 << 20)
        try bytes.write(to: source)
        try AnyHTTPClient.copyVerifiedMigrationFile(from: source, to: copy, size: Int64(bytes.count), digest: AnyContentDigest.sha256(bytes))
        try Data(repeating: 0xb8, count: bytes.count).write(to: source)
        XCTAssertEqual(try Data(contentsOf: copy), bytes, "the uploaded snapshot cannot change with its original")
        let alias = directory.appendingPathComponent("alias")
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: source)
        XCTAssertThrowsError(try AnyHTTPClient.copyVerifiedMigrationFile(from: alias, to: directory.appendingPathComponent("bad"), size: Int64(bytes.count), digest: AnyContentDigest.sha256(bytes)))
        XCTAssertThrowsError(try AnyHTTPClient.copyVerifiedMigrationFile(from: source, to: directory.appendingPathComponent("hash-mismatch"), size: Int64(bytes.count), digest: AnyContentDigest.sha256(bytes)))
        XCTAssertThrowsError(try AnyHTTPClient.copyVerifiedMigrationFile(from: source, to: directory.appendingPathComponent("size-mismatch"), size: Int64(bytes.count)+1, digest: AnyContentDigest.sha256(bytes)))
    }
}
