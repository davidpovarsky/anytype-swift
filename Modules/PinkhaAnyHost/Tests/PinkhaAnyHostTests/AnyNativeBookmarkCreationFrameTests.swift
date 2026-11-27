import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
import XCTest
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

final class AnyNativeBookmarkCreationFrameTests: XCTestCase, @unchecked Sendable {
    private func workspace() throws -> AnyTorahWorkspace {
        try .init(accountID: "account", spaceID: "space")
    }

    private func response(_ changes: [String: AnyJSON] = [:]) -> AnyJSON {
        .object([
            "contract": .string("pinkha-native-bookmark-create-v1"), "version": .integer(1),
            "accountId": .string("account"), "spaceId": .string("space"), "typeId": .string("bookmark-type"),
            "collections": .array([.string("url-owner")]), "propertyOwnerId": .string("url-owner"),
            "propertyId": .string("url"), "canWrite": .bool(true),
            "frame": .string(Self.token(Data("opaque-native-condition".utf8)))
        ].merging(changes) { _, replacement in replacement })
    }

    private func parse(_ value: AnyJSON, typeID: String = "bookmark-type", requested: [String] = []) throws
        -> AnyNativeBookmarkCreationFrame {
        try .init(value: value, workspace: workspace(), typeID: typeID, requestedCollections: requested)
    }

    private static func token(_ raw: Data) -> String {
        raw.base64EncodedString().replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
    }

    private func creationIntent(frame: String? = nil) throws -> AnyNativeObjectCreationIntent {
        try .init(workspace: workspace(), mutationID: String(repeating: "a", count: 32),
            typeID: "bookmark-type", collections: ["z", "url-owner"], initialProperties: .object([
                "any": .object(["name": .string("Bookmark")]),
                "url-owner": .object(["url": .string("https://example.invalid/bookmark")])
            ]), bookmarkDefinitionFrame: frame)
    }

    func testClosedResponseRequiresEveryKeyAndStrictFieldTypes() throws {
        let original = try XCTUnwrap(response().object)
        for key in original.keys {
            var missing = original
            missing.removeValue(forKey: key)
            XCTAssertThrowsError(try parse(.object(missing)), "missing \(key)")
        }
        XCTAssertThrowsError(try parse(response(["unknown": .bool(true)])))
        let malformed: [(String, AnyJSON)] = [
            ("contract", .string("another-contract")), ("version", .integer(2)), ("version", .number(1.5)),
            ("accountId", .integer(1)), ("spaceId", .null), ("typeId", .array([])),
            ("collections", .string("url-owner")), ("collections", .array([.integer(1)])),
            ("propertyOwnerId", .bool(true)), ("propertyId", .integer(1)),
            ("canWrite", .integer(1)), ("frame", .object([:]))
        ]
        for (key, value) in malformed {
            XCTAssertThrowsError(try parse(response([key: value])), "wrong type/value for \(key)")
        }
    }

    func testExactScopeAndNativeIdentifierBounds() throws {
        for key in ["accountId", "spaceId", "typeId"] {
            XCTAssertThrowsError(try parse(response([key: .string("foreign")])))
        }
        for invalid in ["", "contains space", "line\nfeed", "nul\u{0}", "é", String(repeating: "a", count: 1_025)] {
            XCTAssertThrowsError(try parse(response(["propertyOwnerId": .string(invalid),
                "collections": .array([.string(invalid)])])))
            XCTAssertThrowsError(try parse(response(["typeId": .string(invalid)]), typeID: invalid))
        }
        for invalid in ["", "nul\u{0}", String(repeating: "א", count: 513)] {
            XCTAssertThrowsError(try parse(response(["propertyId": .string(invalid)])))
        }
        let propertyID = "כתובת-e\u{301}"
        let frame = try parse(response(["propertyId": .string(propertyID), "canWrite": .bool(false)]))
        XCTAssertEqual(Array(frame.propertyID.utf8), Array(propertyID.utf8))
        XCTAssertFalse(frame.canWrite)
        let maxID = String(repeating: "a", count: 1_024)
        XCTAssertNoThrow(try parse(response(["typeId": .string(maxID)]), typeID: maxID))
    }

    func testCollectionsAreExactlyTheSortedUniqueRequestedOwnerUnion() throws {
        let requested = ["z", "A", "z"]
        let expected = ["A", "url-owner", "z"]
        let correct = response(["collections": .array(expected.map(AnyJSON.string))])
        XCTAssertEqual(try parse(correct, requested: requested).collections, expected)
        for invalid in [["A", "z", "url-owner"], ["A", "url-owner", "z", "z"],
                        ["A", "url-owner"], ["A", "extra", "url-owner", "z"]] {
            XCTAssertThrowsError(try parse(response(["collections": .array(invalid.map(AnyJSON.string))]), requested: requested))
        }
        for forbidden in ["any", "bin", "template", "bookmark-type"] {
            XCTAssertThrowsError(try parse(response(), requested: [forbidden]))
            XCTAssertThrowsError(try parse(response(["propertyOwnerId": .string(forbidden),
                "collections": .array([.string(forbidden)])])))
        }
        let maximumRequest = (0..<127).map { String(format: "collection-%03d", $0) }
        let maximumUnion = (maximumRequest + ["url-owner"]).sorted()
        XCTAssertEqual(try parse(response(["collections": .array(maximumUnion.map(AnyJSON.string))]),
            requested: maximumRequest).collections.count, 128)
        let tooManyDistinct = maximumRequest + ["one-more"]
        XCTAssertThrowsError(try parse(response(), requested: tooManyDistinct))
        XCTAssertThrowsError(try parse(response(), requested: Array(repeating: "url-owner", count: 129)))
    }

