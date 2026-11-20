import Foundation
import Testing
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

@Suite("Native conditional property fences and archive request contracts")
struct AnyConditionalPropertyFenceTests {
    private let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")
    private let schema = try! AnyHierarchySchema(
        collectionID: "wiki", parentPropertyID: "parent", positionPropertyID: "pos", folderPropertyID: "folder")

    private func row(_ memberships: [AnyJSON] = [.string("wiki")]) -> AnyJSON {
        .object(["id": .string("document"), "spaceId": .string("space"), "_applySeq": .integer(7),
                 "_ver": .object(["id": .string("v1"), "any": .object(["collections": .string("v1")]),
                                  "modifiedAt": .string("v3"), "modifiedBy": .string("v3")]),
                 "any": .object(["type": .string("page"), "collections": .array(memberships)]),
                 "future": .object(["unknown": .array([.integer(19), .string("שלום")])])])
    }

    private func capabilities(noop: AnyJSON? = .integer(1)) -> AnyJSON {
        var value: [String: AnyJSON] = [
            "contract": .string("pinkha-torah-native-v1"),
            "conditionalPropertiesSet": .integer(1), "conditionalMembershipSet": .integer(1),
            "conditionalPropertiesApplySeq": .integer(1)]
        value["conditionalPropertiesNoop"] = noop
        return .object(value)
    }

    private func request(_ record: AnyJSON, archived: Bool,
                         capabilities: AnyJSON? = nil) throws -> AnyHierarchyArchiveRequest {
        try .init(record: record, objectID: "document", workspace: workspace, schema: schema,
                  archived: archived, engineStartedAt: "original-run", capabilities: capabilities ?? self.capabilities())
    }

    @Test func fenceRoundTripRetainsExactRequiredNativeMetadata() throws {
        let original = row()
        let fence = try AnyConditionalPropertyFence(record: original, engineStartedAt: "original-run")
        let restored = try JSONDecoder().decode(AnyConditionalPropertyFence.self, from: JSONEncoder().encode(fence))
        #expect(restored == fence)
        let body = restored.requestBody(patch: ["name": .string("renamed")])
        #expect(Set(try #require(body.object).keys) == ["patch", "ifVersion", "ifApplySeq", "ifStartedAt"])
        #expect(body["ifVersion"] == original["_ver"])
        #expect(body["ifApplySeq"] == .integer(7))
        #expect(body["ifStartedAt"] == .string("original-run"))
        #expect(body["future"] == nil)
    }

    @Test func lateSameVersionContentHasDifferentCapturedFence() throws {
        let original = row()
        var changed = try #require(original.object)
        changed["_applySeq"] = .integer(8)
        var any = try #require(changed["any"]?.object)
        any["collections"] = .array([.string("wiki"), .string("late-collection")])
        changed["any"] = .object(any)
        let first = try AnyConditionalPropertyFence(record: original, engineStartedAt: "run")
        let later = try AnyConditionalPropertyFence(record: .object(changed), engineStartedAt: "run")
        #expect(first.nativeVersion == later.nativeVersion)
        #expect(first != later)
        #expect(first.requestBody(patch: [:])["ifApplySeq"] == .integer(7))
        // This checks client capture only. The combined native CRDT witness is a separate test.
    }

