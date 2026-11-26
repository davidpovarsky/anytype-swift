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
        var drain: (@MainActor () async -> Void)?
        init(account: String, app: String = "anytype") throws {
            let scope = try HanlinConversationNamespace(app: app, account: account,
                                                       workspace: "native-space", space: "native-space")
            session = .init(conversationID: UUID(), context: .init(namespace: scope,
                sceneID: UUID(), generation: UUID()))
        }
        func invalidate() { invalidations += 1 }
        func revokeAndDrain() async { await drain?() }
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
    func testSameNativeAccountInOtherEngineKeepsItsPresentationAndAvailability() async throws {
        let account = "shared-native-account-" + UUID().uuidString
        let heart = try Presentation(account: account, app: "anytype")
        let any = try Presentation(account: account, app: "anytype-any")
        let owner = PinkhaHanlinAccountOwner.shared
        try owner.register(heart); try owner.register(any)
        defer { owner.unregister(heart.session.id); owner.unregister(any.session.id) }
        try await owner.closeAccount(account, removeData: false, app: "anytype-any")
        XCTAssertEqual(any.invalidations, 1)
        XCTAssertEqual(heart.invalidations, 0)
        XCTAssertFalse(owner.isAvailable(namespace: any.session.context.namespace))
        XCTAssertTrue(owner.isAvailable(namespace: heart.session.context.namespace))
        XCTAssertThrowsError(try owner.register(any))
        try owner.accountDidOpen(account, app: "anytype-any")
        XCTAssertTrue(owner.isAvailable(namespace: any.session.context.namespace))
        try await owner.closeAccount(account, removeData: false)
        XCTAssertEqual(heart.invalidations, 1)
        XCTAssertEqual(any.invalidations, 1)
        XCTAssertTrue(owner.isAvailable(namespace: any.session.context.namespace))
        try owner.accountDidOpen(account)
    }

    @MainActor
    func testEngineSwitchWaitsForActualDrainAndKeepsOtherEngineAvailable() async throws {
        let owner = PinkhaHanlinAccountOwner()
        let heart = try Presentation(account: "source", app: "anytype")
        let any = try Presentation(account: "source", app: "anytype-any")
        var release: CheckedContinuation<Void, Never>?
        var finished = false
        heart.drain = { await withCheckedContinuation { release = $0 } }
        try owner.register(heart); try owner.register(any)
        let closing = Task { @MainActor in
            try await owner.deactivateEngine("anytype")
            finished = true
        }
        for _ in 0..<1_000 {
            if release != nil { break }
            await Task.yield()
        }
        guard let release else {
            closing.cancel()
            XCTFail("Engine close did not reach the real presentation drain")
            return
        }
        XCTAssertFalse(finished)
        XCTAssertEqual(heart.invalidations, 1)
        XCTAssertEqual(any.invalidations, 0)
        XCTAssertFalse(owner.isAvailable(namespace: heart.session.context.namespace))
        XCTAssertTrue(owner.isAvailable(namespace: any.session.context.namespace))
        // A native account callback racing engine selection cannot reopen AI work.
        try owner.accountDidOpen("new-source", app: "anytype")
        XCTAssertFalse(owner.isAvailable(account: "new-source", app: "anytype"))
        XCTAssertThrowsError(try owner.activateEngine("anytype"))
        XCTAssertThrowsError(try owner.register(heart))
        release.resume()
        try await closing.value
        XCTAssertTrue(finished)
        XCTAssertFalse(owner.isAvailable(account: "new-source", app: "anytype"))
        try owner.activateEngine("anytype")
        XCTAssertTrue(owner.isAvailable(account: "new-source", app: "anytype"))
        XCTAssertTrue(owner.isAvailable(namespace: any.session.context.namespace))
    }

    @MainActor
    func testAccountCannotReopenUntilItsOwnedPresentationDrains() async throws {
        let owner = PinkhaHanlinAccountOwner()
        let account = "closing-account"
        let presentation = try Presentation(account: account)
        var release: CheckedContinuation<Void, Never>?
        presentation.drain = { await withCheckedContinuation { release = $0 } }
        try owner.register(presentation)
        let closing = Task { @MainActor in
            try await owner.closeAccount(account, removeData: false)
        }
        for _ in 0..<1_000 {
            if release != nil { break }
            await Task.yield()
        }
        guard let release else {
            closing.cancel()
            XCTFail("Account close did not reach the actual presentation drain")
            return
        }
        XCTAssertFalse(owner.isAvailable(account: account))
        XCTAssertThrowsError(try owner.accountDidOpen(account))
        XCTAssertThrowsError(try owner.register(presentation))
        release.resume()
        try await closing.value
        XCTAssertFalse(owner.isAvailable(account: account))
        try owner.accountDidOpen(account)
        XCTAssertTrue(owner.isAvailable(account: account))
    }

    @MainActor
    func testForeignEngineNamespaceCannotOpenOrRegisterAccount() throws {
        let account = "foreign-host-" + UUID().uuidString
        let owner = PinkhaHanlinAccountOwner.shared
        let foreign = try Presentation(account: account, app: "unrelated")
        XCTAssertFalse(owner.isAvailable(account: account, app: "unrelated"))
        XCTAssertThrowsError(try owner.accountDidOpen(account, app: "unrelated"))
        XCTAssertThrowsError(try owner.register(foreign))
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
