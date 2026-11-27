// swift-tools-version: 6.2
import PackageDescription
import Foundation

let unifiedRuntime = ProcessInfo.processInfo.environment["PINKHA_ANY_NATIVE_ARTIFACT"] == "verified-unified-v1"

let package = Package(
    name: "PinkhaAnyNative",
    platforms: [.iOS("27.0")],
    products: [.library(name: "PinkhaAnyNative", targets: ["PinkhaAnyNative"])],
    dependencies: [
        .package(path: "../PinkhaSharing"),
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinMiniAppsBridge"),
        .package(path: "../PinkhaAnyRuntime"),
        .package(path: "../PinkhaAnyUI"),
        .package(path: "../PinkhaAnyHost"),
        .package(path: "../PinkhaAnyEngine"),
        .package(path: "../PinkhaAnyIntegration"),
        .package(path: "../PinkhaKit"),
        .package(path: "../PinkhaTorahPresentation"),
        .package(url: "https://github.com/davidpovarsky/TorahInspectorKit.git",
                 revision: "26beca175d64a4d34e3567f2bbb4bf308d714478"),
        .package(path: "../PinkhaAnyHanlin"),
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinAgentSDK"),
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinPlatform")
    ],
    targets: [
        .target(name: "PinkhaAnyNative", dependencies: ["PinkhaSharing", "PinkhaAnyRuntime", "PinkhaAnyUI",
            "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",
            .product(name: "PinkhaHanlinCore", package: "PinkhaAnyHanlin")]),
        .testTarget(name: "PinkhaAnyNativeTests", dependencies: ["PinkhaAnyNative", "PinkhaAnyRuntime", "PinkhaAnyEngine",
            "PinkhaAnyHost", "PinkhaAnyIntegration", "PinkhaAnyUI",
            "PinkhaKit", "PinkhaTorahPresentation",
            .product(name: "TorahInspectorCore", package: "TorahInspectorKit"),
            .product(name: "PinkhaAnyHanlin", package: "PinkhaAnyHanlin"),
            .product(name: "PinkhaHanlinCore", package: "PinkhaAnyHanlin"),
            .product(name: "PinkhaHanlinUI", package: "PinkhaAnyHanlin"),
            .product(name: "HanlinMiniAppsBridge", package: "HanlinMiniAppsBridge"),
            .product(name: "HanlinHostContracts", package: "HanlinAgentSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinPlatform")],
            swiftSettings: unifiedRuntime ? [.define("PINKHA_DUAL_ENGINE_RUNTIME")] : [])
    ]
)
