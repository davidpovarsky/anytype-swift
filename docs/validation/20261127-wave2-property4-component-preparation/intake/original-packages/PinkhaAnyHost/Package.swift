// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PinkhaAnyHost",
    platforms: [.iOS(.v18), .macOS(.v14)],
    products: [.library(name: "PinkhaAnyHost", targets: ["PinkhaAnyHost"]),
               .executable(name: "pinkha-any-host-probe", targets: ["PinkhaAnyHostProbe"])],
    dependencies: [
        .package(path: "../PinkhaAnyEngine"),
        .package(path: "../PinkhaAnyIntegration"),
        .package(path: "../PinkhaKit"),
        .package(url: "https://github.com/apple/swift-crypto.git", exact: "3.12.3")
    ],
    targets: [
        .target(name: "PinkhaAnyHost", dependencies: [
            "PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaKit",
            .product(name: "Crypto", package: "swift-crypto")
        ]),
        .testTarget(name: "PinkhaAnyHostTests", dependencies: ["PinkhaAnyHost"]),
        .executableTarget(name: "PinkhaAnyHostProbe", dependencies: ["PinkhaAnyHost"])
    ]
)
