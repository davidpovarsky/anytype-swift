// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "PinkhaAnyNative",
    platforms: [.iOS("27.0")],
    products: [.library(name: "PinkhaAnyNative", targets: ["PinkhaAnyNative"])],
    dependencies: [
        .package(path: "../PinkhaAnyRuntime"),
        .package(path: "../PinkhaAnyUI"),
        .package(path: "../PinkhaAnyHost"),
        .package(path: "../PinkhaAnyEngine"),
        .package(path: "../PinkhaAnyIntegration")
    ],
    targets: [
        .target(name: "PinkhaAnyNative", dependencies: ["PinkhaAnyRuntime", "PinkhaAnyUI",
            "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration"]),
        .testTarget(name: "PinkhaAnyNativeTests", dependencies: ["PinkhaAnyNative", "PinkhaAnyRuntime", "PinkhaAnyEngine",
            "PinkhaAnyHost", "PinkhaAnyIntegration", "PinkhaAnyUI"])
    ]
)
