#if DEBUG
import Foundation
import Observation
import PinkhaAnyNative

/// Explicit, disposable UI-test setup. It never writes a document or its body.
/// The production Type picker and conditional property writer remain unchanged.
@MainActor @Observable
final class NativeCustomTypeFixture {
    nonisolated static let contract = "pinkha-native-custom-type-ui-v1"
    nonisolated static let createFlag = "--native-ui-custom-type-fixture-v1"
    nonisolated static let auditFlag = "--native-ui-custom-type-audit-v1"
    enum Mode: String, Sendable { case prepare, audit }
    enum Failure: Error { case scope, existingAttempt, ownerDeadline, ownerChanged, nativeDefinition, receipt }

    private(set) var accessibilityValue = "waiting"
    private let scope: UUID
    private let directory: URL
    private let mode: Mode
    private let attempt = UUID()
    private var started = false
    private let counter: NativeCustomTypeWriteCounter

    private init(scope: UUID, directory: URL, mode: Mode) {
        self.scope = scope; self.directory = directory; self.mode = mode
        counter = .init(writesAllowed: mode == .prepare)
    }

    static func configured(arguments: [String], dataDirectory: URL,
                           credentialService: String) throws -> NativeCustomTypeFixture? {
        let prepare = arguments.filter { $0 == createFlag }.count
        let audit = arguments.filter { $0 == auditFlag }.count
        guard prepare + audit != 0 else { return nil }
        guard prepare + audit == 1,
              arguments.filter({ $0 == "--native-ui-tests" }).count == 1,
              arguments.filter({ $0 == "--native-ui-test-scope" }).count == 1,
              let index = arguments.firstIndex(of: "--native-ui-test-scope"), index + 1 < arguments.count,
              let scope = UUID(uuidString: arguments[index + 1]),
              arguments[index + 1] == scope.uuidString,
              credentialService == "io.pinkha.anynative.uitests." + scope.uuidString else { throw Failure.scope }
        let temporary = FileManager.default.temporaryDirectory
        let expected = temporary.appendingPathComponent("native-ui-" + scope.uuidString)
        guard dataDirectory.standardizedFileURL == expected.standardizedFileURL else { throw Failure.scope }
        return .init(scope: scope,
            directory: temporary.appendingPathComponent("native-ui-custom-type-" + scope.uuidString),
            mode: prepare == 1 ? .prepare : .audit)
    }

    /// Latch before any suspension. A failed/cancelled invocation cannot retry
    /// when SwiftUI re-enters .task. The exclusive marker also survives a kill.
    func run(application: AnyNativeApplication) async {
        guard !started else { return }
        started = true
        accessibilityValue = "running"
        do {
            let owner = try await waitForOwner(application)
            let spaces = try await application.listSpaces()
            let suffix = String(scope.uuidString.prefix(8))
            guard spaces.contains(where: { $0.id == owner.workspace.spaceID &&
                $0.name == "Custom Type UI Space " + suffix && $0.ownRole == "owner" }),
                await application.currentAccount()?.id == owner.workspace.accountID else { throw Failure.scope }
            let receiptURL = directory.appendingPathComponent("seed.json")
            let seed: NativeCustomTypeSeed
            if mode == .prepare {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
                let marker = NativeCustomTypeAttempt(contract: Self.contract, scopeUUID: scope.uuidString,
                    attemptUUID: attempt.uuidString, accountID: owner.workspace.accountID,
                    spaceID: owner.workspace.spaceID, ownerGeneration: owner.session.generation.uuidString)
                let markerURL = directory.appendingPathComponent("attempt.json")
                do { try Self.encoded(marker).write(to: markerURL, options: .withoutOverwriting) }
                catch { throw Failure.existingAttempt }
                guard !FileManager.default.fileExists(atPath: receiptURL.path) else { throw Failure.existingAttempt }
                seed = try await Self.prepare(owner: owner, scope: scope, attempt: attempt, counter: counter)
                try Self.encoded(seed).write(to: receiptURL, options: .withoutOverwriting)
            } else {
                let bytes = try Self.boundedFile(receiptURL, directory: directory)
                seed = try JSONDecoder().decode(NativeCustomTypeSeed.self, from: bytes)
                let marker = try JSONDecoder().decode(NativeCustomTypeAttempt.self,
                    from: Self.boundedFile(directory.appendingPathComponent("attempt.json"), directory: directory))
                guard marker.contract == Self.contract, marker.scopeUUID == scope.uuidString,
                      marker.attemptUUID == seed.attemptUUID, marker.accountID == seed.accountID,
                      marker.spaceID == seed.spaceID, marker.ownerGeneration == seed.ownerGeneration else {
                    throw Failure.receipt
                }
                try Self.validate(seed, scope: scope, owner: owner)
                guard seed.ownerGeneration != owner.session.generation.uuidString,
                      seed.processID != ProcessInfo.processInfo.processIdentifier else { throw Failure.ownerChanged }
                try await Self.audit(seed, owner: owner)
            }
            guard let current = await application.currentWorkspace(), current.session === owner.session else {
                throw Failure.ownerChanged
            }
            try await owner.session.perform { lease in try await lease.validate() }
            let writes = await counter.value
            guard writes == (mode == .prepare ? 3 : 0) else { throw Failure.receipt }
            let observation = NativeCustomTypeObservation(contract: Self.contract, phase: mode.rawValue,
                seed: seed, nativeWritesThisProcess: writes,
                ownerGeneration: owner.session.generation.uuidString,
                engineStartedAt: owner.session.engineStartedAt,
                processID: ProcessInfo.processInfo.processIdentifier)
            guard let value = String(data: try Self.encoded(observation), encoding: .utf8) else { throw Failure.receipt }
            accessibilityValue = "ready|" + value
        } catch {
            // Do not expose an HTTP error, credential or an account payload.
            accessibilityValue = "failed|" + String(reflecting: type(of: error))
        }
    }

