// swift-tools-version:6.0
import PackageDescription
import Foundation

guard let protobuf = ProcessInfo.processInfo.environment["OTZARIA_METADATA_SWIFTPROTOBUF_CHECKOUT"],
      !protobuf.isEmpty else {
    fatalError("Use the independently verified immutable SwiftProtobuf checkout.")
}
let package = Package(
    name: "OriginalMetadataControls",
    dependencies: [.package(name: "SwiftProtobuf", path: protobuf)],
    targets: [
        .target(
            name: "ProtobufMessages",
            dependencies: [.product(name: "SwiftProtobuf", package: "SwiftProtobuf")],
            path: "proto"
        ),
        .target(name: "PinkhaKit", path: "pinkha"),
        .testTarget(
            name: "OriginalAnnotationNativeMetadataTests",
            dependencies: [
                "ProtobufMessages", "PinkhaKit",
                .product(name: "SwiftProtobuf", package: "SwiftProtobuf")
            ],
            path: "tests"
        )
    ],
    swiftLanguageModes: [.v6]
)
