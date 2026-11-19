"""Run one fresh r15 account through real production pagination and native mutations."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from uuid import uuid4

import run_t5_apple_pair as pair
import t5_native_pagination_evidence as evidence
import t5_native_account_retry_evidence as retry_evidence

PRIVATE_RELATIVE_PATH = "Library/Application Support/pinkha-t5-native-pagination"
ALLOWED_PHASE_FILES = ["test.log", "test.command.json", "summary.json", "tests.json", "receipt.json", "result.json",
                       "selection.json", "install.log", "install.command.json", "export-summary.command.json",
                       "export-tests.command.json", "account-retry-receipt.json", "account-retry-controller.json"]


def selected_method(account_retry):
    pair.require(type(account_retry) is bool, "Explicit native account-retry mode required")
    return retry_evidence.METHOD if account_retry else evidence.METHOD


def existing_directory_identity(path):
    pair.require(path.is_absolute() and path.is_dir() and not path.is_symlink()
                 and path.resolve(strict=True) == path, "Canonical existing native directory required")
    value = path.stat()
    pair.require(hasattr(value, "st_birthtime"), "Actual Apple directory creation date required")
    result = dict(pathSHA256=pair.sha_bytes(str(path).encode()), device=value.st_dev,
                  inode=value.st_ino, createdAt=value.st_birthtime)
    retry_evidence.validate_directory(result)
    return result


def private_file(container, filename):
    path = container / PRIVATE_RELATIVE_PATH / filename
    pair.require(path.is_file() and not path.is_symlink() and path.resolve(strict=True).is_relative_to(container.resolve(strict=True))
                 and path.stat().st_size <= 2 * 1024 * 1024, "Bounded owned native pagination file required")
    return path


def publish_native_evidence(work, proof, container, token):
    policy = dict(status="WITHHELD_NO_SECRET_INVENTORY", raw_xcresult_uploaded=False,
                  account_data_uploaded=False, secrets_uploaded=False)
    if container is None or not (container / PRIVATE_RELATIVE_PATH / "secrets.json").is_file():
        pair.write(proof / "native-evidence-policy.json", policy)
        return False
    secret_path = private_file(container, "secrets.json")
    raw = secret_path.read_bytes()
    secrets = json.loads(raw)
    pair.require(secrets.get("token") == token and all(isinstance(secrets.get(key), str) and secrets[key]
                 for key in ["mnemonic", "accountKey"]), "Exact complete disposable credential inventory required")
    inventory = work / "credential-inventory.json"
    pair.require(not inventory.exists(), "Refuse an existing pagination credential inventory")
    with inventory.open("xb") as stream:
        stream.write(raw)
    inventory.chmod(0o600)
    needles = [secrets[key].encode(encoding) for key in ["mnemonic", "accountKey"]
               for encoding in ["utf8", "utf-16-le", "utf-16-be"]]
    destination = proof / "actual-native"
    pair.require(not destination.exists(), "Refuse stale public pagination evidence")
    candidates = []
    for name in ALLOWED_PHASE_FILES:
        path = work / "phase" / name
        if path.is_file():
            pair.require(not path.is_symlink() and path.resolve().is_relative_to(work.resolve()), "Native evidence escaped owned work")
            pair.require(not pair.contains_secret(path, needles), "Disposable credential found; all native pagination evidence withheld")
            candidates.append(path)
    pair.require(candidates, "No native execution evidence to publish")
    destination.mkdir()
    published = []
    for path in candidates:
        target = destination / path.name
        shutil.copyfile(path, target)
        published.append(dict(path=str(target.relative_to(proof)), sha256=pair.digest(target), bytes=target.stat().st_size))
    policy.update(status="PASS", files=published, scanned_complete_credential_encodings=3)
    pair.write(proof / "native-evidence-policy.json", policy)
    return True


def execute_phase(*, app, work, build, udid, source, run_id, token, ui, method_results, account_retry=False):
    from run_t5_native_ui import selected_configuration
    from t5_native_ui_evidence import validate_selection

    directory = work / "phase"
    pair.require(not directory.exists(), "Fresh native pagination phase directory required")
    directory.mkdir()
    method = selected_method(account_retry)
    selected_class = method.split("/", 1)[0]
    record = dict(status="RUNNING", method=method, actual_test_counts=None)
    pair.write(directory / "result.json", record)
    bundle = directory / "original.xcresult"
    try:
        pair.run_logged(["xcrun", "simctl", "install", udid, build["app"]], app, directory, "install", 120)
        environment = {"PINKHA_T5_NATIVE_PAGINATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
                       "PINKHA_T5_PAGINATION_TOKEN": token, "PINKHA_T5_PAGINATION_APP_SHA": source,
                       "PINKHA_T5_PAGINATION_RUN_ID": run_id}
        if account_retry:
            environment["PINKHA_T5_ACCOUNT_RETRY"] = "1"
            run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
            pair.require(run_attempt.isdigit() and int(run_attempt) > 0, "Actual account-retry run attempt required")
            environment["PINKHA_T5_ACCOUNT_RETRY_RUN_ATTEMPT"] = run_attempt
        configuration, filters = selected_configuration(Path(build["configuration"]), "AnytypeTests", [method], environment, ui)
        pair.require(filters == [selected_class], "Exact native pagination/retry XCTest class required")
        pair.write(directory / "selection.json", dict(method=method, environment=environment, device_udid=udid,
                   xctestrun_sha256=pair.digest(configuration), packaged_code_sha256=build["code_sha256"]))
        command = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
                   "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
                   "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "900",
                   "-maximum-test-execution-time-allowance", "900",
                   "-only-testing:AnytypeTests/" + selected_class, "-resultBundlePath", str(bundle)]
        outcome, _ = pair.run_logged(command, app, directory, "test", 1200, check=False)
        record.update(command_exit_code=outcome["return_code"], timed_out=outcome.get("timed_out", False))
        if bundle.exists():
            for mode in ["summary", "tests"]:
                pair.run_logged(["xcrun", "xcresulttool", "get", "test-results", mode, "--path", str(bundle), "--format", "json"],
                                app, directory, "export-" + mode, 120, check=False, output=directory / (mode + ".json"))
        container = pair.app_container(udid, "data")
        receipt_path = container / PRIVATE_RELATIVE_PATH / "receipt.json"
        if receipt_path.is_file():
            shutil.copyfile(private_file(container, "receipt.json"), directory / "receipt.json")
        if account_retry and (container / PRIVATE_RELATIVE_PATH / "account-retry-receipt.json").is_file():
            shutil.copyfile(private_file(container, "account-retry-receipt.json"), directory / "account-retry-receipt.json")
        installed = pair.app_container(udid, "app")
        pair.require(ui.code_carriers(installed)["sha256"] == build["code_sha256"], "Installed pagination executable bytes differ")
        pair.require(outcome["return_code"] == 0 and not outcome.get("timed_out"), "Actual native pagination XCTest failed")
        summary = json.loads((directory / "summary.json").read_text(encoding="utf8"))
        methods = method_results(json.loads((directory / "tests.json").read_text(encoding="utf8")))
        record["actual_test_counts"] = validate_selection(summary, methods, [method], udid)
        report = json.loads((directory / "receipt.json").read_text(encoding="utf8"))
        root = container / pair.ROOT_RELATIVE_PATH
        pair.require(root.is_dir() and not root.is_symlink() and root.resolve().is_relative_to(container.resolve()), "Actual owned native account root missing")
        counts = evidence.validate_receipt(report, source=source, run_id=run_id, token=token, root_sha=pair.sha_bytes(str(root.resolve()).encode()))
        if account_retry:
            account_id = report["accountID"]
            pair.require(account_id not in {".", ".."} and "/" not in account_id and "\\" not in account_id,
                         "Original account directory name is invalid")
            canonical_root = root.resolve(strict=True)
            observed = dict(root=existing_directory_identity(canonical_root),
                            account=existing_directory_identity(canonical_root / account_id))
            credential_sha = pair.digest(private_file(container, "secrets.json"))
            window = [summary.get("startTime"), summary.get("finishTime")]
            controller = dict(current_directories=observed, credential_sha256=credential_sha, run_attempt=run_attempt,
                              actual_xctest_execution_window=window, baseline_receipt_sha256=pair.digest(directory / "receipt.json"))
            pair.write(directory / "account-retry-controller.json", controller)
            retry_report = json.loads((directory / "account-retry-receipt.json").read_text(encoding="utf8"))
            counts = retry_evidence.validate_receipt(retry_report, report, (directory / "receipt.json").read_bytes(),
                source=source, run_id=run_id, run_attempt=run_attempt, token=token, root_sha=observed["root"]["pathSHA256"],
                credential_sha=credential_sha, current_directories=observed, execution_window=window)
            record["account_retry_receipt_sha256"] = pair.digest(directory / "account-retry-receipt.json")
        record.update(status="PASS", native_process_id=report["processID"], receipt_sha256=pair.digest(directory / "receipt.json"),
                      installed_code_sha256=build["code_sha256"], actual_counts=counts, actual_methods=methods)
        return counts
    finally:
        if record["status"] != "PASS":
            record["status"] = "FAIL"
        pair.write(directory / "result.json", record)


def execute(args, result):
    pair.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple silicon Mac required")
    pair.require(sys.version_info >= (3, 12), "Python3.12 required for safe native archive extraction")
    app, native_source, work, proof, derived = [value.resolve() for value in [args.app, args.native_source, args.work, args.evidence, args.derived]]
    pair.require(len({app, native_source, work, proof, derived}) == 5 and not work.exists(), "Separate fresh owned private work required")
    work.mkdir(parents=True, mode=0o700)
    source = pair.verify_published_source(app, proof)
    pair.require(pair.git(native_source, "rev-parse", "HEAD") == pair.NATIVE_SOURCE and not pair.git(native_source, "status", "--porcelain"),
                 "Exact clean immutable native inventory checkout required")
    preflight = json.loads((proof / "preflight/preflight.json").read_text(encoding="utf8"))
    pair.require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN" and preflight.get("source_sha") == source,
                 "Actual source-bound Xcode27 preflight required")
    run_id = os.environ["GITHUB_RUN_ID"]
    selection = preflight["selected"]["ipad"]
    udid = selection["udid"]
    pair.require(selection["name"] == "Pinkha-UI27-" + run_id + "-ipad", "Fresh job-owned simulator identity differs")
    pair.require(shutil.disk_usage(work).free >= 8 * 1024**3, "Native build disk reserve below8GiB")
    helper_path = app / "Tools/PinkhaNativeDerived"
    pair.require(pair.digest(helper_path / "build_custom_heart.py", True) == pair.BUILDER_SHA, "Reviewed runtime helper source changed")
    sys.path.insert(0, str(helper_path))
    sys.path.insert(0, str(app / "Tools/PinkhaSimulatorGate"))
    import build_custom_heart as heart_helper
    import build_native_ipa as native_helper
    import run_ui27 as ui
    from validate_release import method_results

    result.update(app_source_sha=source, run_id=run_id, device_udid=udid, app_flags=pair.FLAGS,
                  expected_runtime_version=pair.runtime_version("new"), phase="NATIVE_RUNTIME_AND_BUILD")
    pair.write(proof / "result.json", result)
    token = uuid4().hex
    published = False
    try:
        pair.run_logged(["xcrun", "simctl", "boot", udid], app, proof / "simulator", "boot", 120)
        pair.run_logged(["xcrun", "simctl", "bootstatus", udid, "-b"], app, proof / "simulator", "boot-status", 180)
        pair.require(pair.app_container(udid, "data", required=False) is None, "Fresh pagination simulator already contains an account")
        runtime_proof = proof / "runtime-new"
        archive, source_run = pair.download_runtime("new", args.heart_r15_run_id, work, runtime_proof, os.environ["GITHUB_REPOSITORY"])
        installed = pair.install_runtime("new", archive, source_run, app, native_source, work, runtime_proof, heart_helper)
        build = pair.build_app("new", app, derived, work, proof / "build-new", udid, source, (ui, native_helper))
        shutil.move(str(installed), work / "installed-framework-new")
        account_retry = getattr(args, "include_account_retry", False)
        result.update(phase="ACTUAL_NATIVE_ACCOUNT_RETRY" if account_retry else "ACTUAL_NATIVE_PAGINATION",
                      kit_sha=build["kit_sha"], packaged_code_sha256=build["code_sha256"])
        pair.write(proof / "result.json", result)
        result["actual_counts"] = execute_phase(app=app, work=work, build=build, udid=udid, source=source,
                                                run_id=run_id, token=token, ui=ui, method_results=method_results,
                                                account_retry=account_retry)
        pair.require(pair.git(app, "rev-parse", "HEAD") == source and not pair.git(app, "status", "--porcelain"),
                     "Published application source changed during native execution")
    finally:
        try:
            published = publish_native_evidence(work, proof, pair.app_container(udid, "data", required=False), token)
        finally:
            pair.run_logged(["xcrun", "simctl", "shutdown", udid], app, proof / "simulator", "shutdown", 120, check=False)
    pair.require(published, "Complete secret-scanned native pagination evidence required")
    result.update(status="APPLE_NATIVE_ACCOUNT_RETRY_PASS" if account_retry else "APPLE_NATIVE_PAGINATION_PASS",
                  phase="COMPLETE", product_lookup_flag="OFF",
                  full_matrix_accepted=False, whole_index_completeness="NOT_PROVEN", acl_revocation="NOT_PROVEN",
                  physical_device_accepted=False, ui_navigation="NOT_RUN")


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    for name in ["app", "native-source", "work", "evidence", "derived"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--heart-r15-run-id", required=True)
    parser.add_argument("--include-account-retry", action="store_true")
    args = parser.parse_args(argv)
    result = dict(protocol=retry_evidence.PROTOCOL if args.include_account_retry else evidence.PROTOCOL,
                  status="RUNNING", phase="PREFLIGHT", started_at=datetime.now(timezone.utc).isoformat(),
                  product_lookup_flag="OFF", full_matrix_accepted=False, whole_index_completeness="NOT_PROVEN",
                  acl_revocation="NOT_PROVEN", physical_device_accepted=False, ui_navigation="NOT_RUN")
    code = 1
    try:
        execute(args, result)
        code = 0
    except (Exception, KeyboardInterrupt) as error:
        result.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                      error=type(error).__name__, message=str(error))
    finally:
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        pair.write(args.evidence / "result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
