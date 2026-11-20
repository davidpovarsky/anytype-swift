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
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)
NEW_SOURCES = [
    "Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteLifetime.swift",
    "Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift",
    "Anytype/Sources/ServiceLayer/Block/TextServiceHandler/DocumentOwnedTextService.swift",
    "Anytype/Sources/ServiceLayer/Block/DocumentOwnedLocalEventPublisher.swift",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swiftc", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "FAIL", "native": "NOT_RUN", "apple_typecheck": "NOT_RUN",
              "baseline": "67a23f718548ee80dbb084e57933115a07601ea3",
              "scope": "Actual original interfaces and new document owner/text/event wrappers; held Foundation service/event boundaries",
              "boundary_doubles": ["UIKit/Combine/document UI values", "protobuf style/mode/marks",
                                  "original EventsBunch recorder", "Foundation services and held async operation probes",
                                  "mutable document fields protected by NSLock, matching the original unchecked-Sendable document boundary"],
              "not_proven": ["Native RPC atomicity or rollback", "annotation durability", "full original editor write isolation",
                             "routed sheet ownership", "Apple rendering", "Otzaria integration"]}
    try:
        BOUNDARY.preserve(report)
        BOUNDARY.validate_writer_preservation(report)
        sources = BOUNDARY.projected_sources(output, report)
        extra = [
            ("ObjectPermissions", "Anytype/Sources/Models/ObjectPermissions/ObjectPermissions.swift", "struct ObjectPermissions:"),
            ("EditBlocksPermission", "Anytype/Sources/Models/Documents/Document/EditBlocksPermission.swift", None),
        ] + [(Path(path).stem, path, None) for path in NEW_SOURCES]
        for name, path, projection in extra:
            absolute = ROOT / path
            raw = absolute.read_bytes() if absolute.exists() else subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT)
            source = raw.decode("utf-8").replace("\r\n", "\n")
            if projection:
                source = BOUNDARY.declaration(source, projection) + "\n"
            removed = re.findall(r"^import (?!Foundation$)([^\n]+)$", source, re.M)
            source = re.sub(r"^import (?!Foundation$)[^\n]+\n", "", source, flags=re.M)
            destination = output / (name + ".swift")
            destination.write_text(source, encoding="utf-8", newline="\n")
            sources.append(destination)
            report["compiled_sources"].append({
                "path": path, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "projection": projection or "whole_file", "removed_imports": removed,
                "compiled_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            })
        base_fixture = ROOT / "Scripts/CI/fixtures/original-editor-boundary.swift"
        prefix = base_fixture.read_text(encoding="utf-8").split("@main struct OriginalEditorBoundaryFixture", 1)[0]
        BOUNDARY.require(prefix.count("struct ObjectPermissions: Sendable {}\n") == 1, "Unexpected permissions boundary")
        prefix = prefix.replace("struct ObjectPermissions: Sendable {}\n", "")
        (output / "BoundaryDoubles.swift").write_text(prefix, encoding="utf-8", newline="\n")
        sources.append(output / "BoundaryDoubles.swift")
        fixture = ROOT / "Scripts/CI/fixtures/original-editor-ownership.swift"
        report["fixture_sha256"] = hashlib.sha256(fixture.read_bytes()).hexdigest()
        report["boundary_fixture_sha256"] = hashlib.sha256(base_fixture.read_bytes()).hexdigest()
        executable = output / "original-editor-ownership.exe"
        command = [args.swiftc, "-swift-version", "6", "-strict-concurrency=complete", "-parse-as-library",
                   *map(str, sources), str(fixture), "-o", str(executable)]
        report["compile"] = BOUNDARY.run(command, output, "compile", 180)
        BOUNDARY.require(report["compile"]["exit_code"] == 0, "Ownership boundary did not compile")
        report["execution"] = BOUNDARY.run([str(executable)], output, "execution", 45)
        BOUNDARY.require(report["execution"]["exit_code"] == 0, "Ownership controls failed")
        rows = json.loads((output / "execution.log").read_text(encoding="utf-8").strip())
        BOUNDARY.require(len(rows) == 30 and len({row["name"] for row in rows}) == 30
                         and all(row["passed"] is True for row in rows), "Incomplete ownership controls")
        report.update(status="PASS", passed=len(rows), failed=0, checks=rows)
        syntax = []
        for path in NEW_SOURCES + ["AnytypeTests/Markdown/EditorDocumentWriteOwnerTests.swift"]:
            entry = BOUNDARY.run([args.swiftc, "-frontend", "-parse", "-swift-version", "5", str(ROOT / path)],
                                 output, "parse-" + str(len(syntax) + 1), 30)
            entry["path"] = path
            syntax.append(entry)
            BOUNDARY.require(entry["exit_code"] == 0, "Source syntax rejected: " + path)
        report["syntax_only"] = syntax
        return 0
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        return 1
    finally:
        (output / "RESULT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: report.get(key) for key in ["status", "error", "passed", "failed", "native", "apple_typecheck"]}))


if __name__ == "__main__":
    raise SystemExit(main())