    func testOpaqueTokenHasCanonicalUnpaddedEncodingAndExactSizeLimit() throws {
        // The Host validates the transport encoding, not the native inner proof.
        let arbitrary = Self.token(Data([0xff, 0x00, 0x81]))
        XCTAssertNoThrow(try AnyNativeBookmarkCreationFrame.validateToken(arbitrary))
        XCTAssertNoThrow(try parse(response(["frame": .string(arbitrary)])))
        let largest = Self.token(Data(repeating: 0xff, count: 65_536))
        XCTAssertEqual(largest.utf8.count, 87_382)
        XCTAssertNoThrow(try AnyNativeBookmarkCreationFrame.validateToken(largest))
        XCTAssertThrowsError(try AnyNativeBookmarkCreationFrame.validateToken(Self.token(Data(repeating: 0, count: 65_537))))
        for invalid in ["", "A", "AA=", "AA==", "+w", "/w", "AA\n", " AA", "AA ", "éA", "AB", "AAB"] {
            XCTAssertThrowsError(try AnyNativeBookmarkCreationFrame.validateToken(invalid), "invalid canonical token")
        }
        XCTAssertNoThrow(try AnyNativeBookmarkCreationFrame.validateToken("AA"))
        XCTAssertNoThrow(try AnyNativeBookmarkCreationFrame.validateToken("AAA"))
    }

    func testIntentFreezesTheConditionAndExactMappedURLValue() throws {
        let key = "u\u{301}rl"
        let normalizedKey = "úrl"
        XCTAssertEqual(key, normalizedKey)
        XCTAssertNotEqual(Array(key.utf8), Array(normalizedKey.utf8))
        let value = "https://example.invalid/e\u{301}?q=ש\u{5c1}\u{5b8}"
        let frame = try parse(response(["propertyId": .string(key), "canWrite": .bool(false)]))
        let properties: AnyJSON = .object([
            "url-owner": .object([key: .string(value), "extra": .integer(7)]),
            "any": .object(["name": .string("Bookmark")]),
            "bookmark-type": .object(["note": .string("typed value")])
        ])
        let intent = try frame.makeCreationIntent(mutationID: String(repeating: "a", count: 32), initialProperties: properties)
        XCTAssertEqual(intent.bookmarkDefinitionFrame, frame.definitionFrame)
        XCTAssertEqual(intent.body["bookmarkDefinitionFrame"]?.string, frame.definitionFrame)
        XCTAssertEqual(intent.collections, ["url-owner"])
        XCTAssertEqual(Array(try XCTUnwrap(intent.initialProperties["url-owner"]?[key]?.string).utf8), Array(value.utf8))
        let wrongKey: AnyJSON = .object(["url-owner": .object([normalizedKey: .string(value)])])
        XCTAssertThrowsError(try frame.makeCreationIntent(mutationID: String(repeating: "a", count: 32), initialProperties: wrongKey))
        for nonString in [AnyJSON.null, .integer(3), .array([.string(value)])] {
            XCTAssertThrowsError(try frame.makeCreationIntent(mutationID: String(repeating: "a", count: 32),
                initialProperties: .object(["url-owner": .object([key: nonString])])))
        }
        for extraGroup in ["foreign", "template"] {
            XCTAssertThrowsError(try frame.makeCreationIntent(mutationID: String(repeating: "a", count: 32),
                initialProperties: .object(["url-owner": .object([key: .string(value)]), extraGroup: .object([:])])))
        }
        XCTAssertThrowsError(try frame.makeCreationIntent(mutationID: String(repeating: "a", count: 32),
            initialProperties: .object(["url-owner": .object([key: .string(value)]), "any": .object(["template": .bool(true)])])))
    }

    func testDiagnosticsDoNotSerializeTheOpaqueCondition() throws {
        let frame = try parse(response())
        XCTAssertEqual(String(describing: frame), "AnyNativeBookmarkCreationFrame(redacted)")
        XCTAssertEqual(String(reflecting: frame), "AnyNativeBookmarkCreationFrame(redacted)")
        XCTAssertFalse(String(describing: frame).contains(frame.definitionFrame))
    }

