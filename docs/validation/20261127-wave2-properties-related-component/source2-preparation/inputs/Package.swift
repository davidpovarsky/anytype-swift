// swift-tools-version: 6.0
import PackageDescription

// Isolated source-model component only. The model and full Models.swift are
// exact published bytes; tests are the exact new suite suffix with imports.
// This does not compile the original App module, old tests, or SwiftUI callers.
let package = Package(
    name: "PropertiesSourceDocumentsComponent",
    products: [.library(name: "PinkhaAnyUI", targets: ["PinkhaAnyUI"])],
    targets: [
        .target(name: "TorahInspectorCore"),
        .target(name: "PinkhaAnyUI", dependencies: ["TorahInspectorCore"]),
        .testTarget(name: "PinkhaAnyUITests", dependencies: ["PinkhaAnyUI", "TorahInspectorCore"])
    ]
)