    private func waitForOwner(_ application: AnyNativeApplication) async throws -> AnyNativeWorkspaceOwner {
        let clock = ContinuousClock(), deadline = ContinuousClock.now + .seconds(120)
        while clock.now < deadline {
            try Task.checkCancellation()
            if let owner = await application.currentWorkspace() { return owner }
            try await Task.sleep(for: .milliseconds(200))
        }
        throw Failure.ownerDeadline
    }

    private nonisolated static func prepare(owner: AnyNativeWorkspaceOwner, scope: UUID, attempt: UUID,
                                           counter: NativeCustomTypeWriteCounter) async throws -> NativeCustomTypeSeed {
        let suffix = String(scope.uuidString.prefix(8)), token = scope.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
        let typeName = "UI canonical Type " + suffix, propertyName = "UI custom value " + suffix
        let typeKey = "ui_custom_type_" + token, propertyKey = "ui_custom_value_" + token
        let client = owner.client, path = ["v1", "spaces", owner.workspace.spaceID]
        let seed = try await owner.session.perform { lease in
            try await lease.validate()
            let initialCatalog = try await client.requestJSON(method: "GET", path: path + ["types"],
                query: ["includeHidden": "true"], authorize: { try await lease.validate() })
            guard let types = initialCatalog["types"]?.array, types.count <= 512,
                  types.filter({ $0["id"]?.string == "page" }).count == 1,
                  let pageName = types.first(where: { $0["id"]?.string == "page" })?["name"]?.string,
                  !pageName.isEmpty, pageName != typeName else { throw Failure.nativeDefinition }
            try await counter.beforeNativeWrite()
            let created = try await client.requestJSON(method: "POST", path: path + ["types"],
                body: .object(["name": .string(typeName), "xKey": .string(typeKey)]),
                authorize: { try await lease.validate() })
            let typeID = try created.requireString("typeId")
            guard validID(typeID), typeID != "page" else { throw Failure.nativeDefinition }
            try await counter.beforeNativeWrite()
            _ = try await client.requestJSON(method: "POST", path: path + ["types", typeID, "parts"],
                body: .object(["key": .string("body"),
                    "datasets": .array([.object(["module": .string("editor")])])]),
                authorize: { try await lease.validate() })
            try await counter.beforeNativeWrite()
            let property = try await client.requestJSON(method: "POST",
                path: path + ["types", typeID, "properties"],
                body: .object(["name": .string(propertyName), "xKey": .string(propertyKey),
                    "kind": .string("string"), "scope": .string("synced")]),
                authorize: { try await lease.validate() })
            let propertyID = try property.requireString("propId")
            guard validID(propertyID) else { throw Failure.nativeDefinition }
            let seed = NativeCustomTypeSeed(contract: contract, scopeUUID: scope.uuidString,
                attemptUUID: attempt.uuidString, accountID: lease.workspace.accountID, spaceID: lease.workspace.spaceID,
                ownerGeneration: lease.generation.uuidString, engineStartedAt: lease.engineStartedAt,
                processID: ProcessInfo.processInfo.processIdentifier, typeID: typeID, typeName: typeName,
                typeKey: typeKey, pageTypeName: pageName,
                propertyID: propertyID, propertyName: propertyName, propertyKey: propertyKey,
                canonicalEditorDataset: "editor_blocks", eligible: true, nativeWrites: 3,
                documentWrites: 0, bodyWrites: 0, membershipWrites: 0)
            try await lease.validate()
            return seed
        }
        try await audit(seed, owner: owner)
        return seed
    }

    /// GET-only audit is used both after setup and in the fresh cold process.
    /// It has no counter/write closure and cannot allocate or repair a Type.
    private nonisolated static func audit(_ seed: NativeCustomTypeSeed,
                                         owner: AnyNativeWorkspaceOwner) async throws {
        let client = owner.client, path = ["v1", "spaces", owner.workspace.spaceID]
        try await owner.session.perform { lease in
            try await lease.validate()
            let catalog = try await client.requestJSON(method: "GET", path: path + ["types"],
                query: ["includeHidden": "true"], authorize: { try await lease.validate() })
            guard let types = catalog["types"]?.array, types.count <= 512,
                  types.filter({ $0["id"]?.string == "page" }).count == 1,
                  types.first(where: { $0["id"]?.string == "page" })?["name"]?.string == seed.pageTypeName,
                  types.filter({ $0["id"]?.string == seed.typeID }).count == 1,
                  let type = types.first(where: { $0["id"]?.string == seed.typeID }),
                  type["name"]?.string == seed.typeName, type["xKey"]?.string == seed.typeKey,
                  type["builtIn"]?.bool != true, type["hidden"]?.bool != true else { throw Failure.nativeDefinition }
            let policy = try await client.requestJSON(method: "GET",
                path: path + ["pinkha", "document-types", seed.typeID], authorize: { try await lease.validate() })
            guard policy["eligible"] == .bool(true),
                  policy["canonicalEditorDataset"] == .string("editor_blocks") else { throw Failure.nativeDefinition }
            let properties = try await client.requestJSON(method: "GET",
                path: path + ["types", seed.typeID, "properties"], authorize: { try await lease.validate() })
            guard let definitions = properties["properties"]?.array, definitions.count <= 4096,
                  definitions.filter({ $0["id"]?.string == seed.propertyID }).count == 1,
                  let definition = definitions.first(where: { $0["id"]?.string == seed.propertyID }),
                  definition["name"]?.string == seed.propertyName, definition["xKey"]?.string == seed.propertyKey,
                  definition["kind"]?.string == "string", definition["scope"]?.string == "synced" else {
                throw Failure.nativeDefinition
            }
            try await lease.validate()
        }
    }

    private nonisolated static func validate(_ seed: NativeCustomTypeSeed, scope: UUID,
                                             owner: AnyNativeWorkspaceOwner) throws {
        let suffix = String(scope.uuidString.prefix(8)), token = scope.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
        guard seed.contract == contract, seed.scopeUUID == scope.uuidString,
              UUID(uuidString: seed.attemptUUID) != nil, seed.accountID == owner.workspace.accountID,
              seed.spaceID == owner.workspace.spaceID, validID(seed.typeID), seed.typeID != "page",
              validID(seed.propertyID), seed.typeName == "UI canonical Type " + suffix,
              !seed.pageTypeName.isEmpty, seed.pageTypeName != seed.typeName,
              seed.propertyName == "UI custom value " + suffix,
              seed.typeKey == "ui_custom_type_" + token, seed.propertyKey == "ui_custom_value_" + token,
              seed.eligible, seed.canonicalEditorDataset == "editor_blocks", seed.nativeWrites == 3,
              seed.documentWrites == 0, seed.bodyWrites == 0, seed.membershipWrites == 0 else { throw Failure.receipt }
    }

