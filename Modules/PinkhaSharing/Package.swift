// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "PinkhaSharing",
    defaultLocalization: "en",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "PinkhaSharing", targets: ["PinkhaSharing"])],
    targets: [
        .target(name: "PinkhaSharing", resources: [.process("Resources")]),
        .testTarget(name: "PinkhaSharingTests", dependencies: ["PinkhaSharing"])
    ]
)
