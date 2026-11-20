import Foundation

import PinkhaAnyEngine



/// A conditional property write is bound to the exact native record and engine

/// run that the caller reviewed. The application sequence also detects late

/// commutative changes which can leave the complete LWW version map unchanged.

public struct AnyConditionalPropertyFence: Codable, Sendable, Equatable {

    public let nativeVersion: AnyJSON

    public let applySequence: Int64

    public let engineStartedAt: String



    public init(nativeVersion: AnyJSON, applySequence: Int64, engineStartedAt: String) throws {

        guard nativeVersion.object != nil, applySequence > 0,

              !engineStartedAt.isEmpty, engineStartedAt.utf8.count <= 128,

              !engineStartedAt.utf8.contains(0) else {

            throw AnyEngineError.incompatibleSchema("native property fence")

        }

        do { try AnyHierarchyNativeVersion.validate(nativeVersion) }
        catch let error as AnyEngineError { throw error }
        catch { throw AnyEngineError.incompatibleSchema("native property version") }

        self.nativeVersion = nativeVersion

        self.applySequence = applySequence

        self.engineStartedAt = engineStartedAt

    }



    /// Capture all fields from one record and its already-verified engine run.

    /// Numbers are never rounded or coerced; an unrepresentable sequence refuses.

    public init(record: AnyJSON, engineStartedAt: String) throws {

        guard let version = record["_ver"], let sequence = record["_applySeq"]?.integer else {

            throw AnyEngineError.incompatibleSchema("native property fence unavailable")

        }

        try self.init(nativeVersion: version, applySequence: sequence, engineStartedAt: engineStartedAt)

    }



    /// Encoding does not authorize a write. The caller must require the explicit

    /// native capability and preserve its account, target and dispatch checks.

    public func requestBody(patch: [String: AnyJSON]) -> AnyJSON {

        .object(["patch": .object(patch), "ifVersion": nativeVersion,

                 "ifApplySeq": .integer(applySequence), "ifStartedAt": .string(engineStartedAt)])

    }



    private enum CodingKeys: String, CodingKey {

        case nativeVersion, applySequence, engineStartedAt

    }



    public init(from decoder: any Decoder) throws {

        let value = try decoder.container(keyedBy: CodingKeys.self)

        try self.init(nativeVersion: value.decode(AnyJSON.self, forKey: .nativeVersion),

                      applySequence: value.decode(Int64.self, forKey: .applySequence),

                      engineStartedAt: value.decode(String.self, forKey: .engineStartedAt))

    }

}

