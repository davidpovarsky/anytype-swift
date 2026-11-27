import Foundation
import Testing
import AI_Hanlin
import HanlinAgentCore
import HanlinChatCore
import HanlinHostContracts
import HanlinPlatformContracts

/// Actual original component tests. Core entries below are metadata fixtures;
/// no fake MCP transport, script runtime, provider, or dispatch loop is installed.
@MainActor
@Suite("Original assistant component lifecycle", .serialized)
struct HanlinAssistantComponentTests {
    @MainActor private final class Validity {
        var isCurrent = true
        func validate() throws {
            guard isCurrent else { throw HanlinHostError.staleContext }
        }
    }

    private func configuration() -> HanlinApplicationRuntimeConfiguration {
        .applicationSupport(appIdentifier: Bundle.main.bundleIdentifier ?? "hanlin.component.tests")
    }

    private func service(conversation: UUID? = nil) throws -> HanlinAssistantServices {
        try .sharedRuntime(runtimeConfiguration: configuration(), availableTools: { [] },
            validateConversation: { id in
                if let conversation, id != conversation { throw HanlinHostError.staleContext }
            })
    }

    private func identity() throws -> HanlinHostSession {
        .init(conversationID: UUID(), context: .init(
            namespace: try .init(app: "hanlin.component.tests", account: "test-account",
                                 workspace: "test-workspace", space: "test-space"),
            sceneID: UUID(), generation: UUID(), sourceRevision: "original-source-1"))
    }

    private func host(_ identity: HanlinHostSession, validity: Validity = Validity()) throws
        -> HanlinAssistantConversationHost {
        try service(conversation: identity.conversationID).makeConversationHost(identity: identity,
            validateCurrent: { try validity.validate() }, consent: HanlinAppToolConsent())
    }

