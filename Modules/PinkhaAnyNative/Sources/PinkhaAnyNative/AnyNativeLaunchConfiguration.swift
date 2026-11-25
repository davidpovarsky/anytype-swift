import Foundation

/// Both executable compositions use the same private storage and credential
/// namespace. Only DEBUG UI acceptance can opt into an explicitly owned UUID.
public struct AnyNativeLaunchConfiguration: Sendable {
    public let dataDirectory: URL
    public let credentialService: String

    public static func current(arguments: [String] = ProcessInfo.processInfo.arguments) throws -> Self {
        #if DEBUG
        if arguments.contains("--native-ui-tests") {
            guard arguments.filter({ $0 == "--native-ui-tests" }).count == 1,
                  arguments.filter({ $0 == "--native-ui-test-scope" }).count == 1,
                  let position = arguments.firstIndex(of: "--native-ui-test-scope"),
                  position + 1 < arguments.count,
                  let scope = UUID(uuidString: arguments[position + 1]) else {
                throw AnyNativeApplicationError.invalidConfiguration
            }
            return Self(
                dataDirectory: FileManager.default.temporaryDirectory
                    .appendingPathComponent("native-ui-" + scope.uuidString, isDirectory: true),
                credentialService: "io.pinkha.anynative.uitests." + scope.uuidString)
        }
        #endif
        return Self(dataDirectory: try AnyNativeApplication.defaultDataDirectory(),
                    credentialService: "io.pinkha.anynative.accounts.v1")
    }
}
