"""Continue the original RPC gate using authenticated baseline bytes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

BASELINE_ARCHIVE = "failed-run-45055852172/Heart_Schema_RPC_Copy_Generation_45055852172.zip"
BASELINE_SHA256 = "8d76ee6f186f32985c276dba1f79e2ee82e0db7c1ad9c259ce4c2350b43fc769"
BASELINE_BYTES = 11898059
BASELINE_HEAD = "ca6eb576d0ac105ef260bc2703b7d0dc186a8656"
BASELINE_RUN = 45055852172


def _row(raw, path):
    return {"path": path, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def _relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise RuntimeError("invalid retained relative path")
    return path


def restore_verified_baseline(archive_path, current_inputs, roots, evidence):
    """Restore only the exact passed baseline; never restore candidate failure bytes."""
    archive_path, evidence = Path(archive_path), Path(evidence)
    if (archive_path.stat().st_size != BASELINE_BYTES or
            hashlib.sha256(archive_path.read_bytes()).hexdigest() != BASELINE_SHA256):
        raise RuntimeError("retained baseline archive identity mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise RuntimeError("duplicate retained archive member")
        result = json.loads(archive.read("RESULT.json"))
        if (result["control_head"] != BASELINE_HEAD or result["status"] != "FAIL" or
                result["error"] != "owned command failed: baseline-typecheck-generated-swift" or
                not result["owned_command_groups_drained"] or not result["owned_work_removed"]):
            raise RuntimeError("unexpected original terminal result")
        original_inputs = json.loads(archive.read("ORIGINAL_GENERATOR_INPUTS.json"))
        if original_inputs != current_inputs:
            raise RuntimeError("current original generator inputs differ from retained baseline")
        commands = json.loads(archive.read("COMMANDS.json"))
        reused_labels = ("baseline-original-native-generation", "baseline-original-swift-generation",
                         "baseline-compile-generated-go")
        receipts = {}
        for label in reused_labels:
            matches = [row for row in commands if row["label"] == label]
            if len(matches) != 1:
                raise RuntimeError("ambiguous original baseline command")
            row = matches[0]
            if (row["status"] != "TERMINAL" or row["returncode"] != 0 or
                    row["effective_returncode"] != 0 or row["timed_out"] or
                    not any(item.get("drained") is True for item in row["cleanup"])):
                raise RuntimeError("original baseline command did not pass and drain")
            for stream in ("stdout", "stderr"):
                if hashlib.sha256(archive.read(row[stream])).hexdigest() != row[stream + "_sha256"]:
                    raise RuntimeError("original baseline command stream differs")
            receipts[label] = {"status": "REUSED", "source": BASELINE_HEAD, "run": BASELINE_RUN,
                               "stdout_sha256": row["stdout_sha256"], "stderr_sha256": row["stderr_sha256"]}
        outputs = json.loads(archive.read("GENERATED_OUTPUT_INDEX.json"))
        if set(outputs) != {"baseline", "tracked"}:
            raise RuntimeError("retained outputs contain an unexpected candidate")
        counts = {kind: len(rows) for kind, rows in outputs["baseline"].items()}
        if counts != {"native": 11, "swift": 693, "middleware": 37}:
            raise RuntimeError("retained baseline inventory differs")
        for kind in ("native", "swift"):
            if outputs["tracked"][kind] != outputs["baseline"][kind]:
                raise RuntimeError("original baseline unexpectedly differs from tracked output")
        writes = []
        seen = set()
        for kind, rows in outputs["baseline"].items():
            root = Path(roots["heart" if kind == "native" else "swift"]).resolve()
            prefix = "generated/baseline/" + ("native" if kind == "native" else "swift") + "/"
            for row in rows:
                relative = _relative(row["path"])
                target = root.joinpath(*relative.parts)
                if target.is_symlink() or not target.resolve().is_relative_to(root):
                    raise RuntimeError("retained baseline target escapes owned copy")
                if target in seen:
                    raise RuntimeError("duplicate retained baseline target")
                seen.add(target)
                member = prefix + row["path"]
                info = archive.getinfo(member)
                if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                    raise RuntimeError("invalid retained baseline member")
                raw = archive.read(member)
                if _row(raw, row["path"]) != row:
                    raise RuntimeError("retained baseline output hash mismatch")
                if kind != "middleware" and (not target.is_file() or target.read_bytes() != raw):
                    raise RuntimeError("current tracked output differs from original baseline")
                writes.append((target, raw, evidence / member))
        # Validate every destination and byte before restoring into owned disposable copies.
        for target, raw, retained in writes:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            retained.parent.mkdir(parents=True, exist_ok=True)
            retained.write_bytes(raw)
        for kind, rows in outputs["tracked"].items():
            for row in rows:
                member = "generated/tracked/" + kind + "/" + row["path"]
                target = evidence / member
                raw = archive.read(member)
                if _row(raw, row["path"]) != row:
                    raise RuntimeError("retained tracked output hash mismatch")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        tool_receipt = json.loads(archive.read("ACTUAL_TOOL_EXECUTABLES.json"))
    reuse = {"schema": "otzaria.original-rpc-baseline-reuse/1", "run": BASELINE_RUN,
             "source": BASELINE_HEAD, "archive_sha256": BASELINE_SHA256, "rows": counts,
             "checks": receipts, "baseline_swift_typecheck": "NOT_REUSED_PREVIOUSLY_FAILED",
             "candidate_generation": "NOT_REUSED_PREVIOUSLY_NOT_RUN",
             "tool_binaries": "NOT_RETAINED_REBUILD_FROM_ORIGINAL_PINS_AND_RECORD_NEW_HASHES"}
    (evidence / "BASELINE_REUSE.json").write_text(json.dumps(reuse, indent=2) + "\n")
    return outputs, tool_receipt


def resolve_swiftprotobuf_products(plugin, bin_path_output):
    """Use the actual SwiftPM bin directory and an observed module, with no layout guess."""
    plugin = Path(plugin).resolve()
    lines = bin_path_output.strip().splitlines()
    if len(lines) != 1 or not Path(lines[0]).is_absolute():
        raise RuntimeError("SwiftPM did not return one absolute build-product path")
    binary_dir = Path(lines[0]).resolve()
    build_root = (plugin / ".build").resolve()
    if not binary_dir.is_dir() or not binary_dir.is_relative_to(build_root):
        raise RuntimeError("SwiftPM product path escapes the owned package build")
    executable = binary_dir / "protoc-gen-swift"
    if (executable.is_symlink() or not executable.is_file() or executable.stat().st_size == 0 or
            not executable.resolve().is_relative_to(build_root)):
        raise RuntimeError("actual SwiftProtobuf generator binary is absent or foreign")
    modules = []
    for path in binary_dir.rglob("SwiftProtobuf.swiftmodule"):
        if path.is_symlink() or not path.resolve().is_relative_to(build_root):
            raise RuntimeError("SwiftProtobuf module escapes the owned package build")
        if path.is_file() and path.stat().st_size > 0:
            modules.append(path)
        elif path.is_dir() and any(p.is_file() and p.stat().st_size for p in path.iterdir()):
            modules.append(path)
    if len(modules) != 1:
        raise RuntimeError("expected one observed SwiftProtobuf.swiftmodule; found " +
                           repr([str(p.relative_to(binary_dir)) for p in modules]))
    return executable, modules[0]


def retain_module(module, destination):
    module, destination = Path(module), Path(destination)
    files = [module] if module.is_file() else sorted(p for p in module.rglob("*") if p.is_file())
    rows = []
    for path in files:
        if path.is_symlink():
            raise RuntimeError("unexpected compiled module symlink")
        relative = path.name if module.is_file() else str(path.relative_to(module.parent))
        raw = path.read_bytes()
        rows.append(_row(raw, relative))
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    if not rows:
        raise RuntimeError("empty compiled module inventory")
    return rows
