#!/usr/bin/env python3
"""Authenticate exact indexed original generator artifacts without crediting failed gates."""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def row(path, name):
    raw = path.read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def safe_name(name):
    p = PurePosixPath(name)
    require(bool(name) and str(p) == name and not p.is_absolute() and ".." not in p.parts
            and "\0" not in name and "\\" not in name, "Unsafe archive path")
    return p

def unpack(archive, destination, pin):
    require(archive.stat().st_size == pin["artifact_bytes"] and sha(archive) == pin["artifact_sha256"],
            "Generation archive differs from the recorded GitHub bytes")
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        names = [i.filename for i in entries]
        require(len(names) < 10000 and len(set(names)) == len(names)
                and sum(i.file_size for i in entries) <= 805306368,
                "Generation archive closure is duplicated or excessive")
        for item in entries:
            safe_name(item.filename)
            require(not item.is_dir() and stat.S_IFMT(item.external_attr >> 16) in (0, stat.S_IFREG)
                    and item.file_size <= 268435456, "Unexpected generation archive member")
        require(zipped.testzip() is None, "Generation archive CRC failure")
        index = json.loads(zipped.read("EVIDENCE_INDEX.json"))
        indexed = {entry["path"]: entry for entry in index["files"]}
        require(len(indexed) == len(index["files"])
                and set(indexed) == set(names) - {"EVIDENCE_INDEX.json"},
                "Generation archive index is not complete")
        for item in entries:
            data = zipped.read(item)
            if item.filename != "EVIDENCE_INDEX.json":
                expected = indexed[item.filename]
                require(len(data) == expected["bytes"] and hashlib.sha256(data).hexdigest() == expected["sha256"]
                        and hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == expected["git_blob"],
                        "Generation archive member identity differs")
            target = destination / item.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return {"crc_members": len(entries), "indexed_files": len(indexed)}

def intake_failed_generation(control, work, evidence, pin, commands):
    metadata = {}
    for kind, endpoint in (("run", "actions/runs/" + str(pin["run_id"])),
                           ("artifact", "actions/artifacts/" + str(pin["artifact_id"]))):
        raw = commands.require("reuse-generation-" + kind,
            ["gh", "api", "repos/" + pin["repository"] + "/" + endpoint], control, 60)
        metadata[kind] = json.loads(raw.read_bytes())
        write(evidence / ("REUSED_GENERATION_" + kind.upper() + ".json"), metadata[kind])
    run, artifact = metadata["run"], metadata["artifact"]
    require(run["id"] == pin["run_id"] and run["head_sha"] == pin["head_sha"]
            and run["head_branch"] == pin["head_branch"] and run["run_attempt"] == 1
            and run["status"] == "completed" and run["conclusion"] == "failure"
            and run["event"] == "push" and run["path"] == pin["workflow_path"]
            and run["repository"]["full_name"] == pin["repository"],
            "Original failed generator run identity differs")
    require(artifact["id"] == pin["artifact_id"] and artifact["name"] == pin["artifact_name"]
            and artifact["size_in_bytes"] == pin["artifact_bytes"] and not artifact["expired"]
            and artifact["digest"] == "sha256:" + pin["artifact_sha256"]
            and artifact["workflow_run"]["id"] == pin["run_id"]
            and artifact["workflow_run"]["head_sha"] == pin["head_sha"],
            "Original generated artifact identity differs")
    archive = commands.require("download-actual-generation",
        ["gh", "api", "repos/" + pin["repository"] + "/actions/artifacts/" + str(pin["artifact_id"]) + "/zip"],
        control, 240)
    destination = work / "actual-prior-generation"
    receipt = unpack(archive, destination, pin)
    write(evidence / "REUSED_GENERATION_INTAKE.json", receipt)
    result = json.loads((destination / "RESULT.json").read_bytes())
    require(result["status"] == "FAIL" and result["error_type"] == "RuntimeError"
            and result["error"] == "original generator modified native source outside generated output family"
            and result["control_head"] == pin["head_sha"]
            and result["manifest_sha256"] == pin["generation_manifest_sha256"]
            and result["pre_generation_native_tree"] == pin["pre_generation_native_tree"]
            and result["generator_native_invocations"] == 1 and result["generator_swift_invocations"] == 1
            and result["owned_command_groups_drained"] and result["commands"] == 31
            and not result["new_rpc_controls"], "Prior generator result boundary differs")
    recorded = json.loads((destination / "COMMANDS.json").read_bytes())
    require(len(recorded) == 31 and all(c["effective_returncode"] == 0 and not c["timed_out"] for c in recorded),
            "Prior actual generator commands did not finish normally")
    for label, arguments in (
        ("original-native-generation", ["make", "SHELL=/bin/bash", ".SHELLFLAGS=-e -o pipefail -c", "protos-go", "protos-server", "swift-protos"]),
        ("original-swift-generation", ["make", "SHELL=/bin/bash", ".SHELLFLAGS=-e -o pipefail -c", "generate-middle"])):
        matches = [c for c in recorded if c["label"] == label]
        require(len(matches) == 1 and matches[0]["argv"] == arguments, "Prior original generator invocation differs")
    outputs = json.loads((destination / "GENERATED_OUTPUT_INDEX.json").read_bytes())
    require({k:len(v) for k,v in outputs.items()} == {"native":11,"swift":696,"middleware":37},
            "Actual generated output family differs")
    indexed = {r["path"]:r for r in json.loads((destination / "EVIDENCE_INDEX.json").read_bytes())["files"]}
    for family, entries in outputs.items():
        prefix = "generated/candidate/" + ("native/" if family == "native" else "swift/")
        for entry in entries:
            require(row(destination / prefix / entry["path"],entry["path"]) == entry
                    and all(indexed[prefix+entry["path"]][k] == entry[k] for k in ("bytes","sha256","git_blob")),
                    "Prior generated output index does not bind actual retained bytes")
    write(evidence / "REUSED_GENERATION_RESULT.json", result)
    write(evidence / "REUSED_GENERATOR_COMMANDS.json", recorded)
    write(evidence / "REUSED_GENERATED_OUTPUT_INDEX.json", outputs)
    return destination, outputs


