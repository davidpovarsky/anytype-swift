import Foundation

/// An index row can survive a downgrade. Only the separately enabled host build
/// and the exact running Heart identity may authorize the private T5 lookup.
public enum T5NativeRelatedLookupCapability {
    public static let patchSHA256 = "5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2"
    public static let runtimeVersion =
        "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + patchSHA256
        + "-pinkha-native-t5-lookup-v1-" + patchSHA256

    /// Reviewed full-r15 runtime with the canonical attachment regression fixed.
    /// Recognition alone never enables lookup in a build without its explicit flag.
    public static let correctedPatchSHA256 = "595f8142f00035da2fff4925c8fe125fa7cf36de9ae124b528a9d2130b2a9bf6"
    public static let correctedRuntimeVersion =
        "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + correctedPatchSHA256
        + "-pinkha-native-t5-lookup-v1-" + correctedPatchSHA256
        + "-pinkha-torah-attachment-v1-" + correctedPatchSHA256

    /// Exact combined authorized-read/current-read candidate. Lookup still requires
    /// the explicit host build flag; this identity does not enable shipping builds.
    public static let coherentPatchSHA256 = "2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00"
    public static let coherentRuntimeVersion =
        "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + coherentPatchSHA256
        + "-pinkha-native-t5-lookup-v1-" + coherentPatchSHA256
        + "-pinkha-torah-attachment-v1-" + coherentPatchSHA256
        + "-pinkha-current-read-v1-" + coherentPatchSHA256
        + "-pinkha-authorized-read-v1-" + coherentPatchSHA256

    /// Reviewed shipping source closure; execution is still gated by the host build.
    public static let unifiedRuntimeVersion =
        "pinkha-dual-runtime-v1-70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72"

    public static func resolve(
        enabledByBuild: Bool, runtimeVersion: String
    ) -> T5ExpandedRelatedTargets.Capability {
        guard enabledByBuild,
              runtimeVersion == self.runtimeVersion || runtimeVersion == correctedRuntimeVersion
                || runtimeVersion == coherentRuntimeVersion || runtimeVersion == unifiedRuntimeVersion
        else { return .unavailable }
        return .verified
    }
}
