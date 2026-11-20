import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
@testable import PinkhaHanlinCore
@testable import PinkhaAnyHanlin

final class SharedHanlinCoreTests: XCTestCase {
    @MainActor
    func testRevocationCannotBeOverriddenByALateAllow() async {
        let decision = PinkhaHanlinReadConsentDecision()
        var result: Bool?
        XCTAssertTrue(decision.begin { result = $0 })
        decision.revoke()
        decision.resolveAllow(validating: {})
        XCTAssertEqual(result, false)
        XCTAssertTrue(decision.revoked)
        XCTAssertFalse(decision.authorized)
    }

    @MainActor
    func testNativeAllowRequiresLiveValidation() async {
        let decision = PinkhaHanlinReadConsentDecision()
        var result: Bool?
        XCTAssertTrue(decision.begin { result = $0 })
        decision.resolveAllow { throw HanlinHostError.staleContext }
        XCTAssertEqual(result, false)
        XCTAssertFalse(decision.authorized)
    }

    @MainActor
    func testReadCatalogUsesSharedConsentAndWriteInstallationRules() async throws {
        let access = try ReadFixture()
        let reader = try PinkhaHanlinHostAdapter(access: access)
        let router = try PinkhaHanlinHostRouter(read: reader, session: access.session, write: nil)
        let denied = try await router.catalog(for: access.session.context)
        XCTAssertTrue(denied.tools.isEmpty)
        access.consented = true
        let allowed = try await router.catalog(for: access.session.context)
        XCTAssertEqual(allowed.tools.count, 1)
        XCTAssertEqual(allowed.tools.first?.route.alias, "anytype_read_context_text")
        XCTAssertEqual(allowed.tools.first?.writeGuarantee, .readOnly)
        XCTAssertEqual(router.missingWriteInstallation, PinkhaHanlinWriteInstallationRequirement.missing)
        router.revokePresentation()
        do {
            _ = try await router.catalog(for: access.session.context)
            XCTFail("revoked router returned a catalog")
        } catch { XCTAssertEqual(error as? HanlinHostError, .staleContext) }
    }

    func testCanonicalPlanDigestPreservesExactUTF8() {
        XCTAssertEqual(PinkhaHanlinCreatePagePlan.digest(Data("abc".utf8)),
                       "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        XCTAssertNotEqual(PinkhaHanlinCreatePagePlan.digest(Data("é".utf8)),
                          PinkhaHanlinCreatePagePlan.digest(Data("e\u{301}".utf8)))
    }

    func testHomeScopeDoesNotInventDocumentOrSelection() throws {
        let session = try AnyHanlinScope.makeSession(
            accountID: "account", spaceID: "space", sceneID: UUID(),
            conversationID: UUID(), snapshot: nil, selection: [], locale: Locale(identifier: "he"))
        XCTAssertNil(session.context.objectReference)
        XCTAssertTrue(session.context.selectionReferences.isEmpty)
        XCTAssertNil(session.context.sourceRevision)
        XCTAssertEqual(session.context.namespace.app, "anytype")
        XCTAssertEqual(session.context.namespace.workspace, "space")
    }

    func testSelectionWithoutNativeDocumentIsRejected() {
        XCTAssertThrowsError(try AnyHanlinScope.makeSession(
            accountID: "account", spaceID: "space", sceneID: UUID(),
            conversationID: UUID(), snapshot: nil, selection: ["block"], locale: Locale(identifier: "he")))
    }
}

@MainActor
private final class ReadFixture: PinkhaHanlinHostAccess {
    let session: HanlinHostSession
    var consented = false

    init() throws {
        session = HanlinHostSession(conversationID: UUID(), context: .init(
            namespace: try .init(app: "anytype", account: "account", workspace: "space", space: "space"),
            sceneID: UUID(), generation: UUID(), objectReference: "document",
            sourceRevision: "revision", localeIdentifier: "he"))
    }
    func validate(_ context: HanlinHostContext) throws {
        guard context == session.context else { throw HanlinHostError.staleContext }
    }
    func validateRead(_ context: HanlinHostContext) throws {
        try validate(context)
        guard consented else { throw HanlinHostError.denied }
    }
    func read(_ context: HanlinHostContext) async throws -> PinkhaHanlinTextSnapshot {
        try validateRead(context)
        return .init(objectReference: "document", spaceReference: "space", sourceRevision: "revision",
                     title: "כותרת", blocks: [.init(reference: "block", text: "תורה")],
                     coverage: "documentTextBlocksOnly")
    }
    func navigate(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        try validate(destination.context)
        return .queued(requestID: destination.requestID, context: destination.context)
    }
}
