import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativeRecoveredDefinitionError: Error, Equatable, Sendable {
    case invalidBinding, invalidEvidence, invalidDescriptor, limit
}

/// Separately recovered registry vocabulary bound to one unchanged capture.
/// The caller must obtain expectedManifestSHA256 from the independently qualified
/// recovery receipt. A digest supplied by the sidecar itself is not authority.
/// This never rewrites the captured bundle or grants session/destination access.
public struct AnyHeartNativeRecoveredDefinitions: Sendable {
    public let manifestSHA256: String
    public let captureManifestSHA256: String
    public let sourceWitnessSHA256: String
    public let sourceAccountSHA256: String
    public let sourceSpaceSHA256: String
    public let originalProducerSHA256: String
    public let originalSourceManifestSHA256: String
    public let originalNativeBinarySHA256: String
    public let recoveryReceiptSHA256: String
    public let exportManifestSHA256: String
    public let manifestBytes: Data
    public let originalProducerBytes: Data
    public let recoveryReceiptBytes: Data
    public let exportManifestBytes: Data
    public let definitions: [AnyHeartNativeBundledDefinition]
    public let verifiedMembers: [AnyHeartNativeSpaceBundle.Member]
    public var permitsDestinationWrites: Bool { false }
    public var replacesHistoricalCapturedMembers: Bool { false }

