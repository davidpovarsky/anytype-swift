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
                 revision: "511454e49450cb2581ddf77f644146ff3e30dbef")
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
