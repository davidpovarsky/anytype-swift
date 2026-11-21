import Foundation
import PinkhaKit
import PinkhaHeartEngine
import ProtobufMessages

@MainActor
public enum HeartLibAuthorizedOperationReader {
    /// Account identity comes from the existing successful native invocation.
    /// A caller-supplied SpaceID only selects an already verified owned lease.
    public static func makeSession(forOpenedSpaceID spaceID: String) throws -> HeartAuthorizedOperationSession {
#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
        do {
            let lease = try PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: spaceID)
            let transport = HeartLibOperationTransport(lease: lease)
            let session = try HeartAuthorizedOperationSession(accountID: lease.accountID, spaceID: lease.spaceID,
                sessionGeneration: lease.generation, transport: transport)
            transport.session = session
            try lease.observeRetirement(transport)
            return session
        } catch is PinkhaNativeReadLifetimeError {
            throw TorahOperationReadError.accountChanged
        }
#else
        throw TorahOperationReadError.unsupportedContract
#endif
    }
}

#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
@MainActor
private final class HeartLibOperationTransport: HeartAuthorizedOperationTransport, PinkhaNativeReadLeaseObserver {
    let lease: PinkhaNativeReadLease
    weak var session: HeartAuthorizedOperationSession?
    init(lease: PinkhaNativeReadLease) { self.lease = lease }

    func readAuthorizedOperation(request: Data) async throws -> Data {
        do { return try await PinkhaAuthorizedReadByteBridge.read(request, lease: lease) }
        catch let error as PinkhaNativeReadLifetimeError {
            switch error {
            case .noCurrentOwnedScope, .retired: throw TorahOperationReadError.accountChanged
            case .invalidByteBoundary: throw TorahOperationReadError.malformedNativeResponse
            case .responseTooLarge: throw TorahOperationReadError.readLimit
            }
        }
    }

    func nativeReadLeaseDidRetire() { session?.invalidate() }
}
#endif
