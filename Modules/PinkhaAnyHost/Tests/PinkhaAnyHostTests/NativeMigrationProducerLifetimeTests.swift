import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Four component controls of the existing registered producer/source-owner
/// lifetime. The private bundle and session grant below are synthetic.
/// These controls never manufacture AnyHeartNativeMigrationCompletion, invoke
/// execute/produce, contact a native runtime, or qualify destination authority.
final class NativeMigrationProducerLifetimeTests: XCTestCase {
    func testBusyRefusalKeepsTheRegisteredOperationAndReleasesItsSlotAtTerminal() async throws {
        try await ProducerLifetimeControl.withFixture { fixture in
            let release = fixture.tasks.gate()
            let first = try fixture.tasks.start {
                try await fixture.producer.withOwnedOperation { _ in
                    fixture.probe.record("first.entered")
                    await release.wait()
                    fixture.probe.record("first.returning")
                    return 11
                }
            }
            try await ProducerLifetimeControl.until("first operation entered") { fixture.probe.has("first.entered") }
            let refused = try fixture.tasks.start {
                try await fixture.producer.withOwnedOperation { _ in
                    fixture.probe.record("busy.body.must-not-run")
                    return 22
                }
            }
            let refusal = try await ProducerLifetimeControl.failure(refused, "busy refusal")
            XCTAssertEqual(refusal as? AnyHeartNativeMigrationProducerError, .busy)
            XCTAssertFalse(fixture.probe.has("busy.body.must-not-run"))
            XCTAssertFalse(first.finished.isOpen)
            XCTAssertEqual(fixture.probe.snapshot().closeTokens.count, 0)

            release.open()
            let firstValue = try await ProducerLifetimeControl.value(first, "first operation terminal")
            XCTAssertEqual(firstValue, 11)
            let after = try fixture.tasks.start {
                try await fixture.producer.withOwnedOperation { _ in 33 }
            }
            let nextValue = try await ProducerLifetimeControl.value(after, "slot reused after terminal")
            XCTAssertEqual(nextValue, 33)
            let state = await fixture.source.state
            XCTAssertEqual(state, .ready)
            XCTAssertEqual(fixture.probe.snapshot().creates, 1)
        }
    }

    func testExternalInvalidationCancelsAndWaitsForTheLateOuterDestinationResult() async throws {
        try await ProducerLifetimeControl.withFixture { fixture in
            let release = fixture.tasks.gate()
            let operation = try fixture.tasks.start {
                try await fixture.producer.withOwnedOperation { _ in
                    await withTaskCancellationHandler {
                        fixture.probe.record("outer.entered")
                        await release.wait()
                        fixture.probe.record("outer.returning")
                        return 41
                    } onCancel: {
                        fixture.probe.record("outer.cancelled")
                    }
                }
            }
            try await ProducerLifetimeControl.until("outer operation entered") { fixture.probe.has("outer.entered") }
            let invalidation = try fixture.tasks.start {
                try await fixture.producer.invalidate(reason: .engineChanged)
                fixture.probe.record("outer.invalidation.returned")
            }
            try await ProducerLifetimeControl.until("cancellation and native close") {
                fixture.probe.has("outer.cancelled") && fixture.probe.has("native.close.succeeded")
            }
            let refused = try fixture.tasks.start {
                try await fixture.producer.withOwnedOperation { _ in
                    fixture.probe.record("inactive.body.must-not-run")
                    return 42
                }
            }
            let refusal = try await ProducerLifetimeControl.failure(refused, "inactive during late completion")
            XCTAssertEqual(refusal as? AnyHeartNativeMigrationProducerError, .inactive)
            XCTAssertFalse(fixture.probe.has("inactive.body.must-not-run"))
            XCTAssertFalse(operation.finished.isOpen)
            XCTAssertFalse(invalidation.finished.isOpen)

            release.open()
            let terminal = try await ProducerLifetimeControl.failure(operation, "late result refused")
            XCTAssertEqual(terminal as? AnyHeartNativeMigrationProducerError, .inactive)
            try await ProducerLifetimeControl.value(invalidation, "external invalidation drained")
            let events = fixture.probe.snapshot().events
            XCTAssertLessThan(try XCTUnwrap(events.firstIndex(of: "outer.cancelled")),
                              try XCTUnwrap(events.firstIndex(of: "outer.returning")))
            XCTAssertLessThan(try XCTUnwrap(events.firstIndex(of: "native.close.succeeded")),
                              try XCTUnwrap(events.firstIndex(of: "outer.returning")))
            XCTAssertLessThan(try XCTUnwrap(events.firstIndex(of: "outer.returning")),
                              try XCTUnwrap(events.firstIndex(of: "outer.invalidation.returned")))
            let state = await fixture.source.state
            XCTAssertEqual(state, .idle)
        }
    }

