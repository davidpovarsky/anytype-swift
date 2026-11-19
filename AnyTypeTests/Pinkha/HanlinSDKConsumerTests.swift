@testable import PinkhaHanlinCore
import Foundation
import Testing
import HanlinAgentCore
import HanlinChatCore
import HanlinHostContracts
import HanlinPlatformContracts
@testable import Anytype

#if DEBUG
/// Real SDK dispatcher → real Anytype adapter. The native access fixture grants no production
/// authority; these cover the consumer envelope that the original direct-call tests did not use.
@Suite("Canonical Hanlin SDK consumer integration", .serialized)
@MainActor
struct HanlinSDKConsumerTests {
    @Test(arguments: [1_048_576, 8 * 1_048_576])
    func canonicalDispatcherBudgetsReachReadAndReplayOnlyReceipt(budget: Int) async throws {
        let h = try HanlinHostReadWriteTests().harness()
        let dispatcher = HanlinHostDispatcher(host: h.host)
        let catalog = try await h.host.catalog(for: h.access.session.context)
        let run = UUID()
        let limits = try budget == 1_048_576 ? HanlinToolInvocationLimits() : HanlinToolInvocationLimits(maximumOutputBytes: budget)
        let first = try await dispatcher.dispatch(alias: "anytype_read_context_text", argumentsJSON: "{}",
            providerCallID: "opaque/native-sdk/call", runID: run, step: 0,
            session: h.access.session, catalog: catalog, limits: limits)
        guard case .completed = first.result.outcome else { Issue.record("SDK envelope never reached host read"); return }
        #expect(first.effectState == .confirmedNoEffect)
        #expect(h.access.reads == 1)
        let replay = try await dispatcher.dispatch(alias: "anytype_read_context_text", argumentsJSON: "{}",
            providerCallID: "opaque/native-sdk/call", runID: run, step: 0,
            session: h.access.session, catalog: catalog, limits: limits)
        #expect(replay == first)
        #expect(h.access.reads == 1)
    }

    @Test func canonicalLargerEnvelopeDoesNotRelaxHostPayloadCap() async throws {
        let h = try HanlinHostReadWriteTests().harness()
        // Raw text is within 24 KiB, but its escaped JSON exceeds the host's 32 KiB cap.
        h.access.overrideSnapshot = .init(objectReference: "doc", spaceReference: "space", sourceRevision: "r1",
            title: "Fixture", blocks: [.init(reference: "K", text: String(repeating: "\u{0000}", count: 6_000))],
            coverage: "selectedTextBlocksOnly")
        let dispatcher = HanlinHostDispatcher(host: h.host)
        let catalog = try await h.host.catalog(for: h.access.session.context)
        let result = try await dispatcher.dispatch(alias: "anytype_read_context_text", argumentsJSON: "{}",
            providerCallID: "large-fixture", runID: UUID(), step: 0,
            session: h.access.session, catalog: catalog, limits: .init())
        #expect(h.access.reads == 1)
        guard case .failed = result.result.outcome else { Issue.record("Oversized host payload escaped"); return }
    }

    @Test func smallCallerBudgetRejectsPayloadAndKeepsOriginalReceipt() async throws {
        let h = try HanlinHostReadWriteTests().harness()
        let dispatcher = HanlinHostDispatcher(host: h.host)
        let catalog = try await h.host.catalog(for: h.access.session.context)
        do {
            _ = try await dispatcher.dispatch(alias: "anytype_read_context_text", argumentsJSON: "{}",
                providerCallID: "small-budget", runID: UUID(), step: 0,
                session: h.access.session, catalog: catalog, limits: .init(maximumOutputBytes: 128))
            Issue.record("The caller's smaller budget was ignored")
        } catch HanlinHostError.outputLimitExceeded {}
        #expect(h.access.reads == 1)
        #expect(await dispatcher.receipts(for: h.access.session).count == 1)
    }

    @Test func foreignIdempotencyKeyCannotBecomeAuthority() async throws {
        let h = try HanlinHostReadWriteTests().harness()
        let original = try HanlinHostAdapterTests().invocation(h.access)
        let invocation = try sdkEnvelope(original, key: "foreign-key")
        let result = try await h.host.execute(invocation) { _ in }
        #expect(result.effectState == .notDispatched)
        #expect(h.access.reads == 0)
    }

    @Test func canonicalEnvelopeCanPrepareOnlyExactConfirmedCreationShape() throws {
        let fixture = HanlinHostWriteTests()
        let original = try fixture.invocation(session: fixture.session())
        let canonical = try sdkEnvelope(original, key: original.request.id.rawValue)
        let plan = try PinkhaHanlinCreatePagePlan(invocation: canonical)
        #expect(plan.identity.invocationID == original.request.id)
        #expect(plan.identity.session == original.session)
        #expect(throws: PinkhaHanlinWriteError.invalidPlan) {
            try PinkhaHanlinCreatePagePlan(invocation: sdkEnvelope(original, key: "foreign-key"))
        }
    }

    @Test func providerConfigurationUsesCanonicalEngineContractAndRejectsEmbeddedCredentials() throws {
        let value = try PinkhaHanlinModelConfiguration.make(endpoint: "https://api.example.invalid/v1",
            model: "fixture-model", credential: "fixture-only-key")
        #expect(HanlinAISDKProviderFactory.descriptor(for: value).kind == .openAICompatible)
        #expect(value.supportsToolUse)
        for endpoint in ["http://api.example.invalid", "https://user:password@api.example.invalid",
                         "https://api.example.invalid?key=fixture", "https://api.example.invalid#fragment", "file:///tmp/fixture"] {
            #expect(throws: HanlinHostError.invalidArguments) {
                try PinkhaHanlinModelConfiguration.make(endpoint: endpoint, model: "fixture", credential: "fixture")
            }
        }
    }

    private func sdkEnvelope(_ value: HanlinHostInvocation, key: String) throws -> HanlinHostInvocation {
        let request = value.request
        return .init(request: .init(id: request.id, logicalToolID: request.logicalToolID,
            aliasUsed: request.aliasUsed, descriptorRevision: request.descriptorRevision,
            routingTableRevision: request.routingTableRevision, arguments: request.arguments,
            origin: .assistantModel, idempotencyKey: key, deadline: .now.addingTimeInterval(30), limits: try .init()),
            session: value.session, runID: value.runID, step: value.step, providerCallID: value.providerCallID,
            writeGuarantee: value.writeGuarantee, originalArgumentsJSON: try request.arguments.canonicalJSONData(),
            resultID: value.resultID)
    }
}
#endif
