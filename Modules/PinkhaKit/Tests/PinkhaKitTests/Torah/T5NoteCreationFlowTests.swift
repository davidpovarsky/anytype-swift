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
            source: source,
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
            source: source,
            createObject: { creates += 1; return "recoverable-note" },
            linkSource: { _ in throw T5SpaceRelatedDocumentsError.indexUnavailable },
            addSourceLine: { _ in Issue.record("Source write failed before text") },
            linkOrigin: { _ in Issue.record("Source write failed before origin") }
        )
        #expect(first.objectID == "recoverable-note")
        #expect(first.recoveryError != nil)
        let retry = try await flow.create(
            source: source,
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
            source: source,
            createObject: { creates += 1; return "note" }, linkSource: { _ in },
            addSourceLine: { _ in textAttempts += 1; throw T5SpaceRelatedDocumentsError.indexUnavailable },
            linkOrigin: { _ in Issue.record("Text write failed before origin") }
        )
        #expect(first.objectID == "note")
        #expect(first.recoveryError != nil)
        let retry = try await flow.create(
            source: source,
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
                source: source,
                createObject: { throw T5SpaceRelatedDocumentsError.indexUnavailable },
                linkSource: { _ in Issue.record("No object exists") },
                addSourceLine: { _ in Issue.record("No object exists") },
                linkOrigin: { _ in Issue.record("No object exists") }
            )
        }
    }
}
