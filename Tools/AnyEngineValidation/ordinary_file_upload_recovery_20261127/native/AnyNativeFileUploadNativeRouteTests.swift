import Foundation
import XCTest
import PinkhaAnyEngine

/// A separately selected, actual-native route proof. The component controller
/// may compile this complete file, but its thirty-method filter does not run it.
/// The native controller alone creates its fresh synthetic account and inputs.
final class AnyNativeFileUploadNativeRouteTests: XCTestCase, @unchecked Sendable {
    func testOriginalNativeAttachResolvesMetadataAndVerifiesInlineAndFullTierBytes() async throws {
        let environment = ProcessInfo.processInfo.environment
        let inputPath = try XCTUnwrap(environment["PINKHA_ORDINARY_NATIVE_UPLOAD_INPUT"])
        let inputURL = URL(fileURLWithPath: inputPath)
        guard inputPath.hasPrefix("/"), inputURL.resolvingSymlinksInPath().path == inputURL.path else {
            throw NativeUploadProofError.invalidInputs
        }
        let inputHandle = try FileHandle(forReadingFrom: inputURL)
        defer { try? inputHandle.close() }
        let inputBytes = try inputHandle.read(upToCount: 16_385) ?? Data()
        guard !inputBytes.isEmpty, inputBytes.count <= 16_384 else {
            throw NativeUploadProofError.invalidInputs
        }
        let input = try JSONDecoder().decode(NativeUploadInput.self, from: inputBytes)
        guard input.schema == 1, input.files.count == 2,
              input.files.map(\.label) == ["empty-inline", "sniffed-png-full"],
              input.files.map(\.relativePath) == ["empty.bin", "generated.png"],
              input.files[0].byteCount == 0, input.files[0].inline,
              (4_096...1_048_576).contains(input.files[1].byteCount), !input.files[1].inline,
              input.files[0].expectedMIME.isEmpty,
              input.files[1].expectedMIME == "image/png",
              input.files[1].mimeHint == "application/octet-stream",
              input.files[1].expectedName == input.files[1].nameHint + ".png",
              !input.files[1].nameHint.contains(".") else {
            throw NativeUploadProofError.invalidInputs
        }
        let root = inputURL.deletingLastPathComponent()
        let records = NativeUploadObservations(root: root)
        let endpoint = try XCTUnwrap(URL(string: input.baseURL))
        let authorization = try input.controlToken.map(AnyHTTPAuthorization.init(token:))
        let client = try AnyHTTPClient(baseURL: endpoint, expectedAccountID: input.accountID,
                                       authorization: authorization)
        let uploader = AnyNativeFileUploader(client: client)
        let currentOwner: @Sendable () async throws -> Void = {
            let member = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", input.spaceID, "members", "me"], maximumResponseBytes: 16_384)
            guard member["identity"]?.string?.utf8.elementsEqual(input.accountID.utf8) == true,
                  member["status"]?.string == "active", member["permission"]?.string == "owner" else {
                throw NativeUploadProofError.scopeChanged
            }
        }
        try await currentOwner()
        var fileIDs = Set<String>()
        for source in input.files {
            guard source.relativePath == "empty.bin" || source.relativePath == "generated.png" else {
                throw NativeUploadProofError.invalidInputs
            }
            let fileURL = root.appendingPathComponent(source.relativePath)
            guard fileURL.resolvingSymlinksInPath().path == fileURL.path else {
                throw NativeUploadProofError.invalidInputs
            }
            let fingerprint = try await AnyNativeFileUploader.fingerprint(fileURL: fileURL)
            XCTAssertEqual(fingerprint.byteCount, source.byteCount)
            XCTAssertEqual(fingerprint.sha256, source.sha256)
            let specification = try AnyNativeFileUploadSpecification(accountID: input.accountID,
                spaceID: input.spaceID, objectID: input.objectID,
                name: source.nameHint, mime: source.mimeHint,
                size: source.byteCount, contentSHA256: source.sha256)
            let admitted = NativeUploadOneShot()
            let result: AnyNativeAttachedFile
            do {
                result = try await uploader.attach(specification: specification, fileURL: fileURL,
                    validateScope: currentOwner,
                    authorizeDispatch: {
                        try await currentOwner()
                        try await admitted.admit()
                    }, retainReceipt: { receipt in
                        // This is an observational test ledger, not a replacement
                        // for the production protected creation journal.
                        try await records.acknowledge(source.label, receipt: receipt)
                    })
            } catch {
                let originalError = error
                do { try await records.failed(source.label) }
                catch { XCTFail("Native failure observation could not be retained") }
                throw originalError
            }
            XCTAssertTrue(fileIDs.insert(result.reference.fileID).inserted)
            XCTAssertEqual(result.reference.accountID, input.accountID)
            XCTAssertEqual(result.reference.spaceID, input.spaceID)
            XCTAssertEqual(result.reference.objectID, input.objectID)
            XCTAssertEqual(result.byteCount, source.byteCount)
            XCTAssertEqual(result.name, source.expectedName)
            XCTAssertEqual(result.mime, source.expectedMIME)
            XCTAssertEqual(result.inline, source.inline)
            XCTAssertTrue(result.cached)
            if source.inline {
                XCTAssertNil(result.rootCID)
                XCTAssertTrue(result.durable)
            } else {
                XCTAssertFalse(try XCTUnwrap(result.rootCID).isEmpty)
                // No cloud fleet is configured for this new owned fixture.
                XCTAssertFalse(result.durable)
            }
            let first = try await uploader.info(specification: specification,
                fileID: result.reference.fileID, authorize: currentOwner)
            try sameMetadata(result, first)
            let content = try await client.readFileContentDigest(spaceID: input.spaceID,
                fileID: result.reference.fileID, size: source.byteCount, mime: result.mime,
                authorize: currentOwner)
            XCTAssertEqual(content.byteCount, source.byteCount)
            XCTAssertEqual(content.sha256, source.sha256)
            let second = try await uploader.info(specification: specification,
                fileID: result.reference.fileID, authorize: currentOwner)
            try sameMetadata(first, second)
            XCTAssertTrue(second.cached)
            let approvals = await admitted.count
            XCTAssertEqual(approvals, 1)
            try await records.verified(source.label, receipt: second, digest: content.sha256)
        }
        XCTAssertEqual(fileIDs.count, 2)
        try await currentOwner()
        try await records.complete()
    }

