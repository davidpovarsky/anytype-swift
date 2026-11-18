import Foundation

/// An index row can survive a downgrade. Only the separately enabled host build
/// and the exact running Heart identity may authorize the private T5 lookup.
public enum T5NativeRelatedLookupCapability {
    public static let patchSHA256 = "5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2"
    public static let runtimeVersion =
        "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + patchSHA256
        + "-pinkha-native-t5-lookup-v1-" + patchSHA256

    public static func resolve(
        enabledByBuild: Bool, runtimeVersion: String
    ) -> T5ExpandedRelatedTargets.Capability {
        guard enabledByBuild, runtimeVersion == self.runtimeVersion else { return .unavailable }
        return .verified
    }
}
