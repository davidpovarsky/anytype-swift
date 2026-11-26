import Foundation
import PinkhaAnyEngine

/// Display-only interpretation of an imported native Type. Every address is
/// checked against the current object's real property definitions. This policy
/// never makes a field writable and never authorizes a native mutation.
public struct AnyNativeImportedTypePresentation: Sendable {
    public static let contract = "pinkha-heart-native-type-presentation-v2"
    public static let bookmarkContract = "pinkha-heart-native-bookmark-presentation-v1"
    public let sourceURLKey: AnyNativePropertyKey?
    public let orderedKeys: [AnyNativePropertyKey]
    public let defaultHiddenKeys: Set<String>

    public init?(type: AnyNativePropertyOwner?, catalog: AnyNativePropertyCatalog,
                 collectionIDs: [String], definitions: [AnyNativePropertyDefinition],
                 raw: AnyJSON) throws {
        guard let type, let descriptor = type.raw["layout"]?["config"]?["pinkhaHeart"] else { return nil }
        let isBasic = descriptor["contract"]?.string == Self.contract
        let isBookmark = descriptor["contract"]?.string == Self.bookmarkContract
        let commonFields: Set<String> = ["contract", "sourceRecommendedLayout", "propertyOwnerId",
                                         "recommended", "featured", "hidden", "files", "definitionHidden"]
        guard type.documentEligible, !type.builtIn,
              (isBasic && type.raw["layout"]?["type"] == .string("page") &&
                  descriptor["sourceRecommendedLayout"] == .integer(0)) ||
              (isBookmark && type.raw["layout"]?["type"] == .string("bookmark") &&
                  descriptor["sourceRecommendedLayout"] == .integer(11)),
              let fields = descriptor.object,
              Set(fields.keys).isSubset(of: commonFields.union(isBookmark ? ["sourceURL"] : [])),
              definitions.count <= 4096,
              Set(definitions.map(\.key)).count == definitions.count else {
            throw AnyNativePropertyError.invalidCatalog
        }
        let propertyOwner: String?
        if let value = descriptor["propertyOwnerId"] {
            guard let id = value.string, AnyEditorBlock.validID(id), id != "any",
                  collectionIDs.contains(id),
                  catalog.collections.contains(where: { $0.id == id && !$0.builtIn }) else {
                throw AnyNativePropertyError.invalidCatalog
            }
            propertyOwner = id
        } else { propertyOwner = nil }
        let byKey = Dictionary(uniqueKeysWithValues: definitions.map { ($0.key, $0) })
        func addresses(_ field: String, optional: Bool = false) throws -> [AnyNativePropertyKey] {
            if optional && descriptor[field] == nil { return [] }
            guard let values = descriptor[field]?.array, values.count <= 512 else {
                throw AnyNativePropertyError.invalidCatalog
            }
            var keys: [AnyNativePropertyKey] = [], seen = Set<AnyNativePropertyKey>()
            for value in values {
                guard let pair = value.object, Set(pair.keys) == ["ownerId", "propertyId"],
                      let owner = pair["ownerId"]?.string, let property = pair["propertyId"]?.string else {
                    throw AnyNativePropertyError.invalidCatalog
                }
                let key = try AnyNativePropertyKey(ownerID: owner, propertyID: property)
                guard let definition = byKey[key], seen.insert(key).inserted else {
                    throw AnyNativePropertyError.invalidCatalog
                }
                if owner == "any" {
                    if let role = AnyDestinationCanonicalPropertyBinding.IdentityRole(rawValue: property) {
                        let expected = AnyDestinationCanonicalPropertyBinding.nativeIdentityDescriptor(role)
                        guard definition.kind == .string,
                              try AnyDestinationDefinitionChecks.bytes(definition.raw) ==
                                  AnyDestinationDefinitionChecks.bytes(expected) else {
                            throw AnyNativePropertyError.invalidCatalog
                        }
                    } else {
                        guard ["name", "description"].contains(property), definition.kind == .string,
                              definition.scope == "synced" else {
                            throw AnyNativePropertyError.invalidCatalog
                        }
                    }
                } else {
                    guard owner == propertyOwner else { throw AnyNativePropertyError.invalidCatalog }
                }
                keys.append(key)
            }
            return keys
        }
        let featured = try addresses("featured"), recommended = try addresses("recommended")
        let hidden = try addresses("hidden"), files = try addresses("files")
        let definitionHidden = try addresses("definitionHidden", optional: true)
        if isBookmark {
            guard let propertyOwner, let pair = descriptor["sourceURL"]?.object,
                  Set(pair.keys) == ["ownerId", "propertyId"],
                  pair["ownerId"]?.string == propertyOwner,
                  let property = pair["propertyId"]?.string,
                  let key = try? AnyNativePropertyKey(ownerID: propertyOwner, propertyID: property),
                  Set(featured + recommended).contains(key),
                  let definition = byKey[key], definition.kind == .string,
                  definition.scope == "synced", definition.xFormat?["type"] == .string("url") else {
                throw AnyNativePropertyError.invalidCatalog
            }
            sourceURLKey = key
        } else {
            sourceURLKey = nil
        }
        var seen = Set<AnyNativePropertyKey>(), ordered: [AnyNativePropertyKey] = []
        for key in featured + recommended + files + hidden where seen.insert(key).inserted { ordered.append(key) }
        let shownByType = Set(featured + recommended + files)
        // Definition visibility is independent of the Type's ordered hidden
        // recommendations. Both are display defaults, never value identity.
        var hiddenKeys = Set((hidden + definitionHidden).map(\.visibilityKey))
        if let propertyOwner {
            for definition in definitions where definition.key.ownerID == propertyOwner {
                let key = definition.key
                // Zero, false, an empty string and an empty list are all present
                // business values. Only genuinely absent, unused fields default
                // to hidden; source-hidden fields remain hidden until customized.
                if !shownByType.contains(key), raw[propertyOwner]?[key.propertyID] == nil {
                    hiddenKeys.insert(key.visibilityKey)
                }
            }
        }
        try AnyNativePropertyStore.validateHiddenKeys(Array(hiddenKeys))
        orderedKeys = ordered; defaultHiddenKeys = hiddenKeys
    }

    func ordered(_ definitions: [AnyNativePropertyDefinition]) -> [AnyNativePropertyDefinition] {
        let ranks = Dictionary(uniqueKeysWithValues: orderedKeys.enumerated().map { ($0.element, $0.offset) })
        return definitions.sorted {
            let a = ranks[$0.key] ?? Int.max, b = ranks[$1.key] ?? Int.max
            if a != b { return a < b }
            return $0.key.ownerID == $1.key.ownerID
                ? AnyNativePropertyStore.utf8Less($0.key.propertyID, $1.key.propertyID)
                : AnyNativePropertyStore.utf8Less($0.key.ownerID, $1.key.ownerID)
        }
    }
}
