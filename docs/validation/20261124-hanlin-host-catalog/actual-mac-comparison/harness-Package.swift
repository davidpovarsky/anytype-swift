// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "HanlinCatalogFocusedControls",
    platforms: [.macOS(.v26)],
    dependencies: [
        .package(path: "../source/Packages/HanlinPlatform"),
        .package(url: "https://github.com/davidpovarsky/swift-ai-sdk.git", revision: "e7bf34111e603ca977becd007dd4e5bb109af857")
    ],
    targets: [
        .testTarget(name: "HanlinChatCoreTests", dependencies: [
            .product(name: "HanlinChatCore", package: "HanlinPlatform"),
            .product(name: "AISDKProviderUtils", package: "swift-ai-sdk")
        ])
    ],
    swiftLanguageModes: [.v6]
)
