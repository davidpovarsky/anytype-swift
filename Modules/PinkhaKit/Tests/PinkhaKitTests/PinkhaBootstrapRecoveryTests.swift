import Foundation
import Testing
@testable import PinkhaKit

@Suite("PinkhaBootstrapRecoveryTests")
struct PinkhaBootstrapRecoveryTests {
    @Test("A later activation retries a failed read and rejects the old completion")
    func failureCanBeRetriedWithoutStaleCompletion() throws {
        let state = PinkhaBootstrapStateStorage()
        let old = try #require(state.beginProvisioningClaim(spaceId: "space"))
        #expect(state.setState(.failed("temporary native read failure"), for: "space", claim: old))
        let retry = try #require(state.beginProvisioningClaim(spaceId: "space"))
        #expect(retry != old)
        #expect(!state.setState(.ready(.initial(spaceId: "space")), for: "space", claim: old))
        #expect(state.state(for: "space") == .provisioning)
        #expect(state.setState(.ready(.initial(spaceId: "space")), for: "space", claim: retry))
        #expect(state.beginProvisioningClaim(spaceId: "space") == nil)
    }

    @Test("Concurrent retries admit exactly one owner after a failure")
    func concurrentRetryHasOneOwner() async throws {
        let state = PinkhaBootstrapStateStorage()
        state.setState(.failed("temporary read failure"), for: "space")
        let claims = await withTaskGroup(of: UUID?.self, returning: [UUID].self) { group in
            for _ in 0..<64 {
                group.addTask { state.beginProvisioningClaim(spaceId: "space") }
            }
            var result: [UUID] = []
            for await claim in group { if let claim { result.append(claim) } }
            return result
        }
        #expect(claims.count == 1)
        #expect(state.state(for: "space") == .provisioning)
        #expect(state.beginProvisioningClaim(spaceId: "space") == nil)
    }

    @Test("Account reset revokes an old claim even when the Space is selected again")
    func accountResetRejectsOldClaim() throws {
        let state = PinkhaBootstrapStateStorage()
        let old = try #require(state.beginProvisioningClaim(spaceId: "space"))
        state.resetForAccountChange()
        let fresh = try #require(state.beginProvisioningClaim(spaceId: "space"))
        #expect(!state.setState(.failed("old account failure"), for: "space", claim: old))
        #expect(state.state(for: "space") == .provisioning)
        #expect(state.setState(.ready(.initial(spaceId: "space")), for: "space", claim: fresh))
    }

    @Test("A different Space never shares a provisioning claim")
    func spacesRemainIndependent() throws {
        let state = PinkhaBootstrapStateStorage()
        let first = try #require(state.beginProvisioningClaim(spaceId: "first"))
        let second = try #require(state.beginProvisioningClaim(spaceId: "second"))
        #expect(first != second)
        #expect(!state.setState(.ready(.initial(spaceId: "second")), for: "second", claim: first))
        #expect(state.state(for: "first") == .provisioning)
        #expect(state.state(for: "second") == .provisioning)
    }

    @Test("Missing and malformed native payloads cannot become absence")
    func unreadableExistingManifestThrows() throws {
        for payload in [nil, "", "{not valid JSON}"] as [String?] {
            #expect(throws: (any Error).self) {
                try PinkhaSpaceManifest.fromStoredJSONString(payload, objectId: "manifest", spaceId: "space")
            }
        }
    }

    @Test("A fresh native read validates both Space and self identity")
    func nativeIdentityCannotBeRelabelled() throws {
        var value = PinkhaSpaceManifest.initial(spaceId: "space")
        value.manifestObjectId = "manifest"
        let raw = try value.toJSONString()
        #expect(throws: PinkhaBootstrapError.self) {
            try PinkhaSpaceManifest.fromStoredJSONString(raw, objectId: "other", spaceId: "space")
        }
        #expect(throws: PinkhaBootstrapError.self) {
            try PinkhaSpaceManifest.fromStoredJSONString(raw, objectId: "manifest", spaceId: "other")
        }
        #expect(try PinkhaSpaceManifest.fromStoredJSONString(raw, objectId: "manifest", spaceId: "space") == value)
    }

    @Test("Legacy missing self identity binds only to the observed native root")
    func legacySelfIdentityBindsWithoutChangingSchema() throws {
        let value = PinkhaSpaceManifest.initial(spaceId: "space")
        let decoded = try PinkhaSpaceManifest.fromStoredJSONString(
            value.toJSONString(), objectId: "manifest", spaceId: "space")
        #expect(decoded.manifestObjectId == "manifest")
        #expect(decoded.spaceId == value.spaceId)
        #expect(decoded.schemaVersion == value.schemaVersion)
        #expect(decoded.provisioningState == .inProgress)
        #expect(decoded.registeredDocumentTypes == value.registeredDocumentTypes)
    }

    @Test("A newer schema still fails migration after a valid native read")
    func newerSchemaIsNotRepairedOrHidden() throws {
        var value = PinkhaSpaceManifest.initial(spaceId: "space")
        value.manifestObjectId = "manifest"
        value.schemaVersion = 99
        let decoded = try PinkhaSpaceManifest.fromStoredJSONString(
            value.toJSONString(), objectId: "manifest", spaceId: "space")
        #expect(decoded.schemaVersion == 99)
        #expect(throws: PinkhaSchemaMigrationError.self) {
            try PinkhaSchemaMigrator().migrate(manifest: decoded)
        }
    }
}
