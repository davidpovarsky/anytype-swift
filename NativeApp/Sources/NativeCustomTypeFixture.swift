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
