#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = "a05088b98844bba30f90b794effb8cf579e2ef08"
ASSEMBLY = "Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorPageModuleAssembly.swift"
VIEW = "Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageView.swift"
ACTION = "Anytype/Sources/ServiceLayer/Block/BlockActionHandler/BlockActionService/BlockActionService.swift"
TEXT = "Anytype/Sources/ServiceLayer/Block/TextServiceHandler/TextServiceHandler.swift"
DEPENDENCIES = str(Path(ACTION).with_name("BlockActionServiceDependencies.swift")).replace("\\", "/")
VALIDATOR = str(Path(ASSEMBLY).with_name("PreparedEditorPageDocument.swift")).replace("\\", "/")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def original(path):
    return subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT).decode("utf-8")


def declaration(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 1
    index = opening + 1
    while depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    return source[start:index]


def preserve(report):
    action = (ROOT / ACTION).read_text(encoding="utf-8")
    text = (ROOT / TEXT).read_text(encoding="utf-8")
    view = (ROOT / VIEW).read_text(encoding="utf-8")
    assembly = (ROOT / ASSEMBLY).read_text(encoding="utf-8")
    require(action.split("    // MARK: Actions", 1)[1] == original(ACTION).split("    // MARK: Actions", 1)[1], "An original block action changed")
    require(text.split("    func setText(", 1)[1] == original(TEXT).split("    func setText(", 1)[1], "An original text operation changed")
    require(view.split("    var body:", 1)[1] == original(VIEW).split("    var body:", 1)[1], "Original SwiftUI body changed")
    require(declaration(view, "    init(") == declaration(original(VIEW), "    init("), "Original StateObject initializer changed")
    original_class = original(ASSEMBLY).split("final class EditorPageModuleAssembly:", 1)[1]
    old_body = declaration(original_class, "    func buildStateModel(").split("{", 1)[1]
    new_body = declaration(assembly, "    private func assembleStateModel(").split("{", 1)[1]
    original_resolution = """        let document = documentService.document(
            objectId: data.objectId,
            spaceId: data.spaceId,
            mode: data.mode
        )"""
    require(new_body.replace("        let document = resolveDocument()", original_resolution) == old_body,
            "Original controller/view-model assembly changed beyond document resolution")
    require(assembly.split("    private func buildViewModel(", 1)[1] == original(ASSEMBLY).split("    private func buildViewModel(", 1)[1],
            "Original downstream editor assembly changed")
    report["source_preservation"] = {
        "all_original_block_action_methods": "IDENTICAL",
        "all_original_text_service_methods": "IDENTICAL",
        "original_view_body_and_default_initializer": "IDENTICAL",
        "original_controller_and_view_model_assembly_except_resolution": "IDENTICAL",
        "original_downstream_assembly": "IDENTICAL",
    }


def projected_sources(output, report):
    specifications = [
        ("DocumentMode", "Anytype/Sources/Models/Documents/Document/DocumentMode.swift", None),
        ("EditorPageObject", "Anytype/Sources/PresentationLayer/TextEditor/Assembly/EditorScreenData.swift", "struct EditorPageObject:"),
        ("BaseDocumentProtocol", "Anytype/Sources/Models/Documents/Document/BaseDocumentProtocol.swift", None),
        ("MiddlewareString", "Modules/Services/Sources/Models/MiddlewareString.swift", None),
        ("TextServiceProtocol", "Modules/Services/Sources/Services/TextService/TextServiceProtocol.swift", None),
        ("TextServiceHandler", TEXT, None),
        ("PreparedEditorPageDocument", VALIDATOR, None),
        ("BlockActionServiceDependencies", DEPENDENCIES, None),
        ("BlockActionServiceConstruction", ACTION, "construction"),
    ]
    paths = []
    records = []
    for name, relative, projection in specifications:
        path = ROOT / relative
        raw = path.read_bytes() if path.is_file() else subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=ROOT)
        source = raw.decode("utf-8").replace("\r\n", "\n")
        if projection == "construction":
            source = source.split("    // MARK: Actions", 1)[0] + "}\n"
        elif projection:
            source = declaration(source, projection) + "\n"
        removed = re.findall(r"^import (?!Foundation$)([^\n]+)$", source, re.M)
        source = re.sub(r"^import (?!Foundation$)[^\n]+\n", "", source, flags=re.M)
        target = output / (name + ".swift")
        target.write_text(source, encoding="utf-8", newline="\n")
        paths.append(target)
        records.append({"path": relative, "raw_sha256": digest(raw), "projection": projection or "whole_file",
                        "removed_imports": removed, "compiled_sha256": digest(target.read_bytes())})
    report["compiled_sources"] = records
    return paths


def run(command, output, name, timeout):
    started = time.monotonic()
    process = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    (output / (name + ".log")).write_bytes(process.stdout)
    return {"exit_code": process.returncode, "seconds": round(time.monotonic() - started, 3),
            "log_sha256": digest(process.stdout), "log": name + ".log", "command": [str(value) for value in command]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swiftc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "FAIL", "baseline": BASE, "native": "NOT_RUN", "apple_typecheck": "NOT_RUN",
              "scope": "Foundation identity checks, original TextServiceHandler forwarding, actual BlockActionService constructor only",
              "boundary_doubles": ["UIKit/rendering not compiled", "InfoContainer/document value dependencies; immutable DocumentProbe uses the same @unchecked Sendable boundary as original BaseDocument",
                                   "protobuf style/mode/mark boundary",
                                   "event publisher recorder", "six non-text service interfaces", "Factory original-services provider"],
              "not_proven": ["Full original editor isolation", "Anytype UI mounting", "Annotation durable writes", "Otzaria in-process integration"]}
    try:
        preserve(report)
        sources = projected_sources(output, report)
        fixture = ROOT / "Scripts/CI/fixtures/original-editor-boundary.swift"
        report["fixture_sha256"] = digest(fixture.read_bytes())
        executable = output / "original-editor-boundary.exe"
        compile_command = [args.swiftc, "-swift-version", "6", "-strict-concurrency=complete", "-parse-as-library",
                           *map(str, sources), str(fixture), "-o", str(executable)]
        report["compile"] = run(compile_command, output, "compile", 180)
        require(report["compile"]["exit_code"] == 0, "Foundation boundary fixture did not compile")
        report["execution"] = run([str(executable)], output, "execution", 30)
        require(report["execution"]["exit_code"] == 0, "Foundation boundary fixture failed")
        rows = json.loads((output / "execution.log").read_text(encoding="utf-8").strip())
        require(len(rows) == 29 and len({row["name"] for row in rows}) == 29 and all(row["passed"] is True for row in rows),
                "Incomplete original-editor boundary controls")
        report.update(status="PASS", checks=rows, passed=len(rows), failed=0)
        parsed = []
        for relative in [ASSEMBLY, VIEW, ACTION, TEXT, DEPENDENCIES, VALIDATOR,
                         "AnytypeTests/Markdown/PreparedEditorPageDocumentTests.swift", "AnytypeTests/Markdown/TextServiceHandlerInjectionTests.swift"]:
            item = run([args.swiftc, "-frontend", "-parse", "-swift-version", "5", str(ROOT / relative)],
                       output, "parse-" + str(len(parsed) + 1), 30)
            item["path"] = relative
            parsed.append(item)
            require(item["exit_code"] == 0, "Source syntax rejected: " + relative)
        report["syntax_only"] = parsed
        return 0
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        return 1
    finally:
        (output / "RESULT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: report.get(key) for key in ["status", "error", "passed", "failed", "native", "apple_typecheck"]}), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
