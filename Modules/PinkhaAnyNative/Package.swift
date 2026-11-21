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
        .package(path: "../PinkhaAnyIntegration"),
        .package(path: "../PinkhaKit"),
        .package(path: "../PinkhaTorahPresentation"),
        .package(url: "https://github.com/davidpovarsky/TorahInspectorKit.git",
                 revision: "158acb295f832e96907cdadc813a1c2a4bb6a03c"),
        .package(path: "../PinkhaAnyHanlin"),
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinAgentSDK"),
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinPlatform")
    ],
    targets: [
        .target(name: "PinkhaAnyNative", dependencies: ["PinkhaAnyRuntime", "PinkhaAnyUI",
            "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",
            .product(name: "PinkhaHanlinCore", package: "PinkhaAnyHanlin")]),
        .testTarget(name: "PinkhaAnyNativeTests", dependencies: ["PinkhaAnyNative", "PinkhaAnyRuntime", "PinkhaAnyEngine",
            "PinkhaAnyHost", "PinkhaAnyIntegration", "PinkhaAnyUI",
            "PinkhaKit", "PinkhaTorahPresentation",
            .product(name: "TorahInspectorCore", package: "TorahInspectorKit"),
            .product(name: "PinkhaAnyHanlin", package: "PinkhaAnyHanlin"),
            .product(name: "PinkhaHanlinCore", package: "PinkhaAnyHanlin"),
            .product(name: "HanlinHostContracts", package: "HanlinAgentSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinPlatform")])
    ]
)
