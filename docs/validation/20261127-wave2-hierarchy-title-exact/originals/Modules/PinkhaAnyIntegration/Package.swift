// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PinkhaAnyIntegration",
    platforms: [.iOS(.v18), .macOS(.v14)],
    products: [.library(name: "PinkhaAnyIntegration", targets: ["PinkhaAnyIntegration"]),
               .executable(name: "pinkha-any-integration-probe", targets: ["PinkhaAnyIntegrationProbe"])],
    dependencies: [
        .package(path: "../PinkhaAnyEngine"),
        .package(path: "../PinkhaKit")
    ],
    targets: [
        .target(name: "PinkhaAnyIntegration", dependencies: ["PinkhaAnyEngine", "PinkhaKit"]),
        .testTarget(name: "PinkhaAnyIntegrationTests", dependencies: ["PinkhaAnyIntegration"]),
        .executableTarget(name: "PinkhaAnyIntegrationProbe", dependencies: ["PinkhaAnyIntegration"])
    ]
)
