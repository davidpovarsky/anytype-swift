#!/usr/bin/env python3
"""Bounded preservation/admission audit; does not execute Swift or native RPCs."""
from pathlib import Path
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
P = "Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/"
MODEL = P + "Views/TypePropertiesView/TypePropertiesViewModel.swift"
VIEW = P + "Views/TypePropertiesView/TypePropertiesView.swift"
MOVE = P + "Views/TypePropertiesView/Model/TypePropertiesMoveHandler.swift"
DROP = P + "Views/TypePropertiesView/Model/TypePropertiesDropDelegate.swift"
COORD = P + "Coordinator/PropertiesListCoordinatorViewModel.swift"
COORD_VIEW = P + "Coordinator/PropertiesListCoordinatorView.swift"
EXT = "Anytype/Sources/ServiceLayer/Extensions/PropertiesServiceProtocolExtensions.swift"
SCOPE = "Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/OriginalEditorPropertyScope.swift"
CHANGED = {MODEL, VIEW, MOVE, DROP, COORD, COORD_VIEW, EXT}


def read(path, kind="source"):
    return (ROOT / kind / path).read_text()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def block(text, marker):
    """Return one actual brace body, ignoring strings and comments."""
    start = text.index("{", text.index(marker))
    token = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|[{}]')
    depth = 0
    for match in token.finditer(text, start):
        item = match.group()
        if item == "{":
            depth += 1
        elif item == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:match.start()]
    raise AssertionError("Unterminated Swift body: " + marker)


def compact(text):
    return re.sub(r"\s+", "", text)


