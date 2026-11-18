import Darwin
import Foundation
import UIKit

/// One disposable UIKit application measuring the failing journal's platform contracts.
/// It never imports Anytype/Hanlin or invokes a provider, account, permission or write tool.
private struct ProbeStage: Encodable {
    var name: String
    var satisfied: Bool
    var requiredForInitialJournal: Bool = true
    var returnCode: Int32?
    var posixErrno: Int32?
    var foundationDomain: String?
    var foundationCode: Int?
    var protectionValueType: String?
    var protectionRawValue: String?
    var permissions: Int?
    var isDirectory: Bool?
    var isSymbolicLink: Bool?
}

private struct ProbeReport: Encodable {
    let protocolVersion = 1
    let status = "SYNTHETIC_PLATFORM_OBSERVATION_COMPLETE"
    let sourceSHA: String
    let runID: String
    let runAttempt: String
    let token: String
    let processID: Int32
    let bundleIdentifier: String
    let simulator: Bool
    let systemVersion: String
    let protectedDataAvailable: Bool
    let expectedProtectionRawValue: String
    let firstUnsatisfiedStage: String?
    let firstUnsatisfiedStageByStorageScope: [String: String]
    let storageScopes = ["application-support", "temporary-directory"]
    let allInitialJournalRequirementsObserved: Bool
    let stages: [ProbeStage]
    let nativeWriteAccepted = false
    let sdkAcceptance = false
    let physicalDeviceProtectionAccepted = false
    let physicalPowerLossDurabilityAccepted = false
}

@MainActor
private final class JournalFilesystemProbe {
    private var stages: [ProbeStage] = []
    private var storageScope = "application-support"
    private let fileManager = FileManager.default
    private let expectedProtection = FileProtectionType.completeUntilFirstUserAuthentication

    private func record(_ stage: ProbeStage) {
        var tagged = stage
        tagged.name = storageScope + "." + stage.name
        stages.append(tagged)
    }

    private func foundation(_ name: String, body: () throws -> Void) -> Bool {
        do {
            try body()
            record(.init(name: name, satisfied: true))
            return true
        } catch {
            let native = error as NSError
            record(.init(name: name, satisfied: false,
                                foundationDomain: native.domain, foundationCode: native.code))
            return false
        }
    }

    private func syscall(_ name: String, result: Int32, capturedErrno: Int32, succeeds: Bool) {
        record(.init(name: name, satisfied: succeeds, returnCode: result, posixErrno: capturedErrno))
    }

