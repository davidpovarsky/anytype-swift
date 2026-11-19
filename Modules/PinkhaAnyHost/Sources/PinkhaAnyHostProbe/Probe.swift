import Foundation
#if os(Windows)
import CRT
#elseif canImport(Darwin)
import Darwin
#else
import Glibc
#endif
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

enum ProbeError: Error { case usage, failed(String) }
func require(_ value: Bool, _ label: String) throws {
    guard value else { throw ProbeError.failed(label) }
}

@main
enum NativeHostProbe {
    static func main() async {
        do { try await run() }
        catch {
            // Synthetic fixture only; avoid dumping native responses or credentials.
            FileHandle.standardError.write(Data(("HOST_PROBE_FAILED: " + String(describing: error) + "\n").utf8))
            exit(1)
        }
    }

    static func run() async throws {
        let arguments = CommandLine.arguments
        guard arguments.count >= 4, let url = URL(string: arguments[1]) else { throw ProbeError.usage }
        let workspace = try AnyTorahWorkspace(accountID: arguments[3], spaceID: arguments[2])
        let nativeCAS = arguments.contains("--native-cas")
        let client = try AnyHTTPClient(baseURL: url, expectedAccountID: workspace.accountID)
        let owner = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        if arguments.contains("--torah-workflow") {
            guard arguments.contains("--allow-disposable-writes") else { throw ProbeError.usage }
            try await runNativeTorahWorkflowProbe(client: client, workspace: workspace, owner: owner)
            return
        }
        if arguments.contains("--creation-retry") {
            guard arguments.contains("--allow-disposable-writes") else { throw ProbeError.usage }
            try await runNativeCreationProbe(client: client, workspace: workspace, owner: owner)
            return
        }
        if arguments.contains("--properties") {
            guard arguments.contains("--allow-disposable-writes") else { throw ProbeError.usage }
            try await runNativePropertyProbe(client: client, workspace: workspace, owner: owner,
                fixture: PropertyProbeFixture(arguments: arguments))
            return
        }
        let store = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let spacePath = ["v1", "spaces", workspace.spaceID]
        let object = try await client.requestJSON(method: "POST", path: spacePath + ["objects"],
            body: .object(["type": .string("page"),
                "initialProperties": .object(["any": .object(["name": .string("בדיקת עורך Pinkha Any")])])]))
        let objectID = try object.requireString("objectId")
        let blocksPath = spacePath + ["objects", objectID, "editor", "editor_blocks", "blocks"]
        let parent = try await client.requestJSON(method: "POST", path: blocksPath,
            body: .object(["type": .string("paragraph"), "text": .string("**שלום**"),
                "style": .object(["future": .object(["keep": .bool(true)]),
                    "pinkhaWritingDirection": .string("rightToLeft")])]))
        guard let parentID = parent["recordIds"]?.array?.first?.string else { throw ProbeError.failed("parent id") }
        let child = try await client.requestJSON(method: "POST", path: blocksPath,
            body: .object(["type": .string("paragraph"), "text": .string("child"),
                "nav": .object(["parentId": .string(parentID)])]))
        guard let childID = child["recordIds"]?.array?.first?.string else { throw ProbeError.failed("child id") }

        var checks = try await owner.perform { lease -> [String] in
            var checks: [String] = []
            let initial = try await store.read(objectID: objectID, lease: lease)
            try require(initial.snapshot.depthFirstIDs == [parentID, childID], "native structural ordering")
            checks.append("native_bounded_tree_and_stable_ids")
            let text = try initial.snapshot.boundedText(selection: [parentID])
            try require(text.blocks.count == 1 && text.blocks[0].inlineMarkdown == "**שלום**", "Hebrew selected text")
            checks.append("selected_native_inline_markdown_exact_bytes")
            try require(initial.snapshot.blocks.first(where: { $0.id == parentID })?.direction == .rightToLeft, "RTL readback")
            checks.append("native_rtl_style_readback")
            let edit = try store.prepareTextEdit(initial, blockID: parentID, inlineMarkdown: "טקסט חדש")
            if nativeCAS {
                let receipt = try await store.apply(edit, lease: lease)
                try require(receipt.readback == .verifiedCurrent && receipt.undo != nil, "conditional native write receipt")
                checks.append("conditional_block_patch_verified_readback")
                do {
                    _ = try await store.apply(edit, lease: lease)
                    throw ProbeError.failed("stale block edit accepted")
                } catch AnyHostError.changedDocument {}
                checks.append("stale_block_edit_refused")
                guard let undo = receipt.undo else { throw ProbeError.failed("missing undo") }
                let undone = try await store.apply(undo, lease: lease)
                try require(undone.readback == .verifiedCurrent, "conditional undo")
                let restored = try await store.read(objectID: objectID, lease: lease)
                let restoredParent = restored.snapshot.blocks.first(where: { $0.id == parentID })
                try require(restoredParent?.text == "**שלום**" &&
                    restoredParent?.native["style"]?["future"]?["keep"]?.bool == true &&
                    restored.snapshot.depthFirstIDs == [parentID, childID], "undo retained native identity/style")
                checks.append("undo_preserves_block_children_unknown_styles")
                let style = try store.prepareWritingStyle(restored, blockID: parentID,
                    direction: .rightToLeft, alignment: .right)
                let styled = try await store.apply(style, lease: lease)
                try require(styled.readback == .verifiedCurrent && styled.undo != nil, "style receipt")
                checks.append("explicit_rtl_alignment_native_write")
                _ = try await client.requestJSON(method: "PATCH", path: blocksPath + [childID],
                    body: .object(["set": .object(["text": .string("remote child change")])]))
                guard let staleUndo = styled.undo else { throw ProbeError.failed("missing style undo") }
                do {
                    _ = try await store.apply(staleUndo, lease: lease)
                    throw ProbeError.failed("undo overwrote intervening edit")
                } catch AnyHostError.changedDocument {}
                checks.append("undo_refuses_intervening_nested_write")
            } else {
                do {
                    _ = try await store.apply(edit, lease: lease)
                    throw ProbeError.failed("stock engine accepted extension contract")
                } catch AnyEngineError.http(let status, _) where status == 400 {}
                let unchanged = try await store.read(objectID: objectID, lease: lease)
                try require(unchanged.nativeVersion == initial.nativeVersion &&
                            unchanged.snapshot.revision == initial.snapshot.revision, "stock refusal mutated document")
                checks.append("stock_engine_refuses_without_unconditional_fallback")
            }
            return checks
        }
        await owner.revokeAndDrain()
        do { _ = try await owner.perform { _ in true }; throw ProbeError.failed("closed session accepted operation") }
        catch AnyHostError.sessionClosed {}
        checks.append("closed_session_refuses_new_work")

        // Delete only the page allocated by this probe, after its leases drain.
        _ = try await client.requestJSON(method: "DELETE", path: spacePath + ["objects", objectID])
        checks.append("owned_synthetic_document_cleanup")
        let output: AnyJSON = .object(["status": .string("PASS"),
            "nativeConditionalExtension": .bool(nativeCAS),
            "checks": .array(checks.map(AnyJSON.string)),
            "count": .integer(Int64(checks.count))])
        print(String(decoding: try JSONEncoder().encode(output), as: UTF8.self))
    }
}
