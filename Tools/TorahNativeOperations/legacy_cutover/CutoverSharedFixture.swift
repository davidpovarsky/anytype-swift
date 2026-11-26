import Foundation
import PinkhaKit

/// Test-data production uses the actual shared codec and planner. These bytes
/// confer no native authority; the native test must persist/read them itself.
@main
struct CutoverSharedFixture {
    static func main() throws {
        let arguments = Array(CommandLine.arguments.dropFirst())
        guard arguments.count == 4,
              arguments.prefix(3).allSatisfy({ !$0.isEmpty && $0.utf8.count <= 1_024 && !$0.contains("\0") }),
              ["populated", "missing", "empty"].contains(arguments[3]) else {
            throw NSError(domain: "PinkhaCutoverFixture", code: 1)
        }
        let space = arguments[0], object = arguments[1], key = arguments[2]
        let location = TorahAssociationLocation(spaceId: space, target: .object(objectId: object))
        let value: Data?
        switch arguments[3] {
        case "missing":
            value = nil
        case "empty":
            value = Data()
        default:
            var records: [TorahStoredAssociationRecord] = []
            for (id, uuid) in [("native-first", "11111111-1111-4111-8111-111111111111"),
                               ("native-second", "22222222-2222-4222-8222-222222222222")] {
                let item = TorahAssociationItem(id: id, kind: .ref, role: .sourceQuote,
                    providerID: "sefaria", externalID: "Genesis 1:1", canonicalKey: "Genesis.1.1",
                    labelHe: "בראשית א א", labelEn: "Genesis",
                    createdAt: Date(timeIntervalSince1970: 1_795_600_000.125),
                    customMetadata: ["unchanged": "shared-codec"],
                    unknownFields: ["futureItem": .object(["number": .number(9_007_199_254_740_992),
                                                         "unicode": .string("א 😀 / +")])])
                let anchor = try PinkhaSemanticTextAnchor(spaceID: space, objectID: object, id: UUID(uuidString: uuid)!)
                let linked = try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: item, location: location)
                records.append(.init(location: location, item: linked, unknownFields: ["futureRecord": .bool(true)]))
            }
            value = try TorahAssociationPayloadCodec().encodeCanonicalDocument(
                .init(records: records, unknownFields: ["futureEnvelope": .array([.null, .number(1.25), .string("exact")])]))
        }
        let plan = try TorahLegacyAssociationCutoverPlan(spaceID: space, objectID: object, propertyKey: key, propertyValue: value)
        let wire = try plan.wireData()
        guard wire.count <= 4_194_304 else { throw NSError(domain: "PinkhaCutoverFixture", code: 2) }
        try FileHandle.standardOutput.write(contentsOf: wire)
    }
}
