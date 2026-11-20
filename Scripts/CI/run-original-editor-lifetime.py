#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("editor_boundary", Path(__file__).with_name("run-original-editor-boundary.py"))
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
BASELINE = "1c8058112d95cb1278f5746cc0ad3ae4565d0ddb"
PAGE = "Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/"
EDITOR = "Anytype/Sources/PresentationLayer/TextEditor/EditorPage/"
DOC = "Anytype/Sources/Models/Documents/Document/BaseDocument.swift"
OWNER = PAGE + "EditorDocumentWriteOwner.swift"
LIFETIME = PAGE + "EditorDocumentWriteLifetime.swift"
SESSION = PAGE + "PreparedEditorPageSession.swift"
ASSEMBLY = PAGE + "EditorPageModuleAssembly.swift"
VIEW = EDITOR + "EditorPageView.swift"
STATE = EDITOR + "EditorPageViewState.swift"
CONTAINER = EDITOR + "EditorSwiftUIViewContainer.swift"
TABLE_PROTOCOL = "Modules/Services/Sources/Services/BlockTableService/BlockTableService.swift"
TABLE_WRAPPER = "Anytype/Sources/ServiceLayer/Block/DocumentOwnedBlockTableService.swift"
TABLE_FIXTURE = "Scripts/CI/fixtures/original-editor-owned-tables.swift"
HOST_FIXTURE = "Scripts/CI/fixtures/original-editor-host-update.swift"
HOST_BASELINE = "ed250e6e926262a67f6c86f483802674c98f41f3"
TABLE_MODELS = ["Modules/Services/Sources/Models/Block/Common/BlockPosition.swift",
                "Modules/Services/Sources/Models/Common/BlocksSortType.swift"]
TABLE_BASELINE = "bc8be790e86876a014aa048e82c57157e13a62d2"
BLOCK_BASELINE = "076fc7c7b005de203ea0b4f1f3dd4807d62e0cec"
BLOCK_PROTOCOL = "Modules/Services/Sources/Services/BlockService/BlockServiceProtocol.swift"
BLOCK_ORIGINAL = "Modules/Services/Sources/Services/BlockService/BlockService.swift"
BLOCK_WRAPPER = "Anytype/Sources/ServiceLayer/Block/DocumentOwnedBlockService.swift"
BLOCK_FIXTURE = "Scripts/CI/fixtures/original-editor-owned-blocks.swift"
BLOCK_MODELS = ["Modules/Services/Sources/Models/Block/BlockInformation/BlockInformation.swift","Modules/Services/Sources/Models/Block/BlockInformation/BlockInformationMetadata.swift","Modules/Services/Sources/Models/Block/BlockInformation/MiddlewareColor.swift","Modules/Services/Sources/Models/Block/BlockContent/Content/BlockLink.swift","Modules/Services/Sources/Models/ObjectTypeUniqueKey.swift","Modules/Services/Sources/Models/Text/MarkupType.swift"]
BLOCK_POSITION = "Modules/ProtobufMessages/Sources/Protocol/Models/Anytype_Model_Block.Position.swift"
BLOCK_ALIGN = "Modules/ProtobufMessages/Sources/Protocol/Models/Anytype_Model_Block.Align.swift"
BLOCK_ALIASES = "Modules/Services/Sources/Models/Aliases.swift"
BLOCK_LAYOUT = "Modules/Services/Sources/Models/Common/LayoutAlignment.swift"
BLOCK_DETAILS = "Modules/Services/Sources/Models/Details/BundledDetails.swift"
BLOCK_READ_METHOD = "    /// Read only the original owned object/Space without requiring edit mode.\n    /// The same lifetime and pending lease still govern result delivery.\n    func performRead<Value: Sendable>(\n        contextId: String,\n        spaceId: String,\n        operation: @Sendable () async throws -> Value\n    ) async throws -> Value {\n        guard spaceId.utf8.elementsEqual(data.spaceId.utf8) else {\n            throw EditorDocumentWriteError.rejected(.wrongContext)\n        }\n        let lease = try admit(contextId: contextId, requiresEditing: false)\n        defer { finish(lease) }\n        let value = try await operation()\n        if let reason = rejection(contextId: contextId, requiresEditing: false) {\n            throw EditorDocumentWriteError.completedWithoutOwnership(reason)\n        }\n        guard pending.contains(lease) else {\n            throw EditorDocumentWriteError.completedWithoutOwnership(.invalidLease)\n        }\n        return value\n    }\n\n"
BLOCK_SESSION_REPLACEMENTS = [["Text/table/local-event","Text/block/table/local-event"],["                blockService: existing.blockService,","                blockService: DocumentOwnedBlockService(owner: owner, service: existing.blockService),"],["                blockService: services.blockActionHandler.blockService,","                blockService: DocumentOwnedBlockService(owner: owner, service: services.blockActionHandler.blockService),"],["            keyboardHandler: services.keyboardHandler,\n            blocksStateManager: services.blocksStateManager,","            keyboardHandler: .init(\n                blockService: DocumentOwnedBlockService(owner: owner, service: services.keyboardHandler.blockService),\n                keyboardInsertedBlocksStorage: services.keyboardHandler.keyboardInsertedBlocksStorage\n            ),\n            blocksStateManager: .init(\n                blockService: DocumentOwnedBlockService(owner: owner, service: services.blocksStateManager.blockService),\n                pasteboardService: services.blocksStateManager.pasteboardService,\n                documentsProvider: services.blocksStateManager.documentsProvider,\n                objectActionsService: services.blocksStateManager.objectActionsService,\n                toastPresenter: services.blocksStateManager.toastPresenter\n            ),"],["                blockService: services.blockBuilder.blockService","                blockService: DocumentOwnedBlockService(owner: owner, service: services.blockBuilder.blockService)"],["            viewModel: services.viewModel,","            viewModel: .init(\n                objectActionsService: services.viewModel.objectActionsService,\n                objectTypeProvider: services.viewModel.objectTypeProvider,\n                searchService: services.viewModel.searchService,\n                templatesSubscriptionService: services.viewModel.templatesSubscriptionService,\n                accountManager: services.viewModel.accountManager,\n                publishingService: services.viewModel.publishingService,\n                participantStorage: services.viewModel.participantStorage,\n                publishedUrlBuilder: services.viewModel.publishedUrlBuilder,\n                keyboardInsertedBlocksStorage: services.viewModel.keyboardInsertedBlocksStorage,\n                blockService: DocumentOwnedBlockService(owner: owner, service: services.viewModel.blockService)\n            ),"]]
BLOCK_MODEL_INPUTS = BLOCK_MODELS + [BLOCK_POSITION, BLOCK_ALIGN, BLOCK_ALIASES, BLOCK_LAYOUT, BLOCK_DETAILS]

