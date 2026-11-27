import Foundation
import Crypto
import XCTest
@testable import PinkhaAnyEngine
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

final class AnyNativeFileUploadTests: XCTestCase, @unchecked Sendable {
    func testPublicFingerprintBuildsAnIntentWithoutWholeFileLoadingAndChangedSelectionIsRefused() async throws {
        let files = try UploadTestFiles()
        defer { files.remove() }
        for count in [0, 2 * AnyNativeFileUploadStaging.chunkByteCount + 17] {
            let source = try files.write(byteCount: count)
            let fingerprint = try await AnyNativeFileUploader.fingerprint(fileURL: source.url)
            XCTAssertEqual(fingerprint.byteCount, Int64(count))
            XCTAssertEqual(fingerprint.sha256, source.sha256)
            let specification = try uploadSpecification(size: fingerprint.byteCount, digest: fingerprint.sha256)
            let staged = try AnyNativeFileUploadStaging.copy(source: source.url, specification: specification)
            staged.finish()
            let link = files.directory.appendingPathComponent(UUID().uuidString)
            try FileManager.default.createSymbolicLink(at: link, withDestinationURL: source.url)
            do { _ = try await AnyNativeFileUploader.fingerprint(fileURL: link); XCTFail("A selected symlink was followed") }
            catch { XCTAssertEqual(error as? AnyNativeFileUploadError, .invalidSource) }
            let handle = try FileHandle(forWritingTo: source.url)
            try handle.write(contentsOf: Data([0x99])); try handle.close()
            XCTAssertThrowsError(try AnyNativeFileUploadStaging.copy(source: source.url, specification: specification))
        }
        let source = try files.write(byteCount: 12)
        let cancelled = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try await AnyNativeFileUploader.fingerprint(fileURL: source.url)
        }
        do { _ = try await cancelled.value; XCTFail("Cancelled fingerprint returned data") }
        catch { XCTAssertTrue(error is CancellationError) }
    }

    func testSpecificationIncludesEmptyInlineFilesAndRejectsUnsafeOrUnboundedInputs() throws {
        for size in [Int64(0), 4_095, 4_096, AnyNativeFileUploadSpecification.maximumByteCount] {
            let value = try uploadSpecification(size: size)
            XCTAssertEqual(value.size, size)
        }
        for size in [Int64(-1), AnyNativeFileUploadSpecification.maximumByteCount + 1] {
            XCTAssertThrowsError(try uploadSpecification(size: size))
        }
        for digest in ["", String(repeating: "0", count: 63), String(repeating: "A", count: 64), String(repeating: "g", count: 64)] {
            XCTAssertThrowsError(try uploadSpecification(digest: digest))
        }
        for name in ["bad\nname", "bad\u{0000}name", String(repeating: "n", count: 8_193)] {
            XCTAssertThrowsError(try uploadSpecification(name: name))
        }
        for mime in ["image/png\r\nX-Test: injected", String(repeating: "a", count: 1_025), "טקסט"] {
            XCTAssertThrowsError(try uploadSpecification(mime: mime))
        }
        for bad in ["", ".", "..", "foreign/space", "foreign%2Fspace", "space\u{0000}"] {
            XCTAssertThrowsError(try AnyNativeFileUploadSpecification(accountID: "account", spaceID: bad,
                objectID: "object", name: "", mime: "", size: 0, contentSHA256: uploadDigest(Data())))
        }
    }

    func testNativeReceiptPreservesResolvedMetadataAndKeepsInlineCustodyDistinct() throws {
        let hint = try uploadSpecification(name: "screenshot", mime: "application/octet-stream", size: 12)
        let resolved = try AnyNativeAttachedFile(native: uploadBody(size: 12, name: "screenshot.png", mime: "image/png"),
            specification: hint)
        XCTAssertEqual(resolved.name, "screenshot.png")
        XCTAssertEqual(resolved.mime, "image/png")
        XCTAssertEqual(resolved.reference.accountID, "account")
        XCTAssertEqual(resolved.reference.spaceID, "space")
        XCTAssertEqual(resolved.reference.objectID, "object")
        XCTAssertEqual(resolved.reference.fileID, "file")
        XCTAssertEqual(resolved.byteCount, 12)
        XCTAssertTrue(resolved.inline)
        XCTAssertTrue(resolved.durable)
        XCTAssertNil(resolved.rootCID)
        XCTAssertFalse(String(describing: resolved).contains("screenshot"))

        let maximumHint = String(repeating: "x", count: 8_192)
        let maximum = try uploadSpecification(name: maximumHint, mime: "image/png", size: 12)
        let extended = try AnyNativeAttachedFile(native: uploadBody(size: 12, name: maximumHint + ".png", mime: "image/png"),
            specification: maximum)
        XCTAssertEqual(extended.name.utf8.count, 8_196)
        XCTAssertThrowsError(try AnyNativeAttachedFile(native: uploadBody(size: 12,
            name: String(repeating: "x", count: 16_385)), specification: maximum))

        var empty = uploadBody(size: 0).object!
        empty.removeValue(forKey: "name"); empty.removeValue(forKey: "mime")
        let zero = try AnyNativeAttachedFile(native: .object(empty), specification: uploadSpecification(size: 0))
        XCTAssertEqual(zero.name, ""); XCTAssertEqual(zero.mime, "")

        var external = uploadBody(size: 8_192, inline: false).object!
        external["cached"] = .bool(false)
        let uncached = try AnyNativeAttachedFile(native: .object(external), specification: uploadSpecification(size: 8_192))
        XCTAssertFalse(uncached.inline); XCTAssertFalse(uncached.durable); XCTAssertFalse(uncached.cached)
        XCTAssertEqual(uncached.rootCID, "native-root")
    }

    func testReceiptRejectsForeignIdentityVariantsAndMalformedStorage() throws {
        let specification = try uploadSpecification(size: 12)
        let baseline = uploadBody(size: 12).object!
        let changes: [(String, AnyJSON)] = [
            ("objectId", .string("different-object")), ("fileId", .string("bad/file")),
            ("size", .integer(13)), ("size", .number(12.5)), ("size", .bool(true)),
            ("inline", .null), ("durable", .bool(false)), ("cached", .bool(false)),
            ("rootCid", .string("root-on-inline")), ("rootCid", .null),
            ("variant", .string("thumb")), ("variantOf", .string("other-file")),
            ("name", .null), ("mime", .string("image/png\r\n")),
            ("spaceId", .string("foreign")), ("accountId", .string("foreign"))
        ]
        for (key, value) in changes {
            var row = baseline; row[key] = value
            XCTAssertThrowsError(try AnyNativeAttachedFile(native: .object(row), specification: specification), key)
        }
        XCTAssertThrowsError(try AnyNativeAttachedFile(native: .null, specification: specification))
        XCTAssertThrowsError(try AnyNativeAttachedFile(native: .object(baseline), specification: specification, expectedFileID: "other"))
        var external = uploadBody(size: 12, inline: false).object!
        external.removeValue(forKey: "rootCid")
        XCTAssertThrowsError(try AnyNativeAttachedFile(native: .object(external), specification: specification))

        let composed = "object-\u{00E9}", decomposed = "object-e\u{0301}"
        XCTAssertEqual(composed, decomposed)
        var unicode = baseline; unicode["objectId"] = .string(decomposed)
        let exact = try AnyNativeFileUploadSpecification(accountID: "account", spaceID: "space",
            objectID: composed, name: "", mime: "", size: 12, contentSHA256: uploadDigest(Data()))
        XCTAssertThrowsError(try AnyNativeAttachedFile(native: .object(unicode), specification: exact))
    }

    func testVerifiedStagingStreamsSeveralChunksAndCleansOnlyItsOwnPrivateCopy() throws {
        let files = try UploadTestFiles()
        defer { files.remove() }
        for count in [0, 3 * AnyNativeFileUploadStaging.chunkByteCount + 17] {
            let source = try files.write(byteCount: count)
            let specification = try uploadSpecification(size: Int64(count), digest: source.sha256)
            let staged = try AnyNativeFileUploadStaging.copy(source: source.url, specification: specification)
            let copy = staged.fileURL
            let attributes = try FileManager.default.attributesOfItem(atPath: copy.path)
            let parent = try FileManager.default.attributesOfItem(atPath: copy.deletingLastPathComponent().path)
            XCTAssertEqual((attributes[.posixPermissions] as? NSNumber)?.intValue, 0o600)
            XCTAssertEqual((parent[.posixPermissions] as? NSNumber)?.intValue, 0o700)
            XCTAssertEqual(try files.digest(copy), source.sha256)
            try staged.requireUnchangedSourceAndCopy()
            staged.finish(); staged.finish()
            XCTAssertFalse(FileManager.default.fileExists(atPath: copy.path))
            XCTAssertFalse(FileManager.default.fileExists(atPath: copy.deletingLastPathComponent().path))
            XCTAssertEqual(try files.digest(source.url), source.sha256)
        }
    }

    func testSourceSymlinkWrongDigestReplacementAndChangedCopyCannotBeDispatched() throws {
        let files = try UploadTestFiles()
        defer { files.remove() }
        let source = try files.write(byteCount: 8_193)
        let specification = try uploadSpecification(size: 8_193, digest: source.sha256)
        let link = files.directory.appendingPathComponent("source-link")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: source.url)
        XCTAssertThrowsError(try AnyNativeFileUploadStaging.copy(source: link, specification: specification))
        XCTAssertThrowsError(try AnyNativeFileUploadStaging.copy(source: files.directory, specification: specification))
        let wrong = try uploadSpecification(size: 8_193, digest: String(repeating: "0", count: 64))
        XCTAssertThrowsError(try AnyNativeFileUploadStaging.copy(source: source.url, specification: wrong)) { error in
            XCTAssertEqual(error as? AnyNativeFileUploadError, .contentMismatch)
        }

        let staged = try AnyNativeFileUploadStaging.copy(source: source.url, specification: specification)
        defer { staged.finish() }
        try Data([0x42]).write(to: source.url, options: .atomic)
        XCTAssertThrowsError(try staged.requireUnchangedSourceAndCopy()) { error in
            XCTAssertEqual(error as? AnyNativeFileUploadError, .sourceChanged)
        }
        // Its already verified copy remains separate from the changed source.
        XCTAssertEqual(try files.digest(staged.fileURL), source.sha256)
        try Data([0x43]).write(to: staged.fileURL)
        XCTAssertThrowsError(try staged.requireUnchangedCopy())
    }
}

