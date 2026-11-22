import Foundation

final class SelectionGate: @unchecked Sendable {
    private struct State {
        var entered = false
        var released = false
        var waiters: [CheckedContinuation<Void, Never>] = []
    }
    private let state = AtomicStorage(State())
    var hasEntered: Bool { state.value.entered }
    func pause() async {
        await withCheckedContinuation { continuation in
            let resume = state.access { value -> Bool in
                value.entered = true
                if value.released { return true }
                value.waiters.append(continuation)
                return false
            }
            if resume { continuation.resume() }
        }
    }
    func release() {
        let values = state.access { value -> [CheckedContinuation<Void, Never>] in
            value.released = true
            let result = value.waiters
            value.waiters.removeAll()
            return result
        }
        for value in values { value.resume() }
    }
}

final class SelectionNativePause: @unchecked Sendable {
    private let state = AtomicStorage((entered: false, released: false))
    private let semaphore = DispatchSemaphore(value: 0)
    var hasEntered: Bool { state.value.entered }
    func block() throws {
        let released = state.access { value -> Bool in
            value.entered = true
            return value.released
        }
        if released { return }
        guard semaphore.wait(timeout: .now() + 30) == .success else {
            throw SelectionProbeError.nativePauseTimedOut
        }
    }
    func release() {
        let shouldSignal = state.access { value -> Bool in
            guard !value.released else { return false }
            value.released = true
            return true
        }
        if shouldSignal { semaphore.signal() }
    }
}

enum SelectionProbeError: Error, Sendable, Equatable {
    case missingDependency, missingBinding, missingPlan, plannedNativeFailure
    case nativePauseTimedOut, conditionTimedOut, missingManager
    case recordedAssertions([String])
}

enum Anytype_Model_Account {
    struct Info: Sendable {
        var homeObjectID = ""
        var archiveObjectID = ""
        var profileObjectID = ""
        var gatewayURL = ""
        var accountSpaceID = ""
        var spaceViewID = ""
        var widgetsID = ""
        var analyticsID = ""
        var deviceID = ""
        var networkID = ""
        var techSpaceID = ""
        var ethereumAddress = ""
        var spaceChatID = ""
        var metaDataKey = ""
    }
}

struct SelectionWorkspaceRequest: Sendable, Equatable {
    var spaceID = ""
    var withChat = false
    static func with(_ body: (inout Self) -> Void) -> Self {
        var value = Self()
        body(&value)
        return value
    }
}

struct SelectionWorkspaceResponse: Sendable {
    let info: Anytype_Model_Account.Info
}

final class SelectionRPCPlan: Sendable {
    let info: Anytype_Model_Account.Info
    let fail: Bool
    let beforeAdmission: SelectionGate?
    let duringBody: SelectionNativePause?
    let afterResponse: SelectionNativePause?
    init(
        info: Anytype_Model_Account.Info, fail: Bool = false,
        beforeAdmission: SelectionGate? = nil,
        duringBody: SelectionNativePause? = nil,
        afterResponse: SelectionNativePause? = nil
    ) {
        self.info = info
        self.fail = fail
        self.beforeAdmission = beforeAdmission
        self.duringBody = duringBody
        self.afterResponse = afterResponse
    }
    func release() {
        beforeAdmission?.release()
        duringBody?.release()
        afterResponse?.release()
    }
}

final class SelectionRPCProbe: @unchecked Sendable {
    struct State {
        var plans: [SelectionRPCPlan] = []
        var used: [SelectionRPCPlan] = []
        var requests: [SelectionWorkspaceRequest] = []
        var prepared = 0
        var admitted = 0
        var effects = 0
        var finished = 0
        var qos: [DispatchQoS.QoSClass] = []
    }
    let state = AtomicStorage(State())
    func enqueue(_ plan: SelectionRPCPlan) { state.access { $0.plans.append(plan) } }
    func take(_ request: SelectionWorkspaceRequest, qos: DispatchQoS.QoSClass) throws -> SelectionRPCPlan {
        let plan = state.access { value -> SelectionRPCPlan? in
            guard !value.plans.isEmpty else { return nil }
            let plan = value.plans.removeFirst()
            value.used.append(plan)
            value.requests.append(request)
            value.qos.append(qos)
            return plan
        }
        guard let plan else { throw SelectionProbeError.missingPlan }
        return plan
    }
    func releaseAll() {
        for plan in state.value.plans + state.value.used { plan.release() }
    }
}

