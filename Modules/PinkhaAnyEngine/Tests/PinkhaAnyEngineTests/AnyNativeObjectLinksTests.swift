import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyNativeObjectLinksTests: XCTestCase, @unchecked Sendable {
    func testRetainsCanonicalObjectRecordPropertyIdentityFileAndOpenEdgeKinds() throws {
        let targets: [AnyJSON] = [
            target("o", ["spaceId": "other-space", "objectId": "destination"]),
            target("o", ["spaceId": "space", "objectId": "destination", "dataset": "page", "recordId": "block"]),
            target("p", ["spaceId": "space", "objectId": "destination", "propId": "property"]),
            target("u", ["identity": "member"]),
            target("f", ["spaceId": "space", "fileId": "file"])
        ]
        let links = targets.map { edge($0, kind: "future-v2") }
        let snapshot = try outgoing(.object(["links": .array(links)]))
        XCTAssertEqual(snapshot.accountID, "account")
        XCTAssertEqual(snapshot.links.count, 5)
        XCTAssertEqual(snapshot.links.map(\.target.kind), [.object, .object, .property, .identity, .file])
        XCTAssertEqual(snapshot.links[0].target.spaceID, "other-space")
        XCTAssertEqual(snapshot.links[1].target.recordID, "block")
        XCTAssertEqual(snapshot.links[2].target.propID, "property")
        XCTAssertEqual(snapshot.links[3].target.uri, "any://u/member")
        XCTAssertEqual(snapshot.links[4].target.fileID, "file")
        XCTAssertTrue(snapshot.links.allSatisfy { $0.kind == "future-v2" })
    }

    func testNativeSelectionsAndReadCapsArePreserved() throws {
        let record = try AnyNativeObjectLinks.query(spaceID: "space", objectID: "object",
            selection: .record(dataset: "page", recordID: "block"), kind: "mention", limit: 37, incoming: true)
        XCTAssertEqual(record, ["dataset": "page", "record": "block", "kind": "mention", "limit": "37"])
        let property = try AnyNativeObjectLinks.query(spaceID: "space", objectID: "object",
            selection: .property("property"), kind: nil, limit: 500, incoming: true)
        XCTAssertEqual(property, ["prop": "property", "limit": "500"])
        let dataset = try AnyNativeObjectLinks.query(spaceID: "space", objectID: "object",
            selection: .dataset("page"), kind: nil, limit: 500, incoming: false)
        XCTAssertEqual(dataset["dataset"], "page")
        for limit in [0, 501] {
            XCTAssertThrowsError(try AnyNativeObjectLinks.query(spaceID: "space", objectID: "object",
                selection: .object, kind: nil, limit: limit, incoming: false))
        }
        XCTAssertThrowsError(try AnyNativeObjectLinks.query(spaceID: "space", objectID: "object",
            selection: .dataset("page"), kind: nil, limit: 500, incoming: true))
        XCTAssertThrowsError(try AnyNativeObjectLinks.query(spaceID: "space", objectID: "object",
            selection: .record(dataset: "prop", recordID: "property"), kind: nil, limit: 500, incoming: true))
    }

    func testOutgoingScopeUsesExactBytesAndCanonicalURIHasNoSecondIdentity() throws {
        let composed = "sp-\u{00E9}"
        let decomposed = "sp-e\u{0301}"
        XCTAssertEqual(composed, decomposed) // Swift's text equivalence is not an opaque native identity.
        XCTAssertThrowsError(try outgoing(.object(["links": .array([
            edge(target("o", ["spaceId": "space", "objectId": "destination"]), sourceSpace: decomposed)
        ])]), spaceID: composed))
        var malformed = target("o", ["spaceId": "space", "objectId": "destination"]).object!
        malformed["uri"] = .string("any://o/other-space/destination")
        XCTAssertThrowsError(try outgoing(.object(["links": .array([edge(.object(malformed))])])))
        XCTAssertThrowsError(try outgoing(.object(["links": .array([
            edge(target("o", ["spaceId": "space", "objectId": "destination"]), sourceObject: "other-object")
        ])])))
    }

    func testBacklinksRetainObjectAndPartGroupsAndNarrowToTheExactPart() throws {
        let objectEdge = edge(target("o", ["spaceId": "space", "objectId": "object"]), sourceObject: "source")
        let recordEdge = edge(target("o", ["spaceId": "space", "objectId": "object",
                                               "dataset": "page", "recordId": "block"]), sourceObject: "source")
        let propertyEdge = edge(target("p", ["spaceId": "space", "objectId": "object",
                                                 "propId": "property"]), sourceObject: "source")
        let all = try incoming(.object(["object": .array([objectEdge]), "parts": .array([recordEdge, propertyEdge])]))
        XCTAssertEqual(all.object.count, 1)
        XCTAssertEqual(all.parts.count, 2)
        XCTAssertEqual(all.parts[0].target.recordID, "block")
        let narrowed = try incoming(.object(["object": .array([recordEdge]), "parts": .array([])]),
                                    selection: .record(dataset: "page", recordID: "block"))
        XCTAssertEqual(narrowed.object[0].target.recordID, "block")
        XCTAssertTrue(narrowed.parts.isEmpty)
        XCTAssertThrowsError(try incoming(.object(["object": .array([recordEdge]), "parts": .array([])])))
        XCTAssertThrowsError(try incoming(.object(["object": .array([]), "parts": .array([recordEdge])]),
                                           selection: .record(dataset: "page", recordID: "block")))
    }

    func testBacklinksRejectDifferentSourceSpaceTargetObjectAndProperty() throws {
        for candidate in [
            edge(target("o", ["spaceId": "space", "objectId": "object"]), sourceSpace: "other-space"),
            edge(target("o", ["spaceId": "space", "objectId": "different-object"])),
            edge(target("o", ["spaceId": "different-space", "objectId": "object"]))
        ] {
            XCTAssertThrowsError(try incoming(.object(["object": .array([candidate]), "parts": .array([])])))
        }
        let wrongProperty = edge(target("p", ["spaceId": "space", "objectId": "object", "propId": "different"]))
        XCTAssertThrowsError(try incoming(.object(["object": .array([wrongProperty]), "parts": .array([])]),
                                           selection: .property("property")))
    }

    func testTruncationAndNullArraysNeverBecomeCompleteEmptyReads() throws {
        let body: AnyJSON = .object(["links": .array([edge(target("u", ["identity": "member"]))]),
                                     "truncated": .bool(true)])
        XCTAssertThrowsError(try outgoing(body)) { XCTAssertEqual($0 as? AnyEngineError, .readLimit) }
        let partial = try outgoing(body, requireComplete: false)
        XCTAssertTrue(partial.truncated)
        XCTAssertEqual(partial.links.count, 1)
        XCTAssertThrowsError(try outgoing(.object(["links": .null])))
        XCTAssertThrowsError(try outgoing(.object(["links": .array([]), "truncated": .string("false")])))
        XCTAssertThrowsError(try incoming(.object(["object": .array([])])))
        XCTAssertThrowsError(try outgoing(.object(["links": .array([
            edge(target("u", ["identity": "member"])), edge(target("u", ["identity": "other"]))
        ])]), limit: 1))
    }

    func testMalformedOrFutureTargetKindsFailWithoutDiscardingEdges() throws {
        let malformed: [AnyJSON] = [
            .object(["kind": .string("i"), "uri": .string("any://i/invite")]),
            .object(["kind": .string("u"), "uri": .string("any://u/member"),
                     "identity": .string("member"), "spaceId": .string("space")]),
            .object(["kind": .string("o"), "uri": .string("any://o/space/object"),
                     "spaceId": .string("space"), "objectId": .string("object"), "recordId": .string("record")]),
            .object(["kind": .string("f"), "uri": .string("any://f/space/file?variant=thumbnail"),
                     "spaceId": .string("space"), "fileId": .string("file")])
        ]
        for wrong in malformed {
            XCTAssertThrowsError(try outgoing(.object(["links": .array([edge(wrong)])])))
        }
    }

    func testPropertySourceRetainsDeclaringTypeAndRecordSourceRetainsField() throws {
        var prop = edge(target("u", ["identity": "member"])).object!
        prop["source"] = .object(["spaceId": .string("space"), "objectId": .string("object"),
            "dataset": .string("prop"), "recordId": .string("creator"), "typeId": .string("type")])
        let result = try outgoing(.object(["links": .array([.object(prop)])]), selection: .property("creator"))
        XCTAssertEqual(result.links[0].source.typeID, "type")
        XCTAssertEqual(result.links[0].source.recordID, "creator")
        let row = try outgoing(.object(["links": .array([edge(target("u", ["identity": "member"]))])]))
        XCTAssertEqual(row.links[0].source.field, "text")
        XCTAssertThrowsError(try outgoing(.object(["links": .array([.object(prop)])]), selection: .property("other")))
    }

    private func outgoing(_ value: AnyJSON, spaceID: String = "space",
                          selection: AnyNativeLinkSelection = .object, limit: Int = 500,
                          requireComplete: Bool = true) throws -> AnyNativeLinksSnapshot {
        try AnyNativeObjectLinks.decodeLinks(value, accountID: "account", spaceID: spaceID,
            objectID: "object", selection: selection, kind: nil, limit: limit, requireComplete: requireComplete)
    }

    private func incoming(_ value: AnyJSON, selection: AnyNativeLinkSelection = .object) throws -> AnyNativeBacklinksSnapshot {
        try AnyNativeObjectLinks.decodeBacklinks(value, accountID: "account", spaceID: "space",
            objectID: "object", selection: selection, kind: nil, limit: 500, requireComplete: true)
    }

    private func edge(_ target: AnyJSON, kind: String = "mention",
                      sourceSpace: String = "space", sourceObject: String = "object") -> AnyJSON {
        .object(["kind": .string(kind), "target": target, "source": .object([
            "spaceId": .string(sourceSpace), "objectId": .string(sourceObject),
            "dataset": .string("page"), "recordId": .string("block"), "field": .string("text")])])
    }

    private func target(_ kind: String, _ values: [String: String]) -> AnyJSON {
        let keys: [String]
        switch kind {
        case "o": keys = values["dataset"] == nil ? ["spaceId", "objectId"] : ["spaceId", "objectId", "dataset", "recordId"]
        case "p": keys = ["spaceId", "objectId", "propId"]
        case "u": keys = ["identity"]
        default: keys = ["spaceId", "fileId"]
        }
        var result = values.mapValues(AnyJSON.string)
        result["kind"] = .string(kind)
        result["uri"] = .string("any://" + ([kind] + keys.map { values[$0]! }).joined(separator: "/"))
        return .object(result)
    }
}

