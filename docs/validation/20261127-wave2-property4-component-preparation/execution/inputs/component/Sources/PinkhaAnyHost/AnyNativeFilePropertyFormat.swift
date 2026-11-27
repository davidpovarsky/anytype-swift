import Foundation
import PinkhaAnyEngine

/// Consumer-owned file presentation over the native array + link-index contract.
/// Any deliberately has no built-in file xFormat slug. The explicit extension
/// keeps file URIs distinct from object relations and preserves native storage.
public struct AnyNativeFilePropertyFormat: Equatable, Sendable {
    public static let contract = "pinkha-native-file-property-v1"
    public static let slug = "pinkha-file"
    public let multiple: Bool

    public init?(property: AnyJSON) throws {
        let format = property["xFormat"]
        guard format?["type"] == .string(Self.slug) || format?["pinkhaFile"] != nil else { return nil }
        guard property["kind"] == .string("array"), format?["type"] == .string(Self.slug),
              format?["links"] == .string("links"),
              let vendor = format?["pinkhaFile"]?.object, Set(vendor.keys) == ["contract"],
              vendor["contract"] == .string(Self.contract),
              let config = format?["config"]?.object, Set(config.keys) == ["multiple"],
              let multiple = config["multiple"]?.bool else {
            throw AnyNativePropertyError.invalidProperty
        }
        self.multiple = multiple
    }

    public func references(in value: AnyJSON) throws -> [AnyNativeFileReference] {
        guard let list = value.array, list.count <= 20_000, multiple || list.count <= 1 else {
            throw AnyNativePropertyError.invalidProperty
        }
        return try list.map {
            guard let uri = $0.string else { throw AnyNativePropertyError.invalidProperty }
            return try AnyNativeFileReference(uri: uri)
        }
    }

    static func descriptor(multiple: Bool) -> [String: AnyJSON] {
        ["type": .string(slug), "links": .string("links"),
         "config": .object(["multiple": .bool(multiple)]),
         "pinkhaFile": .object(["contract": .string(contract)])]
    }
}