BUNDLES = {
    "blockActionService": "Anytype/Sources/ServiceLayer/Block/BlockActionHandler/BlockActionService/BlockActionServiceDependencies.swift",
    "blockActionHandler": "Anytype/Sources/ServiceLayer/Block/BlockActionHandler/BlockActionHandlerDependencies.swift",
    "keyboardHandler": "Anytype/Sources/ServiceLayer/Block/BlockActionHandler/KeyboardActionHandler/KeyboardActionHandlerDependencies.swift",
    "blocksStateManager": EDITOR + "EditorPageBlocksStateManagerDependencies.swift",
    "blockBuilder": EDITOR + "Models/BlockViewModelBuilderDependencies.swift",
    "simpleTable": "Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/SimpleTable/SimpleTableServiceDependencies.swift",
    "slashMenu": "Anytype/Sources/PresentationLayer/TextEditor/AccessoryView/SlashMenu/Handler/SlashMenuActionHandlerDependencies.swift",
    "header": EDITOR + "Views/Header/Entities/ObjectHeaderViewModelDependencies.swift",
    "router": "Anytype/Sources/PresentationLayer/TextEditor/Routing/Editor/EditorRouterDependencies.swift",
    "viewModel": EDITOR + "EditorPageViewModelDependencies.swift",
}


def content(path, revision=None):
    if revision:
        raw = subprocess.check_output(["git", "show", revision + ":" + path], cwd=ROOT)
    else:
        absolute = ROOT / path
        raw = absolute.read_bytes() if absolute.exists() else subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT)
    return raw.decode("utf-8").replace("\r\n", "\n")


