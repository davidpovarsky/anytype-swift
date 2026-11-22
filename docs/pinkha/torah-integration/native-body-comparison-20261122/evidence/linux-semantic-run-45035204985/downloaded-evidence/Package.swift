// swift-tools-version:6.0
import PackageDescription
let package = Package(
    name: "NativeBodySemanticControls",
    products: [.executable(name: "NativeBodySemanticControls", targets: ["NativeBodySemanticControls"])],
    dependencies: [
        .package(url: "https://github.com/apple/swift-protobuf", revision: "c6fe6442e6a64250495669325044052e113e990c"),
        .package(url: "https://github.com/weichsel/ZIPFoundation", revision: "22787ffb59de99e5dc1fbfe80b19c97a904ad48d")
    ],
    targets: [
        .target(name: "ProtobufMessages", dependencies: [.product(name: "SwiftProtobuf", package: "swift-protobuf")], path: "Sources/ProtobufMessages", swiftSettings: [.swiftLanguageMode(.v6)]),
        .executableTarget(name: "NativeBodySemanticControls", dependencies: ["ProtobufMessages", .product(name: "SwiftProtobuf", package: "swift-protobuf"), .product(name: "ZIPFoundation", package: "ZIPFoundation")], path: "Sources/NativeBodySemanticControls", swiftSettings: [.swiftLanguageMode(.v6)])
    ]
)
