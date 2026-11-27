import PinkhaKit
import Testing
@testable import Anytype

@Suite("Pinkha bootstrap single-flight")
struct PinkhaBootstrapStateManagerTests {
    @Test("Only one concurrent caller can claim provisioning for a Space")
    func onlyOneProvisioningOwner() async {
        let manager = PinkhaBootstrapStateManager()
        let claims = await withTaskGroup(of: Bool.self, returning: [Bool].self) { group in
            for _ in 0..<64 {
                group.addTask {
                    manager.beginProvisioningIfNeeded(spaceId: "pinkha-acceptance-space")
                }
            }

            var values: [Bool] = []
            for await value in group {
                values.append(value)
            }
            return values
        }

        #expect(claims.filter { $0 }.count == 1)
        guard case .provisioning = manager.state(for: "pinkha-acceptance-space") else {
            Issue.record("The winning claim must publish provisioning before returning")
            return
        }
    }
    @Test("An old account completion cannot overwrite a new claim for the same Space")
    func oldAccountCompletionCannotPublishIntoReplacementClaim() throws {
        let manager = PinkhaBootstrapStateManager()
        let original = try #require(manager.beginProvisioningClaim(spaceId: "same-space"))
        manager.resetForAccountChange()
        let replacement = try #require(manager.beginProvisioningClaim(spaceId: "same-space"))
        #expect(original != replacement)
        manager.setState(.failed("retired account"), for: "same-space", claim: original)
        guard case .provisioning = manager.state(for: "same-space") else {
            Issue.record("A retired completion changed the replacement account's state")
            return
        }
        manager.setState(.failed("current account"), for: "same-space", claim: replacement)
        #expect(manager.state(for: "same-space") == .failed("current account"))
    }

}

#if DEBUG
import AnytypeCore
import Combine
import Foundation
import ProtobufMessages
import Services

