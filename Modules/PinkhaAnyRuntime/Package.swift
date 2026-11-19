// swift-tools-version: 6.0
import PackageDescription
import Foundation

let nativeMode = ProcessInfo.processInfo.environment["PINKHA_ANY_NATIVE_ARTIFACT"]
precondition(nativeMode == nil || nativeMode == "verified-v1", "Unknown native artifact selection")
let isNative = nativeMode == "verified-v1"
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
    targets: [
        binary,
        .target(
            name: "PinkhaAnyRuntime",
            dependencies: ["AnyLib"],
            swiftSettings: isNative ? [.define("PINKHA_NATIVE_RUNTIME")] : [],
            linkerSettings: [.linkedFramework("Security"), .linkedFramework("SystemConfiguration"), .linkedLibrary("resolv")]
        ),
        .testTarget(name: "PinkhaAnyRuntimeTests", dependencies: ["PinkhaAnyRuntime"])
    ]
)
