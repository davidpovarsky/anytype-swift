import Foundation

extension Foundation.Bundle {
    static nonisolated let module: Bundle = {
        let mainPath = Bundle.main.bundleURL.appendingPathComponent("SwiftProtobuf_SwiftProtobufPluginLibrary.resources").path
        let buildPath = "C:\\Users\\DAVID\\AppData\\Local\\Temp\\omd-20261122\\build\\x86_64-unknown-windows-msvc\\debug\\SwiftProtobuf_SwiftProtobufPluginLibrary.resources"

        let preferredBundle = Bundle(path: mainPath)

        guard let bundle = preferredBundle ?? Bundle(path: buildPath) else {
            // Users can write a function called fatalError themselves, we should be resilient against that.
            Swift.fatalError("could not load resource bundle: from \(mainPath) or \(buildPath)")
        }

        return bundle
    }()
}