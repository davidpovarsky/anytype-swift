import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
@testable import PinkhaHanlinCore

/// Pure production planner/state transitions only. No native write, conversion,
/// Apple execution, filesystem durability or UI behavior is claimed by this suite.
final class PinkhaHanlinSaveMessageStateTests: XCTestCase {
    func testExactTitleAndMarkdownBytesArePreserved() throws {
        let fixture = try Fixture()
        let title = "  כותרת e\u{301}  "
        let markdown = "# כותרת\r\n\r\n**שלום** `a_b` 👩🏽‍💻\n"
        let plan = try fixture.plan(title: title, markdown: markdown)
        XCTAssertEqual(Data(plan.title.utf8), Data(title.utf8))
        XCTAssertEqual(Data(plan.markdown.utf8), Data(markdown.utf8))
        XCTAssertEqual(plan.identity.session, fixture.session)
    }

    func testBoundsUseUTF8BytesWithoutTruncation() throws {
        let fixture = try Fixture()
        let maximum = try fixture.plan(title: String(repeating: "א", count: 256),
                                       markdown: String(repeating: "😀", count: 16_384))
        XCTAssertEqual(maximum.title.utf8.count, 512)
        XCTAssertEqual(maximum.markdown.utf8.count, 65_536)
        XCTAssertThrowsError(try fixture.plan(title: String(repeating: "א", count: 257)))
        XCTAssertThrowsError(try fixture.plan(markdown: String(repeating: "😀", count: 16_384) + "a"))
    }

