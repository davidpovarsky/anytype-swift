// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "PinkhaAnyUI",
    platforms: [.iOS("27.0"), .macOS(.v26)],
    products: [.library(name: "PinkhaAnyUI", targets: ["PinkhaAnyUI"])],
    dependencies: [
        .package(path: "../../Dependencies/Hanlin/Packages/HanlinMiniAppsBridge"),
        .package(path: "../PinkhaSharing"),
        .package(path: "../PinkhaTorahPresentation"),
        .package(path: "../PinkhaAnyHost"),
        .package(path: "../PinkhaAnyEngine"),
        .package(path: "../PinkhaAnyIntegration"),
        .package(path: "../PinkhaKit"),
        .package(path: "../PinkhaAnyHanlin"),
        .package(path: "../Loc"),
        .package(path: "../DesignKit"),
        .package(path: "../AnytypeCore"),
        .package(url: "https://github.com/davidpovarsky/TorahInspectorKit.git",
                 revision: "9058b489e9acc271b4f8ef69e2ed24648f93b4ed")
    ],
    targets: [
        .target(name: "PinkhaAnyUI", dependencies: [
            .product(name: "HanlinMiniAppsBridge", package: "HanlinMiniAppsBridge", condition: .when(platforms: [.iOS])),
            "PinkhaSharing",
            "PinkhaTorahPresentation", "PinkhaAnyHost", "PinkhaAnyHanlin",
            "PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaKit",
            .product(name: "PinkhaHanlinUI", package: "PinkhaAnyHanlin", condition: .when(platforms: [.iOS])),
            .product(name: "Loc", package: "Loc", condition: .when(platforms: [.iOS, .macOS])),
            .product(name: "DesignKit", package: "DesignKit", condition: .when(platforms: [.iOS])),
            .product(name: "AnytypeCore", package: "AnytypeCore", condition: .when(platforms: [.iOS])),
            .product(name: "TorahInspectorCore", package: "TorahInspectorKit"),
            .product(name: "TorahInspectorUI", package: "TorahInspectorKit",
                     condition: .when(platforms: [.iOS, .macOS]))
        ]),
        .testTarget(name: "PinkhaAnyUITests", dependencies: [
            "PinkhaAnyUI", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",
            .product(name: "DesignKit", package: "DesignKit", condition: .when(platforms: [.iOS]))
        ])
    ]
)
