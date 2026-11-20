#!/usr/bin/env python3
"""Own the Hanlin HTTPS fixture and trust only this CI run's disposable simulator."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import ssl
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "Tools/AnyEngineValidation/HanlinProviderFixture/fixture.py"
ENV_KEYS = {
    "TEST_RUNNER_PINKHA_HANLIN_FIXTURE_URL",
    "TEST_RUNNER_PINKHA_HANLIN_FIXTURE_MODEL",
    "TEST_RUNNER_PINKHA_HANLIN_FIXTURE_KEY",
    "TEST_RUNNER_PINKHA_HANLIN_FIXTURE_CONTROL_URL",
    "TEST_RUNNER_PINKHA_HANLIN_FIXTURE_CONTROL_TOKEN",
}
OWNED_DIR_ENV = "PINKHA_HANLIN_FIXTURE_OWNED_DIR"
CONFIG_ENV = "PINKHA_HANLIN_FIXTURE_PRIVATE_CONFIG"


class BoundaryError(RuntimeError):
    """Only fixed reason identifiers may reach safe evidence."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise BoundaryError(reason)


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(command: list[str], *, timeout: int = 30) -> str:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    require(result.returncode == 0, "owned_command_failed")
    return result.stdout


def github_context() -> tuple[str, str, Path]:
    require(platform.system() == "Darwin", "apple_runner_required")
    require(os.environ.get("GITHUB_ACTIONS") == "true", "github_owned_runner_required")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    source_sha = os.environ.get("GITHUB_SHA", "")
    require(run_id.isdigit(), "missing_run_identity")
    require(len(source_sha) == 40 and all(c in "0123456789abcdef" for c in source_sha),
            "missing_source_identity")
    require(run(["git", "rev-parse", "HEAD"]).strip() == source_sha, "checkout_identity_mismatch")
    temp_root = Path(os.environ.get("RUNNER_TEMP", "")).resolve()
    require(bool(os.environ.get("RUNNER_TEMP")) and temp_root.is_dir(), "missing_runner_temp")
    return run_id, source_sha, temp_root


def safe_directory(value: Path) -> Path:
    result = value.resolve()
    allowed = (ROOT / "build/any-patched-evidence/hanlin-provider").resolve()
    require(result == allowed, "unexpected_evidence_directory")
    result.mkdir(parents=True, exist_ok=True)
    return result


def append_environment(values: dict[str, str]) -> None:
    env_path = os.environ.get("GITHUB_ENV")
    require(bool(env_path), "missing_github_environment_file")
    for key, value in values.items():
        require(isinstance(value, str) and 0 < len(value) <= 4096 and
                "\n" not in value and "\r" not in value and "\0" not in value,
                "invalid_fixture_environment_value")
        require(key in ENV_KEYS or key in {OWNED_DIR_ENV, CONFIG_ENV},
                "unexpected_fixture_environment_key")
    with open(env_path, "a", encoding="utf-8", newline="\n") as output:
        for key, value in sorted(values.items()):
            output.write(key + "=" + value + "\n")