    func testOnlyExactTwoStringArgumentsAreAccepted() throws {
        let fixture = try Fixture()
        let bad: [HanlinJSONValue] = [
            .object([:]), .array([]),
            .object(["title": .string("Title")]),
            .object(["title": .string("Title"), "markdown": .null]),
            .object(["title": .string("Title"), "markdown": .integer(1)]),
            .object(["title": .integer(1), "markdown": .string("Body")]),
            .object(["title": .string(" \n"), "markdown": .string("Body")]),
            .object(["title": .string("Title"), "markdown": .string("")]),
            .object(["title": .string("Title"), "markdown": .string("Body"), "space": .string("other")]),
            .object(["title": .string("Title"), "markdown": .string("Body"), "objectID": .string("existing")])
        ]
        for arguments in bad {
            XCTAssertThrowsError(try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation(arguments: arguments)))
        }
    }

    func testReadOnlyCASAndOldCreateAliasCannotBecomeMessageSave() throws {
        let fixture = try Fixture()
        for guarantee in [HanlinHostWriteGuarantee.readOnly, .atomicRevisionMutation] {
            XCTAssertThrowsError(try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation(guarantee: guarantee)))
        }
        XCTAssertThrowsError(try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation(expectedRevision: "version")))
        XCTAssertThrowsError(try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation(alias: "anytype_create_page")))
        XCTAssertThrowsError(try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation(localTool: "create-page")))
    }

    func testInputIdentityDoesNotNormalizeUnicodeOrConfuseTitleBodyBoundaries() throws {
        let fixture = try Fixture()
        let composed = try fixture.plan(markdown: "é")
        let decomposed = try fixture.plan(markdown: "e\u{301}")
        XCTAssertNotEqual(composed.identity.argumentsDigest, decomposed.identity.argumentsDigest)
        XCTAssertNotEqual(try fixture.plan(title: "a", markdown: "bc").identity.argumentsDigest,
                          try fixture.plan(title: "ab", markdown: "c").identity.argumentsDigest)
    }

    func testOriginalMutationIDsSurviveReplayAndDistinctIdenticalBlocksDoNotCollide() throws {
        let fixture = try Fixture()
        let first = try fixture.manifest(blockDigests: [digest("same"), digest("same")])
        let second = try fixture.manifest(blockDigests: [digest("same"), digest("same")])
        XCTAssertEqual(first.rootMutationID, second.rootMutationID)
        XCTAssertEqual(try first.blockMutationID(at: 0), try second.blockMutationID(at: 0))
        XCTAssertNotEqual(try first.blockMutationID(at: 0), try first.blockMutationID(at: 1))
        XCTAssertNotEqual(first.rootMutationID, try first.blockMutationID(at: 0))
        XCTAssertThrowsError(try first.blockMutationID(at: -1))
        XCTAssertThrowsError(try first.blockMutationID(at: 2))
    }

    func testManifestRejectsUnsupportedSizeAndChangedContent() throws {
        let fixture = try Fixture()
        XCTAssertThrowsError(try fixture.manifest(blockDigests: []))
        XCTAssertThrowsError(try fixture.manifest(blockDigests: Array(repeating: digest("b"), count: 65)))
        XCTAssertThrowsError(try fixture.manifest(blockDigests: ["not-a-digest"]))
        let manifest = try fixture.manifest()
        XCTAssertThrowsError(try manifest.validate(plan: fixture.plan(markdown: "changed")))
    }

    func testKnownOrVerifiedRootAloneNeverCompletesMessageSave() throws {
        var state = try Fixture().initial()
        state = try state.applying(.rootDispatched)
        state = try state.applying(.rootKnown(reference: "native-page"))
        XCTAssertEqual(state.root.reference, "native-page")
        XCTAssertFalse(state.root.isVerified)
        XCTAssertFalse(state.isReadyForCommit)
        XCTAssertThrowsError(try state.applying(.blockDispatched(index: 0)))
        state = try state.applying(.rootVerified(reference: "native-page", readbackSHA256: digest("page")))
        XCTAssertFalse(state.isReadyForCommit)
        XCTAssertThrowsError(try state.applying(.bodyVerified(readback(state, references: []))))
    }

    func testOnlySequentialPreflightedBodyEffectsMayDispatch() throws {
        var state = try Fixture().initial(blockDigests: [digest("first"), digest("second")])
        XCTAssertThrowsError(try state.applying(.blockDispatched(index: 0)))
        state = try verifyRoot(state)
        XCTAssertThrowsError(try state.applying(.blockDispatched(index: 1)))
        state = try state.applying(.blockDispatched(index: 0))
        XCTAssertThrowsError(try state.applying(.blockDispatched(index: 0)))
        XCTAssertThrowsError(try state.applying(.blockDispatched(index: 1)))
        state = try state.applying(.blockVerified(index: 0, reference: "block-0", readbackSHA256: digest("first")))
        state = try state.applying(.blockDispatched(index: 1))
        XCTAssertFalse(state.isReadyForCommit)
    }

    func testCancellationBeforeDispatchIsTerminalWithoutInventingAWrite() throws {
        let state = try Fixture().initial().applying(.closeDispatch)
        XCTAssertTrue(state.isNotDispatched)
        XCTAssertFalse(state.isReadyForCommit)
        XCTAssertThrowsError(try state.applying(.rootDispatched))
        XCTAssertThrowsError(try state.applying(.rootKnown(reference: "unobserved")))
        XCTAssertThrowsError(try state.applying(.rootUncertain))
    }

    func testCancellationKeepsLateNativeReceiptButCannotStartAnotherEffect() throws {
        var state = try verifyRoot(Fixture().initial(blockDigests: [digest("first"), digest("second")]))
        state = try state.applying(.blockDispatched(index: 0))
        state = try state.applying(.closeDispatch)
        state = try state.applying(.blockUncertain(index: 0))
        state = try state.applying(.blockKnown(index: 0, reference: "late-block"))
        state = try state.applying(.blockVerified(index: 0, reference: "late-block", readbackSHA256: digest("first")))
        XCTAssertEqual(state.blocks[0].reference, "late-block")
        XCTAssertFalse(state.isNotDispatched)
        XCTAssertFalse(state.isReadyForCommit)
        XCTAssertThrowsError(try state.applying(.blockDispatched(index: 1)))
    }

    func testLastDispatchedEffectMaySettleOriginalAggregateAfterCancellation() throws {
        var state = try verifyRoot(Fixture().initial())
        state = try state.applying(.blockDispatched(index: 0))
        state = try state.applying(.closeDispatch)
        state = try state.applying(.blockVerified(index: 0, reference: "late-block", readbackSHA256: digest("body")))
        state = try state.applying(.bodyVerified(readback(state, references: ["late-block"])))
        XCTAssertTrue(state.isReadyForCommit)
        XCTAssertTrue(state.dispatchClosed)
        // No generic Hanlin journal .committed or caller/UI delivery occurs here.
    }

    func testUncertaintyNeverAuthorizesRootOrBlockRedispatch() throws {
        var state = try Fixture().initial().applying(.rootDispatched).applying(.rootUncertain)
        XCTAssertThrowsError(try state.applying(.rootDispatched))
        state = try state.applying(.rootKnown(reference: "original-root"))
        XCTAssertThrowsError(try state.applying(.rootKnown(reference: "replacement-root")))
        state = try state.applying(.rootVerified(reference: "original-root", readbackSHA256: digest("page")))
        state = try state.applying(.blockDispatched(index: 0)).applying(.blockUncertain(index: 0))
        XCTAssertThrowsError(try state.applying(.blockDispatched(index: 0)))
        state = try state.applying(.blockKnown(index: 0, reference: "original-block"))
        XCTAssertThrowsError(try state.applying(.blockVerified(index: 0, reference: "replacement-block", readbackSHA256: digest("body"))))
    }

    func testDuplicateNativeConfirmationIsMetadataNoOpAndCannotChangeDigest() throws {
        var state = try verifyRoot(Fixture().initial())
        let unchanged = try state.applying(.rootVerified(reference: "native-page", readbackSHA256: digest("page")))
        XCTAssertEqual(unchanged, state)
        XCTAssertThrowsError(try PinkhaHanlinSaveMessageProgressRecord(previous: state,
            event: .rootVerified(reference: "native-page", readbackSHA256: digest("page"))))
        XCTAssertThrowsError(try state.applying(.rootVerified(reference: "native-page", readbackSHA256: digest("different"))))
        state = try state.applying(.rootUncertain)
        XCTAssertTrue(state.root.isVerified)
    }

    func testCompleteReadbackBindsManifestRootAndOrderedExactBlockReferences() throws {
        var state = try verifyRoot(Fixture().initial(blockDigests: [digest("first"), digest("second")]))
        for index in 0..<2 {
            state = try state.applying(.blockDispatched(index: index))
            state = try state.applying(.blockVerified(index: index, reference: "block-\(index)",
                                                     readbackSHA256: state.manifest.blockSHA256[index]))
        }
        XCTAssertThrowsError(try state.applying(.bodyVerified(readback(state, references: ["block-1", "block-0"]))))
        XCTAssertThrowsError(try state.applying(.bodyVerified(readback(state, references: ["block-0"]))))
        XCTAssertThrowsError(try state.applying(.bodyVerified(.init(manifestSHA256: digest("other"),
            objectReference: "native-page", blockReferences: ["block-0", "block-1"],
            nativeReadbackSHA256: state.manifest.expectedBodyReadbackSHA256))))
        XCTAssertThrowsError(try state.applying(.bodyVerified(.init(manifestSHA256: state.manifest.canonicalSHA256(),
            objectReference: "foreign-page", blockReferences: ["block-0", "block-1"],
            nativeReadbackSHA256: state.manifest.expectedBodyReadbackSHA256))))
        state = try state.applying(.bodyVerified(readback(state, references: ["block-0", "block-1"])))
        XCTAssertTrue(state.isReadyForCommit)
    }

    func testNativeReferenceCannotBeReusedForAnotherBodyBlockOrRoot() throws {
        var state = try verifyRoot(Fixture().initial(blockDigests: [digest("a"), digest("b")]))
        state = try state.applying(.blockDispatched(index: 0))
        XCTAssertThrowsError(try state.applying(.blockKnown(index: 0, reference: "native-page")))
        state = try state.applying(.blockVerified(index: 0, reference: "block", readbackSHA256: digest("a")))
        state = try state.applying(.blockDispatched(index: 1))
        XCTAssertThrowsError(try state.applying(.blockKnown(index: 1, reference: "block")))
    }

    func testKnownIDsWithWrongRootOrBlockContentCannotBecomeVerified() throws {
        var state = try Fixture().initial().applying(.rootDispatched)
        state = try state.applying(.rootKnown(reference: "native-page"))
        XCTAssertThrowsError(try state.applying(.rootVerified(reference: "native-page",
                                                              readbackSHA256: digest("wrong-title-or-type"))))
        state = try state.applying(.rootVerified(reference: "native-page", readbackSHA256: digest("page")))
        state = try state.applying(.blockDispatched(index: 0))
        state = try state.applying(.blockKnown(index: 0, reference: "block"))
        XCTAssertThrowsError(try state.applying(.blockVerified(index: 0, reference: "block",
                                                              readbackSHA256: digest("wrong-content-or-style"))))
        XCTAssertFalse(state.isReadyForCommit)
    }

    func testSyntacticallyValidButWrongCompleteBodyDigestCannotCommit() throws {
        var state = try verifyRoot(Fixture().initial())
        state = try state.applying(.blockDispatched(index: 0))
        state = try state.applying(.blockVerified(index: 0, reference: "block", readbackSHA256: digest("body")))
        let wrong = PinkhaHanlinSaveMessageBodyReadback(manifestSHA256: try state.manifest.canonicalSHA256(),
            objectReference: "native-page", blockReferences: ["block"],
            nativeReadbackSHA256: digest("wrong-hierarchy-or-document-content"))
        XCTAssertThrowsError(try state.applying(.bodyVerified(wrong)))
        XCTAssertFalse(state.isReadyForCommit)
        state = try state.applying(.bodyVerified(readback(state, references: ["block"])))
        XCTAssertTrue(state.isReadyForCommit)
    }

    func testCanonicalEventReplayRejectsMissingReorderedOrForeignHistory() throws {
        let initial = try Fixture().initial()
        let first = try PinkhaHanlinSaveMessageProgressRecord(previous: initial, event: .rootDispatched)
        let middle = try first.replay(on: initial)
        let second = try PinkhaHanlinSaveMessageProgressRecord(previous: middle, event: .rootKnown(reference: "root"))
        let data = try second.canonicalBytes()
        let restored = try PinkhaHanlinSaveMessageProgressRecord.decodeCanonical(data, previous: middle)
        XCTAssertEqual(try restored.replay(on: middle), try middle.applying(.rootKnown(reference: "root")))
        XCTAssertThrowsError(try second.replay(on: initial))
        XCTAssertThrowsError(try first.replay(on: middle))
        XCTAssertThrowsError(try first.replay(on: Fixture(app: "anytype-any").initial()))
    }

    func testCanonicalDecodeRejectsUnknownFieldsAndForeignOriginalIdentity() throws {
        let fixture = try Fixture()
        let state = try fixture.initial()
        let data = try state.canonicalBytes()
        XCTAssertEqual(try PinkhaHanlinSaveMessageProgress.decodeCanonical(data, identity: fixture.plan().identity), state)
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        json["inventedPermission"] = true
        let unknown = try JSONSerialization.data(withJSONObject: json, options: [.sortedKeys])
        XCTAssertThrowsError(try PinkhaHanlinSaveMessageProgress.decodeCanonical(unknown, identity: fixture.plan().identity))
        XCTAssertThrowsError(try PinkhaHanlinSaveMessageProgress.decodeCanonical(data,
            identity: Fixture(account: "other-account").plan().identity))
        XCTAssertThrowsError(try PinkhaHanlinSaveMessageProgress.decodeCanonical(data,
            identity: Fixture(space: "other-space").plan().identity))
    }

    func testProgressAndEventsDoNotPersistBusinessTitleOrMarkdown() throws {
        let fixture = try Fixture()
        let plan = try fixture.plan()
        let state = try fixture.initial()
        let record = try PinkhaHanlinSaveMessageProgressRecord(previous: state, event: .rootDispatched)
        for bytes in [try state.canonicalBytes(), try record.canonicalBytes()] {
            let text = String(decoding: bytes, as: UTF8.self)
            XCTAssertFalse(text.contains(plan.title))
            XCTAssertFalse(text.contains(plan.markdown))
        }
    }

    func testMaximumEscapedNativeReferencesFitBoundedFinalRecordAndReplayExactly() throws {
        let fixture = try Fixture()
        let root = String(repeating: "\\", count: 256)
        let references = (0..<64).map { index in
            let prefix = "block-\(index):"
            return prefix + String(repeating: "\\", count: 256 - prefix.utf8.count)
        }
        var state = try fixture.initial(blockDigests: Array(repeating: digest("body"), count: 64))
        state = try state.applying(.rootDispatched).applying(.rootVerified(reference: root, readbackSHA256: digest("page")))
        for index in references.indices {
            state = try state.applying(.blockDispatched(index: index))
                .applying(.blockVerified(index: index, reference: references[index], readbackSHA256: digest("body")))
        }
        let readback = PinkhaHanlinSaveMessageBodyReadback(manifestSHA256: try state.manifest.canonicalSHA256(),
            objectReference: root, blockReferences: references, nativeReadbackSHA256: digest("original-native-readback"))
        let record = try PinkhaHanlinSaveMessageProgressRecord(previous: state, event: .bodyVerified(readback))
        let bytes = try record.canonicalBytes()
        XCTAssertGreaterThan(bytes.count, 32_768)
        XCTAssertLessThanOrEqual(bytes.count, 65_536)
        let restored = try PinkhaHanlinSaveMessageProgressRecord.decodeCanonical(bytes, previous: state)
        let complete = try restored.replay(on: state)
        XCTAssertTrue(complete.isReadyForCommit)
        XCTAssertEqual(try complete.canonicalBytes(), try state.applying(.bodyVerified(readback)).canonicalBytes())
        XCTAssertThrowsError(try PinkhaHanlinSaveMessageProgressRecord.decodeCanonical(
            Data(repeating: 0x20, count: 65_537), previous: state))
    }

    func testControlBearingNativeReferencesAreRefusedBeforeReceiptEncoding() throws {
        let state = try Fixture().initial().applying(.rootDispatched)
        for scalar in ["\u{0}", "\u{1}", "\t", "\n", "\u{7f}", "\u{85}"] {
            XCTAssertThrowsError(try state.applying(.rootKnown(reference: "native" + scalar + "id")))
        }
    }

    private func digest(_ value: String) -> String { PinkhaHanlinCreatePagePlan.digest(Data(value.utf8)) }

    private func verifyRoot(_ initial: PinkhaHanlinSaveMessageProgress) throws -> PinkhaHanlinSaveMessageProgress {
        try initial.applying(.rootDispatched).applying(.rootVerified(reference: "native-page", readbackSHA256: digest("page")))
    }

    private func readback(_ state: PinkhaHanlinSaveMessageProgress, references: [String]) throws -> PinkhaHanlinSaveMessageBodyReadback {
        .init(manifestSHA256: try state.manifest.canonicalSHA256(), objectReference: "native-page",
              blockReferences: references, nativeReadbackSHA256: digest("original-native-readback"))
    }

    private struct Fixture {
        let session: HanlinHostSession
        let id = UUID().uuidString.lowercased()
        let run = UUID()
        let provider = UUID().uuidString
        let deadline = Date().addingTimeInterval(20)

        init(app: String = "anytype", account: String = "disposable-account", space: String = "disposable-space") throws {
            session = .init(conversationID: UUID(), context: .init(
                namespace: try .init(app: app, account: account, workspace: space, space: space),
                sceneID: UUID(), generation: UUID()))
        }

        func invocation(arguments: HanlinJSONValue = .object([
            "title": .string("PRIVATE-SAVE-TEST-TITLE"), "markdown": .string("PRIVATE-SAVE-TEST-BODY")]),
            guarantee: HanlinHostWriteGuarantee = .independentObjectCreation,
            expectedRevision: String? = nil, alias: String = PinkhaHanlinSaveMessagePlan.alias,
            localTool: String = "save-message") throws -> HanlinHostInvocation {
            .init(request: .init(id: try .init(validating: id),
                logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"),
                                     localToolID: try .init(validating: localTool)),
                aliasUsed: alias, descriptorRevision: try .init(1), routingTableRevision: .init(1),
                arguments: arguments, origin: .assistantModel, deadline: deadline,
                limits: try .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
                session: session, runID: run, step: 0, providerCallID: provider,
                writeGuarantee: guarantee, expectedRevision: expectedRevision)
        }

        func plan(title: String = "PRIVATE-SAVE-TEST-TITLE", markdown: String = "PRIVATE-SAVE-TEST-BODY") throws -> PinkhaHanlinSaveMessagePlan {
            try .init(invocation: invocation(arguments: .object(["title": .string(title), "markdown": .string(markdown)])))
        }

        func manifest(blockDigests: [String]? = nil) throws -> PinkhaHanlinSaveMessageManifest {
            let blocks = blockDigests ?? [PinkhaHanlinCreatePagePlan.digest(Data("body".utf8))]
            let bodyDigest = PinkhaHanlinCreatePagePlan.digest(try JSONEncoder().encode(blocks))
            return try .init(plan: plan(), bodyPlanSHA256: bodyDigest,
                expectedRootReadbackSHA256: PinkhaHanlinCreatePagePlan.digest(Data("page".utf8)),
                expectedBodyReadbackSHA256: PinkhaHanlinCreatePagePlan.digest(Data("original-native-readback".utf8)),
                blockSHA256: blocks)
        }

        func initial(blockDigests: [String]? = nil) throws -> PinkhaHanlinSaveMessageProgress {
            try .init(manifest: manifest(blockDigests: blockDigests))
        }
    }
}
