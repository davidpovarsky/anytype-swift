// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PinkhaKit",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "PinkhaKit",
            targets: ["PinkhaKit"]
        ),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "PinkhaKit",
            dependencies: [],
            path: "Sources/PinkhaKit",
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
        .testTarget(
            name: "PinkhaKitTests",
            dependencies: ["PinkhaKit"],
            path: "Tests/PinkhaKitTests",
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
    ]
)