func uploadSpecification(name: String = "source.bin", mime: String = "application/octet-stream",
                         size: Int64 = 0, digest: String = String(repeating: "0", count: 64),
                         account: String = "account") throws -> AnyNativeFileUploadSpecification {
    try .init(accountID: account, spaceID: "space", objectID: "object", name: name,
              mime: mime, size: size, contentSHA256: digest)
}

func uploadBody(size: Int64, name: String = "source.bin", mime: String = "application/octet-stream",
                inline: Bool = true) -> AnyJSON {
    var value: [String: AnyJSON] = ["fileId": .string("file"), "objectId": .string("object"),
        "size": .integer(size), "inline": .bool(inline), "durable": .bool(inline), "cached": .bool(true),
        "name": .string(name), "mime": .string(mime)]
    if !inline { value["rootCid"] = .string("native-root") }
    return .object(value)
}

func uploadDigest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }

final class UploadTestFiles: @unchecked Sendable {
    let directory: URL
    init(parent: URL? = nil) throws {
        directory = (parent ?? FileManager.default.temporaryDirectory).appendingPathComponent("pinkha-upload-test-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
    }

    func write(byteCount: Int) throws -> (url: URL, sha256: String) {
        let path = directory.appendingPathComponent(UUID().uuidString + ".bin")
        guard FileManager.default.createFile(atPath: path.path, contents: nil, attributes: [.posixPermissions: 0o600]) else {
            throw AnyNativeFileUploadError.ioFailure
        }
        let handle = try FileHandle(forWritingTo: path)
        defer { try? handle.close() }
        var remaining = byteCount, hash = SHA256()
        let chunk = Data((0..<65_536).map { UInt8(truncatingIfNeeded: $0) })
        while remaining > 0 {
            let part = chunk.prefix(min(chunk.count, remaining))
            try handle.write(contentsOf: part); hash.update(data: part); remaining -= part.count
        }
        try handle.synchronize()
        return (path, hash.finalize().map { String(format: "%02x", $0) }.joined())
    }

    func digest(_ path: URL) throws -> String {
        let handle = try FileHandle(forReadingFrom: path)
        defer { try? handle.close() }
        var hash = SHA256()
        while let data = try handle.read(upToCount: 65_536), !data.isEmpty { hash.update(data: data) }
        return hash.finalize().map { String(format: "%02x", $0) }.joined()
    }

    func removeChecked() throws { try FileManager.default.removeItem(at: directory) }
    func remove() { try? removeChecked() }
}