#if os(macOS) || os(Linux)
final class AnyNativeObjectLinksHTTPTests: XCTestCase, @unchecked Sendable {
    func testScopedReadUsesNativeRouteAndRetainsAuthorizationThroughPublication() async throws {
        let fixture = try NativeLinksFixture(body: .object(["links": .array([])]))
        defer { fixture.stop() }
        let checks = NativeLinksAuthorizationCount()
        let result = try await AnyNativeObjectLinks(client: fixture.client()).links(
            spaceID: "space", objectID: "object", selection: .record(dataset: "page", recordID: "block"),
            kind: "mention", limit: 37, authorize: { await checks.check() })
        XCTAssertEqual(result.accountID, "account")
        XCTAssertTrue(result.links.isEmpty)
        XCTAssertFalse(result.truncated)
        let total = await checks.value
        XCTAssertEqual(total, 3)
        XCTAssertEqual(try fixture.dispatched(),
            ["/v1/spaces/space/objects/object/links?dataset=page&kind=mention&limit=37&record=block"])
    }

    func testNativeIndexDisabledPropagatesInsteadOfBecomingEmpty() async throws {
        let fixture = try NativeLinksFixture(body: .object(["error": .object(["code": .string("index.disabled")])]),
                                             status: 409)
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeObjectLinks(client: fixture.client()).backlinks(spaceID: "space", objectID: "object", authorize: {})
            XCTFail("A disabled native index became an empty computed property")
        } catch { XCTAssertEqual(error as? AnyEngineError, .http(status: 409, code: "index.disabled")) }
        XCTAssertEqual(try fixture.dispatched().count, 1)
    }

    func testRevokedReadCannotPublishAComputedSnapshot() async throws {
        let fixture = try NativeLinksFixture(body: .object(["object": .array([]), "parts": .array([])]))
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeObjectLinks(client: fixture.client()).backlinks(
                spaceID: "space", objectID: "object", authorize: { try fixture.requireBeforeResponse() })
            XCTFail("A computed snapshot escaped its revoked lifetime")
        } catch { XCTAssertEqual(error as? NativeLinksFailure, .revoked) }
        XCTAssertEqual(try fixture.dispatched().count, 1)
    }

    func testAccountSwitchCannotPublishOriginalAccountSnapshot() async throws {
        let fixture = try NativeLinksFixture(body: .object(["links": .array([])]), switchAccount: true)
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeObjectLinks(client: fixture.client()).links(spaceID: "space", objectID: "object", authorize: {})
            XCTFail("An account change escaped the link snapshot fence")
        } catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        XCTAssertEqual(try fixture.dispatched().count, 1)
    }

    func testInvalidBacklinkDatasetDoesNotDispatch() async throws {
        let fixture = try NativeLinksFixture(body: .object(["object": .array([]), "parts": .array([])]))
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeObjectLinks(client: fixture.client()).backlinks(
                spaceID: "space", objectID: "object", selection: .dataset("page"), authorize: {})
            XCTFail("Ambiguous dataset-only backlinks were dispatched")
        } catch { XCTAssertEqual(error as? AnyEngineError, .invalidOperation("backlinks require a record or property")) }
        XCTAssertEqual(try fixture.dispatched(), [])
    }
}