/// App-hosted component coverage of the actual account decorator and selection
/// implementations. Controlled protocol effects are not native-account proof.
@Suite("Pinkha account startup, publication and explicit retry", .serialized, .timeLimit(.minutes(2)))
@MainActor
struct PinkhaAccountRuntimeTests {
    @Test("Accepted Stop releases startup, rejects replacement work, and drains after caller cancellation")
    func startupStopRetiresOriginalAttemptAndDrainsBeforeReplacement() async throws {
        let fixture = try AccountRuntimeAuthFixture(selectBlocked: true, logoutBlocked: true)
        try await fixture.run {
            let startup = fixture.startSelection()
            try await accountRuntimeEventually { fixture.events.contains("base.select.enter") }
            let attempt = try #require(fixture.events.originalAttempt)
            let removeData = await accountRuntimeResult { try await fixture.service.logout(removeData: true) }
            #expect(accountRuntimeFailed(removeData))
            #expect(fixture.events.count("base.logout.enter") == 0)

            let stop = fixture.startStop()
            try await accountRuntimeEventually { fixture.events.contains("base.logout.enter") }
            #expect(!attempt.isCurrent)
            let duplicate = await accountRuntimeResult { try await fixture.service.logout(removeData: false) }
            let replacement = await accountRuntimeResult {
                try await fixture.service.selectAccount(id: "component-account-C", preferredSpaceId: "component-space")
            }
            #expect(accountRuntimeFailed(duplicate))
            #expect(accountRuntimeFailed(replacement))
            #expect(fixture.events.count("base.select.enter") == 1)
            #expect(fixture.events.count("base.logout.enter") == 1)

            // The accepted cleanup is the original retained task. Cancelling its
            // caller must not strand the original base operation or its holds.
            stop.cancel()
            fixture.logoutRelease.open()
            let stopResult = await stop.result
            let startupResult = await startup.result
            #expect(accountRuntimeFailed(stopResult))
            if case .failure(let error) = stopResult { #expect(error is CancellationError) }
            #expect(accountRuntimeFailed(startupResult))
            await attempt.waitForDrain()
            try await accountRuntimeEventually { fixture.events.resumedTokens.count == 2 }
            #expect(fixture.events.preparedTokens == fixture.events.resumedTokens)
            #expect(fixture.events.count("miniapps.resume") == 2)
            #expect(fixture.events.count("base.select.drained") == 1)
            #expect(fixture.events.count("base.logout.return") == 1)
            #expect(fixture.events.precedes("base.select.drained", "bootstrap.quiesce", lastSecond: true))
            #expect(fixture.events.count("hanlin.open:component-account-B") == 0)
            #expect(fixture.events.count("sharing.open:component-account-B") == 0)

            let next = fixture.startSelection()
            let nextAccount = try await next.value
            #expect(nextAccount.id == "component-account-B")
            #expect(fixture.events.count("base.select.enter") == 2)
        }
    }

    @Test("Stop joins the actual publication task before closing either presentation owner", arguments: [false, true])
    func queuedPublicationCannotReopenOwnersAfterStop(holdSharing: Bool) async throws {
        let boundary: AccountRuntimePublicationBoundary = holdSharing ? .sharingReturn : .hanlinHop
        let fixture = try AccountRuntimeAuthFixture(publicationBoundary: boundary)
        try await fixture.run {
            let startup = fixture.startSelection()
            let held = boundary == .hanlinHop ? "publication.hanlin.hop" : "sharing.open.enter"
            try await accountRuntimeEventually { fixture.events.contains(held) }
            let attempt = try #require(fixture.events.originalAttempt)
            let stop = fixture.startStop()
            try await accountRuntimeEventually { !attempt.isCurrent }
            fixture.hanlinHopRelease.open()
            fixture.sharingRelease.open()
            let startupResult = await startup.result
            try await stop.value
            #expect(accountRuntimeFailed(startupResult))
            await attempt.waitForDrain()
            try await accountRuntimeEventually { fixture.events.resumedTokens.count == 2 }
            #expect(fixture.events.preparedTokens == fixture.events.resumedTokens)
            #expect(fixture.events.count("miniapps.resume") == 2)
            #expect(fixture.events.count("sharing.close") == 3)
            #expect(fixture.events.count("hanlin.close:component-account-B:false") == 2)
            #expect(fixture.events.count("base.logout.enter") == 1)
            if boundary == .hanlinHop {
                // This fails if the same-turn MainActor attempt check is lost,
                // even though the outer stage would subsequently reject it.
                #expect(fixture.events.count("hanlin.open:component-account-B") == 0)
                #expect(fixture.events.count("sharing.open.enter") == 0)
            } else {
                #expect(fixture.events.count("hanlin.open:component-account-B") == 1)
                #expect(fixture.events.count("sharing.open:component-account-B") == 1)
                #expect(fixture.events.precedesOccurrence("sharing.open:component-account-B", "sharing.close", occurrence: 1))
                #expect(fixture.events.precedes("sharing.open:component-account-B", "base.logout.enter"))
            }
            #expect(fixture.events.allOpensPrecedeLastClose())
        }
    }

    @Test("Account replacement rejects the pending original Space selection and its late publication")
    func accountReplacementRejectsPendingSelectionAndLateBootstrap() async throws {
        let fixture = try AccountRuntimeSelectionFixture(workspaceBlocked: true, failFirstBootstrap: false)
        try await fixture.run {
            let accountLifetime = try #require(fixture.account.editorWriteLifetime)
            let originalCapture = try EditorDocumentWriteCapture(accountLifetime)
            let pending = fixture.startSelection()
            try await accountRuntimeEventually { fixture.events.contains("workspace.open") }
            fixture.account.account = try accountRuntimeAccount("component-account-B")
            #expect(!originalCapture.source.isCurrent(originalCapture.token))
            fixture.workspaceRelease.open()
            let pendingResult = await pending.result
            #expect(accountRuntimeFailed(pendingResult))
            if case .failure(let error) = pendingResult {
                #expect(error as? EditorDocumentWriteError == .rejected(.retired))
            }
            #expect(fixture.manager.workspaceInfo == nil)
            #expect(fixture.events.count("spaces.publish") == 0)
            #expect(fixture.events.count("widgets.prepare") == 0)
            #expect(fixture.events.count("types.start") == 0)
            #expect(fixture.events.count("properties.start") == 0)
            #expect(fixture.events.count("bootstrap.enter") == 0)

            let current = fixture.startSelection()
            let actualInfo = try await current.value
            #expect(actualInfo == fixture.info)
            #expect(fixture.manager.workspaceInfo == fixture.info)
            try await accountRuntimeEventually { fixture.state.state(for: "component-space") == .ready(fixture.manifest) }
            let beforeStaleHook = fixture.events.count("bootstrap.enter")
            PinkhaBootstrapHook.handleSpaceActivated(spaceId: "component-space", accountCapture: originalCapture)
            await originalCapture.source.waitForOperationsToDrain()
            #expect(fixture.events.count("bootstrap.enter") == beforeStaleHook)
            #expect(fixture.events.count("workspace.open") == 2)
            #expect(fixture.events.count("spaces.publish") == 1)
            // The protocol fixture deliberately supplies no original native
            // SpaceView capability; the component seam cannot mint one.
            let nativeSelection = accountRuntimeSyncResult { try fixture.manager.currentOriginalActiveSpaceSelection() }
            #expect(accountRuntimeFailed(nativeSelection))
        }
    }

    @Test("Explicit same-Space retry reuses WorkspaceOpen and gives one failed Bootstrap claim a new owner")
    func cachedSameSpaceFailedBootstrapRetriesOnceWithoutWorkspaceReopen() async throws {
        let fixture = try AccountRuntimeSelectionFixture(workspaceBlocked: false, failFirstBootstrap: true)
        try await fixture.run {
            let first = fixture.startSelection()
            let firstInfo = try await first.value
            #expect(firstInfo == fixture.info)
            try await accountRuntimeEventually {
                if case .failed = fixture.state.state(for: "component-space") { return true }
                return false
            }
            #expect(fixture.events.count("bootstrap.enter") == 1)
            let retry = fixture.startSelection()
            let retryInfo = try await retry.value
            #expect(retryInfo == fixture.info)
            try await accountRuntimeEventually { fixture.events.count("bootstrap.enter") == 2 }
            let concurrentExplicitRetry = fixture.startSelection()
            let concurrentInfo = try await concurrentExplicitRetry.value
            #expect(concurrentInfo == fixture.info)
            #expect(fixture.state.state(for: "component-space") == .provisioning)
            #expect(fixture.events.count("bootstrap.enter") == 2)
            fixture.bootstrapRelease.open()
            try await accountRuntimeEventually { fixture.state.state(for: "component-space") == .ready(fixture.manifest) }
            let readyReuse = fixture.startSelection()
            let readyInfo = try await readyReuse.value
            #expect(readyInfo == fixture.info)
            await fixture.account.editorWriteLifetime?.waitForOperationsToDrain()
            #expect(fixture.events.count("workspace.open") == 1)
            #expect(fixture.events.count("bootstrap.enter") == 2)
            #expect(fixture.events.count("spaces.publish") == 1)
            #expect(fixture.events.count("widgets.prepare") == 1)
            #expect(fixture.events.count("types.start") == 1)
            #expect(fixture.events.count("properties.start") == 1)
            #expect(fixture.events.precedes("widgets.prepare", "types.start"))
            #expect(fixture.events.precedes("types.start", "properties.start"))
        }
    }
}

private enum AccountRuntimePublicationBoundary: String, Sendable {
    case hanlinHop
    case sharingReturn
}

private enum AccountRuntimeFixtureError: Error {
    case timedOut
    case unexpectedCall
    case intentionalBootstrapFailure
    case missingOriginalAttempt
    case missingOriginalBinding
    case conflictingNativeFixture
}

private func accountRuntimeRequireComponentEnvironment() throws {
    let environment = ProcessInfo.processInfo.environment
    let nativeFixtures = ["PINKHA_TYPE_PRESERVATION_POSTFLIGHT", "PINKHA_NATIVE_DERIVED_ACCEPTANCE",
        "PINKHA_PREPARE_TYPE_PRESERVATION", "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION",
        "PINKHA_SIMULATOR_UI_DISPOSABLE", "PINKHA_HANLIN_NATIVE_PREPARATION",
        "PINKHA_PREPARE_HANLIN_SELECTION_UI", "PINKHA_PROPERTIES_PREPARE",
        "PINKHA_T5_UI_PREPARATION", "PINKHA_T5_APPLE_PAIR"]
    guard nativeFixtures.allSatisfy({ environment[$0] != "1" }) else {
        throw AccountRuntimeFixtureError.conflictingNativeFixture
    }
}

@MainActor
private func accountRuntimeEventually(_ predicate: @MainActor () -> Bool) async throws {
    let deadline = ContinuousClock.now.advanced(by: .seconds(20))
    while ContinuousClock.now < deadline {
        if predicate() { return }
        try Task.checkCancellation()
        await Task.yield()
    }
    throw AccountRuntimeFixtureError.timedOut
}

@MainActor
private func accountRuntimeResult<Value>(_ body: @MainActor () async throws -> Value) async -> Result<Value, any Error> {
    do { return .success(try await body()) } catch { return .failure(error) }
}

private func accountRuntimeSyncResult<Value>(_ body: () throws -> Value) -> Result<Value, any Error> {
    do { return .success(try body()) } catch { return .failure(error) }
}

private func accountRuntimeFailed<Value>(_ result: Result<Value, any Error>) -> Bool {
    if case .failure = result { return true }
    return false
}

private func accountRuntimeAccount(_ id: String) throws -> AccountData {
    var original = Anytype_Model_Account()
    original.id = id
    original.status = .active
    original.info.accountSpaceID = "component-space"
    original.info.spaceViewID = "component-view"
    original.info.techSpaceID = "component-tech-space"
    return try original.asModel()
}

private final class AccountRuntimeGate: @unchecked Sendable {
    private let lock = NSLock()
    private var isOpen: Bool
    private var waiters: [CheckedContinuation<Void, Never>] = []
    init(open: Bool = false) { isOpen = open }
    func wait() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if isOpen { lock.unlock(); continuation.resume() }
            else { waiters.append(continuation); lock.unlock() }
        }
    }
    func open() {
        lock.lock()
        isOpen = true
        let pending = waiters
        waiters.removeAll()
        lock.unlock()
        for waiter in pending { waiter.resume() }
    }
}

