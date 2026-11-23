#!/usr/bin/env python3
"""Probe Xcode27 selector grammar against immutable original SDK06 Products.

Every Xcode test action is permanently enumerate-only. A matching selection is
not a test pass, an accepted build, or permission to execute any product test.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
from uuid import uuid4
import zipfile

import run_owned_single_lane as supervisor
import shared_editor_existing_build as component
import simulator_selection
import wave15_batch as owned

REPOSITORY = "davidpovarsky/anytype-swift"
ORIGINAL_RUN = "45087685319"
ORIGINAL_ATTEMPT = "1"
ORIGINAL_SOURCE = "7293e4fd0bcabdcdb643d5768b777b8e87ff1b73"
ARTIFACT_ID = 14782666651
ARTIFACT_NAME = "Pinkha-UI27-hanlin-native-shared-editor-45087685319-1"
OUTER_SHA = "6e22d77dcf964edef2c88a6c5d1b6375c21c9bb9213fab761e0d64b349d95450"
OUTER_BYTES = 697865578
INNER_NAME = "Pinkha-Native-Derived-Evidence.zip"
PRODUCTS_NAME = "sdk06-early-products/BuildProducts.tar.gz"
PRODUCTS_SHA = "7a741f05df92143622a7d07b07682260c0c2281c4b700586fd80839bbc282822"
PRODUCTS_BYTES = 713955862
MANIFEST_NAME = "sdk06-early-products/manifest.json"
MANIFEST_SHA = "cd9a4743f4bec103a8805c0755df680997268147147706287a9356bca75a1889"
EXECUTION_SHA = "2c5dd3601567cc28fd1a0f240e14da7c675d1b4653c91840cbebbada80699e01"
SOURCES = {
    "AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift": "0b533aa0500b9a62043d1f5e49827e6be1ac2ce0f839fa6496b6da81ab26dcbf",
    "AnyTypeTests/Pinkha/SimpleTableTextPersistenceTests.swift": "dbe44987c62f85dc1a26571d0effc8a2138e9aaf6657eec1d469a8517e294166",
    "AnyTypeTests/Pinkha/TorahRelatedReadAuthorityMappingTests.swift": "07675b9e09777ebb5fc503bafcd814dcc10fefb0a950d5ff6231da7b3f51e8b1",
}
XCTESTRUN = "Build/Products/Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun"
XCTESTRUN_SHA = "eb7baf907400841fd1a5e7a687ad0a843e12ff6ddab958d8037fed90a7e767d1"
SOURCE_INPUTS_SHA = "8fdd584e5eecf8fdabc1bf6059070dc662d2f1e6d7ba75706ed89517c98fa4f8"
PROBE_PASS = "EXACT23_ENUMERATED_PRODUCT_TESTS_NOT_RUN"
PROBE_FAIL = "NO_SELECTOR_QUALIFIED_PRODUCT_TESTS_NOT_RUN"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    return owned.digest(path)


def save(path, value):
    owned.write(path, value)


def _api_artifact(value):
    require(isinstance(value, dict) and type(value.get("id")) is int and value["id"] == ARTIFACT_ID
            and value.get("name") == ARTIFACT_NAME and value.get("digest") == "sha256:" + OUTER_SHA
            and value.get("size_in_bytes") == OUTER_BYTES and value.get("expired") is False,
            "Original SDK artifact API metadata differs")
    run = value.get("workflow_run", {})
    require(run.get("id") == int(ORIGINAL_RUN) and run.get("head_sha") == ORIGINAL_SOURCE
            and run.get("head_branch") == "codex/chatgpt-wave15-acceptance-continuation-20261122",
            "Original SDK artifact belongs to another source/run")


def _api_run(value):
    require(isinstance(value, dict) and type(value.get("id")) is int and value["id"] == int(ORIGINAL_RUN)
            and type(value.get("run_attempt")) is int and value["run_attempt"] == int(ORIGINAL_ATTEMPT) and value.get("head_sha") == ORIGINAL_SOURCE
            and value.get("event") == "workflow_dispatch" and value.get("status") == "completed"
            and value.get("conclusion") == "failure"
            and value.get("repository", {}).get("full_name") == REPOSITORY
            and value.get("path") == ".github/workflows/torah-inspector-ipados27.yml",
            "Original failed SDK attempt identity differs")


def _safe_product(name):
    require(isinstance(name, str) and name, "Invalid archived product path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and "\\" not in name
            and all(part not in {"", ".", ".."} for part in name.split("/"))
            and (name == "Build/PinkhaSourceInputs.json" or name == "Build/Products"
                 or name.startswith("Build/Products/")), "Unexpected archived product path")
    return path


def extract_products(archive, destination, manifest):
    """Restore exact regular entries only; no links or generic tar extraction."""
    require(not destination.exists(), "Fresh product restoration directory required")
    entries = manifest["products"]
    require(isinstance(entries, dict) and entries, "Empty original product manifest")
    for name, entry in entries.items():
        _safe_product(name)
        require(entry.get("kind") in {"file", "directory"}, "This fixed archive must contain no links")
    destination.mkdir(parents=True)
    observed = set()
    with tarfile.open(archive, mode="r:gz") as stream:
        for member in stream:
            name = member.name
            relative = _safe_product(name)
            require(name in entries and name not in observed, "Extra or duplicate archived product")
            expected = entries[name]
            require(member.mode == expected["mode"], "Archived product mode differs")
            target = destination.joinpath(*relative.parts)
            require(target.resolve().is_relative_to(destination.resolve()), "Product escapes owned restoration")
            if expected["kind"] == "directory":
                require(member.isdir(), "Archived directory kind differs")
                target.mkdir(parents=True, exist_ok=True)
            else:
                require(member.isfile() and not member.islnk() and not member.issym()
                        and member.size == expected["bytes"], "Archived regular file kind/size differs")
                target.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                require(sha(target) == expected["sha256"], "Restored original file bytes differ")
            target.chmod(expected["mode"])
            observed.add(name)
    require(observed == set(entries), "Original Products archive is incomplete")
    return {"entries": len(observed), "status": "ORIGINAL_BYTES_RESTORED_ENUMERATION_ONLY"}


def product_manifest_unchanged(destination, manifest):
    for name, entry in manifest["products"].items():
        path = destination.joinpath(*_safe_product(name).parts)
        require(not path.is_symlink() and path.stat().st_mode & 0o777 == entry["mode"], "Original product mode changed")
        require((entry["kind"] == "directory" and path.is_dir()) or
                (entry["kind"] == "file" and path.is_file() and path.stat().st_size == entry["bytes"]
                 and sha(path) == entry["sha256"]), "Original restored product bytes changed")


def selection_contract(execution, discovery):
    source = execution.get("shared_editor_components", {}).get("source", {})
    require(execution.get("source_sha") == ORIGINAL_SOURCE and execution.get("run_id") == ORIGINAL_RUN
            and execution.get("run_attempt") == ORIGINAL_ATTEMPT and execution.get("native_build_succeeded") is True
            and execution.get("phase") == "SHARED_EDITOR_COMPONENTS"
            and execution.get("error") == "Compiled pending selection differs from the exact23 methods; no tests executed",
            "Original build/failed admission scope differs")
    require(source.get("source_hashes") == SOURCES and source.get("expected_methods") == 23
            and source.get("declared_invocations") == 32, "Frozen pending source inventory differs")
    declarations = source.get("compiled_declarations", {})
    require(isinstance(declarations, dict) and len(declarations) == 30, "Exactly30 reviewed source declarations required")
    selected = [declarations[name] for name in source.get("methods", [])]
    require(len(selected) == len(set(selected)) == 23, "Exactly23 unique pending declarations required")
    excluded = sorted(set(declarations.values()) - set(selected))
    require({declarations[name] for name in source.get("unselected_existing_methods", [])} == set(excluded),
            "Original named exclusions differ from the complement")
    require(len(excluded) == 7 and sum(not name.endswith("()") for name in excluded) == 3,
            "Exact seven exclusions, including three parameterized declarations, required")
    plan, enabled, disabled = component.enumerated_identifiers(discovery)
    require(enabled == set(declarations.values()) and not enabled.intersection(disabled),
            "Original actual suite discovery differs from reviewed30 declarations")
    return dict(test_plan=plan, selected=sorted(selected), excluded=excluded, declarations=sorted(enabled))


def variants(selection):
    exact = selection["selected"]
    suites = ["AnytypeTests/" + name for name in component.SUITES]
    decorated = [name if name.endswith("()") else name + "()" for name in exact]
    return [
        dict(name="exact-plist-only", include=exact, exclude=[], cli=[]),
        dict(name="exact-separate-argv", include=exact, exclude=[], cli=exact),
        dict(name="suites-minus-seven-plist", include=suites, exclude=selection["excluded"], cli=[]),
        # A bounded syntax hypothesis, not an accepted identifier translation.
        # Full original compiled identities remain the only admission target.
        dict(name="parameter-signature-terminal-parens", include=decorated, exclude=[], cli=[]),
    ]


def copied_configuration(original, destination, variant):
    before = original.read_bytes()
    original_value = plistlib.loads(before)
    component.scoped_configuration(original, destination, variant["include"], sys.modules[__name__])
    value = plistlib.loads(destination.read_bytes())
    original_targets = original_value["TestConfigurations"][0]["TestTargets"]
    original_target = next(target for target in original_targets if target.get("BlueprintName") == "AnytypeTests")
    target = value["TestConfigurations"][0]["TestTargets"][0]
    old_skip = original_target.get("SkipTestIdentifiers", [])
    require(isinstance(old_skip, list) and all(isinstance(item, str) for item in old_skip),
            "Unexpected original skip identifiers")
    additions = [item.removeprefix("AnytypeTests/") for item in variant["exclude"]]
    if additions:
        target["SkipTestIdentifiers"] = list(dict.fromkeys(old_skip + additions))
        with destination.open("wb") as stream:
            plistlib.dump(value, stream, sort_keys=False)
    require({key: val for key, val in target.items() if key not in {"OnlyTestIdentifiers", "SkipTestIdentifiers"}} ==
            {key: val for key, val in original_target.items() if key not in {"OnlyTestIdentifiers", "SkipTestIdentifiers"}},
            "Non-selection target configuration changed")
    require(original.read_bytes() == before, "Original xctestrun was modified")
    return dict(original_sha256=sha(original), copied_sha256=sha(destination),
                only=target["OnlyTestIdentifiers"], skip=target.get("SkipTestIdentifiers", []))


# The existing scoped_configuration helper expects this narrow digest interface.
digest = sha


def enumeration_command(configuration, udid, output, result_bundle, variant):
    require(owned.valid_udid(udid), "Owned simulator UUID required")
    command = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
               "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO"]
    for identifier in variant["cli"]:
        command += ["-only-testing", identifier]
    command += ["-enumerate-tests", "-test-enumeration-style", "flat", "-test-enumeration-format", "json",
                "-test-enumeration-output-path", str(output), "-resultBundlePath", str(result_bundle)]
    require(command.count("-enumerate-tests") == 1 and "build-for-testing" not in command,
            "Probe cannot execute or build product tests")
    return command


def qualify_enumeration(payload, selection):
    plan, enabled, disabled = component.enumerated_identifiers(payload)
    expected = set(selection["selected"])
    require(plan == selection["test_plan"] and enabled == expected and not expected.intersection(disabled),
            "Probe did not enumerate exactly the requested23 methods")
    require(set(selection["excluded"]) <= disabled, "An excluded existing method was not explicitly disabled")
    return dict(status=PROBE_PASS, enabled=sorted(enabled), excluded=selection["excluded"],
                selected_method_count=23, expected_future_cases=32, actual_product_tests_executed=0)


class Commands:
    def __init__(self, cwd, evidence, receipt):
        self.cwd, self.evidence, self.receipt = cwd, evidence, receipt

    def run(self, argv, name, timeout=60, destination=None, check=True):
        require(re.fullmatch(r"[a-z0-9-]+", name), "Invalid owned command name")
        path = destination or self.evidence / (name + ".log")
        require(not path.exists(), "Refuse stale owned command output")
        primary = None
        try:
            record = owned.run_worker_command(argv, self.cwd, path, timeout)
        except BaseException as error:
            primary = error
            record = json.loads(path.with_suffix(".command.json").read_bytes())
        try:
            record["owned_group_quiescence"] = supervisor.verify_owned_group_stopped(path.with_suffix(".command.json"))
        except BaseException as error:
            record["quiescence_failure"] = dict(error_type=type(error).__name__, error=str(error))
            if primary is None:
                primary = error
        record.update(name=name, output_path=str(path), output_sha256=sha(path) if path.is_file() else None)
        self.receipt.setdefault("commands", []).append(record)
        save(self.evidence / "receipt.json", self.receipt)
        if primary:
            raise primary
        require(not check or record.get("return_code") == 0, "Owned command failed: " + name)
        return path, record

    def json(self, argv, name, timeout=60):
        path, _ = self.run(argv, name, timeout)
        return json.loads(path.read_bytes())


def _download_original(run, work, evidence):
    api = run.json(["gh", "api", "repos/" + REPOSITORY + "/actions/artifacts/" + str(ARTIFACT_ID)],
                   "original-artifact-api")
    _api_artifact(api)
    attempt = run.json(["gh", "api", "repos/" + REPOSITORY + "/actions/runs/" + ORIGINAL_RUN
                        + "/attempts/" + ORIGINAL_ATTEMPT], "original-run-api")
    _api_run(attempt)
    outer = work / "original-github-artifact.zip"
    run.run(["gh", "api", "repos/" + REPOSITORY + "/actions/artifacts/" + str(ARTIFACT_ID) + "/zip"],
            "download-original-products", timeout=300, destination=outer)
    require(outer.stat().st_size == OUTER_BYTES and sha(outer) == OUTER_SHA, "Original GitHub artifact digest differs")
    inner = work / INNER_NAME
    with zipfile.ZipFile(outer) as archive:
        require(archive.namelist() == [INNER_NAME], "Unexpected original GitHub archive members")
        with archive.open(INNER_NAME) as source, inner.open("xb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
    originals = evidence / "originals"
    originals.mkdir()
    with zipfile.ZipFile(inner) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate original evidence members")
        for name in ("execution.json", MANIFEST_NAME, "shared-editor-components/execution.json",
                     "shared-editor-components/compiled-suite-enumeration.json",
                     "shared-editor-components/compiled-selected-enumeration.json",
                     "shared-editor-components/compiled-selected-enumeration-configuration.json"):
            info = archive.getinfo(name)
            require(info.file_size <= 2_000_000, "Unbounded original observation")
            path = originals / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
        product_archive = work / "original-BuildProducts.tar.gz"
        info = archive.getinfo(PRODUCTS_NAME)
        require(info.file_size == PRODUCTS_BYTES, "Original compressed Products size differs")
        with archive.open(info) as source, product_archive.open("xb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
    require(sha(product_archive) == PRODUCTS_SHA and sha(originals / MANIFEST_NAME) == MANIFEST_SHA
            and sha(originals / "execution.json") == EXECUTION_SHA, "Original retained evidence bytes differ")
    manifest = json.loads((originals / MANIFEST_NAME).read_bytes())
    require(manifest.get("source_sha") == ORIGINAL_SOURCE and manifest.get("run_id") == ORIGINAL_RUN
            and manifest.get("run_attempt") == ORIGINAL_ATTEMPT and len(manifest.get("products", {})) == 5007
            and manifest.get("archive_sha256") == PRODUCTS_SHA and manifest.get("archive_bytes") == PRODUCTS_BYTES
            and manifest.get("capture_phase") == "AFTER_BUILD_BEFORE_ADMISSION"
            and manifest.get("status") == "OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION"
            and manifest.get("build_reuse_enabled") is False and manifest.get("native_acceptance_reused") is False
            and manifest.get("ui_acceptance_reused") is False and manifest.get("every_entry_build_origin_verified") is False,
            "Unexpected original pre-admission Products scope")
    execution = json.loads((originals / "execution.json").read_bytes())
    discovery = json.loads((originals / "shared-editor-components/compiled-suite-enumeration.json").read_bytes())
    return product_archive, manifest, selection_contract(execution, discovery)


def control_sources(control, head):
    require(not subprocess.check_output(["git", "-C", str(control), "status", "--porcelain",
                                         "--untracked-files=no"], text=True, timeout=30).strip(),
            "Tracked controller source is dirty")
    hashes = {}
    for module in tuple(sys.modules.values()):
        name = getattr(module, "__file__", None)
        if not name:
            continue
        path = Path(name).resolve()
        if path.suffix != ".py" or not path.is_relative_to(control):
            continue
        relative = path.relative_to(control).as_posix()
        expected = subprocess.check_output(["git", "-C", str(control), "show", head + ":" + relative], timeout=30)
        observed = sha(path)
        require(hashlib.sha256(expected).hexdigest() == observed, "Loaded controller source differs from exact checkout")
        hashes[relative] = observed
    require("Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py" in hashes and len(hashes) >= 5,
            "Controller and imported helper source closure missing")
    return dict(sorted(hashes.items()))


def execute(args, receipt):
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple ARM64 runner required")
    require(not args.work.exists() and not args.evidence.exists(), "Fresh owned work and evidence directories required")
    args.work.mkdir(parents=True)
    args.evidence.mkdir(parents=True)
    head = subprocess.check_output(["git", "-C", str(args.control), "rev-parse", "HEAD"], text=True).strip()
    require(head == os.environ.get("GITHUB_SHA") and re.fullmatch("[0-9a-f]{40}", head),
            "Exact current control checkout required")
    receipt["control_source_sha"] = head
    receipt["control_source_hashes"] = control_sources(args.control, head)
    runner = Commands(args.control, args.evidence, receipt)
    udid = None
    product_root = None
    primary = None
    previous = {}
    cancelled = False
    finalizing = False
    import signal

    def cancel(signum, frame):
        nonlocal cancelled
        cancelled = True
        if not finalizing:
            raise KeyboardInterrupt("Owned enumeration probe cancelled")

    for number in (signal.SIGTERM, signal.SIGINT):
        previous[number] = signal.getsignal(number)
        signal.signal(number, cancel)
    try:
        xcode, _ = runner.run(["xcodebuild", "-version"], "xcode-version")
        require(xcode.read_text().startswith("Xcode 27."), "Actual Xcode27 required")
        archive, manifest, selection = _download_original(runner, args.work, args.evidence)
        for path, expected in SOURCES.items():
            source = subprocess.check_output(["git", "-C", str(args.control), "show", ORIGINAL_SOURCE + ":" + path],
                                             timeout=30)
            require(hashlib.sha256(source).hexdigest() == expected, "Original source Git bytes differ")
        receipt["selection_contract"] = selection
        product_root = args.work / "restored"
        receipt["restored_products"] = extract_products(archive, product_root, manifest)
        original = product_root / XCTESTRUN
        require(sha(original) == XCTESTRUN_SHA and sha(product_root / "Build/PinkhaSourceInputs.json") == SOURCE_INPUTS_SHA,
                "Original descriptor/source-input inventory differs")
        shutil.copyfile(original, args.evidence / "original.xctestrun")
        runtimes = runner.json(["xcrun", "simctl", "list", "runtimes", "-j"], "simulator-runtimes", 30)
        devices = runner.json(["xcrun", "simctl", "list", "devicetypes", "-j"], "simulator-types", 30)
        pair = simulator_selection.choose_pair(runtimes, devices, product_family="iPad", major=27, architecture="arm64")
        nonce = uuid4().hex
        created, _ = runner.run(["xcrun", "simctl", "create", "SDK06Enumeration-" + nonce,
                                 pair["device"]["identifier"], pair["runtime"]["identifier"]], "create-owned-simulator", 60)
        udid = created.read_text().strip()
        require(owned.valid_udid(udid), "Invalid newly created owned simulator")
        receipt["owned_simulator"] = dict(udid=udid, nonce=nonce, selection=pair["selection"])
        save(args.evidence / "receipt.json", receipt)
        runner.run(["xcrun", "simctl", "boot", udid], "boot-owned-simulator", 90)
        runner.run(["xcrun", "simctl", "bootstatus", udid, "-b"], "wait-owned-simulator", 180)
        receipt["probes"] = []
        for variant in variants(selection):
            name = variant["name"]
            configuration = original.with_name("SDK06-" + nonce + "-" + name + ".xctestrun")
            binding = copied_configuration(original, configuration, variant)
            shutil.copyfile(configuration, args.evidence / (name + ".xctestrun"))
            output = args.evidence / (name + ".enumeration.json")
            record = dict(name=name, status="NOT_QUALIFIED", binding=binding, actual_product_tests_executed=0)
            receipt["probes"].append(record)
            command = enumeration_command(configuration, udid, output, args.evidence / (name + ".xcresult"), variant)
            _, outcome = runner.run(command, "enumerate-" + name, 240, check=False)
            require(sha(original) == binding["original_sha256"] and sha(configuration) == binding["copied_sha256"],
                    "Original or candidate descriptor changed during enumeration")
            record["command_return_code"] = outcome["return_code"]
            if outcome["return_code"] == 0 and output.is_file():
                try:
                    payload = json.loads(output.read_bytes())
                    record["qualification"] = qualify_enumeration(payload, selection)
                    record["status"] = PROBE_PASS
                    record["enumeration_sha256"] = sha(output)
                    receipt.update(status=PROBE_PASS, qualified_variant=name)
                    break
                except (ValueError, KeyError, TypeError) as error:
                    record["qualification_failure"] = dict(error_type=type(error).__name__, error=str(error))
            save(args.evidence / "receipt.json", receipt)
        require(receipt.get("status") == PROBE_PASS, "No bounded selector variant qualified exact23")
    except BaseException as error:
        primary = error
        receipt.update(status=PROBE_FAIL, error_type=type(error).__name__, error=str(error))
    finally:
        finalizing = True
        created_log = args.evidence / "create-owned-simulator.log"
        if udid is None and created_log.is_file():
            observed_udid = created_log.read_text().strip()
            if owned.valid_udid(observed_udid):
                udid = observed_udid
                receipt["owned_simulator_recovered_from_original_create_stdout"] = udid
        if udid:
            cleanup = {}
            for action in ("shutdown", "delete"):
                try:
                    _, outcome = runner.run(["xcrun", "simctl", action, udid], "cleanup-owned-" + action, 30)
                    cleanup[action] = dict(status="PASS", return_code=outcome["return_code"])
                except BaseException as error:
                    cleanup[action] = dict(status="FAIL", error_type=type(error).__name__, error=str(error))
                    if primary is None:
                        primary = error
            receipt["owned_simulator_cleanup"] = cleanup
        try:
            require(control_sources(args.control, head) == receipt["control_source_hashes"],
                    "Controller source closure changed during probe")
            receipt["control_sources_unchanged"] = True
            if product_root is not None and (product_root / XCTESTRUN).is_file():
                product_manifest_unchanged(product_root, manifest)
                receipt["original_products_unchanged"] = True
        except BaseException as error:
            receipt["final_integrity_failure"] = dict(error_type=type(error).__name__, error=str(error))
            if primary is None:
                primary = error
        if cancelled:
            receipt["cancelled"] = True
            receipt["status"] = PROBE_FAIL
        if primary:
            receipt["status"] = PROBE_FAIL
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(args.evidence / "receipt.json", receipt)
        for number, handler in previous.items():
            signal.signal(number, handler)
    return 0 if receipt["status"] == PROBE_PASS else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "work", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for name in ("control", "work", "evidence"):
        setattr(args, name, getattr(args, name).resolve())
    receipt = dict(status=PROBE_FAIL, protocol="sdk06-original-products-enumeration-only-v1",
                   original_source_sha=ORIGINAL_SOURCE, original_run_id=ORIGINAL_RUN,
                   original_run_attempt=ORIGINAL_ATTEMPT, original_artifact_id=ARTIFACT_ID,
                   original_artifact_sha256=OUTER_SHA, original_products_sha256=PRODUCTS_SHA,
                   run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
                   started_at=datetime.now(timezone.utc).isoformat(), actual_product_tests_executed=0,
                   app_builds=0, full_matrix_accepted=False, sdk06_accepted=False, release_accepted=False)
    result = execute(args, receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "run_id", "run_attempt", "actual_product_tests_executed", "app_builds")}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
