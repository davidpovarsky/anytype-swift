import AnytypeCore
import Foundation
import Services
import Testing
@testable import Anytype

@Suite("Native acknowledgement of optimistic text", .serialized)
@MainActor
struct PinkhaNativeTextAcknowledgementTests {
    @Test("An unchanged acknowledged model never emits a whole-value native write")
    func unchangedNativeSnapshotDoesNotWrite() async throws {
        let fixture = TextAcknowledgementFixture(text: "already saved")
        try await fixture.write("already saved")
        #expect(fixture.writes.isEmpty)
    }

    @Test("A failed native write remains retryable even when the optimistic model matches")
    func optimisticFailureRequiresNativeRetry() async throws {
        let fixture = TextAcknowledgementFixture(text: "before")
        fixture.nativeWrite = { _, _ in throw TextAcknowledgementFailure.rejected }
        await expectRejection { try await fixture.write("accepted local edit") }
        #expect(fixture.currentText() == "accepted local edit")
        #expect(fixture.writes.count == 1)

        // A second failure must also remain dirty: model equality is not an ack.
        await expectRejection { try await fixture.write("accepted local edit") }
        #expect(fixture.writes.count == 2)
        fixture.nativeWrite = { _, _ in }
        try await fixture.write("accepted local edit")
        #expect(fixture.writes.count == 3)

        // A real acknowledgement restores the no-op suppression.
        try await fixture.write("accepted local edit")
        #expect(fixture.writes.count == 3)
    }

    @Test("Canonically equal strings with different UTF-8 still persist the accepted bytes")
    func canonicallyEquivalentUTF8RequiresNativeWrite() async throws {
        let stored = "\u{00e9}"
        let accepted = "e\u{0301}"
        #expect(stored == accepted)
        #expect(!stored.utf8.elementsEqual(accepted.utf8))
        let fixture = TextAcknowledgementFixture(text: stored)
        try await fixture.write(accepted)
        #expect(fixture.writes.count == 1)
        #expect(fixture.writes.first?.value.text.utf8.elementsEqual(accepted.utf8) == true)
    }

    @Test("An identical in-flight callback receives the native failure instead of false success")
    func identicalInFlightCallbackWaitsForTheNativeResult() async throws {
        let fixture = TextAcknowledgementFixture(text: "before")
        let entered = TextAcknowledgementGate()
        let release = TextAcknowledgementGate()
        fixture.nativeWrite = { _, _ in
            entered.open()
            await release.wait()
            throw TextAcknowledgementFailure.rejected
        }
        let first = Task { try await fixture.write("pending") }
        await entered.wait()
        let duplicateStarted = TextAcknowledgementGate()
        let duplicate = Task {
            duplicateStarted.open()
            try await fixture.write("pending")
        }
        await duplicateStarted.wait()
        await Task.yield()
        #expect(fixture.writes.count == 1)
        release.open()
        await expectRejection { try await first.value }
        await expectRejection { try await duplicate.value }
        #expect(fixture.writes.count == 1)

        fixture.nativeWrite = { _, _ in }
        try await fixture.write("pending")
        #expect(fixture.writes.count == 2)
    }

    @Test("A later accepted edit waits for the older write and survives that write failing")
    func laterTextIsSerializedAfterFailedNativeWrite() async throws {
        let fixture = TextAcknowledgementFixture(text: "before")
        let entered = TextAcknowledgementGate()
        let release = TextAcknowledgementGate()
        var activeWrites = 0
        var maximumActiveWrites = 0
        var events: [String] = []
        fixture.nativeWrite = { _, value in
            activeWrites += 1
            maximumActiveWrites = max(maximumActiveWrites, activeWrites)
            defer { activeWrites -= 1 }
            events.append("begin:\(value.text)")
            if value.text == "first" {
                entered.open()
                await release.wait()
                events.append("fail:first")
                throw TextAcknowledgementFailure.rejected
            }
            events.append("ack:\(value.text)")
        }
        let first = Task { try await fixture.write("first") }
        await entered.wait()
        let secondStarted = TextAcknowledgementGate()
        let second = Task {
            secondStarted.open()
            try await fixture.write("second")
        }
        await secondStarted.wait()
        // Give ready main-actor work a turn while the first native call is held.
        for _ in 0..<10 { await Task.yield() }
        release.open()
        await expectRejection { try await first.value }
        try await second.value
        #expect(maximumActiveWrites == 1)
        #expect(events == ["begin:first", "fail:first", "begin:second", "ack:second"])
        #expect(fixture.currentText() == "second")
        #expect(fixture.writes.map(\.value.text) == ["first", "second"])
    }

