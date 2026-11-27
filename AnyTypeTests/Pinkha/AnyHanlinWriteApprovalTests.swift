import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
@testable import PinkhaAnyHanlin

/// Typed native-consent identity tests only; no native create, body save or UI.
@MainActor
final class AnyHanlinWriteApprovalTests: XCTestCase {
    func testTitleOnlyApprovalCannotAuthorizeBodyAndIsConsumedExactlyOnce() throws {
        let fixture = try Fixture()
        let create = try PinkhaHanlinCreatePagePlan(invocation: fixture.invocation(save: false))
        let save = try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation(save: true))
        let approval = AnyHanlinWriteApproval(identity: create.identity, eligibility: fixture.eligibility)
        XCTAssertThrowsError(try approval.consume(save))
        XCTAssertEqual(try approval.consume(create), fixture.eligibility)
        XCTAssertThrowsError(try approval.consume(create))
        let bodyApproval = AnyHanlinWriteApproval(identity: save.identity, eligibility: fixture.eligibility)
        XCTAssertThrowsError(try bodyApproval.consume(create))
        XCTAssertEqual(try bodyApproval.consume(save), fixture.eligibility)
        XCTAssertThrowsError(try bodyApproval.consume(save))
    }

    func testBodyApprovalRejectsChangedBodyAccountAndRunBeforeConsumption() throws {
        let fixture = try Fixture()
        let approved = try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation(save: true))
        let approval = AnyHanlinWriteApproval(identity: approved.identity, eligibility: fixture.eligibility)
        let variants = [
            try fixture.invocation(save: true, markdown: "different complete body"),
            try fixture.invocation(save: true, account: "other-account"),
            try fixture.invocation(save: true, run: UUID())
        ]
        for invocation in variants {
            let changed = try PinkhaHanlinSaveMessagePlan(invocation: invocation)
            XCTAssertNotEqual(changed.identity, approved.identity)
            XCTAssertThrowsError(try approval.consume(changed))
        }
        XCTAssertEqual(try approval.consume(approved), fixture.eligibility)
        XCTAssertThrowsError(try approval.consume(approved))
    }

    private struct Fixture {
        let conversation = UUID(), scene = UUID(), generation = UUID(), run = UUID()
        let id = UUID().uuidString.lowercased()
        let deadline = Date().addingTimeInterval(25)
        let eligibility = AnyHanlinPageEligibility(fingerprint: "original-native-eligibility",
            permission: "writer", typeID: "page")
        init() throws {}
        func invocation(save: Bool, markdown: String = "complete original body",
                        account: String = "original-account", run: UUID? = nil) throws -> HanlinHostInvocation {
            let session = HanlinHostSession(conversationID: conversation, context: .init(
                namespace: try .init(app: "anytype-any", account: account,
                    workspace: "original-space", space: "original-space"),
                sceneID: scene, generation: generation))
            let arguments: HanlinJSONValue = save
                ? .object(["title": .string("Exact original title"), "markdown": .string(markdown)])
                : .object(["title": .string("Exact original title")])
            return .init(request: .init(id: try .init(validating: id),
                logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"),
                    localToolID: try .init(validating: save ? "save-message" : "create-page")),
                aliasUsed: save ? PinkhaHanlinSaveMessagePlan.alias : PinkhaHanlinCreatePagePlan.alias,
                descriptorRevision: try .init(1), routingTableRevision: .init(1), arguments: arguments,
                origin: .assistantModel, deadline: deadline,
                limits: try .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
                session: session, runID: run ?? self.run, step: 0, providerCallID: "original-provider-call",
                writeGuarantee: .independentObjectCreation, expectedRevision: nil)
        }
    }
}