    func testNilFramePreservesLegacyFingerprintAndMissingOptionalEncoding() throws {
        let intent = try creationIntent()
        // Original AnyHostCanonical d234b3d8 typed framing: 379 bytes. The
        // literal identity is independent of the new condition implementation.
        let known = "54528e8dd53aaf2c76c794b3103960e12c43dbe5d501c3fcb51ea0535ad5a432"
        XCTAssertEqual(intent.fingerprint, known)
        XCTAssertNil(intent.bookmarkDefinitionFrame)
        XCTAssertEqual(Set(try XCTUnwrap(intent.body.object).keys), ["type", "collections", "initialProperties"])
        let encoded = try JSONEncoder().encode(intent)
        let value = try JSONDecoder().decode(AnyJSON.self, from: encoded)
        XCTAssertNil(value["bookmarkDefinitionFrame"])
        XCTAssertEqual(Set(try XCTUnwrap(value.object).keys),
            ["workspace", "mutationID", "typeID", "collections", "initialProperties", "fingerprint"])
        let legacy = Data(#"{"workspace":{"accountID":"account","spaceID":"space"},"mutationID":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","typeID":"bookmark-type","collections":["url-owner","z"],"initialProperties":{"any":{"name":"Bookmark"},"url-owner":{"url":"https://example.invalid/bookmark"}},"fingerprint":"54528e8dd53aaf2c76c794b3103960e12c43dbe5d501c3fcb51ea0535ad5a432"}"#.utf8)
        let decoded = try JSONDecoder().decode(AnyNativeObjectCreationIntent.self, from: legacy)
        XCTAssertEqual(decoded, intent)
        XCTAssertEqual(decoded.body, intent.body)
    }

    func testChangedConditionChangesFingerprintAndCannotReplaceReservedIntent() async throws {
        let first = try creationIntent(frame: Self.token(Data("condition-a".utf8)))
        let second = try creationIntent(frame: Self.token(Data("condition-b".utf8)))
        XCTAssertNotEqual(first.fingerprint, second.fingerprint)
        XCTAssertNotEqual(first.fingerprint, try creationIntent().fingerprint)
        XCTAssertEqual(first.identity.key, second.identity.key)
        let exact = try JSONEncoder().encode(first)
        XCTAssertEqual(try JSONDecoder().decode(AnyNativeObjectCreationIntent.self, from: exact), first)
        var fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: exact).object)
        fields["bookmarkDefinitionFrame"] = .string(try XCTUnwrap(second.bookmarkDefinitionFrame))
        XCTAssertThrowsError(try JSONDecoder().decode(AnyNativeObjectCreationIntent.self,
            from: JSONEncoder().encode(AnyJSON.object(fields)))) { error in
            XCTAssertEqual(error as? AnyNativeCreationError, .contentConflict)
        }
        fields.removeValue(forKey: "bookmarkDefinitionFrame")
        XCTAssertThrowsError(try JSONDecoder().decode(AnyNativeObjectCreationIntent.self,
            from: JSONEncoder().encode(AnyJSON.object(fields))))
        let journal = BookmarkCreationMemoryJournal(workspace: first.workspace)
        let reservation = try await journal.reserve(first.identity)
        XCTAssertTrue(reservation.ownsDispatch)
        do { _ = try await journal.reserve(second.identity); XCTFail("changed definition silently replaced original intent") }
        catch let error as AnyNativeCreationError { XCTAssertEqual(error, .contentConflict) }
        let state = try await journal.lookup(first.identity)
        XCTAssertEqual(state, .reserved)
    }

    func testKnownCreationIDAfterUncertainDispatchResumesWithoutAnotherDispatch() async throws {
        let intent = try creationIntent(frame: Self.token(Data("condition-a".utf8)))
        let journal = BookmarkCreationMemoryJournal(workspace: intent.workspace)
        let native = BookmarkCreationDispatch(intent: intent, uncertain: true)
        let original = bookmarkCreator(journal, native)
        do { _ = try await original.ensureObject(intent, authorize: {}); XCTFail("uncertain root became a success receipt") }
        catch let error as AnyNativeCreationError { XCTAssertEqual(error, .createdObjectIncomplete("created-bookmark")) }
        let firstState = try await journal.lookup(intent.identity)
        let firstObservation = await native.observation()
        let recoveryID = try await original.recordedObjectID(for: intent)
        XCTAssertEqual(firstState, .created("created-bookmark"))
        XCTAssertEqual(recoveryID, "created-bookmark")
        XCTAssertEqual(firstObservation.dispatches, 1)
        XCTAssertEqual(firstObservation.reads, 0)
        let resumed = bookmarkCreator(journal, native)
        let result = try await resumed.ensureObject(intent, authorize: {})
        let lastState = try await journal.lookup(intent.identity)
        let lastObservation = await native.observation()
        XCTAssertEqual(result, "created-bookmark")
        XCTAssertEqual(lastState, .verified("created-bookmark"))
        XCTAssertEqual(lastObservation.dispatches, 1)
        XCTAssertEqual(lastObservation.reads, 1)
    }

    func testCreationCancellationDuringFinalAuthorizationKeepsVerifiedIDWithoutDelivery() async throws {
        let intent = try creationIntent(frame: Self.token(Data("condition-a".utf8)))
        let journal = BookmarkCreationMemoryJournal(workspace: intent.workspace)
        let native = BookmarkCreationDispatch(intent: intent, uncertain: false)
        let creator = bookmarkCreator(journal, native)
        let gate = BookmarkFrameReadGate(holdAt: 4)
        let task = Task { try await creator.ensureObject(intent, authorize: { try await gate.check() }) }
        let retained: AnyNativeCreationState?
        do {
            try await gate.waitUntilHeld()
            retained = try await journal.lookup(intent.identity)
            XCTAssertEqual(retained, .verified("created-bookmark"))
        }
        catch { task.cancel(); await gate.release(); _ = await task.result; throw error }
        task.cancel()
        await gate.release()
        do { _ = try await task.value; XCTFail("cancelled original caller received object ID") }
        catch is CancellationError { }
        let after = try await journal.lookup(intent.identity)
        XCTAssertEqual(after, retained)
        let resumed = bookmarkCreator(journal, native)
        let recovered = try await resumed.ensureObject(intent, authorize: {})
        let observation = await native.observation()
        XCTAssertEqual(recovered, "created-bookmark")
        XCTAssertEqual(observation.dispatches, 1)
        XCTAssertEqual(observation.reads, 2)
    }

    private func bookmarkCreator(_ journal: BookmarkCreationMemoryJournal,
                                 _ native: BookmarkCreationDispatch) -> AnyNativeObjectCreator {
        .init(workspace: journal.workspace, journal: journal,
              dispatch: { try await native.dispatch($0, authorize: $1) }, inspect: { try await native.inspect($0) })
    }

