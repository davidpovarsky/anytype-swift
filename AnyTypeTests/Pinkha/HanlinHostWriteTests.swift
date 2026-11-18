import Foundation
import Testing
import HanlinHostContracts
import HanlinPlatformContracts
@testable import Anytype

/// New write PREPARATION/journal components only. These tests perform no native create and prove no UI.
@Suite("Hanlin host write preparation and metadata recovery", .serialized)
@MainActor
struct HanlinHostWriteTests {
    func session(space: String = "disposable-space") throws -> HanlinHostSession {
        .init(conversationID: UUID(), context: .init(
            namespace: try .init(app: "anytype", account: "disposable-account", workspace: space, space: space),
            sceneID: UUID(), generation: UUID()))
    }

    func invocation(session: HanlinHostSession, id: String = UUID().uuidString.lowercased(),
                    run: UUID = UUID(), provider: String = UUID().uuidString,
                    arguments: HanlinJSONValue = .object(["title": .string("PRIVATE-JOURNAL-TEST-TITLE")]),
                    guarantee: HanlinHostWriteGuarantee = .independentObjectCreation,
                    expectedRevision: String? = nil) throws -> HanlinHostInvocation {
        .init(request: .init(id: try .init(validating: id),
            logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"),
                                 localToolID: try .init(validating: "create-page")),
            aliasUsed: PinkhaHanlinCreatePagePlan.alias, descriptorRevision: try .init(1), routingTableRevision: .init(1),
            arguments: arguments, origin: .assistantModel, deadline: Date().addingTimeInterval(20),
            limits: try .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
            session: session, runID: run, step: 0, providerCallID: provider,
            writeGuarantee: guarantee, expectedRevision: expectedRevision)
    }

