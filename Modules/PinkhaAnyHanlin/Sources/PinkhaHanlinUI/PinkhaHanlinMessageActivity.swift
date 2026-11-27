#if canImport(UIKit)
import Foundation
import HanlinAgentActivityCore
import HanlinChatCore
import HanlinHostContracts
import HanlinPresentationKit

/// A bounded, transient projection of this presentation's authentic SDK stream.
/// The original SDK renders activity/citations. This value owns no tool authority,
/// effect receipt, provider loop or restored execution state.
@MainActor
struct PinkhaHanlinMessageActivity {
    let session: HanlinHostSession
    let messageID: UUID
    private(set) var run: AgentRun?
    private(set) var sources: [HanlinSourceReference] = []
    private var citationAnchorsByText: [String: [HanlinCitationAnchor]] = [:]
    private var citationCount = 0
    private var lastSequence: UInt64?
    private var nextStep = 0
    private var reasoningIndex: Int?
    private var answerTextStartedAt: Date?
    private var retainedBytes = 0
    private var ended = false

    init(session: HanlinHostSession, messageID: UUID) {
        self.session = session
        self.messageID = messageID
    }

    mutating func consume(_ event: HanlinAISDKStreamEvent, session: HanlinHostSession,
                          runID: UUID, sequence: UInt64, now: Date = Date()) throws {
        guard self.session == session, !ended,
              run.map({ $0.id == runID }) ?? true,
              lastSequence.map({ sequence > $0 }) ?? true else {
            throw HanlinHostError.staleContext
        }
        if run == nil { run = AgentRun(id: runID, groupID: session.conversationID, startedAt: now) }
        lastSequence = sequence
        switch event {
        case .runStarted, .stepStarted:
            finishReasoning(at: now)
            answerTextStartedAt = nil
            run?.pendingModelRequestID = runID.uuidString + ":" + String(sequence)
        case .reasoningDelta(let delta):
            try retain(delta)
            run?.pendingModelRequestID = nil
            if reasoningIndex == nil {
                try addStep(.init(sequence: nextStep, kind: .reasoning,
                    title: PinkhaHanlinStrings.thinking, startedAt: now, output: ""))
                reasoningIndex = (run?.steps.count ?? 1) - 1
            }
            if let index = reasoningIndex {
                let output = (run?.steps[index].output ?? "") + delta
                run?.steps[index].output = output
            }
        case .textDelta(let delta):
            if !delta.isEmpty, answerTextStartedAt == nil { answerTextStartedAt = now }
            finishReasoning(at: now)
            run?.pendingModelRequestID = nil
            // The original activity renderer intentionally excludes answer text.
        case .source(let id, let value, let title):
            try admitSource(id: id, value: value, title: title)
        case .textCitations(let annotations):
            guard citationCount + annotations.count <= 256 else { throw HanlinHostError.outputLimitExceeded }
            citationCount += annotations.count
            for annotation in annotations {
                guard let range = annotation.utf16Range else { continue }
                if citationAnchorsByText[annotation.text] == nil { try retain(annotation.text) }
                try admitSource(id: "provider:" + annotation.url, value: annotation.url, title: annotation.title)
                citationAnchorsByText[annotation.text, default: []].append(
                    .init(sourceID: "provider:" + annotation.url, range: range))
            }
        case .toolCallArgumentsStarted(let id, let name):
            finishReasoning(at: now)
            answerTextStartedAt = nil
            run?.pendingModelRequestID = nil
            try beginCall(id: id, name: name, at: now)
        case .toolCall(let call):
            finishReasoning(at: now)
            answerTextStartedAt = nil
            run?.pendingModelRequestID = nil
            try beginCall(id: call.id, name: call.name, at: now)
            // Input is deliberately not copied into another transcript store.
            // The existing native consent dialog still shows the actual request.
        case .toolResult(let id, let name, let output, _, let isError):
            try retain(output)
            try beginCall(id: id, name: name, at: now)
            if let index = callIndex(id) {
                run?.steps[index].status = isError ? .failed : .completed
                run?.steps[index].completedAt = now
            }
            let descriptor = ToolPresentationRegistry.presentation(for: name)
            try addStep(.init(externalID: "execution:" + id + ":execution", sequence: nextStep,
                kind: descriptor.activityKind, title: descriptor.completedDescription,
                status: isError ? .failed : .completed, startedAt: now, completedAt: now, output: output))
        case .toolApprovalRequest(let approval):
            try retain(approval.approvalID)
            guard (run?.approvals.count ?? 0) < 128 else { throw HanlinHostError.outputLimitExceeded }
            try beginCall(id: approval.toolCallID, name: approval.toolName, at: now)
            run?.approvals.append(.init(id: approval.approvalID, canonicalRunID: runID,
                callID: approval.toolCallID, toolName: approval.toolName,
                reviewText: "", disposition: approval.providerExecuted ? .providerRequired : .awaiting))
        case .toolApprovalResolved(let approval, let allowed):
            if let index = run?.approvals.firstIndex(where: { $0.id == approval.approvalID }) {
                run?.approvals[index].disposition = allowed ? .allowedOnce : .notApproved
            }
            if !allowed, let index = callIndex(approval.toolCallID) {
                run?.steps[index].status = .cancelled
                run?.steps[index].completedAt = now
            }
        case .toolOutputDenied(let id, _):
            if let index = callIndex(id) {
                run?.steps[index].status = .failed
                run?.steps[index].completedAt = now
            }
        case .stepFinished:
            finishReasoning(at: now)
            run?.pendingModelRequestID = nil
        case .finished:
            // Provider EOF is not the native-write drain boundary. The consumer
            // calls finish only after the original SDK stream/worker join.
            finishReasoning(at: now)
            run?.pendingModelRequestID = nil
        case .cancelled:
            finishReasoning(at: now)
            run?.pendingModelRequestID = nil
        case .structuredResponseStarted, .structuredPart, .file, .toolCallArgumentsDelta:
            break
        }
    }

