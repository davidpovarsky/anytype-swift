"""Preserve real hosted source, complete Products and original evidence in tar.

Compiler intermediates are deliberately outside the deliverable. No source,
product or failed result is deleted, and this command never grants acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tarfile

import native_inputs as native


def snapshot(roots):
    result = {}
    for prefix, root in roots.items():
        root = Path(root)
        if not root.exists():
            continue
        native.require(root.resolve() == root, "Physical retention input required")
        for path in [root, *sorted(root.rglob("*"))]:
            relative = prefix + ("/" + path.relative_to(root).as_posix() if path != root else "")
            native.safe_relative(relative)
            s = path.lstat()
            row = {"mode": stat.S_IMODE(s.st_mode), "mtimeNS": s.st_mtime_ns}
            if stat.S_ISLNK(s.st_mode):
                target = os.readlink(path)
                native.require(not os.path.isabs(target) and path.resolve().is_relative_to(root), "Product symlink escapes its retained tree")
                row.update(kind="symlink", target=target)
            elif stat.S_ISDIR(s.st_mode):
                row["kind"] = "directory"
            elif stat.S_ISREG(s.st_mode):
                row.update(kind="file", bytes=s.st_size, sha256=native.sha(path))
            else:
                raise ValueError("Unexpected original retention node")
            result[relative] = row
    return result


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, source, control, output = (p.resolve() for p in (args.root, args.source, args.control, args.output))
    native.require(not output.exists(), "Fresh original retention output required")
    output.mkdir(mode=0o700)
    if not root.exists():
        save(output / "receipt.json", {"status": "NOT_RUN_BUILD_INTAKE_DID_NOT_START", "testsExecuted": 0})
        return 0
    config = source / ".git/config"
    if config.is_file():
        text = config.read_text().casefold()
        native.require("extraheader" not in text and "x-access-token" not in text
                       and "oauth" not in text, "Credential-bearing Git configuration must not be archived")
    roots = {"compiled-source": source}
    for name in ("build16", "toolchain", "ui-source-build16", "native-download", "original-native-inputs", "source-inputs"):
        roots["original-build/" + name] = root / name
    for name in ("app-derived", "ui-derived"):
        roots["original-build/" + name + "/Build/Products"] = root / name / "Build/Products"
    for name in ("evidence", "source", "Build.xcresult", "derived/Build/Products"):
        roots["original-build/native23-ui/" + name] = root / "native23-ui" / name
    # Copy only small controller/provenance files to a fresh retained directory.
    # Their executed or compiled origin remains explicit; no compiler is run.
    originals = output / "original-controls-and-top-level"
    originals.mkdir()
    for p in sorted(root.iterdir()):
        if p.is_file():
            native.require(not p.is_symlink(), "Unexpected top-level evidence symlink")
            shutil.copy2(p, originals / p.name)
    admission_path = root / "root-derived-build-admission.json"
    if admission_path.is_file():
        plan_ref = json.loads(admission_path.read_bytes())["rootPlan"]
        plan_path = Path(plan_ref["path"])
        native.require(plan_path.parent.resolve() == Path(os.environ["RUNNER_TEMP"]).resolve()
                       and native.sha(plan_path) == plan_ref["sha256"], "Original root plan custody differs")
        shutil.copy2(plan_path, originals / "root-plan.original.json")
    controls = originals / "control-source"
    controls.mkdir()
    paths = ["Tools/PinkhaDualEngineRuntime/hosted_shared_build/run.py",
             "Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_inputs.py",
             "Tools/PinkhaDualEngineRuntime/hosted_shared_build/retain.py",
             "Tools/PinkhaDualEngineRuntime/hosted_shared_build/native23_build.py",
             "Tools/PinkhaDualEngineRuntime/hosted_shared_build/native23_build_contract.json",
             "Tools/PinkhaDualEngineRuntime/hosted_shared_build/test_native23_build.py",
             "Tools/PinkhaDualEngineRuntime/wave3_shared_build.py",
             "Tools/PinkhaDualEngineRuntime/build_wave2_app16_compiler_qualified.py",
             ".github/workflows/pinkha-hosted-shared-build.yml",
             ".github/workflows/pinkha-native8ac-export.yml",
             ".github/workflows/torah-inspector-ipados27.yml"]
    for name in paths:
        p = control / name
        native.regular(p)
        destination = controls / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, destination)
    roots["original-build/control-and-top-level"] = originals
    before = snapshot(roots)
    needed = sum(row.get("bytes", 0) for row in before.values())
    native.require(needed <= 8 * 1024 ** 3, "Measured result retention exceeds the reviewed 8 GiB envelope")
    native.require(shutil.disk_usage(output).free >= needed + 2 * 1024 ** 3,
                   "Full original result archive plus emergency floor cannot fit")
    save(output / "nodes-before.json", before)
    archive_path = output / "original-app-ui-and-evidence.tar.gz"
    with archive_path.open("xb") as raw, tarfile.open(fileobj=raw, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        for prefix, base in roots.items():
            if not base.exists():
                continue
            for p in [base, *sorted(base.rglob("*"))]:
                name = prefix + ("/" + p.relative_to(base).as_posix() if p != base else "")
                archive.add(p, arcname=name, recursive=False)
    after = snapshot(roots)
    save(output / "nodes-after.json", after)
    native.require(before == after, "Original evidence changed during retention")
    seen = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            name = member.name.rstrip("/")
            native.require(name in before and name not in seen, "Unexpected retained member")
            expected = before[name]
            native.require(member.mode == expected["mode"], "Original retained mode differs")
            if expected["kind"] == "file":
                native.require(member.isfile() or member.islnk(), "Original retained file kind differs")
                # tarfile resolves an actual earlier hardlink, preserving topology.
                stream = archive.extractfile(member)
                h = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 ** 2), b""):
                    h.update(chunk)
                native.require(h.hexdigest() == expected["sha256"], "Retained original file bytes differ")
            elif expected["kind"] == "symlink":
                native.require(member.issym() and member.linkname == expected["target"], "Original product symlink differs")
            else:
                native.require(member.isdir(), "Original retained directory differs")
            seen.add(name)
    native.require(seen == set(before), "Original retention closure incomplete")
    save(output / "receipt.json", {"status": "PASS_RETAINED_ORIGINAL_APP_UI_SOURCE_AND_EVIDENCE_NOT_ACCEPTANCE",
                                   "archive": {"path": str(archive_path), "bytes": archive_path.stat().st_size,
                                               "sha256": native.sha(archive_path)},
                                   "nodesBeforeSHA256": native.sha(output / "nodes-before.json"),
                                   "nodesAfterSHA256": native.sha(output / "nodes-after.json"), "nodes": len(before),
                                   "sourceAndProductsUnchanged": True, "testsExecuted": 0})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
