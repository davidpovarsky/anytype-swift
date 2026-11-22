// swift-tools-version: 6.0
import PackageDescription
let package = Package(name:"SemanticAnchorComponents",
products:[.library(name:"PinkhaKit",targets:["PinkhaKit"])],
targets:[.target(name:"TorahInspectorCore"),.target(name:"PinkhaKit",dependencies:["TorahInspectorCore"]),
.target(name:"PinkhaAnyHost", dependencies:["PinkhaKit"]),
.testTarget(name:"PinkhaKitTests",dependencies:["PinkhaKit"]),
.testTarget(name:"PinkhaAnyHostTests",dependencies:["PinkhaKit","PinkhaAnyHost"])])