    mutating func finish(status: AgentActivityStatus, now: Date = Date()) {
        guard !ended else { return }
        ended = true
        finishReasoning(at: now)
        run?.pendingModelRequestID = nil
        run?.status = status
        run?.completedAt = now
        if status == .completed { run?.finalAnswerStartedAt = answerTextStartedAt }
        for index in run?.steps.indices ?? 0..<0 {
            guard run?.steps[index].status == .running || run?.steps[index].status == .pending else { continue }
            // A missing tool result is never synthesized as successful execution.
            run?.steps[index].status = status == .completed ? .failed : status
            run?.steps[index].completedAt = now
        }
    }

    func snapshot(isActive: Bool, hasAnswerText: Bool) -> HanlinAgentActivitySnapshot {
        .init(run: run, isActive: isActive, hasAnswerText: hasAnswerText)
    }

    func projection(text: String) -> HanlinCitationProjection {
        // An annotation on another ordered text part has no offset in this row.
        // Never infer proximity or translate offsets across parts.
        var anchors = citationAnchorsByText[text] ?? []
        anchors += HanlinCitationProjection.explicitSourceLinkAnchors(text: text, sources: sources)
        return HanlinCitationProjection.make(text: text, messageID: messageID, sources: sources, anchors: anchors)
    }

    private mutating func retain(_ value: String) throws {
        guard value.utf8.count <= 262_144, retainedBytes <= 524_288 - value.utf8.count else {
            throw HanlinHostError.outputLimitExceeded
        }
        retainedBytes += value.utf8.count
    }

    private mutating func addStep(_ step: AgentActivityStep) throws {
        guard nextStep < 128 else { throw HanlinHostError.outputLimitExceeded }
        nextStep += 1
        run?.steps.append(step)
    }

    private func callIndex(_ id: String) -> Int? {
        run?.steps.firstIndex { $0.externalID == "call:" + id }
    }

    private mutating func beginCall(id: String, name: String, at now: Date) throws {
        guard id.utf8.count <= 4096, name.utf8.count <= 512 else { throw HanlinHostError.outputLimitExceeded }
        guard callIndex(id) == nil else { return }
        let descriptor = ToolPresentationRegistry.presentation(for: name)
        // Parsed/streamed arguments prove a request only. Native execution is
        // represented only when an actual original SDK result arrives.
        try addStep(.init(externalID: "call:" + id, sequence: nextStep,
            kind: .toolCall, title: descriptor.runningDescription, status: .pending, startedAt: now))
    }

    private mutating func finishReasoning(at now: Date) {
        guard let index = reasoningIndex else { return }
        run?.steps[index].status = .completed
        run?.steps[index].completedAt = now
        reasoningIndex = nil
    }

    private mutating func admitSource(id: String, value: String, title: String?) throws {
        guard id.utf8.count <= 8192, value.utf8.count <= 8192,
              (title?.utf8.count ?? 0) <= 4096 else { throw HanlinHostError.outputLimitExceeded }
        guard let url = URL(string: value), ["https", "http"].contains(url.scheme?.lowercased() ?? ""),
              url.host?.isEmpty == false, url.user == nil, url.password == nil else { return }
        if let existing = sources.first(where: { $0.id == id }) {
            guard existing.url == url else { throw HanlinHostError.resultMismatch }
            return
        }
        guard sources.count < 128 else { throw HanlinHostError.outputLimitExceeded }
        try retain(id + value + (title ?? ""))
        let label = title.flatMap { $0.isEmpty ? nil : $0 } ?? url.host ?? value
        sources.append(.init(id: id, title: label, url: url))
    }
}
#endif
