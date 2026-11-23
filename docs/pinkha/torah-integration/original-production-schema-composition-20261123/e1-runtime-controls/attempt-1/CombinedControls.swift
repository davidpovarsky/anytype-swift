// BEGIN SOURCE: Modules/AppTarget/Sources/AppTarget/AppTargetType.swift

public enum AppTargetType: Sendable {
    case debug
    case releaseAnytype
}

public extension AppTargetType {
    var isDebug: Bool {
        if case .debug = self { return true }
        return false
    }
    
    var isReleaseAnytype: Bool {
        if case .releaseAnytype = self { return true }
        return false
    }
}

// END SOURCE

// BEGIN SOURCE: Modules/AnytypeCore/AnytypeCore/Utils/CoreEnvironment.swift
import Foundation

// Configurations problem.
// SPM allow only two configurations: debug and release.
// If build name contains Debug - this is debug build.
// Other flags from Xcode configuration don't pass to SPM.
// This means `#if DEBUG` will work only in SPM debug build.
// https://forums.swift.org/t/annoying-limitation-of-packagedescription-buildconfiguration/56037/6
// https://github.com/apple/swift/issues/58321

// Dsym problem.
// Xcode generated Dsym for local packages only in Release configuration. DEBUG_INFORMATION_FORMAT isn't used.😬
// External dependencies don't have this problem. There are contains in App.dsym file.
// We should to use configuration with "Release" name for generate Dsyms in nightly buils for local packages.

// We can't use `#if DEBUG` and generate Dsyms at the same time for local packages 😭.
// One of solution - crate 'Release' build and pass debug flags to package.
// Other solution. Allow for debug configuration dsyms in each local package. But this desition will slow down local builds.

// Check it in feature XCode versions. Maybe it will be fixed.

// Temporary solution - setup environment from main target.
// In the main target, always use #if. This way, the compiler will cut out unused code.

public enum CoreEnvironment {
    
    nonisolated(unsafe) private static var _cachedTargetType: AppTargetType?
    private static let lock = OSAllocatedUnfairLock()

    public static var targetType: AppTargetType {
        lock.lock()
        defer { lock.unlock() }

        if let cached = _cachedTargetType {
            return cached
        }

        let condition = E1Platform.bundle.object(forInfoDictionaryKey: "CompilationCondition") as? String ?? ""

        let resolved: AppTargetType
        switch condition {
        case "DEBUG", "RELEASE_NIGHTLY":
            resolved = .debug
        case "RELEASE_ANYTYPE":
            resolved = .releaseAnytype
        default:
            resolved = .debug
        }

        _cachedTargetType = resolved
        return resolved
    }
    
    public static var isSimulator: Bool {
        #if targetEnvironment(simulator)
          return true
        #else
          return false
        #endif
    }
}

// END SOURCE

