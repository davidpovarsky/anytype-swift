import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
@testable import PinkhaHanlinCore

/// Pure presentation correlation and bounds only. Controlled host events here
/// are not native body-write, SDK execution, consent or UI acceptance evidence.
final class HanlinMessageSaveIntentTests: XCTestCase {
    func testExactUnicodeBodyAndOneRequestIdentitySurviveMenuReuse() throws {
        let session = try session()
        var state = PinkhaHanlinMessageSaveIntents(session: session)
        let origin = origin(session)
        let title = " כותרת e\u{301} "
        let body = "# שלום\r\n\r\n**טקסט** e\u{301} 👩🏽‍💻\n"
        let intent = try state.reserve(origin: origin, title: title, markdown: body)
        let request = try intent.request(title: title, markdown: body)
        XCTAssertEqual(request.requestID, intent.requestID)
        XCTAssertEqual(request.origin, origin)
        XCTAssertEqual(request.arguments, .object(["title": .string(title), "markdown": .string(body)]))
        XCTAssertThrowsError(try intent.request(title: title, markdown: body.replacingOccurrences(of: "e\u{301}", with: "é")))
        XCTAssertThrowsError(try state.reserve(origin: origin, title: title, markdown: body))
        XCTAssertEqual(state.intent(for: origin.messageID)?.requestID, intent.requestID)
        XCTAssertEqual(state.count, 1)
    }

    func testUTF8LimitsRejectWholeMessageInsteadOfTruncatingIt() throws {
        let session = try session()
        var state = PinkhaHanlinMessageSaveIntents(session: session)
        let title = String(repeating: "א", count: 256)
        let body = String(repeating: "😀", count: 16_384)
        let intent = try state.reserve(origin: origin(session), title: title, markdown: body)
        let request = try intent.request(title: title, markdown: body)
        XCTAssertEqual(request.arguments, .object(["title": .string(title), "markdown": .string(body)]))
        XCTAssertThrowsError(try state.reserve(origin: origin(session), title: title + "a", markdown: body))
        XCTAssertThrowsError(try state.reserve(origin: origin(session), title: title, markdown: body + "a"))
        XCTAssertThrowsError(try state.reserve(origin: origin(session), title: " ", markdown: body))
        XCTAssertThrowsError(try state.reserve(origin: origin(session), title: title, markdown: ""))
        XCTAssertEqual(state.count, 1)
    }

    func testOnlyExactOriginalSaveExecutionMayDisplayCommit() throws {
        for app in ["anytype", "anytype-any"] {
            let session = try session(app: app)
            var state = PinkhaHanlinMessageSaveIntents(session: session)
            let origin = origin(session)
            let intent = try state.reserve(origin: origin, title: "Title", markdown: "Body")
            let execution = UUID()
            XCTAssertThrowsError(try state.bindExecution(messageID: origin.messageID,
                requestID: intent.requestID, runID: origin.runID))
            try state.bindExecution(messageID: origin.messageID, requestID: intent.requestID, runID: execution)
            let foreignSession = try self.session(app: app, account: "foreign-account")
            XCTAssertNil(state.observe(try event(intent: intent, run: execution, session: foreignSession)))
            XCTAssertNil(state.observe(try event(intent: intent, run: UUID(), session: session)))
            XCTAssertNil(state.observe(try event(intent: intent, run: execution, session: session,
                provider: UUID().uuidString)))
            XCTAssertNil(state.observe(try event(intent: intent, run: execution, session: session,
                localTool: "create-page")))
            XCTAssertEqual(state.intent(for: origin.messageID)?.status, .pending)
            let actual = try event(intent: intent, run: execution, session: session)
            XCTAssertEqual(state.observe(actual), origin.messageID)
            XCTAssertEqual(state.intent(for: origin.messageID)?.status, .committed)
            XCTAssertEqual(state.intent(for: origin.messageID)?.resultID, actual.resultID)
            XCTAssertNil(state.observe(actual))
            XCTAssertNil(state.observe(try event(intent: intent, run: execution, session: session, effect: .uncertain)))
            XCTAssertEqual(state.intent(for: origin.messageID)?.status, .committed)
        }
    }