#if os(macOS) || os(Linux)
    func testGenericUnicodeWorkspaceConstructionRemainsLazyAndMakesNoHTTPCall() async throws {
        let fixture = try BookmarkFrameHTTPFixture(body: response())
        defer { fixture.stop() }
        let scope = try AnyTorahWorkspace(accountID: "חשבון-e\u{301}", spaceID: "מרחב")
        let endpoint = try fixture.client().baseURL
        let client = try AnyHTTPClient(baseURL: endpoint, expectedAccountID: scope.accountID)
        let journal = BookmarkCreationMemoryJournal(workspace: scope)
        let creator = try AnyNativeObjectCreator(client: client, workspace: scope, journal: journal)
        do {
            _ = try await creator.makeBookmarkCreationFrameReader()
            XCTFail("Bookmark native identifiers must retain their explicit bounds")
        } catch let error as AnyEngineError {
            XCTAssertEqual(error, .invalidIdentity("Bookmark creation frame workspace"))
        }
        XCTAssertEqual(try fixture.rows().count, 0)
        let reservations = await journal.reserveCalls()
        XCTAssertEqual(reservations, 0)
    }

    func testReaderUsesOnlyCapabilityAndFrameReadsWithExactRequest() async throws {
        let fixture = try BookmarkFrameHTTPFixture(body: response(["collections": .array([.string("url-owner"), .string("z")])]))
        defer { fixture.stop() }
        let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
        let gate = BookmarkFrameReadGate()
        let frame = try await reader.frame(typeID: "bookmark-type", collections: ["z", "z"]) { try await gate.check() }
        XCTAssertEqual(frame.collections, ["url-owner", "z"])
        let calls = await gate.calls()
        XCTAssertEqual(calls, 6)
        let rows = try fixture.rows()
        XCTAssertEqual(rows.count, 7)
        let posts = rows.filter { $0["method"]?.string == "POST" }
        XCTAssertEqual(posts.count, 1)
        XCTAssertEqual(posts.first?["path"]?.string, "/v1/spaces/space/pinkha/bookmark-create-frame")
        XCTAssertEqual(posts.first?["body"], .object(["typeId": .string("bookmark-type"),
            "collections": .array([.string("z"), .string("z")])]))
        XCTAssertTrue(rows.allSatisfy { ["/v1/auth", "/v1/pinkha/capabilities", "/v1/spaces/space/pinkha/bookmark-create-frame"].contains($0["path"]?.string ?? "") })
    }

    func testMissingOrMistypedCapabilityRefusesBeforeFramePOST() async throws {
        let capabilities: [AnyJSON] = [
            .object(["contract": .string("pinkha-torah-native-v1"), "currentWriterObjectCreate": .integer(1)]),
            .object(["contract": .string("pinkha-torah-native-v1"), "currentWriterObjectCreate": .integer(1), "nativeBookmarkObjectCreate": .string("1")]),
            .object(["contract": .string("pinkha-torah-native-v1"), "currentWriterObjectCreate": .integer(0), "nativeBookmarkObjectCreate": .integer(1)])
        ]
        for capability in capabilities {
            let fixture = try BookmarkFrameHTTPFixture(body: response(), capabilities: capability)
            defer { fixture.stop() }
            let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
            do { _ = try await reader.frame(typeID: "bookmark-type", authorizeRead: {}); XCTFail("missing capability returned a frame") }
            catch let error as AnyEngineError {
                guard case .incompatibleSchema = error else { return XCTFail("wrong capability refusal") }
            }
            XCTAssertEqual(try fixture.posts().count, 0)
        }
    }

    func testGuardedCreationRequiresNativeCapabilityBeforeJournalOrAnyPOST() async throws {
        let capabilities: AnyJSON = .object(["contract": .string("pinkha-torah-native-v1"),
            "currentWriterObjectCreate": .integer(1)])
        let fixture = try BookmarkFrameHTTPFixture(body: response(), capabilities: capabilities)
        defer { fixture.stop() }
        let intent = try creationIntent(frame: Self.token(Data("condition-a".utf8)))
        let journal = BookmarkCreationMemoryJournal(workspace: intent.workspace)
        let creator = try AnyNativeObjectCreator(client: fixture.client(), workspace: intent.workspace, journal: journal)
        do { _ = try await creator.ensureObject(intent, authorize: {}); XCTFail("native condition capability was bypassed") }
        catch let error as AnyEngineError {
            XCTAssertEqual(error, .incompatibleSchema("native Bookmark definition condition unavailable"))
        }
        let calls = await journal.reserveCalls()
        let state = try await journal.lookup(intent.identity)
        XCTAssertEqual(calls, 0)
        XCTAssertNil(state)
        XCTAssertEqual(try fixture.posts().count, 0)
    }

    func testResponseScopeAccountChangeAndOversizeNeverDeliverFrame() async throws {
        for mode in ["foreign-scope", "switch-after-post", "oversize"] {
            let body = mode == "foreign-scope" ? response(["spaceId": .string("another-space")]) : response()
            let fixture = try BookmarkFrameHTTPFixture(body: body, mode: mode)
            defer { fixture.stop() }
            let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
            do { _ = try await reader.frame(typeID: "bookmark-type", authorizeRead: {}); XCTFail("private frame escaped \(mode)") }
            catch let error as AnyEngineError {
                let expected: AnyEngineError = mode == "foreign-scope"
                    ? .malformedResponse("Bookmark creation frame") : .writeUncertain
                XCTAssertEqual(error, expected)
            }
            XCTAssertEqual(try fixture.posts().count, 1)
        }
    }

    func testReadAuthorizationRefusalAtDispatchResponseAndFinalDelivery() async throws {
        for failedCall in [1, 4, 5, 6] {
            let fixture = try BookmarkFrameHTTPFixture(body: response())
            defer { fixture.stop() }
            let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
            let gate = BookmarkFrameReadGate(failAt: failedCall)
            do { _ = try await reader.frame(typeID: "bookmark-type") { try await gate.check() }; XCTFail("retired owner received frame") }
            catch let error as AnyEngineError {
                XCTAssertEqual(failedCall, 4)
                XCTAssertEqual(error, .writeUncertain)
            } catch BookmarkFrameTestError.retired {
                XCTAssertTrue(failedCall == 1 || failedCall == 5 || failedCall == 6)
            }
            let calls = await gate.calls()
            XCTAssertEqual(calls, failedCall)
            XCTAssertEqual(try fixture.posts().count, failedCall == 1 ? 0 : 1)
        }
    }

    func testCancellationWhileFinalReadCheckSuspendsWithholdsParsedFrame() async throws {
        let fixture = try BookmarkFrameHTTPFixture(body: response())
        defer { fixture.stop() }
        let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
        let gate = BookmarkFrameReadGate(holdAt: 5)
        let task = Task { try await reader.frame(typeID: "bookmark-type") { try await gate.check() } }
        do { try await gate.waitUntilHeld() }
        catch { task.cancel(); await gate.release(); _ = await task.result; throw error }
        task.cancel()
        await gate.release()
        do { _ = try await task.value; XCTFail("cancelled caller received frame") }
        catch is CancellationError { }
        let calls = await gate.calls()
        XCTAssertEqual(calls, 5)
        XCTAssertEqual(try fixture.posts().count, 1)
    }

    func testAccountSwitchInsideFinalReadCheckIsRefused() async throws {
        let fixture = try BookmarkFrameHTTPFixture(body: response())
        defer { fixture.stop() }
        let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
        let gate = BookmarkFrameReadGate()
        do {
            _ = try await reader.frame(typeID: "bookmark-type") {
                try await gate.check()
                if await gate.calls() == 5 { try fixture.changeAccount("other-account") }
            }
            XCTFail("account changed during final read authorization")
        } catch let error as AnyEngineError {
            XCTAssertEqual(error, .accountChanged)
        }
        XCTAssertEqual(try fixture.posts().count, 1)
        XCTAssertEqual(try fixture.rows().last?["path"]?.string, "/v1/auth")
    }

    func testOwnerRetiredDuringFinalAccountResponseIsRefused() async throws {
        let fixture = try BookmarkFrameHTTPFixture(body: response(), mode: "retire-on-final-auth")
        defer { fixture.stop() }
        let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
        let gate = BookmarkFrameReadGate()
        do {
            _ = try await reader.frame(typeID: "bookmark-type") {
                try await gate.check()
                if fixture.hasRetiredOwner() { throw BookmarkFrameTestError.retired }
            }
            XCTFail("owner retired while the final account response was in flight")
        } catch BookmarkFrameTestError.retired { }
        let calls = await gate.calls()
        XCTAssertEqual(calls, 6)
        XCTAssertTrue(fixture.hasRetiredOwner())
        XCTAssertEqual(try fixture.posts().count, 1)
    }

    func testCancelledEntryAndInvalidRequestHaveNoHTTPDispatch() async throws {
        let fixture = try BookmarkFrameHTTPFixture(body: response())
        defer { fixture.stop() }
        let reader = try AnyNativeBookmarkCreationFrameReader(client: fixture.client(), workspace: workspace())
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try await reader.frame(typeID: "bookmark-type", authorizeRead: {})
        }
        do { _ = try await task.value; XCTFail("cancelled entry reached HTTP") }
        catch is CancellationError { }
        do { _ = try await reader.frame(typeID: "bookmark-type", collections: ["any"], authorizeRead: {}); XCTFail("invalid collection reached HTTP") }
        catch let error as AnyEngineError {
            guard case .invalidOperation = error else { return XCTFail("wrong local request refusal") }
        }
        XCTAssertEqual(try fixture.rows().count, 0)
    }