struct SelectionWorkspaceInvocation: Sendable {
    let request: SelectionWorkspaceRequest
    let probe: SelectionRPCProbe
    func invoke(qos: DispatchQoS.QoSClass) async throws -> SelectionWorkspaceResponse {
        guard let binding = InvocationDispatchContext.binding else {
            throw SelectionProbeError.missingBinding
        }
        let plan = try probe.take(request, qos: qos)
        try Task.checkCancellation()
        let permit = try await binding.prepare(messageName: "WorkspaceOpen")
        probe.state.access { $0.prepared += 1 }
        await plan.beforeAdmission?.pause()
        let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<SelectionWorkspaceResponse, Error>) in
            DispatchQueue.global(qos: qos).async {
                do {
                    let completion = try permit.begin()
                    probe.state.access { $0.admitted += 1 }
                    var succeeded = false
                    defer {
                        if !succeeded { completion.markFailed() }
                        completion.finish()
                        probe.state.access { $0.finished += 1 }
                    }
                    try plan.duringBody?.block()
                    if plan.fail { throw SelectionProbeError.plannedNativeFailure }
                    probe.state.access { $0.effects += 1 }
                    succeeded = true
                    continuation.resume(returning: SelectionWorkspaceResponse(info: plan.info))
                    if let pause = plan.afterResponse {
                        do { try pause.block() } catch {
                            ProbeRegistry.assertions.access { $0.append("Selection completion hold timed out") }
                        }
                    }
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
        try Task.checkCancellation()
        return response
    }
}

enum ClientCommands {
    static func workspaceOpen(_ request: SelectionWorkspaceRequest) -> SelectionWorkspaceInvocation {
        .init(request: request, probe: SelectionRegistry.current().rpc)
    }
}

protocol ObjectTypeProviderProtocol: AnyObject, Sendable {
    func prepareData(spaceId: String) async
    func startSubscription(spaceId: String) async
    func stopSubscription() async
}
protocol PropertyDetailsStorageProtocol: AnyObject, Sendable {
    func prepareData(spaceId: String) async
    func startSubscription(spaceId: String) async
    func stopSubscription() async
}
protocol WidgetsObjectsStorageProtocol: AnyObject, Sendable {
    func prepare(info: AccountInfo) async
    func clear() async
}
protocol SpaceRecencyStorageProtocol: AnyObject, Sendable {
    func markInteraction(spaceId: String)
}

final class SelectionHelperProbe: ObjectTypeProviderProtocol, PropertyDetailsStorageProtocol,
                                  WidgetsObjectsStorageProtocol, SpaceRecencyStorageProtocol, Sendable {
    private struct State {
        var calls: [String] = []
        var holds: [String: [SelectionGate]] = [:]
        var allHolds: [SelectionGate] = []
    }
    private let state = AtomicStorage(State())
    var calls: [String] { state.value.calls }
    func hold(_ key: String, at gate: SelectionGate) {
        state.access { value in
            value.holds[key, default: []].append(gate)
            value.allHolds.append(gate)
        }
    }
    private func perform(_ key: String) async {
        let hold = state.access { value -> SelectionGate? in
            value.calls.append(key)
            guard var gates = value.holds[key], !gates.isEmpty else { return nil }
            let first = gates.removeFirst()
            value.holds[key] = gates
            return first
        }
        await hold?.pause()
    }
    func prepareData(spaceId: String) async { await perform("prepareData:" + spaceId) }
    func startSubscription(spaceId: String) async { await perform("start:" + spaceId) }
    func stopSubscription() async { await perform("stop") }
    func prepare(info: AccountInfo) async { await perform("widgets:" + info.accountSpaceId) }
    func clear() async { await perform("clear") }
    func markInteraction(spaceId: String) { state.access { $0.calls.append("recency:" + spaceId) } }
    func releaseAll() { for value in state.value.allHolds { value.release() } }
}

struct SelectionDependencies: Sendable {
    let spaces: SpaceViewsStorage
    let service: any WorkspaceServiceProtocol
    let rpc: SelectionRPCProbe
    let types: SelectionHelperProbe
    let properties: SelectionHelperProbe
    let widgets: SelectionHelperProbe
    let recency: SelectionHelperProbe
}
enum SelectionRegistry {
    static let dependencies = AtomicStorage<SelectionDependencies?>(nil)
    static let bootstrap = AtomicStorage<[String]>([])
    static let analytics = AtomicStorage(0)
    static func current() -> SelectionDependencies {
        guard let value = dependencies.value else { preconditionFailure("Selection fixture dependencies missing") }
        return value
    }
}
extension ProbeDependencies {
    var spaceViewsStorage: any SpaceViewsStorageProtocol { SelectionRegistry.current().spaces }
    var workspaceService: any WorkspaceServiceProtocol { SelectionRegistry.current().service }
    var objectTypeProvider: any ObjectTypeProviderProtocol { SelectionRegistry.current().types }
    var propertyDetailsStorage: any PropertyDetailsStorageProtocol { SelectionRegistry.current().properties }
    var widgetsObjectsStorage: any WidgetsObjectsStorageProtocol { SelectionRegistry.current().widgets }
    var spaceRecencyStorage: any SpaceRecencyStorageProtocol { SelectionRegistry.current().recency }
}
enum PinkhaBootstrapHook {
    static func handleSpaceActivated(spaceId: String) { SelectionRegistry.bootstrap.access { $0.append(spaceId) } }
}
final class AnytypeAnalytics: Sendable {
    private static let singleton = AnytypeAnalytics()
    static func instance() -> AnytypeAnalytics { singleton }
    func logSwitchSpace() { SelectionRegistry.analytics.access { $0 += 1 } }
}
extension Optional {
    var isNotNil: Bool { self != nil }
}

final class ReplacementWorkspaceService: WorkspaceServiceProtocol, Sendable {
    let calls = AtomicStorage(0)
    let shadowCalls = AtomicStorage(0)
    let info: AccountInfo
    init(info: AccountInfo) { self.info = info }
    func workspaceOpen(spaceId: String, withChat: Bool) async throws -> AccountInfo {
        calls.access { $0 += 1 }
        return info
    }
    func workspaceOpenForOriginalSelection(spaceId: String) async throws -> AccountInfo {
        shadowCalls.access { $0 += 1 }
        return info
    }
}

func selectionInfo(_ space: String = "space-A", view: String = "native-view-A",
                   tech: String = "actual-technical-space") -> Anytype_Model_Account.Info {
    var value = Anytype_Model_Account.Info()
    value.homeObjectID = "native-home"
    value.archiveObjectID = "native-archive"
    value.profileObjectID = "native-profile"
    value.gatewayURL = "native-gateway"
    value.accountSpaceID = space
    value.spaceViewID = view
    value.widgetsID = "native-widgets"
    value.analyticsID = "native-analytics"
    value.deviceID = "native-device"
    value.networkID = "native-network"
    value.techSpaceID = tech
    value.ethereumAddress = "native-address"
    value.spaceChatID = "native-chat"
    value.metaDataKey = "native-metadata"
    return value
}

@MainActor
final class SelectionFixture {
    let account: AccountManager
    let spaces: SpaceViewsStorage
    let transport: SpaceSubscriptionProbe
    let rpc: SelectionRPCProbe
    let types = SelectionHelperProbe()
    let properties = SelectionHelperProbe()
    let widgets = SelectionHelperProbe()
    let recency = SelectionHelperProbe()
    var manager: ActiveSpaceManager?
    private let dependencies: ProbeDependencies

