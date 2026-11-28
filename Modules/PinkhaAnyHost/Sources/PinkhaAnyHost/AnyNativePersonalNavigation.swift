import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativePersonalNavigationError: Error, Equatable, Sendable {
    case unavailableContract
    case invalidHome
    case invalidObject
    case invalidOpenedDate
    case intentAlreadyDispatched
    case sessionAttemptLimit
}

/// An explicit current preference. It is independent of the original imported
/// Heart homepage and never synthesizes a Page for a built-in context.
public enum AnyNativeHomeSelection: Equatable, Sendable {
    case empty
    case builtIn(BuiltIn)
    case object(String)

    public enum BuiltIn: String, CaseIterable, Sendable {
        case widgets, graph, lastOpened, chat
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        switch (lhs, rhs) {
        case (.empty, .empty): true
        case (.builtIn(let a), .builtIn(let b)): a == b
        case (.object(let a), .object(let b)): a.utf8.elementsEqual(b.utf8)
        default: false
        }
    }

    static let contract = "pinkha-current-home-v1"

    func wireValue() throws -> AnyJSON {
        if case .empty = self { return .string("") }
        let fields: [String: AnyJSON]
        switch self {
        case .empty: preconditionFailure("handled above")
        case .builtIn(let value):
            fields = ["contract": .string(Self.contract), "kind": .string("builtin"),
                      "value": .string(value.rawValue)]
        case .object(let id):
            guard AnyNativePersonalNavigationStore.validID(id) else {
                throw AnyNativePersonalNavigationError.invalidHome
            }
            fields = ["contract": .string(Self.contract), "kind": .string("object"),
                      "objectId": .string(id)]
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return .string(String(decoding: try encoder.encode(AnyJSON.object(fields)), as: UTF8.self))
    }

    static func decode(_ value: AnyJSON) -> Self? {
        guard let text = value.string, text.utf8.count <= 16_384 else { return nil }
        if text.isEmpty { return .empty }
        guard let fields = try? JSONDecoder().decode(AnyJSON.self, from: Data(text.utf8)).object,
              fields["contract"]?.string == Self.contract,
              let kind = fields["kind"]?.string else { return nil }
        switch kind {
        case "builtin":
            guard Set(fields.keys) == ["contract", "kind", "value"],
                  let raw = fields["value"]?.string,
                  let value = BuiltIn.allCases.first(where: { $0.rawValue.utf8.elementsEqual(raw.utf8) }) else { return nil }
            return .builtIn(value)
        case "object":
            guard Set(fields.keys) == ["contract", "kind", "objectId"],
                  let id = fields["objectId"]?.string,
                  AnyNativePersonalNavigationStore.validID(id) else { return nil }
            return .object(id)
        default: return nil
        }
    }
}

/// Missing, explicitly empty, and unrecognized native preferences stay
/// distinct. Unknown bytes are exposed for preservation, never as a route.
public enum AnyNativeHomeValue: Sendable {
    case absent
    case selection(AnyNativeHomeSelection)
    case unsupported(AnyJSON)

    static func project(_ raw: AnyJSON?) -> Self {
        guard let raw else { return .absent }
        if let selection = AnyNativeHomeSelection.decode(raw) { return .selection(selection) }
        return .unsupported(raw)
    }
}

public struct AnyNativeHomeSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let binding: AnyNativeAccountRunBinding
    public let rawValue: AnyJSON?
    public var value: AnyNativeHomeValue { .project(rawValue) }
}

public struct AnyNativeLastOpenedSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let binding: AnyNativeAccountRunBinding
    public let objectID: String
    /// The original JSON value is retained; absence is not Unix zero.
    public let rawValue: AnyJSON?
    /// Native datetime uses milliseconds. Imported source metadata is separate.
    public let unixMilliseconds: Int64?
}

public struct AnyPreparedNativeHomeSelection: Sendable {
    public let operationID: UUID
    public let selection: AnyNativeHomeSelection?
    let workspace: AnyTorahWorkspace
    let generation: UUID
    let binding: AnyNativeAccountRunBinding
}

public struct AnyPreparedNativeObjectOpen: Sendable {
    public let operationID: UUID
    public let objectID: String
    public let observedUnixSecond: Int64
    let workspace: AnyTorahWorkspace
    let generation: UUID
    let binding: AnyNativeAccountRunBinding
}

