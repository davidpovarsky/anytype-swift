// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PinkhaAnyRuntime",
    platforms: [.iOS("18.4")],
    products: [.library(name: "PinkhaAnyRuntime", targets: ["PinkhaAnyRuntime"])],
    targets: [
        .binaryTarget(
            name: "AnyLib",
            url: "https://github.com/anyproto/any/releases/download/v0.5.0/any.xcframework.zip",
            checksum: "68e0de076baba94770c3367cebca08459620445e21a6aec2c05b1a54800d1812"
        ),
        .target(
            name: "PinkhaAnyRuntime",
            dependencies: ["AnyLib"],
            linkerSettings: [.linkedFramework("Security"), .linkedFramework("SystemConfiguration"), .linkedLibrary("resolv")]
        ),
        .testTarget(name: "PinkhaAnyRuntimeTests", dependencies: ["PinkhaAnyRuntime"])
    ]
)
