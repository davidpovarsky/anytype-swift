#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import Lib

/// The candidate framework must export the actual generated gomobile entry.
/// There is no dynamic symbol lookup or fallback to a legacy read API.
@MainActor
public enum PinkhaAuthorizedReadByteBridge {
    public static func read(_ request: Data, lease: PinkhaNativeReadLease) async throws -> Data {
        try Task.checkCancellation()
        try lease.validate()
        guard !request.isEmpty, request.count <= 2048 else {
            throw PinkhaNativeReadLifetimeError.invalidByteBoundary
        }
        let bytes: Data = await withCheckedContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                continuation.resume(returning: Lib.ServicePinkhaTorahAuthorizedOperationRead(request) ?? Data())
            }
        }
        try Task.checkCancellation()
        try lease.validate()
        return try checkedResponse(bytes)
    }

    static func checkedResponse(_ bytes: Data) throws -> Data {
        guard bytes.count <= 4 * 1024 * 1024 else {
            throw PinkhaNativeReadLifetimeError.responseTooLarge
        }
        guard !bytes.isEmpty else {
            throw PinkhaNativeReadLifetimeError.invalidByteBoundary
        }
        // Private history bytes never pass through Invocation's body logger.
        return bytes
    }
}
#endif