    public init(bundle: AnyHeartNativeSpaceBundle, manifest: Data,
                expectedManifestSHA256: String, originalProducer: Data,
                recoveryReceipt: Data, registryExport: Data,
                memberData: (AnyHeartNativeSpaceBundle.Member) throws -> Data) throws {
        guard Self.digest(expectedManifestSHA256),
              AnyContentDigest.sha256(manifest) == expectedManifestSHA256 else {
            throw AnyHeartNativeRecoveredDefinitionError.invalidBinding
        }
        let root = try Self.decode(manifest, maximum: 1_048_576)
        guard let fields = root.object,
              Set(fields.keys) == ["Contract", "OriginalCapture", "OriginalProducer",
                                  "RecoveryReceiptSHA256", "RegistryExportSHA256", "DefinitionIDs",
                                  "OriginalCapturedMembersReplaced"],
              root["Contract"] == .string("pinkha-recovered-compiled-definition-sidecar-v1"),
              root["OriginalCapturedMembersReplaced"] == .bool(false),
              let capture = root["OriginalCapture"], let captureFields = capture.object,
              Set(captureFields.keys) == ["ManifestSHA256", "SourceWitnessSHA256", "AccountSHA256", "SpaceSHA256"],
              capture["ManifestSHA256"] == .string(bundle.manifestSHA256),
              capture["SourceWitnessSHA256"] == .string(bundle.sourceWitnessSHA256),
              capture["AccountSHA256"] == .string(AnyContentDigest.sha256(Data(bundle.sourceAccountID.utf8))),
              capture["SpaceSHA256"] == .string(AnyContentDigest.sha256(Data(bundle.sourceSpaceID.utf8))),
              let authority = root["OriginalProducer"], let authorityFields = authority.object,
              Set(authorityFields.keys) == ["ReceiptSHA256", "SourceArchiveSHA256", "SourceManifestSHA256",
                                          "NativeBinarySHA256", "HeartCommit"],
              authorityFields.values.allSatisfy({ value in
                  guard let value = value.string else { return false }
                  return Self.digest(value) || Self.commit(value)
              }),
              let heart = authority["HeartCommit"]?.string, Self.commit(heart),
              let producerHash = authority["ReceiptSHA256"]?.string, Self.digest(producerHash),
              let sourceManifestHash = authority["SourceManifestSHA256"]?.string, Self.digest(sourceManifestHash),
              let sourceArchiveHash = authority["SourceArchiveSHA256"]?.string, Self.digest(sourceArchiveHash),
              let binaryHash = authority["NativeBinarySHA256"]?.string, Self.digest(binaryHash),
              let recoveryHash = root["RecoveryReceiptSHA256"]?.string, Self.digest(recoveryHash),
              let exportHash = root["RegistryExportSHA256"]?.string, Self.digest(exportHash),
              AnyContentDigest.sha256(originalProducer) == producerHash,
              AnyContentDigest.sha256(recoveryReceipt) == recoveryHash,
              AnyContentDigest.sha256(registryExport) == exportHash else {
            throw AnyHeartNativeRecoveredDefinitionError.invalidBinding
        }
        let producer = try Self.decode(originalProducer, maximum: 4_194_304)
        let recovery = try Self.decode(recoveryReceipt, maximum: 4_194_304)
        let exported = try Self.decode(registryExport, maximum: 4_194_304)
        // The original producer's overall FAIL remains recorded. This path
        // qualifies only its source identity and the separate successful recovery.
        guard producer["compiled_source_unchanged"] == .bool(true),
              producer["source"]?["manifest_sha256"] == .string(sourceManifestHash),
              producer["input_sha256"]?["source"] == .string(sourceArchiveHash),
              producer["binary"]?["sha256"] == .string(binaryHash),
              producer["heart_sha"] == .string(heart),
              recovery["protocol"] == .string("pinkha-original-source-compiled-definition-recovery-v1"),
              recovery["status"] == .string("PASS_RECOVERED_ORIGINAL_SEVEN_DESCRIPTORS_NOT_CAPTURED_MEMBERS"),
              recovery["originalSourceManifestSHA256"] == .string(sourceManifestHash),
              recovery["originalSourceArchiveSHA256"] == .string(sourceArchiveHash),
              recovery["originalNativeBinarySHA256"] == .string(binaryHash),
              recovery["heartCommit"] == .string(heart),
              recovery["originalProducerAuthority"]?["producerSHA256"] == .string(producerHash),
              recovery["originalProducerAuthority"]?["originalNativeBinarySHA256"] == .string(binaryHash),
              recovery["originalProducerAuthority"]?["originalProducerStatus"] == producer["status"],
              recovery["exportManifestSHA256"] == .string(exportHash),
              recovery["original59826SourceFilesUnchanged"] == .bool(true),
              recovery["originalCompiledWireAndFullDecodedModelEqual"] == .bool(true),
              recovery["originalCapturedMembersReplaced"] == .bool(false),
              recovery["sourceAdmission"] == .bool(false),
              recovery["destinationWrites"] == .bool(false),
              recovery["accountOrSpaceCalls"] == .integer(0),
              recovery["nativeEngineBuilds"] == .integer(0),
              let compiledCount = recovery["compiledInputFiles"]?.integer, compiledCount > 0,
              let exportFields = exported.object,
              Set(exportFields.keys) == ["Contract", "Origin", "Descriptors", "ProtobufDecodeEqualsRegistry",
                                        "JSONDecodeEqualsRegistry", "RegistryUnchangedAfterExport",
                                        "OriginalCapturedMember", "AccountOrSpaceOpened", "DestinationWrites"],
              exported["Contract"] == .string("pinkha-recovered-compiled-definition-export-v1"),
              exported["Origin"] == .string("original-source-registry-recovery-not-historical-captured-members"),
              exported["ProtobufDecodeEqualsRegistry"] == .bool(true),
              exported["JSONDecodeEqualsRegistry"] == .bool(true),
              exported["RegistryUnchangedAfterExport"] == .bool(true),
              exported["OriginalCapturedMember"] == .bool(false),
              exported["AccountOrSpaceOpened"] == .bool(false),
              exported["DestinationWrites"] == .bool(false),
              let rows = exported["Descriptors"]?.array,
              recovery["descriptors"] == .array(rows),
              let declared = root["DefinitionIDs"]?.array else {
            throw AnyHeartNativeRecoveredDefinitionError.invalidEvidence
        }
        guard !rows.isEmpty, rows.count <= 1024, declared.count == rows.count else {
            throw AnyHeartNativeRecoveredDefinitionError.limit
        }
        let declaredIDs = try declared.map { value -> String in
            guard let id = value.string, id.hasPrefix("property:"), id.utf8.count <= 4096 else {
                throw AnyHeartNativeRecoveredDefinitionError.invalidDescriptor
            }
            return id
        }
        guard Set(declaredIDs).count == declaredIDs.count,
              Set(declaredIDs.map { Data($0.utf8) }).count == declaredIDs.count else {
            throw AnyHeartNativeRecoveredDefinitionError.invalidDescriptor
        }
        var members: [AnyHeartNativeSpaceBundle.Member] = []
        var paths = Set<String>(), total = 0
        func member(_ value: AnyJSON?, path: String, maximum: Int) throws -> Data {
            guard let value, let fields = value.object,
                  Set(fields.keys) == ["Path", "SHA256", "Bytes"],
                  value["Path"] == .string(path),
                  let hash = value["SHA256"]?.string, Self.digest(hash),
                  let count = value["Bytes"]?.integer, count > 0, count <= Int64(maximum),
                  paths.insert(path).inserted, total <= 16_777_216 - Int(count) else {
                throw AnyHeartNativeRecoveredDefinitionError.invalidDescriptor
            }
            let descriptor = AnyHeartNativeSpaceBundle.Member(path: path, sha256: hash, byteCount: Int(count))
            let bytes = try memberData(descriptor)
            guard bytes.count == Int(count), AnyContentDigest.sha256(bytes) == hash else {
                throw AnyHeartNativeRecoveredDefinitionError.invalidDescriptor
            }
            total += bytes.count; members.append(descriptor)
            return bytes
        }
        let definitions = try rows.map { row -> AnyHeartNativeBundledDefinition in
            guard let fields = row.object,
                  Set(fields.keys) == ["Kind", "Key", "ProtobufMessage", "Protobuf", "JSONView"],
                  row["Kind"] == .string("property"), let key = row["Key"]?.string,
                  row["ProtobufMessage"] == .string("anytype.model.Relation") else {
                throw AnyHeartNativeRecoveredDefinitionError.invalidDescriptor
            }
            let base = AnyContentDigest.sha256(Data(("property:" + key).utf8))
            return try AnyHeartNativeBundledDefinition(kind: "property", key: key,
                protobufMessage: "anytype.model.Relation",
                protobuf: member(row["Protobuf"], path: base + ".pb", maximum: 1_048_576),
                jsonView: member(row["JSONView"], path: base + ".json", maximum: 4_194_304))
        }
        guard definitions.map(\.identity) == declaredIDs else {
            throw AnyHeartNativeRecoveredDefinitionError.invalidDescriptor
        }
        manifestSHA256 = expectedManifestSHA256
        captureManifestSHA256 = bundle.manifestSHA256
        sourceWitnessSHA256 = bundle.sourceWitnessSHA256
        sourceAccountSHA256 = AnyContentDigest.sha256(Data(bundle.sourceAccountID.utf8))
        sourceSpaceSHA256 = AnyContentDigest.sha256(Data(bundle.sourceSpaceID.utf8))
        originalProducerSHA256 = producerHash
        originalSourceManifestSHA256 = sourceManifestHash
        originalNativeBinarySHA256 = binaryHash
        recoveryReceiptSHA256 = recoveryHash
        exportManifestSHA256 = exportHash
        manifestBytes = manifest; originalProducerBytes = originalProducer
        recoveryReceiptBytes = recoveryReceipt; exportManifestBytes = registryExport
        self.definitions = definitions; verifiedMembers = members
        try validate(bundle: bundle)
    }

