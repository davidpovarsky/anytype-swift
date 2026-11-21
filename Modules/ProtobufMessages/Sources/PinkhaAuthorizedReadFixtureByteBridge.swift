#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_T2_AUTHORIZED_READ_FIXTURE
import Foundation
import Lib

/// Test-host setup only. The native write RPC and its authority are unchanged.
/// The ordinary candidate and default app builds do not compile this wrapper.
@MainActor
public enum PinkhaAuthorizedReadFixtureByteBridge {
    public static func append(_ request: Data, lease: PinkhaNativeReadLease) async throws -> Data {
        try Task.checkCancellation()
        try lease.validate()
        guard !request.isEmpty, request.count <= 128 * 1024 else {
            throw PinkhaNativeReadLifetimeError.invalidByteBoundary
        }
        let response: Data = await withCheckedContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                continuation.resume(returning: Lib.ServicePinkhaTorahOperationsAppend(request) ?? Data())
            }
        }
        try Task.checkCancellation()
        try lease.validate()
        return try PinkhaAuthorizedReadByteBridge.checkedResponse(response)
    }
}
#endif
