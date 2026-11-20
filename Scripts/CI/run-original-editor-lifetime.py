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
TABLE_MODELS = ["Modules/Services/Sources/Models/Block/Common/BlockPosition.swift",
                "Modules/Services/Sources/Models/Common/BlocksSortType.swift"]
TABLE_BASELINE = "bc8be790e86876a014aa048e82c57157e13a62d2"
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


def source_preservation(report):
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
    return {
        "close": BASE.declaration(source, "    @MainActor\n    func close("),
        "setup_view": BASE.declaration(source, "    @MainActor\n    private func setupView("),
        "permissions": BASE.declaration(source, "    private func triggerUpdatePermissions("),
        "close_event": BASE.declaration(source, "        if updates.contains(.close)"),
        "assembly": method,
        "state_bind": bind,
        "coordinator": BASE.declaration(container, "    @MainActor\n    final class Coordinator"),
        "make_coordinator": BASE.declaration(container, "    func makeCoordinator("),
        "dismantle": BASE.declaration(container, "    static func dismantleUIViewController("),
    }


def table_source_preservation(report):
    inverse = content(SESSION)
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
        BASE.require(before == after, "An unrelated original input changed: " + path)
        rows.append({"path": path, "git_lf_sha256": digest(after)})
    report["table_preserved_inputs"] = rows
    report["table_prepared_session_exact_inverse"] = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swiftc", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--prepared-session-revision", choices=[TABLE_BASELINE],
                        help="Compile the immutable parent session for the explicit table-wiring RED control")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "FAIL", "baseline": BASELINE, "native": "NOT_RUN", "apple_typecheck": "NOT_RUN",
        "scope": "Actual document/session lifetime and owned table wrapper with all three prepared table slots; exact original source lifecycle hooks and table protocol/models; Foundation-held boundaries",
        "boundary_doubles": ["UIKit controller/state and existing assembly output", "Combine/document storage and setupView subscriptions/model/setter boundaries",
            "protobuf marks/enums and ObjectDetails/restriction payload values",
            "empty service protocols for retained dependency field identity; original factories omitted",
            "held service/event/close boundary actors", "locked unchecked-Sendable document probe"],
        "prepared_session_under_test": {
            "revision": args.prepared_session_revision or "WORKTREE",
            "git_lf_sha256": digest(content(SESSION, args.prepared_session_revision)),
            "mode": "parent_unowned_table_slots" if args.prepared_session_revision else "candidate_owned_table_slots",
        },
        "not_proven": ["Native original document event stream timing", "Apple view lifecycle execution",
            "all remaining routed writers", "actual account/Space services", "annotation persistence",
            "Maktabah consumer integration", "rollback or cancellation of already-admitted effects"],
    }
    try:
        snapshot_rows = []
        for path in [DOC, LIFETIME, OWNER, SESSION, ASSEMBLY, VIEW, STATE, CONTAINER,
                     TABLE_PROTOCOL, TABLE_WRAPPER, TABLE_FIXTURE, *TABLE_MODELS,
                     "Scripts/CI/run-original-editor-lifetime.py",
                     "Scripts/CI/fixtures/original-editor-lifetime.swift",
                     "AnytypeTests/Markdown/PreparedEditorLifetimeTests.swift",
                     "AnytypeTests/Markdown/EditorDocumentOwnedTableTests.swift"]:
            value = content(path)
            destination = output / "input-snapshot" / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(value, encoding="utf-8", newline="\n")
            snapshot_rows.append({"path": path, "sha256": digest(value), "bytes": len(value.encode("utf-8"))})
        report["input_snapshot"] = snapshot_rows
        BASE.preserve(report)
        BASE.validate_writer_preservation(report)
        hooks = source_preservation(report)
        table_source_preservation(report)
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

        permissions = content("Anytype/Sources/Models/ObjectPermissions/ObjectPermissions.swift")
        permission_body = BASE.declaration(permissions, "struct ObjectPermissions:") + "\n" + BASE.declaration(permissions, "extension ObjectPermissions {") + "\n"
        add("ObjectPermissions", permission_body, "Anytype/Sources/Models/ObjectPermissions/ObjectPermissions.swift",
            "complete original struct and complete original permission initializer; ObjectDetails convenience extension omitted")
        for path in [
            "Anytype/Sources/Models/Documents/Document/EditBlocksPermission.swift",
            "Anytype/Sources/Models/Documents/Document/BaseDocumentUpdate.swift",
            "Anytype/Sources/Models/Documents/Events/Model/DocumentUpdate.swift",
            LIFETIME, OWNER, TABLE_WRAPPER,
            "Anytype/Sources/ServiceLayer/Block/TextServiceHandler/DocumentOwnedTextService.swift",
            "Anytype/Sources/ServiceLayer/Block/DocumentOwnedLocalEventPublisher.swift",
            PAGE + "EditorPageServiceDependencies.swift", SESSION,
        ]:
            revision = args.prepared_session_revision if path == SESSION else None
            add(Path(path).stem, content(path, revision), path, source_revision=revision)

        prefix = content("Scripts/CI/fixtures/original-editor-boundary.swift").split("@main struct OriginalEditorBoundaryFixture", 1)[0]
        for old in ["struct ObjectPermissions: Sendable {}\n", "struct ObjectDetails: Sendable {}\n",
                    "enum BaseDocumentUpdate: Sendable { case fixture }\n"]:
            prefix = replace_once(prefix, old, "")
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
                else:
                    value = "TextProbe()" if protocol == "TextServiceProtocol" else "fixtureMarker"
                args_list.append(field + ": " + value)
            init_rows.append("        " + name + ": .init(" + ", ".join(args_list) + ")")
        service_probes += "@MainActor func fixtureServices(events: any EditorLocalEventPublishing, tableServices: FixtureTableServices? = nil) -> EditorPageServiceDependencies {\n"
        service_probes += "    let ownedTables = tableServices ?? FixtureTableServices()\n"
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
        add("BoundaryDoubles", prefix + ownership_helpers + model_probes + table_helpers + "\n".join(projected_bundles) + service_probes, None,
            "explicit Foundation boundary and dependency-field identity doubles")

        ui_probes = """
@MainActor final class EditorPageController {}
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
""" + hooks["coordinator"] + "\n" + hooks["make_coordinator"] + "\n" + hooks["dismantle"] + "\n}\n"
        add("OriginalPreparedAssemblyMethods", ui_probes, None,
            "exact new original assembly/binding/coordinator bodies with explicit UIKit/existing-assembly boundary doubles")
        fixture = content("Scripts/CI/fixtures/original-editor-lifetime.swift")
        close_event = "    @MainActor func emitCloseEventForFixture() {\n        let updates: [DocumentUpdate] = [.close]\n" + hooks["close_event"] + "\n    }\n"
        fixture = replace_once(fixture, "    // SOURCE_HOOKS", hooks["close"] + "\n" + hooks["setup_view"] + "\n" + hooks["permissions"] + "\n" + close_event)
        fixture = replace_once(fixture, "        let data = try JSONEncoder().encode(checks.checks)",
            "        try await exerciseOwnedTableServices(checks)\n\n        let data = try JSONEncoder().encode(checks.checks)")
        fixture += "\n" + table_controls
        add("ExecutedLifetimeFixture", fixture, "Scripts/CI/fixtures/original-editor-lifetime.swift",
            "preserved lifetime fixture plus exact original lifecycle hooks and complete new table controls")
        report["table_fixture_lf_sha256"] = digest(content(TABLE_FIXTURE))
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
        BASE.require(len(rows) == 75 and len({row["name"] for row in rows}) == 75
            and all(row["passed"] is True for row in rows), "Incomplete lifetime controls")
        report.update(status="PASS")
        syntax = []
        for path in [DOC, LIFETIME, OWNER, SESSION, ASSEMBLY, VIEW, STATE, CONTAINER, TABLE_WRAPPER,
                     "AnytypeTests/Markdown/PreparedEditorLifetimeTests.swift",
                     "AnytypeTests/Markdown/EditorDocumentOwnedTableTests.swift"]:
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