    public func validate(bundle: AnyHeartNativeSpaceBundle) throws {
        let captured = Set(bundle.bundledDefinitions.map { Data($0.identity.utf8) })
        let missing = bundle.bundledDefinitionsUsed.map { Data($0.utf8) }.filter { !captured.contains($0) }
        guard bundle.manifestSHA256 == captureManifestSHA256,
              bundle.sourceWitnessSHA256 == sourceWitnessSHA256,
              AnyContentDigest.sha256(Data(bundle.sourceAccountID.utf8)) == sourceAccountSHA256,
              AnyContentDigest.sha256(Data(bundle.sourceSpaceID.utf8)) == sourceSpaceSHA256,
              !missing.isEmpty, Set(missing).count == missing.count,
              Set(missing) == Set(definitions.map { Data($0.identity.utf8) }),
              captured.isDisjoint(with: definitions.map { Data($0.identity.utf8) }) else {
            throw AnyHeartNativeRecoveredDefinitionError.invalidBinding
        }
    }

    private static func decode(_ data: Data, maximum: Int) throws -> AnyJSON {
        guard !data.isEmpty, data.count <= maximum else { throw AnyHeartNativeRecoveredDefinitionError.limit }
        let value = try JSONDecoder().decode(AnyJSON.self, from: data)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: data, encoded: encoder.encode(value))
        return value
    }
    private static func digest(_ text: String) -> Bool {
        text.utf8.count == 64 && text.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func commit(_ text: String) -> Bool {
        text.utf8.count == 40 && text.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
}
