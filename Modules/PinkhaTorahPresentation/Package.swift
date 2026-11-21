// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "PinkhaTorahPresentation",
    platforms: [.iOS(.v18), .macOS(.v14)],
    products: [.library(name: "PinkhaTorahPresentation", targets: ["PinkhaTorahPresentation"])],
    dependencies: [
        .package(path: "../PinkhaKit"),
        .package(path: "../Loc"),
        .package(url: "https://github.com/davidpovarsky/TorahInspectorKit.git",
                 revision: "158acb295f832e96907cdadc813a1c2a4bb6a03c")
    ],
    targets: [
        .target(name: "PinkhaTorahPresentation", dependencies: [
            "PinkhaKit",
            .product(name: "Loc", package: "Loc", condition: .when(platforms: [.iOS, .macOS])),
            .product(name: "TorahInspectorCore", package: "TorahInspectorKit"),
            .product(name: "TorahInspectorUI", package: "TorahInspectorKit",
                     condition: .when(platforms: [.iOS, .macOS]))
        ]),
        .testTarget(name: "PinkhaTorahPresentationTests", dependencies: ["PinkhaTorahPresentation"],
                    resources: [.process("Fixtures")])
    ]
)
