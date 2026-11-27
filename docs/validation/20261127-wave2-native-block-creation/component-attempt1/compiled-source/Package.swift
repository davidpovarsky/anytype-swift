// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "PinkhaNativeBlockCreationComponent",
    dependencies: [
        .package(path: "/mnt/development/projects/worktrees/anytype-wave2-native-block-menu-20261127/Modules/PinkhaAnyEngine"),
        .package(path: "/mnt/development/projects/worktrees/anytype-wave2-native-block-menu-20261127/Modules/PinkhaAnyHost"),
        .package(path: "/mnt/development/projects/worktrees/anytype-wave2-native-block-menu-20261127/Modules/PinkhaAnyIntegration"),
        .package(path: "/mnt/development/projects/worktrees/anytype-wave2-native-block-menu-20261127/Modules/PinkhaKit")
    ],
    targets: [
        .target(name: "PinkhaAnyUI", dependencies: ["PinkhaAnyEngine", "PinkhaAnyHost", "PinkhaAnyIntegration", "PinkhaKit"]),
        .testTarget(name: "PinkhaAnyUITests", dependencies: ["PinkhaAnyUI", "PinkhaAnyEngine", "PinkhaAnyHost", "PinkhaAnyIntegration", "PinkhaKit"])
    ]
)
