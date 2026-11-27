import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

@Suite("Native editor creation location limits")
struct AnyNativeBlockLocationLimitTests {
    private let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")

    private func intent(parent: String, position: String) throws -> AnyNativeBlockCreationIntent {
        try .init(workspace: workspace, mutationID: String(repeating: "a", count: 32),
                  objectID: "document", type: "paragraph", text: "",
                  parentID: parent, position: position)
    }

    @Test func inclusiveNativeParentAndPositionLimitsSurviveEncoding() throws {
        let parent = String(repeating: "P", count: 256)
        let position = String(repeating: "Q", count: 256)
        let value = try intent(parent: parent, position: position)
        #expect(value.parentID == parent)
        #expect(value.position == position)
        let bytes = try JSONEncoder().encode(value)
        let decoded = try JSONDecoder().decode(AnyNativeBlockCreationIntent.self, from: bytes)
        #expect(decoded == value)
        #expect(decoded.identity == value.identity)
        let root = try intent(parent: "", position: position)
        #expect(root.parentID.isEmpty)
        #expect(root.position == position)
    }

    @Test func oversizedLocationsAreRefusedBeforeAnIntentCanBeDispatched() throws {
        for length in [257, 1024] {
            let oversized = String(repeating: "P", count: length)
            // The generic read/identity envelope intentionally remains broader.
            #expect(AnyEditorBlock.validID(oversized))
            #expect(throws: AnyNativeCreationError.invalidIntent) {
                try intent(parent: oversized, position: "Q")
            }
            #expect(throws: AnyNativeCreationError.invalidIntent) {
                try intent(parent: "", position: oversized)
            }
        }
    }
}