private final class AccountRuntimeEvents: @unchecked Sendable {
    private let lock = NSLock()
    private var values: [String] = []
    private var attempts: [OriginalAuthAttempt] = []
    private var prepared: Set<UUID> = []
    private var resumed: Set<UUID> = []
    func record(_ value: String) { lock.lock(); values.append(value); lock.unlock() }
    func capture(_ attempt: OriginalAuthAttempt) { lock.lock(); attempts.append(attempt); lock.unlock() }
    var originalAttempt: OriginalAuthAttempt? { lock.lock(); defer { lock.unlock() }; return attempts.first }
    var snapshot: [String] { lock.lock(); defer { lock.unlock() }; return values }
    var preparedTokens: Set<UUID> { lock.lock(); defer { lock.unlock() }; return prepared }
    var resumedTokens: Set<UUID> { lock.lock(); defer { lock.unlock() }; return resumed }
    func prepare() -> UUID {
        let token = UUID()
        lock.lock(); prepared.insert(token); values.append("miniapps.prepare"); lock.unlock()
        return token
    }
    func resume(_ token: UUID) { lock.lock(); resumed.insert(token); values.append("miniapps.resume"); lock.unlock() }
    func contains(_ value: String) -> Bool { snapshot.contains(value) }
    func count(_ value: String) -> Int { snapshot.filter { $0 == value }.count }
    func allOpensPrecedeLastClose() -> Bool {
        let values = snapshot
        guard let close = values.lastIndex(of: "sharing.close") else { return false }
        return values.indices.filter { values[$0].hasPrefix("sharing.open:") }.allSatisfy { $0 < close }
    }
    func precedes(_ first: String, _ second: String, lastSecond: Bool = false) -> Bool {
        let values = snapshot
        guard let a = values.firstIndex(of: first),
              let b = lastSecond ? values.lastIndex(of: second) : values.firstIndex(of: second) else { return false }
        return a < b
    }
    func precedesOccurrence(_ first: String, _ second: String, occurrence: Int) -> Bool {
        let values = snapshot
        let positions = values.indices.filter { values[$0] == second }
        guard let a = values.firstIndex(of: first), positions.indices.contains(occurrence) else { return false }
        return a < positions[occurrence]
    }
}

