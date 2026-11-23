#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import Lib

public extension PinkhaHeartSemanticAnchorClient {
    /// Requires a real SDK exporting ServicePinkhaSemanticAnchorCapture from
    /// the exact page154 profile. The current production139 SDK is unsupported.
    static func page154() -> PinkhaHeartSemanticAnchorClient {
        .init(io: .init(
            runtimeVersion: {
                try await ClientCommands.appGetVersion(.init()).invoke(qos: .userInitiated).version
            },
            read: { spaceID, objectID in
                try await ClientCommands.objectShow(.with {
                    $0.spaceID = spaceID; $0.objectID = objectID; $0.contextID = objectID
                }).invoke(qos: .userInitiated)
            },
            capture: { request in
                await withCheckedContinuation { continuation in
                    DispatchQueue.global(qos: .userInitiated).async {
                        continuation.resume(returning: Lib.ServicePinkhaSemanticAnchorCapture(request) ?? Data())
                    }
                }
            },
            canPublish: { InvocationSettings.handler != nil },
            publish: { event in await PinkhaHeartSemanticAnchorNativePublication.send(event) }
        ))
    }
}

#endif
