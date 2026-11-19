import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
@testable import PinkhaAnyUI

@Suite("Unmapped input remains review data without write authority")
@MainActor struct AnyNativeUnmappedRecoveryTests {
    private func buffer() throws -> AnyNativeUnmappedTextDraft {
        let base = try AnyEditorBlock(native: .object(["id": .string("block"), "type": .string("paragraph"),
            "text": .string("**ab** cd"), "nav": .object(["parentId": .string(""), "pos": .string("PPPP")]),
            "style": .object(["future": .object(["exact": .integer(9_007_199_254_740_993)])]),
            "_ver": .object(["text": .string("original-version")])]))
        return try .init(base: base, baselineSource: "**ab** cd", display: "aZd",
                         selection: .init(location: 2, length: 0), reason: "unsupported crossing")
    }
    @Test func exactUnmappedBufferAndBaseSurviveNewOwnerWithoutTypedDraft() throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let recovery = AnyNativeLibraryRecovery(workspace: workspace), item = try buffer()
        try recovery.save(.init(workspace: workspace, objectID: "document", drafts: [],
            selectedBlockIDs: ["block"], focusedBlockID: "block", selection: item.selection, unmappedDrafts: [item]))
        let restored = try #require(try recovery.document("document", workspace: workspace))
        #expect(restored.drafts.isEmpty && restored.unmappedDrafts == [item])
        #expect(restored.unmappedDrafts[0].baseNative["_ver"]?["text"] == .string("original-version"))
        #expect(restored.unmappedDrafts[0].baseNative["style"]?["future"]?["exact"] == .integer(9_007_199_254_740_993))
    }
    @Test func crossAccountAndDuplicateUnmappedIdentitiesAreRefused() throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let recovery = AnyNativeLibraryRecovery(workspace: workspace), item = try buffer()
        #expect(throws: AnyNativeRecoveryError.wrongWorkspace) {
            try recovery.document("document", workspace: AnyTorahWorkspace(accountID: "other", spaceID: "space"))
        }
        #expect(throws: AnyNativeRecoveryError.invalidSnapshot) {
            try AnyNativeDocumentRecoverySnapshot(workspace: workspace, objectID: "document", drafts: [],
                selectedBlockIDs: [], focusedBlockID: nil, selection: .init(location: 0, length: 0), unmappedDrafts: [item, item])
        }
    }
}
