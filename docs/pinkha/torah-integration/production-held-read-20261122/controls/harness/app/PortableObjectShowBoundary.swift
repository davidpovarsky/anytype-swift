import Foundation
import SwiftProtobuf
@testable import ProtobufMessages

enum PortableRPCError: Error, Sendable {
    case noDriver
    case noBinding
    case noResponse
}

actor PortableRPCSignal {
    private var isOpen: Bool
    private var waiters: [CheckedContinuation<Void, Never>] = []
    init(open: Bool = false) { isOpen = open }
    func wait() async {
        if isOpen { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func open() {
        isOpen = true
        let pending = waiters
        waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }
}

actor PortableObjectShowDriver {
    struct Record: Sendable {
        let request: Anytype_Rpc.Object.Show.Request
        let bindingIdentity: UUID
    }
    struct Exchange: Sendable {
        let wire: Data
        let retainsCompletion: Bool
    }
    let began = PortableRPCSignal()
    private let responseGate: PortableRPCSignal
    private let retainCompletion: Bool
    private let failure: (any Error)?
    private var responses: [Data]
    private var records: [Record] = []
    private var completions: [InvocationDispatchCompletion] = []

    init(responses: [Data], paused: Bool = false,
         retainCompletion: Bool = false, failure: (any Error)? = nil) {
        self.responses = responses
        self.responseGate = PortableRPCSignal(open: !paused)
        self.retainCompletion = retainCompletion
        self.failure = failure
    }

    func exchange(request: Anytype_Rpc.Object.Show.Request, bindingIdentity: UUID,
                  completion: InvocationDispatchCompletion) async throws -> Exchange {
        let actualRequest = try Anytype_Rpc.Object.Show.Request(serializedBytes: request.serializedData())
        records.append(Record(request: actualRequest, bindingIdentity: bindingIdentity))
        await began.open()
        await responseGate.wait()
        if let failure { throw failure }
        guard !responses.isEmpty else { throw PortableRPCError.noResponse }
        let wire = responses.removeFirst()
        if retainCompletion { completions.append(completion) }
        return Exchange(wire: wire, retainsCompletion: retainCompletion)
    }

    func releaseResponse() async { await responseGate.open() }
    func recordedRequests() -> [Record] { records }
    func retainedCompletionCount() -> Int { completions.count }
    func finishRetainedCompletions() {
        let pending = completions
        completions.removeAll()
        for completion in pending { completion.finish() }
    }
}

enum PortableObjectShowContext {
    @TaskLocal static var driver: PortableObjectShowDriver?
}

enum ClientCommands {
    static func objectShow(_ request: Anytype_Rpc.Object.Show.Request = .init()) -> PortableObjectShowInvocation {
        PortableObjectShowInvocation(request: request)
    }
}

struct PortableObjectShowInvocation: Sendable {
    let request: Anytype_Rpc.Object.Show.Request

    func invoke(qos: DispatchQoS.QoSClass) async throws -> Anytype_Rpc.Object.Show.Response {
        guard let driver = PortableObjectShowContext.driver else { throw PortableRPCError.noDriver }
        guard let binding = InvocationDispatchContext.binding else { throw PortableRPCError.noBinding }
        let permit = try await binding.prepare(messageName: "ObjectShow")
        let completion = try permit.begin()
        do {
            let exchange = try await driver.exchange(
                request: request, bindingIdentity: binding.contextIdentity, completion: completion
            )
            defer { if !exchange.retainsCompletion { completion.finish() } }
            return try Anytype_Rpc.Object.Show.Response(serializedBytes: exchange.wire)
        } catch {
            completion.markFailed()
            completion.finish()
            throw error
        }
    }
}