    @Test func sequenceMustRemainAnExactPositiveRepresentableInteger() throws {
        for invalid in [AnyJSON.null, .integer(0), .integer(-1), .number(7), .number(7.5),
                        .number(Double.greatestFiniteMagnitude), .bool(true), .string("7")] {
            var value = try #require(row().object); value["_applySeq"] = invalid
            #expect(throws: AnyEngineError.self) {
                try AnyConditionalPropertyFence(record: .object(value), engineStartedAt: "run")
            }
        }
        var missing = try #require(row().object); missing.removeValue(forKey: "_applySeq")
        #expect(throws: AnyEngineError.self) {
            try AnyConditionalPropertyFence(record: .object(missing), engineStartedAt: "run")
        }
        var largest = try #require(row().object); largest["_applySeq"] = .integer(Int64.max)
        #expect(try AnyConditionalPropertyFence(record: .object(largest), engineStartedAt: "run").applySequence == Int64.max)
    }

    @Test func malformedVersionAndRunCannotBecomeAConditionalFence() throws {
        for version in [AnyJSON.null, .string("v1"), .object([:]), .object(["field": .integer(1)])] {
            #expect(throws: AnyEngineError.self) {
                try AnyConditionalPropertyFence(nativeVersion: version, applySequence: 1, engineStartedAt: "run")
            }
        }
        for run in ["", String(repeating: "x", count: 129), "bad\u{0000}run"] {
            #expect(throws: AnyEngineError.self) {
                try AnyConditionalPropertyFence(record: row(), engineStartedAt: run)
            }
        }
    }

    @Test func decodingCannotBypassRequiredFenceFieldsOrValidation() throws {
        let fence = try AnyConditionalPropertyFence(record: row(), engineStartedAt: "run")
        let original = try #require(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(fence)).object)
        for key in ["nativeVersion", "applySequence", "engineStartedAt"] {
            var missing = original; missing.removeValue(forKey: key)
            let data = try JSONEncoder().encode(AnyJSON.object(missing))
            #expect(throws: (any Error).self) { try JSONDecoder().decode(AnyConditionalPropertyFence.self, from: data) }
        }
        var forged = original; forged["applySequence"] = .integer(0)
        let data = try JSONEncoder().encode(AnyJSON.object(forged))
        #expect(throws: AnyEngineError.self) { try JSONDecoder().decode(AnyConditionalPropertyFence.self, from: data) }
    }

    @Test func archivePreservesExactUnknownMembershipOrderAndOriginalFence() throws {
        let original = row(["future-b", "wiki", "future-a"].map(AnyJSON.string))
        let result = try request(original, archived: true)
        #expect(result.isNoop == false)
        #expect(result.path == ["v1", "spaces", "space", "pinkha", "properties", "document", "set", "any"])
        #expect(result.body["patch"] == .object([
            "collections": .array(["future-b", "wiki", "future-a", "bin"].map(AnyJSON.string))]))
        #expect(result.body["ifVersion"] == original["_ver"])
        #expect(result.body["ifApplySeq"] == original["_applySeq"])
        #expect(result.body["ifStartedAt"] == .string("original-run"))
        #expect(result.body["future"] == nil)
        #expect(original["any"]?["collections"] == .array(["future-b", "wiki", "future-a"].map(AnyJSON.string)))
    }

    @Test func restoreRemovesOnlyBinWithoutSortingOtherMemberships() throws {
        let result = try request(row(["future-b", "bin", "wiki", "future-a"].map(AnyJSON.string)), archived: false)
        #expect(result.isNoop == false)
        #expect(result.body["patch"] == .object([
            "collections": .array(["future-b", "wiki", "future-a"].map(AnyJSON.string))]))
    }

    @Test func identicalArchiveAndRestoreStillProduceFencedNativeRequests() throws {
        for (memberships, archived) in [(["future", "bin", "wiki"], true), (["future", "wiki"], false)] {
            let result = try request(row(memberships.map(AnyJSON.string)), archived: archived)
            #expect(result.isNoop)
            #expect(result.body["patch"] == .object([:]))
            #expect(result.body["ifApplySeq"] == .integer(7))
            #expect(result.body["ifStartedAt"] == .string("original-run"))
            #expect(result.path.contains("pinkha"))
        }
    }

    @Test func absentOrMalformedNoopCapabilityCannotChooseAWriteFallback() throws {
        for invalid in [AnyJSON.null, .integer(0), .integer(2), .number(1), .bool(true), .string("1")] {
            #expect(throws: AnyEngineError.self) {
                try request(row([.string("wiki"), .string("bin")]), archived: true,
                            capabilities: capabilities(noop: invalid))
            }
        }
        #expect(throws: AnyEngineError.self) {
            try request(row(), archived: false, capabilities: capabilities(noop: nil))
        }
        // A real membership change requires the strict sequence capability but not a no-op capability.
        #expect(try request(row(), archived: true, capabilities: capabilities(noop: nil)).isNoop == false)
    }

    @Test func everyMembershipRequestRequiresTheExplicitSequenceContract() throws {
        for archived in [true, false] {
            for invalid in [AnyJSON.null, .integer(0), .integer(2), .number(1), .bool(true), .string("1")] {
                var caps = try #require(capabilities().object)
                caps["conditionalPropertiesApplySeq"] = invalid
                #expect(throws: AnyEngineError.self) {
                    try request(row(), archived: archived, capabilities: .object(caps))
                }
            }
        }
        for key in ["contract", "conditionalPropertiesSet", "conditionalMembershipSet"] {
            var caps = try #require(capabilities().object); caps.removeValue(forKey: key)
            #expect(throws: AnyEngineError.self) { try request(row(), archived: true, capabilities: .object(caps)) }
        }
    }

    @Test func malformedMembershipOrScopeCannotDispatchAnArchivePlan() throws {
        let arrays: [[AnyJSON]] = [
            [], [.string("future")], [.string("wiki"), .string("wiki")],
            [.string("wiki"), .string("template")], [.string("wiki"), .integer(3)],
            [.string("wiki"), .string("")]]
        for values in arrays {
            #expect(throws: AnyHierarchyError.malformedRow("document")) {
                try request(row(values), archived: true)
            }
        }
        for (key, value) in [("id", "foreign"), ("spaceId", "foreign-space")] {
            var invalid = try #require(row().object); invalid[key] = .string(value)
            #expect(throws: AnyHierarchyError.malformedRow("document")) {
                try request(.object(invalid), archived: true)
            }
        }
    }

    @Test func legacyOrDifferentRunNativePatchRefusesBeforeNetworking() async throws {
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account")
        let store = try AnyGuardedHTTPHierarchyRecordStore(client: client, workspace: workspace,
                                                          schema: schema, engineStartedAt: "new-run")
        await #expect(throws: AnyEngineError.self) {
            try await store.patch(objectID: "document", ownerID: "any", values: ["name": .string("new")],
                                  expectedVersion: row()["_ver"]!, authorize: {})
        }
        await #expect(throws: AnyEngineError.self) {
            try await store.patch(objectID: "document", ownerID: "any", values: ["name": .string("new")], authorize: {})
        }
        let old = try AnyConditionalPropertyFence(record: row(), engineStartedAt: "old-run")
        await #expect(throws: AnyHierarchyError.stalePlan("document")) {
            try await store.patch(objectID: "document", ownerID: "any", values: ["name": .string("new")],
                                  fence: old, authorize: {})
        }
    }
}