    func testNativeCloseFailureStillJoinsTheOuterResultAndRetriesTheSameOwnedGrant() async throws {
        try await ProducerLifetimeControl.withFixture { fixture in
            fixture.probe.failNextClose()
            let release = fixture.tasks.gate()
            let operation = try fixture.tasks.start {
                try await fixture.producer.withOwnedOperation { _ in
                    await withTaskCancellationHandler {
                        fixture.probe.record("close-failure.outer.entered")
                        await release.wait()
                        fixture.probe.record("close-failure.outer.returning")
                        return 51
                    } onCancel: {
                        fixture.probe.record("close-failure.outer.cancelled")
                    }
                }
            }
            try await ProducerLifetimeControl.until("close-failure outer entered") {
                fixture.probe.has("close-failure.outer.entered")
            }
            let invalidation = try fixture.tasks.start {
                do {
                    try await fixture.producer.invalidate(reason: .engineChanged)
                    fixture.probe.record("close-failure.invalidation.unexpected-success")
                } catch {
                    fixture.probe.record("close-failure.invalidation.returned-error")
                    throw error
                }
            }
            try await ProducerLifetimeControl.until("original source retains failed close") {
                let state = await fixture.source.state
                return state == .sessionCloseFailed && fixture.probe.has("close-failure.outer.cancelled")
            }
            XCTAssertEqual(fixture.probe.snapshot().closeTokens, [ProducerLifetimeNativeProbe.token])
            XCTAssertEqual(fixture.probe.snapshot().successfulCloses, 0)
            XCTAssertFalse(operation.finished.isOpen)
            XCTAssertFalse(invalidation.finished.isOpen)

            release.open()
            let operationError = try await ProducerLifetimeControl.failure(operation, "late close-failure result")
            XCTAssertEqual(operationError as? AnyHeartNativeMigrationProducerError, .inactive)
            let closeError = try await ProducerLifetimeControl.failure(invalidation, "close error after joined result")
            XCTAssertEqual(closeError as? AnyHeartNativeSourceAccountError, .sessionCloseFailed)
            let failedState = await fixture.source.state
            XCTAssertEqual(failedState, .sessionCloseFailed)

            let retry = try fixture.tasks.start {
                try await fixture.producer.invalidate(reason: .engineChanged)
            }
            try await ProducerLifetimeControl.value(retry, "retry original owned token")
            let snapshot = fixture.probe.snapshot()
            XCTAssertEqual(snapshot.creates, 1)
            XCTAssertEqual(snapshot.closeTokens,
                           [ProducerLifetimeNativeProbe.token, ProducerLifetimeNativeProbe.token])
            XCTAssertEqual(snapshot.successfulCloses, 1)
            XCTAssertEqual(snapshot.validations, 0)
            XCTAssertLessThan(try XCTUnwrap(snapshot.events.firstIndex(of: "native.close.failed")),
                              try XCTUnwrap(snapshot.events.firstIndex(of: "close-failure.outer.returning")))
            XCTAssertFalse(snapshot.events.contains("close-failure.invalidation.unexpected-success"))
            XCTAssertLessThan(try XCTUnwrap(snapshot.events.firstIndex(of: "close-failure.outer.returning")),
                              try XCTUnwrap(snapshot.events.firstIndex(of: "close-failure.invalidation.returned-error")))
            let finalState = await fixture.source.state
            XCTAssertEqual(finalState, .idle)
        }
    }

