import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

/// The descriptor grants no authority. A native body-capable binding must be
/// installed and ready before the router can advertise this separate route.
public enum PinkhaHanlinSaveMessageTool {
    public static func make() throws -> HanlinHostTool {
        let logical = HanlinLogicalToolID(providerInstanceID: try .init(validating: "anytype.host"),
                                         localToolID: try .init(validating: "save-message"))
        let descriptorRevision = try HanlinDescriptorRevision(1)
        let schema = try HanlinJSONSchemaDocument.decodeCanonicalJSON(
            Data(#"{"type":"object","properties":{"title":{"type":"string","minLength":1,"maxLength":512},"markdown":{"type":"string","minLength":1,"maxLength":65536}},"required":["title","markdown"],"additionalProperties":false}"#.utf8),
            defaultDialect: .draft2020_12)
        let descriptor = HanlinToolDescriptor(logicalID: logical, descriptorRevision: descriptorRevision, owner: .system,
            title: try .init(["en": "Save message as a page", "he": "שמירת הודעה כדף"]),
            summary: try .init([
                "en": "Save a complete supported Markdown message in one new standard page in the original Space after native confirmation. Title is at most 512 UTF-8 bytes; Markdown is at most 65536 UTF-8 bytes. Unsupported content is refused before writing. Success requires the original native document and complete body readback. No existing-object edits.",
                "he": "שמירת הודעת Markdown מלאה שנתמכת בדף חדש במרחב המקורי, לאחר אישור. הכותרת מוגבלת ל־512 בתים והגוף ל־65536 בתים ב־UTF-8. תוכן שאינו נתמך נדחה לפני הכתיבה. הצלחה דורשת אימות של המסמך ושל גוף ההודעה השמור."
            ]), inputSchema: schema, risk: .write, presentation: .init())
        return .init(route: .init(alias: PinkhaHanlinSaveMessagePlan.alias, logicalToolID: logical,
                                 descriptorRevision: descriptorRevision), descriptor: descriptor,
                     writeGuarantee: .independentObjectCreation)
    }
}