    private nonisolated static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && !value.contains("\0") && value != "." && value != ".."
    }

    private nonisolated static func encoded<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(value)
        guard data.count <= 32_768 else { throw Failure.receipt }
        return data
    }

    private nonisolated static func boundedFile(_ path: URL, directory: URL) throws -> Data {
        guard path.deletingLastPathComponent().standardizedFileURL == directory.standardizedFileURL,
              path.resolvingSymlinksInPath().deletingLastPathComponent() == directory.resolvingSymlinksInPath(),
              try directory.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink == false else {
            throw Failure.receipt
        }
        let values = try path.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard values.isRegularFile == true, values.isSymbolicLink == false,
              let count = values.fileSize, count > 0, count <= 32_768 else {
            throw Failure.receipt
        }
        return try Data(contentsOf: path)
    }
}

private actor NativeCustomTypeWriteCounter {
    private let writesAllowed: Bool
    private(set) var value = 0
    init(writesAllowed: Bool) { self.writesAllowed = writesAllowed }
    func beforeNativeWrite() throws {
        guard writesAllowed, value < 3 else { throw NativeCustomTypeFixture.Failure.receipt }
        value += 1
    }
}

private struct NativeCustomTypeAttempt: Codable, Sendable {
    let contract, scopeUUID, attemptUUID, accountID, spaceID, ownerGeneration: String
}

private struct NativeCustomTypeSeed: Codable, Sendable {
    let contract, scopeUUID, attemptUUID, accountID, spaceID, ownerGeneration, engineStartedAt: String
    let processID: Int32
    let typeID, typeName, typeKey, pageTypeName, propertyID, propertyName, propertyKey, canonicalEditorDataset: String
    let eligible: Bool
    let nativeWrites, documentWrites, bodyWrites, membershipWrites: Int
}

private struct NativeCustomTypeObservation: Codable, Sendable {
    let contract, phase: String
    let seed: NativeCustomTypeSeed
    let nativeWritesThisProcess: Int
    let ownerGeneration, engineStartedAt: String
    let processID: Int32
}
#endif

// BEGIN_NATIVE_BOOKMARK_MOUNTED_FIXTURE_V1
#if DEBUG
import CryptoKit

/// Installs only synthetic definitions in the UI-created, disposable Space.
/// The real Library owns frame acquisition, object creation and every edit.
@MainActor @Observable
final class NativeBookmarkFixture {
    nonisolated static let contract = "pinkha-native-bookmark-mounted-fixture-v1"
    nonisolated static let createFlag = "--native-ui-bookmark-fixture-v1"
    nonisolated static let auditFlag = "--native-ui-bookmark-audit-v1"
    nonisolated static let phases = ["baseline", "cancelled", "created", "edited", "returned"]
    enum Mode: String, Sendable { case prepare, cold }
    enum Failure: Error { case scope, existingAttempt, ownerDeadline, ownerChanged, definition, census, object, receipt }

    private(set) var accessibilityValue = "waiting"
    private(set) var isReading = false
    private let scope: UUID
    private let directory: URL
    private let mode: Mode
    private let attempt = UUID()
    private let counter: NativeBookmarkWriteCounter
    private var started = false
    private var failed = false
    private var nextPhase = 0
    private var seed: NativeBookmarkSeed?
    private var previous: NativeBookmarkObservation?
    private var previousBytes: Data?
    private var baseline: NativeBookmarkReadback?

    var canReadNext: Bool {
        mode == .prepare && seed != nil && !failed && !isReading && nextPhase < Self.phases.count
    }

    private init(scope: UUID, directory: URL, mode: Mode) {
        self.scope = scope; self.directory = directory; self.mode = mode
        counter = .init(writesAllowed: mode == .prepare)
    }

    static func configured(arguments: [String], dataDirectory: URL,
                           credentialService: String) throws -> NativeBookmarkFixture? {
        let prepare = arguments.filter { $0 == createFlag }.count
        let audit = arguments.filter { $0 == auditFlag }.count
        guard prepare + audit != 0 else { return nil }
        guard prepare + audit == 1,
              !arguments.contains(NativeCustomTypeFixture.createFlag),
              !arguments.contains(NativeCustomTypeFixture.auditFlag),
              arguments.filter({ $0 == "--native-ui-tests" }).count == 1,
              arguments.filter({ $0 == "--native-ui-test-scope" }).count == 1,
              let index = arguments.firstIndex(of: "--native-ui-test-scope"), index + 1 < arguments.count,
              let scope = UUID(uuidString: arguments[index + 1]), arguments[index + 1] == scope.uuidString,
              credentialService == "io.pinkha.anynative.uitests." + scope.uuidString else { throw Failure.scope }
        let temporary = FileManager.default.temporaryDirectory
        guard dataDirectory.standardizedFileURL == temporary.appendingPathComponent("native-ui-" + scope.uuidString).standardizedFileURL else {
            throw Failure.scope
        }
        return .init(scope: scope, directory: temporary.appendingPathComponent("native-ui-bookmark-" + scope.uuidString),
                     mode: prepare == 1 ? .prepare : .cold)
    }

