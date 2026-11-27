// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PinkhaAnyEngine",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "PinkhaAnyEngine", targets: ["PinkhaAnyEngine"]),
        .executable(name: "PinkhaAnyEngineProbe", targets: ["PinkhaAnyEngineProbe"])
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-crypto.git", exact: "3.12.3")
    ],
    targets: [
        .target(name: "PinkhaAnyEngine", dependencies: [
            .product(name: "Crypto", package: "swift-crypto")
        ]),
        .executableTarget(name: "PinkhaAnyEngineProbe", dependencies: ["PinkhaAnyEngine"]),
        .testTarget(name: "PinkhaAnyEngineTests", dependencies: ["PinkhaAnyEngine"])
    ]
)
