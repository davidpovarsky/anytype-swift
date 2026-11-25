import Foundation
import ProtobufMessages
import SwiftProtobuf
import ZIPFoundation

/// Read-only projection of an already captured original export. It never writes
/// a block, constructs an archive or promotes a page to an annotation.
internal enum OriginalEditorLocalAnnotationNativeBody {
    static func decoded(_ snapshot: AnytypeOriginalEditorSnapshot) throws -> OriginalAnnotationNativeArchiveComparison {
        try OriginalAnnotationNativeArchiveComparison(
            archiveBytes: snapshot.nativeArchiveBytes,
            rootID: snapshot.provenance.objectID, spaceID: snapshot.provenance.spaceID,
            formatVersion: AnytypeOriginalEditorSnapshot.formatVersion,
            reportedObjectCount: snapshot.exportedObjectCount
        )
    }

    static func requireAnnotation(_ snapshot: AnytypeOriginalEditorSnapshot,
                                  source: AnytypeOriginalEditorLocalAnnotationSource) throws {
        let actual = try decoded(snapshot)
        let details = actual.rootSnapshot.details
        try requireMarkers(details, source: source,
            transportOriginHostProfileID: snapshot.provenance.transportOriginHostProfileID)
        let archive = try Archive(data: snapshot.nativeArchiveBytes, accessMode: .read)
        guard case .listValue(let types)? = details.fields["type"]?.kind,
              types.values.count == 1,
              case .stringValue(let typeID)? = types.values.first?.kind,
              !typeID.isEmpty, !typeID.contains("/"),
              let entry = archive["types/" + typeID + ".pb"] else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
        var bytes = Data()
        _ = try archive.extract(entry, bufferSize: 16_384, skipCRC32: false) { chunk in
            guard bytes.count + chunk.count <= OriginalAnnotationNativeArchiveLayout.maximumExpandedBytes else {
                throw AnytypeOriginalEditorLocalAnnotationError.unsupportedBody
            }
            bytes.append(chunk)
        }
        try OriginalAnnotationNativeMapKeyGuard.validate(bytes)
        let wire = try OriginalAnnotationNativeSnapshotWire(serializedBytes: bytes)
        guard wire.sbType == .sttype, let type = wire.snapshot?.data,
              string(type.details, "id") == typeID,
              string(type.details, "uniqueKey") == OriginalAnnotationNativeMetadata.originalTypeUniqueKey else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
    }

    static func requireMarkers(_ details: Google_Protobuf_Struct,
                               source: AnytypeOriginalEditorLocalAnnotationSource,
                               transportOriginHostProfileID: String? = nil) throws {
        let origin = transportOriginHostProfileID ?? source.hostProfileID
        guard !origin.isEmpty, origin.utf8.count <= 512, !origin.utf8.contains(0),
              string(details, OriginalAnnotationMetadataField.schemaProtocol.rawValue)
                == OriginalAnnotationNativeMetadata.protocolValue,
              string(details, OriginalAnnotationMetadataField.classification.rawValue) == "annotation",
              string(details, OriginalAnnotationMetadataField.namespace.rawValue) == "otzaria.local.annotation",
              annotationUUIDMatches(string(details, OriginalAnnotationMetadataField.annotationUUID.rawValue),
                                    expected: source.annotationUUID),
              string(details, OriginalAnnotationMetadataField.creationDestination.rawValue)
                == "otzaria.local.draft:" + origin else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
    }

    /// UUID identity is case-independent across the original Go and Swift
    /// clients. Stored native bytes remain untouched; other markers remain exact.
    static func annotationUUIDMatches(_ raw: String?, expected: UUID) -> Bool {
        guard let raw, let actual = UUID(uuidString: raw) else { return false }
        return actual == expected
    }

    static func string(_ details: Google_Protobuf_Struct, _ key: String) -> String? {
        guard case .stringValue(let value)? = details.fields[key]?.kind else { return nil }
        return value
    }

    struct TextProjection: Sendable {
        let fullPlainText: String
        let textPreview: String
    }

    static func preview(_ snapshot: AnytypeOriginalEditorSnapshot,
                        source: AnytypeOriginalEditorLocalAnnotationSource) throws -> String {
        try textProjection(snapshot, source: source).textPreview
    }

    static func textProjection(_ snapshot: AnytypeOriginalEditorSnapshot,
                               source: AnytypeOriginalEditorLocalAnnotationSource) throws -> TextProjection {
        try requireAnnotation(snapshot, source: source)
        return try textProjection(root: decoded(snapshot).rootSnapshot,
                                  rootID: snapshot.provenance.objectID)
    }

    /// Only callers that have independently validated the actual native
    /// Annotation or manifest-bound Document may project its immutable text.
    static func textProjection(root body: Anytype_Model_SmartBlockSnapshotBase,
                               rootID: String) throws -> TextProjection {
        // Native IDs are exact UTF-8 bytes. Swift String equality normalizes
        // Unicode, which could otherwise turn two byte-distinct parsed IDs into
        // a Dictionary precondition failure instead of a bounded refusal.
        var blocks: [Data: Anytype_Model_Block] = [:]
        for block in body.blocks {
            let key = Data(block.id.utf8)
            guard blocks.updateValue(block, forKey: key) == nil else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidPreview
            }
        }
        guard let root = blocks[Data(rootID.utf8)] else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidPreview
        }
        var seen = Set<Data>()
        var texts: [String] = []
        func visit(_ id: String) throws {
            let key = Data(id.utf8)
            guard seen.insert(key).inserted, let block = blocks[key] else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidPreview
            }
            if case .text(let text)? = block.content, !text.text.isEmpty {
                texts.append(text.text)
            }
            for child in block.childrenIds { try visit(child) }
        }
        for child in root.childrenIds { try visit(child) }
        let text = texts.joined(separator: "\n")
        guard !text.utf8.contains(0) else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidPreview
        }
        var result = "", bytes = 0
        for scalar in text.unicodeScalars {
            let fragment = String(scalar), count = fragment.utf8.count
            guard bytes + count <= 8_192 else { break }
            result.unicodeScalars.append(scalar)
            bytes += count
        }
        return .init(fullPlainText: text, textPreview: result)
    }
}
