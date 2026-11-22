import Foundation
import ProtobufMessages
import SwiftProtobuf

// Read-only SwiftProtobuf views of the exact original native wrapper messages:
// anytype-heart d98420b1113536afd08cde6de9a5816f6d27ffff,
// pb/protos/snapshot.proto: SnapshotWithType and
// pb/protos/changes.proto: Change.Snapshot / Change.FileKeys.
// The body remains the existing generated SmartBlockSnapshotBase. These types
// do not define a replacement wire format, import state or alter archive bytes.
// Supported message unknown fields are retained and participate in comparison.
// Map-entry extensions that SwiftProtobuf would discard are refused by the
// pre-decode guard; they are never silently normalized into equality.
internal struct OriginalAnnotationNativeSnapshotWire: Sendable {
    var sbType: Anytype_Model_SmartBlockType = .accountOld
    var snapshot: OriginalAnnotationNativeChangeSnapshotWire?
    var unknownFields = UnknownStorage()
    init() {}
}

extension OriginalAnnotationNativeSnapshotWire: Message, _MessageImplementationBase, _ProtoNameProviding {
    static let protoMessageName = "anytype.SnapshotWithType"
    static let _protobuf_nameMap: _NameMap = [1: .same(proto: "sbType"), 2: .same(proto: "snapshot")]
    mutating func decodeMessage<D: SwiftProtobuf.Decoder>(decoder: inout D) throws {
        while let field = try decoder.nextFieldNumber() {
            switch field {
            case 1: try decoder.decodeSingularEnumField(value: &sbType)
            case 2: try decoder.decodeSingularMessageField(value: &snapshot)
            default: break
            }
        }
    }
    func traverse<V: Visitor>(visitor: inout V) throws {
        if sbType != .accountOld { try visitor.visitSingularEnumField(value: sbType, fieldNumber: 1) }
        if let snapshot { try visitor.visitSingularMessageField(value: snapshot, fieldNumber: 2) }
        try unknownFields.traverse(visitor: &visitor)
    }
    static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.sbType == rhs.sbType && lhs.snapshot == rhs.snapshot && lhs.unknownFields == rhs.unknownFields
    }
}

internal struct OriginalAnnotationNativeChangeSnapshotWire: Sendable {
    var logHeads: [String: String] = [:]
    var data: Anytype_Model_SmartBlockSnapshotBase?
    var fileKeys: [OriginalAnnotationNativeFileKeysWire] = []
    var unknownFields = UnknownStorage()
    init() {}
}

extension OriginalAnnotationNativeChangeSnapshotWire: Message, _MessageImplementationBase, _ProtoNameProviding {
    static let protoMessageName = "anytype.Change.Snapshot"
    static let _protobuf_nameMap: _NameMap = [1: .same(proto: "logHeads"), 2: .same(proto: "data"), 3: .same(proto: "fileKeys")]
    mutating func decodeMessage<D: SwiftProtobuf.Decoder>(decoder: inout D) throws {
        while let field = try decoder.nextFieldNumber() {
            switch field {
            case 1: try decoder.decodeMapField(fieldType: _ProtobufMap<_ProtobufString, _ProtobufString>.self, value: &logHeads)
            case 2: try decoder.decodeSingularMessageField(value: &data)
            case 3: try decoder.decodeRepeatedMessageField(value: &fileKeys)
            default: break
            }
        }
    }
    func traverse<V: Visitor>(visitor: inout V) throws {
        if !logHeads.isEmpty { try visitor.visitMapField(fieldType: _ProtobufMap<_ProtobufString, _ProtobufString>.self, value: logHeads, fieldNumber: 1) }
        if let data { try visitor.visitSingularMessageField(value: data, fieldNumber: 2) }
        if !fileKeys.isEmpty { try visitor.visitRepeatedMessageField(value: fileKeys, fieldNumber: 3) }
        try unknownFields.traverse(visitor: &visitor)
    }
    static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.logHeads == rhs.logHeads && lhs.data == rhs.data && lhs.fileKeys == rhs.fileKeys && lhs.unknownFields == rhs.unknownFields
    }
}

internal struct OriginalAnnotationNativeFileKeysWire: Sendable {
    var hash = ""
    var keys: [String: String] = [:]
    var unknownFields = UnknownStorage()
    init() {}
}

extension OriginalAnnotationNativeFileKeysWire: Message, _MessageImplementationBase, _ProtoNameProviding {
    static let protoMessageName = "anytype.Change.FileKeys"
    static let _protobuf_nameMap: _NameMap = [1: .same(proto: "hash"), 2: .same(proto: "keys")]
    mutating func decodeMessage<D: SwiftProtobuf.Decoder>(decoder: inout D) throws {
        while let field = try decoder.nextFieldNumber() {
            switch field {
            case 1: try decoder.decodeSingularStringField(value: &hash)
            case 2: try decoder.decodeMapField(fieldType: _ProtobufMap<_ProtobufString, _ProtobufString>.self, value: &keys)
            default: break
            }
        }
    }
    func traverse<V: Visitor>(visitor: inout V) throws {
        if !hash.isEmpty { try visitor.visitSingularStringField(value: hash, fieldNumber: 1) }
        if !keys.isEmpty { try visitor.visitMapField(fieldType: _ProtobufMap<_ProtobufString, _ProtobufString>.self, value: keys, fieldNumber: 2) }
        try unknownFields.traverse(visitor: &visitor)
    }
    static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.hash == rhs.hash && lhs.keys == rhs.keys && lhs.unknownFields == rhs.unknownFields
    }
}