#endif
}

private enum BookmarkFrameTestError: Error { case retired, fixture, timeout }

/// An injected in-memory journal/native result for the creator's existing
/// recovery boundary. This is not an actual SDK persistence qualification.
private actor BookmarkCreationMemoryJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    private var identity: AnyNativeCreationIdentity?
    private var state: AnyNativeCreationState?
    private var calls = 0
    init(workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func reserve(_ requested: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        calls += 1
        guard requested.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        if let identity {
            guard identity == requested, let state else { throw AnyNativeCreationError.contentConflict }
            return .init(state: state, ownsDispatch: false)
        }
        identity = requested; state = .reserved
        return .init(state: .reserved, ownsDispatch: true)
    }
    func record(_ next: AnyNativeCreationState, identity requested: AnyNativeCreationIdentity) throws {
        guard requested == identity, let previous = state else { throw AnyNativeCreationError.contentConflict }
        switch (previous, next) {
        case (.reserved, .created): break
        case (.created(let before), .verified(let after)) where before == after: break
        case (.verified(let before), .verified(let after)) where before == after: break
        default: throw AnyNativeCreationError.contentConflict
        }
        state = next
    }
    func lookup(_ requested: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        guard requested.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        if let identity, identity != requested { throw AnyNativeCreationError.contentConflict }
        return state
    }
    func reserveCalls() -> Int { calls }
}

