import Foundation
import Testing
@testable import PinkhaKit

@Suite("T5 running Heart capability boundary")
struct T5NativeRelatedLookupCapabilityTests {
    @Test func exactRuntimeCannotEnableAnUnapprovedHostBuild() {
        let capability = T5NativeRelatedLookupCapability.resolve(
            enabledByBuild: false, runtimeVersion: T5NativeRelatedLookupCapability.runtimeVersion
        )
        guard case .unavailable = capability else {
            Issue.record("A runtime marker enabled a host whose feature flag is disabled")
            return
        }
    }

    @Test func separatelyEnabledHostAcceptsTheExactReviewedRuntime() {
        let capability = T5NativeRelatedLookupCapability.resolve(
            enabledByBuild: true, runtimeVersion: T5NativeRelatedLookupCapability.runtimeVersion
        )
        guard case .verified = capability else {
            Issue.record("The exact separately enabled runtime was rejected")
            return
        }
    }

    @Test(arguments: [
        "",
        "v0.51.7-nightly.20261014.1",
        "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077",
        "pinkha-native-t5-lookup-v1-" + T5NativeRelatedLookupCapability.patchSHA256,
        "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + T5NativeRelatedLookupCapability.patchSHA256,
        T5NativeRelatedLookupCapability.runtimeVersion + "-different-build",
        "unverified-" + T5NativeRelatedLookupCapability.runtimeVersion,
        T5NativeRelatedLookupCapability.runtimeVersion.replacingOccurrences(of: "5a090615", with: "00000000"),
        T5NativeRelatedLookupCapability.runtimeVersion + "\n"
    ])
    func olderPartialForeignAndExtendedRuntimeIdentitiesCannotGrantCapability(version: String) {
        let capability = T5NativeRelatedLookupCapability.resolve(enabledByBuild: true, runtimeVersion: version)
        guard case .unavailable = capability else {
            Issue.record("An unverified runtime identity granted private lookup capability")
            return
        }
    }
}
