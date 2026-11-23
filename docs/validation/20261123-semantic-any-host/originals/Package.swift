// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "PinkhaSemanticNativeHostControls", dependencies: [
    .package(path: "Modules/PinkhaKit"), .package(path: "Modules/PinkhaAnyEngine"),
    .package(path: "Modules/PinkhaAnyIntegration"), .package(path: "Modules/PinkhaAnyHost")
], targets: [.testTarget(name: "PinkhaSemanticHostControls", dependencies: [
    .product(name: "PinkhaKit", package: "PinkhaKit"),
    .product(name: "PinkhaAnyEngine", package: "PinkhaAnyEngine"),
    .product(name: "PinkhaAnyIntegration", package: "PinkhaAnyIntegration"),
    .product(name: "PinkhaAnyHost", package: "PinkhaAnyHost")
])])
