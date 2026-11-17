import Testing
@testable import PinkhaKit

@Suite("T5 Note self-association and partial recovery")
@MainActor
struct T5NoteCreationFlowTests {
    let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")

    @Test func sourceIsLinkedOnNewNoteBeforeTextAndOriginReference() async throws {
        let flow = T5NoteCreationFlow()
        var calls: [String] = []
        let result = try await flow.create(
            source: source, authorize: {},
            createObject: { calls.append("create"); return "new-note" },
            linkSource: { calls.append("source:\($0)") },
            addSourceLine: { calls.append("text:\($0)") },
            linkOrigin: { calls.append("origin:\($0)") }
        )
        #expect(result.objectID == "new-note")
        #expect(result.recoveryError == nil)
        #expect(calls == ["create", "source:new-note", "text:new-note", "origin:new-note"])
    }

    @Test func failedSelfLinkPreservesObjectIDAndRetryReusesNote() async throws {
        let flow = T5NoteCreationFlow()
        var creates = 0
        let first = try await flow.create(
            source: source, authorize: {},
            createObject: { creates += 1; return "recoverable-note" },
            linkSource: { _ in throw T5SpaceRelatedDocumentsError.indexUnavailable },
            addSourceLine: { _ in Issue.record("Source write failed before text") },
            linkOrigin: { _ in Issue.record("Source write failed before origin") }
        )
        #expect(first.objectID == "recoverable-note")
        #expect(first.recoveryError != nil)
        let retry = try await flow.create(
            source: source, authorize: {},
            createObject: { creates += 1; return "duplicate-note" },
            linkSource: { #expect($0 == "recoverable-note") },
            addSourceLine: { #expect($0 == "recoverable-note") },
            linkOrigin: { #expect($0 == "recoverable-note") }
        )
        #expect(creates == 1)
        #expect(retry.objectID == "recoverable-note")
        #expect(retry.recoveryError == nil)
    }

    @Test func uncertainTextWriteIsNotBlindlyRepeatedOnRetry() async throws {
        let flow = T5NoteCreationFlow()
        var creates = 0
        var textAttempts = 0
        let first = try await flow.create(
            source: source, authorize: {},
            createObject: { creates += 1; return "note" }, linkSource: { _ in },
            addSourceLine: { _ in textAttempts += 1; throw T5SpaceRelatedDocumentsError.indexUnavailable },
            linkOrigin: { _ in Issue.record("Text write failed before origin") }
        )
        #expect(first.objectID == "note")
        #expect(first.recoveryError != nil)
        let retry = try await flow.create(
            source: source, authorize: {},
            createObject: { creates += 1; return "duplicate" }, linkSource: { _ in },
            addSourceLine: { _ in textAttempts += 1 }, linkOrigin: { #expect($0 == "note") }
        )
        #expect(retry.objectID == "note")
        #expect(creates == 1)
        #expect(textAttempts == 1)
    }

    @Test func failedObjectCreationThrowsWithoutFabricatingRecoveryObject() async {
        let flow = T5NoteCreationFlow()
        await #expect(throws: T5SpaceRelatedDocumentsError.indexUnavailable) {
            try await flow.create(
                source: source, authorize: {},
                createObject: { throw T5SpaceRelatedDocumentsError.indexUnavailable },
                linkSource: { _ in Issue.record("No object exists") },
                addSourceLine: { _ in Issue.record("No object exists") },
                linkOrigin: { _ in Issue.record("No object exists") }
            )
        }
    }
    @Test("Revocation after each suspended write preserves the Note and stops later writes", arguments: [0, 1, 2])
    func revokedBetweenWritesPreservesRecoverableNote(stage: Int) async throws {
        let flow = T5NoteCreationFlow()
        let barrier = T5NoteWriteBarrier()
        var permitted = true
        var creates = 0
        var sourceWrites = 0
        var textWrites = 0
        var originWrites = 0
        let authorize: T5NoteCreationFlow.Authorize = {
            guard permitted else { throw TorahAssociationRepositoryError.permissionDenied }
        }
        let request = Task { @MainActor in
            try await flow.create(
                source: source, authorize: authorize,
                createObject: {
                    creates += 1
                    if stage == 0 { await barrier.hold() }
                    return "recoverable-note"
                },
                linkSource: { _ in
                    sourceWrites += 1
                    if stage == 1 { await barrier.hold() }
                },
                addSourceLine: { _ in
                    textWrites += 1
                    if stage == 2 { await barrier.hold() }
                },
                linkOrigin: { _ in originWrites += 1 }
            )
        }
        await barrier.waitUntilHeld()
        permitted = false
        await barrier.release()
        let result = try await request.value
        #expect(result.objectID == "recoverable-note")
        #expect(result.recoveryError as? TorahAssociationRepositoryError == .permissionDenied)
        #expect(creates == 1)
        #expect(sourceWrites == (stage == 0 ? 0 : 1))
        #expect(textWrites == (stage == 2 ? 1 : 0))
        #expect(originWrites == 0)

        permitted = true
        let resumed = try await flow.create(
            source: source, authorize: authorize,
            createObject: { creates += 1; return "duplicate-note" },
            linkSource: { _ in sourceWrites += 1 },
            addSourceLine: { _ in textWrites += 1 },
            linkOrigin: { _ in originWrites += 1 }
        )
        #expect(resumed.objectID == "recoverable-note")
        #expect(resumed.recoveryError == nil)
        #expect(creates == 1)
        #expect(textWrites == 1)
        #expect(originWrites == 1)
    }

    @Test("Revoked authority before creation cannot allocate or mutate a Note")
    func revokedBeforeCreationProducesNoObject() async {
        let flow = T5NoteCreationFlow()
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await flow.create(
                source: source,
                authorize: { throw TorahAssociationRepositoryError.permissionDenied },
                createObject: { Issue.record("Revoked action allocated a Note"); return "unexpected-note" },
                linkSource: { _ in Issue.record("Revoked action linked a source") },
                addSourceLine: { _ in Issue.record("Revoked action wrote text") },
                linkOrigin: { _ in Issue.record("Revoked action linked its origin") }
            )
        }
    }

}

private actor T5NoteWriteBarrier {
    private var held = false
    private var waiter: CheckedContinuation<Void, Never>?
    private var continuation: CheckedContinuation<Void, Never>?

    func hold() async {
        await withCheckedContinuation { continuation in
            self.continuation = continuation
            held = true
            waiter?.resume()
            waiter = nil
        }
    }

    func waitUntilHeld() async {
        if held { return }
        await withCheckedContinuation { waiter = $0 }
    }

    func release() {
        continuation?.resume()
        continuation = nil
    }
}
