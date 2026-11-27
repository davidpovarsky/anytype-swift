#if DEBUG && targetEnvironment(simulator) && canImport(UIKit)
import Foundation
import UIKit
import HanlinAgentCore
import HanlinChatCore
import HanlinHostContracts
import PinkhaHanlinCore

/// Only the model HTTP response is controlled. The original provider adapter,
/// AgentSession, presentation action, native consent, worker and journal execute
/// unchanged. XCTest must press Send, Save and the actual native decisions.
@MainActor
public final class PinkhaHanlinSaveMessageAcceptanceDriver {
    public typealias Snapshot = PinkhaHanlinWriteJournal.SaveMessageAcceptanceSnapshot
    public typealias NativeReadback = @MainActor @Sendable (Snapshot) async throws -> PinkhaHanlinSaveMessageBodyReadback

    private struct Attempt: Codable {
        let origin: HanlinHostInteractionOrigin
        var requestID: UUID?
        var executionRunID: UUID?
        var call: HanlinHostCallIdentity?
        var resultID: UUID?
        var effect: String?
        var journalIdentityKey: String?
        var journalProgressSHA256: String?
    }
    private struct Receipt: Codable {
        let version = 1
        let fixture: PinkhaHanlinSaveMessageAcceptanceFixture
        let session: HanlinHostSession
        let processID: Int32
        let startedAt: Date
        var phase = "PREPARING_ORIGINAL_SDK"
        var attempts: [Attempt] = []
        var nativeBodyReadback: PinkhaHanlinSaveMessageBodyReadback?
        var atomicAcknowledgement: PinkhaHanlinSaveMessageAtomicAcknowledgement?
        var finishedAt: Date?
        var failure: String?
    }

    private let fixture: PinkhaHanlinSaveMessageAcceptanceFixture
    private weak var presentation: PinkhaHanlinChatPresentation?
    private let verifyNativeReadback: NativeReadback
    private let directory: URL
    private let label: UILabel
    private var receipt: Receipt
    private var ordinal = 0
    private var sequence = 0
    private var journal: PinkhaHanlinWriteJournal?
    private var originalResult: HanlinHostResultEvent?
    private var task: Task<Void, Never>?
    private var ended = false

    public static func start(fixture: PinkhaHanlinSaveMessageAcceptanceFixture,
        presentation: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController,
        verifyNativeReadback: @escaping NativeReadback) {
        do {
            if try presentation.hasSaveMessageAcceptanceDriver(for: fixture) { return }
            let driver = try Self(fixture: fixture, presentation: presentation,
                controller: controller, verifyNativeReadback: verifyNativeReadback)
            try presentation.installSaveMessageAcceptanceDriver(driver)
            driver.task = Task { @MainActor in await driver.prepare() }
        } catch {
            presentation.invalidate()
        }
    }

    func matches(fixture: PinkhaHanlinSaveMessageAcceptanceFixture, session: HanlinHostSession) -> Bool {
        self.fixture.fixtureID == fixture.fixtureID && self.fixture.preparationReceiptSHA256 == fixture.preparationReceiptSHA256
            && receipt.session == session
    }

    private init(fixture: PinkhaHanlinSaveMessageAcceptanceFixture,
        presentation: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController,
        verifyNativeReadback: @escaping NativeReadback) throws {
        try fixture.validate(session: presentation.session)
        try presentation.validateInstallation(for: presentation.session)
        guard controller.presentation === presentation, !presentation.isConfigured,
              presentation.messages.isEmpty, let window = controller.viewIfLoaded?.window else {
            throw HanlinHostError.staleContext
        }
        self.fixture = fixture; self.presentation = presentation
        self.verifyNativeReadback = verifyNativeReadback
        self.directory = try fixture.claimResultDirectory()
        self.receipt = .init(fixture: fixture, session: presentation.session,
            processID: ProcessInfo.processInfo.processIdentifier, startedAt: .now)
        let label = UILabel(frame: CGRect(x: 12, y: window.safeAreaInsets.top + 2,
            width: max(100, window.bounds.width - 24), height: 22))
        label.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        label.textAlignment = .center; label.backgroundColor = .systemBackground
        label.isAccessibilityElement = true
        label.accessibilityIdentifier = "pinkha.hanlin.save-acceptance-status"
        window.addSubview(label)
        self.label = label
        try emit("PREPARING_ORIGINAL_SDK")
    }