    func testSourceBindingRefusalClosesTheOriginalGrantWithoutJoiningItsAwaitingProducer() async throws {
        try await ProducerLifetimeControl.withFixture { fixture in
            // The constructor must succeed before the negative control starts.
            // This empty synthetic bundle intentionally has no complete head
            // census, so it cannot authorize a source revalidation or migration.
            let binding = try AnyDestinationSourceBinding(
                accountID: fixture.review.bundle.sourceAccountID,
                spaceID: fixture.review.bundle.sourceSpaceID,
                witnessSHA256: fixture.review.bundle.sourceWitnessSHA256,
                captureManifestSHA256: fixture.review.bundle.manifestSHA256,
                semanticPlanSHA256: ProducerLifetimeFixtureFiles.hash("negative-lifetime-plan"),
                sourceObjectIDs: ["synthetic-head-that-was-not-captured"])
            XCTAssertEqual(binding.accountID, fixture.review.bundle.sourceAccountID)
            XCTAssertEqual(binding.spaceID, fixture.review.bundle.sourceSpaceID)
            XCTAssertEqual(binding.captureManifestSHA256, fixture.review.bundle.manifestSHA256)
            XCTAssertNil(fixture.review.bundle.nativeStoreContext?.headCensus)
            XCTAssertNil(binding.definitionManifestBytes)

            let operation = try fixture.tasks.start {
                try await fixture.producer.withOwnedOperation { _ -> Int in
                    fixture.probe.record("revalidate.entered")
                    do {
                        try await fixture.source.revalidate(source: binding)
                        fixture.probe.record("revalidate.must-not-succeed")
                        throw ProducerLifetimeControlError.unexpectedSuccess
                    } catch {
                        fixture.probe.record("revalidate.returned")
                        throw error
                    }
                }
            }
            let refusal = try await ProducerLifetimeControl.failure(operation, "source refusal without join cycle")
            XCTAssertEqual(refusal as? AnyHeartNativeSourceCaptureCoordinatorError, .sourceBinding)
            let snapshot = fixture.probe.snapshot()
            XCTAssertTrue(snapshot.events.contains("revalidate.entered"))
            XCTAssertFalse(snapshot.events.contains("revalidate.must-not-succeed"))
            XCTAssertEqual(snapshot.validations, 0)
            XCTAssertEqual(snapshot.creates, 1)
            XCTAssertEqual(snapshot.closeTokens, [ProducerLifetimeNativeProbe.token])
            XCTAssertEqual(snapshot.successfulCloses, 1)
            XCTAssertLessThan(try XCTUnwrap(snapshot.events.firstIndex(of: "native.close.succeeded")),
                              try XCTUnwrap(snapshot.events.firstIndex(of: "revalidate.returned")))
            let state = await fixture.source.state
            XCTAssertEqual(state, .idle)
        }
    }
}

private enum ProducerLifetimeControlError: Error, Sendable {
    case timeout(String), fixtureIdentity, unexpectedSuccess, unexpectedValidation
    case injectedNativeCloseFailure, taskRegistrationAfterCleanup
}

/// Deliberately ignores task cancellation until the test or cleanup opens it.
/// This models an admitted outer destination operation returning late.
private final class ProducerLifetimeGate: @unchecked Sendable {
    private let lock = NSLock()
    private var opened = false
    private var waiters: [CheckedContinuation<Void, Never>] = []

    func wait() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if opened {
                lock.unlock()
                continuation.resume()
            } else {
                waiters.append(continuation)
                lock.unlock()
            }
        }
    }

    func open() {
        lock.lock()
        opened = true
        let pending = waiters
        waiters.removeAll()
        lock.unlock()
        for continuation in pending { continuation.resume() }
    }

    var isOpen: Bool {
        lock.lock()
        defer { lock.unlock() }
        return opened
    }
}

/// Each observed task owns its actual typed result. Completion is marked only
/// on exit, never by cancellation or by opening a test gate.
private final class ProducerLifetimeTask<Value: Sendable>: Sendable {
    let task: Task<Value, Error>
    let finished: ProducerLifetimeGate

    init(_ operation: @escaping @Sendable () async throws -> Value) {
        let finished = ProducerLifetimeGate()
        self.finished = finished
        task = Task {
            defer { finished.open() }
            return try await operation()
        }
    }
}

