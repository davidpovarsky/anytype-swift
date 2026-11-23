// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "PinkhaAnyHanlin",
    defaultLocalization: "en",
    platforms: [.iOS("27.0"), .macOS(.v26)],
    products: [
        .library(name: "PinkhaHanlinCore", targets: ["PinkhaHanlinCore"]),
        .library(name: "PinkhaAnyHanlin", targets: ["PinkhaAnyHanlin"]),
        .library(name: "PinkhaHanlinUI", targets: ["PinkhaHanlinUI"]),
        .executable(name: "PinkhaAnyHanlinProbe", targets: ["PinkhaAnyHanlinProbe"])
    ],
    dependencies: [
        .package(name: "HanlinSDK", path: "../../Dependencies/Hanlin"),
        .package(path: "../PinkhaAnyHost"),
        .package(path: "../PinkhaAnyEngine"),
        .package(path: "../PinkhaAnyIntegration"),
        .package(url: "https://github.com/apple/swift-crypto.git", exact: "3.12.3"),
        .package(url: "https://github.com/swiftlang/swift-markdown.git",
                 revision: "25cb61d3482054b09ae76ca4f281b1bfe7fe5a43")
    ],
    targets: [
        .target(name: "PinkhaHanlinCore", dependencies: [
            .product(name: "HanlinHostContracts", package: "HanlinSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinSDK"),
            .product(name: "Crypto", package: "swift-crypto")
        ]),
        .target(name: "PinkhaAnyHanlin", dependencies: [
            "PinkhaHanlinCore", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",
            .product(name: "HanlinHostContracts", package: "HanlinSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinSDK"),
            .product(name: "Markdown", package: "swift-markdown")
        ]),
        .target(name: "PinkhaHanlinUI", dependencies: [
            "PinkhaHanlinCore", "PinkhaAnyHanlin", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",
            .product(name: "HanlinHostContracts", package: "HanlinSDK"),
            .product(name: "HanlinAgentCore", package: "HanlinSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinPersistenceAdapters", package: "HanlinSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinChatCore", package: "HanlinSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinScriptUI", package: "HanlinSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinChatUI", package: "HanlinSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinPresentationKit", package: "HanlinSDK", condition: .when(platforms: [.iOS]))
        ], resources: [.process("Resources")]),
        .executableTarget(name: "PinkhaAnyHanlinProbe", dependencies: [
            "PinkhaAnyHanlin", "PinkhaHanlinCore", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",
            .product(name: "HanlinHostContracts", package: "HanlinSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinSDK")
        ]),
        .testTarget(name: "PinkhaAnyHanlinTests", dependencies: [
            "PinkhaAnyHanlin", "PinkhaHanlinCore", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",
            .product(name: "HanlinHostContracts", package: "HanlinSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinSDK")
        ])
    ],
    swiftLanguageModes: [.v6]
)
