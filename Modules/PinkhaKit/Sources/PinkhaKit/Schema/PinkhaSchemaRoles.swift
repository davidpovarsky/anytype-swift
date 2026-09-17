import Foundation

/// Logical roles and identifiers for Pinkha schema components.
/// Concrete Anytype Property and Type IDs are mapped to these roles in `PinkhaSpaceManifest`.
public enum PinkhaSchemaRoles {
    // MARK: - Manifest Identity
    public static let manifestUniqueKey = "pinkha.space.manifest"
    public static let manifestName = "pinkha.space.manifest"

    // MARK: - Logical Property Roles
    public static let parentProperty = "pinkha.parent"
    public static let orderProperty = "pinkha.order"
    public static let documentAssociationsProperty = "pinkha.torahAssociations"

    // MARK: - Logical Internal Type Roles
    public static let folderType = "pinkha.folder"
    public static let bookFolderType = "pinkha.bookFolder"

    // MARK: - Default Writing Types Keys
    public static let chiddushKey = "chiddush"
    public static let articleKey = "article"
    public static let researchKey = "research"

    // MARK: - Default Type Display Names (Hebrew source of truth)
    public static let folderDefaultName = "תיקייה"
    public static let bookFolderDefaultName = "תיקיית ספרים"
    public static let chiddushDefaultName = "חידוש"
    public static let articleDefaultName = "מאמר"
    public static let researchDefaultName = "מחקר"

    // MARK: - Block Fields
    public static let blockAssociationsField = "pinkha.torah.associations.v1"
    public static let blockSourceQuoteField = "pinkha.torah.sourceQuote.v1"
    public static let blockTextDirectionField = "pinkha.textDirection.v1"
}
