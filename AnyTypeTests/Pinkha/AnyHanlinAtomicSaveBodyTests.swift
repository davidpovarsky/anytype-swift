#if os(iOS)
import Foundation
import XCTest
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaHanlinUI
import PinkhaAnyHost
@testable import PinkhaAnyHanlin
@testable import PinkhaAnyEngine

/// Exact original parser plus native-value fixtures. These cases call no HTTP,
/// middleware, UI consent or native engine and do not qualify the actual worker.
@MainActor
final class AnyHanlinAtomicSaveBodyTests: XCTestCase {
    func testCompletedOriginalParserPlanUsesOneAtomicBodyAndExactRequestedBytes() async throws {
        let request = try plan("# כותרת\n\n**גוף** e\u{301}\n")
        let converted = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(request)
        let body = try AnyHanlinAtomicSaveBody(plan: request, conversion: converted)
        XCTAssertEqual(body.manifest.bodyMode, .conditionalMarkdown)
        XCTAssertEqual(body.document, converted.document)
        XCTAssertThrowsError(try body.manifest.blockMutationID(at: 0))
        let intent = try body.intent(reference: reference("native-page"), expectedVersion: "original-version")
        XCTAssertEqual(Data(intent.content.utf8), Data(request.markdown.utf8))
        XCTAssertEqual(intent.context.requestedContentSHA256, request.markdownSHA256)
        XCTAssertEqual(intent.context.requestID, body.manifest.conditionalBodyRequestID)
        XCTAssertFalse(body.description.contains(request.markdown))
    }

    func testOriginalCorrelationBindsPageVersionNativeGenerationAndBodyWithoutRetryIdentity() async throws {
        let request = try plan("body")
        let converted = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(request)
        let body = try AnyHanlinAtomicSaveBody(plan: request, conversion: converted)
        let first = try body.intent(reference: reference("native-page"), expectedVersion: "v1")
        let otherPage = try body.intent(reference: reference("other-page"), expectedVersion: "v1")
        let newer = try body.intent(reference: reference("native-page"), expectedVersion: "v2")
        let generation = UUID()
        let digest = try body.requestSHA256(first, generation: generation, engineStartedAt: "native-run-1")
        XCTAssertEqual(digest, try body.requestSHA256(first, generation: generation, engineStartedAt: "native-run-1"))
        XCTAssertNotEqual(digest, try body.requestSHA256(otherPage, generation: generation, engineStartedAt: "native-run-1"))
        XCTAssertNotEqual(digest, try body.requestSHA256(newer, generation: generation, engineStartedAt: "native-run-1"))
        XCTAssertNotEqual(digest, try body.requestSHA256(first, generation: UUID(), engineStartedAt: "native-run-1"))
        XCTAssertNotEqual(digest, try body.requestSHA256(first, generation: generation, engineStartedAt: "native-run-2"))
        XCTAssertEqual(first.context.requestID, newer.context.requestID)
        let changed = try AnyNativeMarkdownWriteIntent(reference: first.context.reference,
            requestID: first.context.requestID, expectedVersion: first.expectedVersion, content: "changed")
        XCTAssertThrowsError(try body.requestSHA256(changed, generation: generation, engineStartedAt: "native-run-1"))
        let foreign = try AnyNativeMarkdownReference(accountID: "other-account", spaceID: "disposable-space", objectID: "native-page")
        XCTAssertThrowsError(try body.intent(reference: foreign, expectedVersion: "v1"))
    }

    func testNativeACKMustBelongToExactOriginalRequestAndRetainsAllActualGroups() async throws {
        let request = try plan("body")
        let conversion = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(request)
        let body = try AnyHanlinAtomicSaveBody(plan: request, conversion: conversion)
        let intent = try body.intent(reference: reference("native-page"), expectedVersion: "v1")
        let requestDigest = try body.requestSHA256(intent, generation: UUID(), engineStartedAt: "run")
        let actual = ack(intent, inserted: ["new-b", "new-a"], updated: ["updated"], deleted: ["deleted"], unchanged: 2)
        let retained = try AnyHanlinAtomicSaveBody.admittedAcknowledgement(actual, intent: intent, requestSHA256: requestDigest)
        XCTAssertEqual(retained.insertedReferences, ["new-b", "new-a"])
        XCTAssertEqual(retained.updatedReferences, ["updated"])
        XCTAssertEqual(retained.deletedReferences, ["deleted"])
        XCTAssertEqual(retained.unchangedBlocks, 2)
        XCTAssertEqual(retained.nativeReceiptSHA256,
            try AnyHanlinAtomicSaveBody.unadmittedAcknowledgementDigest(actual, intent: intent, requestSHA256: requestDigest))
        let foreign = try AnyNativeMarkdownWriteIntent(reference: reference("other-page"),
            requestID: intent.context.requestID, expectedVersion: "v1", content: intent.content)
        XCTAssertThrowsError(try AnyHanlinAtomicSaveBody.admittedAcknowledgement(ack(foreign),
            intent: intent, requestSHA256: requestDigest))
        XCTAssertThrowsError(try AnyHanlinAtomicSaveBody.admittedAcknowledgement(ack(intent, version: ""),
            intent: intent, requestSHA256: requestDigest))
    }