private final class ProducerLifetimeTasks: @unchecked Sendable {
    struct Entry: Sendable {
        let cancel: @Sendable () -> Void
        let finished: @Sendable () -> Bool
        let join: @Sendable () async -> Void
    }
    private let lock = NSLock()
    private var entries: [Entry] = []
    private var gates: [ProducerLifetimeGate] = []
    private var sealed = false

    func start<Value: Sendable>(
        _ operation: @escaping @Sendable () async throws -> Value
    ) throws -> ProducerLifetimeTask<Value> {
        lock.lock()
        defer { lock.unlock() }
        guard !sealed else { throw ProducerLifetimeControlError.taskRegistrationAfterCleanup }
        let observed = ProducerLifetimeTask(operation)
        entries.append(.init(
            cancel: { observed.task.cancel() },
            finished: { observed.finished.isOpen },
            join: { _ = await observed.task.result }))
        return observed
    }

    func gate() -> ProducerLifetimeGate {
        lock.lock()
        defer { lock.unlock() }
        precondition(!sealed)
        let gate = ProducerLifetimeGate()
        gates.append(gate)
        return gate
    }

    func releaseGatesAndCancelTasks() {
        lock.lock()
        let currentGates = gates, currentTasks = entries
        lock.unlock()
        for gate in currentGates { gate.open() }
        for entry in currentTasks { entry.cancel() }
    }

    func seal() -> [Entry] {
        lock.lock()
        defer { lock.unlock() }
        sealed = true
        return entries
    }
}

private final class ProducerLifetimeNativeProbe: @unchecked Sendable {
    struct Snapshot: Sendable {
        let events: [String]
        let creates: Int
        let captures: Int
        let validations: Int
        let closeTokens: [String]
        let successfulCloses: Int
        let controlIdentityFailures: Int
    }

    static let token = "synthetic-producer-lifetime-full-session"
    private let lock = NSLock()
    private var events: [String] = []
    private var creates = 0, captures = 0, validations = 0
    private var closeTokens: [String] = []
    private var successfulCloses = 0, closeFailuresRemaining = 0
    private var controlIdentityFailures = 0
    private var requestID: String?

    func record(_ event: String) {
        lock.lock()
        events.append(event)
        lock.unlock()
    }

    func snapshot() -> Snapshot {
        lock.lock()
        defer { lock.unlock() }
        return .init(events: events, creates: creates, captures: captures,
                     validations: validations, closeTokens: closeTokens,
                     successfulCloses: successfulCloses,
                     controlIdentityFailures: controlIdentityFailures)
    }

    func has(_ event: String) -> Bool { snapshot().events.contains(event) }

    func create(expectedAccountID: String) throws -> AnyHeartNativeSourceSessionGrant {
        lock.lock()
        defer { lock.unlock() }
        guard expectedAccountID == ProducerLifetimeFixtureFiles.account, creates == 0 else {
            throw ProducerLifetimeControlError.fixtureIdentity
        }
        creates += 1
        events.append("native.create")
        return .init(sessionToken: Self.token, accountID: expectedAccountID,
                     isFull: true, isAppAssociated: false)
    }

    func capture(token: String, accountID: String, spaceID: String,
                 privateDirectory: String, expectedDirectory: String, requestID: String) throws {
        lock.lock()
        defer { lock.unlock() }
        guard token == Self.token, creates == 1, captures == 0,
              accountID == ProducerLifetimeFixtureFiles.account,
              spaceID == ProducerLifetimeFixtureFiles.space,
              privateDirectory == expectedDirectory,
              requestID.hasPrefix("app-source-"), !requestID.isEmpty else {
            throw ProducerLifetimeControlError.fixtureIdentity
        }
        self.requestID = requestID
        captures += 1
        events.append("native.capture")
    }

    func validate(token: String, requestID: String) throws {
        lock.lock()
        defer { lock.unlock() }
        guard token == Self.token, requestID == self.requestID else {
            throw ProducerLifetimeControlError.fixtureIdentity
        }
        validations += 1
        events.append("native.validate")
        throw ProducerLifetimeControlError.unexpectedValidation
    }