    private func sameMetadata(_ first: AnyNativeAttachedFile, _ second: AnyNativeAttachedFile) throws {
        guard first.reference.accountID.utf8.elementsEqual(second.reference.accountID.utf8),
              first.reference.spaceID.utf8.elementsEqual(second.reference.spaceID.utf8),
              first.reference.objectID.utf8.elementsEqual(second.reference.objectID.utf8),
              first.reference.fileID.utf8.elementsEqual(second.reference.fileID.utf8),
              first.byteCount == second.byteCount, first.inline == second.inline,
              first.name.utf8.elementsEqual(second.name.utf8),
              first.mime.utf8.elementsEqual(second.mime.utf8) else {
            throw NativeUploadProofError.metadataChanged
        }
        switch (first.rootCID, second.rootCID) {
        case (nil, nil): break
        case (.some(let a), .some(let b)) where a.utf8.elementsEqual(b.utf8): break
        default: throw NativeUploadProofError.metadataChanged
        }
    }
}

private enum NativeUploadProofError: Error {
    case invalidInputs, scopeChanged, secondDispatch, metadataChanged, incompleteReceipt
}

private struct NativeUploadInput: Decodable, Sendable {
    let schema: Int
    let baseURL: String
    let controlToken: String?
    let accountID: String
    let spaceID: String
    let objectID: String
    let files: [NativeUploadSource]
}

private struct NativeUploadSource: Decodable, Sendable {
    let label: String
    let relativePath: String
    let byteCount: Int64
    let sha256: String
    let nameHint: String
    let mimeHint: String
    let expectedName: String
    let expectedMIME: String
    let inline: Bool
}

private actor NativeUploadOneShot {
    private(set) var count = 0
    func admit() throws {
        guard count == 0 else { throw NativeUploadProofError.secondDispatch }
        count += 1
    }
}

private actor NativeUploadObservations {
    private let root: URL
    private var rows: [AnyJSON] = []
    init(root: URL) { self.root = root }

    func acknowledge(_ label: String, receipt: AnyNativeAttachedFile) throws {
        rows.append(.object(["stage": .string("acknowledged"), "label": .string(label),
            "fileID": .string(receipt.reference.fileID), "byteCount": .integer(receipt.byteCount),
            "name": .string(receipt.name), "mime": .string(receipt.mime),
            "inline": .bool(receipt.inline), "cached": .bool(receipt.cached),
            "durable": .bool(receipt.durable), "rootCID": receipt.rootCID.map(AnyJSON.string) ?? .null]))
        try save("IN_PROGRESS")
    }

    func verified(_ label: String, receipt: AnyNativeAttachedFile, digest: String) throws {
        rows.append(.object(["stage": .string("verified"), "label": .string(label),
            "fileID": .string(receipt.reference.fileID), "byteCount": .integer(receipt.byteCount),
            "contentSHA256": .string(digest)]))
        try save("IN_PROGRESS")
    }

    func failed(_ label: String) throws {
        rows.append(.object(["stage": .string("failed"), "label": .string(label)]))
        try save("FAILED")
    }

    func complete() throws {
        guard rows.count == 4,
              rows.map({ $0["stage"]?.string }) == ["acknowledged", "verified", "acknowledged", "verified"] else {
            throw NativeUploadProofError.incompleteReceipt
        }
        try save("NATIVE_ROUTE_OBSERVED_REQUIRES_XCTEST_AND_CONTROLLER_QUALIFICATION")
    }

    private func save(_ status: String) throws {
        guard rows.count <= 6 else { throw NativeUploadProofError.incompleteReceipt }
        let value: AnyJSON = .object(["schema": .integer(1), "status": .string(status),
            "productionJournalQualified": .bool(false), "cloudQualified": .bool(false),
            "rows": .array(rows)])
        let data = try JSONEncoder().encode(value)
        guard data.count <= 16_384 else { throw NativeUploadProofError.incompleteReceipt }
        try data.write(to: root.appendingPathComponent("swift-native-observations.json"), options: .atomic)
    }
}
