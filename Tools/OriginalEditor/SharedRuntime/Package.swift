// swift-tools-version: 6.0
import PackageDescription

// This single dynamic product owns the complete original FirebaseMessaging
// implementation and the host's overlapping Google/Promises implementation.
// No upstream target, source, feature, or header is renamed or removed.
let package = Package(
    name: "OriginalEditorSharedFirebase",
    platforms: [.iOS(.v18)],
    products: [
        .library(name: "OriginalEditorSharedFirebase", type: .dynamic,
                 targets: ["OriginalEditorSharedFirebase"])
    ],
    dependencies: [
        .package(url: "https://github.com/firebase/firebase-ios-sdk.git", exact: "12.8.0"),
        .package(url: "https://github.com/google/GoogleUtilities.git", exact: "8.1.5"),
        .package(url: "https://github.com/google/GoogleDataTransport.git", exact: "10.1.1"),
        .package(url: "https://github.com/google/promises.git", exact: "2.4.1"),
        // CocoaPods 3.30910.0 and this SwiftPM tag are the same upstream commit.
        .package(url: "https://github.com/firebase/nanopb.git", exact: "2.30910.0")
    ],
    targets: [
        .target(name: "OriginalEditorSharedFirebase", dependencies: [
            .product(name: "FirebaseMessaging", package: "firebase-ios-sdk"),
            .product(name: "GULAppDelegateSwizzler", package: "GoogleUtilities"),
            .product(name: "GULEnvironment", package: "GoogleUtilities"),
            .product(name: "GULLogger", package: "GoogleUtilities"),
            .product(name: "GULMethodSwizzler", package: "GoogleUtilities"),
            .product(name: "GULNetwork", package: "GoogleUtilities"),
            .product(name: "GULNSData", package: "GoogleUtilities"),
            .product(name: "GULReachability", package: "GoogleUtilities"),
            .product(name: "GULSwizzlerTestHelpers", package: "GoogleUtilities"),
            .product(name: "GULUserDefaults", package: "GoogleUtilities"),
            .product(name: "GoogleDataTransport", package: "GoogleDataTransport"),
            .product(name: "Promises", package: "promises"),
            .product(name: "nanopb", package: "nanopb")
        ])
    ]
)