    func control(_ name: String, token: String, requestID: String) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        guard token == Self.token, requestID == self.requestID else {
            controlIdentityFailures += 1
            return false
        }
        events.append("native." + name)
        return true
    }

    func failNextClose() {
        lock.lock()
        closeFailuresRemaining = 1
        lock.unlock()
    }

    /// Cleanup may retry an injected failure; the assertions have already
    /// observed the original failure and exact attempt count before this call.
    func allowCleanupClose() {
        lock.lock()
        closeFailuresRemaining = 0
        lock.unlock()
    }

    func close(token: String) throws {
        lock.lock()
        defer { lock.unlock() }
        guard token == Self.token, creates == 1 else {
            throw ProducerLifetimeControlError.fixtureIdentity
        }
        closeTokens.append(token)
        if closeFailuresRemaining > 0 {
            closeFailuresRemaining -= 1
            events.append("native.close.failed")
            throw ProducerLifetimeControlError.injectedNativeCloseFailure
        }
        successfulCloses += 1
        events.append("native.close.succeeded")
    }
}

private struct ProducerLifetimeFixture: Sendable {
    let source: AnyHeartNativeSourceAccountController
    let review: AnyHeartNativeSourceCaptureReview
    let producer: AnyHeartNativeMigrationProducer
    let probe: ProducerLifetimeNativeProbe
    let tasks: ProducerLifetimeTasks
}

private enum ProducerLifetimeControl {
    /// Poll only observable completion; a timeout never implicitly joins or
    /// cancels the task being observed. Cleanup performs those operations.
    static func until(_ label: String,
                      _ condition: @escaping @Sendable () async -> Bool) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(5))
        while !(await condition()) {
            guard clock.now < deadline else { throw ProducerLifetimeControlError.timeout(label) }
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    static func value<Value: Sendable>(
        _ observed: ProducerLifetimeTask<Value>, _ label: String
    ) async throws -> Value {
        try await until(label) { observed.finished.isOpen }
        return try await observed.task.value
    }

    static func failure<Value: Sendable>(
        _ observed: ProducerLifetimeTask<Value>, _ label: String
    ) async throws -> any Error {
        try await until(label) { observed.finished.isOpen }
        switch await observed.task.result {
        case .success:
            XCTFail("Expected a typed refusal: " + label)
            throw ProducerLifetimeControlError.unexpectedSuccess
        case .failure(let error): return error
        }
    }

    static func withFixture(
        _ body: @escaping @Sendable (ProducerLifetimeFixture) async throws -> Void
    ) async throws {
        let files = try ProducerLifetimeFixtureFiles.create()
        let probe = ProducerLifetimeNativeProbe()
        let tasks = ProducerLifetimeTasks()
        let authority = AnyHeartNativeSourceSessionAuthority(
            create: { try probe.create(expectedAccountID: $0) },
            close: { try probe.close(token: $0) })
        let bridge = AnyHeartNativeSourceBridge(
            capture: { token, account, space, directory, request in
                try probe.capture(token: token, accountID: account, spaceID: space,
                                  privateDirectory: directory, expectedDirectory: files.root.path,
                                  requestID: request)
                return try ProducerLifetimeFixtureFiles.descriptor(
                    manifest: files.manifest, directory: files.bundle, requestID: request)
            },
            validate: { token, request, _ in try probe.validate(token: token, requestID: request) },
            cancel: { probe.control("cancel", token: $0, requestID: $1) },
            release: { probe.control("release", token: $0, requestID: $1) })
        let source: AnyHeartNativeSourceAccountController
        do {
            source = try .init(authority: authority, bridge: bridge, privateDirectory: files.root)
        } catch {
            // No capture or grant exists yet.
            try? FileManager.default.removeItem(at: files.root)
            throw error
        }

        var producer: AnyHeartNativeMigrationProducer?
        let outcome: Result<Void, Error>
        do {
            let capture = try tasks.start {
                try await source.capture(accountID: ProducerLifetimeFixtureFiles.account,
                                         spaceID: ProducerLifetimeFixtureFiles.space)
            }
            let review = try await value(capture, "source capture")
            let owner = try AnyHeartNativeMigrationProducer(
                source: source, review: review, privateCaptureParent: files.root)
            producer = owner
            let ready = await source.state
            XCTAssertEqual(ready, .ready)
            XCTAssertFalse(review.permitsDestinationWrites)
            XCTAssertEqual(probe.snapshot().creates, 1)
            XCTAssertEqual(probe.snapshot().captures, 1)
            guard ready == .ready else { throw ProducerLifetimeControlError.fixtureIdentity }
            try await body(.init(source: source, review: review, producer: owner, probe: probe, tasks: tasks))
            outcome = .success(())
        } catch {
            outcome = .failure(error)
        }

        // This supervisor is not a registered child of the producer or of the
        // test task. It can finish cleanup even if the XCTest caller cancelled.
        let finalProducer = producer
        let cleanup = Task.detached {
            probe.allowCleanupClose()
            tasks.releaseGatesAndCancelTasks()
            let close = try tasks.start {
                if let finalProducer { try await finalProducer.release() }
                else { try await source.release() }
            }
            let entries = tasks.seal()
            try await until("all fixture tasks and original native cleanup") {
                entries.allSatisfy { $0.finished() }
            }
            for entry in entries { await entry.join() }
            try await close.task.value
            let finalState = await source.state
            guard finalState == .idle else { throw ProducerLifetimeControlError.fixtureIdentity }
        }
        do {
            try await cleanup.value
        } catch {
            // A cleanup regression must not race deletion of a private bundle.
            // Abort this test process after the finite observation window; the
            // fixture remains available for the external runner's failure log.
            XCTFail("Producer fixture cleanup failed; retaining " + files.root.path + ": " + String(describing: error))
            fatalError("Refusing to delete a fixture with unfinished producer/source ownership")
        }
        XCTAssertEqual(probe.snapshot().controlIdentityFailures, 0)
        try FileManager.default.removeItem(at: files.root)
        try outcome.get()
    }
}