    @Test func onlyExactNonnumericTitleSchemaIsPrepared() throws {
        let session = try session()
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        #expect(plan.title == "PRIVATE-JOURNAL-TEST-TITLE")
        for invalid in [HanlinJSONValue.object([:]), .array([]), .object(["title": .null]),
                        .object(["title": .integer(1)]), .object(["title": .number(1.0)]),
                        .object(["title": .string("" )]), .object(["title": .string("   ")]),
                        .object(["title": .string(String(repeating: "א", count: 257))]),
                        .object(["title": .string("Page"), "targetSpace": .string("other")]),
                        .object(["title": .string("Page"), "body": .string("not supported")]),
                        .object(["title": .array([])])] {
            #expect(throws: PinkhaHanlinWriteError.invalidPlan) {
                try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session, arguments: invalid))
            }
        }
    }

    @Test func existingObjectCASAndReadOnlyNeverProduceCreationPlan() throws {
        let session = try session()
        for guarantee in [HanlinHostWriteGuarantee.atomicRevisionMutation, .readOnly] {
            #expect(throws: PinkhaHanlinWriteError.invalidPlan) {
                try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session, guarantee: guarantee))
            }
        }
        #expect(throws: PinkhaHanlinWriteError.invalidPlan) {
            try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session, expectedRevision: "r1"))
        }
    }

    @Test func titleIdentityUsesExactBytesAndMetadataDoesNotEncodeBusinessTitle() throws {
        let session = try session()
        let decomposed = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session,
            arguments: .object(["title": .string("e\u{301}")])))
        let composed = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session,
            arguments: .object(["title": .string("\u{e9}")])))
        #expect(decomposed.identity.argumentsDigest != composed.identity.argumentsDigest)
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        let data = try JSONEncoder().encode(plan.identity)
        #expect(!String(decoding: data, as: UTF8.self).contains(plan.title))
        #expect(plan.identity.session == session)
    }

    #if os(iOS) && DEBUG
    func directory() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("hanlin-write-tests-" + UUID().uuidString,
                                                                               isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: false)
        return url
    }

    func scopeDirectory(_ parent: URL, namespace: HanlinConversationNamespace) throws -> URL {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return parent.appendingPathComponent("HanlinHostMetadataV1", isDirectory: true)
            .appendingPathComponent(PinkhaHanlinCreatePagePlan.digest(try encoder.encode(namespace)), isDirectory: true)
    }

    @Test func protectionReadbackRejectsWrongPresentValues() {
        let expected = FileProtectionType.completeUntilFirstUserAuthentication
        #expect(PinkhaHanlinMetadataProtection.acceptsReadback([.protectionKey: expected]))
        #expect(PinkhaHanlinMetadataProtection.acceptsReadback([.protectionKey: expected.rawValue]))
        let invalid: [Any] = [FileProtectionType.none, FileProtectionType.complete,
                              FileProtectionType.completeUnlessOpen, "", "unknown", NSNumber(value: 0), NSNull()]
        for value in invalid {
            #expect(!PinkhaHanlinMetadataProtection.acceptsReadback([.protectionKey: value]))
        }
        #if targetEnvironment(simulator)
        // This is an explicit metadata-unavailable platform case, not evidence
        // that a Simulator provides physical-device Data Protection.
        #expect(PinkhaHanlinMetadataProtection.acceptsReadback([:]))
        #else
        #expect(!PinkhaHanlinMetadataProtection.acceptsReadback([:]))
        #endif
    }

    @Test func journalReopenRejectsChangedDirectoryAndRecordModes() async throws {
        for target in ["root", "scope", "namespace", "reservation"] {
            let parent = try directory()
            defer { try? FileManager.default.removeItem(at: parent) }
            let session = try session()
            let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
            var journal: PinkhaHanlinWriteJournal? = try await PinkhaHanlinWriteJournal.openInTestDirectory(
                parent, namespace: session.context.namespace)
            try await journal?.reserve(plan.identity)
            journal = nil
            let scope = try scopeDirectory(parent, namespace: session.context.namespace)
            let marker = scope.appendingPathComponent("namespace.json")
            let reservation = scope.appendingPathComponent(plan.identity.key + ".reserved")
            let markerBytes = try Data(contentsOf: marker)
            let reservationBytes = try Data(contentsOf: reservation)
            let targets = ["root": scope.deletingLastPathComponent(), "scope": scope,
                           "namespace": marker, "reservation": reservation]
            let changed = try #require(targets[target])
            let isDirectory = target == "root" || target == "scope"
            let wrongMode = isDirectory ? 0o755 : 0o644
            try FileManager.default.setAttributes([.posixPermissions: wrongMode], ofItemAtPath: changed.path)
            do {
                _ = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
                Issue.record("Changed journal ownership mode was accepted")
            } catch PinkhaHanlinWriteError.unavailable {
                #expect(isDirectory)
            } catch PinkhaHanlinWriteError.corruptJournal {
                #expect(!isDirectory)
            }
            let after = try FileManager.default.attributesOfItem(atPath: changed.path)
            #expect((after[.posixPermissions] as? NSNumber)?.intValue == wrongMode)
            #expect(try Data(contentsOf: marker) == markerBytes)
            #expect(try Data(contentsOf: reservation) == reservationBytes)
        }
    }

    @Test func journalReopenRejectsExistingFilesAndSymlinksWithoutMutation() async throws {
        for target in ["root", "scope"] {
            for kind in ["file", "symlink"] {
                let parent = try directory()
                defer { try? FileManager.default.removeItem(at: parent) }
                let namespace = try session().context.namespace
                let scope = try scopeDirectory(parent, namespace: namespace)
                let root = scope.deletingLastPathComponent()
                let attributes: [FileAttributeKey: Any] = [
                    .posixPermissions: 0o700,
                    .protectionKey: FileProtectionType.completeUntilFirstUserAuthentication
                ]
                if target == "scope" {
                    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
                        attributes: attributes)
                }
                let foreign = parent.appendingPathComponent("unrelated-owned-directory", isDirectory: true)
                try FileManager.default.createDirectory(at: foreign, withIntermediateDirectories: false,
                    attributes: attributes)
                let sentinel = Data("preserve unrelated owned bytes".utf8)
                let marker = foreign.appendingPathComponent("preserve.txt")
                try sentinel.write(to: marker)
                let blocked = target == "root"
                    ? parent.appendingPathComponent("HanlinHostMetadataV1", isDirectory: false)
                    : root.appendingPathComponent(scope.lastPathComponent, isDirectory: false)
                if kind == "file" {
                    try sentinel.write(to: blocked)
                    try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: blocked.path)
                } else {
                    try FileManager.default.createSymbolicLink(at: blocked, withDestinationURL: foreign)
                }
                do {
                    _ = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: namespace)
                    Issue.record("An existing file or symlink was accepted as a metadata directory")
                } catch PinkhaHanlinWriteError.unavailable {}
                if kind == "file" {
                    #expect(try Data(contentsOf: blocked) == sentinel)
                    let mode = try FileManager.default.attributesOfItem(atPath: blocked.path)[.posixPermissions]
                    #expect((mode as? NSNumber)?.intValue == 0o600)
                } else {
                    #expect(try blocked.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink == true)
                    #expect(try FileManager.default.destinationOfSymbolicLink(atPath: blocked.path) == foreign.path)
                }
                #expect(try Data(contentsOf: marker) == sentinel)
                #expect(try FileManager.default.contentsOfDirectory(atPath: foreign.path) == ["preserve.txt"])
                let foreignMode = try FileManager.default.attributesOfItem(atPath: foreign.path)[.posixPermissions]
                #expect((foreignMode as? NSNumber)?.intValue == 0o700)
            }
        }
    }

    @Test func reservationBlocksAllNewWritesUntilOriginalOutcomeIsKnown() async throws {
        let parent = try directory()
        defer { try? FileManager.default.removeItem(at: parent) } // Only this test's exact owned directory.
        let session = try session()
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        let first = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        let second = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        try await journal.reserve(first.identity)
        do { try await journal.reserve(second.identity); Issue.record("unresolved creation bypassed") }
        catch PinkhaHanlinWriteError.unresolved {}
        try await journal.record(.notDispatched, identity: first.identity)
        try await journal.reserve(second.identity)
        #expect(try await journal.receipt(for: second.identity)?.effect == .reserved)
    }

    @Test func replayConflictAndProviderCallRemintAreRejected() async throws {
        let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
        let session = try session()
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        let call = try invocation(session: session, provider: "opaque/Call:A")
        let first = try PinkhaHanlinCreatePagePlan(invocation: call)
        try await journal.reserve(first.identity)
        try await journal.record(.notDispatched, identity: first.identity)
        do { try await journal.reserve(first.identity); Issue.record("duplicate reserved") }
        catch PinkhaHanlinWriteError.duplicate {}
        let reminted = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session,
            run: call.runID, provider: call.providerCallID))
        do { try await journal.reserve(reminted.identity); Issue.record("provider identity reminted") }
        catch PinkhaHanlinWriteError.conflict {}
        let changed = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session, id: call.request.id.rawValue,
            arguments: .object(["title": .string("changed")])) )
        do { try await journal.reserve(changed.identity); Issue.record("changed arguments reused ID") }
        catch PinkhaHanlinWriteError.conflict {}
    }

    @Test func uncertainMayRefineToCommittedButCannotBeDowngradedOrRetargeted() async throws {
        let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
        let session = try session()
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        try await journal.reserve(plan.identity)
        try await journal.record(.uncertain, identity: plan.identity)
        try await journal.record(.committed, identity: plan.identity, createdObjectReference: "native-created-id")
        let lateCancel = try await journal.record(.uncertain, identity: plan.identity)
        #expect(lateCancel.effect == .committed)
        #expect(lateCancel.identity.session == session)
        do {
            _ = try await journal.record(.committed, identity: plan.identity, createdObjectReference: "other-id")
            Issue.record("committed target changed")
        } catch PinkhaHanlinWriteError.conflict {}
    }

    @Test func pendingReservationSurvivesOwnerReopenAndNeverAutoRetries() async throws {
        let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
        let session = try session()
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        var journal: PinkhaHanlinWriteJournal? = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent,
            namespace: session.context.namespace)
        try await journal?.reserve(plan.identity)
        journal = nil
        let reopened = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        #expect(try await reopened.receipt(for: plan.identity)?.effect == .reserved)
        let fresh = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        do { try await reopened.reserve(fresh.identity); Issue.record("crash reservation discarded") }
        catch PinkhaHanlinWriteError.unresolved {}
    }

    @Test func partialAndUnknownRecordsFailClosedWithoutDeletion() async throws {
        for bytes in [Data(), Data("{partial".utf8)] {
            let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
            let session = try session()
            var journal: PinkhaHanlinWriteJournal? = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent,
                namespace: session.context.namespace)
            let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
            try await journal?.reserve(plan.identity)
            journal = nil
            let unknown = try scopeDirectory(parent, namespace: session.context.namespace).appendingPathComponent("unknown-partial")
            try bytes.write(to: unknown, options: .completeFileProtectionUntilFirstUserAuthentication)
            do {
                _ = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
                Issue.record("partial journal accepted")
            } catch {}
            #expect(try Data(contentsOf: unknown) == bytes)
        }
    }

    @Test func originalScopeAndExclusiveOwnerCannotBeReplacedByAnotherSceneOrSpace() async throws {
        let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
        let session = try session()
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        do {
            _ = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
            Issue.record("two writers acquired one metadata scope")
        } catch {}
        let foreign = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: self.session(space: "other")))
        do { try await journal.reserve(foreign.identity); Issue.record("retargeted namespace") }
        catch PinkhaHanlinWriteError.invalidPlan {}
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        try await journal.reserve(plan.identity)
        let path = try scopeDirectory(parent, namespace: session.context.namespace)
            .appendingPathComponent(plan.identity.key + ".reserved")
        let bytes = try Data(contentsOf: path)
        #expect(!String(decoding: bytes, as: UTF8.self).contains(plan.title))
        let attributes = try FileManager.default.attributesOfItem(atPath: path.path)
        let protection = (attributes[.protectionKey] as? FileProtectionType)?.rawValue
            ?? (attributes[.protectionKey] as? String)
        #expect((attributes[.posixPermissions] as? NSNumber)?.intValue == 0o600)
        #if targetEnvironment(simulator)
        // Missing protection metadata is the measured Simulator limitation;
        // an unexpected present value must still fail, with no device claim.
        #expect(attributes[.protectionKey] == nil
            || protection == FileProtectionType.completeUntilFirstUserAuthentication.rawValue)
        #else
        #expect(protection == FileProtectionType.completeUntilFirstUserAuthentication.rawValue)
        #endif
    }

    @Test func failedExclusiveAppendNeverAcknowledgesReservationAndPoisonsOwnerWithoutCleanup() async throws {
        let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
        let session = try session()
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        let occupied = try scopeDirectory(parent, namespace: session.context.namespace)
            .appendingPathComponent(plan.identity.key + ".reserved")
        let original = Data("incomplete original record".utf8)
        try original.write(to: occupied, options: .completeFileProtectionUntilFirstUserAuthentication)
        do { try await journal.reserve(plan.identity); Issue.record("failed append acknowledged") }
        catch PinkhaHanlinWriteError.unavailable {}
        #expect(try await journal.receipt(for: plan.identity) == nil)
        let fresh = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: session))
        do { try await journal.reserve(fresh.identity); Issue.record("poisoned owner resumed writing") }
        catch PinkhaHanlinWriteError.unavailable {}
        #expect(try Data(contentsOf: occupied) == original)
    }
    @Test func explicitRemovalErasesOnlyOriginalAccountAndLateCallbackCannotRecreateIt() async throws {
        let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
        let original = try session()
        let other = HanlinHostSession(conversationID: UUID(), context: .init(
            namespace: try .init(app: "anytype", account: "different-disposable-account", workspace: "other", space: "other"),
            sceneID: UUID(), generation: UUID()))
        let first = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: original.context.namespace)
        let second = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: other.context.namespace)
        let firstPlan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: original))
        let secondPlan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: other))
        try await first.reserve(firstPlan.identity)
        try await first.record(.uncertain, identity: firstPlan.identity)
        try await second.reserve(secondPlan.identity)
        await first.revokeForDataRemoval()
        try PinkhaHanlinWriteJournal.removeAccountDataInTestDirectory(original.context.namespace.account, parent: parent)
        let erased = try scopeDirectory(parent, namespace: original.context.namespace)
        let preserved = try scopeDirectory(parent, namespace: other.context.namespace)
        #expect(!FileManager.default.fileExists(atPath: erased.path))
        #expect(FileManager.default.fileExists(atPath: preserved.path))
        do {
            try await first.record(.committed, identity: firstPlan.identity, createdObjectReference: "late-native-id")
            Issue.record("A late callback recreated explicitly erased metadata")
        } catch PinkhaHanlinWriteError.unavailable {}
        #expect(!FileManager.default.fileExists(atPath: erased.path))
        #expect(try await second.receipt(for: secondPlan.identity)?.effect == .reserved)
    }

    @Test func removalPreservesMetadataWhoseAccountOwnershipCannotBeVerified() async throws {
        let parent = try directory(); defer { try? FileManager.default.removeItem(at: parent) }
        let original = try session()
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: original.context.namespace)
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation(session: original))
        try await journal.reserve(plan.identity)
        await journal.revokeForDataRemoval()
        let scope = try scopeDirectory(parent, namespace: original.context.namespace)
        let marker = scope.appendingPathComponent("namespace.json")
        try Data("invalid ownership".utf8).write(to: marker)
        do {
            try PinkhaHanlinWriteJournal.removeAccountDataInTestDirectory(original.context.namespace.account, parent: parent)
            Issue.record("Unknown ownership was erased")
        } catch {}
        #expect(FileManager.default.fileExists(atPath: scope.appendingPathComponent(plan.identity.key + ".reserved").path))
    }
    #endif
}
