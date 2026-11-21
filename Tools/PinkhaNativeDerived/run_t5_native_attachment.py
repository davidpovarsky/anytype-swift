"""Run the real native attachment fix and its original-source counterexample.

This gate uses an isolated pinned Heart checkout. It never rewrites the
immutable r14/r15 approvals and does not claim old-client or Apple acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

from build_custom_heart import fetch_tantivy


HEART_SHA = "d98420b1113536afd08cde6de9a5816f6d27ffff"
BASE_PATCH_SHA256 = "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077"
PATCH_SHA256 = "d055933d365d3f0453ad42ce4eb4463a25deceac3d0df11162d460896810a6b4"
IMAGE = "golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8"
APPROVAL = "docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-14"
GENERATED = "docs/validation/20261119-t5-native-attachment/generated"
DETAILS = "core/block/editor/basic/details.go"
BASIC_PACKAGE = "github.com/anyproto/anytype-heart/core/block/editor/basic"
EXPLICIT_PACKAGE = "github.com/anyproto/anytype-heart/core/block/detailservice"
BASIC_TEST = "TestTorahOrdinaryDetailsDoNotAttachProjectedProperties"
EXPLICIT_TEST = "TestTorahExplicitAttachmentsSurviveOrdinaryDetailsEdits"
NEGATIVE_CASES = {
    BASIC_TEST + "/" + api + "/" + attached
    for api in ("SetDetails", "UpdateDetails")
    for attached in ("unattached", "explicit-source-already-attached")
}
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(root: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *arguments])


def scoped_patch(patch: bytes, path: str) -> bytes:
    marker = f"diff --git a/{path} b/{path}\n".encode()
    sections = [b"diff --git " + part for part in patch.split(b"diff --git ")[1:]]
    found = [part for part in sections if part.startswith(marker)]
    if len(found) != 1:
        raise RuntimeError("Original patch does not identify one exact details file")
    return found[0]


def qualify_log(path: Path, exit_code: int, *, negative: bool) -> dict:
    starts: Counter = Counter()
    endings: dict[tuple[str, str], list[str]] = {}
    packages: dict[str, list[str]] = {}
    output: dict[tuple[str, str], str] = {}
    with path.open(errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            package, test, action = event.get("Package"), event.get("Test"), event.get("Action")
            if not package:
                continue
            if test:
                key = (package, test)
                if action == "run":
                    starts[key] += 1
                if action in {"pass", "fail", "skip"}:
                    endings.setdefault(key, []).append(action)
                if action == "output":
                    output[key] = output.get(key, "") + event.get("Output", "")
            elif action in {"pass", "fail", "skip"}:
                packages.setdefault(package, []).append(action)
    if not starts or set(starts) != set(endings) or any(count != 1 for count in starts.values()):
        raise RuntimeError("Native test start/terminal inventory is absent, duplicate, or incomplete")
    if negative:
        expected = {(BASIC_PACKAGE, name) for name in NEGATIVE_CASES | {BASIC_TEST}}
        if exit_code != 1 or set(endings) != expected or any(actions != ["fail"] for actions in endings.values()):
            raise RuntimeError("Pre-fix control did not fail every exact ordinary-edit case")
        if packages != {BASIC_PACKAGE: ["fail"]}:
            raise RuntimeError("Pre-fix control has the wrong native package outcome")
        for case in NEGATIVE_CASES:
            reason = ("an ordinary edit must preserve the existing attachment decision" if case.endswith("/unattached")
                      else "projected topics must not create an attachment")
            if reason not in output.get((BASIC_PACKAGE, case), ""):
                raise RuntimeError("Pre-fix case failed for an unrelated reason: " + case)
        status = "PASS_EXPECTED_ORIGINAL_SOURCE_FAILURE"
    else:
        expected = {(BASIC_PACKAGE, name) for name in NEGATIVE_CASES | {BASIC_TEST}}
        expected.add((EXPLICIT_PACKAGE, EXPLICIT_TEST))
        if exit_code != 0 or not expected.issubset(endings) or any(actions != ["pass"] for actions in endings.values()):
            raise RuntimeError("Native packages or exact new fixture inventory did not pass without skips")
        if packages != {BASIC_PACKAGE: ["pass"], EXPLICIT_PACKAGE: ["pass"]}:
            raise RuntimeError("Both actual native packages must complete")
        status = "PASS_ACTUAL_NATIVE_PACKAGES"
    return {"status": status, "exit_code": exit_code, "log_sha256": digest(path),
            "tests": [{"package": p, "name": t, "outcome": endings[p, t][0]} for p, t in sorted(endings)],
            "packages": packages}


def run(argv: list[str], cwd: Path, log: Path, env: dict, timeout: int, *, require_success: bool = True) -> dict:
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with log.open("w") as stream:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            save(log.with_suffix(".command.json"), {"argv": argv, "pid": process.pid, "status": "TIMEOUT",
                                                   "started_unix": started, "ended_unix": time.time()})
            raise RuntimeError("Native command exceeded its finite deadline: " + log.name)
    result = {"argv": argv, "pid": process.pid, "exit_code": code, "started_unix": started,
              "ended_unix": time.time(), "log_sha256": digest(log)}
    save(log.with_suffix(".command.json"), result)
    if require_success and code:
        raise RuntimeError("Native command failed: " + log.name)
    return result


def source_inputs(control: Path) -> dict[str, str]:
    roots = ["Modules/PinkhaHeart", "Tools/TorahNativeDerivedSpike", "Tools/PinkhaNativeDerived",
             APPROVAL, GENERATED, ".github/workflows/pinkha-t5-native-attachment.yml",
             ".github/workflows/torah-inspector-ipados27.yml"]
    paths = git(control, "ls-files", "-z", "--", *roots).decode().strip("\0").split("\0")
    return {p: digest(control / p) for p in paths if p}


def verify_applied(heart: Path, inventory: dict) -> dict[str, str]:
    actual = {}
    for entry in inventory["files"]:
        p = entry["path"]
        actual[p] = digest(heart / p)
        if actual[p] != entry["after_sha256"]:
            raise RuntimeError("Applied native source changed: " + p)
    return actual


def native_stage(receipt: dict, key: str, command: list[str], heart: Path, log: Path,
                 env: dict, timeout: int, *, negative: bool) -> None:
    receipt[key] = {"status": "STARTED_RESULT_UNQUALIFIED"}
    try:
        result = run(command, heart, log, env, timeout, require_success=False)
        receipt[key].update(result)
        receipt[key].update(qualify_log(log, result["exit_code"], negative=negative))
    except Exception as error:
        receipt[key].update(status="FAIL", error=str(error))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--heart", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    control, heart, work, evidence = (x.resolve() for x in (args.control, args.heart, args.work, args.evidence))
    work.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "NOT_RUN", "native_packages": "NOT_RUN", "original_source_negative_control": "NOT_RUN",
               "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
               "app_sha": os.environ.get("GITHUB_SHA"), "heart_sha": HEART_SHA, "patch_sha256": PATCH_SHA256,
               "apple_runtime": "NOT_RUN", "unmodified_old_client_compatibility": "NOT_PROVEN",
               "full_t5_acceptance": "NOT_PROVEN"}
    before = applied = inventory = expected_original = overlay = baseline_file = None
    try:
        env = dict(os.environ, GOMAXPROCS="2", CGO_ENABLED="1", GOWORK="off", GOTOOLCHAIN="local")
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise RuntimeError("This gate requires the pinned Linux amd64 musl container")
        if subprocess.check_output(["go", "version"], text=True).strip() != "go version go1.26.5 linux/amd64":
            raise RuntimeError("Wrong native Go toolchain")
        if os.environ.get("T5_GO_IMAGE") != IMAGE:
            raise RuntimeError("Missing exact container image binding")
        if git(control, "rev-parse", "HEAD").decode().strip() != receipt["app_sha"]:
            raise RuntimeError("Integration checkout differs from the dispatched source")
        if git(control, "status", "--porcelain").strip():
            raise RuntimeError("Integration source is not clean")
        if git(heart, "rev-parse", "HEAD").decode().strip() != HEART_SHA or git(heart, "status", "--porcelain").strip():
            raise RuntimeError("Heart must start as the clean pinned checkout")
        before = source_inputs(control)
        save(evidence / "source-inputs-before.json", before)
        original_patch = control / APPROVAL / "native-heart-integration.patch"
        if digest(original_patch) != BASE_PATCH_SHA256:
            raise RuntimeError("Immutable r14 patch changed")
        run([sys.executable, "-B", str(control / "Tools/TorahNativeDerivedSpike/prepare_heart_integration.py"),
             "--heart-source", str(heart), "--output", str(work / "generated")],
            control, evidence / "generate.log", env, 120)
        generated = work / "generated/native-heart-integration.patch"
        inventory_path = work / "generated/native-heart-integration.json"
        inventory = json.loads(inventory_path.read_text())
        frozen = control / GENERATED
        if (digest(generated) != PATCH_SHA256 or inventory["patch_sha256"] != PATCH_SHA256 or
                generated.read_bytes() != (frozen / generated.name).read_bytes() or
                inventory_path.read_bytes() != (frozen / inventory_path.name).read_bytes()):
            raise RuntimeError("Fresh generator output differs from the frozen reviewed candidate")
        save(evidence / "candidate-inventory.json", inventory)
        run(["git", "-c", "core.autocrlf=false", "apply", "--check", str(generated)], heart, evidence / "apply-check.log", env, 30)
        run(["git", "-c", "core.autocrlf=false", "apply", str(generated)], heart, evidence / "apply.log", env, 30)
        applied = verify_applied(heart, inventory)
        save(evidence / "applied-native-source.json", applied)
        baseline = work / "original-r14"
        baseline_file = baseline / DETAILS
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        baseline_file.write_bytes(git(heart, "show", HEART_SHA + ":" + DETAILS))
        baseline_patch = work / "original-r14-details.patch"
        baseline_patch.write_bytes(scoped_patch(original_patch.read_bytes(), DETAILS))
        run(["git", "-c", "core.autocrlf=false", "apply", str(baseline_patch)], baseline, evidence / "prepare-original-source.log", env, 30)
        original_inventory = json.loads((control / APPROVAL / "native-heart-integration.json").read_text())
        expected_original = next(e["after_sha256"] for e in original_inventory["files"] if e["path"] == DETAILS)
        if digest(baseline_file) != expected_original:
            raise RuntimeError("Counterexample source differs from the actual immutable r14 details file")
        overlay = work / "original-source-overlay.json"
        save(overlay, {"Replace": {str(heart / DETAILS): str(baseline_file)}})
        save(evidence / "counterexample-source.json", {"path": DETAILS, "sha256": expected_original,
                                                       "candidate_sha256": applied[DETAILS], "patch_sha256": BASE_PATCH_SHA256})
        save(evidence / "tantivy.json", fetch_tantivy(heart, "linux-amd64-musl"))
        env["CGO_LDFLAGS"] = "-L" + str(heart / "deps/libs/linux-amd64-musl")
        command = ["go", "test", "-mod=readonly", "-p", "2", "-json", "-count=1", "-tags", TAGS]
        positive_log = evidence / "native-packages.log"
        native_stage(receipt, "native_packages",
                     command + ["-timeout", "10m", "./core/block/editor/basic", "./core/block/detailservice"],
                     heart, positive_log, env, 1800, negative=False)
        negative_log = evidence / "original-source-negative.log"
        native_stage(receipt, "original_source_negative_control",
                     command + ["-overlay", str(overlay), "-timeout", "2m", "-run", "^" + BASIC_TEST + "$", "./core/block/editor/basic"],
                     heart, negative_log, env, 300, negative=True)
        receipt["status"] = "PASS_NATIVE_ATTACHMENT_CORRECTION"
    except Exception as error:
        receipt["status"] = "FAIL"
        receipt["error"] = str(error)
    finally:
        final_errors = []
        if before is not None:
            try:
                after = source_inputs(control)
                save(evidence / "source-inputs-after.json", after)
                if after != before:
                    raise RuntimeError("Integration source changed during native verification")
            except Exception as error:
                final_errors.append(str(error))
        if applied is not None:
            try:
                actual_after = verify_applied(heart, inventory)
                save(evidence / "applied-native-source-after.json", actual_after)
                if actual_after != applied:
                    raise RuntimeError("Applied native source changed during verification")
            except Exception as error:
                final_errors.append(str(error))
        if overlay is not None:
            try:
                if digest(baseline_file) != expected_original or json.loads(overlay.read_text()) != {"Replace": {str(heart / DETAILS): str(baseline_file)}}:
                    raise RuntimeError("Original-source compile overlay changed during verification")
            except Exception as error:
                final_errors.append(str(error))
        receipt["final_source_validation"] = {"status": "FAIL" if final_errors else "PASS" if applied is not None else "NOT_RUN",
                                               "errors": final_errors}
        if final_errors:
            receipt["status"] = "FAIL"
            receipt.setdefault("error", final_errors[0])
        save(evidence / "attachment-receipt.json", receipt)
    return int(receipt["status"] != "PASS_NATIVE_ATTACHMENT_CORRECTION")


if __name__ == "__main__":
    raise SystemExit(main())
