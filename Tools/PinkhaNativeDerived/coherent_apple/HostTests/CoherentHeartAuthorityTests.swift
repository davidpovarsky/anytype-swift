import Foundation
import Lib
import PinkhaKit
import XCTest
@testable import PinkhaHeartEngine

/// One new actual Apple journey. The explicitly tagged native fixture uses its
/// own local-only account and signed ACL records. Its bytes then pass through
/// the unchanged shared Swift decoder. This is not full App acceptance and
/// does not assert that the separate production binary executed.
final class CoherentHeartAuthorityTests: XCTestCase {
    func testActualCombinedLibSignedAuthorityAndSharedSwiftDecoding() throws {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "host-config", withExtension: "json"))
        let configuration = try JSONDecoder().decode(Configuration.self, from: Data(contentsOf: url))
        let request = try JSONSerialization.data(withJSONObject: [
            "nonce": configuration.nonce, "bridge_sha256": configuration.bridgeSHA,
            "runtime_version": configuration.runtimeVersion
        ], options: [.sortedKeys])
        let raw = try XCTUnwrap(ServicePinkhaCoherentAppleAuthorityFixture(request))
        guard raw.count < 4 * 1024 * 1024 else { throw Failure.oversized }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let native = try decoder.decode(NativeResult.self, from: raw)
        let names = Set(["ownership.json", "native-observation.json", "coherent-observation.json",
                         "coherent-owner.pb", "coherent-reader.pb", "coherent-removed.pb",
                         "object-search-removed.pb", "object-show-removed.pb"])
        guard native.status == "PASS_ACTUAL_COHERENT_APPLE_FIXTURE", native.nonce == configuration.nonce,
              native.pid == Int(ProcessInfo.processInfo.processIdentifier),
              native.bridgeSha256 == configuration.bridgeSHA,
              native.originalFixtureSha256 == configuration.originalFixtureSHA,
              native.runtimeVersion == configuration.runtimeVersion,
              native.heartSha == "d98420b1113536afd08cde6de9a5816f6d27ffff",
              native.fixtureTag == "pinkha_coherent_apple_fixture", !native.productionBinaryExecuted,
              native.networkAclTransport == "NOT_RUN", native.fullAppAcceptance == "NOT_RUN",
              Set(native.files.keys) == names, Set(native.filesSha256.keys) == names,
              native.operationId == configuration.nonce else { throw Failure.nativeIdentity }
        for (name, bytes) in native.files {
            guard !bytes.isEmpty, bytes.count < 2 * 1024 * 1024,
                  HeartNativeOperationCanonical.digest(bytes) == native.filesSha256[name] else { throw Failure.rawEvidence }
        }
        let scope = try TorahOperationReadScope(engine: .heart, accountID: native.accountId,
                                               spaceID: native.spaceId, sessionGeneration: UUID())
        let owner = try HeartAuthorizedOperationCodec.decode(try XCTUnwrap(native.files["coherent-owner.pb"]),
                                                             operationID: native.operationId, scope: scope)
        let reader = try HeartAuthorizedOperationCodec.decode(try XCTUnwrap(native.files["coherent-reader.pb"]),
                                                              operationID: native.operationId, scope: scope)
        guard owner.outcome == .found, reader.outcome == .found,
              owner.variants.count == 1, reader.variants == owner.variants,
              owner.nativeSnapshotToken != reader.nativeSnapshotToken,
              let variant = owner.variants.first, variant.authorID == native.accountId,
              variant.reachability == .liveBlock, variant.provenance.count == 1,
              variant.provenance.first?.creator == native.accountId else { throw Failure.sharedDecode }
        let removedError: String
        do {
            _ = try HeartAuthorizedOperationCodec.decode(try XCTUnwrap(native.files["coherent-removed.pb"]),
                                                         operationID: native.operationId, scope: scope)
            throw Failure.revokedPayload
        } catch let error as TorahOperationReadError {
            switch error {
            case .permissionDenied: removedError = "permissionDenied"
            case .snapshotChanged: removedError = "snapshotChanged"
            default: throw error
            }
        }
        let coherent = try JSONSerialization.jsonObject(with: try XCTUnwrap(native.files["coherent-observation.json"])) as? [String: Any]
        let nativeT5 = try JSONSerialization.jsonObject(with: try XCTUnwrap(native.files["native-observation.json"])) as? [String: Any]
        guard coherent?["status"] as? String == "PASS_COHERENT_SIGNED_AUTHORITY",
              coherent?["canonical_sha256"] as? String == HeartNativeOperationCanonical.digest(variant.canonicalBytes),
              coherent?["removed_has_payload"] as? Bool == false,
              coherent?["account_stop_verified"] as? Bool == true,
              nativeT5?["status"] as? String == "PASS_LOCAL_SIGNED_REVOCATION",
              nativeT5?["object_search_rows"] as? Int == 0, nativeT5?["object_search_total"] as? Int == 0,
              nativeT5?["object_show_has_payload"] as? Bool == false,
              nativeT5?["read_key_rotated"] as? Bool == true,
              nativeT5?["native_acl_updater"] as? String == "NOT_REPLACED_OR_SUPPRESSED" else { throw Failure.rawEvidence }
        let observation: [String: Any] = [
            "status": "PASS_COHERENT_HEART_IOS_FIXTURE_AND_SWIFT_CODEC",
            "app_sha": configuration.appSHA, "run_id": configuration.runID,
            "run_attempt": configuration.runAttempt, "nonce": configuration.nonce,
            "pid": Int(ProcessInfo.processInfo.processIdentifier),
            "native": try JSONSerialization.jsonObject(with: raw),
            "shared_swift_codec": ["owner_decoded": true, "reader_decoded": true, "exact_variants": true,
                                   "removed_rejected": true, "removed_error": removedError],
            "production_binary_execution": "NOT_RUN", "full_app_acceptance": "NOT_RUN",
            "network_acl_transport": "NOT_RUN", "fresh_ios_process_reopen": "NOT_RUN"
        ]
        let data = try JSONSerialization.data(withJSONObject: observation, options: [.sortedKeys])
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = "coherent-heart-ios-proof-" + configuration.nonce + ".json"
        attachment.lifetime = .keepAlways
        add(attachment)
        print("PINKHA_COHERENT_HEART_IOS_PASS " + configuration.nonce)
    }

    private struct Configuration: Decodable {
        let appSHA, runID, runAttempt, nonce, bridgeSHA, originalFixtureSHA, runtimeVersion: String
    }
    private struct NativeResult: Decodable {
        let status, nonce, bridgeSha256, originalFixtureSha256, runtimeVersion, heartSha: String
        let accountId, spaceId, operationId, fixtureTag, networkAclTransport, fullAppAcceptance: String
        let pid: Int
        let productionBinaryExecuted: Bool
        let files: [String: Data]
        let filesSha256: [String: String]
    }
    private enum Failure: Error {
        case oversized, nativeIdentity, rawEvidence, sharedDecode, revokedPayload
    }
}
