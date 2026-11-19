import XCTest
import Foundation
import HanlinHostContracts
import PinkhaAnyHost
@testable import PinkhaHanlinCore
@testable import PinkhaAnyHanlin

final class SharedHanlinAccountAndProjectionTests: XCTestCase {
    @MainActor
    private final class Presentation: PinkhaHanlinOwnedPresentation {
        let session: HanlinHostSession
        var invalidations = 0
        init(account: String) throws {
            let scope = try HanlinConversationNamespace(app: "anytype", account: account,
                                                       workspace: "native-space", space: "native-space")
            session = .init(conversationID: UUID(), context: .init(namespace: scope,
                sceneID: UUID(), generation: UUID()))
        }
        func invalidate() { invalidations += 1 }
    }

    @MainActor
    func testSharedAccountOwnerOnlyRevokesOriginalAccount() async throws {
        let first = try Presentation(account: "test-a-" + UUID().uuidString)
        let second = try Presentation(account: "test-b-" + UUID().uuidString)
        let owner = PinkhaHanlinAccountOwner.shared
        try owner.register(first); try owner.register(second)
        defer { owner.unregister(first.session.id); owner.unregister(second.session.id) }
        XCTAssertTrue(owner.owns(first)); XCTAssertTrue(owner.owns(second))
        try await owner.closeAccount(first.session.context.namespace.account, removeData: false)
        XCTAssertEqual(first.invalidations, 1)
        XCTAssertEqual(second.invalidations, 0)
        XCTAssertFalse(owner.isAvailable(account: first.session.context.namespace.account))
        XCTAssertThrowsError(try owner.register(first))
        XCTAssertTrue(owner.isAvailable(account: second.session.context.namespace.account))
        try owner.accountDidOpen(first.session.context.namespace.account)
        XCTAssertTrue(owner.isAvailable(account: first.session.context.namespace.account))
    }

    @MainActor
    func testRegistryUnregisterDoesNotEraseAnotherPresentation() throws {
        let account = "test-owner-" + UUID().uuidString
        let first = try Presentation(account: account), second = try Presentation(account: account)
        let owner = PinkhaHanlinAccountOwner.shared
        try owner.register(first); try owner.register(second)
        owner.unregister(first.session.id)
        defer { owner.unregister(second.session.id) }
        XCTAssertFalse(owner.owns(first)); XCTAssertTrue(owner.owns(second))
    }

    func testSelectedProjectionPreservesCanonicalBlockIdentityAndPlainText() throws {
        let snapshot = try makeSnapshot()
        let value = try AnyHanlinPlainText.project(snapshot, selection: ["child"])
        XCTAssertEqual(value.objectReference, "native-object")
        XCTAssertEqual(value.coverage, "selectedTextBlocksOnly")
        XCTAssertEqual(value.blocks.map(\.reference), ["child"])
        XCTAssertEqual(value.blocks.map(\.text), ["שלום עולם"])
        XCTAssertEqual(value.sourceRevision, snapshot.revision)
    }

    func testProjectionRejectsUnknownSelectionAndNonTextSelection() throws {
        let snapshot = try makeSnapshot()
        XCTAssertThrowsError(try AnyHanlinPlainText.project(snapshot, selection: ["missing"]))
        XCTAssertThrowsError(try AnyHanlinPlainText.project(snapshot, selection: ["media"]))
    }

    func testProjectionRefusesOrphansRatherThanLeakingDetachedText() throws {
        let snapshot = try makeSnapshot(orphan: true)
        XCTAssertThrowsError(try AnyHanlinPlainText.project(snapshot, selection: []))
    }

    private func makeSnapshot(orphan: Bool = false) throws -> AnyEditorSnapshot {
        try .init(spaceID: "native-space", objectID: "native-object", title: "כותרת",
                  response: .object([
                    "total": .integer(3), "hasNext": .bool(false), "records": .array([
                        .object(["id": .string("root"), "type": .string("paragraph"), "text": .string("ראש"),
                                 "nav": .object(["parentId": .string(""), "pos": .string("a")]),
                                 "_ver": .object(["text": .string("v1")])]),
                        .object(["id": .string("child"), "type": .string("paragraph"),
                                 "text": .string("**שלום** _עולם_"),
                                 "nav": .object(["parentId": .string(orphan ? "missing" : "root"), "pos": .string("b")]),
                                 "_ver": .object(["text": .string("v2")])]),
                        .object(["id": .string("media"), "type": .string("image"),
                                 "nav": .object(["parentId": .string(""), "pos": .string("c")]),
                                 "_ver": .object(["type": .string("v3")])])
                    ])]))
    }
}