    private func inspectKind(_ url: URL, name: String) -> Bool {
        do {
            let values = try url.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey])
            let valid = values.isSymbolicLink != true && values.isDirectory == true
            record(.init(name: name, satisfied: valid,
                                isDirectory: values.isDirectory, isSymbolicLink: values.isSymbolicLink))
            return valid
        } catch {
            let native = error as NSError
            record(.init(name: name, satisfied: false,
                                foundationDomain: native.domain, foundationCode: native.code))
            return false
        }
    }

    private func inspectProtection(_ url: URL, name: String, mode: Int, required: Bool = true) {
        do {
            let attributes = try fileManager.attributesOfItem(atPath: url.path)
            let protection = attributes[.protectionKey]
            let raw = (protection as? FileProtectionType)?.rawValue ?? (protection as? String)
            let permissions = (attributes[.posixPermissions] as? NSNumber)?.intValue
            record(.init(name: name,
                satisfied: raw == expectedProtection.rawValue && permissions == mode,
                requiredForInitialJournal: required,
                protectionValueType: protection.map { String(reflecting: type(of: $0)) },
                protectionRawValue: raw, permissions: permissions))
        } catch {
            let native = error as NSError
            record(.init(name: name, satisfied: false, requiredForInitialJournal: required,
                                foundationDomain: native.domain, foundationCode: native.code))
        }
    }

    private func exercise(parent: URL) {
        guard inspectKind(parent, name: "parent.kind") else { return }
        let root = parent.appendingPathComponent("HanlinHostMetadataV1", isDirectory: true)
        let scope = root.appendingPathComponent(String(repeating: "1", count: 64), isDirectory: true)
        for (label, folder) in [("root", root), ("scope", scope)] {
            guard foundation(label + ".create", body: {
                try fileManager.createDirectory(at: folder, withIntermediateDirectories: false,
                    attributes: [.posixPermissions: 0o700, .protectionKey: expectedProtection])
            }) else { return }
            guard inspectKind(folder, name: label + ".kind") else { return }
            guard foundation(label + ".backup-exclusion", body: {
                var url = folder
                var values = URLResourceValues()
                values.isExcludedFromBackup = true
                try url.setResourceValues(values)
            }) else { return }
            // Record an attribute mismatch and continue ONLY this synthetic probe to
            // measure independent syscalls. The production journal guard is untouched.
            inspectProtection(folder, name: label + ".attributes", mode: 0o700)
        }

        let lockURL = scope.appendingPathComponent("owner.lock")
        errno = 0
        let lockFD = Darwin.open(lockURL.path, O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        let lockOpenErrno = errno
        syscall("lock.open", result: lockFD, capturedErrno: lockOpenErrno, succeeds: lockFD >= 0)
        guard lockFD >= 0 else { return }
        defer { Darwin.close(lockFD) }
        errno = 0
        let locked = flock(lockFD, LOCK_EX | LOCK_NB)
        let lockErrno = errno
        syscall("lock.exclusive", result: locked, capturedErrno: lockErrno, succeeds: locked == 0)
        guard locked == 0 else { return }
        var info = stat()
        errno = 0
        let stated = fstat(lockFD, &info)
        let statErrno = errno
        syscall("lock.regular-file", result: stated, capturedErrno: statErrno,
                succeeds: stated == 0 && (info.st_mode & S_IFMT) == S_IFREG)
        guard stated == 0 else { return }
        guard foundation("lock.set-attributes", body: {
            try fileManager.setAttributes([.protectionKey: expectedProtection, .posixPermissions: 0o600],
                                          ofItemAtPath: lockURL.path)
        }) else { return }

        let file = scope.appendingPathComponent("namespace.json")
        errno = 0
        let fd = Darwin.open(file.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        let openErrno = errno
        syscall("namespace.exclusive-open", result: fd, capturedErrno: openErrno, succeeds: fd >= 0)
        guard fd >= 0 else { return }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        guard foundation("namespace.set-protection", body: {
            try fileManager.setAttributes([.protectionKey: expectedProtection], ofItemAtPath: file.path)
        }) else { return }
        guard foundation("namespace.write", body: {
            try handle.write(contentsOf: Data("{\"app\":\"synthetic-probe\",\"metadataOnly\":true}".utf8))
        }) else { return }
        guard foundation("namespace.filehandle-synchronize", body: { try handle.synchronize() }) else { return }
        errno = 0
        let firstFlush = Darwin.fcntl(fd, F_FULLFSYNC)
        let firstFlushErrno = errno
        syscall("namespace.fullfsync-before-directories", result: firstFlush,
                capturedErrno: firstFlushErrno, succeeds: firstFlush == 0)
        for (label, folder) in [("scope", scope), ("root", root), ("parent", parent)] {
            errno = 0
            let parentFD = Darwin.open(folder.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            let parentOpenErrno = errno
            syscall(label + ".directory-open", result: parentFD,
                    capturedErrno: parentOpenErrno, succeeds: parentFD >= 0)
            guard parentFD >= 0 else { continue }
            errno = 0
            let synchronized = Darwin.fsync(parentFD)
            let synchronizeErrno = errno
            Darwin.close(parentFD)
            syscall(label + ".directory-fsync", result: synchronized,
                    capturedErrno: synchronizeErrno, succeeds: synchronized == 0)
        }
        errno = 0
        let finalFlush = Darwin.fcntl(fd, F_FULLFSYNC)
        let finalFlushErrno = errno
        syscall("namespace.fullfsync-after-directories", result: finalFlush,
                capturedErrno: finalFlushErrno, succeeds: finalFlush == 0)
        inspectProtection(file, name: "namespace.readback-attributes", mode: 0o600, required: false)
    }

    func run() {
        let environment = ProcessInfo.processInfo.environment
        do {
            let support = try fileManager.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                              appropriateFor: nil, create: true)
            let temporary = fileManager.temporaryDirectory.appendingPathComponent("hanlin-write-tests-" + UUID().uuidString,
                                                                                 isDirectory: true)
            let parents = [("application-support", support.appendingPathComponent("Anytype", isDirectory: true), true),
                           ("temporary-directory", temporary, false)]
            for (scope, parent, intermediates) in parents {
                storageScope = scope
                if foundation("host.create", body: {
                    try fileManager.createDirectory(at: parent, withIntermediateDirectories: intermediates)
                }) { exercise(parent: parent) }
            }
            #if targetEnvironment(simulator)
            let simulator = true
            #else
            let simulator = false
            #endif
            let failed = stages.first { $0.requiredForInitialJournal && !$0.satisfied }
            var firstByScope: [String: String] = [:]
            for (scope, _, _) in parents {
                firstByScope[scope] = stages.first {
                    $0.name.hasPrefix(scope + ".") && $0.requiredForInitialJournal && !$0.satisfied
                }?.name
            }
            let report = ProbeReport(sourceSHA: environment["PINKHA_PROBE_SOURCE_SHA"] ?? "",
                runID: environment["PINKHA_PROBE_RUN_ID"] ?? "", runAttempt: environment["PINKHA_PROBE_RUN_ATTEMPT"] ?? "",
                token: environment["PINKHA_PROBE_TOKEN"] ?? "", processID: ProcessInfo.processInfo.processIdentifier,
                bundleIdentifier: Bundle.main.bundleIdentifier ?? "", simulator: simulator,
                systemVersion: UIDevice.current.systemVersion,
                protectedDataAvailable: UIApplication.shared.isProtectedDataAvailable,
                expectedProtectionRawValue: expectedProtection.rawValue,
                firstUnsatisfiedStage: failed?.name, firstUnsatisfiedStageByStorageScope: firstByScope,
                allInitialJournalRequirementsObserved: failed == nil,
                stages: stages)
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
            let pending = support.appendingPathComponent("pinkha-hanlin-journal-probe.pending.json")
            let destination = support.appendingPathComponent("pinkha-hanlin-journal-probe.json")
            try encoder.encode(report).write(to: pending, options: .withoutOverwriting)
            try fileManager.moveItem(at: pending, to: destination)
            print("PINKHA_JOURNAL_PROBE_RECEIPT_READY")
        } catch {
            let error = error as NSError
            // Never log URLs, paths, userInfo, descriptions, payloads or credentials.
            print("PINKHA_JOURNAL_PROBE_RECEIPT_FAILED domain=\(error.domain) code=\(error.code)")
        }
    }
}

@main
@MainActor
final class JournalProbeAppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication, configurationForConnecting session: UISceneSession,
                     options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        let configuration = UISceneConfiguration(name: "JournalProbe", sessionRole: session.role)
        configuration.delegateClass = JournalProbeSceneDelegate.self
        return configuration
    }
}

@MainActor
final class JournalProbeSceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    private var started = false
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
        guard let scene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: scene)
        let controller = UIViewController()
        controller.view.backgroundColor = .systemBackground
        window.rootViewController = controller
        window.makeKeyAndVisible()
        self.window = window
    }
    func sceneDidBecomeActive(_ scene: UIScene) {
        guard !started else { return }
        started = true
        JournalFilesystemProbe().run()
    }
}
