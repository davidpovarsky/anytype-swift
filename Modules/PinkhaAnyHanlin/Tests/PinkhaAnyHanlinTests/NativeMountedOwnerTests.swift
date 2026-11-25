import Foundation
import XCTest
import HanlinHostContracts
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaHanlinCore
@testable import PinkhaAnyHost
@testable import PinkhaAnyHanlin

final class NativeMountedOwnerTests: XCTestCase {
    @MainActor
    private final class SourceOwner: AnyHanlinPresentationOwner {
        let scope: AnyHanlinPresentationScope
        var mounted = true
        init(workspace: AnyTorahWorkspace) {
            scope = .init(accountID: workspace.accountID, spaceID: workspace.spaceID,
                          sceneID: UUID(), ownerID: UUID(), document: nil, selection: [])
        }
        func currentScope() throws -> AnyHanlinPresentationScope {
            guard mounted else { throw HanlinHostError.staleContext }
            return scope
        }
        func install(session: HanlinHostSession, invalidate: @escaping @Sendable () -> Void) throws {}
        func presentReadConsent(context: HanlinHostContext, answer: @escaping @MainActor (Bool) -> Void) throws {
            throw HanlinHostError.denied
        }
        func dismissPendingPrompts() {}
        func validateMounted(_ destination: HanlinHostDestination) throws { throw HanlinHostError.denied }
    }

    @MainActor
    private final class MountedOwner: PinkhaHanlinOwnedPresentation {
        let session: HanlinHostSession
        var revoked = false
        init(session: HanlinHostSession) { self.session = session }
        func invalidate() { revoked = true }
        func revokeAndDrain() async { }
    }

    @MainActor
    private func fixture() throws -> (AnyHanlinHost, SourceOwner, AnyApplicationSession) {
        let workspace = try AnyTorahWorkspace(accountID: "test-mounted-" + UUID().uuidString, spaceID: "space")
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: "http://127.0.0.1:1")),
                                       expectedAccountID: workspace.accountID)
        let native = AnyApplicationSession(workspace: workspace, engineStartedAt: "synthetic-owned-run",
                                            verifyRun: { "synthetic-owned-run" })
        let documents = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let source = SourceOwner(workspace: workspace)
        let host = try AnyHanlinHost(native: native, documents: documents, owner: source, conversationID: UUID())
        return (host, source, native)
    }

    @MainActor
    func testMountedOwnerReplacesProvisionalHostAndRemountsOnlySameIdentity() async throws {
        let (host, source, native) = try fixture()
        try withExtendedLifetime(source) {
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.owns(host))
            let presentation = MountedOwner(session: host.session)
            try PinkhaHanlinAccountOwner.shared.register(presentation)
            try host.bindMountedPresentation(presentation)
            XCTAssertFalse(PinkhaHanlinAccountOwner.shared.owns(host))
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.owns(presentation))
            try host.bindMountedPresentation(presentation)
            host.invalidate()
            XCTAssertThrowsError(try host.bindMountedPresentation(presentation))
        }
        await host.close()
        await native.revokeAndDrain()
    }

    @MainActor
    func testForeignSessionCannotBindNativeHost() async throws {
        let (host, source, native) = try fixture()
        try withExtendedLifetime(source) {
            let other = MountedOwner(session: .init(conversationID: UUID(), context: host.session.context))
            try PinkhaHanlinAccountOwner.shared.register(other)
            defer { PinkhaHanlinAccountOwner.shared.unregister(other.session.id) }
            XCTAssertThrowsError(try host.bindMountedPresentation(other))
            XCTAssertTrue(PinkhaHanlinAccountOwner.shared.owns(host))
        }
        await host.close()
        await native.revokeAndDrain()
    }

    @MainActor
    func testAnotherPresentationCannotRearmAnAlreadyBoundSDKSession() async throws {
        let (host, source, native) = try fixture()
        try withExtendedLifetime(source) {
            let first = MountedOwner(session: host.session)
            try PinkhaHanlinAccountOwner.shared.register(first)
            try host.bindMountedPresentation(first)
            let replacement = MountedOwner(session: host.session)
            try PinkhaHanlinAccountOwner.shared.register(replacement)
            XCTAssertThrowsError(try host.bindMountedPresentation(replacement))
            XCTAssertFalse(PinkhaHanlinAccountOwner.shared.owns(first))
        }
        await host.close()
        await native.revokeAndDrain()
    }

    @MainActor
    func testStaleSourceCannotBindEvenARegisteredMatchingPresentation() async throws {
        let (host, source, native) = try fixture()
        let presentation = MountedOwner(session: host.session)
        try PinkhaHanlinAccountOwner.shared.register(presentation)
        source.mounted = false
        XCTAssertThrowsError(try host.bindMountedPresentation(presentation))
        await host.close()
        await native.revokeAndDrain()
    }
}