def digest(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def replace_once(source, old, new):
    BASE.require(source.count(old) == 1, "Expected one exact source region: " + old[:70])
    return source.replace(old, new)


HOST_UPDATE_GUARD = "        guard context.coordinator.permitsUpdate(\n            of: uiViewController, incomingController: viewController,\n            incomingSession: preparedSession\n        ) else { return }\n"
HOST_UPDATE_METHOD = "        /// Prepared hosts must retain the controller/session pair that attached.\n        /// The legacy nil-session path keeps its original update semantics.\n        func permitsUpdate(\n            of uiViewController: EditorPageController,\n            incomingController: EditorPageController,\n            incomingSession: PreparedEditorPageSession?\n        ) -> Bool {\n            guard session != nil || incomingSession != nil else { return true }\n            guard controller === uiViewController else { return false }\n            guard controller === incomingController, session === incomingSession else {\n                hostLease?.cancel()\n                session?.retire(controller: controller)\n                incomingSession?.rejectUnattachedHost(controller: incomingController)\n                return false\n            }\n            return true\n        }\n\n"
HOST_REJECT_METHOD = "    /// Reject only this bound owner's failed first host attempt. An owner\n    /// already attached elsewhere is not revoked by another host's update.\n    func rejectUnattachedHost(controller: AnyObject) {\n        guard !hostClaimed, boundController === controller else { return }\n        retire()\n    }\n\n"


def block_inverse(path, value):
    if path == OWNER and BLOCK_READ_METHOD in value:
        value = replace_once(value, BLOCK_READ_METHOD, "")
    if path == SESSION and "Text/block/table/local-event" in value:
        for before, after in BLOCK_SESSION_REPLACEMENTS:
            value = replace_once(value, after, before)
    return value


def block_source_preservation(report):
    rows = []
    for path in [OWNER, SESSION]:
        current, prior = content(path), content(path, BLOCK_BASELINE)
        BASE.require(block_inverse(path, current) == prior,
                     "Block boundary changed beyond exact read/slot injection: " + path)
        rows.append({"path": path, "parent": BLOCK_BASELINE,
            "parent_sha256": digest(prior), "candidate_sha256": digest(current),
            "exact_inverse_verified": True})
    original_inputs = [BLOCK_PROTOCOL, BLOCK_ORIGINAL, *BLOCK_MODEL_INPUTS,
                       *BUNDLES.values(), TABLE_WRAPPER]
    for path in original_inputs:
        value = content(path)
        BASE.require(value == content(path, BLOCK_BASELINE), "Original block/value/dependency changed: " + path)
        rows.append({"path": path, "git_lf_sha256": digest(value), "byte_identical_to_parent": True})
    def signatures(value):
        pattern = r"func\s+(\w+)\s*\(([\s\S]*?)\)\s*async\s+throws(?:\s*->\s*([^\n{]+))?"
        return [(name, re.sub(r"\s+", "", params), re.sub(r"\s+", "", result))
                for name, params, result in re.findall(pattern, value)]
    expected, actual = signatures(content(BLOCK_PROTOCOL)), signatures(content(BLOCK_WRAPPER))
    BASE.require(len(expected) == 18 and actual == expected, "Original block protocol signatures not preserved")
    report["block_source_preservation"] = rows
    report["block_original_method_signatures"] = expected
    before = content("Scripts/CI/fixtures/original-editor-lifetime.swift", BLOCK_BASELINE)
    current = content("Scripts/CI/fixtures/original-editor-lifetime.swift")
    expected_fixture = replace_once(before,
        "prepared.services.blockActionService.blockService === fixtureMarker",
        "prepared.services.blockActionService.objectActionService === fixtureMarker")
    expected_fixture = replace_once(expected_fixture,
        "prepared.services.blockBuilder.blockService === fixtureMarker",
        "prepared.services.blockBuilder.detailsService === fixtureMarker")
    BASE.require(current == expected_fixture, "Lifetime fixture changed beyond two retained-service references")
    report["prior_fixture_reference_evolution"] = {
        "one_control": "prepared_session_preserves_other_explicit_service_instances",
        "two_comparisons": ["blockActionService.objectActionService", "blockBuilder.detailsService"],
        "third_comparison_and_other_assertions_unchanged": True,
        "parent_sha256": digest(before), "current_sha256": digest(current)
    }


def host_inverse(path, value):
    if path == CONTAINER and HOST_UPDATE_GUARD in value:
        value = replace_once(value, HOST_UPDATE_GUARD, "")
        value = replace_once(value, HOST_UPDATE_METHOD, "")
    elif path == SESSION and HOST_REJECT_METHOD in value:
        value = replace_once(value, HOST_REJECT_METHOD, "")
    return value


def host_source_preservation(report):
    rows = []
    for path in [CONTAINER, SESSION]:
        value = content(path)
        before = content(path, HOST_BASELINE)
        BASE.require(host_inverse(path, block_inverse(path, value)) == before,
                     "Host source changed beyond the exact prepared identity guard: " + path)
        rows.append({"path": path, "parent": HOST_BASELINE,
            "parent_sha256": digest(before), "candidate_sha256": digest(value),
            "exact_inverse_verified": True})
    report["host_source_preservation"] = rows
    original_update = BASE.declaration(content(CONTAINER, HOST_BASELINE), "    func updateUIViewController(")
    actual_update = BASE.declaration(content(CONTAINER), "    func updateUIViewController(")
    if HOST_UPDATE_GUARD in actual_update:
        actual_update = replace_once(actual_update, HOST_UPDATE_GUARD, "")
    BASE.require(actual_update == original_update, "The three original update setters changed")
    report["original_update_body_sha256"] = digest(original_update)


def source_preservation(report, host_revision=None):
    source = content(DOC)
    inverse = replace_once(source,
        "BaseDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, @unchecked Sendable",
        "BaseDocument: BaseDocumentProtocol, @unchecked Sendable")
    inverse = replace_once(inverse, "    let editorWriteLifetime = EditorDocumentWriteLifetime(isAvailable: false)\n", "")
    inverse = replace_once(inverse,
        "        let closeLease = editorWriteLifetime.beginClosing()\n        defer { closeLease.cancel() }\n        try await objectLifecycleService.close(contextId: objectId, spaceId: spaceId)",
        "        try await objectLifecycleService.close(contextId: objectId, spaceId: spaceId)")
    inverse = replace_once(inverse,
        "        if updates.contains(.close) {\n            editorWriteLifetime.markUnavailable()\n",
        "        if updates.contains(.close) {\n")
    inverse = replace_once(inverse,
        "            if permissions.canEditBlocks && !newPermissios.canEditBlocks {\n                editorWriteLifetime.invalidate()\n            }\n", "")
    inverse = replace_once(inverse, "        editorWriteLifetime.confirmOpened()\n", "")
    BASE.require(inverse == content(DOC, BASELINE), "Original document changed beyond passive lifetime hooks")

    assembly = content(ASSEMBLY)
    signature = """    func buildStateModel(
        preparedSession: PreparedEditorPageSession,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?
    ) throws -> EditorPageViewState"""
    method = BASE.declaration(assembly.split("final class EditorPageModuleAssembly:", 1)[1], signature)
    inverse = replace_once(assembly, signature + "\n\n", "")
    inverse = replace_once(inverse, method + "\n\n", "")
    BASE.require(inverse == content(ASSEMBLY, BASELINE), "Original assembly/default overload changed")

    view = content(VIEW)
    inverse = replace_once(view,
        "EditorSwiftUIViewContainer(viewController: stateModel.viewController, preparedSession: stateModel.preparedSession)",
        "EditorSwiftUIViewContainer(viewController: stateModel.viewController)")
    BASE.require(inverse == content(VIEW, BASELINE), "Original editor view changed")

    state = content(STATE)
    bind = BASE.declaration(state, "    @MainActor\n    func bindPreparedSession(")
    inverse = replace_once(state, "    private(set) var preparedSession: PreparedEditorPageSession?\n", "")
    inverse = replace_once(inverse, bind + "\n\n", "")
    BASE.require(inverse == content(STATE, BASELINE), "Original state initialization changed")

    container = content(CONTAINER)
    owned_start = container.index("    var preparedSession: PreparedEditorPageSession? = nil\n")
    owned_end = container.index("    func makeUIViewController(", owned_start)
    owned = container[owned_start:owned_end]
    inverse = container[:owned_start] + "\n" + container[owned_end:]
    if HOST_UPDATE_GUARD in inverse:
        inverse = replace_once(inverse, HOST_UPDATE_GUARD, "")
    BASE.require(inverse == content(CONTAINER, BASELINE), "Original UIKit container make/update changed")
    report["preserved_original_files"] = [{
        "path": p, "baseline": BASELINE, "baseline_lf_sha256": digest(content(p, BASELINE)),
        "candidate_lf_sha256": digest(content(p)), "exact_inverse_verified": True
    } for p in [DOC, ASSEMBLY, VIEW, STATE, CONTAINER]]
    owner = content(OWNER)
    old_owner = content(OWNER, BASELINE)
    identical = ["    init(", "    func performMutation<", "    private func exactSourceMatches(",
                 "    private func finish(", "    private func notifyDrainIfNeeded("]
    report["owner_preserved_methods"] = []
    for token in identical:
        old = BASE.declaration(old_owner, token)
        new = BASE.declaration(owner, token)
        BASE.require(new == old, "An original owner method changed: " + token)
        report["owner_preserved_methods"].append({"declaration": token, "sha256": digest(old)})
    executed_container = content(CONTAINER, host_revision)
    report["host_container_under_test"] = {"revision": host_revision or "WORKTREE",
        "git_lf_sha256": digest(executed_container), "projection": "complete original coordinator and update methods; explicit context/UI value doubles"}
    return {
        "close": BASE.declaration(source, "    @MainActor\n    func close("),
        "setup_view": BASE.declaration(source, "    @MainActor\n    private func setupView("),
        "permissions": BASE.declaration(source, "    private func triggerUpdatePermissions("),
        "close_event": BASE.declaration(source, "        if updates.contains(.close)"),
        "assembly": method,
        "state_bind": bind,
        "coordinator": BASE.declaration(executed_container, "    @MainActor\n    final class Coordinator"),
        "make_coordinator": BASE.declaration(executed_container, "    func makeCoordinator("),
        "dismantle": BASE.declaration(executed_container, "    static func dismantleUIViewController("),
        "update": BASE.declaration(executed_container, "    func updateUIViewController("),
    }


def table_source_preservation(report):
    inverse = host_inverse(SESSION, block_inverse(SESSION, content(SESSION)))
    inverse = replace_once(inverse, "            blockActionHandler: .init(\n                blockService: services.blockActionHandler.blockService,\n                blockTableService: DocumentOwnedBlockTableService(\n                    owner: owner, service: services.blockActionHandler.blockTableService\n                ),\n                fileService: services.blockActionHandler.fileService,\n                objectService: services.blockActionHandler.objectService,\n                pasteboardBlockService: services.blockActionHandler.pasteboardBlockService,\n                bookmarkService: services.blockActionHandler.bookmarkService,\n                objectTypeProvider: services.blockActionHandler.objectTypeProvider\n            ),\n", "            blockActionHandler: services.blockActionHandler,\n")
    inverse = replace_once(inverse, "            blockBuilder: .init(\n                tableService: DocumentOwnedBlockTableService(\n                    owner: owner, service: services.blockBuilder.tableService\n                ),\n                detailsService: services.blockBuilder.detailsService,\n                audioSessionService: services.blockBuilder.audioSessionService,\n                objectTypeProvider: services.blockBuilder.objectTypeProvider,\n                pasteboardService: services.blockBuilder.pasteboardService,\n                blockService: services.blockBuilder.blockService\n            ),\n            simpleTable: .init(\n                tableService: DocumentOwnedBlockTableService(\n                    owner: owner, service: services.simpleTable.tableService\n                ),\n                pasteboardService: services.simpleTable.pasteboardService,\n                defaultObjectService: services.simpleTable.defaultObjectService,\n                typesService: services.simpleTable.typesService\n            ),\n", "            blockBuilder: services.blockBuilder,\n            simpleTable: services.simpleTable,\n")
    inverse = replace_once(inverse, "Text/table/local-event\n", "Text/local-event\n")
    BASE.require(inverse == content(SESSION, TABLE_BASELINE),
                 "Prepared session changed beyond exact table-owner injection")
    stable = [DOC, LIFETIME, OWNER, ASSEMBLY, VIEW, STATE, CONTAINER,
              TABLE_PROTOCOL] + TABLE_MODELS
    rows = []
    for path in stable:
        before = content(path, TABLE_BASELINE)
        after = content(path)
        BASE.require(before == host_inverse(path, block_inverse(path, after)), "An unrelated original input changed: " + path)
        rows.append({"path": path, "git_lf_sha256": digest(after),
                     "preservation": "byte_identical" if before == after else "exact_prepared_host_and_block_inverse"})
    report["table_preserved_inputs"] = rows
    report["table_prepared_session_exact_inverse"] = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swiftc", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--prepared-session-revision", choices=[TABLE_BASELINE],
                        help="Compile the immutable parent session for the explicit table-wiring RED control")
    parser.add_argument("--host-update-revision", choices=[HOST_BASELINE],
                        help="Compile the exact parent host/session for the explicit update-identity RED controls")
    parser.add_argument("--block-services-revision", choices=[BLOCK_BASELINE],
                        help="Compile the immutable parent session for the six explicit raw-block-slot RED controls")
    args = parser.parse_args()
    BASE.require(sum(bool(value) for value in [args.prepared_session_revision, args.host_update_revision, args.block_services_revision]) <= 1,
                 "Choose one historical source projection at a time")
    session_revision = args.prepared_session_revision or args.host_update_revision or args.block_services_revision
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "FAIL", "baseline": BASELINE, "native": "NOT_RUN", "apple_typecheck": "NOT_RUN",
        "scope": "Original18-method block protocol and owner/session forwarding;83 prior controls with two explicit retained-reference comparisons evolved;61 new block/read/lifetime controls; Foundation service boundaries",
        "boundary_doubles": ["UIKit controller/state and existing assembly output; exact update body uses explicit context and Int/Bool/String environment setter recorders", "Combine/document storage and setupView subscriptions/model/setter boundaries",
            "protobuf marks/enums and ObjectDetails/restriction payload values",
            "other retained service protocols are identity boundaries; BlockService and table protocols are complete originals; only other Factory resolvers omitted",
            "original generated Position/Align enum bodies use a protocol boundary matching pinned SwiftProtobuf Sendable inheritance; no generated runtime/serialization",
            "BlockContent/Google_Protobuf_Value/MentionObject/Emoji/CoverType are explicit payload boundaries; original BlockInformation/appearance/color/key/markup declarations preserved",
            "held service/event/close boundary actors", "locked unchecked-Sendable document probe"],
        "prepared_session_under_test": {
            "revision": session_revision or "WORKTREE",
            "git_lf_sha256": digest(content(SESSION, session_revision)),
            "mode": ("parent_unowned_table_slots" if args.prepared_session_revision else
                     "parent_host_update" if args.host_update_revision else
                     "parent_raw_block_slots" if args.block_services_revision else "candidate_owned_block_table_slots_and_host"),
        },
        "not_proven": ["Actual SwiftUI reuse; current only caller has stable StateObject and immutable controller", "Native original document event stream timing", "Apple view lifecycle execution",
            "all remaining routed writers", "actual account/Space services", "annotation persistence",
            "Maktabah consumer integration", "rollback or cancellation of already-admitted effects"],
    }
    try:
        snapshot_rows = []
        for path in [DOC, LIFETIME, OWNER, SESSION, ASSEMBLY, VIEW, STATE, CONTAINER,
                     TABLE_PROTOCOL, TABLE_WRAPPER, TABLE_FIXTURE, HOST_FIXTURE, *TABLE_MODELS,
                     BLOCK_PROTOCOL, BLOCK_ORIGINAL, BLOCK_WRAPPER, BLOCK_FIXTURE, *BLOCK_MODEL_INPUTS,
                     "Scripts/CI/run-original-editor-lifetime.py",
                     "Scripts/CI/fixtures/original-editor-lifetime.swift",
                     "AnytypeTests/Markdown/PreparedEditorLifetimeTests.swift",
                     "AnytypeTests/Markdown/EditorDocumentOwnedTableTests.swift",
                     "AnytypeTests/Markdown/EditorDocumentOwnedBlockTests.swift"]:
            value = content(path)
            destination = output / "input-snapshot" / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(value, encoding="utf-8", newline="\n")
            snapshot_rows.append({"path": path, "sha256": digest(value), "bytes": len(value.encode("utf-8"))})
        report["input_snapshot"] = snapshot_rows
        BASE.preserve(report)
        BASE.validate_writer_preservation(report)
        hooks = source_preservation(report, args.host_update_revision)
        table_source_preservation(report)
        host_source_preservation(report)
        block_source_preservation(report)
        sources = BASE.projected_sources(output, report)

        def add(name, source, path, projection="whole_file", source_revision=None):
            removed = re.findall(r"^import (?!Foundation$)([^\n]+)$", source, re.M)
            source = re.sub(r"^import (?!Foundation$)[^\n]+\n", "", source, flags=re.M)
            destination = output / (name + ".swift")
            destination.write_text(source, encoding="utf-8", newline="\n")
            sources.append(destination)
            report["compiled_sources"].append({
                "path": path, "projection": projection, "removed_imports": removed,
                "source_lf_sha256": digest(content(path, source_revision)) if path else None,
                "source_revision": source_revision,
                "compiled_sha256": digest(source),
            })

        table_protocol = BASE.declaration(content(TABLE_PROTOCOL), "public protocol BlockTableServiceProtocol:")
        add("BlockTableServiceProtocol", table_protocol + "\n", TABLE_PROTOCOL,
            "complete original public protocol; actual Heart implementation preserved but not executed")
        for path in TABLE_MODELS:
            add(Path(path).stem, content(path), path)
        table_helpers, table_controls = content(TABLE_FIXTURE).split("// BEGIN_OWNED_TABLE_CONTROLS\n", 1)


        add("BlockServiceProtocol", content(BLOCK_PROTOCOL), BLOCK_PROTOCOL)
        block_error = BASE.declaration(content(BLOCK_ORIGINAL), "public enum BlockServiceError:")
        add("BlockServiceError", block_error + "\n", BLOCK_ORIGINAL,
            "complete original error declaration; actual Heart implementation preserved but not executed")
        for path in BLOCK_MODELS:
            add(Path(path).stem, content(path), path)
        for path in [BLOCK_POSITION, BLOCK_ALIGN]:
            enum_body = BASE.declaration(content(path), "extension Anytype_Model_Block {")
            add(Path(path).stem, enum_body + "\n", path,
                "complete original generated enum body; serialization/runtime-name/version-check extensions omitted")
        aliases = content(BLOCK_ALIASES)
        block_fields = re.search(r"^public typealias BlockFields = .+$", aliases, re.M).group()
        add("BlockFields", block_fields + "\n", BLOCK_ALIASES, "exact original BlockFields typealias")
        layout = content(BLOCK_LAYOUT)
        layout_alias = re.search(r"^public typealias LayoutAlignment = .+$", layout, re.M).group()
        add("LayoutAlignment", layout_alias + "\n", BLOCK_LAYOUT,
            "exact original alias; retroactive Codable extension omitted because protobuf enum is co-compiled locally")
        details = BASE.declaration(content(BLOCK_DETAILS), "public enum BundledDetails:")
        add("BundledDetails", "import Foundation\n" + details + "\n", BLOCK_DETAILS,
            "complete original public enum; middleware serialization extension is not executed by denied creation")
        block_helpers, block_controls = content(BLOCK_FIXTURE).split("// BEGIN_OWNED_BLOCK_CONTROLS\n", 1)

        permissions = content("Anytype/Sources/Models/ObjectPermissions/ObjectPermissions.swift")
        permission_body = BASE.declaration(permissions, "struct ObjectPermissions:") + "\n" + BASE.declaration(permissions, "extension ObjectPermissions {") + "\n"
        add("ObjectPermissions", permission_body, "Anytype/Sources/Models/ObjectPermissions/ObjectPermissions.swift",
            "complete original struct and complete original permission initializer; ObjectDetails convenience extension omitted")
        for path in [
            "Anytype/Sources/Models/Documents/Document/EditBlocksPermission.swift",
            "Anytype/Sources/Models/Documents/Document/BaseDocumentUpdate.swift",
            "Anytype/Sources/Models/Documents/Events/Model/DocumentUpdate.swift",
            LIFETIME, OWNER, TABLE_WRAPPER, BLOCK_WRAPPER,
            "Anytype/Sources/ServiceLayer/Block/TextServiceHandler/DocumentOwnedTextService.swift",
            "Anytype/Sources/ServiceLayer/Block/DocumentOwnedLocalEventPublisher.swift",
            PAGE + "EditorPageServiceDependencies.swift", SESSION,
        ]:
            revision = session_revision if path == SESSION else None
            add(Path(path).stem, content(path, revision), path, source_revision=revision)

        prefix = content("Scripts/CI/fixtures/original-editor-boundary.swift").split("@main struct OriginalEditorBoundaryFixture", 1)[0]
        for old in ["struct ObjectPermissions: Sendable {}\n", "struct ObjectDetails: Sendable {}\n",
                    "enum BaseDocumentUpdate: Sendable { case fixture }\n"]:
            prefix = replace_once(prefix, old, "")

        prefix = replace_once(prefix, "struct BlockInformation: Sendable {}\n", "")
        prefix = replace_once(prefix, "protocol BlockServiceProtocol: AnyObject, Sendable {}\n", "")
        prefix = replace_once(prefix,
            "ServiceMarker: ObjectActionsServiceProtocol, BlockServiceProtocol, BookmarkServiceProtocol,",
            "ServiceMarker: ObjectActionsServiceProtocol, BookmarkServiceProtocol,")
        prefix = replace_once(prefix, 'let block = ServiceMarker("original-block")',
            'let block = OwnedBlockServiceProbe(label: "original-block")')
        table_helpers = replace_once(table_helpers,
            "public extension Anytype_Model_Block {\n    enum Position: Sendable { case none, top, bottom, left, right, inner, replace, unrecognized }\n}\n", "")

        ownership_helpers = content("Scripts/CI/fixtures/original-editor-ownership.swift").split("@main\nstruct OriginalEditorOwnershipFixture", 1)[0]
        extras = set()
        fields = {}
        projected_bundles = []
        for name, path in BUNDLES.items():
            value = content(path)
            fields[name] = re.findall(r"    let (\w+): any (\w+)", value)
            extras.update(protocol for field, protocol in fields[name])
            if name == "blockActionService":
                continue
            body = value[value.index("@MainActor"):value.index("    static func original()")]
            projected_bundles.append(body.rstrip() + "\n}\n")
            report.setdefault("dependency_field_projections", []).append({
                "path": path, "source_sha256": digest(value), "fields_sha256": digest(body),
                "omitted": "original Factory resolver; not exercised by prepared explicit dependencies",
            })
        defined = set(re.findall(r"\bprotocol (\w+)", prefix))
        extras.discard("TextServiceProtocol")
        extras.discard("BlockTableServiceProtocol")
        extras.discard("BlockServiceProtocol")
        missing = sorted(extras - defined)
        service_probes = "\n".join("@MainActor protocol " + name + ": AnyObject {}" for name in missing)
        service_probes += "\n@MainActor final class LifetimeServiceMarker: " + ", ".join(sorted(extras)) + " {}\n"
        service_probes += "@MainActor let fixtureMarker = LifetimeServiceMarker()\n"
        init_rows = []
        for name, field_values in fields.items():
            args_list = []
            for field, protocol in field_values:
                if protocol == "BlockTableServiceProtocol":
                    slot = {"blockActionHandler": "action", "blockBuilder": "builder", "simpleTable": "simple"}[name]
                    value = "ownedTables." + slot
                elif protocol == "BlockServiceProtocol":
                    slot = {"blockActionService": "action", "blockActionHandler": "handler",
                            "keyboardHandler": "keyboard", "blocksStateManager": "state",
                            "blockBuilder": "builder", "viewModel": "viewModel"}[name]
                    value = "ownedBlocks." + slot
                else:
                    value = "TextProbe()" if protocol == "TextServiceProtocol" else "fixtureMarker"
                args_list.append(field + ": " + value)
            init_rows.append("        " + name + ": .init(" + ", ".join(args_list) + ")")
        service_probes += "@MainActor func fixtureServices(events: any EditorLocalEventPublishing, tableServices: FixtureTableServices? = nil, blockServices: FixtureBlockServices? = nil) -> EditorPageServiceDependencies {\n"
        service_probes += "    let ownedTables = tableServices ?? FixtureTableServices()\n"
        service_probes += "    let ownedBlocks = blockServices ?? FixtureBlockServices()\n"
        service_probes += "    return .init(\n" + ",\n".join(init_rows) + ",\n        localEvents: events\n    )\n}\n"

        model_probes = r"""
extension String { var isNotEmpty: Bool { !isEmpty } }
enum ObjectRestriction: Sendable { case typeChange, delete, duplicate, template, details, relations, blocks }
struct PermissionLayout: Sendable {
    let isFileOrMedia = false, isChat = false, isList = false, isParticipant = false
    let haveIcon = true, haveCover = true, isEditorLayout = true
}
struct ObjectDetails: Sendable {
    var id: String = ""
    var isArchived = false
    var isTemplate = false
    var isObjectType = false
    var canMakeTemplate = true
    var resolvedLayoutValue = PermissionLayout()
}
final class CallbackRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    func add() { lock.lock(); count += 1; lock.unlock() }
    var value: Int { lock.lock(); defer { lock.unlock() }; return count }
}
"""
        add("BoundaryDoubles", prefix + ownership_helpers + model_probes + table_helpers + block_helpers + "\n".join(projected_bundles) + service_probes, None,
            "explicit Foundation boundary and dependency-field identity doubles")

        ui_probes = """
@MainActor final class EditorPageController {
    private(set) var updateEffects: [String] = []
    var additionalSafeAreaInsets = 0 {
        didSet { updateEffects.append("insets:" + String(additionalSafeAreaInsets)) }
    }
    func setPageNavigationHiddenBackButton(_ value: Bool) {
        updateEffects.append("hidden:" + String(value))
    }
    func setPinkhaHanlinRouteOwner(_ value: String?) {
        updateEffects.append("owner:" + (value ?? "nil"))
    }
}
@MainActor protocol EditorPageModuleOutput: AnyObject {}
@MainActor final class TorahEditorSession {}
@MainActor final class EditorPageViewState {
    let viewController = EditorPageController()
    private(set) var preparedSession: PreparedEditorPageSession?
""" + hooks["state_bind"] + """
}
@MainActor final class FixturePreparedAssembly {
    var data: EditorPageObject?
    var document: (any BaseDocumentProtocol)?
    var duringBuild: (@MainActor () -> Void)?
    func buildStateModel(data: EditorPageObject, preparedDocument: any BaseDocumentProtocol,
        services: EditorPageServiceDependencies, output: (any EditorPageModuleOutput)?,
        showHeader: Bool, torahSession: TorahEditorSession?) throws -> EditorPageViewState {
        self.data = data
        self.document = preparedDocument
        duringBuild?()
        return EditorPageViewState()
    }
""" + hooks["assembly"] + """
}
@MainActor struct FixturePreparedContainer {
    let viewController: EditorPageController
    var preparedSession: PreparedEditorPageSession? = nil
    let pageEditorAdditionalSafeAreaInsets = 91
    let pageNavigationHiddenBackButton = true
    let pinkhaHanlinRouteOwner: String? = "fixture-owner"
    struct Context { let coordinator: Coordinator }
""" + hooks["coordinator"] + "\n" + hooks["make_coordinator"] + "\n" + hooks["dismantle"] + "\n" + hooks["update"] + "\n}\n"
        add("OriginalPreparedAssemblyMethods", ui_probes, None,
            "exact original assembly/binding/coordinator/update bodies with explicit UIKit/context/environment/existing-assembly boundary doubles")
        fixture = content("Scripts/CI/fixtures/original-editor-lifetime.swift")
        close_event = "    @MainActor func emitCloseEventForFixture() {\n        let updates: [DocumentUpdate] = [.close]\n" + hooks["close_event"] + "\n    }\n"
        fixture = replace_once(fixture, "    // SOURCE_HOOKS", hooks["close"] + "\n" + hooks["setup_view"] + "\n" + hooks["permissions"] + "\n" + close_event)
        fixture = replace_once(fixture, "        let data = try JSONEncoder().encode(checks.checks)",
            "        try await exerciseOwnedTableServices(checks)\n        try await exerciseOriginalHostUpdates(checks)\n        try await exerciseOwnedBlockServices(checks)\n\n        let data = try JSONEncoder().encode(checks.checks)")
        fixture += "\n" + table_controls + "\n" + content(HOST_FIXTURE) + "\n" + block_controls
        add("ExecutedLifetimeFixture", fixture, "Scripts/CI/fixtures/original-editor-lifetime.swift",
            "prior83 lifetime/table/host controls with exactly two retained-reference comparisons evolved; original lifecycle/update bodies;61 new block controls")
        report["table_fixture_lf_sha256"] = digest(content(TABLE_FIXTURE))
        report["host_fixture_lf_sha256"] = digest(content(HOST_FIXTURE))
        report["block_fixture_lf_sha256"] = digest(content(BLOCK_FIXTURE))
        report["exact_method_projections"] = {name: {"sha256": digest(value), "bytes": len(value.encode())} for name, value in hooks.items()}

        executable = output / "original-editor-lifetime.exe"
        report["compile"] = BASE.run([args.swiftc, "-swift-version", "6", "-strict-concurrency=complete",
            "-parse-as-library", *map(str, sources), "-o", str(executable)], output, "compile", 180)
        BASE.require(report["compile"]["exit_code"] == 0, "Lifetime boundary did not compile")
        checks_path = output / "CHECKS.json"
        BASE.require(not checks_path.exists(), "Attempt already has a control report")
        report["execution"] = BASE.run([str(executable), str(checks_path)], output, "execution", 45)
        BASE.require(checks_path.is_file(), "Missing durable lifetime control report")
        raw_checks = checks_path.read_bytes()
        report["checks_sha256"] = digest(raw_checks)
        rows = json.loads(raw_checks)
        BASE.require(isinstance(rows, list) and rows and
            all(isinstance(row, dict) and isinstance(row.get("passed"), bool) and isinstance(row.get("name"), str)
                for row in rows), "Malformed lifetime control report")
        report.update(passed=sum(row["passed"] is True for row in rows),
                      failed=sum(row["passed"] is not True for row in rows), checks=rows)
        BASE.require(report["execution"]["exit_code"] == 0, "Lifetime controls failed")
        BASE.require(len(rows) == 144 and len({row["name"] for row in rows}) == 144
            and all(row["passed"] is True for row in rows), "Incomplete lifetime controls")
        report.update(status="PASS")
        syntax = []
        for path in [DOC, LIFETIME, OWNER, SESSION, ASSEMBLY, VIEW, STATE, CONTAINER, TABLE_WRAPPER, BLOCK_WRAPPER,
                     "AnytypeTests/Markdown/PreparedEditorLifetimeTests.swift",
                     "AnytypeTests/Markdown/EditorDocumentOwnedTableTests.swift",
                     "AnytypeTests/Markdown/EditorDocumentOwnedBlockTests.swift"]:
            entry = BASE.run([args.swiftc, "-frontend", "-parse", "-swift-version", "5", str(ROOT / path)],
                output, "parse-" + str(len(syntax) + 1), 30)
            entry["path"] = path
            syntax.append(entry)
            BASE.require(entry["exit_code"] == 0, "Source syntax failed: " + path)
        report["syntax_only"] = syntax
        return 0
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        return 1
    finally:
        (output / "RESULT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: report.get(k) for k in ["status", "error", "passed", "failed", "native", "apple_typecheck"]}))


if __name__ == "__main__":
    raise SystemExit(main())
