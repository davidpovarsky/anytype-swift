import Foundation
import CryptoKit
import Darwin
import ProtobufMessages
import SwiftProtobuf

/// A versioned, byte-preserving envelope around an original native protobuf ZIP.
/// Decoding checks this envelope; it does not import, authenticate the provenance,
/// resolve an object ID, select an account, or grant permission to edit anything.
public struct AnytypeOriginalEditorSnapshot: Sendable {
    public static let format = "anytype.native-protobuf-archive"
    public static let formatVersion: Int64 = 1

    public struct Provenance: Codable, Sendable {
        public let accountID: String
        public let spaceID: String
        public let objectID: String
        public let hostProfileID: String
        public let annotationUUID: UUID
        /// Historical pre-save revision, never authority for a later reopen.
        public let capturedAgainstRevision: Int64
        public let sourceWitnessSHA256: String
        /// Original native creation profile retained after a genuine selected-account
        /// read is framed for a different current Host. This is history, never
        /// account authority or permission to write to the original object.
        public let transportOriginHostProfileID: String?

        fileprivate init(binding: AnytypeOriginalEditorBinding,
                         transportOriginHostProfileID: String? = nil) {
            accountID = binding.accountID
            spaceID = binding.spaceID
            objectID = binding.objectID
            hostProfileID = binding.hostProfileID
            annotationUUID = binding.annotationUUID
            capturedAgainstRevision = binding.expectedRevision
            sourceWitnessSHA256 = binding.sourceWitnessSHA256
            self.transportOriginHostProfileID = transportOriginHostProfileID
        }

        /// Exact identity comparison for the host's captured pre-save context.
        /// A true result alone never establishes current source ownership.
        public func matchesCaptureBinding(_ binding: AnytypeOriginalEditorBinding) -> Bool {
            accountID.utf8.elementsEqual(binding.accountID.utf8)
                && spaceID.utf8.elementsEqual(binding.spaceID.utf8)
                && objectID.utf8.elementsEqual(binding.objectID.utf8)
                && hostProfileID.utf8.elementsEqual(binding.hostProfileID.utf8)
                && annotationUUID == binding.annotationUUID
                && capturedAgainstRevision == binding.expectedRevision
                && sourceWitnessSHA256 == binding.sourceWitnessSHA256
        }
    }

    /// These are the exact framed bytes supplied to the host's opaque rich body.
    public let bodyBytes: Data
    public let provenance: Provenance
    /// Untouched archive bytes; blocks and file entries are never reserialized.
    public let nativeArchiveBytes: Data
    public let nativeArchiveSHA256: String
    /// Original message serialized by SwiftProtobuf, including unknown fields.
    /// This is not a claim to retain the original RPC's wire field ordering.
    public let nativeExportReportBytes: Data
    public let exportedObjectCount: Int32

    private static let magic = Data([0x41, 0x54, 0x4f, 0x53, 0x4e, 0x41, 0x50, 0x00])
    private static let prefixByteCount = OriginalAnnotationPayloadBudget.framePrefixBytes
    private static let maximumHeaderBytes = OriginalAnnotationPayloadBudget.maximumHeaderBytes
    /// The host must also enforce its entire JSON/base64 envelope limit.
    private static let absoluteMaximumBodyBytes = OriginalAnnotationPayloadBudget.maximumBodyBytes

    private struct Header: Codable, Sendable {
        let archiveFormat: String
        let provenance: Provenance
        let archiveByteCount: Int
        let archiveSHA256: String
        let exportedObjectCount: Int32
        let exportReport: Data
    }

