import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

/// Host-private seam, implemented by the native presentation owner, not an SDK authority substitute.
@MainActor
public protocol PinkhaHanlinHostAccess: AnyObject, Sendable {
    var session: HanlinHostSession { get }
    func validate(_ context: HanlinHostContext) throws
    func validateRead(_ context: HanlinHostContext) throws
    func read(_ context: HanlinHostContext) async throws -> PinkhaHanlinTextSnapshot
    func navigate(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult
}

public struct PinkhaHanlinTextSnapshot: Codable, Sendable {
    public struct Block: Codable, Sendable {
        public let reference: String
        public let text: String
        public init(reference: String, text: String) { self.reference = reference; self.text = text }
    }
    public let objectReference: String
    public let spaceReference: String
    public let sourceRevision: String
    public let title: String
    public let blocks: [Block]
    public let coverage: String
    public init(objectReference: String, spaceReference: String, sourceRevision: String,
                title: String, blocks: [Block], coverage: String) {
        self.objectReference = objectReference; self.spaceReference = spaceReference
        self.sourceRevision = sourceRevision; self.title = title; self.blocks = blocks; self.coverage = coverage
    }
}

/// Read-only first tranche. There is deliberately no creation/property/text mutation dispatch.
/// A writable catalog needs a real confirmation owner AND durable original-scope journal first.
@MainActor
public final class PinkhaHanlinHostAdapter: HanlinHostIntegration {
    public nonisolated let apiVersion = HanlinAPIVersion(major: 1, minor: 0)
    private let access: any PinkhaHanlinHostAccess
    private let tool: HanlinHostTool
    private let catalogRevision = HanlinCatalogRevision(1)
    private let maximumCalls = 256
    private var calls: [HanlinToolInvocationID: Call] = [:]
    private var providerCalls: [ProviderCall: HanlinToolInvocationID] = [:]
    private var cancelled = Set<HanlinToolInvocationID>()
    private var pendingRead: (id: HanlinToolInvocationID, race: PinkhaHanlinReadRace)?

    private struct ProviderCall: Hashable {
        let run: UUID
        let step: Int
        let opaqueID: Data
    }
    private struct Fingerprint: Equatable {
        let providerCall: ProviderCall
        let session: HanlinHostSession
        let arguments: Data
        let alias: Data
        let logical: HanlinLogicalToolID
        let descriptor: HanlinDescriptorRevision
        let catalog: HanlinCatalogRevision
        let guarantee: HanlinHostWriteGuarantee
        let revision: Data?
        let limits: HanlinToolInvocationLimits
        let deadline: Date?
        let origin: HanlinExecutionOrigin
    }
    private struct Call {
        let fingerprint: Fingerprint
        var receipt: HanlinHostExecutionResult?
    }

