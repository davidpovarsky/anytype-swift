import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost
@testable import PinkhaAnyUI

@Suite("Native UI recovery is scoped and never grants write authority")
@MainActor
struct AnyNativeLibraryRecoveryTests {
    private func workspace(_ account: String = "account", _ space: String = "space") throws -> AnyTorahWorkspace {
        try .init(accountID: account, spaceID: space)
    }
    private func block(text: String = "old", version: String = "v1",
                       type: String = "paragraph") throws -> AnyEditorBlock {
        try .init(native: .object(["id": .string("block"), "type": .string(type),
            "text": .string(text), "nav": .object(["parentId": .string(""), "pos": .string("PPPP")]),
            "style": .object(["future": .object(["exact": .integer(9_007_199_254_740_993)])]),
            "_ver": .object(["text": .string(version), "style": .object(["future": .string("style-v1")])])]))
    }
    private func draft() throws -> AnyNativeRecoveredBlockDraft {
        try .init(base: block(), inlineMarkdown: "שלום 😀", selection: .init(location: 7, length: 0),
                  revision: 3)
    }
    private func snapshot(_ objectID: String = "document",
                          workspace supplied: AnyTorahWorkspace? = nil) throws -> AnyNativeDocumentRecoverySnapshot {
        try .init(workspace: supplied ?? workspace(), objectID: objectID,
                  drafts: [draft()], selectedBlockIDs: ["block"], focusedBlockID: "block",
                  selection: .init(location: 7, length: 0))
    }
    @Test func newRuntimeOwnerCanReadExactDraftAndNavigationWithoutAnyServices() throws {
        let scope = try workspace()
        let recovery = AnyNativeLibraryRecovery(workspace: scope)
        let value = try snapshot()
        try recovery.save(value)
        try recovery.replaceNavigation([.folder("folder"), .document("document", "block")], workspace: scope)
        let restored = try #require(try recovery.document("document", workspace: scope))
        #expect(restored.drafts == value.drafts)
        #expect(restored.drafts[0].baseNative["style"]?["future"]?["exact"] == .integer(9_007_199_254_740_993))
        #expect(restored.selectedBlockIDs == ["block"])
        #expect(recovery.navigation == [.folder("folder"), .document("document", "block")])
    }
    @Test func crossAccountAndCrossSpaceReadSaveNavigationAndDiscardAreDenied() throws {
        let recovery = AnyNativeLibraryRecovery(workspace: try workspace())
        try recovery.save(snapshot())
        for foreign in [try workspace("other"), try workspace("account", "other")] {
            #expect(throws: AnyNativeRecoveryError.wrongWorkspace) {
                try recovery.document("document", workspace: foreign)
            }
            #expect(throws: AnyNativeRecoveryError.wrongWorkspace) {
                try recovery.save(snapshot(workspace: foreign))
            }
            #expect(throws: AnyNativeRecoveryError.wrongWorkspace) {
                try recovery.replaceNavigation([.notes], workspace: foreign)
            }
            #expect(throws: AnyNativeRecoveryError.wrongWorkspace) {
                try recovery.discardDocument("document", workspace: foreign)
            }
        }
        #expect(try recovery.document("document", workspace: workspace()) != nil)
    }
    @Test func lateNativeCommitIsRecognizedWithoutAnotherWrite() throws {
        let value = try draft()
        #expect(AnyNativeDraftReconciliation.evaluate(value,
            current: try block(text: "שלום 😀", version: "late-commit"), reachable: true) == .alreadyStored)
    }
    @Test func unchangedBaseStillRequiresManualReviewAndABARemainsConflict() throws {
        let value = try draft()
        #expect(AnyNativeDraftReconciliation.evaluate(value,
            current: try block(), reachable: true) == .requiresReview)
        #expect(AnyNativeDraftReconciliation.evaluate(value,
            current: try block(version: "A-to-B-to-A"), reachable: true) == .conflict)
        #expect(AnyNativeDraftReconciliation.evaluate(value,
            current: try block(text: "remote", version: "v2"), reachable: true) == .conflict)
    }
    @Test func missingOrUnreachableBlocksRetainDraftAsConflict() throws {
        let value = try draft()
        #expect(AnyNativeDraftReconciliation.evaluate(value, current: nil, reachable: false) == .conflict)
        #expect(AnyNativeDraftReconciliation.evaluate(value,
            current: try block(text: value.inlineMarkdown), reachable: false) == .conflict)
    }
    @Test func invalidSelectionAndMultipartRecoveryAreRefused() throws {
        #expect(throws: (any Error).self) {
            try AnyNativeRecoveredBlockDraft(base: block(), inlineMarkdown: "😀",
                selection: .init(location: 1, length: 0), revision: 0)
        }
        #expect(throws: AnyNativeRecoveryError.invalidSnapshot) {
            try AnyNativeDocumentRecoverySnapshot(workspace: workspace(), objectID: "document",
                dataset: "other-part", drafts: [draft()], selectedBlockIDs: [], focusedBlockID: nil,
                selection: .init(location: 0, length: 0))
        }
    }
    @Test func scalarBoundariesAreValidatedOnDisplayedAndCodeText() throws {
        for (base, source) in [(try block(), "**😀**"), (try block(type: "code"), "😀")] {
            for range in [NSRange(location: 1, length: 0), NSRange(location: 0, length: 1),
                          NSRange(location: 1, length: 1)] {
                #expect(throws: AnyNativeRecoveryError.invalidSnapshot) {
                    try AnyNativeRecoveredBlockDraft(base: base, inlineMarkdown: source,
                        selection: range, revision: 0)
                }
            }
            for range in [NSRange(location: 0, length: 0), NSRange(location: 0, length: 2),
                          NSRange(location: 2, length: 0)] {
                let value = try AnyNativeRecoveredBlockDraft(base: base, inlineMarkdown: source,
                    selection: range, revision: 0)
                #expect(value.selection == range)
                #expect(value.inlineMarkdown == source)
            }
        }
    }
    @Test func capacityFailureNeverEvictsOlderUnsavedContent() throws {
        let recovery = AnyNativeLibraryRecovery(workspace: try workspace())
        for index in 0..<128 { try recovery.save(snapshot("document-\(index)")) }
        #expect(throws: AnyNativeRecoveryError.capacityExceeded) { try recovery.save(snapshot("overflow")) }
        #expect(try recovery.document("document-0", workspace: workspace())?.drafts == [draft()])
    }
}
