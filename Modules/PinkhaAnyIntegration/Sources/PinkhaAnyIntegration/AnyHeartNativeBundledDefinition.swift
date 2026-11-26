import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativeBundledDefinitionError: Error, Equatable, Sendable {
    case invalidBinding, invalidDescriptor, limit
}

/// The actual compiled native resolver entry. Its containing capture or explicit
/// recovered-source envelope supplies provenance; this value alone does not.
/// This value is neither a native object/tree nor account/session authority.
/// Raw protobuf and its generated JSON view remain separately hash-bound.
public struct AnyHeartNativeBundledDefinition: Sendable {
    public enum Kind: String, Sendable { case property, type }
    public let kind: Kind
    public let key: String
    public let protobufMessage: String
    public let protobufSHA256: String
    public let jsonViewSHA256: String
    public let protobufBytes: Data
    public let jsonViewBytes: Data
    public let definition: AnyJSON
    public var identity: String { kind.rawValue + ":" + key }

    public init(kind: String, key: String, protobufMessage: String,
                protobuf: Data, jsonView: Data) throws {
        guard !protobuf.isEmpty, protobuf.count <= 1_048_576,
              !jsonView.isEmpty, jsonView.count <= 4_194_304 else {
            throw AnyHeartNativeBundledDefinitionError.limit
        }
        guard let parsedKind = Kind(rawValue: kind), !key.isEmpty, key.utf8.count <= 4096,
              key.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }),
              protobufMessage == (parsedKind == .property ? "anytype.model.Relation" : "anytype.model.ObjectType") else {
            throw AnyHeartNativeBundledDefinitionError.invalidBinding
        }
        let root = try JSONDecoder().decode(AnyJSON.self, from: jsonView)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: jsonView, encoded: encoder.encode(root))
        let digest = AnyContentDigest.sha256(protobuf)
        guard let fields = root.object,
              Set(fields.keys) == ["Contract", "Kind", "Key", "ProtobufMessage",
                                   "ProtobufSHA256", "ProtobufBytes", "Definition"],
              root["Contract"] == .string("pinkha-native-bundled-definition-json-v1"),
              root["Kind"] == .string(kind),
              root["Key"]?.string.map({ Data($0.utf8) }) == Data(key.utf8),
              root["ProtobufMessage"] == .string(protobufMessage),
              root["ProtobufSHA256"] == .string(digest),
              root["ProtobufBytes"] == .integer(Int64(protobuf.count)),
              let definition = root["Definition"], definition.object != nil,
              definition["key"]?.string.map({ Data($0.utf8) }) == Data(key.utf8) else {
            throw AnyHeartNativeBundledDefinitionError.invalidDescriptor
        }
        if parsedKind == .property {
            guard definition["id"]?.string.map({ Data($0.utf8) }) == Data(("_br" + key).utf8) else {
                throw AnyHeartNativeBundledDefinitionError.invalidDescriptor
            }
        }
        self.kind = parsedKind; self.key = key; self.protobufMessage = protobufMessage
        protobufSHA256 = digest; jsonViewSHA256 = AnyContentDigest.sha256(jsonView)
        protobufBytes = protobuf; jsonViewBytes = jsonView; self.definition = definition
    }
}
