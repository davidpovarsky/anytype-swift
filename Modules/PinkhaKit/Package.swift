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
    dependencies: [
        .package(
            url: "https://github.com/davidpovarsky/TorahInspectorKit.git",
            revision: "5aa16f616910d70e54e74b2a0e58e107e07a90e3"
        )
    ],
    targets: [
        .target(
            name: "PinkhaKit",
            dependencies: [
                .product(name: "TorahInspectorCore", package: "TorahInspectorKit")
            ],
            path: "Sources/PinkhaKit",
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
        .testTarget(
            name: "PinkhaKitTests",
            dependencies: [
                "PinkhaKit",
                .product(name: "TorahInspectorCore", package: "TorahInspectorKit")
            ],
            path: "Tests/PinkhaKitTests",
            resources: [
                .process("Torah/Fixtures")
            ],
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
    ]
)
