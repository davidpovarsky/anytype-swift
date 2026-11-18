"""Build exact r14/r15 component binaries and run the preserved process-pair proof.

This is not an Apple runtime, account/export or full F10 acceptance route.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import run_t5_coverage_ci as coverage

PAIR_SOURCE = "01025e412e7382cc6bb8107dd11b2ca7e15f5d7d"
PAIR_DIRECTORY = "Tools/PinkhaNativeDerived/compatibility_pairs"
PAIR_HASHES = {
    "README.md": "3609e7122b9d8c3c6ad2738dfaeef3b68c3722680849b6a886c52f2a7d530457",
    "run_pairs.py": "815ed7e197a7c5443e5da2bae3a39ad392f7d2c3686cb3191c1a9f9c382513d4",
    "pair_phase_test.go": "eeb6bb048470a6805c35d7f6f574750ebe8873196b8b447f6345a3649113e4e8",
    "test_controls.py": "9840895c252c71447349924020b4c8c72c57ba5224fe76a695b877e7ab345c7d",
    "manifest.template.json": "af516a2fcf963bd8fc385d42333e252643a5b963f697eaea43811b89ba0d8dc6",
}
APPROVAL_ROOT = "docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval"
OLD_PATCH = "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077"
OLD_INVENTORY = "952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14"
GENPROTO_PATH = "google.golang.org/genproto"
GENPROTO_VERSION = "v0.0.0-20241021214115-324edc3d5d38"
GENPROTO_SUM = "h1:Q3nlH8iSQSRUwOskjbcSMcF2jiYMNiQYZ0c2KEJLKKU="
GENPROTO_MOD_SUM = "h1:xBI+tzfqGGN2JBeSebfKXFSdBpWVQ7sLW40PTupVRm4="
GENPROTO_DECLARATION = "Tools/PinkhaNativeDerived/compatibility/go.mod"
GENPROTO_DECLARATION_SHA = "6616b2ae644a325a32edaae1528c5e5c2d41a1ff17c1ed4d1b84beec5242958d"
TANTIVY = "88b34e006707bfec2d29e8b26405f67cbb975d06fd4ea164da856d0084aaabbc"
PHASES = ["old-create", "new-upgrade", "old-edit", "new-recover"]
CLIENT_DISABLED = "DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF"
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_pair_inputs(control):
    for name, expected in PAIR_HASHES.items():
        if coverage.digest(control / PAIR_DIRECTORY / name) != expected:
            raise RuntimeError("Preserved pair input differs: " + name)


def validate_genproto_selection(selection):
    effective = selection.get("Replace", selection)
    if (selection.get("Path") != GENPROTO_PATH
            or effective.get("Path") != GENPROTO_PATH
            or effective.get("Version") != GENPROTO_VERSION
            or effective.get("Sum") != GENPROTO_SUM
            or effective.get("GoModSum") != GENPROTO_MOD_SUM):
        raise RuntimeError("Selected genproto differs from the existing reviewed dependency and checksum")
    return effective


def validate_pair_result(result):
    phases = result.get("phase_reports", [])
    if (result.get("status") != "COMPONENT_STORE_PAIR_PASS"
            or result.get("full_F10") != "NOT_PROVEN"
            or result.get("export_status") != "NOT_RUN_COMPONENT_NO_RPC"
            or result.get("swift_pairing_status") != "NOT_RUN"
            or result.get("client_enablement") != CLIENT_DISABLED
            or [p.get("phase") for p in phases] != PHASES
            or any(p.get("test_passed") is not True or p.get("closed") is not True for p in phases)):
        raise RuntimeError("Component sequence receipt is incomplete or overstates acceptance")
    pids = [p.get("pid") for p in phases]
    if len(set(pids)) != 4 or any(type(pid) is not int or pid <= 0 for pid in pids):
        raise RuntimeError("Four distinct completed native process identities are required")
    return dict(binaries=2, native_processes=4, passing_test_invocations=4)


def execute(args, control, evidence):
    if os.name != "posix":
        raise RuntimeError("Actual pairing requires the POSIX native CI lane")
    identity = coverage.require_identity(control)
    source = args.source.resolve()
    hearts = {"old": args.heart_old.resolve(), "new": args.heart_new.resolve()}
    work, artifacts = args.work.resolve(), args.artifacts.resolve()
    paths = [control, source, *hearts.values(), work, artifacts, evidence]
    if len(set(paths)) != len(paths):
        raise RuntimeError("Separate control/source/native/work/artifact/evidence directories required")
    for tree, pin in [(control, identity["integration_sha"]), (source, coverage.SOURCE),
                      *[(heart, coverage.HEART) for heart in hearts.values()]]:
        if coverage.git(tree, "rev-parse", "HEAD") != pin or coverage.git(tree, "status", "--porcelain"):
            raise RuntimeError("Exact clean fresh checkout required: " + str(tree))
    frozen = dict(coverage.HASHES)
    frozen[GENPROTO_DECLARATION] = GENPROTO_DECLARATION_SHA
    frozen[APPROVAL_ROOT + "/revision-14/native-heart-integration.patch"] = OLD_PATCH
    frozen[APPROVAL_ROOT + "/revision-14/native-heart-integration.json"] = OLD_INVENTORY
    for path, expected in frozen.items():
        if coverage.digest(source / path) != expected:
            raise RuntimeError("Reviewed source input differs: " + path)
    verify_pair_inputs(control)
    version = subprocess.check_output(["go", "version"], text=True).strip()
    if version != "go version go1.26.5 linux/amd64":
        raise RuntimeError("Expected exact Linux Go 1.26.5")
    if shutil.disk_usage(work).free < 8 * 1024**3:
        raise RuntimeError("Disk reserve below preserved 8 GiB guard")
    build_root = work / "build"
    build_root.mkdir(exist_ok=False)
    artifacts.mkdir(parents=True, exist_ok=True)
    if any(artifacts.iterdir()):
        raise RuntimeError("Fresh empty binary artifact directory required")
    commands = []

    def run(command, name, cwd=source, env=None, timeout=900):
        commands.append(dict(name=name, argv=[str(v) for v in command], cwd=str(cwd),
                             environment={key: (env or os.environ).get(key) for key in
                                          ["GOWORK", "GOFLAGS", "GOPROXY", "GOTOOLCHAIN", "GOMAXPROCS",
                                           "CGO_ENABLED", "CGO_LDFLAGS", "CC", "CXX"]}))
        coverage.write_receipt(evidence / "commands.json", commands)
        with (evidence / (name + ".log")).open("x", encoding="utf8") as log:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            raise RuntimeError(name + " failed; see retained log")

    helper_path = source / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    native_helper = load_module("pair_native_builder", helper_path)
    pair_root = control / PAIR_DIRECTORY
    pair_controller = load_module("preserved_pair_controller", pair_root / "run_pairs.py")
    fixture = pair_root / "pair_phase_test.go"
    run([sys.executable, "-B", str(pair_root / "test_controls.py")], "preserved-controller-controls",
        cwd=pair_root)
    manifest = {"schema": 1}
    build_receipts = {}
    for role, revision in [("old", 14), ("new", 15)]:
        heart = hearts[role]
        approval = source / APPROVAL_ROOT / ("revision-" + str(revision))
        patch, inventory = approval / "native-heart-integration.patch", approval / "native-heart-integration.json"
        patch_sha = OLD_PATCH if role == "old" else coverage.PATCH
        run([sys.executable, "-B", str(helper_path), "--heart-source", str(heart),
             "--patch", str(patch), "--inventory", str(inventory),
             "--approved-patch-sha256", patch_sha, "--apply-approved-patch",
             "--target", "verify", "--evidence", str(evidence / (role + "-source"))],
            role + "-source-preflight")
        tantivy = native_helper.fetch_tantivy(heart, "linux-amd64-musl")
        if tantivy["archive_sha256"] != TANTIVY:
            raise RuntimeError("Unexpected pinned Tantivy artifact")
        role_work = build_root / role
        role_work.mkdir()
        gowork = role_work / "go.work"
        # The existing 947 compatibility probe already pins this post-split
        # genproto. Keep only this role's Heart module in the workspace, and
        # resolve the obsolete root-module overlap without overriding native code.
        gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace "
                          + GENPROTO_PATH + " => " + GENPROTO_PATH + " " + GENPROTO_VERSION + "\n",
                          encoding="utf8")
        overlay_destination = heart / "pkg/lib/localstore/objectstore/spaceindex/pinkha_t5_pair_phase_test.go"
        if overlay_destination.exists():
            raise RuntimeError("Preserved pair overlay would replace a native source file")
        overlay = role_work / "overlay.json"
        overlay.write_text(json.dumps({"Replace": {str(overlay_destination): str(fixture)}}) + "\n",
                           encoding="utf8")
        env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1",
                   GOMAXPROCS="2", GOFLAGS="-mod=readonly",
                   CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
        # Fetch only modules selected by the immutable go.mod/go.sum first.
        # Compilation and process pairing then use that exact offline module cache.
        run(["go", "mod", "download"], role + "-pinned-module-download", cwd=heart, env=env)
        env["GOPROXY"] = "off"
        run(["go", "list", "-m", "-json", "all"], role + "-resolved-modules", cwd=heart, env=env)
        run(["go", "list", "-m", "-json", GENPROTO_PATH], role + "-genproto-selection", cwd=heart, env=env)
        selected = json.loads((evidence / (role + "-genproto-selection.log")).read_text(encoding="utf8"))
        genproto = validate_genproto_selection(selected)
        summary = native_helper.TAG + "-pinkha-native-derived-v1-" + patch_sha
        if role == "new":
            summary += "-pinkha-native-t5-lookup-v1-" + patch_sha
        fixture_sha = PAIR_HASHES["pair_phase_test.go"]
        ldflags = ("-extldflags=-static"
                   " -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + coverage.HEART
                   + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + summary
                   + " -X github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex.pairFixtureSHA=" + fixture_sha)
        binary = artifacts / ("pinkha-r" + str(revision) + "-spaceindex.test")
        run(["go", "test", "-c", "-p", "1", "-tags", TAGS, "-overlay", str(overlay),
             "-ldflags", ldflags, "-o", str(binary), "./pkg/lib/localstore/objectstore/spaceindex"],
            role + "-compile", cwd=heart, env=env)
        entry = dict(binary=str(binary), binary_sha256=pair_controller.digest(binary),
                     source=str(heart), inventory=str(inventory), patch=str(patch),
                     fixture_sha256=fixture_sha)
        verified = pair_controller.verify_artifact(role, entry)
        manifest[role] = entry
        build_receipts[role] = dict(status="BINARY_BUILT_SOURCE_VERIFIED", **verified,
                                    go_version=version, linked_summary=summary, tantivy=tantivy,
                                    genproto_resolution=genproto,
                                    overlay=json.loads(overlay.read_text()), gowork=gowork.read_text())
        coverage.write_receipt(evidence / (role + "-build.json"), build_receipts[role])
    manifest_path = evidence / "manifest.json"
    coverage.write_receipt(manifest_path, manifest)
    pair_workspace = work / "pair-sequence"
    try:
        run([sys.executable, "-B", str(pair_root / "run_pairs.py"), "--manifest", str(manifest_path),
             "--workspace", str(pair_workspace)], "native-pair-controller",
            cwd=control, env=dict(os.environ, GOTOOLCHAIN="local", GOPROXY="off", GOMAXPROCS="2"))
    finally:
        if pair_workspace.is_dir():
            destination = evidence / "pair-sequence"
            destination.mkdir(exist_ok=True)
            for path in pair_workspace.iterdir():
                if path.is_file() and path.suffix in [".json", ".log"]:
                    shutil.copyfile(path, destination / path.name)
    result_path = evidence / "pair-sequence/result.json"
    result = json.loads(result_path.read_text(encoding="utf8"))
    actual_counts = validate_pair_result(result)
    verify_pair_inputs(control)
    if coverage.require_identity(control) != identity or coverage.git(source, "status", "--porcelain"):
        raise RuntimeError("Source/control identity changed during native pairing")
    for path, expected in frozen.items():
        if coverage.digest(source / path) != expected:
            raise RuntimeError("Frozen source changed during pairing: " + path)
    for role in hearts:
        if pair_controller.verify_artifact(role, manifest[role]) != {
                key: value for key, value in build_receipts[role].items()
                if key in result["identities"][role]}:
            raise RuntimeError("Binary/source inputs changed after the completed sequence")
    return dict(status="COMPONENT_STORE_PAIR_PASS", **identity, source_sha=coverage.SOURCE,
                heart_sha=coverage.HEART, preserved_pair_source_sha=PAIR_SOURCE,
                preserved_pair_hashes=PAIR_HASHES, actual_counts=actual_counts,
                binary_sha256={role: entry["binary_sha256"] for role, entry in manifest.items() if role != "schema"},
                pair_receipt_sha256=coverage.digest(result_path), go_version=version)


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    for name in ["source", "heart-old", "heart-new", "work", "artifacts", "evidence"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(),
                   component="compatibility-pairs", full_F10="NOT_PROVEN",
                   export_status="NOT_RUN_COMPONENT_NO_RPC", swift_pairing_status="NOT_RUN",
                   client_enablement=CLIENT_DISABLED,
                   scope="two exact Go spaceindex test binaries and four processes on one synthetic on-disk store")
    receipt_path = evidence / "ci-result.json"
    coverage.write_receipt(receipt_path, receipt)
    try:
        receipt.update(execute(args, Path(__file__).resolve().parents[2], evidence))
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    coverage.write_receipt(receipt_path, receipt)
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "COMPONENT_STORE_PAIR_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
