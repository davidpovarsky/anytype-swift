// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "T5AuthorizationComponentProof", targets: [
    .target(name: "TorahInspectorCore"),
    .target(name: "PinkhaKit", dependencies: ["TorahInspectorCore"]),
    .testTarget(name: "PinkhaKitTests", dependencies: ["PinkhaKit", "TorahInspectorCore"]),
    .testTarget(name: "TorahInspectorCoreTests", dependencies: ["TorahInspectorCore"])
])
