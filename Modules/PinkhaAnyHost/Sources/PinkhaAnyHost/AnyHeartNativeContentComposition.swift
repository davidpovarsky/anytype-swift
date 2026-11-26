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
    public let pages: [AnyHeartNativePageComposition]
    public let items: [AnyDestinationMigrationItem]
    public let coverage: [AnyDestinationCoverage]
    public let contentSHA256: String
    public var permitsWholeSourceAdmission: Bool { false }

    public init(bundle: AnyHeartNativeSpaceBundle) throws {
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: bundle)
        let selection = try AnyHeartNativeContentSelection(bundle: bundle, catalog: catalog)
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: catalog, contentSelection: selection)
        let objects = selection.objects.map {
            AnyHeartNativeDefinitionPlan.ObjectBinding(sourceObjectID: $0.sourceObjectID,
                destinationSourceKey: AnyHeartNativePageComposition.objectSourceKey(
                    spaceID: bundle.sourceSpaceID, objectID: $0.sourceObjectID))
        }
        let pages = try selection.objects.map {
            try AnyHeartNativePageComposition(bundle: bundle, sourceObjectID: $0.sourceObjectID,
                                               definitions: definitions, objects: objects)
        }
        // All actual objects must exist before deferred references, including
        // references to a later source object and genuine cycles. Body order
        // within each page remains the original parser-owned hierarchy order.
        let currentItems = pages.flatMap(\.items)
        let creates = currentItems.filter { if case .object = $0.operation { return true }; return false }
        let updates = currentItems.filter { if case .propertyUpdate = $0.operation { return true }; return false }
        let bodies = currentItems.filter {
            switch $0.operation { case .object, .propertyUpdate: false; default: true }
        }
        let items = definitions.schemaItems + creates + bodies + updates
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
            items: items, coverage: coverage))
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        self.bundle = bundle; self.selection = selection; self.definitions = definitions
        self.pages = pages; self.items = items; self.coverage = coverage
        contentSHA256 = AnyContentDigest.sha256(bytes)
    }

    /// Explicit current-content execution scope. The unchanged source capture
    /// coordinator rejects this as a full migration unless its identities also
    /// equal the complete original native-head census. No count is promoted.
    public func currentContentPlan(workspace: AnyTorahWorkspace, storeID: String,
                                   planID: String) throws -> AnyDestinationMigrationPlan {
        _ = try definitions.admittedSchemaItems()
        for page in pages { _ = try page.admittedSelectedItems(selection) }
        let source = try AnyDestinationSourceBinding(bundle: bundle, semanticPlanSHA256: contentSHA256,
                                                     sourceObjectIDs: selection.executedSourceObjectIDs)
        return try .init(source: source, workspace: workspace, storeID: storeID, planID: planID,
                         coverage: coverage, items: items)
    }
}
