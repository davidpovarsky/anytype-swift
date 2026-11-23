// swift-tools-version:6.0
import Foundation
import PackageDescription

let authorizedReadCandidate = ProcessInfo.processInfo.environment["PINKHA_NATIVE_T2_AUTHORIZED_READ_V1"] == "1"
// The enabled source directly references the new generated Lib symbol and
// verifies this exact native runtime before a capture can be dispatched.
let semanticAnchorPage154 = authorizedReadCandidate
    && ProcessInfo.processInfo.environment["PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1"]
        == "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
let authorizedReadFixture = authorizedReadCandidate
    && ProcessInfo.processInfo.environment["PINKHA_NATIVE_T2_AUTHORIZED_READ_FIXTURE"] == "1"

let package = Package(
    name: "ProtobufMessages",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v17),
    ],
    products: [
        .library(
            name: "ProtobufMessages",
            type: .dynamic,
            targets: ["ProtobufMessages"]),
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-protobuf", revision: "1.32.0")
    ],
    targets: [
        .target(
            name: "ProtobufMessages",
            dependencies: [
                .product(name: "SwiftProtobuf", package: "swift-protobuf"),
                "Lib"
            ],
            path: "Sources",
            resources: [.process("Loc/Resources")],
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ] + (authorizedReadCandidate ? [.define("PINKHA_NATIVE_T2_AUTHORIZED_READ_V1")] : [])
              + (authorizedReadFixture ? [.define("PINKHA_NATIVE_T2_AUTHORIZED_READ_FIXTURE")] : [])
              + (semanticAnchorPage154 ? [.define("PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1")] : []),
            linkerSettings: [
                .linkedLibrary("c++"),
                .linkedLibrary("resolv")
            ]
        ),
        .testTarget(
            name: "ProtobufMessagesTests",
            dependencies: ["ProtobufMessages"],
            resources: [.copy("Fixtures/NativePage")]
        ),
        .binaryTarget(name: "Lib", path: "../../Dependencies/Middleware/Lib.xcframework")
    ]
)
