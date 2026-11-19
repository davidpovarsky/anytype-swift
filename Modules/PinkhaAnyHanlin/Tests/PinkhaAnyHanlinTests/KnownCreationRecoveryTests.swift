import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
@testable import PinkhaHanlinCore

final class KnownCreationRecoveryTests: XCTestCase {
    fileprivate static func identity(account: String = "recovery-account") throws -> PinkhaHanlinWriteIdentity {
        let session = HanlinHostSession(conversationID: UUID(), context: .init(
            namespace: try .init(app: "anytype", account: account, workspace: "space", space: "space"),
            sceneID: UUID(), generation: UUID(), localeIdentifier: "he"))
        return .init(session: session, invocationID: try .init(validating: UUID().uuidString.lowercased()),
            runID: UUID(), step: 0, providerCallDigest: String(repeating: "a", count: 64),
            argumentsDigest: PinkhaHanlinCreatePagePlan.digest(Data("synthetic private title".utf8)),
            envelopeDigest: String(repeating: "c", count: 64), deadline: Date(timeIntervalSince1970: 1000))
    }
    private func entry(_ identity: PinkhaHanlinWriteIdentity, effect: PinkhaHanlinWriteJournal.Effect,
                       id: String? = nil) -> PinkhaHanlinWriteJournal.Entry {
        .init(version: 1, identity: identity, effect: effect, createdObjectReference: id)
    }

    func testKnownRootRemainsUncertainUntilVerifiedMatchingCommit() throws {
        let identity = try Self.identity()
        let recovery = PinkhaHanlinKnownObjectRecovery(version: 1, identity: identity,
                                                        createdObjectReference: "known-native-root")
        let uncertain = entry(identity, effect: .uncertain)
        XCTAssertNoThrow(try recovery.validate(against: entry(identity, effect: .reserved)))
        XCTAssertNoThrow(try recovery.validate(against: uncertain))
        XCTAssertEqual(uncertain.effect, .uncertain)
        XCTAssertNil(uncertain.createdObjectReference)
        XCTAssertNoThrow(try recovery.validate(against: entry(identity, effect: .committed, id: "known-native-root")))
        XCTAssertThrowsError(try recovery.validate(against: entry(identity, effect: .committed, id: "another-root")))
        XCTAssertThrowsError(try recovery.validate(against: entry(identity, effect: .notDispatched)))
    }

    func testRecoveryCannotRetargetAnotherOriginalIdentity() throws {
        let original = try Self.identity(), another = try Self.identity(account: "another-account")
        let recovery = PinkhaHanlinKnownObjectRecovery(version: 1, identity: original,
                                                        createdObjectReference: "known-native-root")
        XCTAssertThrowsError(try recovery.validate(against: entry(another, effect: .reserved)))
        for id in ["", String(repeating: "x", count: 257), "bad\u{0}root"] {
            XCTAssertThrowsError(try PinkhaHanlinKnownObjectRecovery(
                version: 1, identity: original, createdObjectReference: id)
                .validate(against: entry(original, effect: .reserved)))
        }
    }

    func testRecoveryDecoderRejectsForeignNamespaceUnknownBusinessPayloadAndWrongFilename() throws {
        let identity = try Self.identity()
        let recovery = PinkhaHanlinKnownObjectRecovery(version: 1, identity: identity,
                                                        createdObjectReference: "known-native-root")
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(recovery)
        let name = identity.key + PinkhaHanlinKnownObjectRecovery.suffix
        let namespace = identity.session.context.namespace
        XCTAssertEqual(try PinkhaHanlinKnownObjectRecovery.decode(bytes, fileName: name, namespace: namespace), recovery)
        XCTAssertThrowsError(try PinkhaHanlinKnownObjectRecovery.decode(bytes, fileName: "other.known-object", namespace: namespace))
        let foreign = try HanlinConversationNamespace(app: "anytype", account: "other", workspace: "space", space: "space")
        XCTAssertThrowsError(try PinkhaHanlinKnownObjectRecovery.decode(bytes, fileName: name, namespace: foreign))
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        object["businessPayload"] = "must not be accepted as metadata"
        let altered = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        XCTAssertThrowsError(try PinkhaHanlinKnownObjectRecovery.decode(altered, fileName: name, namespace: namespace))
    }

