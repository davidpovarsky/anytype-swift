#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import Lib

/// One source-qualified library owns both engines and the shared Go runtime.
/// Native account/Space authorization remains in each engine's existing API.
public enum PinkhaUnifiedRuntimeProfile {
    public static let sourceManifestSHA256 =
        "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"
    public static let heartVersion = "pinkha-dual-runtime-v1-" + sourceManifestSHA256
    public static let anyVersion = "v0.5.0-pinkha.dual.1-" + sourceManifestSHA256
    public static let anyRuntimeVersion = "any " + anyVersion
        + " (commit cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3, built 2026-11-25)"
}

public enum PinkhaAnyEmbeddedBridge {
    public struct StartResult: Sendable {
        public let code: Int32
        public let address: String
        public let message: String
    }

    public static func version() -> String { Lib.MobileVersion() }

    public static func start(dataDirectory: String, listenAddress: String, nodeConfiguration: String,
                             pushPeerID: String, pushAddresses: String, mode: String,
                             controlToken: String) -> StartResult? {
        guard let result = Lib.MobileStartWithResult(dataDirectory, listenAddress, nodeConfiguration,
            pushPeerID, pushAddresses, mode, controlToken) else { return nil }
        return StartResult(code: result.code, address: result.address, message: result.message)
    }

    /// The original mobile bridge calls embedded.Stop(true), waits for the drain,
    /// and returns nil. This has the same contract as the prior void C shim.
    public static func stop() { _ = Lib.MobileStop(nil) }
    public static func stopNow() { Lib.MobileStopNow() }
}
#endif
