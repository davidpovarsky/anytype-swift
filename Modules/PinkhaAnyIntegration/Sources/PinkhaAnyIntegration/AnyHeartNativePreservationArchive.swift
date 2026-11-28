import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativePreservationError: Error, Equatable, Sendable {
    case binding, member, limit, malformedArchive
}

/// Bounded, reversible native-source file. Capture members and separately
/// recovered registry evidence retain distinct namespaces and exact bytes.
/// Decoding performs no filesystem write, restore, session acquisition or import.
public struct AnyHeartNativePreservationArchive: Sendable {
    public static let contract = "pinkha-heart-preserved-source-file-v1"
    public static let maximumBytes = 64 * 1024 * 1024
    public static let mimeType = "application/vnd.pinkha.heart-source"
    private static let magic = Data("PINKHA-HEART-SOURCE-1\u{0}".utf8)
    public static let capturedContract = "pinkha-heart-preserved-source-file-v2"
    private static let capturedMagic = Data("PINKHA-HEART-SOURCE-2\u{0}".utf8)

    public struct Binding: Equatable, Sendable {
        public let accountID: String
        public let spaceID: String
        public let captureManifestSHA256: String
        public let sourceWitnessSHA256: String
        public let definitionEvidenceKind: AnyHeartNativeDefinitionEvidence.Kind
        public let recoveredManifestSHA256: String?
        public init(bundle: AnyHeartNativeSpaceBundle, recovered: AnyHeartNativeRecoveredDefinitions) throws {
            _ = try AnyHeartNativeDefinitionCatalog(bundle: bundle, recoveredDefinitions: recovered)
            accountID = bundle.sourceAccountID; spaceID = bundle.sourceSpaceID
            captureManifestSHA256 = bundle.manifestSHA256; sourceWitnessSHA256 = bundle.sourceWitnessSHA256
            recoveredManifestSHA256 = recovered.manifestSHA256
            definitionEvidenceKind = .recoveredOriginal
        }

        public init(capturedBundle bundle: AnyHeartNativeSpaceBundle) throws {
            _ = try AnyHeartNativeDefinitionEvidence.capturedComplete.catalog(bundle: bundle)
            accountID = bundle.sourceAccountID; spaceID = bundle.sourceSpaceID
            captureManifestSHA256 = bundle.manifestSHA256; sourceWitnessSHA256 = bundle.sourceWitnessSHA256
            recoveredManifestSHA256 = nil; definitionEvidenceKind = .capturedComplete
        }

        /// An expected persisted identity, not a source session or admission.
        /// restore still checks the complete original bundle and recovered
        /// descriptors against all five values before returning any member.
        public init(expectedAccountID: String, expectedSpaceID: String,
                    captureManifestSHA256: String, sourceWitnessSHA256: String,
                    recoveredManifestSHA256: String) throws {
            func identifier(_ value: String) -> Bool {
                !value.isEmpty && value.utf8.count <= 4096 &&
                    value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
            }
            func digest(_ value: String) -> Bool {
                value.utf8.count == 64 &&
                    value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
            }
            guard identifier(expectedAccountID), identifier(expectedSpaceID),
                  [captureManifestSHA256, sourceWitnessSHA256, recoveredManifestSHA256].allSatisfy(digest) else {
                throw AnyHeartNativePreservationError.binding
            }
            self.accountID = expectedAccountID; self.spaceID = expectedSpaceID
            self.captureManifestSHA256 = captureManifestSHA256
            self.sourceWitnessSHA256 = sourceWitnessSHA256
            self.recoveredManifestSHA256 = recoveredManifestSHA256
            self.definitionEvidenceKind = .recoveredOriginal
        }

