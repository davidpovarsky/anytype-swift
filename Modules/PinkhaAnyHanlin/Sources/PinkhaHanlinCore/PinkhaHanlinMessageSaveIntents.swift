import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

/// Transient presentation correlation, never native write authority or a
/// replacement journal. A completed original SDK run must separately admit the
/// origin. Only its exact original host result can display a successful save.
public struct PinkhaHanlinMessageSaveIntents: Sendable {
    public static let maximumAttempts = 256

    public enum Status: String, Sendable {
        case pending, committed, notCommitted, uncertain, unconfirmed
    }

    public struct Intent: Sendable {
        public let origin: HanlinHostInteractionOrigin
        public let requestID: UUID
        public let titleSHA256: String
        public let markdownSHA256: String
        public let logicalToolID: HanlinLogicalToolID
        public fileprivate(set) var executionRunID: UUID?
        public fileprivate(set) var resultID: UUID?
        public fileprivate(set) var status: Status = .pending

        /// Recheck the exact complete message bytes immediately before entering
        /// the original SDK. A menu closure cannot substitute another body.
        public func request(title: String, markdown: String) throws -> HanlinHostInteractionRequest {
            guard titleSHA256 == PinkhaHanlinSaveMessagePlan.digest(Data(title.utf8)),
                  markdownSHA256 == PinkhaHanlinSaveMessagePlan.digest(Data(markdown.utf8)) else {
                throw HanlinHostError.staleContext
            }
            return .init(requestID: requestID, origin: origin,
                actionID: PinkhaHanlinSaveMessagePlan.alias,
                arguments: .object(["title": .string(title), "markdown": .string(markdown)]))
        }
    }

    public let session: HanlinHostSession
    private var attempts: [UUID: Intent] = [:]

    public init(session: HanlinHostSession) { self.session = session }

    public var count: Int { attempts.count }
    public func intent(for messageID: UUID) -> Intent? { attempts[messageID] }
    public func canReserve(messageID: UUID) -> Bool {
        attempts[messageID] == nil && attempts.count < Self.maximumAttempts
    }

    /// Even a cancelled/failed intent retains its original request ID for this
    /// presentation. Deleting a transcript row cannot free a replay slot.
    public mutating func reserve(origin: HanlinHostInteractionOrigin, title: String,
                                 markdown: String) throws -> Intent {
        guard origin.session == session, canReserve(messageID: origin.messageID) else {
            throw HanlinHostError.invalidArguments
        }
        try PinkhaHanlinSaveMessagePlan.validateContent(title: title, markdown: markdown)
        let logical = HanlinLogicalToolID(providerInstanceID: try .init(validating: "anytype.host"),
            localToolID: try .init(validating: PinkhaHanlinSaveMessagePlan.localToolID))
        let intent = Intent(origin: origin, requestID: UUID(),
            titleSHA256: PinkhaHanlinSaveMessagePlan.digest(Data(title.utf8)),
            markdownSHA256: PinkhaHanlinSaveMessagePlan.digest(Data(markdown.utf8)),
            logicalToolID: logical)
        attempts[origin.messageID] = intent
        return intent
    }

    public mutating func bindExecution(messageID: UUID, requestID: UUID, runID: UUID) throws {
        guard var intent = attempts[messageID], intent.requestID == requestID,
              intent.status == .pending, intent.executionRunID == nil,
              runID != intent.origin.runID else { throw HanlinHostError.staleContext }
        intent.executionRunID = runID
        attempts[messageID] = intent
    }

    /// Receipts from another account, message, original run or tool cannot mark
    /// this message as saved. The result carries no replacement write permission.
    @discardableResult
    public mutating func observe(_ event: HanlinHostResultEvent) -> UUID? {
        guard event.call.session == session, event.result.context == session.context,
              event.call.step == 0,
              let messageID = attempts.first(where: { _, intent in
                  intent.executionRunID == event.call.runID &&
                  event.call.providerCallID.utf8.elementsEqual(intent.requestID.uuidString.utf8) &&
                  intent.logicalToolID == event.call.logicalToolID
              })?.key,
              var intent = attempts[messageID], intent.resultID == nil,
              intent.status == .pending else { return nil }
        intent.resultID = event.resultID
        switch event.result.effectState {
        case .confirmedCommitted:
            if case .completed = event.result.result.outcome { intent.status = .committed }
            else { intent.status = .uncertain }
        case .confirmedNoEffect, .notDispatched: intent.status = .notCommitted
        case .uncertain: intent.status = .uncertain
        }
        attempts[messageID] = intent
        return messageID
    }

    /// Completion of the SDK call itself is not a native commit receipt. Keep
    /// an unconfirmed action unavailable instead of silently generating a retry.
    public mutating func finishWithoutReceipt(messageID: UUID, requestID: UUID) {
        guard var intent = attempts[messageID], intent.requestID == requestID,
              intent.status == .pending else { return }
        intent.status = .unconfirmed
        attempts[messageID] = intent
    }
}
