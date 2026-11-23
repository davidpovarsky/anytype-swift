enum OriginalAuthRequestContext {
    @TaskLocal static var parent: OriginalAuthAttempt?
}

enum OriginalAuthFlowError: Error {
    case busy
    case successfulStopRequired
}

/// One actual original Auth/Hanlin operation. The original Lifetime supplies
/// synchronous retirement, admission and actual-operation drain; no new account
/// generation or asynchronous cancellation flag is introduced.
final class OriginalAuthAttempt: Sendable {
    enum Kind: Equatable, Sendable { case startup, ordinary, stop }
    let kind: Kind
    let captures: [EditorDocumentWriteCapture]
    private let lifetime: EditorDocumentWriteLifetime
    private let outer: EditorDocumentWriteLifetime.Observation
    private let parent: OriginalAuthAttempt?
    private let parentObservations: [EditorDocumentWriteLifetime.Observation]

    init(
        kind: Kind,
        parent: OriginalAuthAttempt? = OriginalAuthRequestContext.parent,
        restricting restrictions: [EditorDocumentWriteCapture] = []
    ) throws {
        try Task.checkCancellation()
        try parent?.validate()
        for restriction in restrictions { try restriction.validate() }
        let inheritedCaptures = (parent?.captures ?? []) + restrictions
        let lifetime = EditorDocumentWriteLifetime()
        let capture = try EditorDocumentWriteCapture(lifetime)
        guard let outer = lifetime.admitOperation(capture.token) else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        self.kind = kind
        self.lifetime = lifetime
        self.outer = outer
        self.parent = parent
        captures = inheritedCaptures + [capture]
        parentObservations = inheritedCaptures.map { value in
            value.source.observe(value.token) { lifetime.markUnavailable() }
        }
    }

    func validate() throws {
        try Task.checkCancellation()
        for capture in captures { try capture.validate() }
    }

    var isCurrent: Bool {
        captures.allSatisfy { $0.source.isCurrent($0.token) }
    }

    func retire() { lifetime.markUnavailable() }
    func finishOuter() { outer.cancel() }
    func waitForDrain() async { await lifetime.waitForOperationsToDrain() }

    func admitStage() throws -> [EditorDocumentWriteLifetime.Observation] {
        try validate()
        return try EditorDocumentWriteCapture.acquireAll(captures)
    }

    /// Startup native calls are tracked by this exact attempt, not added to the
    /// account-operation drain which AccountStop itself must wait before dispatch.
    func startupBinding(validating: @escaping @Sendable () throws -> Void = {}) -> InvocationDispatchBinding {
        InvocationDispatchBinding(committedEvents: { nil }) { [self] _ in
            try validate()
            try validating()
            return InvocationDispatchPermit { [self] in
                try validate()
                try validating()
                let admissions = try EditorDocumentWriteCapture.acquireAll(captures)
                return InvocationDispatchCompletion {
                    for admission in admissions { admission.cancel() }
                }
            }
        }
    }

    deinit {
        retire()
        finishOuter()
    }
}

