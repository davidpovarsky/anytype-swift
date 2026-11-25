import Services

/// Downstream document-list policy composed into the original query services.
/// By-ID loading, explicit type selection and the original Archive keep their
/// existing access. This filter grants no permission and changes no object data.
enum OriginalAnnotationSearchVisibility {
    static func filters(includeAnnotations: Bool = false) -> [DataviewFilter] {
        guard !includeAnnotations else { return [] }
        var filter = SearchHelper.typeUniqueKeyFilter(OriginalAnnotationNativeMetadata.originalTypeUniqueKey)
        filter.condition = .notEqual
        return [filter]
    }

    /// The original search type-token UI is an explicit opt-in, including in
    /// a cross-Space query where native type object IDs are different.
    static func includesExplicitAnnotationType(_ uniqueKey: String?) -> Bool {
        uniqueKey?.utf8.elementsEqual(OriginalAnnotationNativeMetadata.originalTypeUniqueKey.utf8) ?? false
    }
}
