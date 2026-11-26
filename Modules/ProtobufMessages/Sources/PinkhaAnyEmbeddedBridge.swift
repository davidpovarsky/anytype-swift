#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import Lib

/// One source-qualified library owns both engines and the shared Go runtime.
/// Native account/Space authorization remains in each engine's existing API.
public enum PinkhaUnifiedRuntimeProfile {
    public static let sourceManifestSHA256 = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
    public static let heartVersion = "pinkha-dual-runtime-v1-" + sourceManifestSHA256
    public static let anyVersion = "v0.5.0-pinkha.dual.1-" + sourceManifestSHA256
    public static let anyCommit = "8fbd1e819fb132ac0e0a848d2ddf5c5714189b81"
    public static let anyBuildDate = "2026-11-26"
    public static let anyRuntimeVersion = "any " + anyVersion
        + " (commit " + anyCommit + ", built " + anyBuildDate + ")"
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