private actor BookmarkCreationDispatch {
    private let intent: AnyNativeObjectCreationIntent
    private let uncertain: Bool
    private var dispatches = 0
    private var reads = 0
    init(intent: AnyNativeObjectCreationIntent, uncertain: Bool) { self.intent = intent; self.uncertain = uncertain }
    func dispatch(_ request: AnyNativeObjectCreationIntent,
                  authorize: @escaping @Sendable () async throws -> Void) async throws -> String {
        guard request == intent, dispatches == 0 else { throw AnyNativeCreationError.contentConflict }
        try await authorize()
        dispatches += 1
        if uncertain {
            let failure = try AnyObjectCreationUncertain(spaceID: intent.workspace.spaceID,
                objectID: "created-bookmark", stage: .rootStored)
            throw failure
        }
        return "created-bookmark"
    }
    func inspect(_ id: String) throws -> AnyJSON {
        guard id == "created-bookmark", dispatches == 1,
              var properties = intent.initialProperties.object else { throw BookmarkFrameTestError.fixture }
        reads += 1
        var any = properties["any"]?.object ?? [:]
        any["type"] = .string(intent.typeID)
        any["collections"] = .array(intent.collections.map(AnyJSON.string))
        properties["any"] = .object(any)
        properties["id"] = .string(id)
        properties["spaceId"] = .string(intent.workspace.spaceID)
        return .object(properties)
    }
    func observation() -> (dispatches: Int, reads: Int) { (dispatches, reads) }
}

private actor BookmarkFrameReadGate {
    private var count = 0
    private let failAt: Int?
    private let holdAt: Int?
    private var held = false
    private var released = false
    private var continuation: CheckedContinuation<Void, Never>?
    init(failAt: Int? = nil, holdAt: Int? = nil) { self.failAt = failAt; self.holdAt = holdAt }
    func check() async throws {
        count += 1
        if count == failAt { throw BookmarkFrameTestError.retired }
        if count == holdAt && !released {
            held = true
            await withCheckedContinuation { continuation = $0 }
        }
    }
    func calls() -> Int { count }
    func release() { released = true; continuation?.resume(); continuation = nil }
    func waitUntilHeld() async throws {
        let deadline = Date().addingTimeInterval(5)
        while !held {
            guard Date() < deadline else { throw BookmarkFrameTestError.timeout }
            try await Task.sleep(for: .milliseconds(10))
        }
    }
}

#if os(macOS) || os(Linux)
/// This synthetic HTTP process owns no native account. Its only lifetime
/// signal is EOF on the inherited pipe. Before serving it joins the verified
/// live outer owner group; no historical PID is signalled or probed.
private final class BookmarkFrameHTTPFixture: @unchecked Sendable {
    private let directory: URL
    private let process = Process()
    private let control = Pipe()
    private var stderr: FileHandle?
    private var port = 0
    private var started = false
    private var stopped = false
    private let token = String(repeating: "a", count: 64)

