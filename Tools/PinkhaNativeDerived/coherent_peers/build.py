#!/usr/bin/env python3
"""Compile one frozen coherent139 peer fixture; select no prior test suite."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys

import contract

sys.path.insert(0, str(contract.ROOT / "Tools/PinkhaNativeDerived"))
sys.path.insert(0, str(contract.ROOT / "Tools/TorahNativeOperations"))
import build_custom_heart as binary_tools
import coherent_read_runtime as composition
from coherent_apple import contract as original
import run_account_lifecycle as processes
import run_account_rpc as account
import run_native_clients as peers
import run_native_registration as modules


def source_snapshot(control):
    names = subprocess.check_output(["git", "-C", str(control), "ls-files", "-z", "--",
        "Tools/PinkhaNativeDerived", "Tools/TorahNativeOperations", ".github/workflows/pinkha-coherent-heart-peers.yml"]).decode().split("\0")
    return {name: contract.digest(control / name) for name in names if name}


def execute(args, receipt, run):
    control, heart, work, evidence = args.control, args.heart, args.work, args.evidence
    contract.require(platform.system() == "Linux" and platform.machine() == "x86_64"
                     and os.environ.get("T2_GO_IMAGE") == contract.IMAGE, "Exact musl build image required")
    contract.require(subprocess.check_output(["go", "version"], text=True).strip() == "go version go1.26.5 linux/amd64",
                     "Pinned native Go compiler required")
    for path, expected in ((control, args.expected_app_sha), (heart, contract.HEART)):
        contract.require(binary_tools.git(path, "rev-parse", "HEAD") == expected
                         and not binary_tools.git(path, "status", "--porcelain"), "Clean exact source required")
    contract.require(not work.exists() and shutil.disk_usage(work.parent).free >= 8 * 1024**3,
                     "Fresh build directory and 8 GiB reserve required")
    work.mkdir(mode=0o755)
    before = source_snapshot(control)
    contract.save(evidence / "build-control-source-before.json", before)
    proof = control / contract.PROOF
    qualified = original.qualified_native(proof)
    original.validate_native_run(contract.load(args.original_run))
    run(["git", "apply", "--check", str(qualified["patch"])], "qualified-patch-check", heart, os.environ.copy())
    run(["git", "apply", str(qualified["patch"])], "qualified-patch-apply", heart, os.environ.copy())
    actual = composition.verify_source(heart, qualified["inventory"], qualified["generation"]["module_sha256"])
    contract.save(evidence / "native-source-before.json", actual)
    # Keep original helpers and their assertions byte-for-byte. Their existing
    # tests are compiled as dependencies but the new runner selects only METHOD.
    manifest, account_sha, folder = account.fixture_inputs(control)
    fixture_directory = account.prepare_fixtures(control, work, manifest, folder, run)
    peer_manifest, peer_files = peers.source_inputs(control)
    # The legacy helper implements the same symbols as the new helper and is
    # deliberately excluded, exactly as in the retained new-role builder.
    names = ("account_phase_test.go", "new_runtime_test.go", "native_handler_test.go", "native_rpc_account_test.go")
    overlays = {str(heart / "clientlibrary/service" / ("coherent_helper_" + name)): str(fixture_directory / name)
                for name in names}
    overlays.update({str(heart / "clientlibrary/service" / ("coherent_helper_" + name)): str(path)
                     for name, path in peer_files.items()})
    own = control / "Tools/PinkhaNativeDerived/coherent_peers/native_peer_test.go"
    overlays[str(heart / "clientlibrary/service/coherent_native_peer_test.go")] = str(own)
    contract.require(all(not Path(name).exists() for name in overlays), "Fixture must not replace production source")
    hashes = {Path(name).name: contract.digest(Path(path)) for name, path in overlays.items()}
    fixture_sha = contract.sha(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode())
    overlay_path = work / "peer-overlay.json"
    contract.save(overlay_path, {"Replace": overlays})
    tantivy = binary_tools.fetch_tantivy(heart, "linux-amd64-musl")
    contract.require(tantivy["archive_sha256"] == modules.TANTIVY_SHA, "Wrong native Tantivy bytes")
    contract.save(evidence / "tantivy.json", tantivy)
    gowork = work / "go.work"
    gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + modules.GENPROTO_PATH
                     + " => " + modules.GENPROTO_PATH + " " + modules.GENPROTO_VERSION + "\n", encoding="utf8")
    env = dict(os.environ, GOMAXPROCS="2", CGO_ENABLED="1", GOTOOLCHAIN="local", GOFLAGS="-mod=readonly",
               GOWORK=str(gowork), CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
    run(["go", "mod", "download"], "download-modules", heart, env, 900)
    env["GOPROXY"] = "off"
    run(["go", "list", "-m", "-json", modules.GENPROTO_PATH], "genproto", heart, env, 120)
    selected = contract.load(evidence / "genproto.log")
    genproto = selected.get("Replace", selected)
    contract.require(genproto.get("Path") == modules.GENPROTO_PATH and genproto.get("Version") == modules.GENPROTO_VERSION
                     and genproto.get("Sum") == modules.GENPROTO_SUM and genproto.get("GoModSum") == modules.GENPROTO_MOD_SUM,
                     "Wrong native genproto closure")
    symbols = {
        "github.com/anyproto/anytype-heart/util/vcs.GitCommit": contract.HEART,
        "github.com/anyproto/anytype-heart/util/vcs.GitSummary": qualified["version"],
        "github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRuntimeRole": "new",
        "github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountFixtureSHA": account_sha,
        "github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRegistrationSHA": contract.PATCH,
        "github.com/anyproto/anytype-heart/clientlibrary/service.t2RPCAccountSchemaSHA": manifest["rpc_manifest_sha256"],
        "github.com/anyproto/anytype-heart/clientlibrary/service.t2NativeClientFixtureSHA": peer_manifest["fixture_sha256"],
        "github.com/anyproto/anytype-heart/clientlibrary/service.coherentPeerFixtureSHA": fixture_sha,
        "github.com/anyproto/anytype-heart/clientlibrary/service.coherentPeerSourceSHA": args.expected_app_sha,
    }
    ldflags = "-extldflags=-static " + " ".join("-X " + key + "=" + value for key, value in symbols.items())
    runtime = work / "client-runtime"
    runtime.mkdir(mode=0o755)
    binary = runtime / "native.test"
    run(["go", "test", "-c", "-p", "1", "-tags", processes.TAGS, "-overlay", str(overlay_path),
         "-ldflags", ldflags, "-o", str(binary), "./clientlibrary/service"], "compile-new-peer-fixture", heart, env, 1800)
    binary.chmod(0o755)
    for marker in (qualified["version"], fixture_sha, args.expected_app_sha, contract.METHOD):
        contract.require(binary_tools.contains(binary, marker.encode()), "Native test executable lacks its source marker")
    contract.require({Path(name).name: contract.digest(Path(path)) for name, path in overlays.items()} == hashes,
                     "Fixture source changed during compilation")
    account.verify_fixture_copy(fixture_directory, manifest)
    after = composition.verify_source(heart, qualified["inventory"], qualified["generation"]["module_sha256"])
    contract.require(after == actual and source_snapshot(control) == before, "Native or controller source changed")
    contract.save(evidence / "native-source-after.json", after)
    contract.save(evidence / "build-control-source-after.json", source_snapshot(control))
    receipt.update(status=contract.BUILD, heart_sha=contract.HEART, patch_sha256=contract.PATCH,
        inventory_sha256=contract.INVENTORY, native_source_run=contract.NATIVE_RUN, native_source_count=139,
        runtime_version=qualified["version"], fixture_sha256=fixture_sha, fixture_source_sha256=hashes,
        binary_path="client-runtime/native.test", binary_sha256=contract.digest(binary), native_source_sha256=actual,
        module_sha256=qualified["generation"]["module_sha256"], genproto=genproto,
        old_test_methods_executed=0, protobuf_generation_executed=0)
    contract.validate_build(receipt, args.expected_app_sha, receipt["run_id"], receipt["run_attempt"])


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control", "heart", "work", "evidence", "original-run"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args()
    for name in ("control", "heart", "work", "evidence", "original_run"):
        setattr(args, name, getattr(args, name).resolve())
    args.evidence.mkdir(parents=True, exist_ok=True)
    path = args.evidence / "build.json"
    contract.require(not path.exists(), "Fresh original build receipt required")
    receipt = dict(status="NOT_RUN", app_sha=args.expected_app_sha, run_id=os.environ.get("GITHUB_RUN_ID"),
                   run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), commands=[], **contract.LIMITS)
    contract.require(contract.is_hash(args.expected_app_sha, 40) and (receipt["run_id"] or "").isdigit()
                     and (receipt["run_attempt"] or "").isdigit(), "Exact source/run/attempt required")
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
        entry = dict(name=name, argv=list(map(str, argv)), status="RUNNING")
        receipt["commands"].append(entry)
        contract.save(path, receipt)
        try:
            entry["pid"] = processes.run_process(entry["argv"], cwd, env, args.evidence / (name + ".log"), timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException:
            entry["status"] = "FAIL"
            raise
        finally:
            contract.save(path, receipt)
    try:
        execute(args, receipt, run)
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                       error_type=type(error).__name__, error=str(error))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        contract.save(path, receipt)
        for number, handler in handlers.items():
            signal.signal(number, handler)
    return int(receipt["status"] != contract.BUILD)


if __name__ == "__main__":
    raise SystemExit(main())
