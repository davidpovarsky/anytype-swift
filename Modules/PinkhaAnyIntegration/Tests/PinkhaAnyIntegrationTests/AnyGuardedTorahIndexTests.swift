
import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

@Suite("Native indexed source and expanded related contracts")
struct AnyGuardedTorahIndexTests {
    private let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")
    private let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 1:1")
    private var base: [String: AnyJSON] {
        ["contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
         "identity": .string(source.indexValue), "coverage": .string("complete"),
         "unsupportedClaimsPresent": .bool(false),
         "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                                "generation": .string(String(repeating: "a", count: 64))])]
    }
    private func row(_ object: String = "document", block: String? = nil,
                     contexts: [String] = ["context"], quotes: [String] = [], unlink: Bool = true) -> AnyJSON {
        var v: [String: AnyJSON] = [
            "spaceId": .string("space"), "objectId": .string(object),
            "contextItemIds": .array(contexts.map(AnyJSON.string)),
            "sourceQuoteItemIds": .array(quotes.map(AnyJSON.string)),
            "canSafelyUnlink": .bool(unlink),
            "semanticInputSHA256": .string(String(repeating: "b", count: 64))]
        if let block { v["blockId"] = .string(block) }
        return .object(v)
    }

    @Test func nativeIdentityAndDocumentBlockQuoteTargetsStayDistinct() throws {
        #expect(source.indexValue == "torah1|3:ref|7:sefaria|11:Genesis 1:1")
        var value = base
        value["targets"] = .array([
            row(contexts: ["קשר-א"]), row(block: "block", contexts: [], quotes: ["quote-1", "quote-2"], unlink: false)])
        value["conflictingTargets"] = .array([])
        let result = try AnyGuardedTorahIndex.parseRelated(.object(value), workspace: workspace,
                                                          identity: source.indexValue, limit: 1000)
        #expect(result.readiness.complete)
        #expect(result.targets[0].canSafelyUnlink)
        #expect(result.targets[0].contextItemIDs == ["קשר-א"])
        #expect(result.targets[1].target.blockId == "block")
        #expect(result.targets[1].sourceQuoteItemIDs == ["quote-1", "quote-2"])
    }

    @Test func unsafeUnlinkAndForeignTargetAreRefused() {
        for bad in [row(block: "block"), row(quotes: ["quote"], unlink: true)] {
            var value = base; value["targets"] = .array([bad]); value["conflictingTargets"] = .array([])
            #expect(throws: AnyEngineError.self) {
                try AnyGuardedTorahIndex.parseRelated(.object(value), workspace: workspace,
                                                      identity: source.indexValue, limit: 1000)
            }
        }
        var bad = row().object!; bad["spaceId"] = .string("foreign")
        var value = base; value["targets"] = .array([.object(bad)]); value["conflictingTargets"] = .array([])
        #expect(throws: TorahAssociationRepositoryError.targetOutsideSpace) {
            try AnyGuardedTorahIndex.parseRelated(.object(value), workspace: workspace,
                                                  identity: source.indexValue, limit: 1000)
        }
    }

    @Test func incompleteNativeCoverageNeverBecomesCompleteEmptyResults() throws {
        var value = base
        value["coverage"] = .string("incomplete-unsupported-payload")
        value["unsupportedClaimsPresent"] = .bool(true)
        value["readiness"] = .object(["version": .integer(1), "state": .string("incomplete"),
                                      "generation": .string(String(repeating: "a", count: 64))])
        value["targets"] = .array([]); value["conflictingTargets"] = .array([])
        let result = try AnyGuardedTorahIndex.parseRelated(.object(value), workspace: workspace,
                                                          identity: source.indexValue, limit: 1000)
        #expect(!result.readiness.complete && result.unsupportedClaimsPresent)
        value["readiness"] = base["readiness"]
        #expect(throws: AnyEngineError.self) {
            try AnyGuardedTorahIndex.parseRelated(.object(value), workspace: workspace,
                                                  identity: source.indexValue, limit: 1000)
        }
    }

    @Test func sourceQueryRejectsWrongIdentityDuplicateIDsAndConflictAsComplete() {
        for change in [
            ["identity": AnyJSON.string("another identity")],
            ["objectIds": .array([.string("same"), .string("same")])],
            ["conflictedObjectIds": .array([.string("conflict")])]
        ] {
            var value = base
            value["field"] = .string("pinkhaSources")
            value["objectIds"] = .array([]); value["conflictedObjectIds"] = .array([])
            value.merge(change) { _, new in new }
            #expect(throws: AnyEngineError.self) {
                try AnyGuardedTorahIndex.parseSources(.object(value), field: "pinkhaSources",
                                                       identity: source.indexValue, limit: 1000)
            }
        }
    }

    @Test func exactWindowLimitAndDuplicateTargetAreEnforced() {
        var value = base; value["targets"] = .array([row(), row()]); value["conflictingTargets"] = .array([])
        #expect(throws: AnyEngineError.self) {
            try AnyGuardedTorahIndex.parseRelated(.object(value), workspace: workspace,
                                                  identity: source.indexValue, limit: 1000)
        }
        value["targets"] = .array([row(), row("another")])
        #expect(throws: AnyEngineError.self) {
            try AnyGuardedTorahIndex.parseRelated(.object(value), workspace: workspace,
                                                  identity: source.indexValue, limit: 1)
        }
    }
}