private enum ProducerLifetimeFixtureFiles {
    static let account = "source-account", space = "source-space"
    struct Files: Sendable {
        let root: URL
        let bundle: URL
        let manifest: Data
    }

    static func hash(_ text: String) -> String { AnyContentDigest.sha256(Data(text.utf8)) }

    private static func encode(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }

    // Exact receipt body from the source-only descriptor fixture 90d0f70b.
    // Its absent head census and false authority/semantic fields stay intact.
    private static func receipt() -> AnyJSON {
        .object([
            "Version": .string("loaded-account-native-space-source-v1"),
            "Source": .object([
                "version": .string("loaded-account-native-witness-v1"),
                "accountAuthority": .string("held-application-account-directory-lease-v1"),
                "sessionAuthority": .string("validated-native-full-unassociated-session-v1"),
                "accountSHA256": .string(hash(account)), "accountDirectorySHA256": .string(hash("unit-directory")),
                "accountSessionAuthorizedAtCapture": .bool(true), "nativeIdentityCensusRequired": .bool(true),
                "source": .object([
                    "version": .string("loaded-native-acl-witness-v1"),
                    "accountSHA256": .string(hash(account)), "spaceSHA256": .string(hash(space)),
                    "alreadyLoaded": .bool(true), "aclReadAuthorizedAtCapture": .bool(true),
                    "aclIdSHA256": .string(hash("acl")), "aclHeadSHA256": .string(hash("head")),
                    "native": .object([
                        "Version": .string("native-localstore-witness-v1"), "SpaceSHA256": .string(hash(space)),
                        "WitnessSHA256": .string(hash("unit-witness")), "LocalDecodedRowsComplete": .bool(true),
                        "Generation": .integer(0)])
                ])
            ]),
            "Inventory": .object(["SpaceSHA256": .string(hash(space)), "SourceWitnessSHA256": .string(hash("unit-witness")),
                "ACLHeadSHA256": .string(hash("head")), "Generation": .integer(0), "Trees": .integer(0),
                "OtherCollections": .integer(0), "OtherCollectionRows": .integer(0)]),
            "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
            "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true), "OriginalNativeHistoryRowsRetained": .bool(true),
            "NativeTrees": .integer(0), "CapturedObjects": .integer(0), "CapturedFiles": .integer(0),
            "FileReferences": .integer(0), "UnresolvedEntries": .integer(0), "ClosedResolverUnmapped": .integer(0),
            "SnapshotBytes": .integer(0), "MetadataBytes": .integer(0), "PlaintextBytes": .integer(0),
            "Tombstones": .integer(0), "SettingsTrees": .integer(0), "UnsupportedTrees": .integer(0),
            "IndexResolverSnapshotBound": .bool(false), "Objects": .array([]),
            "AllCurrentObjectsCaptured": .bool(true), "CurrentFilePayloadCompleteness": .bool(true),
            "PermitsDestinationWrites": .bool(false), "HasNativeSourceAdmission": .bool(false),
            "SemanticCompleteness": .bool(false), "HistorySemanticsValidated": .bool(false)])
    }


