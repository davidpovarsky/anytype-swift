import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// A dependency-closed graph for the captured current Page instances and
/// their actual schema. It cannot replace the whole-source plan: excluded
/// definition vocabulary, system heads and history remain explicitly listed.
public struct AnyHeartNativeContentComposition: Sendable {
    public let bundle: AnyHeartNativeSpaceBundle
    public let selection: AnyHeartNativeContentSelection
    public let definitions: AnyHeartNativeDefinitionPlan
    /// nil preserves the original zero-file composition and encoded material.
    public let capturedFiles: AnyHeartNativeCapturedFilePlan?
    public let pages: [AnyHeartNativePageComposition]
    public let bookmarks: [AnyHeartNativeBookmarkComposition]
    public let items: [AnyDestinationMigrationItem]
    public let coverage: [AnyDestinationCoverage]
    public let contentSHA256: String
    public var permitsWholeSourceAdmission: Bool { false }

    public init(bundle: AnyHeartNativeSpaceBundle) throws {
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: bundle)
        let selection = try AnyHeartNativeContentSelection(bundle: bundle, catalog: catalog)
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: catalog, contentSelection: selection)
        let capturedFiles: AnyHeartNativeCapturedFilePlan?
        if bundle.fileVariants.isEmpty && bundle.fileReferences.isEmpty { capturedFiles = nil }
        else { capturedFiles = try .init(bundle: bundle, catalog: catalog, selection: selection) }
        let objects = selection.objects.map {
            AnyHeartNativeDefinitionPlan.ObjectBinding(sourceObjectID: $0.sourceObjectID,
                destinationSourceKey: AnyHeartNativePageComposition.objectSourceKey(
                    spaceID: bundle.sourceSpaceID, objectID: $0.sourceObjectID))
        }
        var pages: [AnyHeartNativePageComposition] = []
        var bookmarks: [AnyHeartNativeBookmarkComposition] = []
        var objectItems: [AnyDestinationMigrationItem] = []
        for selected in selection.objects {
            guard let type = definitions.types.first(where: {
                $0.definition.objectID.utf8.elementsEqual(selected.typeObjectID.utf8)
            }) else { throw AnyHeartNativePageCompositionError.typeBinding }
            if type.definition.recommendedLayout == 11 {
                let bookmark = try AnyHeartNativeBookmarkComposition(bundle: bundle,
                    sourceObjectID: selected.sourceObjectID, definitions: definitions, objects: objects,
                    capturedFiles: capturedFiles)
                bookmarks.append(bookmark); objectItems.append(contentsOf: bookmark.items)
            } else {
                let page = try AnyHeartNativePageComposition(bundle: bundle,
                    sourceObjectID: selected.sourceObjectID, definitions: definitions, objects: objects,
                    capturedFiles: capturedFiles)
                pages.append(page); objectItems.append(contentsOf: page.items)
            }
        }
        // Keep the existing native plan phases: all identities before bodies,
        // then files/references, then immutable source facts. Stable ordering
        // within a phase retains schema dependencies and parser-owned body
        // hierarchy. The plan still rejects every unresolved earlier owner.
        let unsorted = definitions.schemaItems + objectItems + (capturedFiles?.entries.map(\.item) ?? [])
        let items = unsorted.enumerated().sorted {
            let lhs = $0.element.operation.phase, rhs = $1.element.operation.phase
            return lhs == rhs ? $0.offset < $1.offset : lhs < rhs
        }.map(\.element)
        let fixedCoverage = Dictionary(uniqueKeysWithValues:
            definitions.definitionCoverage.map { (Data($0.sourceObjectID.utf8), $0) })
        var coverage: [AnyDestinationCoverage] = []
        for sourceID in selection.executedSourceObjectIDs {
            if let fixed = fixedCoverage[Data(sourceID.utf8)] { coverage.append(fixed); continue }
            let keys = items.filter { Data($0.sourceObjectID.utf8) == Data(sourceID.utf8) }.map(\.sourceKey)
            guard !keys.isEmpty else { throw AnyDestinationMigrationError.incompleteCoverage(sourceID) }
            coverage.append(.init(sourceObjectID: sourceID, disposition: .mapped(itemSourceKeys: keys)))
        }
        struct Material: Encodable {
            let contract: String
            let sourceManifestSHA256: String
            let sourceWitnessSHA256: String
            let catalogSHA256: String
            let selectedSourceObjectIDs: [String]
            let remainingSourceObjectIDs: [String]
            let retainedAbsentDeclarations: [AnyHeartNativeContentSelection.AbsentDeclaration]
            let retainedCompiledDefinitionIDs: [String]
            let retainedWholeSourceIssues: [String]
            let pageSHA256: [String]
            let bookmarkSHA256: [String]?
            let capturedFileSHA256: String?
            let items: [AnyDestinationMigrationItem]
            let coverage: [AnyDestinationCoverage]
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(Material(contract: "pinkha-heart-current-content-composition-v1",
            sourceManifestSHA256: bundle.manifestSHA256, sourceWitnessSHA256: bundle.sourceWitnessSHA256,
            catalogSHA256: catalog.contentSHA256, selectedSourceObjectIDs: selection.executedSourceObjectIDs,
            remainingSourceObjectIDs: selection.remainingSourceObjectIDs,
            retainedAbsentDeclarations: selection.retainedAbsentDeclarations,
            retainedCompiledDefinitionIDs: selection.retainedCompiledDefinitionIDs,
            retainedWholeSourceIssues: selection.retainedWholeSourceIssues, pageSHA256: pages.map(\.contentSHA256),
            bookmarkSHA256: bookmarks.isEmpty ? nil : bookmarks.map(\.contentSHA256),
            capturedFileSHA256: capturedFiles?.contentSHA256,
            items: items, coverage: coverage))
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        self.bundle = bundle; self.selection = selection; self.definitions = definitions
        self.capturedFiles = capturedFiles
        self.pages = pages; self.bookmarks = bookmarks; self.items = items; self.coverage = coverage
        contentSHA256 = AnyContentDigest.sha256(bytes)
    }

    /// Explicit current-content execution scope. The unchanged source capture
    /// coordinator rejects this as a full migration unless its identities also
    /// equal the complete original native-head census. No count is promoted.
    public func currentContentPlan(workspace: AnyTorahWorkspace, storeID: String,
                                   planID: String) throws -> AnyDestinationMigrationPlan {
        _ = try definitions.admittedSchemaItems()
        try capturedFiles?.require(catalog: definitions.catalog)
        for page in pages { _ = try page.admittedSelectedItems(selection) }
        for bookmark in bookmarks { _ = try bookmark.admittedSelectedItems(selection) }
        let source = try AnyDestinationSourceBinding(bundle: bundle, semanticPlanSHA256: contentSHA256,
                                                     sourceObjectIDs: selection.executedSourceObjectIDs)
        return try .init(source: source, workspace: workspace, storeID: storeID, planID: planID,
                         coverage: coverage, items: items)
    }
}