    private func prepare() async {
        do {
            guard let presentation else { throw HanlinHostError.staleContext }
            let original = try await PinkhaHanlinAccountOwner.shared.journal(for: presentation.session.context.namespace)
            try Task.checkCancellation()
            try fixture.validate(session: presentation.session)
            try presentation.validateInstallation(for: presentation.session)
            // Retain this exact actor now. Later observations never reopen a
            // journal through whichever account happens to be current.
            journal = original
            let configuration = try PinkhaHanlinModelConfiguration.make(
                endpoint: "https://hanlin-save-acceptance.invalid/v1", model: "pinkha-native-save-acceptance",
                credential: "controlled-transport-no-network")
            let transport = PinkhaHanlinSaveMessageModelTransport(fixture: fixture)
            let engine = try HanlinAISDKAgentEngine(configuration: configuration, fetch: { request in
                let data = try await transport.response(for: request)
                guard let url = request.url,
                      let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "text/event-stream"]) else { throw HanlinHostError.invalidArguments }
                let stream = AsyncThrowingStream<Data, Error> { continuation in
                    continuation.yield(data); continuation.finish()
                }
                return .init(body: .stream(stream), urlResponse: response)
            })
            try presentation.installSaveMessageAcceptanceEngine(configuration: configuration, engine: engine)
            presentation.draft = fixture.prompt(0)
            try emit("AWAIT_SEND_CANCEL")
        } catch { fail("original_sdk_preparation_failed") }
    }

    func admitted(origin: HanlinHostInteractionOrigin, markdown: String) {
        do {
            guard !ended, ordinal < 2, receipt.attempts.count == ordinal,
                  markdown.utf8.elementsEqual(fixture.markdown.utf8),
                  origin.session == receipt.session,
                  !receipt.attempts.contains(where: { $0.origin.messageID == origin.messageID || $0.origin.runID == origin.runID }) else {
                throw HanlinHostError.resultMismatch
            }
            receipt.attempts.append(.init(origin: origin))
            try emit(ordinal == 0 ? "AWAIT_SAVE_CANCEL" : "AWAIT_SAVE_ALLOW")
        } catch { fail("completed_original_message_mismatch") }
    }

    func started(_ intent: PinkhaHanlinMessageSaveIntents.Intent) {
        do {
            guard !ended, receipt.attempts.indices.contains(ordinal),
                  receipt.attempts[ordinal].origin == intent.origin,
                  receipt.attempts[ordinal].requestID == nil,
                  intent.markdownSHA256 == PinkhaHanlinCreatePagePlan.digest(Data(fixture.markdown.utf8)),
                  let run = intent.executionRunID else { throw HanlinHostError.resultMismatch }
            receipt.attempts[ordinal].requestID = intent.requestID
            receipt.attempts[ordinal].executionRunID = run
            try emit(ordinal == 0 ? "AWAIT_NATIVE_CANCEL" : "AWAIT_NATIVE_ALLOW")
        } catch { fail("original_presentation_tool_start_mismatch") }
    }

    func observed(_ event: HanlinHostResultEvent, messageID: UUID) {
        guard !ended, receipt.attempts.indices.contains(ordinal) else { return }
        let attempt = receipt.attempts[ordinal]
        guard attempt.origin.messageID == messageID, event.call.session == receipt.session,
              attempt.executionRunID == event.call.runID,
              attempt.requestID?.uuidString.utf8.elementsEqual(event.call.providerCallID.utf8) == true,
              originalResult == nil else { fail("original_host_result_mismatch"); return }
        originalResult = event
        receipt.attempts[ordinal].call = event.call
        receipt.attempts[ordinal].resultID = event.resultID
        receipt.attempts[ordinal].effect = String(describing: event.result.effectState)
    }

    func consumerFinished(_ intent: PinkhaHanlinMessageSaveIntents.Intent) {
        guard !ended, receipt.attempts.indices.contains(ordinal),
              receipt.attempts[ordinal].requestID == intent.requestID else { return }
        task = Task { @MainActor in await finishAttempt(intent) }
    }

    private func finishAttempt(_ intent: PinkhaHanlinMessageSaveIntents.Intent) async {
        do {
            guard let presentation, let journal, let event = originalResult else {
                throw HanlinHostError.resultMismatch
            }
            try presentation.validateInstallation(for: receipt.session)
            let snapshot = try await journal.saveMessageAcceptanceSnapshot(for: event.call)
            try Task.checkCancellation()
            try presentation.validateInstallation(for: receipt.session)
            if ordinal == 0 {
                guard intent.status == .notCommitted, snapshot == nil,
                      event.result.effectState == .notDispatched || event.result.effectState == .confirmedNoEffect,
                      !presentation.canSaveMessage(intent.origin.messageID), !presentation.isMessageSaved(intent.origin.messageID) else {
                    throw HanlinHostError.resultMismatch
                }
                ordinal = 1; originalResult = nil
                presentation.draft = fixture.prompt(1)
                try emit("AWAIT_SEND_ALLOW")
            } else {
                guard intent.status == .committed, event.result.effectState == .confirmedCommitted,
                      let snapshot, snapshot.entry.effect == .committed,
                      let progress = snapshot.progress, progress.isReadyForCommit,
                      let expected = progress.bodyReadback,
                      progress.manifest.titleSHA256 == intent.titleSHA256,
                      progress.manifest.markdownSHA256 == intent.markdownSHA256,
                      event.result.reconciliationReference == snapshot.entry.identity.key,
                      presentation.isMessageSaved(intent.origin.messageID),
                      !presentation.canSaveMessage(intent.origin.messageID) else { throw HanlinHostError.resultMismatch }
                try progress.validate()
                receipt.attempts[ordinal].journalIdentityKey = snapshot.entry.identity.key
                receipt.attempts[ordinal].journalProgressSHA256 = PinkhaHanlinCreatePagePlan.digest(try progress.canonicalBytes())
                try emit("NATIVE_COMMIT_RECORDED_POSTFLIGHT_REQUIRED")
                let actual = try await verifyNativeReadback(snapshot)
                try Task.checkCancellation()
                try presentation.validateInstallation(for: receipt.session)
                guard try canonical(actual) == canonical(expected) else { throw HanlinHostError.resultMismatch }
                receipt.nativeBodyReadback = actual
                receipt.atomicAcknowledgement = progress.atomicBody?.acknowledgement
                receipt.finishedAt = .now
                try emit("CANCEL_RECEIPT_AND_NATIVE_SAVE_READBACK_PASS")
                ended = true
            }
        } catch { fail("original_receipt_or_native_postflight_failed") }
    }

    func invalidate() {
        task?.cancel()
        if !ended { fail("original_presentation_invalidated") }
        label.removeFromSuperview()
    }

    func drain() async { await task?.value }

    private func emit(_ phase: String) throws {
        guard sequence < 16 else { throw HanlinHostError.outputLimitExceeded }
        receipt.phase = phase
        let data = try canonical(receipt)
        guard data.count <= 196_608 else { throw HanlinHostError.outputLimitExceeded }
        let filename = String(format: "%02d", sequence) + ".json"
        try data.write(to: directory.appendingPathComponent(filename), options: .withoutOverwriting)
        sequence += 1
        label.text = phase; label.accessibilityValue = String(decoding: data, as: UTF8.self)
    }

    private func fail(_ code: String) {
        guard !ended else { return }
        receipt.failure = code; receipt.finishedAt = .now
        do { try emit("NATIVE_SAVE_ACCEPTANCE_FAIL") }
        catch { label.text = "NATIVE_SAVE_EVIDENCE_WRITE_FAILED" }
        ended = true
    }

    private func canonical<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
}