private enum NativeLinksFailure: Error { case revoked }
private actor NativeLinksAuthorizationCount {
    private(set) var value = 0
    func check() { value += 1 }
}

private final class NativeLinksFixture: @unchecked Sendable {
    private let process = Process()
    private let pipe = Pipe()
    private let directory: URL
    private var port = 0

    init(body: AnyJSON, status: Int = 200, switchAccount: Bool = false) throws {
        directory = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-native-links-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        try JSONEncoder().encode(AnyJSON.object(["body": body, "status": .integer(Int64(status)),
            "switchAccount": .bool(switchAccount)])).write(to: directory.appendingPathComponent("config.json"))
        let script = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Fixtures/native_links_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            let line = String(data: pipe.fileHandleForReading.availableData, encoding: .utf8) ?? ""
            guard let port = Int(line.trimmingCharacters(in: .whitespacesAndNewlines)), (1...65_535).contains(port) else {
                throw AnyEngineError.invalidEndpoint
            }
            self.port = port
        } catch {
            if process.isRunning { process.terminate() }
            if process.processIdentifier > 0 { process.waitUntilExit() }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    func client() throws -> AnyHTTPClient {
        try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:\(port)")!, expectedAccountID: "account")
    }

    func requireBeforeResponse() throws {
        if FileManager.default.fileExists(atPath: directory.appendingPathComponent("response-began").path) {
            throw NativeLinksFailure.revoked
        }
    }

    func dispatched() throws -> [String] {
        let path = directory.appendingPathComponent("dispatch.json")
        guard FileManager.default.fileExists(atPath: path.path) else { return [] }
        return try JSONDecoder().decode([String].self, from: Data(contentsOf: path))
    }

    func stop() {
        if process.isRunning { process.terminate() }
        if process.processIdentifier > 0 { process.waitUntilExit() }
        try? FileManager.default.removeItem(at: directory)
    }
}
#endif