    /// Inspect only the explicitly supported version. Callers retain unknown
    /// rich-body versions unchanged; this initializer never rewrites them.
    public init(bodyBytes: Data, maximumBodyBytes: Int) throws {
        try Self.validateLimit(maximumBodyBytes)
        guard bodyBytes.count <= maximumBodyBytes else {
            throw AnytypeOriginalEditorSnapshotError.bodyTooLarge
        }
        guard bodyBytes.count >= Self.prefixByteCount,
              bodyBytes.prefix(Self.magic.count) == Self.magic else {
            throw AnytypeOriginalEditorSnapshotError.invalidFrame
        }
        // Rebase Data's indices so sliced input cannot change integer offsets.
        let bytes = Data(bodyBytes)
        guard Self.readUInt32(bytes, at: 8) == UInt32(Self.formatVersion) else {
            throw AnytypeOriginalEditorSnapshotError.unsupportedVersion
        }
        let headerLength = Int(Self.readUInt32(bytes, at: 12))
        guard headerLength > 0, headerLength <= Self.maximumHeaderBytes,
              headerLength < bytes.count - Self.prefixByteCount else {
            throw AnytypeOriginalEditorSnapshotError.invalidFrame
        }
        let boundary = Self.prefixByteCount + headerLength
        let headerBytes = bytes.subdata(in: Self.prefixByteCount..<boundary)
        let header = try JSONDecoder().decode(Header.self, from: headerBytes)
        // Unknown v1 fields, duplicate keys and alternate encodings cannot be
        // silently discarded by a decode/re-encode of this opaque body.
        guard try Self.encodeHeader(header) == headerBytes else {
            throw AnytypeOriginalEditorSnapshotError.noncanonicalHeader
        }
        _ = try AnytypeOriginalEditorBinding(
            accountID: header.provenance.accountID,
            spaceID: header.provenance.spaceID,
            objectID: header.provenance.objectID,
            hostProfileID: header.provenance.hostProfileID,
            annotationUUID: header.provenance.annotationUUID,
            expectedRevision: header.provenance.capturedAgainstRevision,
            sourceWitnessSHA256: header.provenance.sourceWitnessSHA256
        )
        if let origin = header.provenance.transportOriginHostProfileID {
            guard !origin.isEmpty, origin.utf8.count <= 512, !origin.utf8.contains(0) else {
                throw AnytypeOriginalEditorSnapshotError.invalidFrame
            }
        }
        guard OriginalAnnotationPayloadBudget.acceptsArchiveBytes(
            bytes.count - boundary, maximumBodyBytes: maximumBodyBytes
        ) else { throw AnytypeOriginalEditorSnapshotError.bodyTooLarge }
        let archive = bytes.subdata(in: boundary..<bytes.count)
        guard header.archiveFormat == "anytype.protobuf.zip",
              header.archiveByteCount == archive.count,
              archive.count >= 22,
              archive.prefix(4) == Data([0x50, 0x4b, 0x03, 0x04]),
              Self.digest(archive) == header.archiveSHA256 else {
            throw AnytypeOriginalEditorSnapshotError.invalidArchive
        }
        let report = try Anytype_Model_ExportReport(serializedBytes: header.exportReport)
        try Self.validateReport(report, responseCount: header.exportedObjectCount)
        self.bodyBytes = bytes
        provenance = header.provenance
        nativeArchiveBytes = archive
        nativeArchiveSHA256 = header.archiveSHA256
        nativeExportReportBytes = header.exportReport
        exportedObjectCount = header.exportedObjectCount
    }

    /// Internal framing seam. Only the Host's admitted original export may
    /// supply new capture data; public decoding is never an import operation.
    internal static func frame(
        archive: Data, reportBytes: Data, responseCount: Int32,
        binding: AnytypeOriginalEditorBinding, maximumBodyBytes: Int,
        transportOriginHostProfileID: String? = nil
    ) throws -> Self {
        try validateLimit(maximumBodyBytes)
        guard OriginalAnnotationPayloadBudget.acceptsArchiveBytes(
            archive.count, maximumBodyBytes: maximumBodyBytes
        ) else {
            throw AnytypeOriginalEditorSnapshotError.bodyTooLarge
        }
        let report = try Anytype_Model_ExportReport(serializedBytes: reportBytes)
        try validateReport(report, responseCount: responseCount)
        let header = Header(
            archiveFormat: "anytype.protobuf.zip",
            provenance: Provenance(binding: binding, transportOriginHostProfileID: transportOriginHostProfileID),
            archiveByteCount: archive.count,
            archiveSHA256: digest(archive),
            exportedObjectCount: responseCount,
            exportReport: reportBytes
        )
        let encodedHeader = try encodeHeader(header)
        guard OriginalAnnotationPayloadBudget.acceptsFrame(
            headerBytes: encodedHeader.count, archiveBytes: archive.count,
            maximumBodyBytes: maximumBodyBytes
        ) else {
            throw AnytypeOriginalEditorSnapshotError.bodyTooLarge
        }
        var framed = magic
        appendUInt32(UInt32(formatVersion), to: &framed)
        appendUInt32(UInt32(encodedHeader.count), to: &framed)
        framed.append(encodedHeader)
        framed.append(archive)
        return try Self(bodyBytes: framed, maximumBodyBytes: maximumBodyBytes)
    }

