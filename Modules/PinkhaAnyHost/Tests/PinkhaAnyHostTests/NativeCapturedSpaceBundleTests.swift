import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// One actual native fixture from the independently retained Go producer. The
/// private originals are supplied explicitly; no account IDs or text are logged.
final class NativeCapturedSpaceBundleTests: XCTestCase {
    func testOriginalNativeCapturedSpaceAndJSONViewsCrossTheSwiftBoundary() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_NATIVE_CAPTURE_FIXTURE"] else {
            throw XCTSkip("An independently retained private native capture is required")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let pieces = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !pieces.isEmpty, !relative.hasPrefix("/"), !relative.contains("\\"),
                  !relative.contains("\0"), pieces.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw FixtureError.invalidPath
            }
            let candidate = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard candidate.path.hasPrefix(directory.path + "/"),
                  try candidate.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw FixtureError.invalidPath
            }
            return try Data(contentsOf: candidate, options: [.mappedIfSafe])
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == "5357d52f5e76b604a40d7a5f2b1bc002e19bc864c419a45f90128bfa965d5850" else {
            throw FixtureError.changedOriginal
        }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        guard context["format"]?.string == "pinkha-native-source-fixture-context-v1",
              context["runId"]?.string == "45472745870",
              context["controllerSHA"]?.string == "fb5b40a5e91c68520d0f2921600a9f04b1e25439",
              context["nativeSourceSHA"]?.string == "d2696b36d169f57f1bcb03c055384e5ec944d930",
              context["identityOrigin"]?.string == "original-native-account-directory-and-source-witness-binding",
              context["originalCommandReceiptSHA256"]?.string == "71f4f64ba71f9e3d4e2687576a05e499e3f165d46349e9ccd138ed813a27eb5c",
              context["originalJSONReceiptSHA256"]?.string == "b3c5f92d6884a6f571223a639c23d3f933b886d67b2b80500518d9506f9e1753",
              let account = context["sourceAccountID"]?.string,
              let space = context["sourceSpaceID"]?.string,
              context["bundleRelativePath"]?.string == "source-bundle",
              context["bundleManifestName"]?.string == "manifest.json" else {
            throw FixtureError.invalidContext
        }
        let directory = root.appendingPathComponent("source-bundle", isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        guard AnyContentDigest.sha256(manifest) == "2a1a02987204321aaa1c8cf9f0c7f413f4b50dbce87280d82499c4f9bc7be238" else {
            throw FixtureError.changedOriginal
        }
        var consumed = Set<String>()
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: account, sourceSpaceID: space) { member in
            guard consumed.insert(member.path).inserted else { throw FixtureError.duplicateRead }
            return try bytes(member.path, under: directory)
        }
        XCTAssertEqual(bundle.objects.count, 144)
        XCTAssertEqual(bundle.trees.count, 145)
        XCTAssertEqual(bundle.verifiedMembers.count, 291)
        XCTAssertEqual(consumed, Set(bundle.verifiedMembers.map(\.path)))
        XCTAssertEqual(bundle.fileVariants.count, 1)
        XCTAssertEqual(bundle.sourceRows.sha256, "7322c6bafb98588b09695a79e9bd56ab52e41915cf2fe3d27869a663bef125f2")
        XCTAssertTrue(bundle.sourceAccountID == account && bundle.sourceSpaceID == space,
                      "Captured identities must agree with the original private context")
        XCTAssertEqual(bundle.receipt["Source"]?["accountDirectorySHA256"], context["originalAccountDirectorySHA256"])
        var typeCounts: [Int64: Int] = [:]
        for object in bundle.objects { typeCounts[object.nativeType, default: 0] += 1 }
        XCTAssertEqual(typeCounts, [521: 119, 528: 19, 16: 1, 48: 1, 112: 1, 32: 1, 533: 1, 518: 1])

        let sample = try XCTUnwrap(context["nativeJSONSample"])
        let sampleHash = try XCTUnwrap(sample["objectSHA256"]?.string)
        let view = try XCTUnwrap(bundle.objects.first {
            AnyContentDigest.sha256(Data($0.sourceObjectID.utf8)) == sampleHash
        })
        XCTAssertEqual(view.snapshotSHA256, sample["protobufSHA256"]?.string)
        XCTAssertEqual(view.viewSHA256, sample["jsonSHA256"]?.string)
        XCTAssertTrue(view.protobufBytes == (try bytes(try XCTUnwrap(sample["protobufPath"]?.string), under: directory)),
                      "Original native protobuf bytes must be retained verbatim")
        XCTAssertTrue(view.jsonViewBytes == (try bytes(try XCTUnwrap(sample["jsonPath"]?.string), under: directory)),
                      "Original native JSON bytes must be retained verbatim")
        XCTAssertTrue(view.details["name"] == sample["expectedTitle"], "Captured Unicode title differs")
        XCTAssertEqual(view.rawSnapshot["fileInfo"], .null)
        XCTAssertEqual(view.rawSnapshot["fileKeys"], .null)
        let bodyID = try XCTUnwrap(sample["expectedTextBlockID"]?.string)
        let block = try XCTUnwrap(view.blocks.first { $0.id == bodyID })
        XCTAssertEqual(block.contentKind, "text")
        XCTAssertTrue(block.content?["text"] == sample["expectedText"], "Native visible Unicode text differs")
        XCTAssertEqual(block.content?["style"], sample["expectedTextStyle"])
        let projected = try block.inlineProjection()
        XCTAssertTrue(projected.text == sample["expectedText"]?.string, "UTF-16 projection changed visible text")
        XCTAssertEqual(projected.marks.count, sample["expectedMarks"]?.array?.count)
        XCTAssertEqual(projected.sourceSHA256, AnyContentDigest.sha256(Data(projected.text.utf8)))
        XCTAssertTrue(view.depthFirstIDs.contains(bodyID), "Actual native body must remain in the source hierarchy")

        // Preserve this original producer's known namespace gap and its explicit
        // non-admission flags. A reader cannot silently repair or promote them.
        XCTAssertEqual(bundle.resolverUnmapped.count, 143)
        XCTAssertTrue(bundle.issues.contains { $0.code == "closed-resolver-unmapped" })
        for flag in ["CurrentFilePayloadCompleteness", "SemanticCompleteness",
                     "HistorySemanticsValidated", "HasNativeSourceAdmission", "PermitsDestinationWrites"] {
            XCTAssertEqual(bundle.receipt[flag]?.bool, false, flag)
        }
        XCTAssertEqual(bundle.receipt["AccountSessionAuthorizedAtFinalCapture"]?.bool, true)
        XCTAssertEqual(bundle.receipt["AllNativeHeadRowsAccounted"]?.bool, true)
        XCTAssertEqual(bundle.receipt["CapturedSnapshotsBoundToUnchangedCheckpoint"]?.bool, true)
        XCTAssertEqual(bundle.receipt["OriginalNativeHistoryRowsRetained"]?.bool, true)
        for member in bundle.verifiedMembers {
            let original = try bytes(member.path, under: directory)
            XCTAssertEqual(original.count, member.byteCount)
            XCTAssertEqual(AnyContentDigest.sha256(original), member.sha256)
        }
        XCTAssertEqual(AnyContentDigest.sha256(try bytes("manifest.json", under: directory)), bundle.manifestSHA256)
        XCTAssertEqual(AnyContentDigest.sha256(try bytes("fixture-context.json", under: root)), AnyContentDigest.sha256(contextBytes))
        print("NATIVE_CAPTURE_SWIFT_VERIFIED snapshots=144 trees=145 members=291 fileVariants=1 rawBytesUnchanged=true namespaceGapsRetained=143 destinationWrites=false manifestSHA256=\(bundle.manifestSHA256)")
    }

    private enum FixtureError: Error {
        case invalidPath, invalidContext, changedOriginal, duplicateRead
    }
}