        public init(expectedAccountID: String, expectedSpaceID: String,
                    capturedManifestSHA256: String, sourceWitnessSHA256: String) throws {
            func identifier(_ value: String) -> Bool {
                !value.isEmpty && value.utf8.count <= 4096 &&
                    value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
            }
            func digest(_ value: String) -> Bool {
                value.utf8.count == 64 &&
                    value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
            }
            guard identifier(expectedAccountID), identifier(expectedSpaceID),
                  [capturedManifestSHA256, sourceWitnessSHA256].allSatisfy(digest) else {
                throw AnyHeartNativePreservationError.binding
            }
            accountID = expectedAccountID; spaceID = expectedSpaceID
            captureManifestSHA256 = capturedManifestSHA256
            self.sourceWitnessSHA256 = sourceWitnessSHA256
            recoveredManifestSHA256 = nil; definitionEvidenceKind = .capturedComplete
        }

        public static func == (lhs: Self, rhs: Self) -> Bool {
            Data(lhs.accountID.utf8) == Data(rhs.accountID.utf8) &&
                Data(lhs.spaceID.utf8) == Data(rhs.spaceID.utf8) &&
                lhs.captureManifestSHA256 == rhs.captureManifestSHA256 &&
                lhs.sourceWitnessSHA256 == rhs.sourceWitnessSHA256 &&
                lhs.definitionEvidenceKind == rhs.definitionEvidenceKind &&
                lhs.recoveredManifestSHA256 == rhs.recoveredManifestSHA256
        }
    }
    public struct Restored: Sendable {
        public let bundle: AnyHeartNativeSpaceBundle
        public let recoveredDefinitions: AnyHeartNativeRecoveredDefinitions?
        public var definitionEvidence: AnyHeartNativeDefinitionEvidence {
            if let recoveredDefinitions { return .recoveredOriginal(recoveredDefinitions) }
            return .capturedComplete
        }
        public let originalMemberCount: Int
        public let recoveredMemberCount: Int
        fileprivate let members: [String: Data]
        public var grantsSourceSession: Bool { false }

        /// Exact verified bytes remain available to an explicit export caller.
        /// This accessor does not write a path or restore a native account.
        public func capturedMemberData(_ member: AnyHeartNativeSpaceBundle.Member) throws -> Data {
            try memberData(member, declared: bundle.verifiedMembers, prefix: "capture/")
        }
        public func recoveredMemberData(_ member: AnyHeartNativeSpaceBundle.Member) throws -> Data {
            guard let recoveredDefinitions else { throw AnyHeartNativePreservationError.member }
            return try memberData(member, declared: recoveredDefinitions.verifiedMembers, prefix: "recovery/descriptors/")
        }
        private func memberData(_ member: AnyHeartNativeSpaceBundle.Member,
                                declared: [AnyHeartNativeSpaceBundle.Member], prefix: String) throws -> Data {
            guard declared.contains(where: {
                Data($0.path.utf8) == Data(member.path.utf8) &&
                    $0.sha256 == member.sha256 && $0.byteCount == member.byteCount
            }), let bytes = members[prefix + member.path],
                  bytes.count == member.byteCount, AnyContentDigest.sha256(bytes) == member.sha256 else {
                throw AnyHeartNativePreservationError.member
            }
            return bytes
        }
        public var restoresAnAccount: Bool { false }
    }

    public let binding: Binding
    public let bytes: Data
    public let sha256: String
    public let originalMemberCount: Int
    public let recoveredMemberCount: Int
    public var permitsDestinationWrites: Bool { false }

