// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "HeartAuthorizedReadHarness",
    platforms: [.iOS(.v17)],
    products: [.library(name: "HeartAuthorizedReadHarness", targets: ["HeartAuthorizedReadHarness"])],
    dependencies: [
        .package(path: "../Modules/PinkhaKit"),
        .package(path: "../Modules/PinkhaHeartEngine"),
        .package(path: "../Modules/PinkhaHeartNative"),
        .package(path: "../Modules/ProtobufMessages"),
        .package(url: "https://github.com/apple/swift-protobuf", revision: "1.32.0"),
        .package(url: "https://github.com/apple/swift-asn1.git", exact: "1.7.4")
    ],
    targets: [
        .target(name: "HeartAuthorizedReadHarness"),
        .testTarget(name: "HeartAuthorizedReadHarnessTests", dependencies: [
            "HeartAuthorizedReadHarness", "PinkhaKit", "PinkhaHeartEngine", "PinkhaHeartNative", "ProtobufMessages",
            .product(name: "SwiftProtobuf", package: "swift-protobuf")
        ], resources: [.copy("Fixtures"), .copy("host-config.json")],
        swiftSettings: [.define("PINKHA_NATIVE_T2_AUTHORIZED_READ_V1")])
    ]
)