    private func catalog(_ identity: HanlinHostSession, alias: String? = nil) throws -> HanlinHostCatalog {
        var tools: [HanlinHostTool] = []
        if let alias {
            let logical = try HanlinLogicalToolID(providerInstanceID: .init(validating: "unit.original.core"),
                localToolID: .init(validating: "library.lookup"))
            let schema = Data(#"{"type":"object","properties":{},"additionalProperties":false}"#.utf8)
            let descriptor = try HanlinToolDescriptor(logicalID: logical, descriptorRevision: .init(1),
                owner: .system, title: .init(["en": "Fixture concordance lookup"]),
                summary: .init(["en": "Search the supplied host concordance catalog"]),
                inputSchema: .decodeCanonicalJSON(schema, defaultDialect: .draft2020_12),
                risk: .read, presentation: .init())
            tools = [.init(route: .init(alias: alias, logicalToolID: logical, descriptorRevision: descriptor.descriptorRevision),
                descriptor: descriptor, writeGuarantee: .readOnly, originalInputSchemaJSON: schema)]
        }
        return .init(apiVersion: .init(major: 1, minor: 1), revision: .init(71),
                     context: identity.context, tools: tools)
    }

    private func invocation(_ host: HanlinAssistantConversationHost, alias: String, json: String,
                            portable: HanlinJSONValue? = nil) async throws -> HanlinHostInvocation {
        let current = try await host.catalog(for: host.identity.context)
        let tool = try #require(current.tools.first { $0.route.alias == alias })
        let bytes = Data(json.utf8)
        let request = try HanlinToolInvocationRequest(id: .init(validating: UUID().uuidString.lowercased()),
            logicalToolID: tool.route.logicalToolID, aliasUsed: alias,
            descriptorRevision: tool.route.descriptorRevision, routingTableRevision: current.revision,
            arguments: portable ?? HanlinJSONValue.decodeCanonicalJSON(bytes), origin: .assistantModel,
            deadline: Date().addingTimeInterval(30), limits: .init())
        return .init(request: request, session: host.identity, runID: UUID(), step: 0,
            providerCallID: UUID().uuidString, writeGuarantee: tool.writeGuarantee,
            originalArgumentsJSON: bytes)
    }

    private func text(_ result: HanlinHostExecutionResult) throws -> String {
        guard case .completed(let parts) = result.result.outcome else {
            Issue.record("Original read did not complete: \(result.result.outcome)")
            throw HanlinHostError.invalidRecord
        }
        return parts.compactMap { if case .text(let value) = $0 { value } else { nil } }.joined()
    }

    @Test func multipleFacadesShareTheOriginalRuntimeAndKeepConversationValidation() async throws {
        let firstID = UUID(), secondID = UUID()
        let first = try service(conversation: firstID)
        let second = try service(conversation: secondID)
        _ = try await first.mcp.selectedServers(for: firstID)
        _ = try await second.mcp.selectedServers(for: secondID)
        do {
            _ = try await first.mcp.selectedServers(for: secondID)
            Issue.record("A second facade must not replace the first conversation validator.")
        } catch HanlinHostError.staleContext {} catch { throw error }
        let incompatible = HanlinApplicationRuntimeConfiguration(
            directory: FileManager.default.temporaryDirectory.appending(path: UUID().uuidString),
            mcpSecretService: "unit.other.mcp", environmentSecretService: "unit.other.runtime")
        do {
            _ = try HanlinAssistantServices.sharedRuntime(runtimeConfiguration: incompatible,
                availableTools: { [] }, validateConversation: { _ in })
            Issue.record("A live original runtime must not be replaced by another configuration.")
        } catch HanlinApplicationError.incompatibleRuntimeConfiguration {} catch { throw error }
        _ = try await first.mcp.selectedServers(for: firstID)
    }

    @Test func originalToolSearchUsesTheActualSuppliedCoreCatalog() async throws {
        let identity = try identity(), host = try host(identity)
        defer { host.revoke() }
        try await host.beginRequest(hostCatalog: catalog(identity, alias: "unit_core_concordance"))
        let prepared = try await host.prepareStep(0, session: identity)
        #expect(prepared.activeAliases.contains("unit_core_concordance"))
        let ownCatalog = try await host.catalog(for: identity.context)
        #expect(!ownCatalog.tools.contains { $0.route.alias == "unit_core_concordance" })
        let call = try await invocation(host, alias: ToolSearchTool.toolName, json: #"{"query":"concordance"}"#)
        let result = try await host.execute(call, progress: { _ in })
        #expect(result.effectState == .confirmedNoEffect)
        #expect(try text(result).contains("unit_core_concordance"))
        #expect(try text(result).contains("Fixture concordance lookup"))
    }

    @Test func originalDispatchRejectsInvalidRawSchemaAndForgedProjection() async throws {
        let identity = try identity(), host = try host(identity)
        defer { host.revoke() }
        try await host.beginRequest(hostCatalog: catalog(identity))
        let invalid = try await invocation(host, alias: ToolSearchTool.toolName, json: #"{"query":17}"#)
        let invalidResult = try await host.execute(invalid, progress: { _ in })
        #expect(invalidResult.effectState == .notDispatched)
        if case .failed(let error) = invalidResult.result.outcome { #expect(error.code == .invalidArguments) }
        else { Issue.record("Invalid original schema was accepted.") }
        let forged = try await invocation(host, alias: ToolSearchTool.toolName, json: #"{"query":"original"}"#,
            portable: .object(["query": .string("changed")]))
        let forgedResult = try await host.execute(forged, progress: { _ in })
        #expect(forgedResult.effectState == .notDispatched)
        if case .failed(let error) = forgedResult.result.outcome { #expect(error.code == .schemaProjectionWidensInput) }
        else { Issue.record("A forged portable projection was accepted.") }
    }

    @Test func originalResultHistorySurvivesRequestFinishAndReconstruction() async throws {
        let identity = try identity()
        _ = try service()
        // A real existing original result is seeded before the host opens it.
        let existing = AssistantCapabilitySession(chatID: identity.conversationID.uuidString).resultStore
        defer { existing.clear() }
        let payload = String(repeating: "מקור עברי — original result\n", count: 1000)
        let reference = try #require(existing.store(payload))
        let host = try host(identity)
        defer { host.revoke() }
        for _ in 0..<2 {
            try await host.beginRequest(hostCatalog: catalog(identity))
            let json = "{\"reference\":\"\(reference)\",\"offset\":0,\"limit\":1024}"
            let call = try await invocation(host, alias: ReadToolResultTool.toolName, json: json)
            let result = try await host.execute(call, progress: { _ in })
            #expect(result.effectState == .confirmedNoEffect)
            #expect(try text(result).contains("מקור עברי"))
            host.finishRequest()
            #expect(try await host.catalog(for: identity.context).tools.isEmpty)
        }
        #expect(existing.fullPayload(for: reference) == payload)
    }

    @Test func duplicateAliasFailureDoesNotPoisonTheNextOriginalRequest() async throws {
        let identity = try identity(), host = try host(identity)
        defer { host.revoke() }
        do {
            try await host.beginRequest(hostCatalog: catalog(identity, alias: ToolSearchTool.toolName))
            Issue.record("A foreign Core alias must not replace an original meta tool.")
        } catch HanlinHostError.duplicateAlias {} catch { throw error }
        #expect(try await host.catalog(for: identity.context).tools.isEmpty)
        try await host.beginRequest(hostCatalog: catalog(identity))
        #expect(try await host.prepareStep(0, session: identity).activeAliases.contains(ToolSearchTool.toolName))
    }

    @Test func originalPendingConsentIsCancelledBeforeAnySkillDispatch() async throws {
        let identity = try identity(), host = try host(identity)
        defer { host.revoke() }
        try await host.beginRequest(hostCatalog: catalog(identity))
        let skillID = try HanlinSkillID(validating: "unit_consent_" + UUID().uuidString.lowercased())
        // In-memory catalog fixture has no executable resource. This case must
        // stop at the real original consent boundary and never invoke a runtime.
        HanlinSkillCatalog.shared.register(skill: try .init(id: skillID, title: "Consent fixture",
            summary: "Original consent cancellation fixture", instructions: .inline("Fixture only")))
        let raw = "{\"skill_id\":\"\(skillID.rawValue)\",\"relative_path\":\"scripts/never-dispatched.js\"}"
        let call = try await invocation(host, alias: "execute_skill_resource", json: raw)
        let operation = Task { @MainActor in try await host.execute(call, progress: { _ in }) }
        defer { operation.cancel() }
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(5))
        while host.consent.pending == nil, clock.now < deadline {
            try await Task.sleep(for: .milliseconds(10))
        }
        let request = try #require(host.consent.pending)
        #expect(request.remembersDecision)
        #expect(request.originalArgumentsJSON == Data(raw.utf8))
        host.finishRequest()
        let result = try await operation.value
        #expect(result.effectState == .notDispatched)
        #expect(host.consent.pending == nil)
        // A late Allow from a retained presentation cannot reopen consent.
        host.consent.answer(id: request.id, allowed: true)
        #expect(host.consent.pending == nil)
        try await host.beginRequest(hostCatalog: catalog(identity))
    }

    @Test func changedAndRevokedOwnersCannotReuseAnOriginalPreparedHost() async throws {
        let identity = try identity(), validity = Validity()
        let host = try host(identity, validity: validity)
        try await host.beginRequest(hostCatalog: catalog(identity))
        let call = try await invocation(host, alias: ToolSearchTool.toolName, json: #"{"query":"anything"}"#)
        validity.isCurrent = false
        let result = try await host.execute(call, progress: { _ in })
        #expect(result.effectState == .notDispatched)
        host.revoke()
        validity.isCurrent = true
        do {
            try await host.beginRequest(hostCatalog: catalog(identity))
            Issue.record("Revoking the original owner must be permanent.")
        } catch HanlinHostError.staleContext {} catch { throw error }
        do {
            _ = try host.capabilityCatalog()
            Issue.record("A retained management sheet must not recover a revoked owner.")
        } catch HanlinHostError.staleContext {} catch { throw error }
    }
}