    func testRecoveryMetadataDoesNotContainOriginalTitleOrChangeLegacyEntryShape() throws {
        let identity = try Self.identity()
        let recovery = PinkhaHanlinKnownObjectRecovery(version: 1, identity: identity,
                                                        createdObjectReference: "known-native-root")
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let text = String(decoding: try encoder.encode(recovery), as: UTF8.self)
        XCTAssertFalse(text.contains("synthetic private title"))
        let legacy = entry(identity, effect: .uncertain)
        let bytes = try encoder.encode(legacy)
        let keys = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any]).keys
        XCTAssertEqual(Set(keys), ["version", "identity", "effect"])
        XCTAssertEqual(try JSONDecoder().decode(PinkhaHanlinWriteJournal.Entry.self, from: bytes), legacy)
    }
}

#if os(iOS)
final class KnownCreationRecoveryFilesystemTests: XCTestCase {
    @MainActor
    func testKnownPartialRootSurvivesReopenWithoutChangingV1OutcomeBytes() async throws {
        let identity = try KnownCreationRecoveryTests.identity()
        let parent = try temporaryParent()
        defer { try? FileManager.default.removeItem(at: parent) }
        try await seedUncertainKnownObject(parent: parent, identity: identity)
        let reopened = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: identity.session.context.namespace)
        let entry = try await reopened.receipt(for: identity)
        let known = try await reopened.knownCreatedObjectReference(for: identity)
        XCTAssertEqual(entry?.effect, .uncertain)
        XCTAssertNil(entry?.createdObjectReference)
        XCTAssertEqual(known, "native-partial-root")
        let committed = try await reopened.record(.committed, identity: identity, createdObjectReference: "native-partial-root")
        XCTAssertEqual(committed.effect, .committed)
    }

    @MainActor
    func testDifferentRootAndNoEffectCannotReplaceDurableKnownRoot() async throws {
        let identity = try KnownCreationRecoveryTests.identity()
        let parent = try temporaryParent()
        defer { try? FileManager.default.removeItem(at: parent) }
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: identity.session.context.namespace)
        try await journal.reserve(identity)
        try await journal.recordKnownIncompleteObject("native-partial-root", identity: identity)
        _ = try await journal.record(.uncertain, identity: identity)
        do { try await journal.recordKnownIncompleteObject("another-root", identity: identity); XCTFail("root changed") } catch {}
        do { _ = try await journal.record(.committed, identity: identity, createdObjectReference: "another-root"); XCTFail("wrong root committed") } catch {}
        do { _ = try await journal.record(.notDispatched, identity: identity); XCTFail("known effect erased") } catch {}
        let receipt = try await journal.receipt(for: identity)
        let known = try await journal.knownCreatedObjectReference(for: identity)
        XCTAssertEqual(receipt?.effect, .uncertain)
        XCTAssertEqual(known, "native-partial-root")
    }

    @MainActor
    func testRecordedNoDispatchCannotAcquireAKnownNativeRoot() async throws {
        let identity = try KnownCreationRecoveryTests.identity()
        let parent = try temporaryParent()
        defer { try? FileManager.default.removeItem(at: parent) }
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: identity.session.context.namespace)
        try await journal.reserve(identity)
        _ = try await journal.record(.notDispatched, identity: identity)
        do { try await journal.recordKnownIncompleteObject("native-root", identity: identity); XCTFail("contradictory sidecar accepted") } catch {}
        let known = try await journal.knownCreatedObjectReference(for: identity)
        XCTAssertNil(known)
    }

    private func temporaryParent() throws -> URL {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("hanlin-known-root-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        return directory
    }

    private func outcomeBytes(_ parent: URL) throws -> [String: Data] {
        guard let enumerator = FileManager.default.enumerator(at: parent, includingPropertiesForKeys: nil) else {
            throw PinkhaHanlinWriteError.unavailable
        }
        var result: [String: Data] = [:]
        for case let path as URL in enumerator {
            if path.pathExtension == "reserved" || path.pathExtension == "uncertain" {
                result[path.lastPathComponent] = try Data(contentsOf: path)
            }
        }
        return result
    }

    private func seedUncertainKnownObject(parent: URL, identity: PinkhaHanlinWriteIdentity) async throws {
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: identity.session.context.namespace)
        try await journal.reserve(identity)
        _ = try await journal.record(.uncertain, identity: identity)
        let before = try outcomeBytes(parent)
        XCTAssertEqual(before.count, 2)
        try await journal.recordKnownIncompleteObject("native-partial-root", identity: identity)
        XCTAssertEqual(try outcomeBytes(parent), before)
    }
}
#endif
