#!/usr/bin/env python3
"""Build the real candidate App, then run exactly one new Page154 XCTest."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
from uuid import uuid4
import zipfile

import consumer_contract as proof

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
sys.path.insert(0, str(ROOT / "Tools/PinkhaNativeDerived"))
import early_build_products
import run_owned_single_lane as supervisor
import run_ui27 as shared
import shared_editor_existing_build as component
import simulator_selection
import wave15_batch as owned
import ui_build

spec = importlib.util.spec_from_file_location(
    "semantic_page_producer_contract", ROOT / "Tools/PinkhaSemanticAnchorWire/apple_runtime/contract.py")
producer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = producer
spec.loader.exec_module(producer)

BUILD_FLAGS = [
    "OTHER_SWIFT_FLAGS=$(inherited) -D DEBUG -D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 "
        "-D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1",
    "ENABLE_TESTABILITY=YES", "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone",
    "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES",
    "PROVISIONING_PROFILE_SPECIFIER=",
]


class Commands:
    def __init__(self, root, evidence, receipt):
        self.root, self.evidence, self.receipt = root, evidence, receipt

    def run(self, argv, name, timeout=60, *, destination=None, check=True):
        proof.require(re.fullmatch("[a-z0-9-]+", name), "Invalid owned command identity")
        path = destination or self.evidence / (name + ".log")
        proof.require(not path.exists(), "Refuse stale command output")
        primary = None
        try:
            record = owned.run_worker_command(argv, self.root, path, timeout)
        except BaseException as error:
            primary = error
            record = json.loads(path.with_suffix(".command.json").read_bytes())
        try:
            record["owned_group_quiescence"] = supervisor.verify_owned_group_stopped(
                path.with_suffix(".command.json"), cleanup_profile="semantic-page154")
        except BaseException as error:
            record["quiescence_failure"] = dict(error_type=type(error).__name__, error=str(error),
                timeout_observations=getattr(error, "timeout_observations", []),
                quiescence_observation=getattr(error, "quiescence_observation", None))
            if primary is None: primary = error
        record.update(name=name, log_sha256=proof.digest(path) if path.is_file() else None)
        self.receipt.setdefault("commands", []).append(record)
        proof.save(self.evidence / "execution.json", self.receipt)
        if primary: raise primary
        proof.require(not check or record.get("return_code") == 0, "Owned command failed: " + name)
        return path, record

    def json(self, argv, name, timeout=60):
        path, _ = self.run(argv, name, timeout)
        return json.loads(path.read_bytes())


def xctest_command(configuration, udid, *, enumeration=None, result=None):
    proof.require(owned.valid_udid(udid) and (enumeration is None) != (result is None),
                  "Exactly one owned native enumeration or execution is required")
    command = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
               "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
               "-only-testing", proof.SELECTOR]
    if enumeration is not None:
        command += ["-enumerate-tests", "-test-enumeration-style", "flat", "-test-enumeration-format", "json",
                    "-test-enumeration-output-path", str(enumeration)]
    else:
        command += ["-resultBundlePath", str(result)]
    return command


def exact_native_enumeration(payload):
    plan, enabled, disabled = component.enumerated_identifiers(payload)
    proof.require(plan == "AnytypeTests" and len(enabled) == 1 and
                  proof.canonical_case(next(iter(enabled))) == proof.SUITE + "/" + proof.METHOD
                  and not enabled.intersection(disabled),
                  "Actual compiled selection differs from exact one new method in the original AnytypeTests plan")
    return dict(plan=plan, enabled=sorted(enabled))


def checkout_inputs(root, head):
    """Bind all tracked input bytes, including every imported in-repo controller."""
    proof.require(producer.git(root, "rev-parse", "HEAD") == head
                  and not producer.git(root, "status", "--porcelain", "--untracked-files=no"),
                  "Exact clean published source checkout required")
    rows = subprocess.check_output(["git", "-C", str(root), "ls-tree", "-rz", head], timeout=30)
    actual = {}
    for row in filter(None, rows.split(b"\0")):
        metadata, name = row.split(b"\t", 1)
        mode, kind, expected = metadata.decode("ascii").split()
        name = name.decode("utf8"); path = root / proof.relative(name)
        proof.require(kind == "blob" and mode in {"100644", "100755", "120000"},
                      "Unreviewed tracked source kind")
        raw = str(path.readlink()).encode("utf8") if mode == "120000" else path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        proof.require(blob == expected, "Tracked input differs from exact source SHA: " + name)
        actual[name] = hashlib.sha256(raw).hexdigest()
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw: continue
        path = Path(raw).resolve()
        if path.suffix == ".py" and path.is_relative_to(root):
            name = path.relative_to(root).as_posix()
            proof.require(name in actual and proof.digest(path) == actual[name],
                          "Loaded helper is not exact tracked source")
    return actual


def download_producer(runner, work, evidence, manifest, expected_files):
    api = runner.json(["gh", "api", "repos/" + proof.REPOSITORY + "/actions/runs/" +
                       proof.PRODUCER_RUN + "/attempts/1"], "producer-run-api")
    proof.api_run(api)
    paths = {}
    for kind, expected in proof.ARTIFACTS.items():
        value = runner.json(["gh", "api", "repos/" + proof.REPOSITORY + "/actions/artifacts/" +
                             str(expected["id"])], "producer-" + kind + "-api")
        proof.api_artifact(value, kind)
        destination = work / (kind + ".zip")
        runner.run(["gh", "api", "repos/" + proof.REPOSITORY + "/actions/artifacts/" +
                    str(expected["id"]) + "/zip"], "download-" + kind, 300, destination=destination)
        proof.require(destination.stat().st_size == expected["bytes"]
                      and proof.digest(destination) == expected["sha256"], "Original producer archive differs")
        paths[kind] = destination
    archive = work / proof.ARCHIVE_NAME
    with zipfile.ZipFile(paths["runtime"]) as source:
        proof.require(source.namelist() == [proof.ARCHIVE_NAME], "Unexpected runtime wrapper archive")
        with source.open(proof.ARCHIVE_NAME) as incoming, archive.open("xb") as output:
            shutil.copyfileobj(incoming, output, 1024 * 1024)
    packaged = proof.install_runtime(archive, ROOT / "Dependencies/Middleware", expected_files)
    originals = evidence / "producer-originals"; originals.mkdir()
    with zipfile.ZipFile(paths["proof"]) as source:
        proof.require(len(source.namelist()) == len(set(source.namelist())), "Duplicate original producer proof member")
        for name in ("build.json", "runtime-artifact.json", "generated-entry.json",
                     "actual-exported-symbols.log", "actual-swift-entry-typecheck.command.json"):
            proof.require(source.getinfo(name).file_size <= 8_000_000, "Unbounded original producer receipt")
            (originals / name).write_bytes(source.read(name))
    proof.producer_proof(json.loads((originals / "build.json").read_bytes()), packaged, manifest, expected_files)
    shutil.copyfile(ROOT / "Dependencies/Middleware" / proof.RECEIPT_NAME, originals / proof.RECEIPT_NAME)
    return dict(run_id=proof.PRODUCER_RUN, source_sha=proof.PRODUCER_SHA,
                artifact_sha256={kind: row["sha256"] for kind, row in proof.ARTIFACTS.items()},
                archive_sha256=proof.ARCHIVE_SHA, packaged_receipt_sha256=proof.RECEIPT_SHA,
                framework_files_sha256=expected_files, original_native_methods_rerun=0,
                producer_scope="BUILD_HEADER_SYMBOL_AND_TINY_SIGNATURE_TYPECHECK_ONLY")


def exported_xctest(runner, result, evidence):
    errors = []
    for kind in ("summary", "tests"):
        try:
            runner.run(["xcrun", "xcresulttool", "get", "test-results", kind, "--path", str(result),
                        "--format", "json"], "export-test-" + kind, 120,
                       destination=evidence / ("actual-" + kind + ".json"))
        except BaseException as error:
            errors.append(dict(stage=kind, error_type=type(error).__name__, error=str(error)))
    try:
        runner.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result),
                    "--output-path", str(evidence / "actual-attachments")], "export-test-attachments", 180)
    except BaseException as error:
        errors.append(dict(stage="attachments", error_type=type(error).__name__, error=str(error)))
    proof.require(not errors, "Actual xcresult export failed: " + json.dumps(errors))


def execute(args, receipt):
    proof.require(platform.system() == "Darwin" and platform.machine() == "arm64",
                  "Actual ARM64 Apple runner required")
    proof.require(ROOT == args.app and not args.work.exists() and not args.evidence.exists(),
                  "Fresh isolated App/work/evidence paths required")
    args.work.mkdir(parents=True); args.evidence.mkdir(parents=True)
    head = producer.git(ROOT, "rev-parse", "HEAD")
    run_binding = proof.binding(dict(sourceSHA=head, runID=os.environ.get("GITHUB_RUN_ID"),
                                    runAttempt=os.environ.get("GITHUB_RUN_ATTEMPT"), nonce=uuid4().hex))
    proof.require(head == os.environ.get("GITHUB_SHA"), "Actual App checkout must equal dispatched source")
    receipt["binding"] = run_binding
    inputs = checkout_inputs(ROOT, head)
    proof.save(args.evidence / "source-before.json", inputs)
    # Frozen only after the product owner finalizes the real App factory/fence.
    source_pins = json.loads((Path(__file__).parent / "candidate-sources.json").read_bytes())
    proof.require(source_pins and all(inputs.get(path) == expected for path, expected in source_pins.items()),
                  "Reviewed candidate factory/App/test/publication source closure differs")
    mounted_build_plan = ui_build.read_plan(ROOT, inputs)
    receipt["mounted_build_plan"] = dict(source_plan_sha256=mounted_build_plan["source_plan_sha256"],
                                        mounted_source_origin_sha=mounted_build_plan["mounted_source_origin_sha"])
    manifest = producer.candidate(ROOT)
    receipt["retained_native"] = producer.retained_native(ROOT, manifest)
    expected_files = json.loads((Path(__file__).parent / "framework-files.json").read_bytes())
    runner = Commands(ROOT, args.evidence, receipt)
    primary = None; udid = None; original = None; copied = None; descriptor = None; derived = None
    finalizing = False; cancelled = False
    previous = {}
    def cancel(signum, frame):
        nonlocal cancelled
        cancelled = True
        if not finalizing: raise KeyboardInterrupt("Owned Page154 consumer cancelled")
    for number in (signal.SIGINT, signal.SIGTERM):
        previous[number] = signal.getsignal(number); signal.signal(number, cancel)
    try:
        receipt["phase"] = "ORIGINAL_PRODUCER"
        receipt["producer"] = download_producer(runner, args.work, args.evidence, manifest, expected_files)
        os.environ["PINKHA_NATIVE_T2_AUTHORIZED_READ_V1"] = "1"
        os.environ["PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1"] = proof.MANIFEST_SHA
        runner.run([sys.executable, "-B", "Tools/Hanlin/prepare_sdk.py", "--source", str(args.hanlin_source)],
                   "prepare-canonical-hanlin", 180)
        runner.run([sys.executable, "-B", "Tools/Hanlin/prepare_sdk.py", "--check"], "check-canonical-hanlin", 60)
        shutil.copyfile(ROOT / "Dependencies/Hanlin/.pinkha-source.json", args.evidence / "hanlin-snapshot.json")
        version, _ = runner.run(["xcodebuild", "-version"], "xcode-version")
        proof.require(version.read_text().startswith("Xcode 27."), "Actual Xcode27 required")
        runtimes = runner.json(["xcrun", "simctl", "list", "runtimes", "-j"], "available-runtimes", 30)
        devices = runner.json(["xcrun", "simctl", "list", "devicetypes", "-j"], "available-device-types", 30)
        pair = simulator_selection.choose_pair(runtimes, devices, product_family="iPad", major=27, architecture="arm64")
        path, _ = runner.run(["xcrun", "simctl", "create", "Page154Consumer-" + run_binding["nonce"],
                              pair["device"]["identifier"], pair["runtime"]["identifier"]],
                             "create-owned-simulator", 60)
        udid = path.read_text().strip()
        proof.require(owned.valid_udid(udid), "Invalid actual owned simulator UUID")
        receipt["owned_simulator"] = dict(udid=udid, nonce=run_binding["nonce"], selection=pair["selection"])
        runner.run(["xcrun", "simctl", "boot", udid], "boot-owned-simulator", 90)
        runner.run(["xcrun", "simctl", "bootstatus", udid, "-b"], "wait-owned-simulator", 180)
        derived = args.work / "derived"
        shared.prepare_source_cache(ROOT, derived)
        receipt["phase"] = "BUILD_ACTUAL_APP"
        command = ["xcodebuild", "build-for-testing", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
                   "-configuration", "Debug-Anytype", "-destination", "platform=iOS Simulator,id=" + udid,
                   "-parallel-testing-enabled", "NO", "-derivedDataPath", str(derived),
                   "-only-testing:" + proof.SELECTOR, *BUILD_FLAGS]
        receipt["app_builds_started"] = 1
        runner.run(command, "build-actual-candidate-app", 6000)
        receipt["app_build_succeeded"] = True
        receipt["early_products"] = early_build_products.capture(
            derived, args.evidence, source_sha=head, run_id=run_binding["runID"],
            run_attempt=run_binding["runAttempt"], build_flags=BUILD_FLAGS, scope="semantic-page154")
        proof.framework_unchanged(ROOT / "Dependencies/Middleware/Lib.xcframework", expected_files)
        proof.require(checkout_inputs(ROOT, head) == inputs, "Source changed during the App build")
        products = derived / "Build/Products"
        built = products / "Debug-Anytype-iphonesimulator/Anytype.app"
        verification = ("import sys;from pathlib import Path;sys.path.insert(0," +
                        repr(str(ROOT / "Tools/PinkhaSimulatorGate")) + ");import run_ui27 as s;"
                        "s.verify_signed_simulator(Path(" + repr(str(built)) + "),Path(" + repr(str(args.evidence)) + "));"
                        "s.verify_runtime_copies(Path(" + repr(str(built)) + ")," + repr(proof.VERSION.encode("utf8")) +
                        ",Path(" + repr(str(args.evidence)) + "))")
        runner.run([sys.executable, "-B", "-c", verification], "verify-built-signatures-and-runtime", 120)
        original = shared.test_configuration(products, "AnytypeTests")
        copied = original.with_name("Page154-" + run_binding["nonce"] + ".xctestrun")
        descriptor = proof.copied_descriptor(original, copied, run_binding)
        receipt["descriptor"] = descriptor
        shutil.copyfile(original, args.evidence / "original.xctestrun")
        shutil.copyfile(copied, args.evidence / "bound.xctestrun")
        receipt["phase"] = "ENUMERATE_EXACT_ONE"
        enumeration = args.evidence / "enumeration.json"
        runner.run(xctest_command(copied, udid, enumeration=enumeration), "enumerate-exact-one", 600)
        receipt["enumeration"] = dict(exact_native_enumeration(json.loads(enumeration.read_bytes())),
                                      sha256=proof.digest(enumeration))
        proof.require(proof.digest(original) == descriptor["original_sha256"]
                      and proof.digest(copied) == descriptor["copied_sha256"], "Descriptor changed before execution")
        receipt["phase"] = "ACTUAL_XCTEST"
        result = args.evidence / "actual-page154.xcresult"
        test_error = None
        receipt["actual_xctest_commands_started"] = 1
        try:
            runner.run(xctest_command(copied, udid, result=result), "actual-single-xctest", 900)
        except BaseException as error:
            test_error = error
        if result.exists() and not cancelled:
            try: exported_xctest(runner, result, args.evidence)
            except BaseException as error:
                receipt["export_error"] = dict(error_type=type(error).__name__, error=str(error))
                if test_error is None: test_error = error
        if test_error: raise test_error
        receipt["actual_execution"] = proof.exact_execution(
            json.loads((args.evidence / "actual-summary.json").read_bytes()),
            json.loads((args.evidence / "actual-tests.json").read_bytes()), udid)
        attachment = proof.attachment(args.evidence / "actual-attachments", udid)
        receipt["observation"] = proof.observation(json.loads(attachment.read_bytes()), run_binding)
        receipt["observation_sha256"] = proof.digest(attachment)
        receipt.update(native_boundary_status=proof.PASS, actual_product_methods_passed=1)
        receipt["native_products_integrity_before_ui_build"] = ui_build.verify_preserved_products(
            derived, args.evidence, receipt["early_products"], run_binding, BUILD_FLAGS,
            descriptor_additions={copied.relative_to(derived).as_posix(): descriptor["copied_sha256"]})
        receipt["phase"] = "BUILD_MOUNTED_UI_RUNNER_ONLY"
        ui_build.build_mounted_ui(runner, ROOT, args.work, args.evidence, run_binding, BUILD_FLAGS,
                                  mounted_build_plan, shared, receipt, udid)
        receipt.update(status=proof.PASS, phase="COMPLETE")
    except BaseException as error:
        primary = error
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        finalizing = True
        created = args.evidence / "create-owned-simulator.log"
        if udid is None and created.is_file() and owned.valid_udid(created.read_text().strip()):
            udid = created.read_text().strip()
            receipt["owned_simulator_recovered_from_create_stdout"] = udid
        if udid:
            receipt["owned_simulator_cleanup"] = {}
            for action in ("shutdown", "delete"):
                try:
                    _, record = runner.run(["xcrun", "simctl", action, udid], "cleanup-owned-" + action, 30)
                    receipt["owned_simulator_cleanup"][action] = dict(status="PASS", return_code=record["return_code"])
                except BaseException as error:
                    receipt["owned_simulator_cleanup"][action] = dict(status="FAIL", error_type=type(error).__name__,
                                                                      error=str(error))
                    if primary is None: primary = error
        try:
            proof.require(checkout_inputs(ROOT, head) == inputs, "Final exact source closure differs")
            proof.save(args.evidence / "source-after.json", inputs)
            if receipt.get("producer"):
                proof.framework_unchanged(ROOT / "Dependencies/Middleware/Lib.xcframework", expected_files)
            if descriptor:
                proof.require(proof.digest(original) == descriptor["original_sha256"]
                              and proof.digest(copied) == descriptor["copied_sha256"], "Final descriptor bytes differ")
            if receipt.get("early_products") and derived is not None:
                additions = {copied.relative_to(derived).as_posix(): descriptor["copied_sha256"]} if descriptor else {}
                receipt["native_products_integrity_final"] = ui_build.verify_preserved_products(
                    derived, args.evidence, receipt["early_products"], run_binding, BUILD_FLAGS,
                    descriptor_additions=additions)
            ui_preservation = receipt.get("ui_runner_build", {}).get("early_products")
            if ui_preservation:
                receipt["ui_products_integrity_final"] = ui_build.verify_preserved_products(
                    args.work / "derived-ui", args.evidence, ui_preservation, run_binding, BUILD_FLAGS)
            receipt["source_and_framework_unchanged"] = True
        except BaseException as error:
            receipt["integrity_error"] = dict(error_type=type(error).__name__, error=str(error))
            if primary is None: primary = error
        if primary or cancelled: receipt["status"] = "FAIL"
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        proof.save(args.evidence / "execution.json", receipt)
        for number, handler in previous.items(): signal.signal(number, handler)
    return int(receipt["status"] != proof.PASS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("app", "hanlin-source", "work", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for name in ("app", "hanlin_source", "work", "evidence"):
        setattr(args, name, getattr(args, name).resolve())
    receipt = dict(protocol=proof.PROTOCOL, status="NOT_RUN", phase="ADMISSION",
                   started_at=datetime.now(timezone.utc).isoformat(), native_builds=0, native_methods_rerun=0,
                   existing_product_methods_rerun=0, limits=proof.LIMITS)
    try: status = execute(args, receipt)
    except BaseException as error:
        receipt.update(status="FAIL_ADMISSION", error_type=type(error).__name__, error=str(error))
        proof.save(args.evidence / "execution.json", receipt); status = 1
    print(json.dumps({key: receipt[key] for key in ("status", "phase", "native_builds",
                                                  "native_methods_rerun", "existing_product_methods_rerun")}))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