def verify_simulator(receipt_path: Path, run_id: str) -> tuple[str, dict]:
    expected_receipt = ROOT / "build/any-patched-evidence/simulator.json"
    require(receipt_path.resolve() == expected_receipt.resolve(), "unexpected_simulator_receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    udid = receipt.get("ownedUDID", "")
    try:
        normalized = str(uuid.UUID(udid)).upper()
    except (ValueError, TypeError, AttributeError):
        raise BoundaryError("invalid_owned_simulator_identity") from None
    require(udid.upper() == normalized, "invalid_owned_simulator_identity")
    require(os.environ.get("ANY_NATIVE_SIMULATOR_UDID", "").upper() == normalized,
            "owned_simulator_environment_mismatch")
    data = json.loads(run(["xcrun", "simctl", "list", "devices", "available", "--json"]))
    matches = [(runtime, device) for runtime, devices in data.get("devices", {}).items()
               for device in devices if device.get("udid", "").upper() == normalized]
    require(len(matches) == 1, "owned_simulator_not_unique")
    runtime, device = matches[0]
    require(device.get("isAvailable") is True and
            device.get("name") == "AnyNativePort-" + run_id and
            runtime == receipt.get("runtime") and
            device.get("deviceTypeIdentifier") == receipt.get("deviceType"),
            "owned_simulator_receipt_mismatch")
    return normalized, receipt


def read_owned_config(run_id: str, source_sha: str, temp_root: Path) -> tuple[Path, Path, dict]:
    owned_value = os.environ.get(OWNED_DIR_ENV, "")
    config_value = os.environ.get(CONFIG_ENV, "")
    require(bool(owned_value) and bool(config_value), "fixture_ownership_environment_missing")
    owned = Path(owned_value).resolve()
    config = Path(config_value).resolve()
    require(owned.parent == temp_root and owned.name.startswith("pinkha-hanlin-ci-" + run_id + "-"),
            "fixture_owned_directory_mismatch")
    require(config == owned / "fixture/private-config.json", "fixture_config_location_mismatch")
    marker = json.loads((owned / "owner.json").read_text(encoding="utf-8"))
    require(isinstance(marker, dict) and type(marker.get("schemaVersion")) is int and
            marker == {"schemaVersion": 1, "githubRunID": run_id,
                       "sourceCommit": source_sha, "ownedDirectory": str(owned)},
            "fixture_owner_marker_mismatch")
    return owned, config, marker


def validate_private_config(config_path: Path, private_fixture: Path) -> dict[str, str]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    require(type(config.get("schemaVersion")) is int and config["schemaVersion"] == 1,
            "fixture_config_schema_mismatch")
    ca = Path(config.get("rootCAPath", "")).resolve()
    require(ca == private_fixture / "root-ca.pem" and ca.is_file(),
            "fixture_public_root_location_mismatch")
    fixture_id = config.get("runID", "")
    try:
        require(str(uuid.UUID(fixture_id)) == fixture_id, "fixture_run_identity_mismatch")
    except (ValueError, TypeError, AttributeError):
        raise BoundaryError("fixture_run_identity_mismatch") from None
    fingerprint = config.get("rootCAFingerprintSHA256", "")
    require(isinstance(fingerprint, str) and len(fingerprint) == 64 and
            all(c in "0123456789abcdef" for c in fingerprint), "fixture_root_fingerprint_invalid")
    actual_fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
        ca.read_text(encoding="ascii"))).hexdigest()
    require(actual_fingerprint == fingerprint, "fixture_root_fingerprint_mismatch")
    values = config.get("testRunnerEnvironment")
    require(isinstance(values, dict) and set(values) == ENV_KEYS, "fixture_environment_contract_mismatch")
    for key in ENV_KEYS:
        value = values[key]
        require(isinstance(value, str) and 0 < len(value) <= 4096 and
                "\n" not in value and "\r" not in value and "\0" not in value,
                "invalid_fixture_environment_value")
    urls = [urlsplit(values[key]) for key in
            ["TEST_RUNNER_PINKHA_HANLIN_FIXTURE_URL",
             "TEST_RUNNER_PINKHA_HANLIN_FIXTURE_CONTROL_URL"]]
    require(all(url.scheme == "https" and url.hostname == "127.0.0.1" and
                url.username is None and url.password is None and not url.query and
                not url.fragment and url.port is not None and 0 < url.port < 65536
                for url in urls), "fixture_not_owned_https_loopback")
    require(urls[0].netloc == urls[1].netloc and urls[0].path == "/v1" and
            urls[1].path == "/__fixture", "fixture_url_contract_mismatch")
    return values


