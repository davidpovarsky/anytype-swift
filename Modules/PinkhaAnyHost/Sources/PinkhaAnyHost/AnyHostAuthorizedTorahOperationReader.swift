import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaKit

/// Binds the shared native reader to the application's actual account/Space
/// owner. The private stream lifetime inherits that owner's generation; all
/// work also runs inside its engine-run check and revoke/cancel/drain boundary.
public struct AnyHostAuthorizedTorahOperationReader: TorahAuthorizedOperationReading, Sendable {
    public let scope: TorahOperationReadScope
    private let session: AnyApplicationSession
    private let reader: AnyAuthorizedTorahOperationReader

    public init(client: AnyHTTPClient, session: AnyApplicationSession) async throws {
        let workspace = session.workspace
        guard client.expectedAccountID.utf8.elementsEqual(workspace.accountID.utf8),
              await session.isActive else {
            throw TorahOperationReadError.accountChanged
        }
        let stream = AnyStreamSession(generation: session.generation)
        let reader = try await AnyAuthorizedTorahOperationReader(
            client: client, workspace: workspace, session: stream)
        self.session = session
        self.reader = reader
        self.scope = reader.scope
    }

    public func readOperation(operationID: String) async throws -> TorahAuthorizedOperationSnapshot {
        try TorahAuthorizedOperationReadContract.validateOperationID(operationID)
        do {
            let reader = reader, scope = scope
            return try await session.perform { lease in
                guard lease.generation == scope.sessionGeneration,
                      lease.workspace.accountID.utf8.elementsEqual(scope.accountID.utf8),
                      lease.workspace.spaceID.utf8.elementsEqual(scope.spaceID.utf8) else {
                    throw TorahOperationReadError.accountChanged
                }
                let value = try await reader.readOperation(operationID: operationID)
                guard value.scope == scope else { throw TorahOperationReadError.malformedNativeResponse }
                // perform validates the real owner and native boot again after
                // this closure returns, before delivering the acquired value.
                return value
            }
        } catch {
            if error is CancellationError { throw error }
            if let shared = error as? TorahOperationReadError { throw shared }
            if let host = error as? AnyHostError {
                switch host {
                case .sessionClosed, .engineRestarted, .wrongWorkspace:
                    throw TorahOperationReadError.accountChanged
                default: break
                }
            }
            throw TorahOperationReadError.nativeFailure
        }
    }
}
