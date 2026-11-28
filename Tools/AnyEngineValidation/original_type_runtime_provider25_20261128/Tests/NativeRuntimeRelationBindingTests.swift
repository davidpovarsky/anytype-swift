import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// These controls use the actual retained eight source definitions. They do not
/// assert native quota, sync, navigation or permission behavior before a real
/// current provider is qualified.
final class NativeRuntimeRelationBindingTests: XCTestCase {
    func testOriginalEightRuntimeDefinitionsPreserveExactIdentityAndWritability() throws {
        for row in originals {
            let evidence = try load(row)
            let binding = try AnyHeartNativeRuntimeRelationBinding(evidence: evidence)
            XCTAssertEqual(binding.role, row.role)
            XCTAssertEqual(binding.scope, row.scope)
            XCTAssertEqual(binding.evidence.protobufBytes, evidence.protobufBytes)
            XCTAssertEqual(binding.evidence.jsonViewBytes, evidence.jsonViewBytes)
            XCTAssertEqual(binding.evidence.snapshotSHA256, row.snapshotSHA256)
            XCTAssertEqual(binding.evidence.viewSHA256, row.viewSHA256)
            XCTAssertEqual(evidence.snapshot.details["relationReadonlyValue"]?.bool,
                row.role.sourceDeclaresReadonlyValue)
            XCTAssertFalse(binding.permitsDestinationWrites)
            XCTAssertEqual(try JSONDecoder().decode(AnyHeartNativeRuntimeRelationBinding.self,
                from: JSONEncoder().encode(binding)), binding)
            XCTAssertEqual(try load(row), evidence)
        }
        XCTAssertFalse(AnyHeartNativeRuntimeRelationBinding.Role.spaceAccessType.sourceDeclaresReadonlyValue)
        XCTAssertFalse(AnyHeartNativeRuntimeRelationBinding.Role.spaceDashboardId.sourceDeclaresReadonlyValue)
    }

    func testOriginalRuntimeDefinitionOverridesCannotSelectBuiltinProviders() throws {
        for row in originals {
            let original = try load(row)
            let readonly = try XCTUnwrap(original.snapshot.details["relationReadonlyValue"]?.bool)
            let mutations: [(String, AnyJSON)] = [
                ("name", .string("changed name")), ("description", .string("changed semantics")),
                ("relationKey", .string("custom_" + row.role.rawValue)),
                ("relationFormat", .integer(109)), ("relationMaxCount", .integer(0)),
                ("relationReadonlyValue", .bool(!readonly)), ("relationDefaultValue", .integer(0)),
                ("relationFormatObjectTypes", .array([.string("foreign-type")])),
                ("isHidden", .bool(false)), ("revision", .integer(20)),
                ("apiObjectKey", .string("foreign_role")), ("unknownSemanticField", .bool(true)),
            ]
            for (key, value) in mutations {
                XCTAssertThrowsError(try AnyHeartNativeRuntimeRelationBinding(
                    evidence: replacing(original, detail: (key, value))), "\(row.role):\(key)")
            }
            XCTAssertThrowsError(try AnyHeartNativeRuntimeRelationBinding(
                evidence: replacing(original, nativeType: 528)))
            XCTAssertThrowsError(try AnyHeartNativeRuntimeRelationBinding(
                evidence: replacing(original, uniqueKey: "rel-custom")))
            XCTAssertEqual(try load(row), original)
        }
    }

