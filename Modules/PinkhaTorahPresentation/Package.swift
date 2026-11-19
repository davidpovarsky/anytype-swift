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
                 revision: "4e59e909dd22685bb46f9396bc57e5f8c627d773")
    ],
    targets: [
        .target(name: "PinkhaTorahPresentation", dependencies: [
            "PinkhaKit",
            .product(name: "Loc", package: "Loc", condition: .when(platforms: [.iOS, .macOS])),
            .product(name: "TorahInspectorCore", package: "TorahInspectorKit"),
            .product(name: "TorahInspectorUI", package: "TorahInspectorKit",
                     condition: .when(platforms: [.iOS, .macOS]))
        ]),
        .testTarget(name: "PinkhaTorahPresentationTests", dependencies: ["PinkhaTorahPresentation"])
    ]
)