    func testOverLimitActualACKRemainsUnadmittedWithoutTruncatingItsFingerprint() async throws {
        let request = try plan("body")
        let conversion = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(request)
        let body = try AnyHanlinAtomicSaveBody(plan: request, conversion: conversion)
        let intent = try body.intent(reference: reference("native-page"), expectedVersion: "v1")
        let requestDigest = try body.requestSHA256(intent, generation: UUID(), engineStartedAt: "run")
        let ids = (0..<65).map { "block-\($0)" }
        let actual = ack(intent, inserted: ids)
        XCTAssertThrowsError(try AnyHanlinAtomicSaveBody.admittedAcknowledgement(actual, intent: intent, requestSHA256: requestDigest))
        let full = try AnyHanlinAtomicSaveBody.unadmittedAcknowledgementDigest(actual, intent: intent, requestSHA256: requestDigest)
        let truncated = try AnyHanlinAtomicSaveBody.unadmittedAcknowledgementDigest(ack(intent, inserted: Array(ids.prefix(64))),
            intent: intent, requestSHA256: requestDigest)
        XCTAssertNotEqual(full, truncated)
    }

    func testNormalizedNativeBytesAreDistinctFromInputButFullSemanticAndACKIdentityStillRequired() async throws {
        let request = try plan("body")
        let conversion = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(request)
        let body = try AnyHanlinAtomicSaveBody(plan: request, conversion: conversion)
        let intent = try body.intent(reference: reference("native-page"), expectedVersion: "v1")
        let requestDigest = try body.requestSHA256(intent, generation: UUID(), engineStartedAt: "run")
        let metadata = try AnyHanlinAtomicSaveBody.admittedAcknowledgement(ack(intent, inserted: ["native-one"]),
            intent: intent, requestSHA256: requestDigest)
        let row = conversion.blocks[0]
        let snapshot = try AnyEditorSnapshot(spaceID: "disposable-space", objectID: "native-page", title: "TITLE",
            response: .object(["records": .array([.object([
                "id": .string("native-one"), "type": .string(row.type), "text": .string(row.text), "style": row.style,
                "nav": .object(["parentId": .string(""), "pos": .string(row.position)]),
                "_ver": .object(["text": .string("native-field-version")])
            ])]), "total": .integer(1), "hasNext": .bool(false)]))
        let actual = try AnyHanlinSaveMessageReadback(snapshot: snapshot, rootRecord: .object([
            "id": .string("native-page"), "spaceId": .string("disposable-space"),
            "any": .object(["name": .string("TITLE"), "type": .string("page")])
        ]), workspace: .init(accountID: "disposable-account", spaceID: "disposable-space"))
        let nativeExport = "body\n"
        let witness = try actual.verifiedBody(manifest: body.manifest,
            nativeVersionSHA256: metadata.savedVersionSHA256,
            nativeMarkdownSHA256: AnyHanlinAtomicSaveBody.digest(nativeExport), nativeMarkdownUTF8Bytes: nativeExport.utf8.count)
        XCTAssertNotEqual(witness.nativeMarkdownSHA256, body.manifest.markdownSHA256)
        XCTAssertEqual(witness.nativeReadbackSHA256, body.manifest.expectedBodyReadbackSHA256)
        var progress = try PinkhaHanlinSaveMessageProgress(manifest: body.manifest).applying(.rootDispatched)
            .applying(.rootVerified(reference: "native-page", readbackSHA256: actual.rootReadbackSHA256))
            .applying(.atomicBodyDispatched(requestSHA256: requestDigest,
                expectedVersionSHA256: AnyHanlinAtomicSaveBody.digest(intent.expectedVersion)))
            .applying(.atomicBodyReceipt(metadata))
        XCTAssertFalse(progress.isReadyForCommit)
        progress = try progress.applying(.bodyVerified(witness))
        XCTAssertTrue(progress.isReadyForCommit)
        XCTAssertTrue(progress.blocks.isEmpty)
    }

    private func ack(_ intent: AnyNativeMarkdownWriteIntent, version: String = "native-saved-version",
                     inserted: [String] = ["native-one"], updated: [String] = [], deleted: [String] = [],
                     unchanged: Int64 = 0) -> AnyNativeMarkdownAcknowledgement {
        .init(context: intent.context, nativeVersion: version, insertedBlockIDs: inserted,
              updatedBlockIDs: updated, deletedBlockIDs: deleted, unchangedBlocks: unchanged)
    }

    private func reference(_ object: String) throws -> AnyNativeMarkdownReference {
        try .init(accountID: "disposable-account", spaceID: "disposable-space", objectID: object)
    }

    private func plan(_ markdown: String) throws -> PinkhaHanlinSaveMessagePlan {
        let session = HanlinHostSession(conversationID: UUID(), context: .init(
            namespace: try .init(app: PinkhaHanlinEngineNamespace.any, account: "disposable-account",
                                 workspace: "disposable-space", space: "disposable-space"),
            sceneID: UUID(), generation: UUID()))
        return try .init(invocation: .init(request: .init(id: .init(validating: UUID().uuidString.lowercased()),
            logicalToolID: .init(providerInstanceID: .init(validating: "anytype.host"), localToolID: .init(validating: "save-message")),
            aliasUsed: PinkhaHanlinSaveMessagePlan.alias, descriptorRevision: .init(1), routingTableRevision: .init(1),
            arguments: .object(["title": .string("TITLE"), "markdown": .string(markdown)]), origin: .assistantModel,
            deadline: .now.addingTimeInterval(20), limits: .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
            session: session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
            writeGuarantee: .independentObjectCreation, expectedRevision: nil))
    }
}
#endif