    /// One invocation, including failure. Cold mode cannot enter preparation.
    func run(application: AnyNativeApplication) async {
        guard !started else { return }
        started = true; isReading = true; accessibilityValue = "running|" + mode.rawValue
        defer { isReading = false }
        do {
            let owner = try await waitForOwner(application)
            try await requireScope(owner, application: application)
            let value: NativeBookmarkSeed
            if mode == .prepare {
                guard !FileManager.default.fileExists(atPath: directory.path) else { throw Failure.existingAttempt }
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
                let marker = NativeBookmarkAttempt(contract: Self.contract, scopeUUID: scope.uuidString,
                    attemptUUID: attempt.uuidString, accountID: owner.workspace.accountID,
                    spaceID: owner.workspace.spaceID, ownerGeneration: owner.session.generation.uuidString,
                    processID: ProcessInfo.processInfo.processIdentifier)
                try Self.encoded(marker).write(to: directory.appendingPathComponent("attempt.json"), options: .withoutOverwriting)
                let definitions = try await Self.prepareDefinitions(owner: owner, scope: scope, counter: counter)
                let definitionsHash = try await Self.auditDefinitions(definitions, owner: owner)
                guard await counter.value == 5 else { throw Failure.receipt }
                value = .init(contract: Self.contract, scopeUUID: scope.uuidString, attemptUUID: attempt.uuidString,
                    accountID: owner.workspace.accountID, spaceID: owner.workspace.spaceID,
                    ownerGeneration: owner.session.generation.uuidString, engineStartedAt: owner.session.engineStartedAt,
                    processID: ProcessInfo.processInfo.processIdentifier, definitions: definitions,
                    definitionsSHA256: definitionsHash, syntheticInstalledDefinitions: true,
                    fixtureDefinitionWrites: 5, fixtureObjectWrites: 0, fixtureBodyWrites: 0, fixtureMembershipWrites: 0)
                try await requireCurrent(owner, application: application)
                try Self.encoded(value).write(to: directory.appendingPathComponent("seed.json"), options: .withoutOverwriting)
                seed = value
                try await publish(phase: "prepare", seed: value, readback: nil, owner: owner, application: application)
            } else {
                value = try JSONDecoder().decode(NativeBookmarkSeed.self, from: Self.boundedFile("seed.json", directory: directory))
                let marker = try JSONDecoder().decode(NativeBookmarkAttempt.self, from: Self.boundedFile("attempt.json", directory: directory))
                try Self.validate(value, scope: scope, owner: owner)
                guard marker.contract == value.contract, marker.scopeUUID == value.scopeUUID,
                      marker.attemptUUID == value.attemptUUID, marker.accountID == value.accountID,
                      marker.spaceID == value.spaceID, marker.ownerGeneration == value.ownerGeneration,
                      marker.processID == value.processID else { throw Failure.receipt }
                // Read every original checkpoint and its hash chain. Never repair it.
                var prior: Data?
                var warm: NativeBookmarkObservation?
                for phase in ["prepare"] + Self.phases {
                    let bytes = try Self.boundedFile(phase + ".json", directory: directory)
                    let observation = try JSONDecoder().decode(NativeBookmarkObservation.self, from: bytes)
                    guard observation.contract == Self.contract, observation.phase == phase,
                          try Self.encoded(observation.seed) == Self.encoded(value),
                          observation.nativeDefinitionWritesThisProcess == 5,
                          observation.processID == value.processID,
                          observation.previousObservationSHA256 == prior.map(Self.digest) else { throw Failure.receipt }
                    if phase == "baseline" { baseline = observation.readback }
                    if phase != "prepare" {
                        guard let readback = observation.readback else { throw Failure.receipt }
                        try Self.validateTransition(phase: phase, seed: value, readback: readback,
                                                    baseline: baseline, previous: warm?.readback)
                    } else if observation.readback != nil { throw Failure.receipt }
                    prior = bytes; warm = observation
                }
                guard let warm, let prior, let baseline, let original = warm.readback?.document,
                      warm.phase == "returned", value.processID != ProcessInfo.processInfo.processIdentifier,
                      warm.ownerGeneration != owner.session.generation.uuidString,
                      value.ownerGeneration != owner.session.generation.uuidString,
                      await counter.value == 0 else { throw Failure.ownerChanged }
                seed = value; previous = warm; previousBytes = prior
                let readback = try await Self.readback(value, owner: owner, baseline: baseline,
                                                       objectID: original.objectID, includeDocument: true)
                try Self.validateTransition(phase: "cold", seed: value, readback: readback,
                                            baseline: baseline, previous: warm.readback)
                try await publish(phase: "cold", seed: value, readback: readback, owner: owner, application: application)
            }
        } catch { await retainFailure(error, phase: mode.rawValue) }
    }

    /// Fixed read-only checkpoints, triggered after actual UI transitions.
    /// POSTs below are only native query reads, never create/frame requests.
    func readNext(application: AnyNativeApplication) async {
        guard canReadNext, let seed else { return }
        let phase = Self.phases[nextPhase]
        nextPhase += 1; isReading = true; accessibilityValue = "running|" + phase
        defer { isReading = false }
        do {
            guard let owner = await application.currentWorkspace() else { throw Failure.ownerChanged }
            try await requireScope(owner, application: application)
            try Self.validate(seed, scope: scope, owner: owner)
            guard seed.processID == ProcessInfo.processInfo.processIdentifier else { throw Failure.ownerChanged }
            let readback = try await Self.readback(seed, owner: owner, baseline: baseline,
                objectID: previous?.readback?.document?.objectID,
                includeDocument: ["created", "edited", "returned"].contains(phase))
            if phase == "baseline" { baseline = readback }
            try Self.validateTransition(phase: phase, seed: seed, readback: readback,
                                        baseline: baseline, previous: previous?.readback)
            try await publish(phase: phase, seed: seed, readback: readback, owner: owner, application: application)
        } catch { await retainFailure(error, phase: phase) }
    }

    private func publish(phase: String, seed: NativeBookmarkSeed, readback: NativeBookmarkReadback?,
                         owner: AnyNativeWorkspaceOwner, application: AnyNativeApplication) async throws {
        try await requireCurrent(owner, application: application)
        let writes = await counter.value
        guard writes == (mode == .prepare ? 5 : 0) else { throw Failure.receipt }
        let observation = NativeBookmarkObservation(contract: Self.contract, phase: phase, seed: seed,
            readback: readback, nativeDefinitionWritesThisProcess: writes,
            ownerGeneration: owner.session.generation.uuidString, engineStartedAt: owner.session.engineStartedAt,
            processID: ProcessInfo.processInfo.processIdentifier,
            previousObservationSHA256: previousBytes.map(Self.digest))
        let bytes = try Self.encoded(observation)
        try bytes.write(to: directory.appendingPathComponent(phase + ".json"), options: .withoutOverwriting)
        try await requireCurrent(owner, application: application)
        guard let text = String(data: bytes, encoding: .utf8) else { throw Failure.receipt }
        previous = observation; previousBytes = bytes; accessibilityValue = "ready|" + text
    }