    init(body: AnyJSON, capabilities: AnyJSON? = nil, mode: String = "normal") throws {
        let parent: URL
        if let path = ProcessInfo.processInfo.environment["PINKHA_BOOKMARK_FRAME_FIXTURE_ROOT"] {
            parent = URL(fileURLWithPath: path, isDirectory: true)
            let attributes = try FileManager.default.attributesOfItem(atPath: path)
            guard parent.resolvingSymlinksInPath().path == parent.path,
                  attributes[.type] as? FileAttributeType == .typeDirectory,
                  (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700,
                  (attributes[.ownerAccountID] as? NSNumber)?.uint32Value == geteuid() else {
                throw BookmarkFrameTestError.fixture
            }
        } else {
            parent = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-bookmark-frame-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        }
        directory = parent.appendingPathComponent("case-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        let capability = capabilities ?? .object(["contract": .string("pinkha-torah-native-v1"),
            "currentWriterObjectCreate": .integer(1), "nativeBookmarkObjectCreate": .integer(1)])
        try JSONEncoder().encode(AnyJSON.object(["body": body, "capabilities": capability,
            "mode": .string(mode), "controlToken": .string(token)])).write(to: directory.appendingPathComponent("config.json"))
        let script = directory.appendingPathComponent("server.py")
        try Data(Self.server.utf8).write(to: script)
        try Data("account".utf8).write(to: directory.appendingPathComponent("account.txt"))
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardInput = control
        guard fcntl(control.fileHandleForWriting.fileDescriptor, F_SETFD, FD_CLOEXEC) == 0 else { throw BookmarkFrameTestError.fixture }
        let log = directory.appendingPathComponent("stderr.log")
        guard FileManager.default.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600]) else {
            throw BookmarkFrameTestError.fixture
        }
        stderr = try FileHandle(forWritingTo: log)
        process.standardOutput = FileHandle.nullDevice
        process.standardError = stderr
        do {
            try process.run()
            started = true
            try control.fileHandleForReading.close()
            let path = directory.appendingPathComponent("port.json")
            let deadline = Date().addingTimeInterval(5)
            while !FileManager.default.fileExists(atPath: path.path) {
                guard process.isRunning, Date() < deadline else { throw BookmarkFrameTestError.fixture }
                Thread.sleep(forTimeInterval: 0.01)
            }
            port = try JSONDecoder().decode(Int.self, from: Data(contentsOf: path))
            guard (1...65_535).contains(port) else { throw BookmarkFrameTestError.fixture }
        } catch { stop(); throw error }
    }

    deinit { try? control.fileHandleForWriting.close() }

    func client() throws -> AnyHTTPClient {
        let url = try XCTUnwrap(URL(string: "http://127.0.0.1:\(port)"))
        return try .init(baseURL: url, expectedAccountID: "account", authorization: AnyHTTPAuthorization(token: token))
    }
    func changeAccount(_ account: String) throws {
        try Data(account.utf8).write(to: directory.appendingPathComponent("account.txt"), options: .atomic)
    }
    func hasRetiredOwner() -> Bool { FileManager.default.fileExists(atPath: directory.appendingPathComponent("owner-retired.json").path) }
    func rows() throws -> [AnyJSON] {
        let path = directory.appendingPathComponent("requests.json")
        if !FileManager.default.fileExists(atPath: path.path) { return [] }
        return try JSONDecoder().decode([AnyJSON].self, from: Data(contentsOf: path))
    }
    func posts() throws -> [AnyJSON] { try rows().filter { $0["method"]?.string == "POST" } }

    func stop() {
        guard !stopped else { return }
        stopped = true
        var errors: [String] = []
        do { try control.fileHandleForWriting.close() }
        catch { errors.append("owned stdin close failed") }
        let deadline = Date().addingTimeInterval(3)
        while started && process.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.01) }
        let exited = started && !process.isRunning
        var status: Int64?
        if exited {
            process.waitUntilExit()
            status = Int64(process.terminationStatus)
            if process.terminationReason != .exit || status != 0 { errors.append("fixture did not exit normally") }
        } else if started { errors.append("fixture remained live after stdin EOF") }
        do { try stderr?.synchronize(); try stderr?.close() }
        catch { errors.append("stderr retention failed") }
        let initial = try? JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: directory.appendingPathComponent("start.json")))
        let ended = try? JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: directory.appendingPathComponent("exit.json")))
        if started && (initial?["pid"]?.integer != Int64(process.processIdentifier) ||
                       ended?["pid"]?.integer != Int64(process.processIdentifier) || ended?["reason"]?.string != "stdin-eof") {
            errors.append("fixture exit ownership mismatch")
        }
        for key in ["pgid", "sessionID", "parentPID", "startTimeTicks", "bootID", "controllerOwnedGroup",
                    "ownerRecord", "ownerRecordSHA256", "ownerPID", "ownerAncestors"] {
            if initial?[key] != ended?[key] { errors.append("fixture ownership changed: " + key) }
        }
        if ProcessInfo.processInfo.environment["PINKHA_BOOKMARK_FRAME_OWNER_RECORD"] != nil &&
            (initial?["controllerOwnedGroup"]?.bool != true || initial?["pgid"] != initial?["ownerPID"] ||
             initial?["sessionID"] != initial?["ownerPID"]) {
            errors.append("fixture original owner group was not qualified")
        }
        let proof: AnyJSON = .object(["started": .bool(started), "pid": .integer(Int64(process.processIdentifier)),
            "leaderObservedExited": .bool(exited), "exitCode": status.map(AnyJSON.integer) ?? .null,
            "ownership": initial ?? .null,
            "errors": .array(errors.map(AnyJSON.string))])
        do { try JSONEncoder().encode(proof).write(to: directory.appendingPathComponent("parent-stop.json"), options: .atomic) }
        catch { errors.append("stop evidence retention failed") }
        XCTAssertTrue(errors.isEmpty, errors.joined(separator: "; "))
        // An abnormal live descendant is left to the outer owned test-group
        // supervisor. Retained synthetic request/source/lifecycle files remain.
    }

    private static let server = #"""
import hashlib, http.server, json, os, selectors, signal, socket, stat, sys, time
from pathlib import Path

root = Path(sys.argv[1])
config = json.loads((root / 'config.json').read_text())
rows = []
serial = 0
reason = 'deadline'
auth_count = 0