private final class AccountRuntimeBaseAuth: AuthServiceProtocol, Sendable {
    let account: AccountManager
    let selectedAccount: AccountData
    let events: AccountRuntimeEvents
    let selectRelease: AccountRuntimeGate
    let logoutRelease: AccountRuntimeGate
    init(account: AccountManager, selectedAccount: AccountData, events: AccountRuntimeEvents,
         selectRelease: AccountRuntimeGate, logoutRelease: AccountRuntimeGate) {
        self.account = account; self.selectedAccount = selectedAccount; self.events = events
        self.selectRelease = selectRelease; self.logoutRelease = logoutRelease
    }
    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        guard let attempt = OriginalAuthRequestContext.parent, attempt.kind == .startup else {
            throw AccountRuntimeFixtureError.missingOriginalAttempt
        }
        try attempt.validate()
        let admissions = try attempt.admitStage()
        events.capture(attempt)
        events.record("base.select.enter")
        defer {
            for admission in admissions { admission.cancel() }
            events.record("base.select.drained")
        }
        await selectRelease.wait()
        try attempt.validate()
        guard id == selectedAccount.id, preferredSpaceId == selectedAccount.info.accountSpaceId else {
            throw AccountRuntimeFixtureError.unexpectedCall
        }
        account.account = selectedAccount
        events.record("base.select.return")
        return selectedAccount
    }
    func logout(removeData: Bool) async throws {
        guard let attempt = OriginalAuthRequestContext.parent, attempt.kind == .stop, !removeData else {
            throw AccountRuntimeFixtureError.missingOriginalAttempt
        }
        try attempt.validate()
        events.record("base.logout.enter")
        selectRelease.open()
        await logoutRelease.wait()
        events.record("base.logout.return")
    }
    func createWallet() async throws -> String { throw AccountRuntimeFixtureError.unexpectedCall }
    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData { throw AccountRuntimeFixtureError.unexpectedCall }
    func walletRecovery(mnemonic: String) async throws { throw AccountRuntimeFixtureError.unexpectedCall }
    func accountRecover() async throws { throw AccountRuntimeFixtureError.unexpectedCall }
    func mnemonicByEntropy(_ entropy: String) async throws -> String { throw AccountRuntimeFixtureError.unexpectedCall }
    func deleteAccount() async throws -> AccountStatus { throw AccountRuntimeFixtureError.unexpectedCall }
    func restoreAccount() async throws -> AccountStatus { throw AccountRuntimeFixtureError.unexpectedCall }
}

