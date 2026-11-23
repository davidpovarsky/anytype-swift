#!/usr/bin/env python3
"""Source admission and evidence accounting for the original Import/Cancel generators."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
SWIFT = "997e285617d57b31c4205976f01019819fa29a03"
PLUGIN = "c6fe6442e6a64250495669325044052e113e990c"
NATIVE_TREE = "16764dde5a16208b778e1a37e41bc05ef1735677"
COMMAND_HELPER_SHA = "aae68a25c0499d1bf61e98eca0ace9ffc48997823fdce9a775b22b239e904cdf"
ORIGINAL_GENERATOR_SHA = "2edac97dbc4a9a076acb548532bdb491f889b2fc7c453973059a3005f39edf4f"
CONTINUATION_SHA = "c86ee99a6e5a94b5b9229b9badc53023447b20c648657e58aee5d699dc5334dd"
CODEGEN_SHA = "56ad3a9accfd6c86af6aca7a4f51e8989b0499c2f637d7c4c883bf4dcee48482"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def row(path, relative):
    raw = Path(path).read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}

def relative_path(root, name):
    p = PurePosixPath(name)
    if not name or str(p) != name or p.is_absolute() or ".." in p.parts or "\0" in name or "\\" in name:
        raise RuntimeError("noncanonical relative input path")
    root = Path(root).resolve()
    path = root.joinpath(*p.parts)
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise RuntimeError("symlink input refused: " + name)
    if not path.resolve().is_relative_to(root):
        raise RuntimeError("input escapes its owned source root")
    return path

def check_rows(root, rows):
    seen = set()
    total = 0
    for entry in rows:
        name = entry["path"]
        if name in seen:
            raise RuntimeError("duplicate indexed input: " + name)
        seen.add(name)
        path = relative_path(root, name)
        actual = row(path, name)
        for field in ("bytes", "sha256"):
            if actual[field] != entry[field]:
                raise RuntimeError("indexed bytes differ: " + name)
        if entry.get("git_blob") is not None and actual["git_blob"] != entry["git_blob"]:
            raise RuntimeError("indexed Git blob differs: " + name)
        total += actual["bytes"]
    return {"files": len(seen), "bytes": total}

def git(root, *args):
    return subprocess.check_output(["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
                                   text=True, timeout=30).rstrip("\r\n")

def load_module(path, name, expected_sha):
    if sha(path) != expected_sha:
        raise RuntimeError("retained original module differs: " + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def admit_packet(packet, manifest_sha):
    packet = Path(packet).resolve()
    manifest_path = packet / "EXECUTION_INPUTS.json"
    if sha(manifest_path) != manifest_sha:
        raise RuntimeError("execution manifest identity differs")
    manifest = json.loads(manifest_path.read_bytes())
    if (manifest["heart_base"] != HEART or manifest["swift_base"] != SWIFT
            or manifest["swift_protobuf_base"] != PLUGIN
            or manifest["pre_generation_native_tree"] != NATIVE_TREE):
        raise RuntimeError("source composition identity differs")
    control = check_rows(packet, manifest["control_inputs"])
    composition = packet / "inherited-composition"
    index = json.loads((composition / "PACKET_INDEX.json").read_bytes())
    checked = check_rows(composition, index["files"])
    if checked != {"files": 159, "bytes": 2600385} or index["pre_generation_native_tree"] != NATIVE_TREE:
        raise RuntimeError("inherited composition closure differs")
    afterimages = json.loads((composition / "FINAL_NATIVE_AFTERIMAGES.json").read_bytes())["rows"]
    if len(afterimages) != 88 or len({x["native_path"] for x in afterimages}) != 88:
        raise RuntimeError("inherited native afterimage set differs")
    for entry in afterimages:
        actual = row(relative_path(composition, entry["afterimage"]["path"]), entry["native_path"])
        for field in ("bytes", "sha256", "git_blob"):
            if actual[field] != entry["final"][field] or actual[field] != entry["afterimage"][field]:
                raise RuntimeError("native source afterimage differs")
    for entry in manifest["rpc_controls"]:
        check_rows(packet, [entry["retained"]])
    return manifest, {"scope": "Source admission only; no generator/compiler/runtime execution.",
                      "control_inputs": control, "composition": checked, "native_afterimages": 88}

def retained_qualification(packet):
    root = Path(packet) / "retained-qualification"
    intake = json.loads((root / "INTAKE.json").read_bytes())
    metadata = json.loads((root / "artifact-metadata.json").read_bytes())["artifacts"]
    terminal = json.loads((root / "terminal.json").read_bytes())
    archive = root / "original-rpc-generation.zip"
    expected = "ec13df1db9405ffa42b2ef76ec1bda7988ecee8dff1c3fcb1fd01c556a7cf80e"
    if archive.stat().st_size != 10822146 or sha(archive) != expected:
        raise RuntimeError("retained genuine generation archive differs")
    artifacts = [x for x in metadata if x["id"] == 14787700016]
    if len(artifacts) != 1 or artifacts[0]["size_in_bytes"] != 10822146 or artifacts[0]["digest"] != "sha256:" + expected:
        raise RuntimeError("retained artifact metadata differs")
    if (terminal["databaseId"] != 45101449367 or terminal["attempt"] != 1
            or terminal["headSha"] != "7496e47fa4d37b0117abeae6b35ca5f4c8eaf638"
            or terminal["status"] != "completed" or terminal["conclusion"] != "success"
            or artifacts[0]["workflow_run"]["id"] != terminal["databaseId"]
            or artifacts[0]["workflow_run"]["head_sha"] != terminal["headSha"]):
        raise RuntimeError("retained producer source/terminal binding differs")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        names = [i.filename for i in members]
        if len(names) != 2279 or len(set(names)) != len(names) or sum(i.file_size for i in members) != 95054701:
            raise RuntimeError("retained generation archive closure differs")
        for info in members:
            name = PurePosixPath(info.filename)
            if (str(name) != info.filename or name.is_absolute() or ".." in name.parts
                    or "\0" in info.filename or "\\" in info.filename or info.is_dir()
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise RuntimeError("unsafe retained archive member")
        if z.testzip() is not None:
            raise RuntimeError("retained archive CRC failure")
        index = json.loads(z.read("EVIDENCE_INDEX.json"))
        if len(index["files"]) != 2278 or {x["path"] for x in index["files"]} != set(names) - {"EVIDENCE_INDEX.json"}:
            raise RuntimeError("retained archive index closure differs")
        for entry in index["files"]:
            raw = z.read(entry["path"])
            actual = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                      "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}
            if any(actual[k] != entry[k] for k in actual):
                raise RuntimeError("retained archive member differs")
        result = json.loads(z.read("RESULT.json"))
        if (result["status"] != "GENERATED_AND_MESSAGE_COMPILE_VERIFIED"
                or result["control_head"] != terminal["headSha"] or not result["owned_command_groups_drained"]):
            raise RuntimeError("retained source generation did not pass")
        commands = json.loads(z.read("COMMANDS.json"))
        if len(commands) != 35 or any(x["effective_returncode"] != 0 or x["timed_out"] for x in commands):
            raise RuntimeError("retained command outcome differs")
        outputs = json.loads(z.read("GENERATED_OUTPUT_INDEX.json"))["candidate"]
        indexed = {x["path"]: x for x in index["files"]}
        for family, rows in outputs.items():
            prefix = "generated/candidate/" + ("native/" if family == "native" else "swift/")
            for entry in rows:
                previous = indexed[prefix + entry["path"]]
                if any(previous[k] != entry[k] for k in ("bytes", "sha256", "git_blob")):
                    raise RuntimeError("retained generated output index differs")
        if {k: len(v) for k, v in outputs.items()} != {"native": 11, "swift": 695, "middleware": 37}:
            raise RuntimeError("retained generated output count differs")
        tools = json.loads(z.read("ACTUAL_TOOL_EXECUTABLES.json"))
    return outputs, tools, {"run_id": 45101449367, "attempt": 1, "artifact_id": 14787700016,
        "source": terminal["headSha"], "archive_sha256": expected, "verified_crc_members": 2279,
        "verified_index_rows": 2278, "scope": "Historical generation/message compilation reused without replay; no new Import/Cancel or native ABI credit."}

def apply_composition(packet, heart, commands, evidence):
    composition = Path(packet) / "inherited-composition"
    entries = json.loads((composition / "FINAL_NATIVE_AFTERIMAGES.json").read_bytes())["rows"]
    if git(heart, "rev-parse", "HEAD^{tree}") != "3d5c0ac2b15840e71693a7a94e229bb605d5f0f6":
        raise RuntimeError("actual original Heart tree differs")
    for entry in entries:
        target = relative_path(heart, entry["native_path"])
        original = entry["original"]
        if original["git_blob"] is None:
            if target.exists():
                raise RuntimeError("new native source already exists")
        else:
            before = row(target, entry["native_path"])
            if any(before[k] != original[k] for k in ("bytes", "sha256", "git_blob")):
                raise RuntimeError("original native preimage differs")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(relative_path(composition, entry["afterimage"]["path"]).read_bytes())
    commands.require("seal-native-composition-index", ["git", "add", "--", *[e["native_path"] for e in entries]], heart, 60)
    actual_tree = commands.require("read-native-composition-tree", ["git", "write-tree"], heart, 30).read_text().strip()
    if actual_tree != NATIVE_TREE:
        raise RuntimeError("actual composed native tree differs")
    return {"base": HEART, "base_tree": "3d5c0ac2b15840e71693a7a94e229bb605d5f0f6",
            "afterimages": 88, "actual_pre_generation_tree": actual_tree,
            "original_ordered_transform_receipt": "inherited-composition/ORDERED_SOURCE_TRANSFORMS.json"}

def validate_go_test(path, expected_names):
    events = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            events.append(json.loads(line))
    failed = [x for x in events if x.get("Action") in ("fail", "skip")]
    top = [x for x in events if x.get("Test") and "/" not in x["Test"] and x.get("Action") == "pass"]
    if failed or sorted(x["Test"] for x in top) != sorted(expected_names):
        raise RuntimeError("new RPC controls did not all execute and pass")
    if len([x for x in events if x.get("Action") == "pass" and not x.get("Test")]) != 1:
        raise RuntimeError("new RPC control package lacks an actual terminal PASS")
    return {"passed": [x["Test"] for x in top], "failed": 0, "skipped": 0,
            "scope": "These prepared original transport/size/cancel/logging controls only; no wallet/import/editor runtime."}

def declared_native_inputs(path, heart):
    text = Path(path).read_text()
    decoder, pos, entries, packages = json.JSONDecoder(), 0, {}, []
    fields = ("GoFiles", "CgoFiles", "CFiles", "CXXFiles", "MFiles", "HFiles", "FFiles",
              "SFiles", "SysoFiles", "EmbedFiles", "TestGoFiles", "XTestGoFiles",
              "TestEmbedFiles", "XTestEmbedFiles")
    heart = Path(heart).resolve()
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos == len(text):
            break
        package, pos = decoder.raw_decode(text, pos)
        if package.get("Error") or package.get("DepsErrors"):
            raise RuntimeError("actual Go package declaration contains errors")
        directory = Path(package.get("Dir", "/")).resolve()
        packages.append({"import_path": package.get("ImportPath"), "directory": str(directory),
                         "standard": package.get("Standard", False), "module": package.get("Module")})
        if directory.is_relative_to(heart):
            for field in fields:
                for name in package.get(field, []):
                    source = (directory / name).resolve()
                    if not source.is_relative_to(heart) or source.is_symlink() or not source.is_file():
                        raise RuntimeError("declared native compiler input escapes original source")
                    relative = source.relative_to(heart).as_posix()
                    entries[relative] = row(source, relative)
    if not entries or "core/annotation_import.go" not in entries or "clientlibrary/service/service.pb.go" not in entries:
        raise RuntimeError("actual native compiler declaration omits the original RPC endpoint/mobile export")
    return {"owned_source_inputs": sorted(entries.values(), key=lambda x: x["path"]),
            "packages": packages, "scope": "Actual go list -deps -test declaration; imported module identities retained. This is not compilation success."}

def retain_symbols(heart, swift):
    sources = [Path(heart) / "clientlibrary/service/service.pb.go",
               Path(heart) / "pb/service/service.pb.go",
               Path(swift) / "Modules/ProtobufMessages/Sources/Generated/service+invocation.swift"]
    names = ("AnnotationSchemaRegister", "AnnotationImport", "AnnotationImportCancel",
             "annotationSchemaRegister", "annotationImport", "annotationImportCancel")
    rows = []
    for path in sources:
        matches = [{"line": number, "text": text} for number, text in enumerate(path.read_text().splitlines(), 1)
                   if any(name in text for name in names)]
        if not matches:
            raise RuntimeError("fresh original generated service has no required RPC symbols")
        rows.append({"file": str(path), "sha256": sha(path), "observed_lines": matches})
    return {"scope": "Actual fresh generated Go/mobile export-source and Swift Invocation factory text. No emitted Lib.framework headers or link/runtime claim.",
            "files": rows}
