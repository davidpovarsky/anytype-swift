// swift-tools-version: 6.0
import PackageDescription
import Foundation

let nativeMode = ProcessInfo.processInfo.environment["PINKHA_ANY_NATIVE_ARTIFACT"]
precondition(nativeMode == nil || nativeMode == "verified-v1" || nativeMode == "verified-prepared-v1" ||
             nativeMode == "verified-prepared-inline-v1" || nativeMode == "verified-prepared-file-v1" || nativeMode == "verified-prepared-components-v1" || nativeMode == "verified-prepared-components-v2" || nativeMode == "verified-unified-v1", "Unknown native artifact selection")
let isUnified = nativeMode == "verified-unified-v1"
let isPreparedCandidate = nativeMode == "verified-prepared-v1"
let isPreparedInlineCandidate = nativeMode == "verified-prepared-inline-v1"
let isPreparedFileCandidate = nativeMode == "verified-prepared-file-v1"
let isPreparedComponentsCandidate = nativeMode == "verified-prepared-components-v1"
let isPreparedComponentsV2Candidate = nativeMode == "verified-prepared-components-v2"
let isNative = isUnified || nativeMode == "verified-v1" || isPreparedCandidate || isPreparedInlineCandidate || isPreparedFileCandidate || isPreparedComponentsCandidate || isPreparedComponentsV2Candidate
// This acceptance-only host is never added to the retained runtime test lane.
let readAcceptance = ProcessInfo.processInfo.environment["PINKHA_ANY_AUTHORIZED_READ_ACCEPTANCE"]
precondition(readAcceptance == nil || readAcceptance == "candidate-v10", "Unknown authorized read acceptance selection")
let isReadCandidate = readAcceptance == "candidate-v10"
precondition(!isReadCandidate || isNative, "Authorized read acceptance requires an explicitly installed candidate binary")
precondition(!isReadCandidate || !(isUnified || isPreparedCandidate || isPreparedInlineCandidate || isPreparedFileCandidate || isPreparedComponentsCandidate || isPreparedComponentsV2Candidate), "Acceptance candidates require separate explicit selections")
let isHostAcceptance = isReadCandidate || isPreparedCandidate || isPreparedInlineCandidate || isPreparedFileCandidate || isPreparedComponentsCandidate || isPreparedComponentsV2Candidate
let binaries: [Target] = isUnified ? [] : [isNative
    ? .binaryTarget(name: "AnyLib", path: "Vendor/any.xcframework")
    : .binaryTarget(
        name: "AnyLib",
        url: "https://github.com/anyproto/any/releases/download/v0.5.0/any.xcframework.zip",
        checksum: "68e0de076baba94770c3367cebca08459620445e21a6aec2c05b1a54800d1812"
    )]
let runtimeDependencies: [Target.Dependency] = ["PinkhaAnyEngine"] + (isUnified
    ? [.product(name: "ProtobufMessages", package: "ProtobufMessages")]
    : ["AnyLib"])

// Bound intermediate types keep the acceptance selector matrix below the
// Swift manifest compiler's expression-inference complexity limit.
var packageDependencies: [Package.Dependency] = [.package(path: "../PinkhaAnyEngine")]
if isUnified { packageDependencies.append(.package(path: "../ProtobufMessages")) }
if isHostAcceptance {
    packageDependencies += [.package(path: "../PinkhaAnyIntegration"),
                            .package(path: "../PinkhaAnyHost"), .package(path: "../PinkhaKit")]
}
var runtimeSettings: [SwiftSetting] = []
if isUnified { runtimeSettings.append(.define("PINKHA_DUAL_ENGINE_RUNTIME")) }
if isNative { runtimeSettings.append(.define("PINKHA_NATIVE_RUNTIME")) }
if isPreparedCandidate { runtimeSettings.append(.define("PINKHA_PREPARED_MIGRATION_RUNTIME")) }
if isPreparedInlineCandidate { runtimeSettings.append(.define("PINKHA_PREPARED_INLINE_MIGRATION_RUNTIME")) }
if isPreparedFileCandidate { runtimeSettings.append(.define("PINKHA_PREPARED_FILE_MIGRATION_RUNTIME")) }
if isPreparedComponentsCandidate { runtimeSettings.append(.define("PINKHA_PREPARED_COMPONENTS_RUNTIME")) }
if isPreparedComponentsV2Candidate { runtimeSettings.append(.define("PINKHA_PREPARED_COMPONENTS_V2_RUNTIME")) }
var acceptanceSettings: [SwiftSetting] = []
if isReadCandidate { acceptanceSettings.append(.define("PINKHA_AUTHORIZED_READ_CANDIDATE")) }
if isPreparedCandidate { acceptanceSettings.append(.define("PINKHA_PREPARED_MIGRATION_ACCEPTANCE")) }
if isPreparedInlineCandidate { acceptanceSettings.append(.define("PINKHA_PREPARED_INLINE_MIGRATION_ACCEPTANCE")) }
if isPreparedFileCandidate { acceptanceSettings.append(.define("PINKHA_PREPARED_FILE_MIGRATION_ACCEPTANCE")) }
if isPreparedComponentsCandidate { acceptanceSettings.append(.define("PINKHA_PREPARED_COMPONENTS_ACCEPTANCE")) }
if isPreparedComponentsV2Candidate { acceptanceSettings.append(.define("PINKHA_PREPARED_COMPONENTS_V2_ACCEPTANCE")) }
var testDependencies: [Target.Dependency] = ["PinkhaAnyRuntime"]
if isHostAcceptance {
    testDependencies += ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit"]
}

let package = Package(
    name: "PinkhaAnyRuntime",
    platforms: [.iOS("18.4")],
    products: [.library(name: "PinkhaAnyRuntime", targets: ["PinkhaAnyRuntime"])],
    dependencies: packageDependencies,
    targets: binaries + [
        .target(
            name: "PinkhaAnyRuntime",
            dependencies: runtimeDependencies,
            swiftSettings: runtimeSettings,
            linkerSettings: [.linkedFramework("Security"), .linkedFramework("SystemConfiguration"), .linkedLibrary("resolv")]
        ),
        .testTarget(
            name: "PinkhaAnyRuntimeTests",
            dependencies: testDependencies,
            swiftSettings: acceptanceSettings
        )
    ]
)
