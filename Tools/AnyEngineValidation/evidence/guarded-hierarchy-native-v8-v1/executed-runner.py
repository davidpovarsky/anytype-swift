#!/usr/bin/env python3
"""Exercise the unchanged twenty hierarchy checks on an explicitly pinned v8 fixture.

Creates a NEW disposable Space; the fixture's original Space is never used.
The native process remains running and all synthetic evidence remains retained.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
import urllib.error
import urllib.request
import uuid

SCOPE = "real_native_v8_guarded_wiki_hierarchy"
CHECKS = {
    "current_guarded_capabilities_and_account",
    "custom_document_and_preserved_property_definitions",
    "guarded_wiki_tree_with_page_and_custom_document",
    "guarded_hierarchy_atomic_initial",
    "guarded_rename_and_live_native_query",
    "retired_hierarchy_generation_rejected",
    "prepared_placement_rejects_actual_native_aba",
    "native_full_version_refuses_stale_direct_write",
    "four_native_conditional_writers_have_one_winner",
    "guarded_reorder_and_exact_retry_preserve_native_version",
    "guarded_hierarchy_cycle_refused",
    "archive_dispatch_aba_refused_without_membership_loss",
    "guarded_bin_preserves_other_memberships_and_property_value",
    "guarded_bin_exact_retry_preserves_native_version",
    "guarded_restore_preserves_memberships_values_and_original_block",
    "stale_engine_run_cannot_archive",
    "unguarded_patch_entry_refuses_fallback",
    "guarded_folder_removal_reparents_before_binning",
    "fresh_guarded_reader_preserves_final_hierarchy",
    "wiki_does_not_implicitly_install_claims",
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise RuntimeError("loopback_redirect_refused")


def http(endpoint: str, method: str, path: str, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(endpoint + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=90) as response:
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise RuntimeError("metadata_response_overflow")
        result = json.loads(raw)
    if not isinstance(result, dict) or result.get("error") or result.get("rejections"):
        raise RuntimeError("native_metadata_request_rejected")
    return result


def native_process_identity(pid: int, port: int, binary: Path):
    if os.name != "nt":
        raise RuntimeError("this_fixture_identity_proof_requires_windows")
    script = (
        "$ErrorActionPreference='Stop'; "
        f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
        f"$listeners=@(Get-NetTCPConnection -State Listen -LocalPort {port}); "
        "@{pid=$p.ProcessId; path=$p.ExecutablePath; "
        "owners=@($listeners | Select-Object -ExpandProperty OwningProcess)} | ConvertTo-Json -Compress"
    )
    raw = subprocess.check_output(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                  timeout=30, encoding="utf-8")
    result = json.loads(raw)
    if result.get("pid") != pid or set(result.get("owners", [])) != {pid}:
        raise RuntimeError("native_listener_identity_changed")
    if Path(result.get("path", "")).resolve() != binary.resolve():
        raise RuntimeError("native_executable_path_mismatch")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--native-binary", type=Path, required=True)
    parser.add_argument("--native-manifest", type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    parser.add_argument("--expected-native-manifest-sha256", required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-disposable-writes", action="store_true")
    args = parser.parse_args()
    if not args.allow_disposable_writes:
        parser.error("--allow-disposable-writes is required")
    native_sha = args.expected_native_sha256
    manifest_sha = args.expected_native_manifest_sha256
    if not re.fullmatch("[0-9a-f]{64}", native_sha) or not re.fullmatch("[0-9a-f]{64}", manifest_sha):
        parser.error("explicit native binary and source-manifest SHA-256 pins are required")
    root = args.repo_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    spec = importlib.util.spec_from_file_location("owned_process_runner", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    result = {"status": "FAIL", "scope": SCOPE, "crossObjectAtomicity": False,
              "retainedDisposableFixture": True}
    before = None
    binary = args.native_binary.resolve()
    manifest = args.native_manifest.resolve()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    endpoint = fixture["endpoint"]
    parsed = urlsplit(endpoint)
    try:
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path:
            raise RuntimeError("owned_loopback_fixture_required")
        if helper.sha256(binary) != native_sha or helper.sha256(manifest) != manifest_sha:
            raise RuntimeError("final_native_v8_pins_mismatch")
        if fixture.get("binarySHA256") != native_sha or fixture.get("nativeSourceManifestSHA256") != manifest_sha:
            raise RuntimeError("fixture_native_pin_mismatch")
        result.update({"binarySHA256": native_sha, "nativeManifestSHA256": manifest_sha,
                       "fixtureSHA256": helper.sha256(args.fixture), "endpoint": endpoint,
                       "accountID": fixture["accountId"], "originalFixtureSpaceUnused": fixture["spaceId"]})
        result["nativeProcessBefore"] = native_process_identity(fixture["pid"], parsed.port, binary)
        before = helper.source_snapshot(root, Path(__file__))
        before["files"][helper_path.relative_to(root).as_posix()] = {
            "sha256": helper.sha256(helper_path), "bytes": helper_path.stat().st_size}
        helper.write_json(output / "source-before.json", before)
        shutil.copyfile(__file__, output / "executed-runner.py")
        shutil.copyfile(helper_path, output / "executed-process-helper.py")
        for name, relative in {
            "executed-swift-probe.swift": "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe/GuardedHierarchyProbe.swift",
            "executed-guarded-store.swift": "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyGuardedHTTPHierarchyRecordStore.swift",
        }.items():
            shutil.copyfile(root / relative, output / name)
        executable = args.executable.resolve()
        result["probeSHA256"] = helper.sha256(executable)
        if args.build_receipt:
            proof = json.loads(args.build_receipt.read_text(encoding="utf-8"))
            if proof.get("status") != "PASS_EXACT_SOURCE_COMPONENT_BUILD" or proof.get("sourceStable") is not True or proof.get("binarySHA256") != result["probeSHA256"]:
                raise RuntimeError("direct_build_receipt_mismatch")
            for relative, expected in proof["sourceInputs"].items():
                if helper.sha256(root / relative) != expected:
                    raise RuntimeError("direct_build_source_changed")
            result["buildReceiptSHA256"] = helper.sha256(args.build_receipt)
            result["buildScope"] = proof["scope"]
            shutil.copyfile(args.build_receipt, output / "component-build-receipt.json")
        health = http(endpoint, "GET", "/v1/health")
        if health.get("account") != fixture["accountId"] or not health.get("startedAt"):
            raise RuntimeError("owned_fixture_account_or_run_mismatch")
        result["engineStartedAt"] = health["startedAt"]
        capabilities = http(endpoint, "GET", "/v1/pinkha/capabilities")
        required = ("conditionalPropertiesSet", "conditionalMembershipSet",
                    "conditionalPropertiesApplySeq", "conditionalPropertiesNoop")
        if capabilities.get("contract") != "pinkha-torah-native-v1" or any(
            type(capabilities.get(name)) is not int or capabilities[name] != 1 for name in required):
            raise RuntimeError("strict_v8_property_contract_missing")
        result["requiredNativeCapabilities"] = {name: capabilities[name] for name in required}
        # Use a new disposable Space; never retry an earlier ambiguous fixture.
        created = http(endpoint, "POST", "/v1/spaces", {"name": "Pinkha guarded hierarchy " + uuid.uuid4().hex})
        space = created.get("id")
        if not isinstance(space, str) or not space or space == fixture["spaceId"]:
            raise RuntimeError("new_disposable_space_identity_missing")
        result["spaceID"] = space
        helper.write_json(output / "allocated-space.json", {
            "endpoint": endpoint, "accountID": fixture["accountId"], "spaceID": space,
            "sharedOriginalSpaceUntouched": fixture["spaceId"]})
        run = output / "run"
        run.mkdir()
        result["process"] = helper.run_process(
            [str(executable), "--guarded-hierarchy", "--disposable", endpoint, fixture["accountId"], space],
            root, run, 360)
        report = None
        try:
            raw_report = (run / "stdout.json").read_bytes()
            if len(raw_report) <= 1024 * 1024:
                candidate = json.loads(raw_report)
                if isinstance(candidate, dict):
                    report = candidate
                    result["report"] = report
        except (ValueError, UnicodeError):
            result["reportParseFailed"] = True
        # A partial report is retained even when the executable fails; it can
        # never satisfy the unchanged twenty-check PASS gate below.
        if result["process"].get("exitCode") != 0 or result["process"].get("timedOut") or result["process"].get("cleanupErrors") or result["process"].get("runnerErrorType"):
            raise RuntimeError("actual_guarded_hierarchy_process_failed")
        if report is None:
            raise RuntimeError("hierarchy_structured_report_missing")
        if report.get("status") != "PASS" or report.get("scope") != SCOPE or report.get("accountID") != fixture["accountId"] or report.get("spaceID") != space:
            raise RuntimeError("hierarchy_report_scope_or_result_mismatch")
        if set(report.get("checks", {})) != CHECKS or not all(value is True for value in report["checks"].values()):
            raise RuntimeError("hierarchy_twenty_checks_not_complete")
        if report.get("crossObjectAtomicity") is not False or report.get("retainedDisposableFixture") is not True:
            raise RuntimeError("hierarchy_report_scope_overstatement")
        after_health = http(endpoint, "GET", "/v1/health")
        if after_health.get("account") != health["account"] or after_health.get("startedAt") != health["startedAt"]:
            raise RuntimeError("native_run_changed")
        result["nativeProcessAfter"] = native_process_identity(fixture["pid"], parsed.port, binary)
        if helper.sha256(executable) != result["probeSHA256"]:
            raise RuntimeError("probe_binary_changed")
        result["status"] = "PASS"
    except Exception as error:
        # Fixed assertion strings and Python type only; never surface a response body.
        result["errorType"] = type(error).__name__
        if type(error) is RuntimeError:
            result["errorCode"] = str(error)
    finally:
        if before is not None:
            try:
                after = helper.source_snapshot(root, Path(__file__))
                after["files"][helper_path.relative_to(root).as_posix()] = {
                    "sha256": helper.sha256(helper_path), "bytes": helper_path.stat().st_size}
                helper.write_json(output / "source-after.json", after)
                result["sourceStable"] = before["files"] == after["files"] and before["dependencies"] == after["dependencies"]
                result["nativeBinaryStable"] = helper.sha256(binary) == native_sha and helper.sha256(manifest) == manifest_sha
                if not result["sourceStable"] or not result["nativeBinaryStable"]:
                    result["status"] = "FAIL"
            except Exception as error:
                result["status"] = "FAIL"
                result["sourceVerificationErrorType"] = type(error).__name__
        helper.write_json(output / "result.json", result)
    print(json.dumps({"status": result["status"], "scope": SCOPE, "evidence": str(output / "result.json"),
                      "checks": len(result.get("report", {}).get("checks", {})), "errorCode": result.get("errorCode")}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
