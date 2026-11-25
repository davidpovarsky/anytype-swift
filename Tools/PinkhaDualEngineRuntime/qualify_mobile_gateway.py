"""Qualify the original Any mobile gateway before the larger Apple phase."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import time
import uuid
import build_apple as apple
import native_gateway

STATUS = "PASS_STANDALONE_ORIGINAL_GATEWAY_COMPONENTS_ONLY"
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--controller-sha", required=True)
    parser.add_argument("--resume-disk-stop", action="store_true")
    args = parser.parse_args()
    root = args.root
    apple.require(platform.system() == "Darwin" and platform.machine() == "arm64",
                  "actual_apple_silicon_host_required")
    apple.require(root.resolve() == root and root.is_dir()
                  and root.parent == Path("/Users/m1/builds")
                  and root.name == "pinkha-dual-native-v1-" + apple.MANIFEST_SHA[:12] + "-gateway",
                  "fixed_owned_gateway_root_required")
    apple.require(len(args.controller_sha) == 40
                  and all(c in "0123456789abcdef" for c in args.controller_sha),
                  "controller_commit_required")
    manifest_path = Path(__file__).with_name("source-manifest.json")
    apple.require(apple.digest(manifest_path) == apple.MANIFEST_SHA,
                  "exact_gateway_source_manifest_required")
    manifest = json.loads(manifest_path.read_text())
    prior = None
    if args.resume_disk_stop:
        original_receipt = root / "evidence/receipt.json"
        prior = json.loads(original_receipt.read_text())
        commands = prior["commands"]
        apple.require(prior["status"] == "FAIL"
                      and prior["sourceManifestSHA256"] == apple.MANIFEST_SHA
                      and [x["name"] for x in commands] ==
                          ["go-version", "module-graph", "mobile-gateway-build"]
                      and all(x["exitCode"] == 0 for x in commands[:-1])
                      and commands[-1]["exitCode"] == -signal.SIGTERM
                      and commands[-1]["stopReason"] == "time_or_disk_limit"
                      and commands[-1]["minimumFreeBytes"] < apple.EMERGENCY_FREE_BYTES
                      and commands[-1]["elapsedSeconds"] < commands[-1]["timeoutSeconds"],
                      "only_original_gateway_compilation_disk_stop_may_resume")
        for item in commands:
            apple.require(apple.digest(root / "evidence" / (item["name"] + ".log")) == item["logSHA256"],
                          "original_gateway_failure_evidence_changed")
            try:
                os.killpg(item["pgid"], 0)
            except ProcessLookupError:
                pass
            else:
                apple.require(False, "original_gateway_group_still_exists")
        apple.require(not (root / "mobile-gateway.test").exists()
                      and not (root / "mobile-gateway-receipt.json").exists()
                      and not (root / "qualified-gateway.json").exists()
                      and (root / "tmp").resolve() == root / "tmp"
                      and not any((root / "tmp").iterdir()),
                      "original_gateway_never_executed_and_private_tmp_retired_required")
        apple.check_source(root / "source", manifest)
    evidence = root / ("evidence-resume-1" if prior else "evidence")
    evidence.mkdir(mode=0o700)
    receipt = {"status": "FAIL", "executionKind": "local-mac",
               "executionUUID": str(uuid.uuid4()), "controllerCommit": args.controller_sha,
               "controllerSHA256": apple.digest(__file__),
               "sourceManifestSHA256": apple.MANIFEST_SHA, "sourceArchiveSHA256": apple.ARCHIVE_SHA,
               "sourcePins": manifest["sourcePins"], "tags": manifest["tags"], "commands": [],
               "appleBuilds": 0, "appleTestsExecuted": 0,
               "applicationAcceptanceClaimed": False, "testsExecuted": 0}
    def run(argv, name, cwd=root, environment=None, timeout=900):
        log = evidence / (name + ".log")
        apple.require(not log.exists(), "command_replay_forbidden")
        item = {"name": name, "argv": [str(x) for x in argv], "cwd": str(cwd),
                "started": time.time(), "timeoutSeconds": timeout, "status": "FAIL"}
        receipt["commands"].append(item)
        if name == "mobile-gateway-original-json":
            receipt["testsExecuted"] = None
        with log.open("xb") as stream:
            os.chmod(log, 0o600)
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            item.update(pid=process.pid, pgid=process.pid)
            apple.write(evidence / (name + ".started.json"), item)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                free = shutil.disk_usage("/System/Volumes/Data").free
                item["minimumFreeBytes"] = min(item.get("minimumFreeBytes", free), free)
                if free < apple.EMERGENCY_FREE_BYTES or time.monotonic() > deadline:
                    item["stopReason"] = "time_or_disk_limit"
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=10)
                    break
                time.sleep(1)
            item.update(exitCode=process.returncode, elapsedSeconds=time.time() - item["started"])
        item["logSHA256"] = apple.digest(log)
        item["status"] = "PASS_EXIT_0" if process.returncode == 0 else "FAIL"
        apple.write(evidence / (name + ".command.json"), item)
        apple.require(process.returncode == 0, "actual_command_failed:" + name)
        return log
    try:
        reference = Path("/Users/m1/builds/pinkha-c-native-file-peer-20261125/any548")
        apple.require(reference.is_file() and reference.resolve() == reference
                      and apple.digest(reference) ==
                      "bc73441d05a502e3e77df479f54279540489869b00ca1aecf4e1e9f681fa0f49",
                      "original_native_host_size_reference_changed")
        native_bytes = reference.stat().st_size
        components = {"sourceBytes": sum(x["bytes"] for x in manifest["files"].values()),
                      "testBinaryAllowanceBytes": 2 * native_bytes,
                      "incrementalCacheAllowanceBytes": 2 * native_bytes,
                      "compilerTemporaryAllowanceBytes": 2 * native_bytes,
                      "workspaceEvidenceAllowanceBytes": 16 * 1024**2}
        if prior:
            observed_global_drop = prior["freeBytesBefore"] - prior["commands"][-1]["minimumFreeBytes"]
            apple.require(observed_global_drop > 0, "original_resource_drop_required")
            components = {"reusedSourceBytes": 0,
                          "previousObservedGlobalPeakDropAllowanceBytes": observed_global_drop,
                          "remainingHostLinkOutputAllowanceBytes": native_bytes}
            receipt["originalDiskStopReceiptSHA256"] = apple.digest(root / "evidence/receipt.json")
            receipt["resourceEstimateLimitation"] = (
                "The prior global peak drop includes concurrent host activity; it is not attributed entirely to this job.")
        receipt["phaseSpaceEstimate"] = {
            "phase": "original-mobile-gateway-host-components", "components": components,
            "referencePath": str(reference), "referenceBytes": native_bytes,
            "referenceSHA256": apple.digest(reference),
            "estimatedAdditionalBytes": sum(components.values()),
            "emergencyFreeBytes": apple.EMERGENCY_FREE_BYTES}
        receipt["freeBytesBefore"] = shutil.disk_usage("/System/Volumes/Data").free
        apple.write(evidence / "phase-space-estimate.json", receipt["phaseSpaceEstimate"])
        apple.require(receipt["freeBytesBefore"] > sum(components.values()) + apple.EMERGENCY_FREE_BYTES,
                      "measured_gateway_phase_space_unavailable")
        source = root / "source"
        if prior:
            apple.require(apple.digest(root / "native-source.tar.gz") == apple.ARCHIVE_SHA,
                          "original_gateway_source_archive_changed")
        else:
            apple.extract(root / "native-source.tar.gz", source, manifest)
        workspace = root / "workspace"
        if not prior:
            workspace.mkdir(mode=0o700)
            (root / "tmp").mkdir(mode=0o700)
        native_roots = [source / name for name in
                        ("sync", "heart", "any", "any/.runtime-artifacts/sdk-source")]
        expected_workspace = "go 1.27.4\n\nuse (\n" + "".join("\t" + str(p) + "\n" for p in native_roots) + ")\n"
        if prior:
            apple.require((workspace / "go.work").read_text() == expected_workspace
                          and apple.digest(workspace / "go.work") == prior["effectiveWorkspaceSHA256"],
                          "original_gateway_workspace_changed")
        else:
            (workspace / "go.work").write_text(expected_workspace)
            shutil.copyfile(source / "go.work.sum", workspace / "go.work.sum")
        receipt["effectiveWorkspaceSHA256"] = apple.digest(workspace / "go.work")
        environment = {**os.environ, "GOROOT": str(apple.GO_ROOT), "GOTOOLCHAIN": "local",
                       "CGO_ENABLED": "1", "GOWORK": str(workspace / "go.work"),
                       "GOCACHE": "/Users/m1/caches/anytapy-go1.27.4-build",
                       "GOMODCACHE": "/Users/m1/caches/anytapy-go-mod",
                       "GOPATH": str(root / "go-state"), "TMPDIR": str(root / "tmp"),
                       "GOTMPDIR": str(root / "tmp"), "GOFLAGS": "-mod=readonly -p=2",
                       "GOMAXPROCS": "2", "GOMEMLIMIT": "2GiB",
                       "PATH": str(apple.GO_ROOT / "bin") + ":" + os.environ.get("PATH", "")}
        go = apple.GO_ROOT / "bin/go"
        receipt["goVersion"] = run([go, "version"], "go-version", environment=environment,
                                  timeout=30).read_text().strip()
        apple.require(receipt["goVersion"] == "go version go1.27.4 darwin/arm64",
                      "exact_original_go_toolchain_required")
        graph = run([go, "list", "-m", "-json", "all"], "module-graph", source, environment, 180)
        receipt["actualModuleGraphSHA256"] = apple.digest(graph)
        receipt["mobileGatewayQualification"] = native_gateway.qualify(
            root, source, manifest, apple.MANIFEST_SHA, "simulator", run, environment, go, reuse_fixture=prior is not None)
        apple.check_source(source, manifest)
        receipt.update(status=STATUS, testsExecuted=3, skippedTests=0,
                       sourceFilesVerified=len(manifest["files"]), sourceUnchanged=True,
                       originalGatewayReceiptSHA256=apple.digest(root / "mobile-gateway-receipt.json"))
    except BaseException as failure:
        receipt["failure"] = {"type": type(failure).__name__, "message": str(failure)}
        raise
    finally:
        receipt["freeBytesAfter"] = shutil.disk_usage("/System/Volumes/Data").free
        apple.write(evidence / "receipt.json", receipt)
        if receipt["status"] == STATUS:
            apple.write(root / "qualified-gateway.json", {
                "sourceManifestSHA256": apple.MANIFEST_SHA,
                "originalReceipt": str((evidence / "receipt.json").relative_to(root)),
                "originalReceiptSHA256": apple.digest(evidence / "receipt.json")})
        print(json.dumps({k: receipt.get(k) for k in
                          ("status", "sourceManifestSHA256", "testsExecuted", "failure")}))

if __name__ == "__main__":
    main()
