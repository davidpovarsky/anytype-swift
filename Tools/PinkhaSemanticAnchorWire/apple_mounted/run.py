#!/usr/bin/env python3
"""Execute only the separately owned mounted preparation and UI journey, without rebuilding."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
from uuid import uuid4
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import mounted_contract as proof

consumer_path = HERE.parent / "apple_consumer/run.py"
spec = importlib.util.spec_from_file_location("page154_original_consumer_helpers", consumer_path)
consumer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = consumer
spec.loader.exec_module(consumer)


def copy_original_fixture(runner, udid, evidence, name):
    path, _ = runner.run(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "data"],
                         "container-" + name.removesuffix(".json"), 30)
    container = Path(path.read_text().strip())
    proof.require(container.is_absolute() and container.is_dir() and not container.is_symlink(),
                  "Owned App data container missing")
    original = container / "Library/Application Support" / name
    proof.require(original.resolve().is_relative_to(container.resolve()) and original.is_file()
                  and not original.is_symlink() and original.stat().st_size <= 65_536,
                  "Expected bounded original synthetic fixture/receipt missing")
    destination = evidence / name
    proof.require(not destination.exists(), "Original fixture/receipt cannot be overwritten")
    shutil.copyfile(original, destination)
    proof.require(proof.digest(original) == proof.digest(destination), "Copied original fixture changed")
    return destination


def download_originals(runner, args, approved):
    prefix = "repos/" + proof.native.REPOSITORY + "/actions/"
    run = runner.json(["gh", "api", prefix + "runs/" + approved["consumer_run"] + "/attempts/" +
                      approved["consumer_attempt"]], "consumer-run-api")
    artifact = runner.json(["gh", "api", prefix + "artifacts/" + str(approved["artifact_id"])], "consumer-artifact-api")
    proof.original_api(run, artifact, approved)
    archive = args.work / "original-consumer.zip"
    runner.run(["gh", "api", prefix + "artifacts/" + str(approved["artifact_id"]) + "/zip"],
               "download-original-consumer", 600, destination=archive)
    proof.require(archive.stat().st_size == approved["artifact_bytes"]
                  and proof.digest(archive) == approved["artifact_sha256"], "Original consumer ZIP bytes differ")
    selected = ["execution.json", "source-before.json", "source-after.json", "xcode-version.log", "original.xctestrun",
        "semantic-page154-early-products/manifest.json", "semantic-page154-early-products/BuildProducts.tar.gz",
        "ui-runner/original.xctestrun", "ui-runner/semantic-page154-early-products/manifest.json",
        "ui-runner/semantic-page154-early-products/BuildProducts.tar.gz"]
    destination = args.work / "consumer-originals"
    destination.mkdir()
    with zipfile.ZipFile(archive) as packed:
        names = packed.namelist()
        proof.require(len(names) == len(set(names)) and len(names) < 100_000, "Duplicate/unbounded original ZIP members")
        for name in names:
            proof.native.relative(name.rstrip("/"))
        for name in selected:
            info = packed.getinfo(name)
            maximum = proof.MAX_ARCHIVE if name.endswith(".tar.gz") else 64 * 1024**2
            proof.require(not info.is_dir() and 0 < info.file_size <= maximum, "Unbounded original artifact member")
            path = destination / proof.native.relative(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with packed.open(info) as incoming, path.open("xb") as output:
                shutil.copyfileobj(incoming, output, 1024 * 1024)
    proof.require(proof.digest(destination / "semantic-page154-early-products/manifest.json") ==
                    approved["native_manifest_sha256"]
                  and proof.digest(destination / "ui-runner/semantic-page154-early-products/manifest.json") ==
                    approved["ui_manifest_sha256"], "Reviewed original Products manifest bytes differ")
    return destination, {name: proof.digest(destination / name) for name in selected}


def product_inputs(inputs):
    # Only our subsequent controllers, workflow wiring and documentation may
    # differ. Every reused App/Module/UI/project/dependency input remains exact.
    return {path: value for path, value in inputs.items()
            if not path.startswith(("Tools/", ".github/", "docs/"))}


def enumerate_and_run(runner, descriptor, udid, selector, expected_plan, evidence, receipt):
    evidence.mkdir()
    scoped = consumer.Commands(ROOT, evidence, receipt)
    listing = evidence / "enumeration.json"
    scoped.run(proof.xctest_command(descriptor, udid, selector, enumeration=listing),
               "enumerate-exact-owned-one", 600)
    plan, enabled, disabled = consumer.component.enumerated_identifiers(proof.read(listing))
    enumeration = proof.exact_enumeration(plan, enabled, disabled, selector, expected_plan)
    result = evidence / "actual.xcresult"
    failure = None
    try:
        scoped.run(proof.xctest_command(descriptor, udid, selector, result=result),
                   "actual-owned-one", 900)
    except BaseException as error:
        failure = error
    if result.exists():
        try: consumer.exported_xctest(scoped, result, evidence)
        except BaseException as error:
            receipt.setdefault("export_errors", []).append({"selector": selector, "error_type": type(error).__name__})
            if failure is None: failure = error
    if failure: raise failure
    verified = proof.exact_execution(proof.read(evidence / "actual-summary.json"),
        proof.read(evidence / "actual-tests.json"), udid, selector)
    verified["enumeration"] = dict(enumeration, sha256=proof.digest(listing))
    return verified


def ui_attachments(directory, udid, capture, reopen):
    manifest = proof.read(directory / "manifest.json")
    proof.require(isinstance(manifest, list), "Actual UI attachment manifest missing")
    expected = {"semantic-anchor-mounted-capture-receipt": capture,
                "semantic-anchor-mounted-cold-reopen-receipt": reopen}
    found = {}
    for row in manifest:
        for item in row.get("attachments", []):
            name = str(item.get("suggestedHumanReadableName", ""))
            matches = [key for key in expected if name.startswith(key + "_")]
            if not matches: continue
            key = matches[0]
            test = str(row.get("testIdentifier", "")).removeprefix("PinkhaStage1AcceptanceUITests/").removesuffix("()")
            proof.require(test == "/".join(proof.UI.split("/")[1:]) and key not in found
                and str(item.get("deviceId", "")).lower() == udid.lower()
                and item.get("isAssociatedWithFailure") is False, "Wrong/duplicate actual UI observation attachment")
            path = directory / proof.native.relative(item.get("exportedFileName"))
            proof.require(path.parent == directory, "Unexpected UI attachment hierarchy")
            value = proof.read(path, 65_536)
            # XCTest re-encodes its strongly typed subset; preserve original on-disk
            # bytes separately and require every exported field to agree with it.
            proof.require(isinstance(value, dict) and value and all(expected[key].get(k) == v for k, v in value.items()),
                          "Actual UI attachment disagrees with original App receipt")
            found[key] = {"path": str(path), "sha256": proof.digest(path), "test": test}
    proof.require(set(found) == set(expected), "Both actual UI receipt attachments required")
    return found


def execute(args, receipt):
    proof.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual ARM64 Mac required")
    proof.require(ROOT == args.app and not args.work.exists() and not args.evidence.exists(),
                  "Fresh separate App/work/evidence roots required")
    approved = proof.admission(proof.read(args.admission))
    proof.require(args.admission.is_relative_to(ROOT), "Reviewed admission must be tracked with the controller")
    head = consumer.producer.git(ROOT, "rev-parse", "HEAD")
    proof.require(head == os.environ.get("GITHUB_SHA"), "Controller checkout must match dispatched source")
    inputs = consumer.checkout_inputs(ROOT, head)
    proof.require(args.admission.relative_to(ROOT).as_posix() in inputs, "Admission file must be committed")
    plan = proof.read(HERE / "source-plan.json")
    proof.require(all(inputs.get(path) == row["sha256"] for path, row in plan["files"].items()),
                  "Frozen mounted App/UI source plan differs")
    binding = proof.native.binding(dict(sourceSHA=approved["consumer_sha"],
        runID=os.environ.get("GITHUB_RUN_ID"), runAttempt=os.environ.get("GITHUB_RUN_ATTEMPT"), nonce=uuid4().hex))
    args.work.mkdir(parents=True); args.evidence.mkdir(parents=True)
    receipt.update(controller_source_sha=head, compiled_app_source_sha=approved["consumer_sha"],
                   binding=binding, admission=approved)
    proof.save(args.evidence / "controller-source-before.json", inputs)
    runner = consumer.Commands(ROOT, args.evidence, receipt)
    owned_udid = None; primary = None; finalizing = False; cancelled = False
    original_descriptors = []; copied_descriptors = []; restores = []
    previous = {}
    def cancel(signum, frame):
        nonlocal cancelled
        cancelled = True
        if not finalizing: raise KeyboardInterrupt("Owned mounted acceptance cancelled")
    for number in (signal.SIGINT, signal.SIGTERM):
        previous[number] = signal.getsignal(number); signal.signal(number, cancel)
    try:
        receipt["phase"] = "EXACT_ORIGINAL_PRODUCTS"
        originals, hashes = download_originals(runner, args, approved)
        receipt["original_artifacts"] = hashes
        original = proof.read(originals / "execution.json")
        proof.require(original.get("status") == proof.native.PASS
            and original.get("actual_product_methods_passed") == 1
            and original.get("binding", {}).get("sourceSHA") == approved["consumer_sha"]
            and original.get("binding", {}).get("runID") == approved["consumer_run"]
            and original.get("binding", {}).get("runAttempt") == approved["consumer_attempt"]
            and original.get("producer", {}).get("archive_sha256") == proof.native.ARCHIVE_SHA
            and original.get("source_and_framework_unchanged") is True,
            "Original actual App boundary/producer proof must be qualified")
        ui_build = original.get("ui_runner_build", {})
        proof.require(original.get("native_boundary_status") == proof.native.PASS
            and ui_build.get("status") == "BUILD_ONLY_ORIGINAL_PRODUCTS_PRESERVED"
            and ui_build.get("configuration") == "Debug-Anytype" and ui_build.get("scheme") == "PinkhaPrebuiltUI"
            and ui_build.get("blueprint") == "PinkhaStage1AcceptanceUITests"
            and ui_build.get("selector") == proof.UI and ui_build.get("preparation_selector") == proof.PREP
            and ui_build.get("mounted_source_origin_sha") == "9d7dbdd68da2e3d48ec84664c50954b9c9ec6762"
            and ui_build.get("source_plan_sha256") == proof.digest(HERE / "source-plan.json")
            and ui_build.get("preparation_executions") == ui_build.get("ui_executions") == 0
            and ui_build.get("acceptance") == "NOT_RUN",
            "Exact compiled-only mounted source/target provenance required")
        original_ui = ui_build.get("original_xctestrun", {})
        proof.require(original_ui.get("path") == "ui-runner/original.xctestrun"
            and original_ui.get("sha256") == proof.digest(originals / "ui-runner/original.xctestrun"),
            "Actual original UI descriptor provenance differs")
        for metadata, name in ((original["early_products"], "semantic-page154-early-products"),
                                (ui_build["early_products"], "ui-runner/semantic-page154-early-products")):
            proof.require(metadata.get("archive_path") == name + "/BuildProducts.tar.gz"
                and metadata.get("manifest_path") == name + "/manifest.json"
                and metadata.get("archive_sha256") == proof.digest(originals / name / "BuildProducts.tar.gz")
                and metadata.get("manifest_sha256") == proof.digest(originals / name / "manifest.json"),
                "Original successful build archive provenance differs")
        before = proof.read(originals / "source-before.json")
        proof.require(before == proof.read(originals / "source-after.json")
            and product_inputs(before) == product_inputs(inputs), "Reused App/Module/UI/project source differs")
        current_version, _ = runner.run(["xcodebuild", "-version"], "actual-xcode-version")
        proof.require(current_version.read_bytes() == (originals / "xcode-version.log").read_bytes()
            and current_version.read_text().startswith("Xcode 27."), "Original Xcode27 toolchain must match exactly")
        native_root = args.work / "native-products"; ui_root = args.work / "ui-products"
        receipt["restored_native"] = proof.restore_products(
            originals / "semantic-page154-early-products/BuildProducts.tar.gz",
            originals / "semantic-page154-early-products/manifest.json", native_root, approved)
        receipt["restored_ui"] = proof.restore_products(
            originals / "ui-runner/semantic-page154-early-products/BuildProducts.tar.gz",
            originals / "ui-runner/semantic-page154-early-products/manifest.json", ui_root, approved)
        restores = [(native_root, originals / "semantic-page154-early-products/manifest.json"),
                    (ui_root, originals / "ui-runner/semantic-page154-early-products/manifest.json")]
        native_products = native_root / "Build/Products"; ui_products = ui_root / "Build/Products"
        app = native_products / "Debug-Anytype-iphonesimulator/Anytype.app"
        proof.require(app.is_dir() and not app.is_symlink(), "Original candidate App missing")
        verification = ("import sys;from pathlib import Path;sys.path.insert(0," +
            repr(str(ROOT / "Tools/PinkhaSimulatorGate")) + ");import run_ui27 as s;"
            "s.verify_signed_simulator(Path(" + repr(str(app)) + "),Path(" + repr(str(args.evidence)) + "));"
            "s.verify_runtime_copies(Path(" + repr(str(app)) + ")," + repr(proof.native.VERSION.encode()) +
            ",Path(" + repr(str(args.evidence)) + "))")
        runner.run([sys.executable, "-B", "-c", verification], "verify-restored-signatures-and-runtime", 120)
        native_original = proof.exact_original_descriptor(native_products, (originals / "original.xctestrun").read_bytes())
        ui_original = proof.exact_original_descriptor(ui_products, (originals / "ui-runner/original.xctestrun").read_bytes())
        original_descriptors = [(path, proof.digest(path)) for path in (native_original, ui_original)]
        runtimes = runner.json(["xcrun", "simctl", "list", "runtimes", "-j"], "available-runtimes")
        types = runner.json(["xcrun", "simctl", "list", "devicetypes", "-j"], "available-device-types")
        pair = consumer.simulator_selection.choose_pair(runtimes, types, product_family="iPad", major=27, architecture="arm64")
        path, _ = runner.run(["xcrun", "simctl", "create", "Page154Mounted-" + binding["nonce"],
            pair["device"]["identifier"], pair["runtime"]["identifier"]], "create-owned-simulator")
        owned_udid = path.read_text().strip()
        proof.require(consumer.owned.valid_udid(owned_udid), "Invalid owned simulator ID")
        receipt["owned_simulator"] = {"udid": owned_udid, "selection": pair["selection"], "nonce": binding["nonce"]}
        runner.run(["xcrun", "simctl", "boot", owned_udid], "boot-owned-simulator", 90)
        runner.run(["xcrun", "simctl", "bootstatus", owned_udid, "-b"], "wait-owned-simulator", 180)
        prep = native_original.with_name("MountedPrep-" + binding["nonce"] + ".xctestrun")
        prep_proof = proof.copied_descriptor(native_original, prep, proof.PREP, binding,
            runtime=pair["runtime"], approved=approved["native_descriptor"])
        copied_descriptors.append((prep, prep_proof["copied_sha256"]))
        proof.save(args.evidence / "preparation-descriptor.json", prep_proof)
        shutil.copyfile(prep, args.evidence / "preparation-bound.xctestrun")
        receipt["phase"] = "ACTUAL_NEW_PREPARATION"
        receipt["preparation_commands_started"] = 1
        receipt["preparation_execution"] = enumerate_and_run(runner, prep, owned_udid, proof.PREP,
            prep_proof["enumeration_plan"], args.evidence / "preparation", receipt)
        fixture_path = copy_original_fixture(runner, owned_udid, args.evidence, "pinkha-semantic-page154-mounted-fixture.json")
        fixture = proof.read(fixture_path, 65_536); proof.fixture(fixture, binding)
        ui = ui_original.with_name("MountedUI-" + binding["nonce"] + ".xctestrun")
        ui_proof = proof.copied_descriptor(ui_original, ui, proof.UI, binding,
            runtime=pair["runtime"], approved=approved["ui_descriptor"], fixture=fixture, app_path=app)
        copied_descriptors.append((ui, ui_proof["copied_sha256"]))
        proof.save(args.evidence / "ui-descriptor.json", ui_proof)
        shutil.copyfile(ui, args.evidence / "ui-bound.xctestrun")
        receipt["phase"] = "ACTUAL_NEW_MOUNTED_JOURNEY"
        receipt["ui_commands_started"] = 1
        receipt["ui_execution"] = enumerate_and_run(runner, ui, owned_udid, proof.UI,
            ui_proof["enumeration_plan"], args.evidence / "ui", receipt)
        capture_path = copy_original_fixture(runner, owned_udid, args.evidence, "pinkha-semantic-page154-mounted-capture.json")
        reopen_path = copy_original_fixture(runner, owned_udid, args.evidence, "pinkha-semantic-page154-mounted-reopen.json")
        captured = proof.read(capture_path, 65_536); reopened = proof.read(reopen_path, 65_536)
        receipt["mounted_proof"] = proof.observations(fixture, captured, reopened, capture_path.read_bytes(), binding)
        receipt["ui_observation_attachments"] = ui_attachments(args.evidence / "ui/actual-attachments",
            owned_udid, captured, reopened)
        receipt.update(status=proof.PASS, phase="COMPLETE", new_preparation_methods_passed=1, new_ui_methods_passed=1)
    except BaseException as error:
        primary = error; receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        finalizing = True
        created = args.evidence / "create-owned-simulator.log"
        if owned_udid is None and created.is_file() and consumer.owned.valid_udid(created.read_text().strip()):
            owned_udid = created.read_text().strip()
        if owned_udid and primary is not None:
            # Retain only our three safe synthetic files before disposable teardown.
            # Never enumerate or export the account store, keychain, or raw logs.
            try:
                container_log, record = runner.run(["xcrun", "simctl", "get_app_container", owned_udid,
                    "io.anytype.app", "data"], "failure-owned-app-container", 30, check=False)
                if record.get("return_code") == 0:
                    container = Path(container_log.read_text().strip())
                    if container.is_absolute() and container.is_dir() and not container.is_symlink():
                        saved = {}
                        for name in ("fixture", "capture", "reopen"):
                            filename = "pinkha-semantic-page154-mounted-" + name + ".json"
                            original_file = container / "Library/Application Support" / filename
                            target = args.evidence / filename
                            if original_file.is_file() and not original_file.is_symlink() and not target.exists():
                                proof.require(original_file.resolve().is_relative_to(container.resolve())
                                    and original_file.stat().st_size <= 65_536, "Unsafe failed synthetic observation")
                                shutil.copyfile(original_file, target)
                                saved[filename] = proof.digest(target)
                        receipt["failed_original_observations_preserved"] = saved
            except BaseException as error:
                receipt["failed_observation_export_error"] = type(error).__name__
        if owned_udid:
            receipt["owned_simulator_cleanup"] = {}
            for action in ("shutdown", "delete"):
                try:
                    _, record = runner.run(["xcrun", "simctl", action, owned_udid], "cleanup-owned-" + action, 30)
                    receipt["owned_simulator_cleanup"][action] = {"status": "PASS", "return_code": record["return_code"]}
                except BaseException as error:
                    receipt["owned_simulator_cleanup"][action] = {"status": "FAIL", "error_type": type(error).__name__}
                    if primary is None: primary = error
        try:
            proof.require(consumer.checkout_inputs(ROOT, head) == inputs, "Exact controller/product source changed")
            for path, expected in original_descriptors + copied_descriptors:
                proof.require(proof.digest(path) == expected, "Original or copied descriptor changed")
            receipt["restored_products_unchanged"] = []
            for root, manifest in restores:
                extras = [path for path, _ in copied_descriptors if path.is_relative_to(root)]
                receipt["restored_products_unchanged"].append(proof.verify_restored_products(root, manifest, extras))
            proof.save(args.evidence / "controller-source-after.json", inputs)
            receipt["source_and_descriptors_unchanged"] = True
        except BaseException as error:
            receipt["integrity_failure"] = {"error_type": type(error).__name__, "error": str(error)}
            if primary is None: primary = error
        if primary is not None or cancelled: receipt["status"] = "FAIL"
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        proof.save(args.evidence / "execution.json", receipt)
        for number, handler in previous.items(): signal.signal(number, handler)
    return int(receipt["status"] != proof.PASS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("app", "admission", "work", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for name in ("app", "admission", "work", "evidence"):
        setattr(args, name, getattr(args, name).resolve())
    receipt = {"protocol": proof.PROTOCOL, "status": "NOT_RUN", "phase": "ADMISSION",
        "started_at": datetime.now(timezone.utc).isoformat(), "native_builds": 0, "app_builds": 0, "ui_builds": 0,
        "previous_native_or_boundary_methods_rerun": 0, "new_preparation_methods_passed": 0, "new_ui_methods_passed": 0,
        "limits": {"shipping": "OFF", "physicalDevice": "NOT_RUN", "fullProductAcceptance": False}}
    try:
        return execute(args, receipt)
    except BaseException as error:
        receipt.update(status="FAIL_BEFORE_OWNED_EXECUTION", error_type=type(error).__name__, error=str(error),
            finished_at=datetime.now(timezone.utc).isoformat())
        if args.evidence.exists(): proof.save(args.evidence / "execution.json", receipt)
        print(json.dumps({"status": receipt["status"], "error_type": type(error).__name__, "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