    public init(bundle: AnyHeartNativeSpaceBundle, recovered: AnyHeartNativeRecoveredDefinitions,
                memberData: (AnyHeartNativeSpaceBundle.Member) throws -> Data,
                recoveredMemberData: (AnyHeartNativeSpaceBundle.Member) throws -> Data) throws {
        let binding = try Binding(bundle: bundle, recovered: recovered)
        var rows: [(String, Data)] = [], names = Set<Data>(), total = 0
        func append(_ path: String, _ value: Data, expected: AnyHeartNativeSpaceBundle.Member? = nil) throws {
            guard Self.path(path), names.insert(Data(path.utf8)).inserted else {
                throw AnyHeartNativePreservationError.member
            }
            if let expected {
                guard value.count == expected.byteCount,
                      AnyContentDigest.sha256(value) == expected.sha256 else {
                    throw AnyHeartNativePreservationError.member
                }
            }
            guard value.count <= Self.maximumBytes - total else { throw AnyHeartNativePreservationError.limit }
            total += value.count; rows.append((path, value))
        }
        try append("capture/manifest.json", bundle.manifestBytes)
        for member in bundle.verifiedMembers {
            guard member.byteCount <= Self.maximumBytes - total else { throw AnyHeartNativePreservationError.limit }
            try append("capture/" + member.path, memberData(member), expected: member)
        }
        try append("recovery/binding.json", recovered.manifestBytes)
        try append("recovery/original-producer.json", recovered.originalProducerBytes)
        try append("recovery/receipt.json", recovered.recoveryReceiptBytes)
        try append("recovery/export.json", recovered.exportManifestBytes)
        for member in recovered.verifiedMembers {
            guard member.byteCount <= Self.maximumBytes - total else { throw AnyHeartNativePreservationError.limit }
            try append("recovery/descriptors/" + member.path, recoveredMemberData(member), expected: member)
        }
        rows.sort { Data($0.0.utf8).lexicographicallyPrecedes(Data($1.0.utf8)) }
        let header: AnyJSON = .object([
            "contract": .string(Self.contract), "accountID": .string(binding.accountID),
            "spaceID": .string(binding.spaceID), "captureManifestSHA256": .string(binding.captureManifestSHA256),
            "sourceWitnessSHA256": .string(binding.sourceWitnessSHA256),
            "recoveredManifestSHA256": .string(recovered.manifestSHA256),
            "members": .array(rows.map { .object(["path": .string($0.0),
                "bytes": .integer(Int64($0.1.count)), "sha256": .string(AnyContentDigest.sha256($0.1))]) }),
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let encoded = try encoder.encode(header)
        guard encoded.count <= 4 * 1024 * 1024,
              total <= Self.maximumBytes - encoded.count - Self.magic.count - 8 else {
            throw AnyHeartNativePreservationError.limit
        }
        var data = Self.magic
        for shift in stride(from: 56, through: 0, by: -8) {
            data.append(UInt8((UInt64(encoded.count) >> UInt64(shift)) & 255))
        }
        data.append(encoded)
        for (_, value) in rows { data.append(value) }
        let restored = try Self.restore(data, expected: binding)
        guard restored.bundle.manifestBytes == bundle.manifestBytes,
              restored.recoveredDefinitions?.manifestBytes == recovered.manifestBytes else {
            throw AnyHeartNativePreservationError.binding
        }
        self.binding = binding; bytes = data; sha256 = AnyContentDigest.sha256(data)
        originalMemberCount = bundle.verifiedMembers.count + 1
        recoveredMemberCount = recovered.verifiedMembers.count + 4
    }



    /// Direct native capture, with zero missing compiled descriptors. The v2
    /// envelope contains only capture members and explicitly no recovery rows.
    public init(capturedBundle bundle: AnyHeartNativeSpaceBundle,
                memberData: (AnyHeartNativeSpaceBundle.Member) throws -> Data) throws {
        let binding = try Binding(capturedBundle: bundle)
        var rows: [(String, Data)] = [], names = Set<Data>(), total = 0
        func append(_ path: String, _ value: Data, expected: AnyHeartNativeSpaceBundle.Member? = nil) throws {
            try Task.checkCancellation()
            guard Self.path(path), names.insert(Data(path.utf8)).inserted else {
                throw AnyHeartNativePreservationError.member
            }
            if let expected {
                guard value.count == expected.byteCount,
                      AnyContentDigest.sha256(value) == expected.sha256 else {
                    throw AnyHeartNativePreservationError.member
                }
            }
            guard value.count <= Self.maximumBytes - total else { throw AnyHeartNativePreservationError.limit }
            total += value.count; rows.append((path, value))
        }
        try append("capture/manifest.json", bundle.manifestBytes)
        for member in bundle.verifiedMembers {
            guard member.byteCount <= Self.maximumBytes - total else { throw AnyHeartNativePreservationError.limit }
            try append("capture/" + member.path, memberData(member), expected: member)
        }
        rows.sort { Data($0.0.utf8).lexicographicallyPrecedes(Data($1.0.utf8)) }
        let header: AnyJSON = .object([
            "contract": .string(Self.capturedContract), "accountID": .string(binding.accountID),
            "spaceID": .string(binding.spaceID), "captureManifestSHA256": .string(binding.captureManifestSHA256),
            "sourceWitnessSHA256": .string(binding.sourceWitnessSHA256),
            "definitionEvidence": .string(AnyHeartNativeDefinitionEvidence.Kind.capturedComplete.rawValue),
            "members": .array(rows.map { .object(["path": .string($0.0),
                "bytes": .integer(Int64($0.1.count)), "sha256": .string(AnyContentDigest.sha256($0.1))]) }),
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let encoded = try encoder.encode(header)
        guard encoded.count <= 4 * 1024 * 1024,
              total <= Self.maximumBytes - encoded.count - Self.capturedMagic.count - 8 else {
            throw AnyHeartNativePreservationError.limit
        }
        var data = Self.capturedMagic
        for shift in stride(from: 56, through: 0, by: -8) {
            data.append(UInt8((UInt64(encoded.count) >> UInt64(shift)) & 255))
        }
        data.append(encoded)
        for (_, value) in rows { data.append(value) }
        let restored = try Self.restore(data, expected: binding)
        guard restored.bundle.manifestBytes == bundle.manifestBytes,
              restored.recoveredDefinitions == nil, restored.recoveredMemberCount == 0 else {
            throw AnyHeartNativePreservationError.binding
        }
        try Task.checkCancellation()
        self.binding = binding; bytes = data; sha256 = AnyContentDigest.sha256(data)
        originalMemberCount = bundle.verifiedMembers.count + 1; recoveredMemberCount = 0
    }

    /// Reopens exactly one already-preserved source file. This validates the
    /// same complete member set as restore and never writes or restores an
    /// account. It preserves the original bytes instead of re-exporting them.
    public init(restoring data: Data, expected: Binding) throws {
        let restored = try Self.restore(data, expected: expected)
        self.binding = expected
        self.bytes = data
        self.sha256 = AnyContentDigest.sha256(data)
        self.originalMemberCount = restored.originalMemberCount
        self.recoveredMemberCount = restored.recoveredMemberCount
    }

    public static func restore(_ data: Data, expected: Binding) throws -> Restored {
        if expected.definitionEvidenceKind == .capturedComplete {
            return try restoreCaptured(data, expected: expected)
        }
        guard expected.definitionEvidenceKind == .recoveredOriginal,
              let recoverySHA256 = expected.recoveredManifestSHA256 else {
            throw AnyHeartNativePreservationError.binding
        }
        guard data.count <= maximumBytes, data.count >= magic.count + 8,
              data.prefix(magic.count) == magic else { throw AnyHeartNativePreservationError.malformedArchive }
        var cursor = magic.count
        var headerLength: UInt64 = 0
        for byte in data[cursor..<(cursor + 8)] { headerLength = (headerLength << 8) | UInt64(byte) }
        cursor += 8
        guard headerLength <= 4 * 1024 * 1024, headerLength <= UInt64(data.count - cursor) else {
            throw AnyHeartNativePreservationError.limit
        }
        let headerBytes = data.subdata(in: cursor..<(cursor + Int(headerLength))); cursor += Int(headerLength)
        let header = try JSONDecoder().decode(AnyJSON.self, from: headerBytes)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: headerBytes, encoded: encoder.encode(header))
        guard let object = header.object,
              Set(object.keys) == ["contract", "accountID", "spaceID", "captureManifestSHA256",
                                   "sourceWitnessSHA256", "recoveredManifestSHA256", "members"],
              header["contract"] == .string(contract),
              same(header["accountID"]?.string, expected.accountID),
              same(header["spaceID"]?.string, expected.spaceID),
              header["captureManifestSHA256"] == .string(expected.captureManifestSHA256),
              header["sourceWitnessSHA256"] == .string(expected.sourceWitnessSHA256),
              header["recoveredManifestSHA256"] == .string(recoverySHA256),
              let declared = header["members"]?.array, !declared.isEmpty, declared.count <= 100_000 else {
            throw AnyHeartNativePreservationError.binding
        }
        var members: [String: Data] = [:], rawNames = Set<Data>(), previous: Data?
        for value in declared {
            guard let row = value.object, Set(row.keys) == ["path", "bytes", "sha256"],
                  let name = value["path"]?.string, path(name),
                  let count = value["bytes"]?.integer, count >= 0, count <= Int64(data.count - cursor),
                  let hash = value["sha256"]?.string, hash.count == 64,
                  rawNames.insert(Data(name.utf8)).inserted,
                  members[name] == nil, previous.map({ $0.lexicographicallyPrecedes(Data(name.utf8)) }) ?? true else {
                throw AnyHeartNativePreservationError.member
            }
            previous = Data(name.utf8)
            let body = data.subdata(in: cursor..<(cursor + Int(count))); cursor += Int(count)
            guard AnyContentDigest.sha256(body) == hash else { throw AnyHeartNativePreservationError.member }
            members[name] = body
        }
        guard cursor == data.count else { throw AnyHeartNativePreservationError.malformedArchive }
        func require(_ path: String) throws -> Data {
            guard let value = members[path] else { throw AnyHeartNativePreservationError.member }
            return value
        }
        let manifest = try require("capture/manifest.json")
        guard AnyContentDigest.sha256(manifest) == expected.captureManifestSHA256 else {
            throw AnyHeartNativePreservationError.binding
        }
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: expected.accountID, sourceSpaceID: expected.spaceID) {
                try require("capture/" + $0.path)
            }
        guard bundle.sourceWitnessSHA256 == expected.sourceWitnessSHA256 else {
            throw AnyHeartNativePreservationError.binding
        }
        let recovered = try AnyHeartNativeRecoveredDefinitions(bundle: bundle,
            manifest: require("recovery/binding.json"),
            expectedManifestSHA256: recoverySHA256,
            originalProducer: require("recovery/original-producer.json"),
            recoveryReceipt: require("recovery/receipt.json"),
            registryExport: require("recovery/export.json")) {
                try require("recovery/descriptors/" + $0.path)
            }
        let expectedPaths = Set(["capture/manifest.json", "recovery/binding.json",
            "recovery/original-producer.json", "recovery/receipt.json", "recovery/export.json"] +
            bundle.verifiedMembers.map { "capture/" + $0.path } +
            recovered.verifiedMembers.map { "recovery/descriptors/" + $0.path })
        let expectedRawPaths = Set(expectedPaths.map { Data($0.utf8) })
        guard Set(members.keys.map { Data($0.utf8) }) == expectedRawPaths,
              members.count == expectedRawPaths.count else {
            throw AnyHeartNativePreservationError.member
        }
        return .init(bundle: bundle, recoveredDefinitions: recovered,
            originalMemberCount: bundle.verifiedMembers.count + 1,
            recoveredMemberCount: recovered.verifiedMembers.count + 4, members: members)
    }


    private static func restoreCaptured(_ data: Data, expected: Binding) throws -> Restored {
        try Task.checkCancellation()
        guard expected.definitionEvidenceKind == .capturedComplete,
              expected.recoveredManifestSHA256 == nil,
              data.count <= maximumBytes, data.count >= capturedMagic.count + 8,
              data.prefix(capturedMagic.count) == capturedMagic else {
            throw AnyHeartNativePreservationError.malformedArchive
        }
        var cursor = capturedMagic.count
        var headerLength: UInt64 = 0
        for byte in data[cursor..<(cursor + 8)] { headerLength = (headerLength << 8) | UInt64(byte) }
        cursor += 8
        guard headerLength <= 4 * 1024 * 1024, headerLength <= UInt64(data.count - cursor) else {
            throw AnyHeartNativePreservationError.limit
        }
        let headerBytes = data.subdata(in: cursor..<(cursor + Int(headerLength))); cursor += Int(headerLength)
        let header = try JSONDecoder().decode(AnyJSON.self, from: headerBytes)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: headerBytes, encoded: encoder.encode(header))
        guard let object = header.object,
              Set(object.keys) == ["contract", "accountID", "spaceID", "captureManifestSHA256",
                                   "sourceWitnessSHA256", "definitionEvidence", "members"],
              header["contract"] == .string(capturedContract),
              header["definitionEvidence"] == .string(AnyHeartNativeDefinitionEvidence.Kind.capturedComplete.rawValue),
              same(header["accountID"]?.string, expected.accountID),
              same(header["spaceID"]?.string, expected.spaceID),
              header["captureManifestSHA256"] == .string(expected.captureManifestSHA256),
              header["sourceWitnessSHA256"] == .string(expected.sourceWitnessSHA256),
              let declared = header["members"]?.array, !declared.isEmpty, declared.count <= 100_000 else {
            throw AnyHeartNativePreservationError.binding
        }
        var members: [String: Data] = [:], rawNames = Set<Data>(), previous: Data?
        for value in declared {
            try Task.checkCancellation()
            guard let row = value.object, Set(row.keys) == ["path", "bytes", "sha256"],
                  let name = value["path"]?.string, path(name), name.hasPrefix("capture/"),
                  let count = value["bytes"]?.integer, count >= 0, count <= Int64(data.count - cursor),
                  let hash = value["sha256"]?.string, hash.count == 64,
                  rawNames.insert(Data(name.utf8)).inserted,
                  members[name] == nil, previous.map({ $0.lexicographicallyPrecedes(Data(name.utf8)) }) ?? true else {
                throw AnyHeartNativePreservationError.member
            }
            previous = Data(name.utf8)
            let body = data.subdata(in: cursor..<(cursor + Int(count))); cursor += Int(count)
            guard AnyContentDigest.sha256(body) == hash else { throw AnyHeartNativePreservationError.member }
            members[name] = body
        }
        guard cursor == data.count, let manifest = members["capture/manifest.json"],
              AnyContentDigest.sha256(manifest) == expected.captureManifestSHA256 else {
            throw AnyHeartNativePreservationError.malformedArchive
        }
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: expected.accountID, sourceSpaceID: expected.spaceID) { member in
                guard let value = members["capture/" + member.path] else { throw AnyHeartNativePreservationError.member }
                return value
            }
        guard bundle.sourceWitnessSHA256 == expected.sourceWitnessSHA256,
              try Binding(capturedBundle: bundle) == expected else {
            throw AnyHeartNativePreservationError.binding
        }
        let expectedPaths = Set((["capture/manifest.json"] +
            bundle.verifiedMembers.map { "capture/" + $0.path }).map { Data($0.utf8) })
        guard Set(members.keys.map { Data($0.utf8) }) == expectedPaths,
              members.count == expectedPaths.count else { throw AnyHeartNativePreservationError.member }
        try Task.checkCancellation()
        return .init(bundle: bundle, recoveredDefinitions: nil,
            originalMemberCount: bundle.verifiedMembers.count + 1, recoveredMemberCount: 0, members: members)
    }

    private static func same(_ lhs: String?, _ rhs: String) -> Bool {
        lhs.map { Data($0.utf8) == Data(rhs.utf8) } ?? false
    }
    private static func path(_ path: String) -> Bool {
        let parts = path.split(separator: "/", omittingEmptySubsequences: false)
        return !path.isEmpty && path.utf8.count <= 4096 && !path.utf8.contains(0) &&
            !path.contains("\\") && parts.allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }
}