    internal static func validateLimit(_ maximum: Int) throws {
        guard maximum > prefixByteCount, maximum <= absoluteMaximumBodyBytes else {
            throw AnytypeOriginalEditorSnapshotError.invalidLimit
        }
    }

    private static func validateReport(
        _ report: Anytype_Model_ExportReport, responseCount: Int32
    ) throws {
        // Even warning/info-only exports are retained for review rather than
        // represented as a proven complete annotation snapshot in version 1.
        guard report.status == .success, responseCount > 0,
              report.succeed == responseCount,
              report.objectErrors == 0, report.fileErrors == 0,
              report.issues.isEmpty else {
            throw AnytypeOriginalEditorSnapshotError.incompleteExport
        }
    }

    private static func encodeHeader(_ header: Header) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(header)
    }

    private static func digest(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }

    private static func readUInt32(_ bytes: Data, at offset: Int) -> UInt32 {
        (0..<4).reduce(UInt32(0)) { ($0 << 8) | UInt32(bytes[offset + $1]) }
    }

    private static func appendUInt32(_ value: UInt32, to bytes: inout Data) {
        bytes.append(contentsOf: [24, 16, 8, 0].map { UInt8(truncatingIfNeeded: value >> $0) })
    }
}

public enum AnytypeOriginalEditorSnapshotError: Error, Sendable, Equatable {
    case invalidLimit, bodyTooLarge, invalidFrame, unsupportedVersion
    case noncanonicalHeader, invalidArchive, incompleteExport, missingExportReport
    case unsafeArchivePath, archiveChanged
    case fileSystemFailure(Int32)
}

/// Temporary recovery evidence only. The rich body contains the entire archive;
/// this path is neither a portable sidecar nor persistent source authority.
public struct AnytypeOriginalEditorSnapshotCapture: Sendable {
    public let snapshot: AnytypeOriginalEditorSnapshot
    public let retainedArchiveURL: URL
    public let retainedDirectoryURL: URL
}

/// Failed captures keep whatever the original exporter left in the owned
/// directory (and report when the original invocation returned it).
/// This also wraps a late source-retirement rejection after original export.
public struct AnytypeOriginalEditorSnapshotCaptureFailure: Error {
    public let retainedDirectoryURL: URL
    public let underlyingError: any Error
}

extension AnytypeOriginalEditorSnapshotCapture {
    /// Callers must hold the original document's exclusive read admission.
    static func exportNativeArchive(binding: AnytypeOriginalEditorBinding, transportOriginHostProfileID: String?,
                                    directory: URL, maximumBodyBytes: Int) async throws -> Self {
        let response = try await ClientCommands.objectListExport(.with {
            $0.spaceID = binding.spaceID
            $0.objectIds = [binding.objectID]
            $0.path = directory.path
            $0.format = .protobuf
            $0.zip = true
            $0.isJson = false
            $0.includeFiles = true
            $0.includeNested = true
            $0.includeArchived = true
            $0.includeBacklinks = false
            $0.includeSpace = false
            $0.noProgress = true
            // No state filters or removeBlocks: original native closure.
        }).invoke()
        guard response.hasReport else {
            throw AnytypeOriginalEditorSnapshotError.missingExportReport
        }
        let reportBytes = try response.report.serializedData()
        try reportBytes.write(
            to: directory.appendingPathComponent("native-export-report.pb"),
            options: .withoutOverwriting
        )
        let archiveURL = URL(fileURLWithPath: response.path)
        let archive = try OriginalEditorArchiveFiles.readArchive(
            archiveURL, in: directory,
            maximumBytes: min(maximumBodyBytes, OriginalAnnotationPayloadBudget.maximumArchiveBytes)
        )
        let snapshot = try AnytypeOriginalEditorSnapshot.frame(
            archive: archive, reportBytes: reportBytes, responseCount: response.succeed,
            binding: binding, maximumBodyBytes: maximumBodyBytes,
            transportOriginHostProfileID: transportOriginHostProfileID
        )
        return AnytypeOriginalEditorSnapshotCapture(
            snapshot: snapshot, retainedArchiveURL: archiveURL,
            retainedDirectoryURL: directory
        )
    }
}