    static func descriptor(manifest: Data, directory: URL, requestID: String) throws -> Data {
        let root = try JSONDecoder().decode(AnyJSON.self, from: manifest)
        return try encode(.object([
            "contract": .string(AnyHeartNativeCaptureDescriptor.contract),
            "requestID": .string(requestID),
            "sourceAccountID": .string(account), "sourceSpaceID": .string(space),
            "privateBundleDirectory": .string(directory.path),
            "manifestSHA256": .string(AnyContentDigest.sha256(manifest)),
            "sourceRowsSHA256": try XCTUnwrap(root["SourceRows"]?["SHA256"]),
            "nativeTrees": try XCTUnwrap(root["Receipt"]?["NativeTrees"]),
            "capturedObjects": try XCTUnwrap(root["Receipt"]?["CapturedObjects"]),
            "capturedFiles": try XCTUnwrap(root["Receipt"]?["CapturedFiles"]),
            "accountSessionAuthorizedAtCapture": .bool(true),
            "capturedSnapshotsBoundToCheckpoint": .bool(true),
            "currentFilePayloadCompleteness": try XCTUnwrap(root["Receipt"]?["CurrentFilePayloadCompleteness"]),
            "originalNativeHistoryRowsRetained": .bool(true), "permitsDestinationWrites": .bool(false)]))
    }

    static func create() throws -> Files {
        let manager = FileManager.default
        let root = manager.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("producer-lifetime-control-" + UUID().uuidString, isDirectory: true)
        let directory = root.appendingPathComponent("native-source-control", isDirectory: true)
        try manager.createDirectory(at: root, withIntermediateDirectories: false,
                                    attributes: [.posixPermissions: 0o700])
        do {
            try manager.createDirectory(at: directory, withIntermediateDirectories: false,
                                        attributes: [.posixPermissions: 0o700])
            let rows = Data("synthetic unit control; not a native capture".utf8)
            let manifest = try encode(.object([
                "Contract": .string("pinkha-native-whole-source-bundle-v1"), "Receipt": receipt(),
                "SourceRows": .object(["Path": .string("native-source-rows.witness"),
                    "SHA256": .string(AnyContentDigest.sha256(rows)), "Bytes": .integer(Int64(rows.count))]),
                "Trees": .array([]), "Objects": .array([]), "Files": .array([]), "FileReferences": .array([]),
                "Gaps": .array([]), "ResolverUnmapped": .array([]), "BundledDefinitionsUsed": .array([]),
                "RetainedOtherCollections": .array([])]))
            for (name, bytes) in [("manifest.json", manifest), ("native-source-rows.witness", rows)] {
                let url = directory.appendingPathComponent(name)
                try bytes.write(to: url, options: .withoutOverwriting)
                try manager.setAttributes([.posixPermissions: 0o400], ofItemAtPath: url.path)
            }
            for url in [root, directory] {
                let attributes = try manager.attributesOfItem(atPath: url.path)
                guard (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700 else {
                    throw ProducerLifetimeControlError.fixtureIdentity
                }
            }
            for name in ["manifest.json", "native-source-rows.witness"] {
                let attributes = try manager.attributesOfItem(atPath: directory.appendingPathComponent(name).path)
                guard (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o400 else {
                    throw ProducerLifetimeControlError.fixtureIdentity
                }
            }
            return .init(root: root, bundle: directory, manifest: manifest)
        } catch {
            // No source grant or task exists during this synchronous setup.
            try? manager.removeItem(at: root)
            throw error
        }
    }
}
