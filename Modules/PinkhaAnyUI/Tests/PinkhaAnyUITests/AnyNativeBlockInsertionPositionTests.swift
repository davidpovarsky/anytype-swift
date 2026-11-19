import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyHost
@testable import PinkhaAnyUI

@Suite("Quote insertion keeps the last visible block's parent")
struct AnyNativeBlockInsertionPositionTests {
    private func block(_ id: String, parent: String = "", position: String) -> AnyJSON {
        .object(["id": .string(id), "type": .string("paragraph"), "text": .string(id),
            "nav": .object(["parentId": .string(parent), "pos": .string(position)]),
            "_ver": .object(["text": .string("v1")])])
    }
    private func snapshot(_ rows: [AnyJSON]) throws -> AnyEditorSnapshot {
        try .init(spaceID: "space", objectID: "document", title: "", response: .object([
            "records": .array(rows), "total": .integer(Int64(rows.count)), "hasNext": .bool(false)]))
    }
    @Test func quoteAppendsAfterNestedDepthFirstTailWhileParagraphStaysRoot() throws {
        let value = try snapshot([block("root", position: "PPPP"),
            block("child", parent: "root", position: "PPPP"),
            block("tail", parent: "child", position: "PPPP")])
        let quote = try AnyNativeBlockInsertionPosition.resolve(snapshot: value, policy: .afterLastVisibleBlock)
        #expect(quote.parentID == "child" && quote.position > "PPPP")
        let paragraph = try AnyNativeBlockInsertionPosition.resolve(snapshot: value, policy: .endOfRoot)
        #expect(paragraph.parentID == "" && paragraph.position > "PPPP")
    }
    @Test func targetedQuoteStaysBeforeTargetInSameParent() throws {
        let value = try snapshot([block("root", position: "PPPP"),
            block("first", parent: "root", position: "AAAA"),
            block("target", parent: "root", position: "PPPP")])
        let result = try AnyNativeBlockInsertionPosition.resolve(snapshot: value, policy: .beforeBlock("target"))
        #expect(result.parentID == "root" && result.position > "AAAA" && result.position < "PPPP")
    }
    @Test func unreachableBlocksCannotBecomeInsertionTargetsOrVisibleTail() throws {
        let value = try snapshot([block("visible", position: "PPPP"),
            block("orphan", parent: "missing", position: "zzzz")])
        let result = try AnyNativeBlockInsertionPosition.resolve(snapshot: value, policy: .afterLastVisibleBlock)
        #expect(result.parentID == "" && result.position > "PPPP")
        #expect(throws: AnyHostError.invalidSelection) {
            try AnyNativeBlockInsertionPosition.resolve(snapshot: value, policy: .beforeBlock("orphan"))
        }
    }
    @Test func emptyQuoteInsertionHasAValidRootPosition() throws {
        let result = try AnyNativeBlockInsertionPosition.resolve(snapshot: snapshot([]), policy: .afterLastVisibleBlock)
        #expect(result.parentID.isEmpty && !result.position.isEmpty)
    }
}
