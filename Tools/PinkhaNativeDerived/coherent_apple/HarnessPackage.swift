// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CoherentHeartAuthorityHarness",
    platforms: [.iOS(.v17)],
    products: [.library(name: "CoherentHeartAuthorityHarness", targets: ["CoherentHeartAuthorityHarness"])],
    dependencies: [
        .package(path: "../Modules/PinkhaKit"),
        .package(path: "../Modules/PinkhaHeartEngine"),
        .package(url: "https://github.com/apple/swift-protobuf", revision: "1.32.0"),
        .package(url: "https://github.com/apple/swift-asn1.git", exact: "1.7.4")
    ],
    targets: [
        .target(name: "CoherentHeartAuthorityHarness"),
        .binaryTarget(name: "Lib", path: "../Dependencies/Middleware/Lib.xcframework"),
        .testTarget(name: "CoherentHeartAuthorityHarnessTests", dependencies: [
            "CoherentHeartAuthorityHarness", "Lib", "PinkhaKit", "PinkhaHeartEngine",
            .product(name: "SwiftProtobuf", package: "swift-protobuf")
        ], resources: [.copy("host-config.json")],
        linkerSettings: [.linkedLibrary("c++"), .linkedLibrary("resolv")])
    ]
)
