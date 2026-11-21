import Foundation
import ProtobufMessages
import SwiftProtobuf
import Testing
@testable import AnytypeOriginalEditor

/// Transport/frame controls only. The ZIP fixture below was generated for
/// these tests; it is not an Anytype engine export or a Native editor witness.
@Suite
struct AnytypeOriginalEditorSnapshotTests {
    @Test
    func preservesUntouchedArchiveReportAndUnknownProtobufBytes() throws {
        let archive = try fixtureArchive()
        // succeed=1 plus unknown field 99=1. Keep these bytes exactly.
        let reportBytes = Data([0x10, 0x01, 0x98, 0x06, 0x01])
        let binding = try fixtureBinding()
        let framed = try AnytypeOriginalEditorSnapshot.frame(
            archive: archive, reportBytes: reportBytes, responseCount: 1,
            binding: binding, maximumBodyBytes: 65_536
        )
        let inspected = try AnytypeOriginalEditorSnapshot(
            bodyBytes: framed.bodyBytes, maximumBodyBytes: 65_536
        )
        #expect(inspected.bodyBytes == framed.bodyBytes)
        #expect(inspected.nativeArchiveBytes == archive)
        #expect(inspected.nativeExportReportBytes == reportBytes)
        #expect(inspected.nativeArchiveSHA256 == "75a87065ff66e6b3a827e1262c89c57b730040c4bc9e92ffe89a8814e90855cc")
        #expect(inspected.provenance.matchesCaptureBinding(binding))
        #expect(inspected.exportedObjectCount == 1)
    }

