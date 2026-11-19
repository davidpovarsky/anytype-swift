import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

/// One canonical descriptor shared by both native host bindings.
public enum PinkhaHanlinCreatePageTool {
    public static func make() throws -> HanlinHostTool {
        let logical = HanlinLogicalToolID(providerInstanceID: try .init(validating: "anytype.host"),
                                         localToolID: try .init(validating: "create-page"))
        let descriptorRevision = try HanlinDescriptorRevision(1)
        let schema = try HanlinJSONSchemaDocument.decodeCanonicalJSON(
            Data(#"{"type":"object","properties":{"title":{"type":"string","minLength":1,"maxLength":512}},"required":["title"],"additionalProperties":false}"#.utf8),
            defaultDialect: .draft2020_12)
        let descriptor = HanlinToolDescriptor(logicalID: logical, descriptorRevision: descriptorRevision, owner: .system,
            title: try .init(["en": "Create a page", "he": "יצירת דף"]),
            summary: try .init(["en": "Create one new standard page with a nonblank title of at most 512 UTF-8 bytes in the original Space, after exact native confirmation. No body or existing-object edits."]),
            inputSchema: schema, risk: .write, presentation: .init())
        return .init(route: .init(alias: PinkhaHanlinCreatePagePlan.alias, logicalToolID: logical,
                                     descriptorRevision: descriptorRevision), descriptor: descriptor,
                          writeGuarantee: .independentObjectCreation)
    }
}