private final class AccountRuntimeBootstrap: PinkhaSpaceBootstrapServiceProtocol, Sendable {
    let events: AccountRuntimeEvents
    let manifestValue: PinkhaSpaceManifest
    let failFirst: Bool
    let release: AccountRuntimeGate
    init(events: AccountRuntimeEvents, manifest: PinkhaSpaceManifest, failFirst: Bool = false,
         release: AccountRuntimeGate = AccountRuntimeGate(open: true)) {
        self.events = events; manifestValue = manifest; self.failFirst = failFirst; self.release = release
    }
    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        guard spaceId == manifestValue.spaceId else { throw AccountRuntimeFixtureError.unexpectedCall }
        guard let binding = InvocationDispatchContext.binding else { throw AccountRuntimeFixtureError.missingOriginalBinding }
        try await binding.validateForOperation(named: "ObjectCreate")
        events.record("bootstrap.enter")
        if failFirst && events.count("bootstrap.enter") == 1 { throw AccountRuntimeFixtureError.intentionalBootstrapFailure }
        await release.wait()
        try await binding.validateForOperation(named: "ObjectCreate")
        events.record("bootstrap.return")
        return manifestValue
    }
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? { nil }
    func isBootstrapped(spaceId: String) -> Bool { false }
    func quiesceAccountOperations() async { events.record("bootstrap.quiesce") }
    func resumeAccountOperations() async throws { events.record("bootstrap.resume") }
}