    private func retainFailure(_ error: Error, phase: String) async {
        failed = true
        let category = (error as? Failure).map { String(describing: $0) } ?? String(reflecting: type(of: error))
        let failure = NativeBookmarkFailure(contract: Self.contract, phase: phase, scopeUUID: scope.uuidString,
            category: category, processID: ProcessInfo.processInfo.processIdentifier,
            nativeDefinitionWritesThisProcess: await counter.value)
        // Best-effort private evidence, never overwrite or expose an HTTP body.
        if let bytes = try? Self.encoded(failure) {
            try? bytes.write(to: directory.appendingPathComponent("failure-" + mode.rawValue + ".json"), options: .withoutOverwriting)
        }
        accessibilityValue = "failed|" + phase + "|" + category
    }

    private func waitForOwner(_ application: AnyNativeApplication) async throws -> AnyNativeWorkspaceOwner {
        let clock = ContinuousClock(), deadline = ContinuousClock.now + .seconds(120)
        while clock.now < deadline {
            try Task.checkCancellation()
            if let owner = await application.currentWorkspace() { return owner }
            try await Task.sleep(for: .milliseconds(200))
        }
        throw Failure.ownerDeadline
    }

    private func requireScope(_ owner: AnyNativeWorkspaceOwner, application: AnyNativeApplication) async throws {
        let spaces = try await application.listSpaces()
        guard spaces.contains(where: { $0.id == owner.workspace.spaceID &&
            $0.name == "Bookmark UI Space " + String(scope.uuidString.prefix(8)) && $0.ownRole == "owner" }),
            await application.currentAccount()?.id == owner.workspace.accountID else { throw Failure.scope }
        try await requireCurrent(owner, application: application)
    }

    private func requireCurrent(_ owner: AnyNativeWorkspaceOwner, application: AnyNativeApplication) async throws {
        guard let current = await application.currentWorkspace(), current.session === owner.session else { throw Failure.ownerChanged }
        try await owner.session.perform { lease in try await lease.validate() }
    }

