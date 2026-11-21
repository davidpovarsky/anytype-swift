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
        let reader: AnyAuthorizedTorahOperationReader
        do {
            reader = try await session.perform { lease in
                guard client.expectedAccountID.utf8.elementsEqual(lease.workspace.accountID.utf8) else {
                    throw TorahOperationReadError.accountChanged
                }
                let stream = AnyStreamSession(generation: lease.generation)
                return try await AnyAuthorizedTorahOperationReader(
                    client: client, workspace: lease.workspace, session: stream)
            }
        } catch {
            throw Self.mappedError(error)
        }
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
            throw Self.mappedError(error)
        }
    }

    private static func mappedError(_ error: any Error) -> any Error {
        if error is CancellationError { return error }
        if let shared = error as? TorahOperationReadError { return shared }
        if let host = error as? AnyHostError {
            switch host {
            case .sessionClosed, .engineRestarted, .wrongWorkspace:
                return TorahOperationReadError.accountChanged
            default: break
            }
        }
        return TorahOperationReadError.nativeFailure
    }
}
