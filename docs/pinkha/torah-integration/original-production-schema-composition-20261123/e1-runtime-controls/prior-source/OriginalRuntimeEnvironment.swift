import Foundation
import AppTarget

/// Deployment configuration for the original editor in an external host.
/// This does not establish an account, selected Space, or permission to write.
public enum OriginalRuntimeEnvironment {
    public enum ConfigurationError: Error, Sendable, Equatable {
        case alreadyInUse
        case conflictingConfiguration
        case invalidAppGroup
        case invalidCompilationCondition
        case deploymentMismatch
        case groupContainerUnavailable
    }

    private static let lock = NSLock()
    nonisolated(unsafe) private static var state: State = .unconfigured

    private enum State {
        case unconfigured
        case configured(Context)
        case captured(Context)
    }

    struct Context: Sendable {
        let appGroup: String
        fileprivate let targetType: AppTargetType
        fileprivate let keyPrefix: String

        func storageKey(_ originalKey: String) -> String {
            keyPrefix + originalKey
        }
    }

    /// Install before any original app-group or defaults consumer is created.
    /// The host must declare its real CompilationCondition and have access to
    /// the signed app-group container. Creating a defaults suite is not proof
    /// of that access. The namespace is fixed and never supplied by a caller.
    ///
    /// CoreEnvironment can have been read directly before this call. Its
    /// existing cached target is checked, never reset or overridden; this
    /// four-file seam cannot detect an earlier matching direct read.
    public static func configureEmbedded(
        appGroup: String,
        expectedTarget: AppTargetType
    ) throws {
        lock.lock()
        defer { lock.unlock() }

        switch state {
        case .captured:
            throw ConfigurationError.alreadyInUse
        case .configured(let context):
            guard context.appGroup == appGroup,
                  context.targetType.isDebug == expectedTarget.isDebug else {
                throw ConfigurationError.conflictingConfiguration
            }
            return
        case .unconfigured:
            break
        }

        let components = appGroup.dropFirst("group.".count)
            .split(separator: ".", omittingEmptySubsequences: false)
        guard appGroup.hasPrefix("group."), appGroup.utf8.count <= 255,
              !components.isEmpty,
              components.allSatisfy({ component in
                  !component.isEmpty && component.utf8.allSatisfy { byte in
                      (65...90).contains(byte) || (97...122).contains(byte)
                          || (48...57).contains(byte) || byte == 45
                  }
              }) else {
            throw ConfigurationError.invalidAppGroup
        }

        let condition = Bundle.main.object(forInfoDictionaryKey: "CompilationCondition") as? String
        let declaredTarget: AppTargetType
        switch condition {
        case "DEBUG", "RELEASE_NIGHTLY":
            declaredTarget = .debug
        case "RELEASE_ANYTYPE":
            declaredTarget = .releaseAnytype
        default:
            throw ConfigurationError.invalidCompilationCondition
        }
        guard declaredTarget.isDebug == expectedTarget.isDebug,
              CoreEnvironment.targetType.isDebug == expectedTarget.isDebug else {
            throw ConfigurationError.deploymentMismatch
        }

        guard let container = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroup
        ), container.isFileURL,
           (try? container.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true else {
            throw ConfigurationError.groupContainerUnavailable
        }

        state = .configured(Context(
            appGroup: appGroup,
            targetType: expectedTarget,
            keyPrefix: "AnytypeOriginalEditor.v1."
        ))
    }

    /// All original group/defaults consumers capture this same immutable value.
    /// First use also seals the original standalone behavior if no external
    /// host configuration was installed.
    static func capture() -> Context {
        lock.lock()
        defer { lock.unlock() }

        switch state {
        case .captured(let context):
            return context
        case .configured(let context):
            state = .captured(context)
            return context
        case .unconfigured:
            let targetType = CoreEnvironment.targetType
            let appGroup: String
            switch targetType {
            case .debug:
                appGroup = "group.io.anytype.app.dev"
            case .releaseAnytype:
                appGroup = "group.io.anytype.app"
            }
            let context = Context(appGroup: appGroup, targetType: targetType, keyPrefix: "")
            state = .captured(context)
            return context
        }
    }
}