def owned_group():
    path = os.environ.get('PINKHA_BOOKMARK_FRAME_OWNER_RECORD')
    if not path:
        return {'controllerOwnedGroup': False}
    record = Path(path)
    if not record.is_absolute() or record.resolve() != record:
        raise RuntimeError('fixture owner record is not physical')
    fd = os.open(record, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        attributes = os.fstat(stream.fileno())
        raw = stream.read(65537)
    if not stat.S_ISREG(attributes.st_mode) or attributes.st_uid != os.geteuid() or stat.S_IMODE(attributes.st_mode) != 0o600 or len(raw) > 65536:
        raise RuntimeError('fixture owner record custody')
    owner = json.loads(raw)
    pid = owner.get('pid')
    if type(pid) is not int or pid <= 1 or owner.get('cwd') != os.environ.get('PINKHA_BOOKMARK_FRAME_OWNER_CWD'):
        raise RuntimeError('fixture owner record identity')
    if os.getsid(pid) != pid or os.getpgid(pid) != pid or os.getsid(0) != pid:
        raise RuntimeError('fixture is outside the qualified owner session')
    ancestor = os.getppid()
    lineage = []
    for _ in range(64):
        raw_stat = Path(f'/proc/{ancestor}/stat').read_bytes()
        if len(raw_stat) > 8192:
            raise RuntimeError('fixture owner ancestor bound')
        fields = raw_stat.rsplit(b')', 1)[1].split()
        if len(fields) < 20 or int(fields[3]) != pid:
            raise RuntimeError('fixture owner ancestor session')
        lineage.append({'pid': ancestor, 'startTimeTicks': int(fields[19])})
        if ancestor == pid: break
        ancestor = int(fields[1])
        if ancestor <= 1: raise RuntimeError('fixture qualified leader is not an ancestor')
    else: raise RuntimeError('fixture owner ancestry exceeded bound')
    os.setpgid(0, pid)
    if os.getpgrp() != pid or os.getsid(0) != pid:
        raise RuntimeError('fixture did not join its original owned group')
    return {'controllerOwnedGroup': True, 'ownerRecord': str(record),
            'ownerRecordSHA256': hashlib.sha256(raw).hexdigest(), 'ownerPID': pid, 'ownerAncestors': lineage}

def save(name, value):
    global serial
    serial += 1
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
    if len(raw) > 1048576: raise RuntimeError('fixture evidence bound')
    temporary = root / (name + '.' + str(serial) + '.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, root / name)

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def setup(self):
        self.request.settimeout(1.0)
        super().setup()
    def log_message(self, *args): pass
    def reply(self, status, body, oversized=False):
        raw = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
        if oversized:
            if len(raw) > 262145: raise RuntimeError('fixture response base bound')
            raw += b' ' * (262145 - len(raw))
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        try: self.wfile.write(raw); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, socket.timeout): pass
    def handle_one(self):
        global auth_count
        if self.headers.get('X-Any-Control-Token') != config['controlToken']:
            self.reply(403, {'error': {'code': 'fixture.control'}}); return
        body = None
        if self.command == 'POST':
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= 262144: raise RuntimeError('fixture request bound')
            raw = self.rfile.read(length)
            if len(raw) != length: raise RuntimeError('fixture short request')
            body = json.loads(raw)
        if len(rows) >= 64: raise RuntimeError('fixture request count')
        rows.append({'method': self.command, 'path': self.path, 'body': body})
        save('requests.json', rows)
        if self.command == 'GET' and self.path == '/v1/auth':
            auth_count += 1
            if config['mode'] == 'retire-on-final-auth' and auth_count == 5:
                save('owner-retired.json', True)
            self.reply(200, {'authorized': True, 'accountId': (root / 'account.txt').read_text()})
        elif self.command == 'GET' and self.path == '/v1/pinkha/capabilities':
            self.reply(200, config['capabilities'])
        elif self.command == 'POST' and self.path == '/v1/spaces/space/pinkha/bookmark-create-frame':
            if set(body) != {'typeId', 'collections'}: raise RuntimeError('fixture exact read request')
            if config['mode'] == 'switch-after-post': (root / 'account.txt').write_text('other-account')
            self.reply(200, config['body'], config['mode'] == 'oversize')
        else: self.reply(404, {'error': {'code': 'fixture.unknown'}})
    do_GET = handle_one
    do_POST = handle_one

if hasattr(signal, 'pthread_sigmask'):
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
owner = owned_group()
server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
selector = selectors.DefaultSelector()
selector.register(0, selectors.EVENT_READ, 'owner')
selector.register(server.socket, selectors.EVENT_READ, 'http')
started = {'pid': os.getpid(), 'pgid': os.getpgrp(), 'sessionID': os.getsid(0), 'parentPID': os.getppid(), **owner}
if Path('/proc/self/stat').is_file():
    started['startTimeTicks'] = int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])
    started['bootID'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
save('start.json', started)
save('port.json', server.server_address[1])
deadline = time.monotonic() + 45
try:
    done = False
    while not done and time.monotonic() < deadline:
        for key, _ in selector.select(0.05):
            if key.data == 'owner':
                if os.read(0, 4096) != b'': raise RuntimeError('unexpected owner bytes')
                reason = 'stdin-eof'; done = True; break
            server._handle_request_noblock()
finally:
    selector.close(); server.server_close()
    save('exit.json', {**started, 'reason': reason, 'requestCount': len(rows)})
if reason != 'stdin-eof': raise RuntimeError('fixture owner deadline')
"""#
}
#endif
