import Testing
@testable import PinkhaKit

@Suite("Shared text input render ownership")
struct PinkhaTextInputRenderPolicyTests {
    @Test("A late native echo cannot erase a newer local word")
    func pendingLocalEditPreservesLiveText() {
        #expect(PinkhaTextInputRenderPolicy.action(incoming: "W", live: "Wave15 drop anchor",
            isComposing: false, hasPendingLocalChanges: true) == .preserve)
        #expect(PinkhaTextInputRenderPolicy.action(incoming: "", live: "שלום",
            isComposing: false, hasPendingLocalChanges: true) == .preserve)
    }

    @Test("Compositions survive empty, different, and identical native text",
          arguments: ["", "old", "שלום"])
    func compositionOwnsItsBuffer(incoming: String) {
        #expect(PinkhaTextInputRenderPolicy.action(incoming: incoming, live: "שלום",
            isComposing: true, hasPendingLocalChanges: false) == .preserve)
    }

    @Test("Formatting a locally owned identical string never replaces its characters")
    func identicalTextUpdatesOnlyAttributes() {
        #expect(PinkhaTextInputRenderPolicy.action(incoming: "abc אבג", live: "abc אבג",
            isComposing: false, hasPendingLocalChanges: true) == .updateAttributes)
    }

    @Test("Remote and undo replacements resume after local acknowledgement")
    func unownedRemoteAndUndoReplaceText() {
        #expect(PinkhaTextInputRenderPolicy.action(incoming: "peer edit", live: "my edit",
            isComposing: false, hasPendingLocalChanges: false) == .replace)
        #expect(PinkhaTextInputRenderPolicy.action(incoming: "", live: "my edit",
            isComposing: false, hasPendingLocalChanges: false) == .replace)
    }

    @Test("Canonically equivalent text with different storage lengths is a replacement")
    func unicodeStorageIdentityUsesExactBytes() {
        let composed = "\u{00E9}"
        let decomposed = "e\u{0301}"
        #expect(composed == decomposed)
        #expect(composed.utf16.count != decomposed.utf16.count)
        #expect(PinkhaTextInputRenderPolicy.action(incoming: decomposed, live: composed,
            isComposing: false, hasPendingLocalChanges: false) == .replace)
    }
}