    public init(access: any PinkhaHanlinHostAccess) throws {
        self.access = access
        let logical = HanlinLogicalToolID(providerInstanceID: try .init(validating: "anytype.host"),
                                        localToolID: try .init(validating: "read-context-text"))
        let revision = try HanlinDescriptorRevision(1)
        let schema = try HanlinJSONSchemaDocument.decodeCanonicalJSON(
            Data(#"{"type":"object","properties":{},"additionalProperties":false}"#.utf8),
            defaultDialect: .draft2020_12)
        let descriptor = HanlinToolDescriptor(logicalID: logical, descriptorRevision: revision, owner: .system,
            title: try .init(["en": "Read current document text", "he": "קריאת טקסט המסמך הנוכחי"]),
            summary: try .init(["en": "Bounded plain text from the authorized current document or selected text blocks. No writes or other document lookup."]),
            inputSchema: schema, risk: .sensitiveRead, presentation: .init())
        self.tool = .init(route: .init(alias: "anytype_read_context_text", logicalToolID: logical,
                                     descriptorRevision: revision), descriptor: descriptor, writeGuarantee: .readOnly)
    }

    public func context(for session: HanlinHostSession) async throws -> HanlinHostContext {
        try validate(session)
        return access.session.context
    }

    public func catalog(for context: HanlinHostContext) async throws -> HanlinHostCatalog {
        try access.validate(context)
        guard context == access.session.context else { throw HanlinHostError.staleContext }
        var readable = false
        if context.objectReference != nil {
            do { try access.validateRead(context); readable = true }
            catch HanlinHostError.denied { readable = false }
        }
        let catalog = HanlinHostCatalog(revision: catalogRevision, context: context, tools: readable ? [tool] : [])
        try catalog.validate()
        return catalog
    }

    public func execute(_ invocation: HanlinHostInvocation,
                 progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
        let started = Date()
        // Refuse conditional/independent writes explicitly BEFORE any native operation.
        guard invocation.writeGuarantee == .readOnly, invocation.expectedRevision == nil else {
            return failure(invocation, code: .operationUnavailable, effect: .notDispatched)
        }
        do {
            try validate(invocation.session)
            guard invocation.step >= 0, !invocation.providerCallID.isEmpty,
                  invocation.providerCallID.utf8.count <= 1_024 else { throw HanlinHostError.invalidArguments }
        } catch {
            return failure(invocation, code: safeCode(error), effect: .notDispatched)
        }
        let key = ProviderCall(run: invocation.runID, step: invocation.step, opaqueID: Data(invocation.providerCallID.utf8))
        let validArguments: Bool
        if case .object(let members) = invocation.request.arguments { validArguments = members.isEmpty }
        else { validArguments = false }
        let fingerprint = Fingerprint(providerCall: key, session: invocation.session,
            arguments: Data([validArguments ? 0 : 1]), alias: Data(invocation.request.aliasUsed.utf8),
            logical: invocation.request.logicalToolID, descriptor: invocation.request.descriptorRevision,
            catalog: invocation.request.routingTableRevision, guarantee: invocation.writeGuarantee,
            revision: invocation.expectedRevision.map { Data($0.utf8) }, limits: invocation.request.limits,
            deadline: invocation.request.deadline, origin: invocation.request.origin)
        if let existingID = providerCalls[key] {
            guard existingID == invocation.request.id, calls[existingID]?.fingerprint == fingerprint else {
                throw HanlinHostError.idempotencyConflict
            }
            throw HanlinHostError.duplicateInvocation
        }
        if let existing = calls[invocation.request.id] {
            throw existing.fingerprint == fingerprint ? HanlinHostError.duplicateInvocation : .idempotencyConflict
        }
        do { try validateRequest(invocation, now: started) }
        catch { return failure(invocation, code: safeCode(error), effect: .notDispatched) }
        guard calls.count < maximumCalls else { throw HanlinHostError.outputLimitExceeded }
        calls[invocation.request.id] = Call(fingerprint: fingerprint)
        providerCalls[key] = invocation.request.id
        var readRace: PinkhaHanlinReadRace?
        do {
            try checkCurrent(invocation)
            await progress(try .init(invocationID: invocation.request.id, sequence: 1, timestamp: .now,
                                    fractionCompleted: 0, message: "Reading current document"))
            try checkCurrent(invocation) // Progress callback is an await, not a grant to continue.
            guard pendingRead?.race.hasEnded != false else { throw HanlinHostError.outputLimitExceeded }
            let race = PinkhaHanlinReadRace()
            readRace = race
            pendingRead = (invocation.request.id, race)
            let snapshot = try await boundedRead(invocation, race: race)
            guard snapshot.objectReference.utf8.elementsEqual(invocation.session.context.objectReference?.utf8 ?? "".utf8),
                  snapshot.spaceReference.utf8.elementsEqual(invocation.session.context.namespace.space.utf8),
                  invocation.session.context.matchesRevision(snapshot.sourceRevision),
                  snapshot.blocks.count <= 128, snapshot.title.utf8.count <= 512,
                  snapshot.blocks.allSatisfy({ !$0.reference.isEmpty && $0.reference.utf8.count <= 256 }),
                  Set(snapshot.blocks.map { Data($0.reference.utf8) }).count == snapshot.blocks.count,
                  snapshot.blocks.reduce(0, { $0 + $1.text.utf8.count }) <= 24_576 else { throw HanlinHostError.resultMismatch }
            let selected = invocation.session.context.selectionReferences.map { Data($0.utf8) }
            if !selected.isEmpty {
                guard Set(selected) == Set(snapshot.blocks.map { Data($0.reference.utf8) }),
                      snapshot.coverage == "selectedTextBlocksOnly" else { throw HanlinHostError.resultMismatch }
            } else {
                guard snapshot.coverage == "documentTextBlocksOnly" else { throw HanlinHostError.resultMismatch }
            }
            let bytes = try JSONEncoder().encode(snapshot)
            guard bytes.count <= min(invocation.request.limits.maximumOutputBytes, 32_768) else {
                throw HanlinHostError.outputLimitExceeded
            }
            guard let text = String(data: bytes, encoding: .utf8) else { throw HanlinHostError.invalidRecord }
            let result = HanlinHostExecutionResult(result: .init(invocationID: invocation.request.id,
                logicalToolID: invocation.request.logicalToolID, outcome: .completed([.text(text)]),
                startedAt: started, completedAt: .now), effectState: .confirmedNoEffect, context: invocation.session.context)
            // Keep only metadata, in the ORIGINAL scope, before stale delivery is checked.
            calls[invocation.request.id]?.receipt = result.metadataReceipt()
            try checkCurrent(invocation)
            await progress(try .init(invocationID: invocation.request.id, sequence: 2, timestamp: .now,
                                    fractionCompleted: 1, message: "Document read completed"))
            try checkCurrent(invocation)
            return result
        } catch {
            if calls[invocation.request.id]?.receipt == nil {
                calls[invocation.request.id]?.receipt = failure(invocation, code: safeCode(error),
                    effect: readRace?.wasDispatched == true ? .confirmedNoEffect : .notDispatched).metadataReceipt()
            }
            // Never deliver a payload/progress/error detail through a revoked presentation.
            try validate(invocation.session)
            if Task.isCancelled || cancelled.contains(invocation.request.id) { throw HanlinHostError.cancelled }
            return failure(invocation, code: safeCode(error), effect: readRace?.wasDispatched == true ? .confirmedNoEffect : .notDispatched)
        }
    }

    public func cancel(_ invocation: HanlinToolInvocationID) async {
        // Cancellation is a request fence, not native rollback. This adapter dispatches reads only.
        if calls[invocation] != nil || cancelled.count < maximumCalls { cancelled.insert(invocation) }
        if pendingRead?.id == invocation { pendingRead?.race.cancel() }
    }

    public func open(_ destination: HanlinHostDestination) async throws -> HanlinHostNavigationResult {
        try access.validate(destination.context)
        guard destination.context == access.session.context else { throw HanlinHostError.staleContext }
        try Task.checkCancellation()
        let result = try access.navigate(destination) // Synchronous native queue boundary on MainActor.
        try access.validate(destination.context)
        try result.validate(for: destination)
        return result
    }

    /// Metadata-only, original-context evidence for host reconciliation/testing; no read authority.
    public func receipt(for invocation: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
        calls[invocation]?.receipt
    }

    private func validate(_ session: HanlinHostSession) throws {
        guard session == access.session else { throw HanlinHostError.staleContext }
        try access.validate(session.context)
    }

    private func checkCurrent(_ invocation: HanlinHostInvocation) throws {
        try validate(invocation.session)
        try access.validateRead(invocation.session.context)
        try Task.checkCancellation()
        guard !cancelled.contains(invocation.request.id) else { throw HanlinHostError.cancelled }
        guard let deadline = invocation.request.deadline, deadline > .now else { throw HanlinHostError.deadlineExceeded }
    }

    private func validateRequest(_ invocation: HanlinHostInvocation, now: Date) throws {
        let request = invocation.request
        guard request.logicalToolID == tool.route.logicalToolID,
              request.aliasUsed.utf8.elementsEqual(tool.route.alias.utf8),
              request.descriptorRevision == tool.route.descriptorRevision,
              request.routingTableRevision == catalogRevision else { throw HanlinHostError.unknownTool }
        guard access.session.context.objectReference != nil, request.origin == .assistantModel,
              request.grantIDs.isEmpty, request.appSessionID == nil, request.runtimeSessionID == nil,
              PinkhaHanlinInvocationEnvelope.acceptsSDKIdentity(request), invocation.step >= 0,
              !invocation.providerCallID.isEmpty, invocation.providerCallID.utf8.count <= 1_024,
              request.limits.timeoutMilliseconds > 0, request.limits.timeoutMilliseconds <= 30_000,
              request.limits.maximumOutputBytes > 0, request.limits.maximumOutputBytes <= 8 * 1_048_576,
              let deadline = request.deadline, deadline > now,
              deadline.timeIntervalSince(now) <= 30 else { throw HanlinHostError.invalidArguments }
        // Complete validation of this advertised schema: exactly an empty JSON object.
        guard case .object(let members) = request.arguments, members.isEmpty else { throw HanlinHostError.invalidArguments }
    }

    private func boundedRead(_ invocation: HanlinHostInvocation, race: PinkhaHanlinReadRace) async throws -> PinkhaHanlinTextSnapshot {
        let remaining = min(Double(invocation.request.limits.timeoutMilliseconds) / 1_000,
                            invocation.request.deadline?.timeIntervalSinceNow ?? 0)
        guard remaining > 0 else { race.operationEnded(); throw HanlinHostError.deadlineExceeded }
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                guard race.install(continuation) else { race.operationEnded(); return }
                let worker = Task { @MainActor in
                    defer { race.operationEnded() }
                    do {
                        // This is the queued worker boundary, not the earlier task creation time.
                        try self.checkCurrent(invocation)
                        guard race.beginDispatch() else { return }
                        let snapshot = try await self.access.read(invocation.session.context)
                        race.finish(.success(snapshot))
                    } catch { race.finish(.failure(error)) }
                }
                let timer = Task.detached {
                    do {
                        try await Task.sleep(for: .seconds(remaining))
                        race.finish(.failure(HanlinHostError.deadlineExceeded))
                    } catch {} // Completion cancels the timer; it cannot replace the first result.
                }
                race.attach(worker: worker, timer: timer)
            }
        } onCancel: { race.cancel() }
    }

    private func failure(_ invocation: HanlinHostInvocation, code: HanlinErrorCode,
                         effect: HanlinHostEffectState) -> HanlinHostExecutionResult {
        .init(result: .init(invocationID: invocation.request.id, logicalToolID: invocation.request.logicalToolID,
            outcome: .failed(.init(code: code, userMessage: "Host operation unavailable or no longer authorized")),
            completedAt: .now), effectState: effect, context: invocation.session.context)
    }

    private func safeCode(_ error: Error) -> HanlinErrorCode {
        switch error {
        case is CancellationError: .cancelled
        case HanlinHostError.cancelled: .cancelled
        case HanlinHostError.deadlineExceeded: .timedOut
        case HanlinHostError.invalidArguments: .invalidArguments
        case HanlinHostError.outputLimitExceeded: .resourceLimitExceeded
        case HanlinHostError.staleContext, HanlinHostError.denied: .permissionDenied
        default: .operationUnavailable
        }
    }
}