    @Test
    func rejectsChangedArchiveTruncationAndUnknownVersionWithoutRepairingInput() throws {
        let original = try fixtureSnapshot().bodyBytes
        var changed = original
        changed[changed.count - 1] ^= 0x01
        #expect(throws: AnytypeOriginalEditorSnapshotError.invalidArchive) {
            try AnytypeOriginalEditorSnapshot(bodyBytes: changed, maximumBodyBytes: 65_536)
        }
        var future = original
        future[11] = 2
        #expect(throws: AnytypeOriginalEditorSnapshotError.unsupportedVersion) {
            try AnytypeOriginalEditorSnapshot(bodyBytes: future, maximumBodyBytes: 65_536)
        }
        var hugeLength = original
        hugeLength.replaceSubrange(12..<16, with: [0xff, 0xff, 0xff, 0xff])
        #expect(throws: AnytypeOriginalEditorSnapshotError.invalidFrame) {
            try AnytypeOriginalEditorSnapshot(bodyBytes: hugeLength, maximumBodyBytes: 65_536)
        }
        #expect(throws: AnytypeOriginalEditorSnapshotError.invalidFrame) {
            try AnytypeOriginalEditorSnapshot(bodyBytes: Data(original.prefix(15)), maximumBodyBytes: 65_536)
        }
        #expect(original == (try fixtureSnapshot().bodyBytes))
    }

    @Test
    func rejectsUnknownVersionOneHeaderFieldsInsteadOfDroppingThem() throws {
        let framed = try fixtureSnapshot().bodyBytes
        let headerSize = (12..<16).reduce(0) { ($0 << 8) | Int(framed[$1]) }
        let originalHeader = framed.subdata(in: 16..<(16 + headerSize))
        var header = try #require(JSONSerialization.jsonObject(with: originalHeader) as? [String: Any])
        header["futureAuthority"] = "must-not-be-ignored"
        let newHeader = try JSONSerialization.data(withJSONObject: header, options: [.sortedKeys, .withoutEscapingSlashes])
        var changed = Data(framed.prefix(12))
        changed.append(contentsOf: [24, 16, 8, 0].map { UInt8(truncatingIfNeeded: UInt32(newHeader.count) >> $0) })
        changed.append(newHeader)
        changed.append(framed.suffix(from: 16 + headerSize))
        #expect(throws: AnytypeOriginalEditorSnapshotError.noncanonicalHeader) {
            try AnytypeOriginalEditorSnapshot(bodyBytes: changed, maximumBodyBytes: 65_536)
        }
    }

    @Test
    func refusesPartialFailedCanceledUnknownAndIssueBearingNativeReports() throws {
        let statuses: [Anytype_Model_ExportReport.Status] = [.partial, .failed, .canceled, .UNRECOGNIZED(99)]
        for status in statuses {
            var report = Anytype_Model_ExportReport()
            report.status = status
            report.succeed = 1
            #expect(throws: AnytypeOriginalEditorSnapshotError.incompleteExport) {
                try frameReport(report, responseCount: 1)
            }
        }
        var report = Anytype_Model_ExportReport()
        report.succeed = 1
        report.objectErrors = 1
        #expect(throws: AnytypeOriginalEditorSnapshotError.incompleteExport) { try frameReport(report, responseCount: 1) }
        report.objectErrors = 0
        report.fileErrors = 1
        #expect(throws: AnytypeOriginalEditorSnapshotError.incompleteExport) { try frameReport(report, responseCount: 1) }
        report.fileErrors = 0
        report.issues = [.with { $0.code = "unresolved_fidelity_warning" }]
        #expect(throws: AnytypeOriginalEditorSnapshotError.incompleteExport) { try frameReport(report, responseCount: 1) }
        report.issues = []
        #expect(throws: AnytypeOriginalEditorSnapshotError.incompleteExport) { try frameReport(report, responseCount: 2) }
        report.succeed = 0
        #expect(throws: AnytypeOriginalEditorSnapshotError.incompleteExport) { try frameReport(report, responseCount: 0) }
    }

    @Test
    func enforcesFrameBudgetIncludingMetadataWithoutTruncatingArchive() throws {
        let snapshot = try fixtureSnapshot()
        let archive = try fixtureArchive()
        #expect(throws: AnytypeOriginalEditorSnapshotError.bodyTooLarge) {
            try AnytypeOriginalEditorSnapshot(bodyBytes: snapshot.bodyBytes, maximumBodyBytes: snapshot.bodyBytes.count - 1)
        }
        #expect(throws: AnytypeOriginalEditorSnapshotError.bodyTooLarge) {
            try AnytypeOriginalEditorSnapshot.frame(
                archive: archive, reportBytes: Data([0x10, 0x01]), responseCount: 1,
                binding: fixtureBinding(), maximumBodyBytes: archive.count
            )
        }
        #expect(throws: AnytypeOriginalEditorSnapshotError.invalidLimit) {
            try AnytypeOriginalEditorSnapshot(bodyBytes: snapshot.bodyBytes, maximumBodyBytes: 65_537)
        }
        #expect(archive == (try fixtureArchive()))
    }

    @Test
    func captureProvenanceDoesNotNormalizeIDsOrBecomeNextRevisionAuthority() throws {
        let binding = try fixtureBinding(profile: "caf\u{00e9}", revision: 7)
        let snapshot = try AnytypeOriginalEditorSnapshot.frame(
            archive: fixtureArchive(), reportBytes: Data([0x10, 0x01]), responseCount: 1,
            binding: binding, maximumBodyBytes: 65_536
        )
        #expect(snapshot.provenance.matchesCaptureBinding(binding))
        #expect(!snapshot.provenance.matchesCaptureBinding(try fixtureBinding(profile: "cafe\u{0301}", revision: 7)))
        #expect(!snapshot.provenance.matchesCaptureBinding(try fixtureBinding(profile: "caf\u{00e9}", revision: 8)))
        // A future reopen can still inspect historical r=7; no r=8 binding is
        // fabricated from the body and no import is performed by decoding.
        let inspected = try AnytypeOriginalEditorSnapshot(bodyBytes: snapshot.bodyBytes, maximumBodyBytes: 65_536)
        #expect(inspected.provenance.capturedAgainstRevision == 7)
    }

    @Test
    func rejectsSymlinkEscapeAndOversizeReadsWhileRetainingOriginalBytes() throws {
        let owned = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        let outside = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        defer {
            try? FileManager.default.removeItem(at: owned)
            try? FileManager.default.removeItem(at: outside)
        }
        let archive = try fixtureArchive()
        let insideFile = owned.appendingPathComponent("owned.zip")
        let outsideFile = outside.appendingPathComponent("outside.zip")
        try archive.write(to: insideFile, options: .withoutOverwriting)
        try archive.write(to: outsideFile, options: .withoutOverwriting)
        #expect(try OriginalEditorArchiveFiles.readArchive(insideFile, in: owned, maximumBytes: 65_536) == archive)
        let sidecar = owned.appendingPathComponent("native-file.bin")
        try archive.write(to: sidecar, options: .withoutOverwriting)
        #expect(try OriginalEditorArchiveFiles.readOwnedRegularFile(sidecar, in: owned, maximumBytes: 65_536) == archive)
        let nested = try OriginalEditorArchiveFiles.makeOwnedDirectory(in: owned)
        #expect(nested.deletingLastPathComponent().path == owned.path)
        let linkedParent = owned.appendingPathComponent("redirect-parent", isDirectory: true)
        try FileManager.default.createSymbolicLink(at: linkedParent, withDestinationURL: outside)
        #expect(throws: AnytypeOriginalEditorSnapshotError.unsafeArchivePath) {
            try OriginalEditorArchiveFiles.makeOwnedDirectory(in: linkedParent)
        }
        #expect(throws: AnytypeOriginalEditorSnapshotError.unsafeArchivePath) {
            try OriginalEditorArchiveFiles.readArchive(sidecar, in: owned, maximumBytes: 65_536)
        }
        #expect(throws: AnytypeOriginalEditorSnapshotError.unsafeArchivePath) {
            try OriginalEditorArchiveFiles.readArchive(outsideFile, in: owned, maximumBytes: 65_536)
        }
        let link = owned.appendingPathComponent("redirect.zip")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: outsideFile)
        #expect(throws: (any Error).self) {
            try OriginalEditorArchiveFiles.readArchive(link, in: owned, maximumBytes: 65_536)
        }
        #expect(throws: AnytypeOriginalEditorSnapshotError.bodyTooLarge) {
            try OriginalEditorArchiveFiles.readArchive(insideFile, in: owned, maximumBytes: archive.count - 1)
        }
        #expect(try Data(contentsOf: insideFile) == archive)
        #expect(try Data(contentsOf: outsideFile) == archive)
    }

    private func frameReport(_ report: Anytype_Model_ExportReport, responseCount: Int32) throws -> AnytypeOriginalEditorSnapshot {
        try AnytypeOriginalEditorSnapshot.frame(
            archive: fixtureArchive(), reportBytes: report.serializedData(), responseCount: responseCount,
            binding: fixtureBinding(), maximumBodyBytes: 65_536
        )
    }

    private func fixtureSnapshot() throws -> AnytypeOriginalEditorSnapshot {
        try AnytypeOriginalEditorSnapshot.frame(
            archive: fixtureArchive(), reportBytes: Data([0x10, 0x01]), responseCount: 1,
            binding: fixtureBinding(), maximumBodyBytes: 65_536
        )
    }

    private func fixtureBinding(profile: String = "profile", revision: Int64 = 7) throws -> AnytypeOriginalEditorBinding {
        try AnytypeOriginalEditorBinding(
            accountID: "account", spaceID: "space", objectID: "object", hostProfileID: profile,
            annotationUUID: UUID(uuidString: "00000000-0000-4000-8000-000000000001")!,
            expectedRevision: revision, sourceWitnessSHA256: String(repeating: "a", count: 64)
        )
    }

    private func fixtureArchive() throws -> Data {
        try #require(Data(base64Encoded: "UEsDBBQAAAAAAAAAISj5oyeuDAAAAAwAAAAVAAAAb2JqZWN0cy9jb250cm9sbGVkLnBiCAESBQoDYWJjmAYBUEsDBBQAAAAAAAAAISiL5VXMCAAAAAgAAAAUAAAAZmlsZXMvY29udHJvbGxlZC5iaW4A/wECCg0AgFBLAQIUAxQAAAAAAAAAISj5oyeuDAAAAAwAAAAVAAAAAAAAAAAAAACAgQAAAABvYmplY3RzL2NvbnRyb2xsZWQucGJQSwECFAMUAAAAAAAAACEoi+VVzAgAAAAIAAAAFAAAAAAAAAAAAAAAgIE/AAAAZmlsZXMvY29udHJvbGxlZC5iaW5QSwUGAAAAAAIAAgCFAAAAeQAAAAAA"))
    }
}