@MainActor
private final class AccountRuntimeAuthFixture {
    let events = AccountRuntimeEvents()
    let selectRelease: AccountRuntimeGate
    let logoutRelease: AccountRuntimeGate
    let hanlinHopRelease: AccountRuntimeGate
    let sharingRelease: AccountRuntimeGate
    let service: PinkhaHanlinAuthService
    private var joins: [@MainActor () async -> Void] = []
    init(selectBlocked: Bool = false, logoutBlocked: Bool = false,
         publicationBoundary: AccountRuntimePublicationBoundary? = nil) throws {
        try accountRuntimeRequireComponentEnvironment()
        selectRelease = AccountRuntimeGate(open: !selectBlocked)
        logoutRelease = AccountRuntimeGate(open: !logoutBlocked)
        hanlinHopRelease = AccountRuntimeGate(open: publicationBoundary != .hanlinHop)
        sharingRelease = AccountRuntimeGate(open: publicationBoundary != .sharingReturn)
        let account = AccountManager()
        account.account = try accountRuntimeAccount("component-account-A")
        let events = events, hanlinGate = hanlinHopRelease, sharingGate = sharingRelease
        let base = AccountRuntimeBaseAuth(account: account, selectedAccount: try accountRuntimeAccount("component-account-B"),
                                          events: events, selectRelease: selectRelease, logoutRelease: logoutRelease)
        let bootstrap = AccountRuntimeBootstrap(events: events, manifest: .initial(spaceId: "component-space"))
        let owners = PinkhaHanlinAuthService.AcceptanceOwners(
            accountManager: account, bootstrap: bootstrap,
            prepareMiniApps: { events.prepare() }, resumeMiniApps: { events.resume($0) },
            prepareEngine: { events.record("engine.prepare") },
            closeSharing: { events.record("sharing.close") },
            openSharing: { account in
                events.record("sharing.open.enter")
                await sharingGate.wait()
                events.record("sharing.open:\(account)")
            },
            closeHanlin: { account, removeData in events.record("hanlin.close:\(account):\(removeData)") },
            beforeHanlinPublication: { events.record("publication.hanlin.hop"); await hanlinGate.wait() },
            openHanlin: { events.record("hanlin.open:\($0)") }
        )
        service = PinkhaHanlinAuthService(base: base, acceptanceOwners: owners)
    }
    func startSelection() -> Task<AccountData, any Error> {
        let service = service
        let task = Task { try await service.selectAccount(id: "component-account-B", preferredSpaceId: "component-space") }
        joins.append { _ = await task.result }
        return task
    }
    func startStop() -> Task<Void, any Error> {
        let service = service
        let task = Task { try await service.logout(removeData: false) }
        joins.append { _ = await task.result }
        return task
    }
    func run(_ body: @MainActor () async throws -> Void) async throws {
        do { try await body(); await finish() }
        catch { await finish(); throw error }
    }
    private func finish() async {
        selectRelease.open(); logoutRelease.open(); hanlinHopRelease.open(); sharingRelease.open()
        for join in joins { await join() }
        do {
            try await accountRuntimeEventually { self.events.preparedTokens == self.events.resumedTokens }
        } catch {
            Issue.record("The component's actual MiniApps resume callbacks did not finish: \(error)")
        }
    }
}