    @Test("A queued A to B to A reversal is not mistaken for an unchanged model")
    func queuedReversalPreservesTheFinalAcceptedText() async throws {
        let fixture = TextAcknowledgementFixture(text: "before")
        let entered = TextAcknowledgementGate()
        let release = TextAcknowledgementGate()
        var firstWrite = true
        var activeWrites = 0
        var maximumActiveWrites = 0
        fixture.nativeWrite = { _, _ in
            activeWrites += 1
            maximumActiveWrites = max(maximumActiveWrites, activeWrites)
            defer { activeWrites -= 1 }
            if firstWrite {
                firstWrite = false
                entered.open()
                await release.wait()
            }
        }
        let first = Task { try await fixture.write("A") }
        await entered.wait()
        let secondStarted = TextAcknowledgementGate()
        let second = Task {
            secondStarted.open()
            try await fixture.write("B")
        }
        await secondStarted.wait()
        for _ in 0..<10 { await Task.yield() }
        #expect(fixture.currentText() == "A")
        let reversal = Task { try await fixture.write("A") }
        for _ in 0..<10 { await Task.yield() }
        release.open()
        try await first.value
        try await second.value
        try await reversal.value
        #expect(maximumActiveWrites == 1)
        #expect(fixture.writes.map(\.value.text) == ["A", "B", "A"])
        #expect(fixture.currentText() == "A")
    }

    @Test("A failed local payload does not turn an unchanged peer value into a new LWW write")
    func failedPayloadDoesNotRewriteANewRemoteValue() async throws {
        let fixture = TextAcknowledgementFixture(text: "before")
        fixture.nativeWrite = { _, _ in throw TextAcknowledgementFailure.rejected }
        await expectRejection { try await fixture.write("failed local") }
        fixture.setModel("acknowledged peer")
        fixture.nativeWrite = { _, _ in }
        try await fixture.write("acknowledged peer")
        #expect(fixture.writes.count == 1)
        #expect(fixture.currentText() == "acknowledged peer")
    }

    private func expectRejection(
        _ operation: @MainActor () async throws -> Void
    ) async {
        do {
            try await operation()
            Issue.record("Expected the actual native rejection to reach the caller")
        } catch TextAcknowledgementFailure.rejected {
            // The original failure, not model equality, decides the result.
        } catch {
            Issue.record("Unexpected failure: \(error)")
        }
    }
}

private enum TextAcknowledgementFailure: Error {
    case rejected
}

@MainActor
private final class TextAcknowledgementFixture {
    struct Write {
        let blockId: String
        let value: MiddlewareString
    }

    let blockId = "native-ack-text-block"
    let container = InfoContainerMock()
    let service = BlockActionServiceMock()
    let document: MockBaseDocument
    let handler: BlockActionHandler
    var writes: [Write] = []
    var nativeWrite: @MainActor (String, MiddlewareString) async throws -> Void = { _, _ in }

    init(text: String) {
        let details = ObjectDetails(id: "native-ack-test-document", values: [:])
        document = MockBaseDocument(objectId: details.id, details: details)
        document.mockSpaceId = "native-ack-test-space"
        document.mockInfoContainer = container
        handler = BlockActionHandler(
            document: document,
            markupChanger: BlockMarkupChangerMock(),
            service: service
        )
        setModel(text)
        service.onSetText = { [weak self] _, blockId, value in
            guard let self else {
                Issue.record("The text fixture disappeared before its native request")
                throw TextAcknowledgementFailure.rejected
            }
            writes.append(Write(blockId: blockId, value: value))
            // Model the document's optimistic local-event subscriber. The real
            // service is invoked after EventsBunch.send(), before native ack.
            setModel(value.text)
            try await nativeWrite(blockId, value)
        }
    }

    func write(_ text: String) async throws {
        try await handler.changeText(NSAttributedString(string: text).sendable(), blockId: blockId)
    }

    func currentText() -> String? {
        container.getReturnInfo[blockId]?.textContent?.text
    }

    func setModel(_ text: String) {
        container.getReturnInfo[blockId] = BlockInformation(
            id: blockId,
            content: .text(.plain(text, contentType: .text)),
            backgroundColor: nil,
            horizontalAlignment: .left,
            childrenIds: [],
            configurationData: BlockInformationMetadata(backgroundColor: .default),
            fields: [:]
        )
    }
}

@MainActor
private final class TextAcknowledgementGate {
    private var isOpen = false
    private var waiters: [CheckedContinuation<Void, Never>] = []

    func wait() async {
        if isOpen { return }
        await withCheckedContinuation { waiters.append($0) }
    }

    func open() {
        isOpen = true
        let pending = waiters
        waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }
}
