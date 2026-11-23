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