    init(views: [SpaceView] = [SpaceView(), SpaceView(id: "native-view-B", targetSpaceId: "space-B")],
         service: (any WorkspaceServiceProtocol)? = nil) {
        let account = AccountManager()
        account.account = AccountData(id: "actual-account", info: selectionInfo().asModel)
        let transport = SpaceSubscriptionProbe(views)
        let dependencies = ProbeDependencies(
            subscriptionStorageProvider: ProbeProvider(participant: ParticipantSubscriptionProbe([]), space: transport),
            accountManager: account,
            spaceViewsSubscriptionBuilder: ProbeSpaceBuilder(),
            serverConfigurationStorage: ProbeServerConfigurationStorage()
        )
        ProbeRegistry.dependencies.value = dependencies
        self.dependencies = dependencies
        self.account = account
        self.transport = transport
        spaces = SpaceViewsStorage()
        rpc = SelectionRPCProbe()
        SelectionRegistry.dependencies.value = SelectionDependencies(
            spaces: spaces, service: service ?? WorkspaceService(), rpc: rpc,
            types: types, properties: properties, widgets: widgets, recency: recency
        )
        SelectionRegistry.bootstrap.value = []
        SelectionRegistry.analytics.value = 0
        manager = ActiveSpaceManager()
    }
    func start() async { await spaces.startSubscription() }
    func ownedManager() throws -> ActiveSpaceManager {
        guard let manager else { throw SelectionProbeError.missingManager }
        return manager
    }
    func enqueue(_ info: Anytype_Model_Account.Info = selectionInfo(),
                 fail: Bool = false, before: SelectionGate? = nil,
                 body: SelectionNativePause? = nil, after: SelectionNativePause? = nil) {
        rpc.enqueue(.init(info: info, fail: fail, beforeAdmission: before,
                          duringBody: body, afterResponse: after))
    }
    func releaseAll() {
        rpc.releaseAll()
        types.releaseAll()
        properties.releaseAll()
        widgets.releaseAll()
        recency.releaseAll()
    }
    func stop() async throws {
        releaseAll()
        await manager?.stopSubscription()
        await spaces.stopSubscription()
        let assertions = ProbeRegistry.assertions.value
        guard assertions.isEmpty else { throw SelectionProbeError.recordedAssertions(assertions) }
    }
}