    func testDecodeRevalidatesRuntimeRoleVersionAndOriginalEvidence() throws {
        let source = try load(originals[0])
        let binding = try AnyHeartNativeRuntimeRelationBinding(evidence: source)
        let encoded = try JSONEncoder().encode(binding)
        let original = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: encoded).object)
        for (key, value) in [("role", AnyJSON.string("writersLimit")),
                             ("readContract", .string("pinkha-heart-runtime-relation-v2"))] {
            var changed = original
            changed[key] = value
            XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartNativeRuntimeRelationBinding.self,
                from: JSONEncoder().encode(AnyJSON.object(changed))))
        }
        let altered = try replacing(source, detail: ("relationReadonlyValue", .bool(false)))
        var changed = original
        changed["evidence"] = try JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(altered))
        XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartNativeRuntimeRelationBinding.self,
            from: JSONEncoder().encode(AnyJSON.object(changed))))
    }

    private typealias Original = (role: AnyHeartNativeRuntimeRelationBinding.Role, stem: String,
        snapshotSHA256: String, viewSHA256: String, scope: AnyHeartNativeRuntimeRelationBinding.Scope)
    private var originals: [Original] { [
        (.readersLimit, "59beae6c4e9a256dad78c25a641f0afc635929168a2ff4b4e4f47e8fc4159a17", "280bc38231f8b30b3f87cdc1dac438f817b07403225b562254652db4ede6b046", "72fe7e4ca9a516217cffc2934a634ec5bc69e64b97d9468cbc27e52dfcce707d", .space),
        (.writersLimit, "69742643acafff6246682d26170fdc115bc795570df5ff8cf44956e29dcba9d1", "4b5dd42f9bafaf208e569763610a93d7d24a6acab3fd97fe01ffddf7ae82fd5a", "c5c30842198bdc64709dbfa171cb4dae9431276629cadcb11fe9abb8fc41ba55", .space),
        (.sharedSpacesLimit, "05c09ed6099f225ed0304ef10babe60417dcfd903280b221c5b0bde8fda08f3f", "d9d91a50d846683b06af7d120a07c91287d22617978757a18138444a9bcbc243", "7eb83cb7c647e1122f3f54d17c261090cfc10a20bb9df9fabdc80e75f777c03e", .account),
        (.syncDate, "3f815c994128a532a324921aa0f573d8fa93ea9a45624c48702f52329e23a278", "e385520891c9fc2168aec2ee2d23b6779ee08318a1b766a04fee44722b4d0898", "f447323294f5ca78f7449864d697d3f72a24426e7e213a720dfe76837a6638bf", .object),
        (.syncError, "2ba05a673defe9f18d42ffd939320402e51e22e189712f6c3850ec7969f0c5a0", "458f4bf5f06a08b2110416b2adadcdccb9dad5fd373f7a09b8ed13d8eed75208", "f1ef3884ebf5578cbcfd8f98308ef69d31ef94002da6568965354c86e33768ab", .object),
        (.syncStatus, "2b37b301b86d522b8cade3e9db9ef997de78e3dcf35c37359d334551d5ac0c63", "6558a9f062728d61e82e7c5b0783f71b1ed00b688bae1768d7692a6da41a4b5d", "978580a6ec635e70b191515666129f640b9b037aa29f2733a992ca8d22c86a4b", .object),
        (.spaceAccessType, "f640f69d32067e4fa902565077553ccf2efec13139a9910c5538f309adc6e016", "cb35396d07efdbe6b20b744ca45e0622c8e496bdb08da747a3d02271dafd4ac4", "74012db0e221c2eb11dc3002eda602e98ef2120e8c1b9763e031a3cace4b368e", .space),
        (.spaceDashboardId, "a41b4835406ebe08515fe7fa72b2a37d07e5c812a5676fa1bdfedcf9f002ffca", "03bdaf43beaea17dabd87f89971e15c37faa5382259e650f6f99e309b37fc9d3", "08122a11df2638f9261df0252632f0a52480510d15ff0ea8a7179a00f136e873", .space),
    ] }

    private func load(_ row: Original) throws -> AnyDestinationDefinitionEvidence {
        guard let directory = ProcessInfo.processInfo.environment["PINKHA_NATIVE_ORIGINAL156"] else {
            throw FixtureError.missingQualifiedSource
        }
        let bundle = URL(fileURLWithPath: directory, isDirectory: true).appendingPathComponent("bundle")
        let stem = "snapshot-" + row.stem
        let json = try Data(contentsOf: bundle.appendingPathComponent(stem + ".json"))
        let protobuf = try Data(contentsOf: bundle.appendingPathComponent(stem + ".pb"))
        guard AnyContentDigest.sha256(json) == row.viewSHA256,
              AnyContentDigest.sha256(protobuf) == row.snapshotSHA256 else { throw FixtureError.changedSource }
        let view = try JSONDecoder().decode(AnyJSON.self, from: json)
        let space = try XCTUnwrap(view["SpaceID"]?.string), object = try XCTUnwrap(view["ObjectID"]?.string)
        return try .init(sourceSpaceID: space, sourceObjectID: object, protobufBytes: protobuf, jsonViewBytes: json)
    }

    /// Explicitly altered JSON is adversarial component input, not another
    /// native capture. It must fail the provider descriptor admission.
    private func replacing(_ original: AnyDestinationDefinitionEvidence,
                           detail: (String, AnyJSON)? = nil,
                           nativeType: Int64? = nil, uniqueKey: String? = nil) throws -> AnyDestinationDefinitionEvidence {
        var view = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: original.jsonViewBytes).object)
        if let detail {
            var snapshot = try XCTUnwrap(view["Snapshot"]?.object)
            var details = try XCTUnwrap(snapshot["details"]?.object)
            details[detail.0] = detail.1
            snapshot["details"] = .object(details); view["Snapshot"] = .object(snapshot)
        }
        if let nativeType { view["NativeType"] = .integer(nativeType) }
        if let uniqueKey { view["UniqueKey"] = .string(uniqueKey) }
        return try .init(sourceSpaceID: original.sourceSpaceID, sourceObjectID: original.sourceObjectID,
            protobufBytes: original.protobufBytes,
            jsonViewBytes: AnyDestinationDefinitionChecks.bytes(.object(view)))
    }

    private enum FixtureError: Error { case missingQualifiedSource, changedSource }
}
