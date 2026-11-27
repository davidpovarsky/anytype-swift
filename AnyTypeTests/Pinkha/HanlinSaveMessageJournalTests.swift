import Foundation
import Testing
import HanlinHostContracts
import HanlinPlatformContracts
@testable import PinkhaHanlinCore

/// Actual original protected-file owner tests on an Apple host. These fixtures
/// perform no native document write and prove neither semantic conversion nor UI.
#if os(iOS) && DEBUG
@Suite("Hanlin original save-message journal", .serialized)
@MainActor
struct HanlinSaveMessageJournalTests {
    @Test(arguments: ["anytype", "anytype-any"])
    func originalReservationAndNamespaceAreRequired(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        let initial = try fixture.initial()
        await #expect(throws: PinkhaHanlinWriteError.invalidPlan) { try await journal.reserveSaveMessage(initial) }
        try await journal.reserve(initial.manifest.identity)
        try await journal.reserveSaveMessage(initial)
        await #expect(throws: PinkhaHanlinWriteError.duplicate) { try await journal.reserveSaveMessage(initial) }
        let other = try Fixture(app: app, account: "other-account")
        defer { other.removeFiles() }
        await #expect(throws: PinkhaHanlinWriteError.invalidPlan) {
            _ = try await journal.saveMessageProgress(for: other.initial().manifest.identity)
        }
        #expect(try await journal.saveMessageProgress(for: initial.manifest.identity) == initial)
    }

    @Test(arguments: ["anytype", "anytype-any"])
    func rootAndIndividualBlocksCannotPrematurelyCommitBody(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        var state = try fixture.initial()
        let identity = state.manifest.identity
        try await journal.reserve(identity)
        let reservation = try Data(contentsOf: fixture.scope.appendingPathComponent(identity.key + ".reserved"))
        try await journal.reserveSaveMessage(state)
        state = try await journal.advanceSaveMessage(state, event: .rootDispatched)
        try await journal.recordKnownIncompleteObject("root-original", identity: identity)
        state = try await journal.advanceSaveMessage(state, event: .rootKnown(reference: "root-original"))
        state = try await journal.advanceSaveMessage(state, event: .rootVerified(reference: "root-original",
            readbackSHA256: state.manifest.expectedRootReadbackSHA256))
        await #expect(throws: PinkhaHanlinWriteError.unresolved) {
            _ = try await journal.record(.committed, identity: identity, createdObjectReference: "root-original")
        }
        state = try await journal.advanceSaveMessage(state, event: .blockDispatched(index: 0))
        state = try await journal.advanceSaveMessage(state, event: .blockVerified(index: 0, reference: "block-original",
            readbackSHA256: state.manifest.blockSHA256[0]))
        await #expect(throws: PinkhaHanlinWriteError.unresolved) {
            _ = try await journal.record(.committed, identity: identity, createdObjectReference: "root-original")
        }
        state = try await journal.advanceSaveMessage(state, event: .bodyVerified(try fixture.readback(state)))
        #expect(state.isReadyForCommit)
        let final = try await journal.record(.committed, identity: identity, createdObjectReference: "root-original")
        #expect(final.effect == .committed)
        #expect(try await journal.record(.uncertain, identity: identity) == final)
        #expect(try Data(contentsOf: fixture.scope.appendingPathComponent(identity.key + ".reserved")) == reservation)
        for url in try FileManager.default.contentsOfDirectory(at: fixture.scope, includingPropertiesForKeys: nil) {
            let bytes = try Data(contentsOf: url)
            #expect(!String(decoding: bytes, as: UTF8.self).contains("PRIVATE-SAVE-BODY"))
            #expect(!String(decoding: bytes, as: UTF8.self).contains("PRIVATE-SAVE-TITLE"))
        }
    }

    @Test(arguments: ["anytype", "anytype-any"])
    func closeRaceRetainsLateOriginalReceiptWithoutReopeningDispatch(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        var journal: PinkhaHanlinWriteJournal? = try await fixture.open()
        var state = try fixture.initial()
        let identity = state.manifest.identity
        try await journal?.reserve(identity)
        try await journal?.reserveSaveMessage(state)
        let persistedProgress1 = try await journal?.advanceSaveMessage(state, event: .rootDispatched)
        state = try #require(persistedProgress1)
        let beforeClose = state
        try await journal?.closeSaveMessageDispatch(for: identity)
        await #expect(throws: PinkhaHanlinWriteError.conflict) {
            _ = try await journal?.advanceSaveMessage(beforeClose, event: .rootKnown(reference: "root-original"))
        }
        let persistedProgress2 = try await journal?.saveMessageProgress(for: identity)
        state = try #require(persistedProgress2)
        #expect(state == (try beforeClose.applying(.closeDispatch)))
        let persistedProgress3 = try await journal?.advanceSaveMessage(state, event: .rootKnown(reference: "root-original"))
        state = try #require(persistedProgress3)
        _ = try await journal?.record(.uncertain, identity: identity)
        journal = nil
        let reopened = try await fixture.open()
        #expect(try await reopened.saveMessageProgress(for: identity) == state)
        #expect(try await reopened.knownCreatedObjectReference(for: identity) == "root-original")
        state = try await reopened.advanceSaveMessage(state, event: .rootVerified(reference: "root-original",
            readbackSHA256: state.manifest.expectedRootReadbackSHA256))
        await #expect(throws: PinkhaHanlinSaveMessageError.invalidTransition) {
            _ = try await reopened.advanceSaveMessage(state, event: .blockDispatched(index: 0))
        }
        await #expect(throws: PinkhaHanlinWriteError.unresolved) {
            _ = try await reopened.record(.committed, identity: identity, createdObjectReference: "root-original")
        }
    }

    @Test func fullBodyReceiptAfterStopMayRefineOnlyTheOriginalJournal() async throws {
        let fixture = try Fixture()
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        var state = try fixture.initial()
        let identity = state.manifest.identity
        try await journal.reserve(identity)
        try await journal.reserveSaveMessage(state)
        state = try await journal.advanceSaveMessage(state, event: .rootDispatched)
        state = try await journal.advanceSaveMessage(state, event: .rootVerified(reference: "root-original",
            readbackSHA256: state.manifest.expectedRootReadbackSHA256))
        state = try await journal.advanceSaveMessage(state, event: .blockDispatched(index: 0))
        try await journal.closeSaveMessageDispatch(for: identity)
        let persistedProgress4 = try await journal.saveMessageProgress(for: identity)
        state = try #require(persistedProgress4)
        _ = try await journal.record(.uncertain, identity: identity)
        state = try await journal.advanceSaveMessage(state, event: .blockVerified(index: 0, reference: "block-original",
            readbackSHA256: state.manifest.blockSHA256[0]))
        state = try await journal.advanceSaveMessage(state, event: .bodyVerified(try fixture.readback(state)))
        let final = try await journal.record(.committed, identity: identity, createdObjectReference: "root-original")
        #expect(final.effect == .committed)
        try await journal.closeSaveMessageDispatch(for: identity)
        #expect(try await journal.saveMessageProgress(for: identity) == state)
    }

    @Test func missingOrTamperedEventFailsReopenWithoutRepairingEvidence() async throws {
        for corruption in ["missing", "sequence", "digest"] {
            let fixture = try Fixture()
            defer { fixture.removeFiles() }
            var journal: PinkhaHanlinWriteJournal? = try await fixture.open()
            var state = try fixture.initial()
            try await journal?.reserve(state.manifest.identity)
            try await journal?.reserveSaveMessage(state)
            let persistedProgress5 = try await journal?.advanceSaveMessage(state, event: .rootDispatched)
            state = try #require(persistedProgress5)
            let persistedProgress6 = try await journal?.advanceSaveMessage(state, event: .rootKnown(reference: "root-original"))
            state = try #require(persistedProgress6)
            journal = nil
            let first = fixture.record(sequence: 1)
            let second = fixture.record(sequence: 2)
            if corruption == "missing" {
                try FileManager.default.removeItem(at: first)
            } else {
                let original = try Data(contentsOf: second)
                var json = try #require(JSONSerialization.jsonObject(with: original) as? [String: Any])
                if corruption == "sequence" { json["sequence"] = 3 }
                else { json["previousSHA256"] = String(repeating: "0", count: 64) }
                try fixture.write(JSONSerialization.data(withJSONObject: json, options: [.sortedKeys]), to: second)
            }
            let retained = try fixture.inventory()
            await #expect(throws: PinkhaHanlinWriteError.corruptJournal) { _ = try await fixture.open() }
            #expect(try fixture.inventory() == retained)
        }
    }

    @Test func forgedRootOnlyCommittedFileCannotBypassAggregateOnReopen() async throws {
        let fixture = try Fixture()
        defer { fixture.removeFiles() }
        var journal: PinkhaHanlinWriteJournal? = try await fixture.open()
        var state = try fixture.initial()
        try await journal?.reserve(state.manifest.identity)
        try await journal?.reserveSaveMessage(state)
        let persistedProgress7 = try await journal?.advanceSaveMessage(state, event: .rootDispatched)
        state = try #require(persistedProgress7)
        let persistedProgress8 = try await journal?.advanceSaveMessage(state, event: .rootVerified(reference: "root-original",
            readbackSHA256: state.manifest.expectedRootReadbackSHA256))
        state = try #require(persistedProgress8)
        journal = nil
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let forged = PinkhaHanlinWriteJournal.Entry(version: 1, identity: state.manifest.identity,
            effect: .committed, createdObjectReference: "root-original")
        try fixture.write(encoder.encode(forged), to: fixture.scope.appendingPathComponent(state.manifest.identity.key + ".committed"))
        let retained = try fixture.inventory()
        await #expect(throws: PinkhaHanlinWriteError.corruptJournal) { _ = try await fixture.open() }
        #expect(try fixture.inventory() == retained)
    }

    @Test func exactKnownRootIdentityCannotChangeAcrossSidecars() async throws {
        let fixture = try Fixture()
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        var state = try fixture.initial()
        try await journal.reserve(state.manifest.identity)
        try await journal.reserveSaveMessage(state)
        state = try await journal.advanceSaveMessage(state, event: .rootDispatched)
        try await journal.recordKnownIncompleteObject("root-original", identity: state.manifest.identity)
        await #expect(throws: PinkhaHanlinWriteError.conflict) {
            _ = try await journal.advanceSaveMessage(state, event: .rootKnown(reference: "root-other"))
        }
        state = try await journal.advanceSaveMessage(state, event: .rootKnown(reference: "root-original"))
        await #expect(throws: PinkhaHanlinWriteError.conflict) {
            try await journal.recordKnownIncompleteObject("root-other", identity: state.manifest.identity)
        }
    }

    @Test(arguments: ["anytype", "anytype-any"])
    func accountRemovalRevokesProgressOwnerBeforeLateWrites(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        let initial = try fixture.initial()
        try await journal.reserve(initial.manifest.identity)
        try await journal.reserveSaveMessage(initial)
        await journal.revokeForDataRemoval()
        try PinkhaHanlinWriteJournal.removeAccountDataInTestDirectory(fixture.session.context.namespace.account,
            parent: fixture.parent, app: app)
        #expect(!FileManager.default.fileExists(atPath: fixture.scope.path))
        await #expect(throws: PinkhaHanlinWriteError.unavailable) {
            _ = try await journal.saveMessageProgress(for: initial.manifest.identity)
        }
        await #expect(throws: PinkhaHanlinWriteError.unavailable) {
            _ = try await journal.advanceSaveMessage(initial, event: .rootDispatched)
        }
        #expect(!FileManager.default.fileExists(atPath: fixture.scope.path))
    }

    @Test func maximumAtomicACKAndBodySurviveOriginalProtectedReopenAfterStop() async throws {
        let fixture = try Fixture(app: "anytype-any")
        defer { fixture.removeFiles() }
        let plan = try PinkhaHanlinSaveMessagePlan(invocation: fixture.invocation)
        let original = try fixture.initial()
        let manifest = try PinkhaHanlinSaveMessageManifest(plan: plan,
            bodyPlanSHA256: original.manifest.bodyPlanSHA256,
            expectedRootReadbackSHA256: original.manifest.expectedRootReadbackSHA256,
            expectedBodyReadbackSHA256: original.manifest.expectedBodyReadbackSHA256,
            blockSHA256: (0..<64).map { PinkhaHanlinCreatePagePlan.digest(Data("semantic-block-\($0)".utf8)) },
            bodyMode: .conditionalMarkdown)
        let root = "root-" + String(repeating: "\\", count: 251)
        let references = (0..<64).map { String(format: "%03d", $0) + String(repeating: "\"", count: 253) }
        #expect(root.utf8.count == 256 && references.allSatisfy { $0.utf8.count == 256 })
        let request = PinkhaHanlinCreatePagePlan.digest(Data("actual-request-fixture".utf8))
        let version = PinkhaHanlinCreatePagePlan.digest(Data("actual-version-fixture".utf8))
        let acknowledgement = try PinkhaHanlinSaveMessageAtomicAcknowledgement(requestSHA256: request,
            savedVersionSHA256: version, insertedReferences: Array(references.reversed()),
            updatedReferences: [], deletedReferences: [], unchangedBlocks: 0)
        var journal: PinkhaHanlinWriteJournal? = try await fixture.open()
        var state = try PinkhaHanlinSaveMessageProgress(manifest: manifest)
        try await journal?.reserve(plan.identity)
        let reservedURL = fixture.scope.appendingPathComponent(plan.identity.key + ".reserved")
        let reservation = try Data(contentsOf: reservedURL)
        try await journal?.reserveSaveMessage(state)
        let dispatchedRoot = try await journal?.advanceSaveMessage(state, event: .rootDispatched)
        state = try #require(dispatchedRoot)
        let knownRoot = try await journal?.advanceSaveMessage(state, event: .rootKnown(reference: root))
        state = try #require(knownRoot)
        let verifiedRoot = try await journal?.advanceSaveMessage(state, event: .rootVerified(reference: root,
            readbackSHA256: manifest.expectedRootReadbackSHA256))
        state = try #require(verifiedRoot)
        let dispatchedBody = try await journal?.advanceSaveMessage(state,
            event: .atomicBodyDispatched(requestSHA256: request, expectedVersionSHA256: version))
        state = try #require(dispatchedBody)
        try await journal?.closeSaveMessageDispatch(for: plan.identity)
        let closed = try await journal?.saveMessageProgress(for: plan.identity)
        state = try #require(closed)
        _ = try await journal?.record(.uncertain, identity: plan.identity)
        let digestOnly = try await journal?.advanceSaveMessage(state, event: .atomicBodyAcknowledged(
            requestSHA256: request, savedVersionSHA256: version, nativeReceiptSHA256: acknowledgement.nativeReceiptSHA256))
        state = try #require(digestOnly)
        let readback = PinkhaHanlinSaveMessageBodyReadback(manifestSHA256: try manifest.canonicalSHA256(),
            objectReference: root, blockReferences: references, nativeReadbackSHA256: manifest.expectedBodyReadbackSHA256,
            nativeVersionSHA256: version, nativeMarkdownSHA256: PinkhaHanlinCreatePagePlan.digest(Data("normalized-output".utf8)),
            nativeMarkdownUTF8Bytes: "normalized-output".utf8.count)
        await #expect(throws: PinkhaHanlinSaveMessageError.invalidProgress) {
            _ = try await journal?.advanceSaveMessage(state, event: .bodyVerified(readback))
        }
        let acknowledged = try await journal?.advanceSaveMessage(state, event: .atomicBodyReceipt(acknowledgement))
        state = try #require(acknowledged)
        let acknowledgementSequence = state.sequence
        let verifiedBody = try await journal?.advanceSaveMessage(state, event: .bodyVerified(readback))
        state = try #require(verifiedBody)
        let bodySequence = state.sequence
        #expect(state.dispatchClosed && state.isReadyForCommit)
        #expect(try state.canonicalBytes().count <= PinkhaHanlinSaveMessageProgress.maximumEncodedBytes)
        _ = try await journal?.record(.committed, identity: plan.identity, createdObjectReference: root)
        journal = nil
        for sequence in [acknowledgementSequence, bodySequence] {
            let bytes = try Data(contentsOf: fixture.record(sequence: sequence))
            #expect(bytes.count > 32_768 && bytes.count <= 65_536)
        }
        let reopened = try await fixture.open()
        let retained = try await reopened.saveMessageProgress(for: plan.identity)
        #expect(retained == state)
        #expect(retained?.atomicBody?.acknowledgement == acknowledgement)
        #expect(retained?.bodyReadback?.blockReferences == references)
        #expect(try await reopened.knownCreatedObjectReference(for: plan.identity) == root)
        #expect(try Data(contentsOf: reservedURL) == reservation)
    }

    private struct Fixture {
        let parent: URL
        let session: HanlinHostSession
        let invocation: HanlinHostInvocation
        var scope: URL {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let bytes = try! encoder.encode(session.context.namespace)
            return parent.appendingPathComponent("HanlinHostMetadataV1", isDirectory: true)
                .appendingPathComponent(PinkhaHanlinCreatePagePlan.digest(bytes), isDirectory: true)
        }
        init(app: String = "anytype", account: String = "disposable-account") throws {
            parent = FileManager.default.temporaryDirectory.appendingPathComponent("hanlin-save-journal-" + UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
            session = .init(conversationID: UUID(), context: .init(namespace: try .init(app: app, account: account,
                workspace: "disposable-space", space: "disposable-space"), sceneID: UUID(), generation: UUID()))
            invocation = .init(request: .init(id: try .init(validating: UUID().uuidString.lowercased()),
                logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"), localToolID: try .init(validating: "save-message")),
                aliasUsed: PinkhaHanlinSaveMessagePlan.alias, descriptorRevision: try .init(1), routingTableRevision: .init(1),
                arguments: .object(["title": .string("PRIVATE-SAVE-TITLE"), "markdown": .string("PRIVATE-SAVE-BODY")]),
                origin: .assistantModel, deadline: Date().addingTimeInterval(20),
                limits: try .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
                session: session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
                writeGuarantee: .independentObjectCreation, expectedRevision: nil)
        }
        func initial() throws -> PinkhaHanlinSaveMessageProgress {
            let plan = try PinkhaHanlinSaveMessagePlan(invocation: invocation)
            func digest(_ text: String) -> String { PinkhaHanlinCreatePagePlan.digest(Data(text.utf8)) }
            return try .init(manifest: .init(plan: plan, bodyPlanSHA256: digest("complete-plan"),
                expectedRootReadbackSHA256: digest("root-title-kind"), expectedBodyReadbackSHA256: digest("whole-native-body"),
                blockSHA256: [digest("block-style-order-content")]))
        }
        func readback(_ state: PinkhaHanlinSaveMessageProgress) throws -> PinkhaHanlinSaveMessageBodyReadback {
            .init(manifestSHA256: try state.manifest.canonicalSHA256(), objectReference: "root-original",
                blockReferences: ["block-original"], nativeReadbackSHA256: state.manifest.expectedBodyReadbackSHA256)
        }
        func open() async throws -> PinkhaHanlinWriteJournal {
            try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        }
        func record(sequence: Int) -> URL {
            let key = PinkhaHanlinCreatePagePlan.digest(Data(invocation.request.id.rawValue.utf8))
            return scope.appendingPathComponent(key + ".save-message-v1." + String(format: "%03d", sequence))
        }
        func write(_ bytes: Data, to url: URL) throws {
            try bytes.write(to: url)
            try FileManager.default.setAttributes([.posixPermissions: 0o600,
                .protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: url.path)
        }
        func inventory() throws -> [String: Data] {
            var result: [String: Data] = [:]
            for url in try FileManager.default.contentsOfDirectory(at: scope, includingPropertiesForKeys: nil) {
                result[url.lastPathComponent] = try Data(contentsOf: url)
            }
            return result
        }
        func removeFiles() { try? FileManager.default.removeItem(at: parent) }
    }
}
#endif