/// This contains only the caller's operation and ownership metadata, not a
/// private object value. The synchronous callback lets an owner retain a known
/// native acknowledgment before a later session check can reject its result.
/// The callback and this store's bounded ledger are not a durable journal.
public struct AnyNativeNavigationAcknowledgment: Sendable {
    public enum Kind: String, Sendable { case home, lastOpened }
    public let operationID: UUID
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let binding: AnyNativeAccountRunBinding
    public let kind: Kind
}

public enum AnyNativeNavigationReadback: Sendable {
    case verifiedCurrent
    case nativeAcknowledgedCurrentStateUnverified
}

public struct AnyNativeHomeWriteReceipt: Sendable {
    public let acknowledgment: AnyNativeNavigationAcknowledgment
    public let readback: AnyNativeNavigationReadback
    public let snapshot: AnyNativeHomeSnapshot?
}

public struct AnyNativeOpenReceipt: Sendable {
    public let acknowledgment: AnyNativeNavigationAcknowledgment
    public let readback: AnyNativeNavigationReadback
    public let snapshot: AnyNativeLastOpenedSnapshot?
}

/// Current Home is an account-private Space setting synchronized to the same
/// account's devices. Last-opened is an explicitly device-local native value.
/// Readers may use both, subject to current signed READ and live native rows.
/// Every mutation uses the new native expected-account/run routes. No legacy
/// fallback, automatic resend, Undo or cross-definition atomicity is implied.
public actor AnyNativePersonalNavigationStore {
    public static let homeSettingKey = "pinkhaHomeV1"
    public static let lastOpenedProperty = "pinkhaLastOpenedV1"
    public static let lastOpenedContract = "pinkha-last-opened-local-v1"

    public nonisolated let workspace: AnyTorahWorkspace
    public nonisolated let binding: AnyNativeAccountRunBinding
    private let client: AnyHTTPClient
    private var attempted: Set<UUID> = []
    private var acknowledgments: [UUID: AnyNativeNavigationAcknowledgment] = [:]
    private let attemptLimit = 256

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                binding: AnyNativeAccountRunBinding) throws {
        guard Self.same(client.expectedAccountID, workspace.accountID),
              Self.same(binding.accountID, workspace.accountID) else {
            throw AnyHostError.wrongWorkspace
        }
        self.client = client
        self.workspace = workspace
        self.binding = binding
    }

    /// Operation metadata remains available after an enclosing application
    /// session rejects delivery. It conveys no authority to read private data.
    public func acknowledgment(for operationID: UUID) -> AnyNativeNavigationAcknowledgment? {
        acknowledgments[operationID]
    }

    public func readHome(lease: AnyHostLease) async throws -> AnyNativeHomeSnapshot {
        try await currentRead(lease)
        // The original native API has GET SpaceInfo, not GET settings.
        let info = try await client.requestJSON(method: "GET", path: spacePath,
            maximumResponseBytes: 1_048_576, authorize: { try await lease.validate() })
        guard let id = info["id"]?.string, Self.same(id, workspace.spaceID),
              info["settings"] == nil || info["settings"]?.object != nil else {
            throw AnyNativePersonalNavigationError.unavailableContract
        }
        let raw = info["settings"]?[Self.homeSettingKey]
        try await currentRead(lease)
        return .init(workspace: workspace, generation: lease.generation,
                     binding: binding, rawValue: raw)
    }

    /// A stored object reference is revalidated before navigation. A deleted,
    /// trashed or unmaterialized destination is never treated as a Page.
    public func requireHomeDestination(_ snapshot: AnyNativeHomeSnapshot,
                                       lease: AnyHostLease) async throws -> AnyNativeHomeSelection? {
        try require(snapshot.workspace, snapshot.generation, snapshot.binding, lease: lease)
        try await currentRead(lease)
        guard case .selection(let selection) = snapshot.value else { return nil }
        if case .object(let id) = selection { _ = try await object(id, lease: lease) }
        try await currentRead(lease)
        return selection
    }

    /// nil means remove this one preference. .empty is an explicit empty
    /// preference. Neither operation manufactures a default homepage.
    public func prepareHome(_ selection: AnyNativeHomeSelection?,
                            lease: AnyHostLease) async throws -> AnyPreparedNativeHomeSelection {
        _ = try selection?.wireValue()
        try await currentRead(lease)
        if let selection, case .object(let id) = selection { _ = try await object(id, lease: lease) }
        try await currentRead(lease)
        return .init(operationID: UUID(), selection: selection, workspace: workspace,
                     generation: lease.generation, binding: binding)
    }

    public func commitHome(
        _ intent: AnyPreparedNativeHomeSelection, lease: AnyHostLease,
        onAcknowledged: @escaping @Sendable (AnyNativeNavigationAcknowledgment) -> Void
    ) async throws -> AnyNativeHomeWriteReceipt {
        try require(intent.workspace, intent.generation, intent.binding, lease: lease)
        try consume(intent.operationID)
        let body: AnyJSON
        if let selection = intent.selection {
            body = .object(["set": .object([Self.homeSettingKey: try selection.wireValue()])])
        } else {
            body = .object(["unset": .array([.string(Self.homeSettingKey)])])
        }
        try await currentRead(lease)
        if let selection = intent.selection, case .object(let id) = selection { _ = try await object(id, lease: lease) }
        let accepted = try await client.dispatchBoundJSONResponse(method: "PATCH",
            path: boundSpacePath + ["settings"], body: body, binding: binding,
            authorize: { try await self.currentRead(lease) })
        guard accepted.binding == binding, accepted.response.statusCode == 204,
              accepted.response.body == .null else { throw AnyEngineError.writeUncertain }
        let ack = remember(intent.operationID, generation: intent.generation, kind: .home)
        onAcknowledged(ack) // No suspension between native success and retention.
        do {
            let current = try await readHome(lease: lease)
            let expected = try intent.selection?.wireValue()
            guard Self.sameRaw(current.rawValue, expected) else {
                return .init(acknowledgment: ack,
                    readback: .nativeAcknowledgedCurrentStateUnverified, snapshot: nil)
            }
            return .init(acknowledgment: ack, readback: .verifiedCurrent, snapshot: current)
        } catch {
            // Native success remains a fact. No stale private readback escapes.
            return .init(acknowledgment: ack,
                readback: .nativeAcknowledgedCurrentStateUnverified, snapshot: nil)
        }
    }

    public func readLastOpened(objectID: String,
                               lease: AnyHostLease) async throws -> AnyNativeLastOpenedSnapshot {
        try await currentRead(lease)
        try await requireLastOpenedDefinition(lease)
        let row = try await object(objectID, lease: lease)
        let raw = row["any"]?[Self.lastOpenedProperty]
        let milliseconds = try Self.lastOpenedMilliseconds(raw)
        try await currentRead(lease)
        return .init(workspace: workspace, generation: lease.generation, binding: binding,
                     objectID: objectID, rawValue: raw, unixMilliseconds: milliseconds)
    }

    /// Called for an actual open, never while importing an archived timestamp.
    /// Heart records whole Unix seconds; the native datetime stores seconds*1000.
    public func prepareActualOpen(objectID: String, observedAt: Date = Date(),
                                  lease: AnyHostLease) async throws -> AnyPreparedNativeObjectOpen {
        let second = try Self.openedSecond(observedAt)
        try await currentRead(lease)
        try await requireLastOpenedDefinition(lease)
        _ = try await object(objectID, lease: lease)
        try await currentRead(lease)
        return .init(operationID: UUID(), objectID: objectID, observedUnixSecond: second,
                     workspace: workspace, generation: lease.generation, binding: binding)
    }

    public func commitActualOpen(
        _ intent: AnyPreparedNativeObjectOpen, lease: AnyHostLease,
        onAcknowledged: @escaping @Sendable (AnyNativeNavigationAcknowledgment) -> Void
    ) async throws -> AnyNativeOpenReceipt {
        try require(intent.workspace, intent.generation, intent.binding, lease: lease)
        guard Self.validID(intent.objectID), (0...253_402_300_799).contains(intent.observedUnixSecond) else {
            throw AnyNativePersonalNavigationError.invalidOpenedDate
        }
        try consume(intent.operationID)
        try await currentRead(lease)
        try await requireLastOpenedDefinition(lease)
        _ = try await object(intent.objectID, lease: lease)
        let milliseconds = intent.observedUnixSecond * 1000
        let body: AnyJSON = .object(["patch": .object([
            Self.lastOpenedProperty: .object(["$date": .integer(milliseconds)])
        ])])
        let accepted = try await client.dispatchBoundJSONResponse(method: "POST",
            path: boundSpacePath + ["properties", intent.objectID, "set", "any"],
            body: body, binding: binding, authorize: { try await self.currentRead(lease) })
        guard accepted.binding == binding, accepted.response.statusCode == 200 else {
            throw AnyEngineError.writeUncertain
        }
        try Self.requireLocalModifyResult(accepted.response.body, expectedObjectID: intent.objectID)
        let ack = remember(intent.operationID, generation: intent.generation, kind: .lastOpened)
        onAcknowledged(ack)
        do {
            let current = try await readLastOpened(objectID: intent.objectID, lease: lease)
            guard current.unixMilliseconds == milliseconds else {
                return .init(acknowledgment: ack,
                    readback: .nativeAcknowledgedCurrentStateUnverified, snapshot: nil)
            }
            return .init(acknowledgment: ack, readback: .verifiedCurrent, snapshot: current)
        } catch {
            return .init(acknowledgment: ack,
                readback: .nativeAcknowledgedCurrentStateUnverified, snapshot: nil)
        }
    }

    private var spacePath: [String] { ["v1", "spaces", workspace.spaceID] }
    private var boundSpacePath: [String] { ["v1", "pinkha", "bound", "spaces", workspace.spaceID] }

    private func consume(_ id: UUID) throws {
        guard !attempted.contains(id) else {
            throw AnyNativePersonalNavigationError.intentAlreadyDispatched
        }
        guard attempted.count < attemptLimit else {
            throw AnyNativePersonalNavigationError.sessionAttemptLimit
        }
        attempted.insert(id)
    }

    private func remember(_ id: UUID, generation: UUID,
                          kind: AnyNativeNavigationAcknowledgment.Kind) -> AnyNativeNavigationAcknowledgment {
        let ack = AnyNativeNavigationAcknowledgment(operationID: id, workspace: workspace,
            generation: generation, binding: binding, kind: kind)
        acknowledgments[id] = ack
        return ack
    }

    private func require(_ other: AnyTorahWorkspace, _ generation: UUID,
                         _ run: AnyNativeAccountRunBinding, lease: AnyHostLease) throws {
        guard Self.sameWorkspace(other, workspace),
              Self.sameWorkspace(lease.workspace, workspace) else { throw AnyHostError.wrongWorkspace }
        guard generation == lease.generation, run == binding else { throw AnyHostError.engineRestarted }
    }

    private func currentRead(_ lease: AnyHostLease) async throws {
        guard Self.sameWorkspace(lease.workspace, workspace) else { throw AnyHostError.wrongWorkspace }
        try await lease.validate()
        try await client.requireNativeAccountRun(binding)
        let member = try await client.requestJSON(method: "GET",
            path: spacePath + ["members", "me"], maximumResponseBytes: 65_536,
            authorize: { try await lease.validate() })
        guard let account = member["identity"]?.string, Self.same(account, workspace.accountID) else {
            throw AnyHostError.wrongWorkspace
        }
        try AnyHTTPTorahTargetAccess.validateMember(member, workspace: workspace, intent: .read)
        try await client.requireNativeAccountRun(binding)
        try await lease.validate()
    }

    private func object(_ id: String, lease: AnyHostLease) async throws -> AnyJSON {
        guard Self.validID(id) else { throw AnyNativePersonalNavigationError.invalidObject }
        let value = try await client.requestJSON(method: "GET",
            path: spacePath + ["objects", id], maximumResponseBytes: 4_194_304,
            authorize: { try await lease.validate() })
        guard let outer = value["objectId"]?.string, Self.same(outer, id),
              let row = value["record"], let inner = row["id"]?.string, Self.same(inner, id),
              let space = row["spaceId"]?.string, Self.same(space, workspace.spaceID),
              let type = row["any"]?["type"]?.string, Self.validID(type),
              row["any"]?["collections"] == nil || row["any"]?["collections"]?.array != nil else {
            throw AnyNativePersonalNavigationError.invalidObject
        }
        let collections = row["any"]?["collections"]?.array ?? []
        guard collections.count <= 1024, collections.allSatisfy({
            guard let id = $0.string else { return false }
            return Self.validID(id) && !Self.same(id, "bin") && !Self.same(id, "template")
        }) else { throw AnyNativePersonalNavigationError.invalidObject }
        return row
    }

    private func requireLastOpenedDefinition(_ lease: AnyHostLease) async throws {
        let value = try await client.requestJSON(method: "GET",
            path: spacePath + ["types", "any", "properties"], maximumResponseBytes: 2_097_152,
            authorize: { try await lease.validate() })
        try Self.validateLastOpenedDefinition(value)
    }

    nonisolated static func validateLastOpenedDefinition(_ value: AnyJSON) throws {
        guard let rows = value["properties"]?.array, rows.count <= 1024 else {
            throw AnyNativePersonalNavigationError.unavailableContract
        }
        let ids = rows.compactMap { $0["id"]?.string }
        guard ids.count == rows.count, Set(ids.map { Data($0.utf8) }).count == ids.count,
              let definition = rows.first(where: {
                  $0["id"]?.string.map { same($0, lastOpenedProperty) } == true
              }),
              definition["kind"]?.string == "datetime", definition["scope"]?.string == "local",
              definition["xFormat"]?["type"]?.string == "datetime",
              definition["xFormat"]?["contract"]?.string == lastOpenedContract,
              definition["xFormat"]?["precision"]?.string == "seconds" else {
            throw AnyNativePersonalNavigationError.unavailableContract
        }
    }

    nonisolated static func requireLocalModifyResult(_ value: AnyJSON, expectedObjectID: String) throws {
        guard let fields = value.object, let version = fields["versionId"]?.string, !version.isEmpty,
              fields["changeId"]?.string == "", let ids = fields["recordIds"]?.array,
              ids.count == 1, let recordID = ids.first?.string, same(recordID, expectedObjectID),
              fields["rejections"] == nil || fields["rejections"]?.array?.isEmpty == true else {
            throw AnyEngineError.writeUncertain
        }
        // This nonempty, single-record local apply always returns the supplied
        // object ID, including an equal-value update. Its changeId is empty:
        // a shared DAG acknowledgment would belong to a different operation.
    }

    nonisolated static func openedSecond(_ date: Date) throws -> Int64 {
        let value = date.timeIntervalSince1970.rounded(.down)
        guard value.isFinite, value >= 0, value <= 253_402_300_799,
              let second = Int64(exactly: value) else {
            throw AnyNativePersonalNavigationError.invalidOpenedDate
        }
        return second
    }

    nonisolated static func lastOpenedMilliseconds(_ raw: AnyJSON?) throws -> Int64? {
        guard let raw else { return nil }
        guard let fields = raw.object, Set(fields.keys) == ["$date"],
              let value = fields["$date"] else {
            throw AnyNativePersonalNavigationError.unavailableContract
        }
        if let milliseconds = value.integer {
            guard (0...253_402_300_799_000).contains(milliseconds), milliseconds % 1000 == 0 else {
                throw AnyNativePersonalNavigationError.invalidOpenedDate
            }
            return milliseconds
        }
        guard let text = value.string, text.utf8.count <= 128 else {
            throw AnyNativePersonalNavigationError.invalidOpenedDate
        }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let fractional = formatter.date(from: text)
        formatter.formatOptions = [.withInternetDateTime]
        guard let date = fractional ?? formatter.date(from: text) else {
            throw AnyNativePersonalNavigationError.invalidOpenedDate
        }
        let second = try openedSecond(date)
        guard date.timeIntervalSince1970 == Double(second) else {
            throw AnyNativePersonalNavigationError.invalidOpenedDate
        }
        return second * 1000
    }

    nonisolated static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096
            && value.utf8.allSatisfy { $0 > 32 && $0 != 127 }
            && value != "." && value != ".."
    }

    nonisolated static func same(_ a: String, _ b: String) -> Bool {
        a.utf8.elementsEqual(b.utf8)
    }

    nonisolated static func sameWorkspace(_ a: AnyTorahWorkspace, _ b: AnyTorahWorkspace) -> Bool {
        same(a.accountID, b.accountID) && same(a.spaceID, b.spaceID)
    }

    nonisolated static func sameRaw(_ a: AnyJSON?, _ b: AnyJSON?) -> Bool {
        switch (a, b) {
        case (nil, nil): true
        case (.string(let a)?, .string(let b)?): same(a, b)
        default: false
        }
    }
}