    func testCancelledUncertainOrMissingReceiptNeverMintsAnotherAttempt() throws {
        let session = try session()
        for effect in [HanlinHostEffectState.notDispatched, .confirmedNoEffect, .uncertain] {
            var state = PinkhaHanlinMessageSaveIntents(session: session)
            let origin = origin(session)
            let intent = try state.reserve(origin: origin, title: "Title", markdown: "Body")
            let execution = UUID()
            try state.bindExecution(messageID: origin.messageID, requestID: intent.requestID, runID: execution)
            XCTAssertEqual(state.observe(try event(intent: intent, run: execution, session: session, effect: effect)), origin.messageID)
            state.finishWithoutReceipt(messageID: origin.messageID, requestID: intent.requestID)
            XCTAssertEqual(state.intent(for: origin.messageID)?.status, effect == .uncertain ? .uncertain : .notCommitted)
            XCTAssertFalse(state.canReserve(messageID: origin.messageID))
            XCTAssertThrowsError(try state.reserve(origin: origin, title: "Title", markdown: "Body"))
            XCTAssertEqual(state.intent(for: origin.messageID)?.requestID, intent.requestID)
        }
        var state = PinkhaHanlinMessageSaveIntents(session: session)
        let origin = origin(session)
        let intent = try state.reserve(origin: origin, title: "Title", markdown: "Body")
        state.finishWithoutReceipt(messageID: origin.messageID, requestID: intent.requestID)
        XCTAssertEqual(state.intent(for: origin.messageID)?.status, .unconfirmed)
        XCTAssertFalse(state.canReserve(messageID: origin.messageID))
    }

    func testFullAttemptBudgetStillProcessesItsLastOriginalUncertainReceipt() throws {
        let session = try session()
        var state = PinkhaHanlinMessageSaveIntents(session: session)
        var last: PinkhaHanlinMessageSaveIntents.Intent?
        for _ in 0..<PinkhaHanlinMessageSaveIntents.maximumAttempts {
            last = try state.reserve(origin: origin(session), title: "Title", markdown: "Body")
        }
        let intent = try XCTUnwrap(last)
        let execution = UUID()
        try state.bindExecution(messageID: intent.origin.messageID, requestID: intent.requestID, runID: execution)
        XCTAssertEqual(state.count, 256)
        XCTAssertThrowsError(try state.reserve(origin: origin(session), title: "Title", markdown: "Body"))
        XCTAssertEqual(state.observe(try event(intent: intent, run: execution, session: session, effect: .uncertain)), intent.origin.messageID)
        XCTAssertEqual(state.intent(for: intent.origin.messageID)?.status, .uncertain)
        XCTAssertEqual(state.count, 256)
        state.finishWithoutReceipt(messageID: intent.origin.messageID, requestID: intent.requestID)
        XCTAssertFalse(state.canReserve(messageID: UUID()))
        XCTAssertEqual(state.intent(for: intent.origin.messageID)?.status, .uncertain)
    }

    private func session(app: String = "anytype", account: String = "disposable-account") throws -> HanlinHostSession {
        .init(conversationID: UUID(), context: .init(namespace: try .init(app: app,
            account: account, workspace: "disposable-space", space: "disposable-space"),
            sceneID: UUID(), generation: UUID()))
    }

    private func origin(_ session: HanlinHostSession) -> HanlinHostInteractionOrigin {
        .init(session: session, runID: UUID(), messageID: UUID(), partID: UUID())
    }

    private func event(intent: PinkhaHanlinMessageSaveIntents.Intent, run: UUID, session: HanlinHostSession,
                       provider: String? = nil, localTool: String = "save-message",
                       effect: HanlinHostEffectState = .confirmedCommitted) throws -> HanlinHostResultEvent {
        let id = try HanlinToolInvocationID(validating: UUID().uuidString.lowercased())
        let tool = HanlinLogicalToolID(providerInstanceID: try .init(validating: "anytype.host"),
                                      localToolID: try .init(validating: localTool))
        let call = HanlinHostCallIdentity(session: session, runID: run, step: 0,
            providerCallID: provider ?? intent.requestID.uuidString, invocationID: id, logicalToolID: tool)
        let result = HanlinHostExecutionResult(result: .init(invocationID: id, logicalToolID: tool,
            outcome: effect == .uncertain
                ? .failed(.init(code: .operationUnavailable, userMessage: "Original scope is uncertain."))
                : .completed([]), completedAt: .now),
            effectState: effect, context: session.context, reconciliationReference: "original-metadata")
        return try .init(resultID: UUID(), call: call, result: result)
    }
}