extension AnytypeOriginalEditorHost {
    /// Drain edits registered by the original UI, then capture while the same
    /// document Owner excludes new mutations. Success terminally retires this
    /// Host before returning; the caller still performs its normal complete
    /// envelope validation and original pre-save revision/source CAS.
    @MainActor
    public func captureNativeSnapshot(maximumBodyBytes: Int) async throws -> AnytypeOriginalEditorSnapshotCapture {
        try validateCurrentSource()
        try AnytypeOriginalEditorSnapshot.validateLimit(maximumBodyBytes)
        let capturedBinding = binding
        let capturedTransportOriginHostProfileID = snapshotTransportOriginHostProfileID
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        var beganCapture = false
        do {
            try beginSnapshotCapture()
            beganCapture = true
            let result = try await preparedSession.owner.withExclusiveRead(
                contextId: capturedBinding.objectID, spaceId: capturedBinding.spaceID,
                rpcNames: ["ObjectListExport"], retireOnSuccess: true
            ) {
                try await AnytypeOriginalEditorSnapshotCapture.exportNativeArchive(
                    binding: capturedBinding, transportOriginHostProfileID: capturedTransportOriginHostProfileID,
                    directory: directory, maximumBodyBytes: maximumBodyBytes)
            }
            // Exclusive completion validated the result and retired this Owner
            // before releasing its barrier. Complete the terminal Host cleanup
            // without trying to re-admit the intentionally retired Owner.
            completeSnapshotCapture()
            return result
        } catch {
            // A second concurrent caller that failed begin must not release
            // the first caller's interaction freeze.
            if beganCapture { failSnapshotCapture() }
            // No blanket cleanup, including after a late ownership rejection.
            throw AnytypeOriginalEditorSnapshotCaptureFailure(
                retainedDirectoryURL: directory, underlyingError: error
            )
        }
    }
}

internal enum OriginalEditorArchiveFiles {
    static func makeOwnedDirectory() throws -> URL {
        let parent = FileManager.default.temporaryDirectory.resolvingSymlinksInPath().standardizedFileURL
        return try makeOwnedDirectory(in: parent)
    }

    static func makeOwnedDirectory(in parent: URL) throws -> URL {
        guard parent.isFileURL, parent.standardizedFileURL == parent,
              parent.resolvingSymlinksInPath().path == parent.path else {
            throw AnytypeOriginalEditorSnapshotError.unsafeArchivePath
        }
        let directory = parent.appendingPathComponent("anytype-original-snapshot-\(UUID().uuidString)", isDirectory: true)
        // Unlike createDirectory, mkdir refuses a pre-existing directory.
        guard Darwin.mkdir(directory.path, 0o700) == 0 else {
            throw AnytypeOriginalEditorSnapshotError.fileSystemFailure(errno)
        }
        return directory
    }

    static func readArchive(_ archive: URL, in directory: URL, maximumBytes: Int) throws -> Data {
        guard archive.pathExtension == "zip" else {
            throw AnytypeOriginalEditorSnapshotError.unsafeArchivePath
        }
        return try readOwnedRegularFile(
            archive, in: directory, maximumBytes: maximumBytes,
            allowedMaximumBytes: OriginalAnnotationPayloadBudget.maximumArchiveBytes
        )
    }

