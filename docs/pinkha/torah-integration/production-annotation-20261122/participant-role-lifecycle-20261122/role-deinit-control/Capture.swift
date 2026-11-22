import Foundation

enum EditorDocumentWriteRejection: Sendable, Equatable {
    case retired
    case wrongContext
    case documentChanged
    case notHandling
    case notEditable
    case cancelled
    case invalidLease
    case unqualifiedDispatch
    case captureInProgress
    case failedWrite
}

enum EditorDocumentWriteError: Error, Sendable, Equatable {
    case rejected(EditorDocumentWriteRejection)
    case completedWithoutOwnership(EditorDocumentWriteRejection)
}

struct EditorDocumentWriteCapture: Sendable {
    let source: EditorDocumentWriteLifetime
    let token: EditorDocumentWriteLifetime.Token

    init(_ source: EditorDocumentWriteLifetime) throws {
        guard let token = source.token() else { throw EditorDocumentWriteError.rejected(.retired) }
        self.source = source
        self.token = token
    }

    init(source: EditorDocumentWriteLifetime, token: EditorDocumentWriteLifetime.Token) {
        self.source = source
        self.token = token
    }

    func validate() throws {
        guard source.isCurrent(token) else { throw EditorDocumentWriteError.rejected(.retired) }
    }

    static func acquireAll(_ captures: [Self]) throws -> [EditorDocumentWriteLifetime.Observation] {
        var admissions: [EditorDocumentWriteLifetime.Observation] = []
        do {
            for capture in captures {
                guard let admission = capture.source.admitOperation(capture.token) else {
                    throw EditorDocumentWriteError.rejected(.retired)
                }
                admissions.append(admission)
            }
            return admissions
        } catch {
            for admission in admissions { admission.cancel() }
            throw error
        }
    }

    func accountDispatchBinding() -> InvocationDispatchBinding {
        InvocationDispatchBinding { _ in
            try validate()
            return InvocationDispatchPermit {
                let admissions = try Self.acquireAll([self])
                return InvocationDispatchCompletion { for admission in admissions { admission.cancel() } }
            }
        }
    }
}