def main():
    passed = []
    baseline = json.loads((ROOT / "BASE_INPUTS.json").read_text())
    assert baseline["source"] == "bbd11635598a77d98e7ffcb336fafee9a75eba10"
    actual_changed = set()
    files = []
    patch = []
    for row in baseline["files"]:
        path = row["path"]
        old = (ROOT / "base" / path).read_bytes()
        new = (ROOT / "source" / path).read_bytes()
        assert sha(old) == row["sha256"]
        assert hashlib.sha1(b"blob " + str(len(old)).encode() + b"\0" + old).hexdigest() == row["git_blob"]
        if old != new:
            actual_changed.add(path)
            files.append({"path": path, "base_git_blob": row["git_blob"],
                          "base_sha256": sha(old), "sha256": sha(new), "bytes": len(new)})
            patch.extend(difflib.unified_diff(old.decode().splitlines(keepends=True),
                                            new.decode().splitlines(keepends=True),
                                            fromfile="a/" + path, tofile="b/" + path))
    assert actual_changed == CHANGED
    assert read(SCOPE) == read(SCOPE, "base")
    passed.append("Exact bbd116 Git blobs; seven-file delta; existing property scope and owner/factory/dispatcher unmodified")

    model, old_model = read(MODEL), read(MODEL, "base")
    legacy_actions = ["onRelationTap", "onAddRelationTap", "onRelationReveal",
                      "onRelationHide", "onRelationRemove", "onAddConflictRelation"]
    for name in legacy_actions:
        body = block(model, "func " + name)
        rejection = "return nil" if name == "onRelationHide" else "return"
        guard = "\n        guard preparedSession == nil else { " + rejection + " }"
        assert body.startswith(guard)
        assert body.replace(guard, "", 1) == block(old_model, "func " + name)
    for name in ["filterProperties", "isRelationHidden"]:
        assert block(model, "func " + name) == block(old_model, "func " + name)
    assert block(model, "func rebuildOriginalTypeProperties") == block(old_model, "func rebuildTypeProperties")
    assert "preparedSession == nil && canEditPropertiesList" in model
    passed.append("Original catalog/property action bodies and rendering algorithm preserved; external schema actions rejected before original effects")

    setup = block(model, "func setupSubscriptions")
    legacy_setup = block(setup, "if preparedSession == nil")
    assert "ensureSpaceAndTypeReady" in legacy_setup
    assert setup.count("ensureSpaceAndTypeReady") == 1
    assert "else if !document.isOpened" in setup and setup.count("document.open()") == 1
    details = block(model, "func setupDetailsSubscription")
    assert "refreshTypeRelationsIfNeeded" in block(details, "if preparedSession == nil")
    assert details.count("refreshTypeRelationsIfNeeded") == 1
    read_body = block(model, "func updateConflictRelations")
    owned_read = block(read_body, "if let scope = originalEditorScope")
    assert 'rpcNames: ["ObjectTypeListConflictingRelations"]' in owned_read
    assert "scope.originalProperties(propertiesService)" in owned_read
    assert "contextId: typeId, spaceId: spaceId" in owned_read
    assert "publishConflictRelations" in block(read_body, "try withCurrentSource")
    passed.append("Owned setup cannot raw-open or provision schema; original same-type conflict read and post-await publication retain actual owner")

    move = read(MOVE)
    stripped = move.replace("    private let originalEditorScope: OriginalEditorPropertyScope?\n\n"
                            "    init(originalEditorScope: OriginalEditorPropertyScope? = nil) {\n"
                            "        self.originalEditorScope = originalEditorScope\n    }\n", "", 1)
    stripped = stripped.replace("        if let originalEditorScope {\n"
                                "            try await originalEditorScope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {\n"
                                "                try originalEditorScope.owner.validateDocument(document)\n"
                                "            }\n        }\n", "", 1)
    stripped = stripped.replace("recommendedHiddenProperties: recommendedHiddenRelationsIds,\n"
                                "            originalEditorScope: originalEditorScope", "recommendedHiddenProperties: recommendedHiddenRelationsIds", 1)
    assert stripped == read(MOVE, "base")
    drop = block(read(DROP), "func dropEntered")
    owned_drop = block(drop, "if let originalEditorScope")
    assert "Task {" not in owned_drop
    assert "originalEditorScope.schedule(requiredPermissions: OriginalEditorPropertyScope.listPermissions)" in owned_drop
    assert "let rows = allRows" in owned_drop and "relationRows: rows, document: document" in owned_drop
    assert drop[drop.index("        Task {"):] == block(read(DROP, "base"), "func dropEntered")[block(read(DROP, "base"), "func dropEntered").index("        Task {"):]
    assert "let prepared = prepareAction" in read(SCOPE) and "Task { try await prepared() }" in read(SCOPE)
    passed.append("Whole original MoveHandler algorithm and nil DropDelegate Task preserved; actual drop reserves existing owner before creating a task")

    extension, old_extension = read(EXT), read(EXT, "base")
    tail = "    func addTypeRecommendedProperty"
    assert extension[extension.index(tail):] == old_extension[old_extension.index(tail):]
    update = block(extension, "func updateTypeProperties")
    assert update.count("self.updateTypeProperties(") == 1
    assert update.count("recordUpdatedTypeRelations(") == 1
    assert "dataviewId: SetConstants.dataviewBlockId" in update
    assert "originalEditorScope.originalProperties(self)" in update
    assert "typeId.utf8.elementsEqual(originalEditorScope.objectId.utf8)" in update
    assert "try await originalEditorScope.perform(" in update
    native_start = update.index("try await self.updateTypeProperties(")
    publication = update.index("try await originalEditorScope.withActionCallback(")
    assert publication > native_start
    assert "publishOriginal(originalEditorScope.spaceId)" in block(update, "try await originalEditorScope.withActionCallback(")
    assert update.count("requiredPermissions: OriginalEditorPropertyScope.listPermissions") == 2
    service = read("Modules/Services/Sources/Services/Properties/PropertiesService.swift", "references")
    native = block(service, "func updateTypeProperties")
    assert native.count("$0.contextID = typeId") == 2
    assert native.count(".invoke()") == 2
    assert "ClientCommands.objectSetDetails(" in native and "ClientCommands.blockDataviewRelationSet(" in native
    assert "ClientCommands" not in extension
    passed.append("One original update payload, two original same-type RPCs, exact target check and concrete delegate; delayed cache update rechecks actual child owner/Space")

    coordinator = read(COORD)
    opening = block(coordinator, "func showTypeRelationsView")
    assert opening.index("PreparedEditorChildPreparation(owner: scope.owner)") < opening.index("typePreparationTask = Task")
    assert "data: .init(objectId: typeId, spaceId: typeData.spaceId)" in opening
    assert "requiredPermissions: OriginalEditorPropertyScope.listPermissions" in opening
    assert "preparedTypePropertiesSession = child" in block(opening, "try withCurrentSource")
    assert "child.retire()" in opening and "preparedTypePropertiesSession === child" in opening
    assert "preparedTypePropertiesSession?.retire()" in block(coordinator, "func didDismissTypeProperties")
    assert block(coordinator, "func onTypeSelected") == block(read(COORD, "base"), "func onTypeSelected")
    coordinator_view = read(COORD_VIEW)
    assert "TypePropertiesView(preparedSession: child)" in coordinator_view
    assert "else if preparedSession == nil" in coordinator_view
    assert "child.document.objectId.utf8.elementsEqual(data.objectId.utf8)" in coordinator_view
    assert "child.document.spaceId.utf8.elementsEqual(data.spaceId.utf8)" in coordinator_view
    assert ".onDisappear { model.cancelTypePreparation() }" in coordinator_view
    assert ".onDisappear { model.retireOwnedPresentation() }" in read(VIEW)
    assert ".disabled(model.originalEditorScope != nil)" in read(VIEW)
    factory = read("Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/PreparedEditorPageSessionFactory.swift", "references")
    assert "originalDocument.openForOriginalEditorSource()" in factory
    base_document = read("Anytype/Sources/Models/Documents/Document/BaseDocument.swift", "references")
    fresh_open = block(base_document, "func openForOriginalEditorSource")
    assert "!isOpened, openTask == nil, originalAccountDispatch == nil" in fresh_open
    passed.append("Selected type acquires and retains its actual fresh child; identity checked before presentation; errors/disappearance retire only that acquisition with no raw fallback")

    provider = read("Anytype/Sources/ServiceLayer/DocumentsProvider/DocumentsProvider.swift", "references")
    concrete_provider = provider[provider.index("final class DocumentsProvider:"):]
    assert "internalDocument(" in block(concrete_provider, "func document(")
    assert "SetDocument(" not in block(concrete_provider, "func document(")
    assert "return BaseDocument(" in block(concrete_provider, "private func createBaseDocument")
    assert ".setDocument(" not in factory and ".setDocument(" not in model
    assert "allowsAutomaticSchemaPreparation" in block(base_document, "private func setupSubscriptions")
    passed.append("Original selected-type acquisition uses BaseDocument, not the separate SetDocument setup/bootstrap route")

    all_source = "\n".join(read(p) for p in CHANGED)
    for forbidden in ("EditorDocumentWriteOwner(", "EditorDocumentWriteLifetime(", "NSLock(", "Task.detached", "ClientCommands."):
        assert forbidden not in all_source
    assert "PreparedEditorPageSessionFactory.swift" not in "\n".join(CHANGED)
    passed.append("No replacement owner, lifetime, dispatcher, RPC implementation, storage engine, factory edit or detached work added")

    patch_bytes = "".join(patch).encode()
    (ROOT / "original-type-properties-owned.patch").write_bytes(patch_bytes)
    manifest = {"source": baseline["source"], "files": files,
                "patch_sha256": sha(patch_bytes), "native": "NOT_RUN"}
    (ROOT / "CANDIDATE_INPUTS.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report = {"status": "SOURCE_PRESERVATION_AND_ADMISSION_AUDIT_PASS", "checks": passed,
              "checked_invariants": len(passed), "changed_files": len(files),
              "patch_sha256": sha(patch_bytes), "swift_execution": "NOT_RUN",
              "native_rpc_calls": 0, "native_editor_ui_tests": 0,
              "historical_owner_and_source_controls": "NOT_RERUN_UNCHANGED_BY_THIS_DELTA",
              "limitations": ["This source audit does not typecheck SwiftUI or execute native interaction.",
                              "Foreign property creation/editing and catalog provisioning remain unqualified.",
                              "Fresh source acquisition rejects already-open cached type documents."]}
    (ROOT / "source-audit-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
