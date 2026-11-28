// swift-tools-version: 6.2
import Foundation
import PackageDescription

// This facade is inert in the preserved Heart-only acceptance build. Shipping
// composition must supply the verified one-runtime artifact explicitly.
let unified = ProcessInfo.processInfo.environment["PINKHA_ANY_NATIVE_ARTIFACT"] == "verified-unified-v1"
let package = Package(
    name: "PinkhaEngineHost",
    platforms: [.iOS("27.0")],
    products: [.library(name: "PinkhaEngineHost", targets: ["PinkhaEngineHost"])],
    dependencies: unified ? [.package(path: "../PinkhaAnyNative"), .package(path: "../PinkhaAnyUI"),
                             .package(path: "../PinkhaAnyHost"), .package(path: "../PinkhaAnyEngine")] : [],
    targets: [
        .target(name: "PinkhaEngineHost",
            dependencies: unified ? [.product(name: "PinkhaAnyNative", package: "PinkhaAnyNative"),
                                     .product(name: "PinkhaAnyUI", package: "PinkhaAnyUI"),
                                     .product(name: "PinkhaAnyHost", package: "PinkhaAnyHost"),
                                     .product(name: "PinkhaAnyEngine", package: "PinkhaAnyEngine")] : [],
            swiftSettings: unified ? [.define("PINKHA_DUAL_ENGINE_RUNTIME")] : [])
    ]
)