    private nonisolated static func prepareDefinitions(owner: AnyNativeWorkspaceOwner, scope: UUID,
                                                       counter: NativeBookmarkWriteCounter) async throws -> NativeBookmarkDefinitions {
        let suffix = String(scope.uuidString.prefix(8))
        let token = scope.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
        let typeName = "UI synthetic Bookmark " + suffix, typeKey = "ui_bookmark_" + token
        let ownerName = "UI Bookmark URL owner " + suffix, ownerKey = "ui_bookmark_url_" + token
        let sourceObjectID = "ui-synthetic-source-definition-" + token
        let client = owner.client, base = ["v1", "spaces", owner.workspace.spaceID]
        return try await owner.session.perform { lease in
            try await lease.validate()
            try await counter.beforeNativeWrite()
            let type = try await client.requestJSONResponse(method: "POST", path: base + ["types"],
                body: .object(["name": .string(typeName), "xKey": .string(typeKey), "layout": .object(["type": .string("page")])]),
                validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
            guard type.statusCode == 201 else { throw Failure.definition }
            let typeID = try type.body.requireString("typeId")
            guard validID(typeID), typeID != "page" else { throw Failure.definition }
            try await counter.beforeNativeWrite()
            let part = try await client.requestJSONResponse(method: "POST", path: base + ["types", typeID, "parts"],
                body: .object(["key": .string("editor"), "name": .string("editor"),
                    "datasets": .array([.object(["module": .string("editor")])])]),
                validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
            guard part.statusCode == 201 else { throw Failure.definition }
            let partID = try part.body.requireString("partId")
            try await counter.beforeNativeWrite()
            let collection = try await client.requestJSONResponse(method: "POST", path: base + ["collections"],
                body: .object(["name": .string(ownerName), "xKey": .string(ownerKey)]),
                validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
            guard collection.statusCode == 201 else { throw Failure.definition }
            let ownerID = try collection.body.requireString("collectionId")
            guard validID(partID), validID(ownerID), ownerID != typeID else { throw Failure.definition }
            try await counter.beforeNativeWrite()
            let property = try await client.requestJSONResponse(method: "POST", path: base + ["collections", ownerID, "properties"],
                body: .object(["name": .string("Source"), "kind": .string("string"), "scope": .string("synced"),
                    "xFormat": .object(["type": .string("url"), "pinkhaHeart": .object([
                        "sourceObjectID": .string(sourceObjectID), "sourceUniqueKey": .string("rel-source"), "relationKey": .string("source")])])]),
                validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
            guard property.statusCode == 201 else { throw Failure.definition }
            let propertyID = try property.body.requireString("propId")
            guard validID(propertyID) else { throw Failure.definition }
            try await counter.beforeNativeWrite()
            let layout = try await client.requestJSONResponse(method: "PATCH", path: base + ["types", typeID],
                body: .object(["layout": .object(["type": .string("bookmark"), "config": .object(["pinkhaHeart": .object([
                    "contract": .string("pinkha-heart-native-bookmark-presentation-v1"), "sourceRecommendedLayout": .integer(11),
                    "propertyOwnerId": .string(ownerID),
                    "sourceURL": .object(["ownerId": .string(ownerID), "propertyId": .string(propertyID)]),
                    "recommended": .array([.object(["ownerId": .string(ownerID), "propertyId": .string(propertyID)])]),
                    "featured": .array([]), "hidden": .array([]), "files": .array([])])])])]),
                validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
            guard layout.statusCode == 204, layout.body == .null else { throw Failure.definition }
            try await lease.validate()
            return .init(typeID: typeID, typeName: typeName, typeKey: typeKey, partID: partID,
                propertyOwnerID: ownerID, propertyOwnerName: ownerName, propertyOwnerKey: ownerKey,
                propertyID: propertyID, sourceObjectID: sourceObjectID,
                acknowledgedStatuses: [type.statusCode, part.statusCode, collection.statusCode, property.statusCode, layout.statusCode])
        }
    }

    private nonisolated static func auditDefinitions(_ value: NativeBookmarkDefinitions,
                                                      owner: AnyNativeWorkspaceOwner) async throws -> String {
        let client = owner.client, base = ["v1", "spaces", owner.workspace.spaceID]
        return try await owner.session.perform { lease in
            let types = try await client.requestJSON(method: "GET", path: base + ["types"], query: ["includeHidden": "true"],
                maximumResponseBytes: 1_048_576, authorize: { try await lease.validate() })
            guard let rows = types["types"]?.array, rows.count <= 512,
                  rows.filter({ $0["id"]?.string == value.typeID }).count == 1,
                  let type = rows.first(where: { $0["id"]?.string == value.typeID }),
                  type["name"]?.string == value.typeName, type["xKey"]?.string == value.typeKey,
                  type["builtIn"]?.bool != true, type["hidden"]?.bool != true,
                  type["layout"]?["type"]?.string == "bookmark",
                  let descriptor = type["layout"]?["config"]?["pinkhaHeart"],
                  descriptor["contract"]?.string == "pinkha-heart-native-bookmark-presentation-v1",
                  descriptor["sourceRecommendedLayout"]?.integer == 11,
                  descriptor["propertyOwnerId"]?.string == value.propertyOwnerID,
                  let address = descriptor["sourceURL"], address["ownerId"]?.string == value.propertyOwnerID,
                  address["propertyId"]?.string == value.propertyID,
                  descriptor["recommended"]?.array == [address], descriptor["featured"]?.array?.isEmpty == true,
                  descriptor["hidden"]?.array?.isEmpty == true, descriptor["files"]?.array?.isEmpty == true else { throw Failure.definition }
            let policy = try await client.requestJSON(method: "GET", path: base + ["pinkha", "document-types", value.typeID],
                authorize: { try await lease.validate() })
            guard policy["eligible"]?.bool == true, policy["canonicalEditorDataset"]?.string == "editor_blocks" else { throw Failure.definition }
            let collection = try await client.requestJSON(method: "GET", path: base + ["collections", value.propertyOwnerID],
                authorize: { try await lease.validate() })
            guard collection["id"]?.string == value.propertyOwnerID, collection["name"]?.string == value.propertyOwnerName,
                  collection["xKey"]?.string == value.propertyOwnerKey, collection["builtIn"]?.bool != true else { throw Failure.definition }
            let properties = try await client.requestJSON(method: "GET", path: base + ["collections", value.propertyOwnerID, "properties"],
                maximumResponseBytes: 1_048_576, authorize: { try await lease.validate() })
            guard let definitions = properties["properties"]?.array, definitions.count <= 128,
                  definitions.filter({ $0["id"]?.string == value.propertyID }).count == 1,
                  let property = definitions.first(where: { $0["id"]?.string == value.propertyID }),
                  property["name"]?.string == "Source", property["kind"]?.string == "string", property["scope"]?.string == "synced",
                  property["invalid"]?.bool != true, property["xFormat"]?["type"]?.string == "url",
                  property["xFormat"]?["pinkhaHeart"]?["sourceObjectID"]?.string == value.sourceObjectID,
                  property["xFormat"]?["pinkhaHeart"]?["sourceUniqueKey"]?.string == "rel-source",
                  property["xFormat"]?["pinkhaHeart"]?["relationKey"]?.string == "source" else { throw Failure.definition }
            try await lease.validate()
            // Hash decoded native definition JSON, not a fabricated frame or HTTP-wire claim.
            return digest(try encoded([type, collection, property], maximum: 1_048_576))
        }
    }

    private nonisolated static func readback(_ seed: NativeBookmarkSeed, owner: AnyNativeWorkspaceOwner,
                                             baseline: NativeBookmarkReadback?, objectID: String?,
                                             includeDocument: Bool) async throws -> NativeBookmarkReadback {
        guard try await auditDefinitions(seed.definitions, owner: owner) == seed.definitionsSHA256 else { throw Failure.definition }
        let client = owner.client, base = ["v1", "spaces", owner.workspace.spaceID]
        return try await owner.session.perform { lease in
            let member = try await client.requestJSON(method: "GET", path: base + ["members", "me"], authorize: { try await lease.validate() })
            guard member["identity"]?.string == seed.accountID, member["status"]?.string == "active",
                  member["permission"]?.string == "owner" else { throw Failure.ownerChanged }
            let bundle = try await client.requestJSON(method: "GET", path: base + ["bundles", "system:wiki/v1"], authorize: { try await lease.validate() })
            guard bundle["bundle"]?["id"]?.string == "system:wiki/v1", bundle["bundle"]?["losers"]?.array?.isEmpty != false,
                  let libraryID = bundle["bundle"]?["rootId"]?.string, validID(libraryID), libraryID != seed.definitions.propertyOwnerID else {
                throw Failure.census
            }
            let library = try await client.requestJSON(method: "GET", path: base + ["collections", libraryID], authorize: { try await lease.validate() })
            guard library["id"]?.string == libraryID, library["xKey"]?.string == "wiki" else { throw Failure.census }
            // Complete bounded census: never accept a partial page. This fresh
            // Space case deliberately refuses larger/paginated Spaces.
            let query = try await client.requestJSON(method: "POST", path: base + ["objects", "query"],
                body: .object(["sort": .array([.string("id")]), "limit": .integer(129), "includeTotal": .bool(true)]),
                maximumResponseBytes: 1_048_576, validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
            guard let records = query["records"]?.array, records.count <= 128,
                  query["total"]?.integer == Int64(records.count), query["hasNext"]?.bool == false else { throw Failure.census }
            var census: [NativeBookmarkCensusRow] = [], seen = Set<String>()
            for record in records {
                guard let id = record["id"]?.string, validID(id), seen.insert(id).inserted,
                      record["spaceId"]?.string == seed.spaceID else { throw Failure.census }
                census.append(.init(objectID: id, decodedRecordSHA256: digest(try encoded(record, maximum: 1_048_576))))
            }
            census.sort { $0.objectID.utf8.lexicographicallyPrecedes($1.objectID.utf8) }
            var document: NativeBookmarkDocument?
            if includeDocument {
                guard let baseline, baseline.libraryCollectionID == libraryID else { throw Failure.census }
                let oldIDs = Set(baseline.census.map(\.objectID))
                let added = census.map(\.objectID).filter { !oldIDs.contains($0) }
                guard added.count == 1, let selected = added.first,
                      objectID == nil || objectID == selected else { throw Failure.object }
                let response = try await client.requestJSON(method: "GET", path: base + ["properties", selected],
                    maximumResponseBytes: 1_048_576, authorize: { try await lease.validate() })
                let definitions = seed.definitions
                guard let raw = response["record"], raw["id"]?.string == selected, raw["spaceId"]?.string == seed.spaceID,
                      let name = raw["any"]?["name"]?.string, name.utf8.count <= 8192,
                      raw["any"]?["type"]?.string == definitions.typeID,
                      let url = raw[definitions.propertyOwnerID]?[definitions.propertyID]?.string, url.utf8.count <= 8192,
                      let membership = raw["any"]?["collections"]?.array, membership.allSatisfy({ $0.string != nil }),
                      let version = raw["_ver"], version.object != nil else { throw Failure.object }
                let collections = membership.compactMap(\.string)
                let expectedCollections = [libraryID, definitions.propertyOwnerID].sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }
                guard collections.count == 2, collections.allSatisfy(validID),
                      try encoded(collections.sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }) == encoded(expectedCollections) else {
                    throw Failure.object
                }
                let rows = try await client.requestJSON(method: "POST", path: base + ["query"],
                    body: .object(["objectId": .string(selected), "dataset": .string("editor_blocks"),
                        "sort": .array([.string("nav.pos")]), "limit": .integer(1), "includeTotal": .bool(true)]),
                    validateResponse: { try await lease.validate() }, authorize: { try await lease.validate() })
                guard let empty = rows["records"]?.array, empty.isEmpty, rows["total"]?.integer == 0,
                      rows["hasNext"]?.bool == false else { throw Failure.object }
                let target = try await client.requestJSON(method: "GET", path: base + ["pinkha", "document-targets", selected], authorize: { try await lease.validate() })
                guard target["spaceId"]?.string == seed.spaceID, target["objectId"]?.string == selected,
                      target["typeId"]?.string == definitions.typeID, target["collections"]?.array == membership,
                      target["eligible"]?.bool == true, target["canWrite"]?.bool == true,
                      target["canonicalEditorDataset"]?.string == "editor_blocks", target["policy"]?.string == "canonical-editor-module-v1" else {
                    throw Failure.object
                }
                let markdownPath = base + ["objects", selected, "editor", "editor_blocks", "markdown"]
                let markdown = try await client.requestJSON(method: "GET", path: markdownPath, authorize: { try await lease.validate() })
                let repeated = try await client.requestJSON(method: "GET", path: markdownPath, authorize: { try await lease.validate() })
                guard let content = markdown["content"]?.string, content.utf8.isEmpty,
                      let bodyVersion = markdown["version"]?.string, !bodyVersion.isEmpty,
                      try encoded(markdown) == encoded(repeated) else { throw Failure.object }
                document = .init(objectID: selected, typeID: definitions.typeID, propertyOwnerID: definitions.propertyOwnerID,
                    sourcePropertyID: definitions.propertyID, collections: collections, rawName: name, rawSourceURL: url,
                    nameUTF8: Array(name.utf8), sourceURLUTF8: Array(url.utf8),
                    decodedRecordSHA256: digest(try encoded(raw, maximum: 1_048_576)),
                    objectVersionSHA256: digest(try encoded(version)),
                    markdownSHA256: digest(try encoded(markdown)), markdownVersion: bodyVersion,
                    markdownUTF8: Array(content.utf8), editorRows: empty.count, editorTotal: 0, editorHasNext: false)
            }
            try await lease.validate()
            return .init(libraryCollectionID: libraryID, census: census, total: census.count, hasNext: false,
                         memberIdentity: seed.accountID, memberStatus: "active", memberPermission: "owner", document: document)
        }
    }

    private nonisolated static func validateTransition(phase: String, seed: NativeBookmarkSeed,
                                                       readback: NativeBookmarkReadback, baseline: NativeBookmarkReadback?,
                                                       previous: NativeBookmarkReadback?) throws {
        guard let baseline, readback.libraryCollectionID == baseline.libraryCollectionID,
              readback.total == readback.census.count, !readback.hasNext,
              readback.memberIdentity == seed.accountID, readback.memberStatus == "active", readback.memberPermission == "owner" else {
            throw Failure.receipt
        }
        if phase == "baseline" || phase == "cancelled" {
            guard readback.document == nil, try encoded(readback) == encoded(baseline) else { throw Failure.census }
            return
        }
        guard readback.census.count == baseline.census.count + 1,
              baseline.census.allSatisfy({ old in readback.census.contains { $0.objectID == old.objectID && $0.decodedRecordSHA256 == old.decodedRecordSHA256 } }),
              let document = readback.document, document.typeID == seed.definitions.typeID,
              document.propertyOwnerID == seed.definitions.propertyOwnerID, document.sourcePropertyID == seed.definitions.propertyID,
              document.nameUTF8 == Array(document.rawName.utf8), document.sourceURLUTF8 == Array(document.rawSourceURL.utf8),
              document.editorRows == 0, document.editorTotal == 0, !document.editorHasNext, document.markdownUTF8.isEmpty else { throw Failure.object }
        let initialURL = "https://example.com/?pinkha_bookmark=" + seed.scopeUUID + "#created"
        let editedURL = "https://example.com/?pinkha_bookmark=" + seed.scopeUUID + "&stage=edited#native-source"
        let editedName = "Bookmark edited " + String(seed.scopeUUID.prefix(8))
        if phase == "created" {
            guard document.nameUTF8.isEmpty, document.sourceURLUTF8 == Array(initialURL.utf8) else { throw Failure.object }
        } else {
            guard document.nameUTF8 == Array(editedName.utf8), document.sourceURLUTF8 == Array(editedURL.utf8),
                  let prior = previous?.document, prior.objectID == document.objectID,
                  try encoded(prior.collections) == encoded(document.collections),
                  prior.markdownSHA256 == document.markdownSHA256 else { throw Failure.object }
            if phase == "returned" || phase == "cold" {
                guard let previous, try encoded(previous) == encoded(readback) else { throw Failure.object }
            } else if phase != "edited" { throw Failure.receipt }
        }
    }

    private nonisolated static func validate(_ seed: NativeBookmarkSeed, scope: UUID, owner: AnyNativeWorkspaceOwner) throws {
        let suffix = String(scope.uuidString.prefix(8)), token = scope.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
        let value = seed.definitions
        guard seed.contract == contract, seed.scopeUUID == scope.uuidString, UUID(uuidString: seed.attemptUUID) != nil,
              seed.accountID == owner.workspace.accountID, seed.spaceID == owner.workspace.spaceID,
              UUID(uuidString: seed.ownerGeneration) != nil, seed.processID > 0,
              [value.typeID, value.partID, value.propertyOwnerID, value.propertyID].allSatisfy(validID),
              value.typeID != "page", value.typeID != value.propertyOwnerID,
              value.typeName == "UI synthetic Bookmark " + suffix, value.typeKey == "ui_bookmark_" + token,
              value.propertyOwnerName == "UI Bookmark URL owner " + suffix, value.propertyOwnerKey == "ui_bookmark_url_" + token,
              value.sourceObjectID == "ui-synthetic-source-definition-" + token,
              value.acknowledgedStatuses == [201, 201, 201, 201, 204],
              seed.syntheticInstalledDefinitions, seed.fixtureDefinitionWrites == 5, seed.fixtureObjectWrites == 0,
              seed.fixtureBodyWrites == 0, seed.fixtureMembershipWrites == 0 else { throw Failure.receipt }
    }

    private nonisolated static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && value.utf8.allSatisfy { (33...126).contains($0) } && value != "." && value != ".."
    }
    private nonisolated static func digest(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
    private nonisolated static func encoded<T: Encodable>(_ value: T, maximum: Int = 32_768) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let bytes = try encoder.encode(value)
        guard !bytes.isEmpty, bytes.count <= maximum else { throw Failure.receipt }
        return bytes
    }
    private nonisolated static func boundedFile(_ name: String, directory: URL) throws -> Data {
        let path = directory.appendingPathComponent(name)
        guard path.deletingLastPathComponent().standardizedFileURL == directory.standardizedFileURL,
              path.resolvingSymlinksInPath().deletingLastPathComponent() == directory.resolvingSymlinksInPath(),
              try directory.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink == false else { throw Failure.receipt }
        let values = try path.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard values.isRegularFile == true, values.isSymbolicLink == false,
              let count = values.fileSize, count > 0, count <= 32_768 else { throw Failure.receipt }
        let bytes = try Data(contentsOf: path)
        guard bytes.count == count else { throw Failure.receipt }
        return bytes
    }
}

private actor NativeBookmarkWriteCounter {
    private let writesAllowed: Bool
    private(set) var value = 0
    init(writesAllowed: Bool) { self.writesAllowed = writesAllowed }
    func beforeNativeWrite() throws {
        guard writesAllowed, value < 5 else { throw NativeBookmarkFixture.Failure.receipt }
        value += 1
    }
}
private struct NativeBookmarkAttempt: Codable, Sendable {
    let contract, scopeUUID, attemptUUID, accountID, spaceID, ownerGeneration: String
    let processID: Int32
}
private struct NativeBookmarkDefinitions: Codable, Sendable {
    let typeID, typeName, typeKey, partID, propertyOwnerID, propertyOwnerName, propertyOwnerKey, propertyID, sourceObjectID: String
    let acknowledgedStatuses: [Int]
}
private struct NativeBookmarkSeed: Codable, Sendable {
    let contract, scopeUUID, attemptUUID, accountID, spaceID, ownerGeneration, engineStartedAt: String
    let processID: Int32
    let definitions: NativeBookmarkDefinitions
    let definitionsSHA256: String
    let syntheticInstalledDefinitions: Bool
    let fixtureDefinitionWrites, fixtureObjectWrites, fixtureBodyWrites, fixtureMembershipWrites: Int
}
private struct NativeBookmarkCensusRow: Codable, Sendable {
    let objectID, decodedRecordSHA256: String
}
private struct NativeBookmarkDocument: Codable, Sendable {
    let objectID, typeID, propertyOwnerID, sourcePropertyID: String
    let collections: [String]
    let rawName, rawSourceURL: String
    let nameUTF8, sourceURLUTF8: [UInt8]
    let decodedRecordSHA256, objectVersionSHA256, markdownSHA256, markdownVersion: String
    let markdownUTF8: [UInt8]
    let editorRows, editorTotal: Int
    let editorHasNext: Bool
}
private struct NativeBookmarkReadback: Codable, Sendable {
    let libraryCollectionID: String
    let census: [NativeBookmarkCensusRow]
    let total: Int
    let hasNext: Bool
    let memberIdentity, memberStatus, memberPermission: String
    let document: NativeBookmarkDocument?
}
private struct NativeBookmarkObservation: Codable, Sendable {
    let contract, phase: String
    let seed: NativeBookmarkSeed
    let readback: NativeBookmarkReadback?
    let nativeDefinitionWritesThisProcess: Int
    let ownerGeneration, engineStartedAt: String
    let processID: Int32
    let previousObservationSHA256: String?
}
private struct NativeBookmarkFailure: Codable, Sendable {
    let contract, phase, scopeUUID, category: String
    let processID: Int32
    let nativeDefinitionWritesThisProcess: Int
}
#endif
// END_NATIVE_BOOKMARK_MOUNTED_FIXTURE_V1
