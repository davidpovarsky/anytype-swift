// swift-tools-version: 6.0
import Foundation
import PackageDescription

let candidate = ProcessInfo.processInfo.environment["PINKHA_NATIVE_T2_AUTHORIZED_READ_V1"] == "1"
let package = Package(
    name: "PinkhaHeartNative",
    platforms: [.iOS(.v17)],
    products: [.library(name: "PinkhaHeartNative", targets: ["PinkhaHeartNative"])],
    dependencies: [.package(path: "../PinkhaHeartEngine"), .package(path: "../PinkhaKit"),
                   .package(path: "../ProtobufMessages")],
    targets: [
        .target(name: "PinkhaHeartNative", dependencies: ["PinkhaHeartEngine", "PinkhaKit", "ProtobufMessages"],
                swiftSettings: candidate ? [.define("PINKHA_NATIVE_T2_AUTHORIZED_READ_V1")] : [])
    ]
)
