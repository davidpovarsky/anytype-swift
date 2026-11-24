// swift-tools-version: 6.0
import PackageDescription
import Foundation

let nativeMode = ProcessInfo.processInfo.environment["PINKHA_ANY_NATIVE_ARTIFACT"]
precondition(nativeMode == nil || nativeMode == "verified-v1" || nativeMode == "verified-prepared-v1" ||
             nativeMode == "verified-prepared-inline-v1" || nativeMode == "verified-prepared-file-v1" || nativeMode == "verified-prepared-components-v1", "Unknown native artifact selection")
let isPreparedCandidate = nativeMode == "verified-prepared-v1"
let isPreparedInlineCandidate = nativeMode == "verified-prepared-inline-v1"
let isPreparedFileCandidate = nativeMode == "verified-prepared-file-v1"
let isPreparedComponentsCandidate = nativeMode == "verified-prepared-components-v1"
let isNative = nativeMode == "verified-v1" || isPreparedCandidate || isPreparedInlineCandidate || isPreparedFileCandidate || isPreparedComponentsCandidate
// This acceptance-only host is never added to the retained runtime test lane.
let readAcceptance = ProcessInfo.processInfo.environment["PINKHA_ANY_AUTHORIZED_READ_ACCEPTANCE"]
precondition(readAcceptance == nil || readAcceptance == "candidate-v10", "Unknown authorized read acceptance selection")
let isReadCandidate = readAcceptance == "candidate-v10"
precondition(!isReadCandidate || isNative, "Authorized read acceptance requires an explicitly installed candidate binary")
precondition(!isReadCandidate || !(isPreparedCandidate || isPreparedInlineCandidate || isPreparedFileCandidate || isPreparedComponentsCandidate), "Acceptance candidates require separate explicit selections")
let isHostAcceptance = isReadCandidate || isPreparedCandidate || isPreparedInlineCandidate || isPreparedFileCandidate || isPreparedComponentsCandidate
let binary: Target = isNative
    ? .binaryTarget(name: "AnyLib", path: "Vendor/any.xcframework")
    : .binaryTarget(
        name: "AnyLib",
        url: "https://github.com/anyproto/any/releases/download/v0.5.0/any.xcframework.zip",
        checksum: "68e0de076baba94770c3367cebca08459620445e21a6aec2c05b1a54800d1812"
    )

let package = Package(
    name: "PinkhaAnyRuntime",
    platforms: [.iOS("18.4")],
    products: [.library(name: "PinkhaAnyRuntime", targets: ["PinkhaAnyRuntime"])],
    dependencies: [.package(path: "../PinkhaAnyEngine")] + (isHostAcceptance ? [
        .package(path: "../PinkhaAnyIntegration"),
        .package(path: "../PinkhaAnyHost"),
        .package(path: "../PinkhaKit")
    ] : []),
    targets: [
        binary,
        .target(
            name: "PinkhaAnyRuntime",
            dependencies: ["AnyLib", "PinkhaAnyEngine"],
            swiftSettings: (isNative ? [.define("PINKHA_NATIVE_RUNTIME")] : []) +
                (isPreparedCandidate ? [.define("PINKHA_PREPARED_MIGRATION_RUNTIME")] : []) +
                (isPreparedInlineCandidate ? [.define("PINKHA_PREPARED_INLINE_MIGRATION_RUNTIME")] : []) +
                (isPreparedFileCandidate ? [.define("PINKHA_PREPARED_FILE_MIGRATION_RUNTIME")] : []) +
                (isPreparedComponentsCandidate ? [.define("PINKHA_PREPARED_COMPONENTS_RUNTIME")] : []),
            linkerSettings: [.linkedFramework("Security"), .linkedFramework("SystemConfiguration"), .linkedLibrary("resolv")]
        ),
        .testTarget(
            name: "PinkhaAnyRuntimeTests",
            dependencies: ["PinkhaAnyRuntime"] + (isHostAcceptance
                ? ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit"] : []),
            swiftSettings: (isReadCandidate ? [.define("PINKHA_AUTHORIZED_READ_CANDIDATE")] : []) +
                (isPreparedCandidate ? [.define("PINKHA_PREPARED_MIGRATION_ACCEPTANCE")] : []) +
                (isPreparedInlineCandidate ? [.define("PINKHA_PREPARED_INLINE_MIGRATION_ACCEPTANCE")] : []) +
                (isPreparedFileCandidate ? [.define("PINKHA_PREPARED_FILE_MIGRATION_ACCEPTANCE")] : []) +
                (isPreparedComponentsCandidate ? [.define("PINKHA_PREPARED_COMPONENTS_ACCEPTANCE")] : [])
        )
    ]
)
