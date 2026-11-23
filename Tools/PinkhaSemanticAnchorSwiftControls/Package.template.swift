// swift-tools-version: 6.0
import PackageDescription

// Isolated Linux controls for exact source files. This is not the production
// ProtobufMessages package or an Apple Lib.xcframework callability claim.
let package = Package(
    name: "PinkhaHeartSemanticAnchorControls",
    products: [.library(name: "ProtobufMessages", targets: ["ProtobufMessages"])],
    dependencies: [
        .package(url: "https://github.com/apple/swift-protobuf", revision: "c6fe6442e6a64250495669325044052e113e990c"),
        .package(url: "https://github.com/apple/swift-crypto.git", exact: "3.12.3"),
        .package(url: "https://github.com/apple/swift-asn1.git", exact: "1.7.4")
    ],
    targets: [
        .target(name: "ProtobufMessages", dependencies: [
            .product(name: "SwiftProtobuf", package: "swift-protobuf"),
            .product(name: "Crypto", package: "swift-crypto")
        ], swiftSettings: [.swiftLanguageMode(.v6), .define("PINKHA_NATIVE_T2_AUTHORIZED_READ_V1")]),
        .testTarget(name: "ProtobufMessagesTests", dependencies: [
            "ProtobufMessages", .product(name: "SwiftProtobuf", package: "swift-protobuf")
        ], resources: [.copy("Fixtures/NativePage")],
        swiftSettings: [.swiftLanguageMode(.v6), .define("PINKHA_NATIVE_T2_AUTHORIZED_READ_V1")])
    ]
)
