@testable import PinkhaHanlinUI
import Foundation
import Testing
import HanlinChatCore
import HanlinHostContracts
import HanlinAgentActivityCore

#if os(iOS) && DEBUG
/// Controlled original SDK events exercise the consumer projection. These do
/// not claim provider, native-write, audio, translation or interactive UI proof.
@Suite("Hanlin original message projection")
@MainActor
struct HanlinOriginalMessageProjectionTests {
    @Test(arguments: ["anytype", "anytype-any"])
    func streamIdentityAndNativeDrainBoundary(app: String) throws {
        let identity = try session(app: app)
        var projection = PinkhaHanlinMessageActivity(session: identity, messageID: UUID())
        let run = UUID()
        try projection.consume(.runStarted, session: identity, runID: run, sequence: 1)
        let otherAccount = try session(app: app, account: "other-account")
        #expect(throws: HanlinHostError.staleContext) {
            try projection.consume(.textDelta("wrong account"), session: otherAccount, runID: run, sequence: 2)
        }
        #expect(throws: HanlinHostError.staleContext) {
            try projection.consume(.textDelta("wrong run"), session: identity, runID: UUID(), sequence: 2)
        }
        #expect(throws: HanlinHostError.staleContext) {
            try projection.consume(.textDelta("replayed event"), session: identity, runID: run, sequence: 1)
        }
        try projection.consume(.textDelta("Actual answer."), session: identity, runID: run, sequence: 2)
        try projection.consume(.cancelled, session: identity, runID: run, sequence: 3)
        #expect(projection.run?.status == .running)
        #expect(projection.run?.completedAt == nil)
        // Only the owner may declare the original SDK/native join complete.
        projection.finish(status: .cancelled)
        #expect(projection.run?.status == .cancelled)
        #expect(projection.run?.completedAt != nil)
        #expect(throws: HanlinHostError.staleContext) {
            try projection.consume(.textDelta("late callback"), session: identity, runID: run, sequence: 4)
        }
    }

    @Test(arguments: ["anytype", "anytype-any"])
    func parsedToolCallIsNotAnExecutionReceipt(app: String) throws {
        let identity = try session(app: app)
        var projection = PinkhaHanlinMessageActivity(session: identity, messageID: UUID())
        let run = UUID()
        try projection.consume(.toolCall(.init(id: "actual-call", name: "anytype_create_page",
            argumentsJSON: "{\"title\":\"private title\"}")), session: identity, runID: run, sequence: 1)
        let requested = try #require(projection.run)
        #expect(requested.steps.count == 1)
        #expect(requested.steps.allSatisfy { !$0.isExecutionLifecycleStep && $0.status == .pending && $0.input == nil })
        try projection.consume(.toolResult(callID: "actual-call", name: "anytype_create_page",
            modelText: "Native operation denied.", resultReference: nil, isError: true),
            session: identity, runID: run, sequence: 2)
        let returned = try #require(projection.run)
        #expect(returned.steps.filter(\.isExecutionLifecycleStep).count == 1)
        #expect(returned.steps.allSatisfy { $0.status == .failed })
        projection.finish(status: .completed)
        #expect(projection.run?.steps.allSatisfy { $0.status == .failed } == true)
    }

    @Test(arguments: ["anytype", "anytype-any"])
    func citationsKeepOriginalTextAndSourceIdentity(app: String) throws {
        let identity = try session(app: app)
        var projection = PinkhaHanlinMessageActivity(session: identity, messageID: UUID())
        let run = UUID()
        let text = "שלום 👋 עולם."
        let source = "https://example.com/original"
        try projection.consume(.textCitations([.init(textPartID: "original-part", text: text,
            startIndex: 0, endIndex: text.unicodeScalars.count, url: source, title: "מקור")]),
            session: identity, runID: run, sequence: 1)
        #expect(projection.projection(text: text).groups.count == 1)
        #expect(projection.projection(text: "prefix " + text).groups.isEmpty)
        try projection.consume(.source(id: "unsafe", url: "javascript:alert(1)", title: "unsafe"),
            session: identity, runID: run, sequence: 2)
        #expect(projection.sources.count == 1)
        #expect(projection.sources.first?.url?.absoluteString == source)
        #expect(throws: HanlinHostError.resultMismatch) {
            try projection.consume(.source(id: "provider:" + source,
                url: "https://example.com/rebound", title: "rebound"),
                session: identity, runID: run, sequence: 3)
        }
        #expect(projection.sources.first?.url?.absoluteString == source)
    }

    @Test(arguments: ["anytype", "anytype-any"])
    func oversizedTransientActivityCannotGrowWithoutBound(app: String) throws {
        let identity = try session(app: app)
        var projection = PinkhaHanlinMessageActivity(session: identity, messageID: UUID())
        #expect(throws: HanlinHostError.outputLimitExceeded) {
            try projection.consume(.reasoningDelta(String(repeating: "א", count: 131_073)),
                session: identity, runID: UUID(), sequence: 1)
        }
        #expect(projection.run?.steps.isEmpty == true)
    }

    private func session(app: String, account: String = "disposable-account") throws -> HanlinHostSession {
        .init(conversationID: UUID(), context: .init(namespace: try .init(app: app,
            account: account, workspace: "disposable-space", space: "disposable-space"),
            sceneID: UUID(), generation: UUID()))
    }
}
#endif
