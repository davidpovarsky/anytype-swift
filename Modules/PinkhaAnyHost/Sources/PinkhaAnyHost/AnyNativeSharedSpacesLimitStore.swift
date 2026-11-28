import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Keeps the native timestamp's exact bytes, including nanoseconds and offset.
/// Parsing validates the Go RFC3339Nano wire domain without rounding it through
/// Foundation.Date or replacing it with the time the caller read a cached value.
public struct AnyNativeRuntimeTimestamp: Equatable, Sendable {
    public let rawValue: String

    public init(_ value: String) throws {
        let bytes = Array(value.utf8)
        func decimal(_ start: Int, _ count: Int) -> Int? {
            guard start >= 0, count > 0, start + count <= bytes.count else { return nil }
            var result = 0
            for byte in bytes[start..<(start + count)] {
                guard (48...57).contains(byte) else { return nil }
                result = result * 10 + Int(byte - 48)
            }
            return result
        }
        guard (20...35).contains(bytes.count), bytes[4] == 45, bytes[7] == 45,
              bytes[10] == 84, bytes[13] == 58, bytes[16] == 58,
              let year = decimal(0, 4), let month = decimal(5, 2), (1...12).contains(month),
              let day = decimal(8, 2), let hour = decimal(11, 2), (0...23).contains(hour),
              let minute = decimal(14, 2), (0...59).contains(minute),
              let second = decimal(17, 2), (0...59).contains(second) else {
            throw AnyEngineError.malformedResponse("native runtime timestamp")
        }
        let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
        let days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        guard (1...days[month - 1]).contains(day) else {
            throw AnyEngineError.malformedResponse("native runtime timestamp date")
        }
        var zone = 19
        if bytes[zone] == 46 {
            zone += 1
            let fractionStart = zone
            while zone < bytes.count && (48...57).contains(bytes[zone]) { zone += 1 }
            guard (1...9).contains(zone - fractionStart) else {
                throw AnyEngineError.malformedResponse("native runtime timestamp fraction")
            }
        }
        guard zone < bytes.count else { throw AnyEngineError.malformedResponse("native runtime timestamp zone") }
        if bytes[zone] == 90 {
            guard zone + 1 == bytes.count else {
                throw AnyEngineError.malformedResponse("native runtime timestamp suffix")
            }
        } else {
            guard zone + 6 == bytes.count, bytes[zone] == 43 || bytes[zone] == 45,
                  bytes[zone + 3] == 58, let hours = decimal(zone + 1, 2), (0...23).contains(hours),
                  let minutes = decimal(zone + 4, 2), (0...59).contains(minutes) else {
                throw AnyEngineError.malformedResponse("native runtime timestamp offset")
            }
        }
        rawValue = value
    }

    public static func == (left: Self, right: Self) -> Bool {
        left.rawValue.utf8.elementsEqual(right.rawValue.utf8)
    }
}

public struct AnyNativeSharedSpacesLimitObservation: Equatable, Sendable {
    public let limit: UInt32
    /// When the coordinator supplied the answer, possibly in an earlier run.
    /// A successful HTTP read does not prove a new coordinator round trip.
    public let fetchedAt: AnyNativeRuntimeTimestamp
}

public enum AnyNativeSharedSpacesLimitValue: Equatable, Sendable {
    /// The native endpoint omitted this part because no answer is available.
    /// This is distinct from an observed limit of zero.
    case unavailable
    case observed(AnyNativeSharedSpacesLimitObservation)
}

public struct AnyNativeSharedSpacesLimitSnapshot: Sendable {
    /// Destination delivery scope. The quota itself belongs to its account,
    /// not only this Space and not the imported source account.
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let binding: AnyHeartNativeRuntimeRelationBinding
    public let value: AnyNativeSharedSpacesLimitValue
    public var permitsDestinationWrites: Bool { false }
}

/// Reads the existing shared account-limits API. It adds no storage, retries,
/// account credentials, permission grant or alternative quota subsystem.
public struct AnyNativeSharedSpacesLimitStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard client.expectedAccountID.utf8.elementsEqual(workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        self.client = client
        self.workspace = workspace
    }

    public func read(binding: AnyHeartNativeRuntimeRelationBinding,
                     source: AnyDestinationSourceBinding,
                     lease: AnyHostLease) async throws -> AnyNativeSharedSpacesLimitSnapshot {
        guard binding.role == .sharedSpacesLimit else {
            throw AnyDestinationMigrationError.invalidPlan("shared-spaces provider role")
        }
        try binding.requireSource(source, objectID: binding.evidence.sourceObjectID)
        try await validate(lease)
        let response = try await client.requestJSON(method: "GET", path: ["v1", "account", "limits"],
            maximumResponseBytes: 16_384, authorize: { try await validate(lease) })
        let value = try Self.parse(response)
        try await validate(lease)
        return .init(workspace: workspace, generation: lease.generation,
            engineStartedAt: lease.engineStartedAt, binding: binding, value: value)
    }

    static func parse(_ response: AnyJSON) throws -> AnyNativeSharedSpacesLimitValue {
        guard let body = response.object else {
            throw AnyEngineError.malformedResponse("account limits object")
        }
        guard let shared = body["sharedSpaces"] else { return .unavailable }
        // Native omitempty emits absence, never null, for an unavailable part.
        // Refuse malformed present data instead of silently erasing it.
        guard let fields = shared.object,
              Set(fields.keys) == Set(["limit", "fetchedAt"]),
              let limit = fields["limit"]?.integer, let bounded = UInt32(exactly: limit),
              let fetchedAt = fields["fetchedAt"]?.string else {
            throw AnyEngineError.malformedResponse("shared-spaces limits")
        }
        return .observed(.init(limit: bounded, fetchedAt: try .init(fetchedAt)))
    }

    private func validate(_ lease: AnyHostLease) async throws {
        guard lease.workspace.accountID.utf8.elementsEqual(workspace.accountID.utf8),
              lease.workspace.spaceID.utf8.elementsEqual(workspace.spaceID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try await lease.validate()
        try Task.checkCancellation()
    }
}