def capture_native_boundary(heart, evidence, label, native_outputs, git, commands):
    names = sorted(filter(None, git(heart, "diff", "--name-only", "-z").split("\0")))
    outside = sorted(set(names) - set(native_outputs))
    before = {}
    for record in filter(None, git(heart, "ls-files", "-s", "-z").split("\0")):
        meta, name = record.split("\t",1)
        mode, blob, stage = meta.split(" ")
        if name in names:
            before[name] = {"mode":mode,"git_blob":blob,"stage":stage}
    after = []
    require(len(names) <= 1024, "Unexpectedly broad native source mutation; raw diff retained")
    for name in names:
        safe_name(name)
        path = heart / name
        item = {"path":name, "indexed_before":before.get(name)}
        if path.is_symlink():
            item["after"] = {"type":"symlink"}
        elif path.is_file():
            item["after"] = {**row(path,name), "mode":oct(stat.S_IMODE(path.stat().st_mode))}
        elif path.exists():
            item["after"] = {"type":"non-file"}
        else:
            item["after"] = None
        after.append(item)
    receipt = {"stage":label,"changed_paths":names,"outside_generated_outputs":outside,"rows":after}
    write(evidence / ("NATIVE_BOUNDARY_" + label + ".json"), receipt)
    if names:
        commands.require("native-diff-" + label,
            ["git","-c","core.fsmonitor=false","diff","--binary","--no-ext-diff","--no-textconv"],heart,60)
    return receipt

def restore_original_output_placeholder(heart, evidence, expected, native_outputs, git, commands):
    """Preserve the exact tracked directory marker moved by original swift-protos.

    The original target is unchanged. Admit only its exact recorded deletion and
    exact moved bytes, then restore the original tracked marker. Every other
    source mutation remains a failure, before this restoration can occur.
    """
    require(expected["path"] == "dist/ios/protobuf/.gitignore"
            and expected["git_blob"] == "a4dc73110580f00f0071a8493cc22cece6307cb4",
            "Original generated-directory marker identity differs")
    before = capture_native_boundary(heart,evidence,"post-original-target",native_outputs,git,commands)
    require(before["outside_generated_outputs"] == [expected["path"]],
            "Original target changed source beyond its exact moved output-directory marker")
    target = heart / expected["path"]
    require(not target.exists() and not target.is_symlink(), "Original output-directory marker was not moved")
    indexed = git(heart,"ls-files","-s","--",expected["path"])
    require(indexed == "100644 " + expected["git_blob"] + " 0\t" + expected["path"],
            "Original output-directory marker index differs")
    moved = heart / "protobuf/.gitignore"
    require(not moved.is_symlink() and row(moved,expected["path"]) == expected,
            "Moved original output-directory marker bytes differ")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(moved.read_bytes())
    target.chmod(0o644)
    after = capture_native_boundary(heart,evidence,"post-marker-restoration",native_outputs,git,commands)
    require(not after["outside_generated_outputs"], "Source mutation remains after exact marker restoration")
    receipt = {"original_target":"make protos-go protos-server swift-protos",
               "original_tracked_marker":expected,"actual_moved_path":"protobuf/.gitignore",
               "before":before,"after":after,"restored_exact_original_bytes":True,
               "scope":"Original target unchanged; only the exact moved directory marker is restored. No additional mutation is admitted."}
    write(evidence / "ORIGINAL_OUTPUT_DIRECTORY_MARKER.json",receipt)
    return receipt
