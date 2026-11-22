#!/usr/bin/env python3
"""Compile additive CAS candidates; retain qualified scopes for a narrow continuation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys

import contract
import resume_native

sys.path.insert(0, str(contract.ROOT / "Tools/PinkhaNativeDerived"))
sys.path.insert(0, str(contract.ROOT / "Tools/TorahNativeOperations"))
import build_custom_heart as binary_tools
import coherent_read_runtime as composition
from coherent_apple import contract as original
import run_account_lifecycle as processes
import run_native_registration as modules


def snapshot(control):
    names = subprocess.check_output(["git", "-C", str(control), "ls-files", "-z", "--",
        "Tools/PinkhaSemanticAnchor", "Tools/PinkhaNativeDerived", "Tools/TorahNativeOperations",
        ".github/workflows/pinkha-semantic-anchor-native.yml"]).decode().split("\0")
    return {name: contract.digest(control / name) for name in names if name}


def verify_candidate(heart, qualified, additions):
    rows = {item["path"]: item for item in qualified["inventory"]["files"]}
    contract.require(len(rows) == 139 and not rows.keys() & additions.keys(), "Candidate replaced a qualified native source")
    actual = {name: contract.digest(heart / name) for name in rows | additions}
    contract.require(actual == {**{name: item["after_sha256"] for name, item in rows.items()}, **additions},
                     "Qualified139 or additive CAS source changed")
    tracked = {name for name, item in rows.items() if item["before_sha256"] is not None}
    changed = set(binary_tools.git(heart, "diff", "--name-only", "HEAD").splitlines())
    untracked = set(binary_tools.git(heart, "ls-files", "--others", "--exclude-standard").splitlines())
    contract.require(changed == tracked and untracked == (rows.keys() - tracked) | additions.keys(),
                     "Unexpected native tracked mutation or source addition")
    pins = qualified["generation"]["module_sha256"]
    contract.require({name: contract.digest(heart / name) for name in pins} == pins,
                     "Original native Go module graph changed")
    return actual


def execute(args, receipt, run):
    control, heart, work, evidence = args.control, args.heart, args.work, args.evidence
    contract.require(control == contract.ROOT and len({control, heart, work, evidence}) == 4
                     and all(not path.is_relative_to(root) for root in (control, heart) for path in (work, evidence)),
                     "Exact controller and separate native/work/evidence paths required")
    contract.require(platform.system() == "Linux" and platform.machine() == "x86_64"
                     and os.environ.get("T2_GO_IMAGE") == contract.IMAGE,
                     "The exact qualified musl build image is required")
    contract.require(subprocess.check_output(["go", "version"], text=True).strip() == "go version go1.26.5 linux/amd64",
                     "Pinned native Go compiler required")
    for path, expected in ((control, args.expected_app_sha), (heart, contract.HEART)):
        contract.require(binary_tools.git(path, "rev-parse", "HEAD") == expected
                         and not binary_tools.git(path, "status", "--porcelain"), "Clean exact source required")
    contract.require(not work.exists() and shutil.disk_usage(work.parent).free >= 8 * 1024**3,
                     "Fresh work directory and 8 GiB build reserve required")
    work.mkdir()
    source_before = snapshot(control)
    contract.save(evidence / "control-source-before.json", source_before)
    additions = contract.source_manifest()
    retained = contract.retained_contract()
    contract.save(evidence / "retained-pure-contract-controls.json", retained)
    shutil.copytree(contract.HERE / contract.RETAINED, evidence / "original-pure-contract-controls")
    qualified = original.qualified_native(control / contract.PROOF)
    original.validate_native_run(contract.load(args.original_run))
    run(["git", "apply", "--check", str(qualified["patch"])], "qualified-patch-check", heart, os.environ.copy())
    run(["git", "apply", str(qualified["patch"])], "qualified-patch-apply", heart, os.environ.copy())
    native139 = composition.verify_source(heart, qualified["inventory"], qualified["generation"]["module_sha256"])
    contract.save(evidence / "qualified139-source-before.json", native139)
    for name, expected in additions.items():
        source, target = contract.HERE / "native" / name, heart / name
        contract.require(not target.exists() and contract.digest(source) == expected,
                         "Additive native candidate may not replace an existing file")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    candidate_before = verify_candidate(heart, qualified, additions)
    contract.save(evidence / "candidate-source-before.json", candidate_before)
    shutil.copyfile(contract.HERE / "native-source.json", evidence / "candidate-additions.json")
    tantivy = binary_tools.fetch_tantivy(heart, "linux-amd64-musl")
    contract.require(tantivy["archive_sha256"] == modules.TANTIVY_SHA, "Wrong native Tantivy bytes")
    contract.save(evidence / "tantivy.json", tantivy)
    gowork = work / "go.work"
    gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + modules.GENPROTO_PATH
                     + " => " + modules.GENPROTO_PATH + " " + modules.GENPROTO_VERSION + "\n", encoding="utf8")
    env = dict(os.environ, GOMAXPROCS="2", GOMEMLIMIT="2048MiB", CGO_ENABLED="1", GOTOOLCHAIN="local", GOFLAGS="-mod=readonly",
               GOWORK=str(gowork), CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
    run(["go", "mod", "download"], "download-modules", heart, env, 900)
    env["GOPROXY"] = "off"
    run(["go", "list", "-m", "-json", modules.GENPROTO_PATH], "genproto", heart, env, 120)
    selected = contract.load(evidence / "genproto.log")
    genproto = selected.get("Replace", selected)
    contract.require(genproto.get("Path") == modules.GENPROTO_PATH and genproto.get("Version") == modules.GENPROTO_VERSION
                     and genproto.get("Sum") == modules.GENPROTO_SUM and genproto.get("GoModSum") == modules.GENPROTO_MOD_SUM,
                     "Wrong native genproto dependency closure")
    candidate_sha = contract.digest(contract.HERE / "native-source.json")
    version = "pinkha-semantic-anchor-native-candidate-v1-" + candidate_sha
    # Deliberately never advertise the original production139 runtime marker.
    ldflags = "-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + contract.HEART + \
              " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + version
    retained = None
    selection = contract.CASES
    binaries, results, current_results = {}, {}, {}
    if args.component_run is not None:
        retained = resume_native.retain(contract.load(args.component_run), native139, additions, evidence)
        selection = resume_native.SELECTED_CASES
        results.update(retained["results"])
        receipt["retained_native_components"] = retained
    for package, cases in selection.items():
        label = package.rsplit("/", 1)[-1]
        binary = work / (label + ".test")
        run(["go", "test", "-c", "-p", "1", "-tags", processes.TAGS, "-ldflags", ldflags,
             "-o", str(binary), "./" + package], "compile-" + label, heart, env, 1800)
        binary.chmod(0o755)
        for method in cases:
            contract.require(binary_tools.contains(binary, method.encode()), "Native executable omits its selected method")
        binaries[package] = dict(path=binary.name, sha256=contract.digest(binary), selected_methods=sorted(cases))
        contract.require(verify_candidate(heart, qualified, additions) == candidate_before
                         and snapshot(control) == source_before, "Source changed while compiling native controls")
    # Compile every selected current binary first. Retained packages are not
    # executed or rebuilt only to recreate an already qualified result.
    receipt["built_control_binaries"] = binaries
    receipt["qualified_partial_results"] = results
    for package, cases in selection.items():
        label = package.rsplit("/", 1)[-1]
        binary = work / binaries[package]["path"]
        selector = "^(" + "|".join(sorted(cases)) + ")$"
        run(["go", "tool", "test2json", "-t", "-p", "github.com/anyproto/anytype-heart/" + package,
             str(binary), "-test.v=test2json", "-test.run=" + selector, "-test.timeout=180s", "-test.count=1"],
             "execute-" + label, heart, env, 240)
        current_results[package] = contract.outcomes(evidence / ("execute-" + label + ".log"),
            "github.com/anyproto/anytype-heart/" + package, cases)
        results[package] = resume_native.combine(results[package], current_results[package]) if package in results else current_results[package]
        contract.require(contract.digest(binary) == binaries[package]["sha256"], "Executed native binary changed")
        contract.require(verify_candidate(heart, qualified, additions) == candidate_before
                         and snapshot(control) == source_before, "Source changed during selected native controls")
        # A later selected package can fail. Preserve completed scopes now so a
        # source-bound continuation can retain them instead of rerunning them.
        contract.save(evidence / ("source-after-" + label + ".json"), candidate_before)
        contract.save(evidence / "qualified-partial-results.json", results)
    after = verify_candidate(heart, qualified, additions)
    contract.require(after == candidate_before and snapshot(control) == source_before, "Native/control source changed during execution")
    contract.require(sum(value["top_level"] for value in results.values()) == 9
                     and sum(value["terminal"] for value in results.values()) == 27,
                     "Incomplete new native control selection")
    contract.save(evidence / "candidate-source-after.json", after)
    contract.save(evidence / "control-source-after.json", snapshot(control))
    receipt.update(status="PASS_NATIVE_SEMANTIC_ANCHOR_COMPONENT_AND_STORAGE_CONTROLS", heart_sha=contract.HEART,
        native_source_run=contract.NATIVE_RUN, original_native139_source_sha256=native139,
        candidate_source_count=148, candidate_additions_count=9, candidate_additions_manifest_sha256=candidate_sha,
        candidate_source_sha256=after, candidate_runtime_version=version, binaries=binaries, results=results,
        retained_pure_contract_methods=5,
        retained_native_top_level_methods=7 if retained else 0, retained_native_terminal_cases=25 if retained else 0,
        original_native_component_run=resume_native.ORIGINAL_RUN if retained else None,
        actual_new_top_level_methods=sum(value["top_level"] for value in current_results.values()),
        actual_new_terminal_cases=sum(value["terminal"] for value in current_results.values()),
        qualified_total_top_level_methods=9, qualified_total_terminal_cases=27,
        current_execution_results=current_results, retained_methods_executed_again=0,
        actual_fail=0, actual_skip=0, native_modules=qualified["generation"]["module_sha256"], genproto=genproto,
        protobuf_generation_executed=0, shipping_frameworks_built=0,
        claim_boundary="Text/state component and real signed-storage/ACL lease controls; actual production Page Apply, wire, account lifecycle and mounted Apple acceptance remain separate.")


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control", "heart", "work", "evidence", "original-run"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--component-run", type=Path,
                        help="Exact original failed run metadata; retains seven passing methods and executes only the missing two")
    args = parser.parse_args()
    for name in ("control", "heart", "work", "evidence", "original_run"):
        setattr(args, name, getattr(args, name).resolve())
    if args.component_run is not None:
        args.component_run = args.component_run.resolve()
    args.evidence.mkdir(parents=True, exist_ok=True)
    path = args.evidence / "receipt.json"
    contract.require(not path.exists(), "Fresh native CAS receipt required")
    receipt = dict(status="NOT_RUN", app_sha=args.expected_app_sha, run_id=os.environ.get("GITHUB_RUN_ID"),
                   run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), commands=[], started_at=datetime.now(timezone.utc).isoformat(),
                   **contract.LIMITS)
    contract.require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha)
                     and (receipt["run_id"] or "").isdigit() and (receipt["run_attempt"] or "").isdigit(),
                     "Exact source/run/attempt required")
    handlers = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    cancelled = False
    def cancel(number, _):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in handlers:
        signal.signal(number, cancel)
    def run(argv, name, cwd, env, timeout=900):
        entry = dict(name=name, argv=list(map(str, argv)), status="RUNNING", timeout_seconds=timeout)
        receipt["commands"].append(entry); contract.save(path, receipt)
        try:
            entry["pid"] = processes.run_process(entry["argv"], cwd, env, args.evidence / (name + ".log"), timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as error:
            entry.update(status="FAIL", error_type=type(error).__name__, error=str(error))
            raise
        finally:
            log = args.evidence / (name + ".log")
            if log.is_file():
                entry.update(log_sha256=contract.digest(log), log_bytes=log.stat().st_size)
            contract.save(path, receipt)
    try:
        execute(args, receipt, run)
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat(); contract.save(path, receipt)
        for number, handler in handlers.items():
            signal.signal(number, handler)
    return int(receipt["status"] != "PASS_NATIVE_SEMANTIC_ANCHOR_COMPONENT_AND_STORAGE_CONTROLS")


if __name__ == "__main__":
    raise SystemExit(main())