def prepare(args: argparse.Namespace, result: dict) -> None:
    run_id, source_sha, temp_root = github_context()
    udid, receipt = verify_simulator(args.simulator_receipt, run_id)
    require(FIXTURE.is_file(), "fixture_source_missing")
    result.update(sourceCommit=source_sha, githubRunID=run_id, ownedSimulatorUDID=udid)
    help_text = run(["xcrun", "simctl", "help", "keychain"])
    require("add-root-cert" in help_text, "simulator_root_command_unavailable")
    (args.safe_dir / "simctl-keychain-help.txt").write_text(help_text, encoding="utf-8", newline="\n")

    owned = Path(tempfile.mkdtemp(prefix="pinkha-hanlin-ci-" + run_id + "-", dir=temp_root)).resolve()
    owned.chmod(0o700)
    (owned / "owner.json").write_text(json.dumps({
        "schemaVersion": 1, "githubRunID": run_id, "sourceCommit": source_sha,
        "ownedDirectory": str(owned)}, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (owned / "owner.json").chmod(0o600)
    private_fixture = owned / "fixture"
    private_fixture.mkdir(mode=0o700)
    config_path = private_fixture / "private-config.json"
    # Record cleanup ownership before the child starts; no private values are logged.
    append_environment({OWNED_DIR_ENV: str(owned), CONFIG_ENV: str(config_path)})
    run([sys.executable, str(FIXTURE), "start",
         "--private-dir", str(private_fixture),
         "--safe-result", str(args.safe_dir / "server-start.json")], timeout=90)
    values = validate_private_config(config_path, private_fixture)
    private_config = json.loads(config_path.read_text(encoding="utf-8"))
    ca = private_fixture / "root-ca.pem"
    # This command can affect only the verified, explicitly named simulator.
    run(["xcrun", "simctl", "keychain", udid, "add-root-cert", str(ca)])
    append_environment(values)
    result.update(status="HOST_TLS_READY_SIMULATOR_ROOT_INSTALLED_UI_EXECUTION_PENDING",
                  fixtureSourceSHA256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                  publicRootFingerprintSHA256=private_config.get("rootCAFingerprintSHA256"),
                  fixtureRunID=private_config.get("runID"),
                  hostTLSReadiness=True, defaultURLSessionSimulatorReadiness="REQUIRED_IN_UI_TEST",
                  simulatorRuntime=receipt["runtime"], privateMaterialUploaded=False)


def verify(args: argparse.Namespace, result: dict) -> None:
    run_id, source_sha, temp_root = github_context()
    _, config, _ = read_owned_config(run_id, source_sha, temp_root)
    run([sys.executable, str(FIXTURE), "verify", "--private-config", str(config),
         "--safe-result", str(args.safe_dir / "provider-contract.json")], timeout=30)
    result.update(status="FINITE_PROVIDER_CONTRACT_VERIFIED",
                  sourceCommit=source_sha, githubRunID=run_id,
                  nativeCreationProof="REQUIRED_IN_NAMED_UI_TEST_AND_NATIVE_READBACK")


def cleanup(args: argparse.Namespace, result: dict) -> None:
    run_id, source_sha, temp_root = github_context()
    if not os.environ.get(OWNED_DIR_ENV):
        result.update(status="NO_FIXTURE_DIRECTORY_WAS_CREATED",
                      sourceCommit=source_sha, githubRunID=run_id)
        return
    owned, config, _ = read_owned_config(run_id, source_sha, temp_root)
    # An externally timed-out starter cannot guarantee its own finally block ran.
    # Preserve the root unless the fixture proves its child stopped, including
    # the initializing-config path. Missing ownership evidence is not cleanup.
    require(config.is_file(), "fixture_start_completion_unproven")
    # This orchestration budget covers bounded initialization, authenticated
    # shutdown, handler drain and observed process exit; no app timeout changes.
    run([sys.executable, str(FIXTURE), "stop", "--private-config", str(config)], timeout=60)
    # A missing receipt or failed stop above prevents private-directory removal.
    shutil.rmtree(owned)
    require(not owned.exists(), "fixture_private_directory_removal_failed")
    result.update(status="OWNED_FIXTURE_STOPPED_AND_PRIVATE_MATERIAL_REMOVED",
                  sourceCommit=source_sha, githubRunID=run_id,
                  simulatorTrustRemoval="OWNED_SIMULATOR_DELETION_FOLLOWS",
                  hostTrustModified=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "verify", "cleanup"])
    parser.add_argument("--safe-dir", type=Path, required=True)
    parser.add_argument("--simulator-receipt", type=Path)
    args = parser.parse_args()
    result = {"schemaVersion": 1, "operation": args.operation, "startedAt": utc_now(),
              "status": "FAIL", "scope": "owned_hanlin_provider_ci_setup_not_product_acceptance"}
    try:
        args.safe_dir = safe_directory(args.safe_dir)
        if args.operation == "prepare":
            require(args.simulator_receipt is not None, "simulator_receipt_required")
        {"prepare": prepare, "verify": verify, "cleanup": cleanup}[args.operation](args, result)
        exit_code = 0
    except BoundaryError as error:
        result.update(status="FAIL", reason=str(error))
        exit_code = 1
    except subprocess.TimeoutExpired:
        result.update(status="FAIL", reason="owned_command_timeout")
        exit_code = 1
    except Exception:
        # Exceptions may carry private subprocess/configuration data; never emit them.
        result.update(status="FAIL", reason="unexpected_setup_or_contract_error")
        exit_code = 1
    result["finishedAt"] = utc_now()
    if args.safe_dir.resolve() == (ROOT / "build/any-patched-evidence/hanlin-provider").resolve():
        args.safe_dir.mkdir(parents=True, exist_ok=True)
        (args.safe_dir / (args.operation + ".json")).write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