private final class AccountRuntimeSpaces: SpaceViewsStorageProtocol, Sendable {
    let events: AccountRuntimeEvents
    init(_ events: AccountRuntimeEvents) { self.events = events }
    var allSpaceViews: [SpaceView] { [] }
    var allSpaceViewsPublisher: AnyPublisher<[SpaceView], Never> { Just([]).eraseToAnyPublisher() }
    func startSubscription() async {}
    func stopSubscription() async {}
    func spaceView(spaceViewId: String) -> SpaceView? { nil }
    func spaceView(spaceId: String) -> SpaceView? { nil }
    func spaceInfo(spaceId: String) -> AccountInfo? { nil }
    func addSpaceInfo(spaceId: String, info: AccountInfo) { events.record("spaces.publish") }
}

private final class AccountRuntimeTypes: ObjectTypeProviderProtocol, Sendable {
    let events: AccountRuntimeEvents
    init(_ events: AccountRuntimeEvents) { self.events = events }
    var syncPublisher: AnyPublisher<Void, Never> { Empty().eraseToAnyPublisher() }
    func setDefaultObjectType(type: ObjectType, spaceId: String, route: AnalyticsDefaultObjectTypeChangeRoute) {}
    func defaultObjectType(spaceId: String) throws -> ObjectType { throw AccountRuntimeFixtureError.unexpectedCall }
    func defaultObjectTypePublisher(spaceId: String) -> AnyPublisher<ObjectType, Never> { Empty().eraseToAnyPublisher() }
    func objectType(id: String) throws -> ObjectType { throw AccountRuntimeFixtureError.unexpectedCall }
    func objectType(recommendedLayout: DetailsLayout, spaceId: String) throws -> ObjectType { throw AccountRuntimeFixtureError.unexpectedCall }
    func objectType(uniqueKey: ObjectTypeUniqueKey, spaceId: String) throws -> ObjectType { throw AccountRuntimeFixtureError.unexpectedCall }
    func objectTypes(spaceId: String) -> [ObjectType] { [] }
    func deletedObjectType(id: String) -> ObjectType { preconditionFailure("Unexpected deleted-type access in account component fixture") }
    func startSubscription(spaceId: String) async { events.record("types.start") }
    func stopSubscription() async { events.record("types.stop") }
    func prepareData(spaceId: String) async {}
}

private final class AccountRuntimeProperties: PropertyDetailsStorageProtocol, Sendable {
    let events: AccountRuntimeEvents
    init(_ events: AccountRuntimeEvents) { self.events = events }
    var syncPublisher: AnyPublisher<Void, Never> { Empty().eraseToAnyPublisher() }
    func relationsDetails(keys: [String], spaceId: String) -> [PropertyDetails] { [] }
    func relationsDetails(key: String, spaceId: String) throws -> PropertyDetails { throw AccountRuntimeFixtureError.unexpectedCall }
    func relationsDetails(bundledKey: BundledPropertyKey, spaceId: String) throws -> PropertyDetails { throw AccountRuntimeFixtureError.unexpectedCall }
    func relationsDetails(ids: [String], spaceId: String) -> [PropertyDetails] { [] }
    func relationsDetails(spaceId: String) -> [PropertyDetails] { [] }
    func startSubscription(spaceId: String) async { events.record("properties.start") }
    func stopSubscription() async { events.record("properties.stop") }
    func prepareData(spaceId: String) async {}
}

