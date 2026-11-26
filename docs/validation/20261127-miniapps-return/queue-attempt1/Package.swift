// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "PinkhaMiniAppsReturnChecks",
    targets: [
        .target(name: "PinkhaHanlinCore"),
        .testTarget(name: "PinkhaAnyHanlinTests", dependencies: ["PinkhaHanlinCore"])
    ],
    swiftLanguageModes: [.v6])
