"""Optional UI acceptance after the actual five-phase Apple runtime pair.

Reuse the exact retained r15 application and native XCTest products. Build only
the independent UI runner. A second fresh simulator owns the UI account; the
paired simulator stays shut down and its original ledger stays byte-identical.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import plistlib
import re
import shutil
from uuid import uuid4

import t5_native_ui_evidence as evidence

PASS = "T5_NATIVE_UI_PASS_VISUAL_REVIEW_PENDING"
PAIR_PASS = "APPLE_SAME_ACCOUNT_RUNTIME_PAIR_PASS"
COMBINED_PASS = "APPLE_SAME_ACCOUNT_RUNTIME_PAIR_AND_UI_PASS_VISUAL_REVIEW_PENDING"


def require_ready(pair_result, build, source, flags, runtime):
    evidence.require(pair_result.get("status") == PAIR_PASS and pair_result.get("include_freshness") is True,
                     "Actual four-phase compatibility and optional fifth freshness must pass before UI")
    counts = pair_result.get("actual_counts", {})
    evidence.require(all(type(value) is int for value in counts.values())
                     and counts == {"app_builds": 2, "actual_native_processes": 5, "named_swift_tests_passed": 5,
                               "failed": 0, "skipped": 0, "host_freshness_observations": 11},
                     "Exact actual five-phase prerequisite counts differ")
    reports = pair_result.get("phase_reports", [])
    fresh = pair_result.get("freshness_report", {})
    evidence.require([item.get("phase") for item in reports] == ["old-create", "new-upgrade", "old-edit", "new-recover"]
                     and fresh.get("phase") == "new-freshness", "The actual predecessor sequence is incomplete")
    evidence.require(fresh.get("readbackBoundary") == "BEFORE_FRESHNESS_MUTATIONS"
                     and fresh.get("freshness", {}).get("status") == "PASS_ACTUAL_SWIFT_NATIVE_LOOKUP"
                     and len(fresh["freshness"].get("observations", [])) == 11,
                     "Actual bounded host freshness evidence is missing")
    all_reports = reports + [fresh]
    evidence.require(all(type(item.get("processID")) is int and item["processID"] > 0
                         and re.fullmatch(r"[0-9a-f]{32}", item.get("nonce", "")) is not None for item in all_reports)
                     and len({item.get("processID") for item in all_reports}) == 5
                     and len({item.get("nonce") for item in all_reports}) == 5,
                     "The prerequisite did not use five distinct processes/attempts")
    for key in ["accountID", "spaceID", "rootPathSHA256", "token"]:
        evidence.require(len({item.get(key) for item in all_reports}) == 1 and evidence.nonempty(fresh.get(key)),
                         "The prerequisite account identity is ambiguous")
    evidence.require(pair_result.get("app_source_sha") == source and all(item.get("appSourceSHA") == source for item in all_reports),
                     "The prerequisite source differs")
    evidence.require(build.get("role") == "new" and build.get("app_source_sha") == source
                     and build.get("flags") == flags and build.get("runtime_version") == runtime,
                     "Retained application identity/flags/runtime differs")
    evidence.require(all(evidence.is_hash(build.get(key)) for key in ["code_sha256", "hanlin_snapshot_sha256"])
                     and re.fullmatch(r"[0-9a-f]{40}", build.get("kit_sha", "")) is not None,
                     "Retained application dependency/carrier receipt is missing")
    return fresh


def simulator_record(inventory, udid):
    matches = [(runtime, item) for runtime, values in inventory.get("devices", {}).items()
               for item in values if item.get("udid", "").lower() == udid.lower()]
    evidence.require(len(matches) == 1, "Actual simulator identity is absent or ambiguous")
    return matches[0]


def validate_owned_simulator(before, after, udid, name, selection):
    old = {item.get("udid", "").lower() for values in before.get("devices", {}).values() for item in values}
    evidence.require(re.fullmatch(evidence.UUID, udid) is not None and udid.lower() not in old,
                     "Refuse a pre-existing or invalid UI simulator identity")
    runtime, item = simulator_record(after, udid)
    evidence.require(runtime == selection["runtime"]["identifier"]
                     and item.get("deviceTypeIdentifier") == selection["device"]["identifier"]
                     and item.get("name") == name and item.get("state") == "Shutdown" and item.get("isAvailable") is True,
                     "Created simulator does not match its exact owned type/runtime/name")
    return item


def original_pair_ledger(container, report):
    path = container / "Library/Application Support/pinkha-t5-runtime-pair/ledger.json"
    evidence.require(path.is_file() and not path.is_symlink(), "The original pair ledger is unavailable")
    value = json.loads(path.read_text(encoding="utf8"))
    for key in ["accountID", "spaceID", "token", "appSourceSHA"]:
        evidence.require(value.get(key) == report.get(key), "The original pair ledger identity differs")
    actual = evidence.digest(path)
    evidence.require(actual == report.get("nextLedgerSHA256"), "The original final pair ledger differs")
    return path, actual


def selected_configuration(configuration, blueprint, selections, environment, ui, app_path=None):
    """Keep __TESTROOT__ beside its original Products and replace only test selection."""
    data = plistlib.loads(configuration.read_bytes())
    ui.inject(data, blueprint, environment, app_path)
    targets = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("BlueprintName") == blueprint or value.get("TestBundlePath", "").endswith(blueprint + ".xctest"):
                targets.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(data)
    evidence.require(len(targets) == 1, "One original XCTest target required for explicit selection")
    filters = sorted({name.split("/")[0] for name in selections}) if blueprint == "AnytypeTests" else list(selections)
    evidence.require(filters and len(filters) == len(set(filters)), "Exact nonempty XCTest selection required")
    targets[0]["OnlyTestIdentifiers"] = filters
    targets[0]["SkipTestIdentifiers"] = []
    selected = configuration.with_name("UI27-T5-" + uuid4().hex + ".xctestrun")
    evidence.require(not selected.exists(), "Refuse an existing selected XCTest configuration")
    selected.write_bytes(plistlib.dumps(data))
    return selected, filters


def select_tests(*, pair, ui, method_results, app, configuration, udid, blueprint, selections, environment, directory, app_path=None):
    evidence.require(not directory.exists(), "Refuse stale UI/preparation XCTest evidence")
    directory.mkdir(parents=True)
    selected, filters = selected_configuration(configuration, blueprint, selections, environment, ui, app_path)
    pair.write(directory / "selection.json", {"blueprint": blueprint, "methods": selections, "environment": environment,
               "device_udid": udid, "xctestrun_sha256": evidence.digest(selected),
               "packaged_app": str(app_path) if app_path else None})
    bundle = directory / "original.xcresult"
    command = ["xcodebuild", "test-without-building", "-xctestrun", str(selected),
               "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
               "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "300",
               "-maximum-test-execution-time-allowance", "300",
               *["-only-testing:" + blueprint + "/" + name for name in filters], "-resultBundlePath", str(bundle)]
    outcome = None
    interrupted = False
    try:
        outcome, _ = pair.run_logged(command, app, directory, "test", 900 if app_path else 600, check=False)
    except KeyboardInterrupt:
        interrupted = True
        raise
    finally:
        if bundle.exists() and not interrupted:
            for mode in ["summary", "tests"]:
                pair.run_logged(["xcrun", "xcresulttool", "get", "test-results", mode, "--path", str(bundle), "--format", "json"],
                                app, directory, "export-" + mode, 120, check=False, output=directory / (mode + ".json"))
            if app_path:
                pair.run_logged(["xcrun", "xcresulttool", "export", "attachments", "--path", str(bundle),
                                 "--output-path", str(directory / "attachments")], app, directory, "export-attachments", 180, check=False)
    evidence.require(outcome and outcome.get("return_code") == 0 and not outcome.get("timed_out"),
                     "Actual selected XCTest command failed")
    summary = json.loads((directory / "summary.json").read_text(encoding="utf8"))
    methods = method_results(json.loads((directory / "tests.json").read_text(encoding="utf8")))
    return evidence.validate_selection(summary, methods, selections, udid)


def run_after_pair(*, app, work, proof, pair_result, build, pair_container, selection, pair, ui, method_results):
    source = pair_result["app_source_sha"]
    run_id = pair_result["run_id"]
    fresh = require_ready(pair_result, build, source, pair.FLAGS, pair.runtime_version("new"))
    private = work / "native-ui"
    public = proof / "native-ui"
    evidence.require(not private.exists() and not public.exists(), "Fresh owned UI work/evidence directories required")
    private.mkdir(mode=0o700)
    token = uuid4().hex
    record = {"status": "RUNNING", "phase": "FRESH_SIMULATOR", "app_source_sha": source, "run_id": run_id,
              "token": token, "app_builds_added": 0, "ui_runner_builds": 0, "preparation": None, "ui": None,
              "pair_ledger_unchanged": None, "pair_simulator_remained_shutdown": None,
              "product_lookup_flag": "OFF", "physical_device_accepted": False, "full_matrix_accepted": False,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "limitations": ["Current-Space indexed targets remain incomplete", "Visual review and physical iPad acceptance remain separate",
                              "Every UI lifetime uses unchanged installed executable carriers; per-lifetime vmmap is not asserted"]}
    pair.write(private / "execution.json", record)
    ui_udid = None
    container = None
    original_path = None
    original_hash = None
    generated_project = None
    additional_files = []
    cancellation = None

    def record_failure(error, key):
        nonlocal cancellation
        if isinstance(error, KeyboardInterrupt):
            cancellation = error
        record.update(status="CANCELLED" if cancellation is not None else "FAIL", **{key: type(error).__name__})

    def command(argv, name, timeout=120, check=True, output=None):
        return pair.run_logged(argv, app, private / "commands", name, timeout, check=check, output=output)

    def inventory(name):
        destination = private / "commands" / (name + ".json")
        command(["xcrun", "simctl", "list", "--json"], name, output=destination)
        return json.loads(destination.read_text(encoding="utf8"))

    try:
        evidence.require(shutil.disk_usage(work).free >= 3 * 1024**3, "UI simulator disk reserve below3GiB")
        evidence.require(pair.git(app, "rev-parse", "HEAD") == source
                         and not pair.git(app, "status", "--porcelain", "--untracked-files=no"), "Published tracked App source changed")
        evidence.require(Path(build["app"]).resolve().is_relative_to((work / "new").resolve())
                         and Path(build["configuration"]).resolve().is_relative_to((work / "new").resolve()),
                         "Application products are outside this pair's retained r15 build")
        evidence.require(ui.code_carriers(Path(build["app"]))["sha256"] == build["code_sha256"], "Retained r15 code bytes changed")
        original_path, original_hash = original_pair_ledger(pair_container, fresh)
        record["pair_ledger_sha256_before"] = original_hash
        before = inventory("simulators-before")
        _, paired = simulator_record(before, selection["udid"])
        evidence.require(paired.get("state") == "Shutdown", "The original pair simulator must remain shut down")
        name = "Pinkha-T5UI-" + run_id + "-" + token[:12]
        evidence.require(not any(item.get("name") == name for values in before.get("devices", {}).values() for item in values),
                         "Refuse an existing UI simulator name")
        _, created_log = command(["xcrun", "simctl", "create", name, selection["device"]["identifier"],
                                  selection["runtime"]["identifier"]], "create-ui-simulator")
        created = created_log.read_text(encoding="utf8").strip()
        after = inventory("simulators-after-create")
        owned = validate_owned_simulator(before, after, created, name, selection)
        ui_udid = created
        record.update(device_udid=ui_udid, device_name=name, device_type=owned["deviceTypeIdentifier"],
                      runtime_identifier=selection["runtime"]["identifier"], kit_sha=build["kit_sha"],
                      hanlin_snapshot_sha256=build["hanlin_snapshot_sha256"], app_flags=build["flags"],
                      packaged_code_sha256=build["code_sha256"])
        command(["xcrun", "simctl", "boot", ui_udid], "boot-ui")
        command(["xcrun", "simctl", "bootstatus", ui_udid, "-b"], "boot-ui-status", 180)
        evidence.require(pair.app_container(ui_udid, "data", required=False) is None, "Fresh UI simulator already contains an App account")
        command(["xcrun", "simctl", "install", ui_udid, build["app"]], "install-retained-r15")
        container = pair.app_container(ui_udid, "data")
        evidence.require(container != pair_container and container.resolve() != pair_container.resolve(), "UI installation reused the pair container")
        environment = {"PINKHA_T5_UI_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
                       "PINKHA_T5_UI_TOKEN": token, "PINKHA_T5_UI_APP_SHA": source, "PINKHA_T5_UI_RUN_ID": run_id}
        record["phase"] = "ACTUAL_NATIVE_PREPARATION"
        pair.write(private / "execution.json", record)
        record["preparation"] = select_tests(pair=pair, ui=ui, method_results=method_results, app=app,
            configuration=Path(build["configuration"]), udid=ui_udid, blueprint="AnytypeTests",
            selections=[evidence.PREPARATION], environment=environment, directory=private / "preparation")
        evidence.require(pair.app_container(ui_udid, "data") == container, "Native preparation replaced the fresh UI data container")
        fixture_path = container / "Library/Application Support/pinkha-t5-native-ui-fixture.json"
        evidence.require(fixture_path.is_file() and fixture_path.stat().st_size <= 64 * 1024, "Bounded native UI fixture is missing")
        raw_fixture = fixture_path.read_text(encoding="utf8")
        fixture = json.loads(raw_fixture)
        evidence.validate_fixture(fixture, source=source, run_id=run_id, token=token,
                                  runtime=pair.runtime_version("new"), pair_report=fresh)
        (private / "fixture.json").write_bytes(fixture_path.read_bytes())
        installed = pair.app_container(ui_udid, "app")
        evidence.require(ui.code_carriers(installed)["sha256"] == build["code_sha256"], "Preparation installed different executable bytes")
        record.update(native_fixture_sha256=evidence.digest(private / "fixture.json"),
                      account_root_path_sha256=fixture["accountRootPathSHA256"],
                      container_path_sha256=pair.sha_bytes(str(container).encode()), phase="UI_RUNNER_BUILD")
        pair.write(private / "execution.json", record)
        original_project = app / "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj/project.pbxproj"
        evidence.require("PinkhaT5NativeAcceptanceUITests.swift" in original_project.read_text(), "New T5 UI source is not registered in the original target")
        original_project_hash = evidence.digest(original_project)
        generated_project = ui.ui_only_project(app)
        ui_derived = private / "UI-DerivedData"
        command(["xcodebuild", "build-for-testing", "-project", str(generated_project), "-scheme", "PinkhaPrebuiltUI",
                 "-configuration", "Release-Anytype", "-destination", "platform=iOS Simulator,id=" + ui_udid,
                 "-derivedDataPath", str(ui_derived), "-parallel-testing-enabled", "NO",
                 *["-only-testing:PinkhaStage1AcceptanceUITests/" + method for method in evidence.METHODS.values()],
                 *pair.FLAGS], "build-ui-runner-only", 900)
        evidence.require(evidence.digest(original_project) == original_project_hash, "Original UI project changed during runner preparation")
        evidence.require(ui.code_carriers(Path(build["app"]))["sha256"] == build["code_sha256"], "UI runner build changed the retained App")
        record["ui_runner_builds"] = 1
        products = ui_derived / "Build/Products"
        runner = products / "Release-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app"
        info = plistlib.loads((runner / "Info.plist").read_bytes())
        evidence.require(info.get("CFBundleIdentifier") == "com.gloiiire.PinkhaStage1AcceptanceUITests.xctrunner", "Actual UI runner bundle identity differs")
        command(["xcrun", "simctl", "install", ui_udid, str(runner)], "install-ui-runner")
        configuration = ui.test_configuration(products, "PinkhaStage1AcceptanceUITests")
        environment = {"PINKHA_NATIVE_UI_DISPOSABLE": "1", "PINKHA_T5_NATIVE_UI_FIXTURE_JSON": raw_fixture,
                       "PINKHA_T5_UI_TOKEN": token, "PINKHA_T5_UI_APP_SHA": source, "PINKHA_T5_UI_RUN_ID": run_id,
                       "PINKHA_UI27_APP_LANGUAGE": "en", "PINKHA_UI27_SELECTION_SCOPE": "WAVE15_ACCEPTANCE"}
        record["phase"] = "ACTUAL_UI_EXECUTION"
        pair.write(private / "execution.json", record)
        record["ui"] = select_tests(pair=pair, ui=ui, method_results=method_results, app=app,
            configuration=configuration, udid=ui_udid, blueprint="PinkhaStage1AcceptanceUITests",
            selections=list(evidence.METHODS.values()), environment=environment, directory=private / "ui", app_path=Path(build["app"]))
        observed, additional_files = evidence.read_ui_receipts(private / "ui/attachments", fixture)
        pair.write(private / "actual-ui-observations.json", observed)
        evidence.require(pair.app_container(ui_udid, "data") == container, "UI/relaunch changed the fresh account container")
        carriers = ui.code_carriers(pair.app_container(ui_udid, "app"))
        evidence.require(carriers["sha256"] == build["code_sha256"], "Actual UI installation differs from the packaged r15 App")
        pair.write(private / "post-ui-code-carriers.json", carriers)
        evidence.require(pair.git(app, "rev-parse", "HEAD") == source
                         and not pair.git(app, "status", "--porcelain", "--untracked-files=no"), "Tracked App source changed during actual UI")
        record.update(status=PASS, phase="COMPLETE", actual_observation_counts={"related_targets": 7, "note_lifecycle": 6},
                      actual_ui_lifetimes=3, installed_code_sha256=carriers["sha256"])
    except BaseException as error:
        record_failure(error, "error_type")
    finally:
        try:
            if original_path is not None:
                record["pair_ledger_sha256_after"] = evidence.digest(original_path)
                record["pair_ledger_unchanged"] = record["pair_ledger_sha256_after"] == original_hash
                evidence.require(record["pair_ledger_unchanged"], "The original pair ledger changed during UI work")
            if ui_udid:
                command(["xcrun", "simctl", "shutdown", ui_udid], "shutdown-owned-ui", check=False)
            if cancellation is None:
                final_inventory = inventory("simulators-final")
                _, original = simulator_record(final_inventory, selection["udid"])
                record["pair_simulator_remained_shutdown"] = original.get("state") == "Shutdown"
                evidence.require(record["pair_simulator_remained_shutdown"], "The original pair simulator became active during UI")
        except BaseException as cleanup_error:
            record_failure(cleanup_error, "cleanup_error_type")
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        pair.write(private / "execution.json", record)
        policy = {"status": "WITHHELD_NO_SECRET_INVENTORY", "raw_xcresult_uploaded": False, "account_data_uploaded": False}
        try:
            secret_path = container / "Library/Application Support/pinkha-t5-native-ui-private/secrets.json" if container else None
            if secret_path and secret_path.is_file():
                secrets = json.loads(secret_path.read_text(encoding="utf8"))
                allowed = [private / "execution.json"]
                for name in ["fixture.json", "actual-ui-observations.json", "post-ui-code-carriers.json"]:
                    if (private / name).is_file():
                        allowed.append(private / name)
                for directory in [private / "commands", private / "preparation", private / "ui"]:
                    if directory.is_dir():
                        allowed.extend(path for path in directory.iterdir() if path.is_file()
                                       and (path.name.endswith(".log") or path.name.endswith(".command.json")
                                            or path.name in {"selection.json", "summary.json", "tests.json",
                                                             "simulators-before.json", "simulators-after-create.json", "simulators-final.json"}))
                # A failed UI run may still have useful original attachments.
                # Validate every manifest reference before any publication.
                attachment_directory = private / "ui/attachments"
                manifest_path = attachment_directory / "manifest.json"
                if manifest_path.is_file():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                    evidence.require(isinstance(manifest, list), "Unexpected failed UI attachment manifest")
                    allowed.append(manifest_path)
                    for case in manifest:
                        if case.get("testIdentifier", "").removesuffix("()") in evidence.METHODS.values():
                            allowed.extend(evidence.attachment_path(attachment_directory, item.get("exportedFileName"))
                                           for item in case.get("attachments", []))
                policy = evidence.publish_evidence(private, public / "actual", allowed,
                    secret_record=secrets, token=token, contains_secret=pair.contains_secret)
            evidence.require(policy["status"] == "PASS", "Complete fresh-account secret inventory required")
        except BaseException as publication_error:
            record_failure(publication_error, "publication_error_type")
            policy = {"status": "WITHHELD", "error_type": type(publication_error).__name__,
                      "raw_xcresult_uploaded": False, "account_data_uploaded": False, "secrets_uploaded": False}
        pair.write(public / "evidence-policy.json", policy)
        pair.write(public / "result.json", record)
    if cancellation is not None:
        raise cancellation
    return record


def continue_with_native_ui(*, app, work, proof, result, build, pair_container, selection, pair, ui, method_results):
    """Commit independent pair evidence before optional UI can fail or be cancelled."""
    require_ready(result, build, result["app_source_sha"], pair.FLAGS, pair.runtime_version("new"))
    pair_receipt = json.loads(json.dumps(result))
    pair_receipt.update(finished_at=datetime.now(timezone.utc).isoformat(), native_ui_status="NOT_RUN")
    receipt = proof / "pair-result.json"
    evidence.require(not receipt.exists(), "Refuse to replace independent pair evidence")
    pair.write(receipt, pair_receipt)
    original = evidence.digest(receipt)
    result.update(pair_status=PAIR_PASS, pair_result_sha256=original, phase="ACTUAL_NATIVE_UI", native_ui_status="RUNNING")
    pair.write(proof / "result.json", result)
    try:
        outcome = run_after_pair(app=app, work=work, proof=proof, pair_result=pair_receipt, build=build,
                                 pair_container=pair_container, selection=selection, pair=pair, ui=ui, method_results=method_results)
        result.update(native_ui_status=outcome["status"], native_ui_result="native-ui/result.json",
                      native_ui_observation_counts=outcome.get("actual_observation_counts"))
        evidence.require(outcome["status"] == PASS, "Optional actual native UI acceptance failed; independent pair evidence retained")
        result.update(status=COMBINED_PASS, phase="COMPLETE")
    except BaseException as error:
        result.update(status="FAIL", native_ui_status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL")
        raise
    finally:
        evidence.require(evidence.digest(receipt) == original, "Independent pair receipt changed during optional UI")