@MainActor
private final class AccountRuntimeWidgets: WidgetsObjectsStorageProtocol {
    let events: AccountRuntimeEvents
    init(_ events: AccountRuntimeEvents) { self.events = events }
    func prepare(info: AccountInfo) { events.record("widgets.prepare") }
    func waitForReady(spaceId: String) async {}
    func widgetsObjects(spaceId: String) -> (channel: any BaseDocumentProtocol, personal: any BaseDocumentProtocol)? { nil }
    func clear() { events.record("widgets.clear") }
}

private final class AccountRuntimeRecency: SpaceRecencyStorageProtocol, Sendable {
    let events: AccountRuntimeEvents
    init(_ events: AccountRuntimeEvents) { self.events = events }
    func markInteraction(spaceId: String) { events.record("recency") }
    func lastInteractionDates() -> [String: Date] { [:] }
}

@MainActor
private final class AccountRuntimeSelectionFixture {
    let account = AccountManager()
    let events = AccountRuntimeEvents()
    let state = PinkhaBootstrapStateManager()
    let workspaceRelease: AccountRuntimeGate
    let bootstrapRelease: AccountRuntimeGate
    let info: AccountInfo
    let manifest: PinkhaSpaceManifest
    let service: AccountRuntimeBootstrap
    let manager: ActiveSpaceManager
    private var joins: [@MainActor () async -> Void] = []
    init(workspaceBlocked: Bool, failFirstBootstrap: Bool) throws {
        try accountRuntimeRequireComponentEnvironment()
        let value = try accountRuntimeAccount("component-account-A")
        account.account = value
        info = value.info
        manifest = PinkhaSpaceManifest(spaceId: "component-space", manifestObjectId: "component-manifest",
                                       createdAt: Date(timeIntervalSince1970: 0), updatedAt: Date(timeIntervalSince1970: 0))
        workspaceRelease = AccountRuntimeGate(open: !workspaceBlocked)
        bootstrapRelease = AccountRuntimeGate(open: !failFirstBootstrap)
        service = AccountRuntimeBootstrap(events: events, manifest: manifest, failFirst: failFirstBootstrap,
                                          release: bootstrapRelease)
        let events = events, gate = workspaceRelease, info = info
        manager = ActiveSpaceManager(
            acceptanceAccount: account, workspaceStorage: AccountRuntimeSpaces(events),
            objectTypes: AccountRuntimeTypes(events), properties: AccountRuntimeProperties(events),
            widgets: AccountRuntimeWidgets(events), recency: AccountRuntimeRecency(events),
            workspaceOpen: { spaceID in
                guard spaceID == info.accountSpaceId else { throw AccountRuntimeFixtureError.unexpectedCall }
                guard let binding = InvocationDispatchContext.binding else { throw AccountRuntimeFixtureError.missingOriginalBinding }
                try await binding.validateForOperation(named: "WorkspaceOpen")
                events.record("workspace.open")
                await gate.wait()
                return info
            }
        )
    }
    func startSelection() -> Task<AccountInfo?, any Error> {
        let manager = manager
        let task = Task { try await manager.setActiveSpace(spaceId: "component-space") }
        joins.append { _ = await task.result }
        return task
    }
    func run(_ body: @MainActor () async throws -> Void) async throws {
        let dependencies = PinkhaBootstrapHook.AcceptanceDependencies(stateManager: state, service: service)
        try await PinkhaBootstrapHook.$acceptanceDependencies.withValue(dependencies) {
            do { try await body(); await finish() }
            catch { await finish(); throw error }
        }
    }
    private func finish() async {
        workspaceRelease.open(); bootstrapRelease.open()
        for join in joins { await join() }
        await manager.stopSubscription()
        await account.editorWriteLifetime?.waitForOperationsToDrain()
    }
}
#endif