    /// The native qualification consumer also uses this same bounded, no-follow
    /// read for an original FileDownload result in its exclusively owned directory.
    static func readOwnedRegularFile(_ archive: URL, in directory: URL, maximumBytes: Int) throws -> Data {
        // The existing attachment qualification caller retains its smaller cap.
        try readOwnedRegularFile(archive, in: directory, maximumBytes: maximumBytes,
                                 allowedMaximumBytes: 65_536)
    }

    /// The MiniApps file path uses the same owned no-follow reader, bounded by
    /// the original native archive's expanded limit. Existing qualification and
    /// archive entry points retain their original, smaller limits.
    static func readMiniAppsAttachment(_ file: URL, in directory: URL, maximumBytes: Int) throws -> Data {
        guard maximumBytes >= 0,
              maximumBytes <= OriginalAnnotationNativeArchiveLayout.maximumExpandedBytes else {
            throw AnytypeOriginalEditorSnapshotError.invalidLimit
        }
        let bytes = try readOwnedRegularFile(file, in: directory, maximumBytes: max(1, maximumBytes),
            allowedMaximumBytes: OriginalAnnotationNativeArchiveLayout.maximumExpandedBytes)
        guard bytes.count <= maximumBytes else {
            throw AnytypeOriginalEditorSnapshotError.bodyTooLarge
        }
        return bytes
    }

    private static func readOwnedRegularFile(
        _ archive: URL, in directory: URL, maximumBytes: Int, allowedMaximumBytes: Int
    ) throws -> Data {
        guard maximumBytes > 0, maximumBytes <= allowedMaximumBytes else {
            throw AnytypeOriginalEditorSnapshotError.invalidLimit
        }
        guard archive.isFileURL,
              archive.standardizedFileURL == archive,
              archive.deletingLastPathComponent().path == directory.path,
              directory.resolvingSymlinksInPath().path == directory.path else {
            throw AnytypeOriginalEditorSnapshotError.unsafeArchivePath
        }
        let directoryFD = Darwin.open(directory.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directoryFD >= 0 else {
            throw AnytypeOriginalEditorSnapshotError.fileSystemFailure(errno)
        }
        defer { Darwin.close(directoryFD) }
        // Open a direct leaf relative to the owned directory descriptor. A
        // symlink cannot redirect this read into another object's filesystem.
        let fileFD = Darwin.openat(directoryFD, archive.lastPathComponent, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard fileFD >= 0 else {
            throw AnytypeOriginalEditorSnapshotError.fileSystemFailure(errno)
        }
        let handle = FileHandle(fileDescriptor: fileFD, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat()
        guard Darwin.fstat(fileFD, &before) == 0 else {
            throw AnytypeOriginalEditorSnapshotError.fileSystemFailure(errno)
        }
        guard before.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG), before.st_size >= 0 else {
            throw AnytypeOriginalEditorSnapshotError.unsafeArchivePath
        }
        guard before.st_size <= Int64(maximumBytes) else {
            throw AnytypeOriginalEditorSnapshotError.bodyTooLarge
        }
        // One byte beyond the limit detects growth without an unbounded read.
        let bytes = try handle.read(upToCount: maximumBytes + 1) ?? Data()
        var after = stat()
        guard Darwin.fstat(fileFD, &after) == 0 else {
            throw AnytypeOriginalEditorSnapshotError.fileSystemFailure(errno)
        }
        guard bytes.count <= maximumBytes else {
            throw AnytypeOriginalEditorSnapshotError.bodyTooLarge
        }
        guard before.st_dev == after.st_dev, before.st_ino == after.st_ino,
              before.st_size == after.st_size, Int64(bytes.count) == after.st_size,
              before.st_mtimespec.tv_sec == after.st_mtimespec.tv_sec,
              before.st_mtimespec.tv_nsec == after.st_mtimespec.tv_nsec,
              before.st_ctimespec.tv_sec == after.st_ctimespec.tv_sec,
              before.st_ctimespec.tv_nsec == after.st_ctimespec.tv_nsec else {
            throw AnytypeOriginalEditorSnapshotError.archiveChanged
        }
        return bytes
    }
}