// BEGIN SOURCE: Modules/AnytypeCore/AnytypeCore/Utils/OriginalRuntimeEnvironment.swift
import Foundation

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

        let condition = E1Platform.bundle.object(forInfoDictionaryKey: "CompilationCondition") as? String
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

        guard let container = E1Platform.containerURL(
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

// END SOURCE

// BEGIN SOURCE: Modules/AnytypeCore/AnytypeCore/Utils/TargetsConstants.swift
public struct TargetsConstants {
    public static var appGroup: String {
        OriginalRuntimeEnvironment.capture().appGroup
    }
}

// END SOURCE

// BEGIN SOURCE: Modules/AnytypeCore/AnytypeCore/Utils/UserDefaultWrapper/UserDefaultByAppGroupStorage.swift
import Foundation

public final class UserDefaultByAppGroupStorage<T: Codable & Sendable>: @unchecked Sendable {
    
    private let key: String
    private let defaultValue: T
    
    public init(key: String, defaultValue: T) {
        let environment = OriginalRuntimeEnvironment.capture()
        self.key = environment.storageKey(key)
        self.defaultValue = defaultValue
        self.groupUserDefaults = E1Platform.groupStore(suiteName: environment.appGroup)
        self.standardUserDefaults = E1Platform.standard
    }
    
    public var value: T {
        get {
            // Read value from UserDefaults
            guard let data = userDefaultsObject(forKey: key) as? Data else {
                // Return defaultValue when no data in UserDefaults
                return defaultValue
            }

            // Convert data to the desire data type
            let value = try? JSONDecoder().decode(T.self, from: data)
            return value ?? defaultValue
        }
        set {            
            if let optional = newValue as? AnyOptional, optional.isNil {
                userDefaultsRemoveObject(forKey: key)
            } else {
                // Convert newValue to data
                let data = try? JSONEncoder().encode(newValue)
                
                // Set value to UserDefaults
                userDefaultsSet(data, forKey: key)
            }
        }
    }
    
    // MARK: - E1Platform.standard migration to UserDefaults with group
        
    private let groupUserDefaults: UserDefaults?
    private let standardUserDefaults: UserDefaults
    
    private func userDefaultsObject(forKey defaultName: String) -> Any? {
        if let object = groupUserDefaults?.object(forKey: defaultName) {
            return object
        } else {
            let object = standardUserDefaults.object(forKey: defaultName)
            groupUserDefaults?.set(object, forKey: defaultName)
            return object
        }
    }
    
    private func userDefaultsRemoveObject(forKey defaultName: String) {
        groupUserDefaults?.removeObject(forKey: defaultName)
        standardUserDefaults.removeObject(forKey: defaultName)
    }
    
    private func userDefaultsSet(_ value: Any?, forKey defaultName: String) {
        groupUserDefaults?.set(value, forKey: defaultName)
        standardUserDefaults.set(value, forKey: defaultName)
    }
}

// END SOURCE

// BEGIN SOURCE: Modules/AnytypeCore/AnytypeCore/Utils/UserDefaultWrapper/UserDefaultStorage.swift
import Foundation

// Since our property wrapper's Value type isn't optional, but
// can still contain nil values, we'll have to introduce this
// protocol to enable us to cast any assigned value into a type
// that we can compare against nil:
public protocol AnyOptional {
    var isNil: Bool { get }
}

extension Optional: AnyOptional { }

// WARNING: - This storage is not synchronized between processes (because of cache), not suitable for use in extensions
public final class UserDefaultStorage<T: Codable & Sendable>: @unchecked Sendable {
    
    private let key: String
    private let defaultValue: T
    
    private var data: T
    private let lock = OSAllocatedUnfairLock()
    
    public init(key: String, defaultValue: T) {
        let environment = OriginalRuntimeEnvironment.capture()
        self.key = environment.storageKey(key)
        self.defaultValue = defaultValue
        
        // Read value from UserDefaults
        if let data = E1Platform.standard.object(forKey: self.key) as? Data,
           let value = try? JSONDecoder().decode(T.self, from: data) {
            self.data = value
        } else {
            self.data = defaultValue
        }
    }
    
    public var value: T {
        get {
            lock.lock()
            defer { lock.unlock() }
            return data
        }
        set {
            lock.lock()
            defer { lock.unlock() }
            
            data = newValue
            
            if let optional = newValue as? AnyOptional, optional.isNil {
                E1Platform.standard.removeObject(forKey: key)
            } else {
                // Convert newValue to data
                let data = try? JSONEncoder().encode(newValue)
                
                // Set value to UserDefaults
                E1Platform.standard.set(data, forKey: key)
            }
        }
    }
}

// END SOURCE

import Foundation
import Dispatch

// Portable control boundary only. Production source has no injection switch.
// Apple-only process metadata/container/lock APIs are explicitly substituted by
// the driver; UserDefaults/JSON/cache/state-machine code remains real Foundation.
final class OSAllocatedUnfairLock: @unchecked Sendable {
    private let value = NSLock()
    func lock() { value.lock() }
    func unlock() { value.unlock() }
}

enum E1Platform {
    enum ContainerMode: Sendable { case available, missing, nonFileURL, regularFile }
    struct MainBundle: Sendable {
        func object(forInfoDictionaryKey key: String) -> Any? {
            key == "CompilationCondition" ? E1Platform.condition : nil
        }
    }
    static let bundle = MainBundle()
    nonisolated(unsafe) static var condition: String? = "DEBUG"
    nonisolated(unsafe) static var containerMode: ContainerMode = .available
    nonisolated(unsafe) static var root: URL!
    private static let lock = NSLock()
    private static let prefix = "org.otzaria.e1.controls." + UUID().uuidString
    nonisolated(unsafe) private static var domains: Set<String> = []
    nonisolated(unsafe) private static var requests = 0
    nonisolated(unsafe) private static var suites = 0

    nonisolated(unsafe) static let standard: UserDefaults = makeStore(prefix + ".standard")!

    private static func makeStore(_ name: String) -> UserDefaults? {
        lock.lock()
        domains.insert(name)
        suites += 1
        lock.unlock()
        return UserDefaults(suiteName: name)
    }

    static func groupStore(suiteName: String) -> UserDefaults? {
        makeStore(prefix + ".group." + suiteName)
    }

    static func containerURL(forSecurityApplicationGroupIdentifier _: String) -> URL? {
        lock.lock()
        requests += 1
        lock.unlock()
        switch containerMode {
        case .available: return root.appendingPathComponent("container", isDirectory: true)
        case .missing: return nil
        case .nonFileURL: return URL(string: "https://invalid.example/owned-group")
        case .regularFile: return root.appendingPathComponent("regular-file")
        }
    }

    static var containerRequests: Int {
        lock.lock(); defer { lock.unlock() }
        return requests
    }
    static var suiteCreations: Int {
        lock.lock(); defer { lock.unlock() }
        return suites
    }

    static func prepare(at path: String) throws {
        root = URL(fileURLWithPath: path, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        try FileManager.default.createDirectory(
            at: root.appendingPathComponent("container"), withIntermediateDirectories: false)
        try Data("owned regular-file adverse control".utf8)
            .write(to: root.appendingPathComponent("regular-file"), options: .withoutOverwriting)
    }

    static func cleanup() throws {
        lock.lock()
        let ownedDomains = domains
        lock.unlock()
        for domain in ownedDomains {
            UserDefaults(suiteName: domain)?.removePersistentDomain(forName: domain)
        }
        try FileManager.default.removeItem(at: root)
    }
}

struct ControlFailure: Error, CustomStringConvertible {
    let description: String
}
nonisolated(unsafe) private var assertions = 0
private let fixedPrefix = "AnytypeOriginalEditor.v1."
private let hostGroup = "group.org.otzaria.e1.host"

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    assertions += 1
    if !condition() { throw ControlFailure(description: message) }
}

func expectError(
    _ expected: OriginalRuntimeEnvironment.ConfigurationError,
    _ operation: () throws -> Void
) throws {
    do {
        try operation()
    } catch let error as OriginalRuntimeEnvironment.ConfigurationError {
        try require(error == expected, "unexpected configuration error: \(error), expected \(expected)")
        return
    }
    throw ControlFailure(description: "expected configuration error: \(expected)")
}

func install(
    _ group: String = hostGroup,
    target: AppTargetType = .debug
) throws {
    try OriginalRuntimeEnvironment.configureEmbedded(appGroup: group, expectedTarget: target)
}

func put<T: Encodable>(_ value: T, _ key: String, in store: UserDefaults) throws {
    store.set(try JSONEncoder().encode(value), forKey: key)
}

func stored<T: Decodable>(_ type: T.Type, _ key: String, in store: UserDefaults) throws -> T {
    guard let data = store.object(forKey: key) as? Data else {
        throw ControlFailure(description: "missing encoded owned value: \(key)")
    }
    return try JSONDecoder().decode(type, from: data)
}

func standaloneDebug() throws {
    let standard = E1Platform.standard
    let group = E1Platform.groupStore(suiteName: "group.io.anytype.app.dev")!
    try put("legacy-account", "userId", in: standard)
    let value = UserDefaultByAppGroupStorage(key: "userId", defaultValue: "default")
    try require(TargetsConstants.appGroup == "group.io.anytype.app.dev", "original debug group changed")
    try require(value.value == "legacy-account", "original migration read changed")
    let migrated = try stored(String.self, "userId", in: group)
    try require(migrated == "legacy-account", "original standard-to-group migration changed")
    value.value = "new-original-account"
    let groupWritten = try stored(String.self, "userId", in: group)
    let standardWritten = try stored(String.self, "userId", in: standard)
    try require(groupWritten == "new-original-account" && standardWritten == groupWritten,
                "original dual write changed")
    let optional = UserDefaultByAppGroupStorage<String?>(key: "userId", defaultValue: nil)
    optional.value = nil
    try require(group.object(forKey: "userId") == nil && standard.object(forKey: "userId") == nil,
                "original optional dual removal changed")
    try require(standard.object(forKey: fixedPrefix + "userId") == nil, "standalone was namespaced")
    try require(E1Platform.containerRequests == 0, "standalone unexpectedly validated external container")
}

func standaloneRelease() throws {
    E1Platform.condition = "RELEASE_ANYTYPE"
    try require(TargetsConstants.appGroup == "group.io.anytype.app", "original release group changed")
    let cache = UserDefaultStorage(key: "serverConfig", defaultValue: "original-release")
    cache.value = "persisted-original-release"
    let written = try stored(String.self, "serverConfig", in: E1Platform.standard)
    try require(written == cache.value, "original standard storage key changed")
    try expectError(.alreadyInUse) { try install(target: .releaseAnytype) }
}

func embeddedIsolation() throws {
    let standard = E1Platform.standard
    let group = E1Platform.groupStore(suiteName: hostGroup)!
    try put("host-account", "userId", in: standard)
    try put("host-group-account", "userId", in: group)
    try put("owned-prior-account", fixedPrefix + "userId", in: standard)
    try put("host-setting", "serverConfig", in: standard)
    try put("owned-prior-setting", fixedPrefix + "serverConfig", in: standard)
    try put("host-only", "bareOnly", in: standard)
    try put("host-group-only", "bareOnly", in: group)
    try install()
    let account = UserDefaultByAppGroupStorage(key: "userId", defaultValue: "default-account")
    let setting = UserDefaultStorage(key: "serverConfig", defaultValue: "default-setting")
    try require(TargetsConstants.appGroup == hostGroup, "embedded group not captured")
    try require(account.value == "owned-prior-account", "embedded read migrated a bare host account")
    try require(setting.value == "owned-prior-setting", "initializer read used the unqualified local key")
    let ownedMigration = try stored(String.self, fixedPrefix + "userId", in: group)
    try require(ownedMigration == "owned-prior-account", "same-namespace migration not preserved")
    let bareOnly = UserDefaultByAppGroupStorage(key: "bareOnly", defaultValue: "isolated-default")
    try require(bareOnly.value == "isolated-default", "embedded fallback read a bare host key")
    account.value = "owned-new-account"
    setting.value = "owned-new-setting"
    let ownGroup = try stored(String.self, fixedPrefix + "userId", in: group)
    let ownStandard = try stored(String.self, fixedPrefix + "userId", in: standard)
    let ownSetting = try stored(String.self, fixedPrefix + "serverConfig", in: standard)
    try require(ownGroup == account.value && ownStandard == account.value, "embedded dual write not namespaced")
    try require(ownSetting == setting.value, "embedded standard write not namespaced")
    let groupOptional = UserDefaultByAppGroupStorage<String?>(key: "userId", defaultValue: nil)
    let standardOptional = UserDefaultStorage<String?>(key: "serverConfig", defaultValue: nil)
    groupOptional.value = nil
    standardOptional.value = nil
    try require(group.object(forKey: fixedPrefix + "userId") == nil, "embedded group removal missed namespace")
    try require(standard.object(forKey: fixedPrefix + "userId") == nil, "embedded fallback removal missed namespace")
    try require(standard.object(forKey: fixedPrefix + "serverConfig") == nil, "embedded standard removal missed namespace")
    let bareAccount = try stored(String.self, "userId", in: standard)
    let bareGroup = try stored(String.self, "userId", in: group)
    let bareSetting = try stored(String.self, "serverConfig", in: standard)
    try require(bareAccount == "host-account" && bareGroup == "host-group-account" && bareSetting == "host-setting",
                "embedded write/removal changed the host's bare keys")
    try expectError(.alreadyInUse) { try install() }
}

func firstConsumer(_ consumer: String) throws {
    switch consumer {
    case "standard": _ = UserDefaultStorage(key: "first", defaultValue: "default")
    case "group": _ = UserDefaultByAppGroupStorage(key: "first", defaultValue: "default")
    case "target": _ = TargetsConstants.appGroup
    default: throw ControlFailure(description: "unknown consumer")
    }
    try expectError(.alreadyInUse) { try install() }
    try require(TargetsConstants.appGroup == "group.io.anytype.app.dev", "late install changed standalone group")
}

func sameInstall() throws {
    try install()
    try require(E1Platform.suiteCreations == 0, "configuration created defaults before capture")
    try install()
    try require(E1Platform.containerRequests == 1, "same unconsumed configuration was reinstalled")
    try require(TargetsConstants.appGroup == hostGroup, "same install changed selected group")
    try expectError(.alreadyInUse) { try install() }
}

func conflictingInstall() throws {
    try install()
    try expectError(.conflictingConfiguration) { try install("group.org.otzaria.e1.other") }
    try expectError(.conflictingConfiguration) { try install(target: .releaseAnytype) }
    try require(E1Platform.containerRequests == 1, "conflicting install reached another container")
    try require(TargetsConstants.appGroup == hostGroup, "conflicting install replaced selected group")
}

func invalidGroupRecovery() throws {
    for invalid in ["", "group.", "group..host", "group.host/path", "group.host\n",
                    "group.אוצריא", "wrong.host", "group." + String(repeating: "x", count: 256)] {
        try expectError(.invalidAppGroup) { try install(invalid) }
    }
    try require(E1Platform.containerRequests == 0 && E1Platform.suiteCreations == 0,
                "invalid group created a container/defaults store")
    try install()
    try require(TargetsConstants.appGroup == hostGroup, "invalid attempt poisoned later valid configuration")
}

func bundleConditionRecovery() throws {
    for condition in [nil, "", "UNKNOWN", "release_anytype"] as [String?] {
        E1Platform.condition = condition
        try expectError(.invalidCompilationCondition) { try install() }
    }
    try require(E1Platform.containerRequests == 0 && E1Platform.suiteCreations == 0,
                "invalid main-bundle metadata reached container/defaults")
    E1Platform.condition = "RELEASE_NIGHTLY"
    try install()
    try require(TargetsConstants.appGroup == hostGroup, "original nightly/debug mapping changed")
}

func declaredMismatch() throws {
    try expectError(.deploymentMismatch) { try install(target: .releaseAnytype) }
    try require(E1Platform.containerRequests == 0, "declared mismatch reached group container")
    try install()
    try require(TargetsConstants.appGroup == hostGroup, "matching declared target could not recover")
}

func cachedMismatch() throws {
    try require(CoreEnvironment.targetType.isDebug, "original cache did not capture debug")
    E1Platform.condition = "RELEASE_ANYTYPE"
    try expectError(.deploymentMismatch) { try install(target: .releaseAnytype) }
    try require(CoreEnvironment.targetType.isDebug, "configuration rewrote original cached target")
    try require(E1Platform.containerRequests == 0, "cached mismatch reached group container")
    E1Platform.condition = "DEBUG"
    try install()
    try require(TargetsConstants.appGroup == hostGroup, "matching cache could not be used")
}

func matchingDirectReadLimitation() throws {
    try require(CoreEnvironment.targetType.isDebug, "direct original environment read failed")
    try install()
    try require(TargetsConstants.appGroup == hostGroup,
                "four-file seam unexpectedly claimed detection of matching direct CoreEnvironment read")
}

func containerDenialRecovery() throws {
    for mode in [E1Platform.ContainerMode.missing, .nonFileURL, .regularFile] {
        E1Platform.containerMode = mode
        try expectError(.groupContainerUnavailable) { try install() }
        try require(E1Platform.suiteCreations == 0, "denied container still created defaults")
    }
    E1Platform.containerMode = .available
    try install()
    try require(E1Platform.suiteCreations == 0, "configuration itself started defaults")
    let value = UserDefaultByAppGroupStorage(key: "afterAccess", defaultValue: "default")
    value.value = "owned-after-access"
    try require(value.value == "owned-after-access", "valid owned directory could not use captured configuration")
}

func cacheAndDecode() throws {
    let standard = E1Platform.standard
    try put("initial", "cache", in: standard)
    let cache = UserDefaultStorage(key: "cache", defaultValue: "default")
    try put("external-change", "cache", in: standard)
    try require(cache.value == "initial", "original process-local cache semantics changed")
    cache.value = "setter-change"
    let storedValue = try stored(String.self, "cache", in: standard)
    try require(cache.value == "setter-change" && storedValue == cache.value, "cache setter/persistence diverged")
    standard.set(Data("not JSON".utf8), forKey: "corrupt")
    let corrupt = UserDefaultStorage(key: "corrupt", defaultValue: "default")
    try require(corrupt.value == "default", "original malformed JSON fallback changed")
    let group = E1Platform.groupStore(suiteName: "group.io.anytype.app.dev")!
    try put("standard-valid", "corrupt-group", in: standard)
    group.set(Data("not JSON".utf8), forKey: "corrupt-group")
    let corruptGroup = UserDefaultByAppGroupStorage(key: "corrupt-group", defaultValue: "group-default")
    try require(corruptGroup.value == "group-default", "original corrupt group-data behavior changed")
    let optional = UserDefaultStorage<String?>(key: "cache", defaultValue: nil)
    optional.value = nil
    try require(standard.object(forKey: "cache") == nil && optional.value == nil, "cached optional removal changed")
}

final class RaceResults: @unchecked Sendable {
    private let lock = NSLock()
    private var contexts: [String] = []
    private var failures: [String] = []
    func record(context: String) { lock.lock(); contexts.append(context); lock.unlock() }
    func record(error: Error) { lock.lock(); failures.append(String(describing: error)); lock.unlock() }
    func snapshot() -> ([String], [String]) {
        lock.lock(); defer { lock.unlock() }
        return (contexts, failures)
    }
}

func concurrentFirstUse() throws {
    let results = RaceResults()
    let group = DispatchGroup()
    for index in 0..<24 {
        group.enter()
        DispatchQueue.global().async {
            defer { group.leave() }
            if index.isMultiple(of: 3) {
                do { try install() }
                catch OriginalRuntimeEnvironment.ConfigurationError.alreadyInUse { }
                catch { results.record(error: error) }
            } else {
                let context = OriginalRuntimeEnvironment.capture()
                results.record(context: context.appGroup + "|" + context.storageKey("race"))
            }
        }
    }
    group.wait()
    let (contexts, failures) = results.snapshot()
    try require(failures.isEmpty, "concurrent first use produced unexpected configuration errors: \(failures)")
    try require(contexts.count == 16 && Set(contexts).count == 1, "concurrent consumers captured different contexts")
    let accepted = [
        "group.io.anytype.app.dev|race",
        hostGroup + "|" + fixedPrefix + "race"
    ]
    try require(contexts.first.map(accepted.contains) == true, "race produced a hybrid group/namespace")
    try expectError(.alreadyInUse) { try install() }
}

@main
struct RuntimeEnvironmentControls {
    static func main() throws {
        let arguments = CommandLine.arguments
        guard arguments.count == 3 else { throw ControlFailure(description: "case and unique fixture path required") }
        let name = arguments[1]
        try E1Platform.prepare(at: arguments[2])
        do {
            switch name {
            case "standalone-debug-migration-roundtrip": try standaloneDebug()
            case "standalone-release-defaults": try standaloneRelease()
            case "embedded-namespace-isolation": try embeddedIsolation()
            case "first-standard-consumer-seals": try firstConsumer("standard")
            case "first-group-consumer-seals": try firstConsumer("group")
            case "first-target-consumer-seals": try firstConsumer("target")
            case "same-install-before-use": try sameInstall()
            case "conflicting-install-before-use": try conflictingInstall()
            case "invalid-group-recovery": try invalidGroupRecovery()
            case "invalid-bundle-condition-recovery": try bundleConditionRecovery()
            case "declared-target-mismatch": try declaredMismatch()
            case "cached-target-mismatch": try cachedMismatch()
            case "matching-direct-read-limitation": try matchingDirectReadLimitation()
            case "container-denial-recovery": try containerDenialRecovery()
            case "original-cache-and-decode": try cacheAndDecode()
            case "concurrent-first-use": try concurrentFirstUse()
            default: throw ControlFailure(description: "unknown control")
            }
            try E1Platform.cleanup()
            let result: [String: Any] = [
                "case": name, "status": "PASS", "assertions": assertions,
                "scope": "portable state/storage control; Apple platform boundaries substituted",
                "owned_fixture_cleanup": "PASS"
            ]
            print(String(decoding: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), as: UTF8.self))
        } catch {
            try? E1Platform.cleanup()
            throw error
        }
    }
}