private actor PinkhaHanlinSaveMessageModelTransport {
    let fixture: PinkhaHanlinSaveMessageAcceptanceFixture
    private var count = 0
    init(fixture: PinkhaHanlinSaveMessageAcceptanceFixture) { self.fixture = fixture }

    func response(for request: URLRequest) throws -> Data {
        try Task.checkCancellation()
        guard count < 2, request.httpMethod == "POST", let url = request.url,
              url.scheme == "https", url.host == "hanlin-save-acceptance.invalid",
              url.path == "/v1/chat/completions", url.query == nil,
              let body = request.httpBody, body.count <= 1_048_576,
              let json = try JSONSerialization.jsonObject(with: body) as? [String: Any],
              json["model"] as? String == "pinkha-native-save-acceptance", json["stream"] as? Bool == true,
              let messages = json["messages"] as? [[String: Any]], messages.count <= 16,
              let last = messages.last, last["role"] as? String == "user",
              try text(last["content"]).utf8.elementsEqual(fixture.prompt(count).utf8) else {
            throw HanlinHostError.invalidArguments
        }
        let users = messages.filter { $0["role"] as? String == "user" }
        let assistants = messages.filter { $0["role"] as? String == "assistant" }
        guard users.count == count + 1, assistants.count == count,
              try assistants.allSatisfy({ try text($0["content"]).utf8.elementsEqual(fixture.markdown.utf8) }) else {
            throw HanlinHostError.resultMismatch
        }
        let identifier = "hanlin-save-" + fixture.fixtureID.uuidString + "-" + String(count)
        func chunk(delta: [String: String], finish: Any) throws -> String {
            let value: [String: Any] = ["id": identifier, "object": "chat.completion.chunk", "created": 1,
                "model": "pinkha-native-save-acceptance", "choices": [["index": 0, "delta": delta, "finish_reason": finish]]]
            return "data: " + String(decoding: try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]), as: UTF8.self) + "\n\n"
        }
        let data = try Data((chunk(delta: ["role": "assistant", "content": fixture.markdown], finish: NSNull())
            + chunk(delta: [:], finish: "stop") + "data: [DONE]\n\n").utf8)
        count += 1
        return data
    }

    private func text(_ value: Any?) throws -> String {
        if let value = value as? String { return value }
        if let parts = value as? [[String: Any]], parts.count == 1,
           parts[0]["type"] as? String == "text", let text = parts[0]["text"] as? String { return text }
        throw HanlinHostError.invalidArguments
    }
}
#endif
