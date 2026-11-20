// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "PinkhaAnyUI",
    platforms: [.iOS("27.0"), .macOS(.v26)],
    products: [.library(name: "PinkhaAnyUI", targets: ["PinkhaAnyUI"])],
    dependencies: [
        .package(path: "../PinkhaTorahPresentation"),
        .package(path: "../PinkhaAnyHost"),
        .package(path: "../PinkhaAnyEngine"),
        .package(path: "../PinkhaAnyIntegration"),
        .package(path: "../PinkhaKit"),
        .package(path: "../PinkhaAnyHanlin"),
        .package(path: "../Loc"),
        .package(url: "https://github.com/davidpovarsky/TorahInspectorKit.git",
                 revision: "4e59e909dd22685bb46f9396bc57e5f8c627d773")
    ],
    targets: [
        .target(name: "PinkhaAnyUI", dependencies: [
            "PinkhaTorahPresentation", "PinkhaAnyHost", "PinkhaAnyHanlin",
            "PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaKit",
            .product(name: "PinkhaHanlinUI", package: "PinkhaAnyHanlin", condition: .when(platforms: [.iOS])),
            .product(name: "Loc", package: "Loc", condition: .when(platforms: [.iOS, .macOS])),
            .product(name: "TorahInspectorCore", package: "TorahInspectorKit"),
            .product(name: "TorahInspectorUI", package: "TorahInspectorKit",
                     condition: .when(platforms: [.iOS, .macOS]))
        ]),
        .testTarget(name: "PinkhaAnyUITests", dependencies: [
            "PinkhaAnyUI", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration"
        ])
    ]
)
