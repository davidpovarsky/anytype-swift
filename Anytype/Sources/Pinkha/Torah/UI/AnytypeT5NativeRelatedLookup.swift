import Foundation
import PinkhaKit
import Services
import ProtobufMessages

enum AnytypeT5NativeRelatedLookup {
    @MainActor
    static func current() async throws -> T5ExpandedRelatedTargets.Capability {
        try Task.checkCancellation()
        // The flag remains absent until the real runtime/reopen/compatibility
        // gates pass. Persisted private row versions cannot activate this path.
        #if PINKHA_NATIVE_T5_LOOKUP_V1
        let response = try await ClientCommands.appGetVersion().invoke(qos: .userInitiated)
        try Task.checkCancellation()
        return T5NativeRelatedLookupCapability.resolve(
            enabledByBuild: true, runtimeVersion: response.version
        )
        #else
        return .unavailable
        #endif
    }
}
