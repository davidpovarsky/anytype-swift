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
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinAgentSDK"),
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinPlatform"),
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinPresentationSDK"),
        .package(path: "../PinkhaAnyHost"),
        .package(url: "https://github.com/apple/swift-crypto.git", exact: "3.12.3"),
        .package(url: "https://github.com/swiftlang/swift-markdown.git",
                 revision: "25cb61d3482054b09ae76ca4f281b1bfe7fe5a43")
    ],
    targets: [
        .target(name: "PinkhaHanlinCore", dependencies: [
            .product(name: "HanlinHostContracts", package: "HanlinAgentSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinPlatform"),
            .product(name: "Crypto", package: "swift-crypto")
        ]),
        .target(name: "PinkhaAnyHanlin", dependencies: [
            "PinkhaHanlinCore", "PinkhaAnyHost",
            .product(name: "HanlinHostContracts", package: "HanlinAgentSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinPlatform"),
            .product(name: "Markdown", package: "swift-markdown")
        ]),
        .target(name: "PinkhaHanlinUI", dependencies: [
            "PinkhaHanlinCore", "PinkhaAnyHanlin", "PinkhaAnyHost",
            .product(name: "HanlinHostContracts", package: "HanlinAgentSDK"),
            .product(name: "HanlinAgentCore", package: "HanlinAgentSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinPersistenceAdapters", package: "HanlinAgentSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinChatCore", package: "HanlinPlatform", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinScriptUI", package: "HanlinPlatform", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinChatUI", package: "HanlinPresentationSDK", condition: .when(platforms: [.iOS])),
            .product(name: "HanlinPresentationKit", package: "HanlinPresentationSDK", condition: .when(platforms: [.iOS]))
        ], resources: [.process("Resources")]),
        .executableTarget(name: "PinkhaAnyHanlinProbe", dependencies: [
            "PinkhaAnyHanlin", "PinkhaHanlinCore", "PinkhaAnyHost",
            .product(name: "HanlinHostContracts", package: "HanlinAgentSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinPlatform")
        ]),
        .testTarget(name: "PinkhaAnyHanlinTests", dependencies: [
            "PinkhaAnyHanlin", "PinkhaHanlinCore",
            .product(name: "HanlinHostContracts", package: "HanlinAgentSDK"),
            .product(name: "HanlinPlatformContracts", package: "HanlinPlatform")
        ])
    ],
    swiftLanguageModes: [.v6]
)
