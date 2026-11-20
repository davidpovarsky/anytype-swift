import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE = "841bc1d635673378289165ce7805497041b1b77a"
ROOT = Path(__file__).resolve().parents[2]
EVENTS = "Anytype/Sources/ServiceLayer/Block/EditorLocalEventPublisher.swift"


def inverse_events(source):
    pairs = [
        ("        await localEvents.refresh(contextId: documentId)",
         "        await EventsBunch(\n            contextId: documentId,\n            localEvents: [.general]\n        ).send()"),
        ("        await localEvents.setStyle(contextId: contextId, blockId: blockId)",
         "        await EventsBunch(\n            contextId: contextId,\n            localEvents: [.setStyle(blockId: blockId)]\n        ).send()"),
        ("            await localEvents.setToggled(contextId: document.objectId, blockId: blockId)",
         "            await EventsBunch(contextId: document.objectId, localEvents: [.setToggled(blockId: blockId)])\n                .send()"),
        ("        await localEvents.setText(contextId: document.objectId, blockId: blockId, text: middlewareString)",
         "        await EventsBunch(\n            contextId: document.objectId,\n            localEvents: [.setText(blockId: blockId, text: middlewareString)]\n        ).send()"),
        ("            await localEvents.setLoadingState(contextId: document.objectId, blockId: blockId)",
         "            await EventsBunch(\n                contextId: document.objectId,\n                localEvents: [.setLoadingState(blockId: blockId)]\n            ).send()"),
    ]
    for current, original in pairs:
        source = source.replace(current, original)
    return source


def inverse_assembly(source):
    rows = {
        "router": 1, "blockActionService": 1, "blockActionHandler": 1,
        "keyboardHandler": 1, "blocksStateManager": 1, "header": 1,
        "simpleTable": 1, "slashMenu": 1, "blockBuilder": 1, "viewModel": 1,
    }
    event_argument = ",\n            localEvents: services?.localEvents ?? OriginalEditorLocalEventPublisher()"
    if source.count(event_argument) != 2:
        raise RuntimeError("Missing exact action/event owner forwarding")
    source = source.replace(event_argument, "")
    for name, count in rows.items():
        text = ",\n            dependencies: services?." + name + " ?? .original()"
        if source.count(text) != count:
            raise RuntimeError("Missing or duplicate exact assembly dependency: " + name)
        source = source.replace(text, "")
    text = ",\n            services: services\n        )\n\n        bottomNavigationManager.output"
    if source.count(text) != 1:
        raise RuntimeError("Missing exact page dependency forwarding")
    source = source.replace(text, "\n        )\n\n        bottomNavigationManager.output")
    source = source.replace("        output: (any EditorPageModuleOutput)?,\n        services: EditorPageServiceDependencies?\n    ) -> EditorPageViewModel",
                            "        output: (any EditorPageModuleOutput)?\n    ) -> EditorPageViewModel")
    return source


def tail_after_initializer(source):
    start = source.index("    init(")
    index = source.index("{", start) + 1
    depth = 1
    while depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    return source[index:]


def validate_writer_preservation(report):
    mapping = json.loads((ROOT / "Scripts/CI/fixtures/editor-writer-source-map.json").read_text(encoding="utf-8"))
    records = []
    for path, item in mapping.items():
        original = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT).decode("utf-8")
        current = (ROOT / path).read_text(encoding="utf-8")
        old_tail = tail_after_initializer(original)
        new_tail = tail_after_initializer(inverse_events(current))
        if old_tail != new_tail:
            raise RuntimeError("Original component methods changed: " + path)
        bundle = (ROOT / item["bundle"]).read_text(encoding="utf-8")
        for name, factory, protocol in item["fields"]:
            required = [
                "let " + name + ": any " + protocol,
                "self." + name + " = dependencies." + name,
            ]
            if not all(value in current for value in required):
                raise RuntimeError("Missing instance dependency: " + path + ":" + name)
            if bundle.count(name + ": Container.shared." + factory + "()") != 1:
                raise RuntimeError("Changed original dependency factory: " + path + ":" + name)
        records.append({"path": path, "original_method_body_sha256": hashlib.sha256(old_tail.encode()).hexdigest(),
                        "method_body": "IDENTICAL_AFTER_EXACT_EVENT_ROUTE_INVERSE" if "BlockActionHandler.swift" in path else "IDENTICAL"})
    for path in [
        "Anytype/Sources/PresentationLayer/TextEditor/Views/UndoRedo/UndoRedoViewModel.swift",
        "Anytype/Sources/PresentationLayer/TextEditor/Views/UndoRedo/UndoRedoView.swift",
    ]:
        old = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT).decode("utf-8")
        current = (ROOT / path).read_text(encoding="utf-8")
        if tail_after_initializer(old) != tail_after_initializer(current):
            raise RuntimeError("Original Undo/Redo behavior changed")
        records.append({"path": path, "method_body": "IDENTICAL"})
    path = "Anytype/Sources/ServiceLayer/Block/Pastboard/DocumentService/PasteboardBlockDocumentService.swift"
    old = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT).decode("utf-8")
    current = (ROOT / path).read_text(encoding="utf-8")
    if old.split("    var hasValidURL:", 1)[1] != current.split("    var hasValidURL:", 1)[1]:
        raise RuntimeError("Original pasteboard forwarding changed")
    records.append({"path": path, "method_body": "IDENTICAL"})
    report["writer_source_preservation"] = records
    return sorted(set(mapping) | {item["bundle"] for item in mapping.values()} | {
        EVENTS, "Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorPageServiceDependencies.swift",
        "Anytype/Sources/PresentationLayer/TextEditor/Views/UndoRedo/UndoRedoViewModel.swift",
        "Anytype/Sources/PresentationLayer/TextEditor/Views/UndoRedo/UndoRedoView.swift", path,
    })
