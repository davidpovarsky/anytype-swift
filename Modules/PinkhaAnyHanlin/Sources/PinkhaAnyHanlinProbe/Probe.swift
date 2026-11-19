import Foundation
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaAnyHanlin
import PinkhaAnyHost
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Explicit synthetic UI owner for a real-engine component proof. This does
/// not claim that a user saw an iOS permission sheet or a target block cell.
@MainActor
private final class ProbeUIOwner: AnyHanlinPresentationOwner {
    var scope: AnyHanlinPresentationScope
    var allow = false
    var mounted = true
    private var invalidate: (@Sendable () -> Void)?
    init(scope: AnyHanlinPresentationScope) { self.scope = scope }
    func currentScope() throws -> AnyHanlinPresentationScope {
        guard mounted else { throw HanlinHostError.staleContext }
        return scope
    }
    func install(session: HanlinHostSession, invalidate: @escaping @Sendable () -> Void) throws {
        self.invalidate = invalidate
    }
    func presentReadConsent(context: HanlinHostContext, answer: @escaping @MainActor (Bool) -> Void) throws {
        answer(allow)
    }
    func dismissPendingPrompts() {}
    func validateMounted(_ destination: HanlinHostDestination) throws {
        throw HanlinHostError.denied // This executable owns no real mounted UI.
    }
    func detach() { mounted = false; invalidate?() }
}

@main
struct PinkhaAnyHanlinProbe {
    @MainActor
    static func main() async throws {
        let args = CommandLine.arguments
        func argument(_ name: String) throws -> String {
            guard let index = args.firstIndex(of: name), args.indices.contains(index + 1) else {
                throw HanlinHostError.invalidArguments
            }
            return args[index + 1]
        }
        guard args.contains("--allow-disposable-writes"),
              let baseURL = URL(string: try argument("--base-url")) else { throw HanlinHostError.denied }
        let account = try argument("--account"), space = try argument("--space")
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let client = try AnyHTTPClient(baseURL: baseURL, expectedAccountID: account)
        let native = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let store = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let title = "בדיקת Hanlin Any " + UUID().uuidString
        let base = ["v1", "spaces", space]
        let objectID: String = try await native.perform { lease in
            let value = try await client.requestJSON(method: "POST", path: base + ["objects"],
                body: .object(["type": .string("page"), "initialProperties": .object([
                    "any": .object(["name": .string(title)])])]), authorize: { try await lease.validate() })
            let id = try value.requireString("objectId")
            _ = try await client.requestJSON(method: "POST",
                path: base + ["objects", id, "editor", "editor_blocks", "blocks"],
                body: .object(["type": .string("paragraph"), "text": .string("**שלום** _עולם_")]),
                authorize: { try await lease.validate() })
            return id
        }
        let read = try await native.perform { lease in try await store.read(objectID: objectID, lease: lease) }
        let owner = ProbeUIOwner(scope: .init(accountID: account, spaceID: space, sceneID: UUID(),
            ownerID: UUID(), document: read.snapshot, selection: []))
        let host = try AnyHanlinHost(native: native, documents: store, owner: owner, conversationID: UUID())
        var checks = ["native_fixture_created_and_read"]
        guard try await host.catalog(for: host.session.context).tools.isEmpty else { throw HanlinHostError.resultMismatch }
        checks.append("read_catalog_starts_without_consent")
        do {
            try await host.requestContextReadConsent()
            throw HanlinHostError.resultMismatch
        } catch HanlinHostError.denied { checks.append("denial_does_not_grant_read") }
        owner.allow = true
        try await host.requestContextReadConsent()
        let catalog = try await host.catalog(for: host.session.context)
        guard catalog.tools.count == 1, catalog.tools[0].writeGuarantee == .readOnly else {
            throw HanlinHostError.resultMismatch
        }
        checks.append("approved_current_scope_has_read_only_catalog")
        let invocation = try HanlinHostInvocation(request: .init(
            id: .init(validating: UUID().uuidString.lowercased()),
            logicalToolID: .init(providerInstanceID: .init(validating: "anytype.host"),
                                localToolID: .init(validating: "read-context-text")),
            aliasUsed: "anytype_read_context_text", descriptorRevision: .init(1),
            routingTableRevision: .init(1), arguments: .object([:]), origin: .assistantModel,
            deadline: .now.addingTimeInterval(25),
            limits: .init(timeoutMilliseconds: 25_000, maximumOutputBytes: 32_768)),
            session: host.session, runID: UUID(), step: 0, providerCallID: "synthetic-native-hanlin-probe",
            writeGuarantee: .readOnly)
        let result = try await host.execute(invocation) { _ in }
        guard result.effectState == .confirmedNoEffect,
              case .completed(let contents) = result.result.outcome,
              contents.count == 1, case .text(let encoded) = contents[0] else { throw HanlinHostError.resultMismatch }
        let snapshot = try JSONDecoder().decode(PinkhaHanlinTextSnapshot.self, from: Data(encoded.utf8))
        guard snapshot.objectReference == objectID, snapshot.spaceReference == space,
              snapshot.title.utf8.elementsEqual(title.utf8), snapshot.blocks.count == 1,
              snapshot.blocks[0].text.utf8.elementsEqual("שלום עולם".utf8) else { throw HanlinHostError.resultMismatch }
        checks.append("actual_native_document_returns_plain_hebrew_through_shared_SDK_router")
        guard case .completed(let metadata)? = host.metadataReceipt(for: invocation.request.id)?.result.outcome,
              metadata.isEmpty else { throw HanlinHostError.resultMismatch }
        checks.append("receipt_excludes_business_payload")
        do {
            _ = try await host.execute(invocation) { _ in }
            throw HanlinHostError.resultMismatch
        } catch HanlinHostError.duplicateInvocation { checks.append("duplicate_dispatch_refused") }
        let destination = HanlinHostDestination(context: host.session.context, objectReference: objectID,
                                               blockReference: snapshot.blocks[0].reference)
        guard !(try await host.open(destination)).presentationAcknowledged else { throw HanlinHostError.resultMismatch }
        checks.append("navigation_queue_is_not_UI_acknowledgment")
        do {
            _ = try host.acknowledgeMounted(destination)
            throw HanlinHostError.resultMismatch
        } catch HanlinHostError.denied { checks.append("unmounted_target_cannot_acknowledge") }
        let authority = try AnyHanlinCreationAuthority(client: client, workspace: workspace)
        let eligible = try await native.perform { lease in try await authority.inspect(lease: lease) }
        guard eligible.typeID == "page", eligible.permission == "owner" else { throw HanlinHostError.resultMismatch }
        checks.append("built_in_hidden_page_and_native_owner_are_eligible")
        owner.detach()
        do {
            _ = try await host.context(for: host.session)
            throw HanlinHostError.resultMismatch
        } catch HanlinHostError.staleContext { checks.append("presentation_detachment_revokes_scope") }
        await host.close()
        await native.revokeAndDrain()
        let evidence: AnyJSON = .object([
            "status": .string("PASS_REAL_ANY_HANLIN_READ_COMPONENT"),
            "scope": .string("real native HTTP and canonical Hanlin policy; synthetic UI owner; no native iOS prompt proof"),
            "checks": .array(checks.map(AnyJSON.string)),
            "fixtureCleanup": .string("synthetic page retained in disposable account for inspection")
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        FileHandle.standardOutput.write(try encoder.encode(evidence))
        FileHandle.standardOutput.write(Data([10]))
    }
}
