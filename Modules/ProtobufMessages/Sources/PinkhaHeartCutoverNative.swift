#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_HEART_CUTOVER_V1
import Foundation
import Lib

public extension PinkhaHeartCutoverClient {
    /// Requires the coherent native framework exporting all five generated
    /// cutover byte methods. Each call also checks the supplied exact native
    /// source/runtime profile and the existing account/Space lifetime lease.
    static func native(profile: PinkhaHeartCutoverProfile) -> PinkhaHeartCutoverClient {
        .init(io: .init(
            runtimeVersion: {
                try await ClientCommands.appGetVersion(.init()).invoke(qos: .userInitiated).version
            },
            invoke: { method, request in
                // Await the original native call even after caller cancellation.
                // The typed client retains a validated committed receipt while
                // withholding private resolution from a cancelled/retired owner.
                // These private frames never enter Invocation's body logger.
                await withCheckedContinuation { continuation in
                    DispatchQueue.global(qos: .userInitiated).async {
                        let response: Data?
                        switch method {
                        case .sourceRead:
                            response = Lib.ServicePinkhaTorahCutoverSourceRead(request)
                        case .read:
                            response = Lib.ServicePinkhaTorahCutoverRead(request)
                        case .append:
                            response = Lib.ServicePinkhaTorahCutoverAppend(request)
                        case .importFact:
                            response = Lib.ServicePinkhaTorahCutoverImport(request)
                        case .associationAppend:
                            response = Lib.ServicePinkhaTorahCutoverAssociationAppend(request)
                        }
                        continuation.resume(returning: response ?? Data())
                    }
                }
            }
        ), profile: profile)
    }
}
#endif
