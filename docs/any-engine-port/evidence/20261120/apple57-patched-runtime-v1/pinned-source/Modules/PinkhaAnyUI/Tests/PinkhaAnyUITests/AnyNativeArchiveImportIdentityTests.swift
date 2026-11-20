import Foundation
import Testing
import PinkhaAnyIntegration
@testable import PinkhaAnyUI

@Suite("Canonical archive UI retry identity")
struct AnyNativeArchiveImportIdentityTests {
    private let digest = String(repeating: "a", count: 64)
    @Test func reopeningTheSameReviewedMappingUsesTheSameStableIdentity() throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let first = try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest, workspace: workspace,
            objectID: "document", blockMap: ["a": "block-a", "b": "block-b"], objectMap: ["note": "native-note"])
        let second = try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest, workspace: workspace,
            objectID: "document", blockMap: ["b": "block-b", "a": "block-a"], objectMap: ["note": "native-note"])
        #expect(first == second)
        #expect(first.count == 64)
    }
    @Test func everyScopeAndReviewedMappingPartSeparatesTheIdentity() throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let base = try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest, workspace: workspace,
            objectID: "document", blockMap: ["source": "target"], objectMap: ["old-note": "note-a"])
        let variants = [
            try AnyNativeArchiveImportIdentity.key(archiveSHA256: String(repeating: "b", count: 64), workspace: workspace,
                objectID: "document", blockMap: ["source": "target"], objectMap: ["old-note": "note-a"]),
            try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest, workspace: workspace,
                objectID: "other", blockMap: ["source": "target"], objectMap: ["old-note": "note-a"]),
            try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest, workspace: workspace,
                objectID: "document", blockMap: ["source": "other-block"], objectMap: ["old-note": "note-a"]),
            try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest, workspace: workspace,
                objectID: "document", blockMap: ["source": "target"], objectMap: ["old-note": "note-b"]),
            try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest,
                workspace: AnyTorahWorkspace(accountID: "other", spaceID: "space"),
                objectID: "document", blockMap: ["source": "target"], objectMap: ["old-note": "note-a"])
        ]
        #expect(variants.allSatisfy { $0 != base })
        #expect(Set(variants).count == variants.count)
    }
    @Test func malformedDigestAndUnreviewableIDsAreRefused() throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        #expect(throws: (any Error).self) {
            try AnyNativeArchiveImportIdentity.key(archiveSHA256: "truncated", workspace: workspace,
                objectID: "document", blockMap: [:], objectMap: [:])
        }
        #expect(throws: (any Error).self) {
            try AnyNativeArchiveImportIdentity.key(archiveSHA256: digest, workspace: workspace,
                objectID: "document", blockMap: ["": "target"], objectMap: [:])
        }
    }
}
