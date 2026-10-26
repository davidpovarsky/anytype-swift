import Testing
@testable import PinkhaKit

@Suite("Pinkha text-direction marker")
struct PinkhaTextDirectionMarkerTests {
    @Test("Automatic direction markers round-trip", arguments: [
        PinkhaLayoutDirection.leftToRight,
        PinkhaLayoutDirection.rightToLeft
    ])
    func automaticRoundTrip(_ direction: PinkhaLayoutDirection) {
        let marker = PinkhaTextDirectionMarker.automatic(direction)
        #expect(PinkhaTextDirectionMarker(storedValue: marker.storedValue) == marker)
    }

    @Test("Explicit alignment markers round-trip", arguments: [
        PinkhaParagraphAlignment.left,
        PinkhaParagraphAlignment.center,
        PinkhaParagraphAlignment.right,
        PinkhaParagraphAlignment.justified,
        PinkhaParagraphAlignment.natural
    ])
    func explicitRoundTrip(_ alignment: PinkhaParagraphAlignment) {
        let marker = PinkhaTextDirectionMarker.explicit(alignment)
        #expect(PinkhaTextDirectionMarker(storedValue: marker.storedValue) == marker)
    }

    @Test("Unknown or malformed markers remain legacy-ambiguous")
    func rejectsUnknownValues() {
        #expect(PinkhaTextDirectionMarker(storedValue: "") == nil)
        #expect(PinkhaTextDirectionMarker(storedValue: "automatic") == nil)
        #expect(PinkhaTextDirectionMarker(storedValue: "explicit:leading") == nil)
    }

    @Test("Only proven-new or already-automatic blocks may persist automatic direction")
    func automaticPersistenceEligibility() {
        #expect(PinkhaAutomaticDirectionEligibility.shouldPersist(
            marker: nil,
            isSessionCreatedBlock: true
        ))
        #expect(!PinkhaAutomaticDirectionEligibility.shouldPersist(
            marker: nil,
            isSessionCreatedBlock: false
        ))
        #expect(PinkhaAutomaticDirectionEligibility.shouldPersist(
            marker: .automatic(.rightToLeft),
            isSessionCreatedBlock: false
        ))
        #expect(!PinkhaAutomaticDirectionEligibility.shouldPersist(
            marker: .explicit(.left),
            isSessionCreatedBlock: true
        ))
    }

    @Test("A stale automatic marker never overrides a stored explicit-looking alignment")
    func automaticMarkerMismatchFailsSafe() {
        #expect(PinkhaAutomaticDirectionEligibility.markerMatchesStoredAlignment(
            marker: .automatic(.rightToLeft),
            storedAlignment: .right
        ))
        #expect(!PinkhaAutomaticDirectionEligibility.markerMatchesStoredAlignment(
            marker: .automatic(.rightToLeft),
            storedAlignment: .left
        ))
        #expect(!PinkhaAutomaticDirectionEligibility.markerMatchesStoredAlignment(
            marker: .automatic(.leftToRight),
            storedAlignment: .center
        ))
    }
}
