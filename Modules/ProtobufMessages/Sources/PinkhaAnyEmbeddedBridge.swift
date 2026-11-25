#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import Lib

/// One source-qualified library owns both engines and the shared Go runtime.
/// Native account/Space authorization remains in each engine's existing API.
public enum PinkhaUnifiedRuntimeProfile {
    public static let sourceManifestSHA256 =
        "70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683"
    public static let heartVersion = "pinkha-dual-runtime-v1-" + sourceManifestSHA256
    public static let anyVersion = "v0.5.0-pinkha.dual.1-" + sourceManifestSHA256
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
    public static func stop() { try? Lib.MobileStop() }
    public static func stopNow() { Lib.MobileStopNow() }
}
#endif
