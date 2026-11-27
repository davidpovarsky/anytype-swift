import Foundation
import PinkhaKit
import PinkhaAnyIntegration

/// A scoped source-side template. The native destination object ID does not
/// exist yet; the executor resolves it before constructing a prepared block.
public struct AnyDestinationAnchoredText: Codable, Equatable, Sendable {
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let inlineMarkdown: String

    public init(sourceSpaceID: String, sourceObjectID: String, inlineMarkdown: String) throws {
        guard inlineMarkdown.utf8.count <= 65_536 else { throw PinkhaSemanticTextAnchorError.limitExceeded }
        let projected = AnyInlineMarkdown(inlineMarkdown)
        let semantic = try projected.semanticText()
        guard !semantic.marks.isEmpty else { throw PinkhaSemanticTextAnchorError.invalidMarker }
        guard semantic.marks.allSatisfy({ $0.anchor.belongsTo(spaceID: sourceSpaceID, objectID: sourceObjectID) }) else {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
        self.sourceSpaceID = sourceSpaceID; self.sourceObjectID = sourceObjectID; self.inlineMarkdown = inlineMarkdown
    }

    private enum CodingKeys: String, CodingKey { case sourceSpaceID, sourceObjectID, inlineMarkdown }
    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(sourceSpaceID: values.decode(String.self, forKey: .sourceSpaceID),
                      sourceObjectID: values.decode(String.self, forKey: .sourceObjectID),
                      inlineMarkdown: values.decode(String.self, forKey: .inlineMarkdown))
    }

    public func resolved(destinationSpaceID: String, destinationObjectID: String) throws -> String {
        try AnyInlineMarkdown(inlineMarkdown).remappingSemanticAnchors(
            sourceSpaceID: sourceSpaceID, sourceObjectID: sourceObjectID,
            destinationSpaceID: destinationSpaceID, destinationObjectID: destinationObjectID)
    }
}

/// Remaps an already decoded, original-location association through the same
/// strict marker contract used by both editors. No source/quote metadata,
/// provider payload, association ID or anchor UUID is regenerated.
public enum AnySemanticAnchorAssociationMigration {
    public static func remapping(_ item: TorahAssociationItem, source: TorahAssociationLocation,
                                 destination: TorahAssociationLocation) throws -> TorahAssociationItem {
        try AnyTorahSemanticAnchorMigration.remapping(item, source: source, destination: destination)
    }
}
