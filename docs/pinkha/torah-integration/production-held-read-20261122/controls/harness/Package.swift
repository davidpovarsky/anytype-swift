// swift-tools-version:6.0
import PackageDescription
import Foundation

guard let protobuf = ProcessInfo.processInfo.environment["OTZARIA_HELD_READ_SWIFTPROTOBUF_CHECKOUT"],
      !protobuf.isEmpty else {
    fatalError("Use the independently verified immutable SwiftProtobuf checkout.")
}
let package = Package(
    name: "OriginalHeldReadControls",
    dependencies: [.package(name: "SwiftProtobuf", path: protobuf)],
    targets: [
        .target(name: "Combine", path: "combine"),
        .target(
            name: "AnytypeCore",
            dependencies: ["Combine", .product(name: "SwiftProtobuf", package: "SwiftProtobuf")],
            path: "core"
        ),
        .target(
            name: "ProtobufMessages",
            dependencies: [.product(name: "SwiftProtobuf", package: "SwiftProtobuf")],
            path: "proto"
        ),
        .target(
            name: "Services",
            dependencies: ["AnytypeCore", "ProtobufMessages", .product(name: "SwiftProtobuf", package: "SwiftProtobuf")],
            path: "services"
        ),
        .target(name: "PinkhaKit", path: "pinkha"),
        .target(
            name: "OriginalHeldRead",
            dependencies: ["AnytypeCore", "Combine", "ProtobufMessages", "Services", "PinkhaKit",
                           .product(name: "SwiftProtobuf", package: "SwiftProtobuf")],
            path: "app",
            swiftSettings: [.swiftLanguageMode(.v5), .unsafeFlags(["-strict-concurrency=complete"])]
        ),
        .testTarget(
            name: "OriginalHeldReadTests",
            dependencies: ["OriginalHeldRead", "ProtobufMessages", "Services", "PinkhaKit",
                           .product(name: "SwiftProtobuf", package: "SwiftProtobuf")],
            path: "tests"
        )
    ],
    swiftLanguageModes: [.v6]
)
