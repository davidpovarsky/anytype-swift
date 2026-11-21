// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PinkhaHeartEngine",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "PinkhaHeartEngine", targets: ["PinkhaHeartEngine"])],
    dependencies: [
        .package(path: "../PinkhaKit"),
        .package(url: "https://github.com/apple/swift-protobuf", exact: "1.32.0"),
        .package(url: "https://github.com/apple/swift-crypto.git", exact: "3.12.3")
    ],
    targets: [
        .target(name: "PinkhaHeartEngine", dependencies: [
            "PinkhaKit",
            .product(name: "SwiftProtobuf", package: "swift-protobuf"),
            .product(name: "Crypto", package: "swift-crypto")
        ]),
        .testTarget(name: "PinkhaHeartEngineTests", dependencies: ["PinkhaHeartEngine"])
    ]
)
