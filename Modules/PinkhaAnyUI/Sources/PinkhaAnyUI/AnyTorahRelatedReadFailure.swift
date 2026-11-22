import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyHost
import TorahInspectorCore

/// This boundary receives native Any reads only. Provider errors must not be
/// converted into an authority decision from their message or localized text.
enum AnyTorahRelatedReadFailure {
    static func classify(_ error: Error, ownerIsActive: Bool) -> TorahRelatedDocumentsAccessError? {
        // A revoked owner can cancel its in-flight task before it throws a
        // session error. Ordinary cancellation with a live owner stays ordinary.
        guard ownerIsActive else { return .invalidated }
        if let host = error as? AnyHostError {
            switch host {
            case .sessionClosed, .engineRestarted, .wrongWorkspace: return .invalidated
            default: return nil
            }
        }
        if let native = error as? AnyEngineError {
            switch native {
            case .accountChanged: return .invalidated
            case .http(status: 401, code: _): return .invalidated
            case .http(status: 403, code: _): return .denied
            default: return nil
            }
        }
        if let repository = error as? TorahAssociationRepositoryError,
           case .permissionDenied = repository {
            return .denied
        }
        return error as? TorahRelatedDocumentsAccessError
    }
}
