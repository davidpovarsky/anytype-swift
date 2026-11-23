#!/usr/bin/env python3
"""Enumerate one evidence-derived SDK06 basename hypothesis, never product tests.

The prior 26-method result remains a failed admission. Only three parameterized
skip spellings change; this new route still requires the original exact23 gate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from uuid import uuid4

import sdk06_enumeration_probe as probe
from sdk06_enumeration_probe import (
    ARTIFACT_ID, Commands, ENUMERATION_TIMEOUT_SECONDS, ENUMERATION_TOTAL_SECONDS,
    ORIGINAL_ATTEMPT, ORIGINAL_RUN, ORIGINAL_SOURCE, OUTER_SHA, PRODUCTS_SHA,
    PROBE_FAIL, PROBE_PASS, SOURCES, SOURCE_INPUTS_SHA, XCTESTRUN, XCTESTRUN_SHA,
    _download_original, copied_configuration, enumeration_budget,
    enumeration_command, extract_products, owned, product_manifest_unchanged,
    qualify_enumeration, require, save, sha, simulator_selection,
)

BASE_PROBE_SHA = "ce2987846cdd42ebab7702e7dff51068bfb15ee48a66011f621695dbd72ebbce"
ENTRYPOINT = "Tools/PinkhaSimulatorGate/sdk06_basename_enumeration_probe.py"
PLAN = "Tools/PinkhaSimulatorGate/sdk06-basename-probe-plan.json"
WORKFLOW = ".github/workflows/pinkha-sdk06-basename-probe.yml"
PROOF_ROOT = "docs/validation/20261123-sdk06-basename-probe/original-45116213338"
PROOF_NAMES = (
    "receipt.json", "suites-minus-seven-cli.enumeration.json",
    "enumerate-suites-minus-seven-cli.command.json", "original.xctestrun",
    "suites-minus-seven-cli.xctestrun",
)
EXTRA_INTEGRITY_PATHS = (
    ENTRYPOINT, PLAN, WORKFLOW,
    ".github/workflows/torah-inspector-ipados27.yml",
) + tuple(PROOF_ROOT + "/" + name for name in PROOF_NAMES)
VARIANT_NAME = "suites-minus-seven-three-parameter-basenames-cli"
PRIOR_RUN = "45116213338"
PRIOR_SOURCE = "4eb4d17f03b36e7d3db1123ec74714d9062b3e46"


def _fixed_inputs():
    root = Path(__file__).resolve().parents[2]
    require(sha(root / "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py") == BASE_PROBE_SHA,
            "The original probe and normalizer must remain byte-identical")
    plan = json.loads((root / PLAN).read_bytes())
    require(set(plan) == {"schema", "status", "name", "prior", "replacements", "evidence"}
            and plan["schema"] == "sdk06-three-parameter-basename-hypothesis-v1"
            and plan["status"] == "UNQUALIFIED_ENUMERATION_HYPOTHESIS"
            and plan["name"] == VARIANT_NAME,
            "Only the fixed reviewed basename hypothesis is supported")
    require(plan["prior"] == dict(run_id=PRIOR_RUN, run_attempt="1", source_sha=PRIOR_SOURCE,
                                   variant="suites-minus-seven-cli"),
            "The hypothesis must derive from the exact original failed enumeration")
    require(set(plan["evidence"]) == set(PROOF_NAMES), "Fixed original proof members differ")
    originals = {}
    for name in PROOF_NAMES:
        entry = plan["evidence"][name]
        relative = PROOF_ROOT + "/" + name
        path = root / relative
        require(set(entry) == {"path", "sha256", "bytes"} and entry["path"] == relative
                and path.is_file() and not path.is_symlink()
                and path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"],
                "An original enumeration proof member differs")
        originals[name] = path.read_bytes()
    require(hashlib.sha256(originals["original.xctestrun"]).hexdigest() == XCTESTRUN_SHA,
            "The original Products descriptor differs")
    return plan, originals


def _reviewed_variant(selection, plan, originals):
    receipt = json.loads(originals["receipt.json"])
    prior = next((item for item in receipt.get("probes", [])
                  if item.get("name") == "suites-minus-seven-cli"), None)
    require(receipt.get("run_id") == PRIOR_RUN and receipt.get("run_attempt") == "1"
            and receipt.get("control_source_sha") == PRIOR_SOURCE
            and receipt.get("status") == PROBE_FAIL
            and receipt.get("protocol") == "sdk06-original-products-enumeration-only-v1"
            and receipt.get("original_run_id") == ORIGINAL_RUN
            and receipt.get("original_run_attempt") == ORIGINAL_ATTEMPT
            and receipt.get("original_source_sha") == ORIGINAL_SOURCE
            and receipt.get("original_artifact_id") == ARTIFACT_ID
            and receipt.get("original_artifact_sha256") == OUTER_SHA
            and receipt.get("original_products_sha256") == PRODUCTS_SHA,
            "Original failed observation lineage differs")
    require(receipt.get("actual_product_tests_executed") == 0 and receipt.get("app_builds") == 0
            and all(receipt.get(key) is False for key in
                    ("full_matrix_accepted", "sdk06_accepted", "release_accepted"))
            and receipt.get("control_sources_unchanged") is True
            and receipt.get("original_products_unchanged") is True
            and receipt.get("owned_simulator_cleanup") == {
                "shutdown": {"status": "PASS", "return_code": 0},
                "delete": {"status": "PASS", "return_code": 0}},
            "The original nonexecution/integrity/cleanup scope differs")
    require(selection == receipt.get("selection_contract")
            and set(selection) == {"test_plan", "selected", "excluded", "declarations"}
            and selection["test_plan"] == "AnytypeTests",
            "Current restored Products selection differs from the original frozen contract")
    selected, excluded, declarations = (set(selection[key]) for key in
                                        ("selected", "excluded", "declarations"))
    require(len(selected) == len(selection["selected"]) == 23
            and len(excluded) == len(selection["excluded"]) == 7
            and len(declarations) == len(selection["declarations"]) == 30
            and not selected.intersection(excluded) and selected | excluded == declarations,
            "Exact23/seven exclusions/thirty declarations must remain intact")
    suites = ["AnytypeTests/" + name for name in probe.component.SUITES]
    require(prior is not None and prior.get("status") == "NOT_QUALIFIED"
            and prior.get("actual_product_tests_executed") == 0
            and prior.get("command_return_code") == 0
            and prior.get("binding", {}).get("original_sha256") == XCTESTRUN_SHA
            and prior["binding"].get("copied_sha256") ==
                hashlib.sha256(originals["suites-minus-seven-cli.xctestrun"]).hexdigest()
            and prior["binding"].get("only") == [name.removeprefix("AnytypeTests/") for name in suites]
            and prior["binding"].get("skip") ==
                [name.removeprefix("AnytypeTests/") for name in selection["excluded"]],
            "The original failed suite-minus-seven descriptor binding differs")
    command = json.loads(originals["enumerate-suites-minus-seven-cli.command.json"])
    argv = command.get("argv", [])
    require(command.get("status") == "COMPLETE" and command.get("return_code") == 0
            and command.get("timeout_seconds") == ENUMERATION_TIMEOUT_SECONDS
            and argv[:2] == ["xcodebuild", "test-without-building"]
            and argv.count("-enumerate-tests") == 1 and "build-for-testing" not in argv
            and [item.removeprefix("-only-testing:") for item in argv
                 if item.startswith("-only-testing:")] == suites
            and [item.removeprefix("-skip-testing:") for item in argv
                 if item.startswith("-skip-testing:")] == selection["excluded"],
            "The original enumeration-only command or filters differ")
    payload = json.loads(originals["suites-minus-seven-cli.enumeration.json"])
    test_plan, enabled, disabled = probe.component.enumerated_identifiers(payload)
    require(test_plan == "AnytypeTests" and len(enabled) == 26 and len(disabled) == 913
            and len(enabled | disabled) == 939 and selected <= enabled,
            "Actual original26/939 inventory differs; no new selector admission is inferred")
    extra = enabled - selected
    parameterized = {name for name in excluded if not name.endswith("()")}
    require(len(extra) == 3 and extra == parameterized and excluded - extra <= disabled,
            "Only the three original parameterized exclusions may change spelling")
    replacements = plan["replacements"]
    require(isinstance(replacements, dict) and set(replacements) == extra
            and replacements == {name: name.split("(", 1)[0] for name in extra},
            "Exactly three full target/suite/function basenames are required")
    for signature, basename in replacements.items():
        require({name for name in enabled | disabled if name.startswith(basename)} == {signature}
                and not any(name.startswith(basename) for name in selected),
                "A basename is ambiguous or also selects a requested method")
    skip = [replacements.get(name, name) for name in selection["excluded"]]
    require(len(skip) == len(set(skip)) == 7, "Exactly seven distinct exclusions remain required")
    return dict(name=VARIANT_NAME, include=suites, exclude=skip, cli=suites, cli_skip=skip)


def fixed_candidates(selection):
    # No CLI plan argument, global mutation, or arbitrary candidate provider.
    # A fixed plan is evidence for a single experiment, never a qualified result.
    plan, originals = _fixed_inputs()
    return [_reviewed_variant(selection, plan, originals)]


def control_sources(control, head):
    hashes = probe.control_sources(control, head)
    for relative in EXTRA_INTEGRITY_PATHS:
        path = control / relative
        require(path.is_file() and not path.is_symlink(), "Missing fixed basename probe input")
        expected = subprocess.check_output(["git", "-C", str(control), "show", head + ":" + relative],
                                            timeout=30)
        observed = sha(path)
        require(hashlib.sha256(expected).hexdigest() == observed,
                "A fixed basename probe input differs from the exact clean checkout")
        hashes[relative] = observed
    require(hashes["Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py"] == BASE_PROBE_SHA,
            "Original shared probe/normalizer changed")
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
        candidates = fixed_candidates(selection)
        require(len(candidates) == 1, "Exactly one reviewed basename hypothesis is allowed")
        deadline = time.monotonic() + ENUMERATION_TOTAL_SECONDS
        receipt["enumeration_limits"] = dict(per_command_seconds=ENUMERATION_TIMEOUT_SECONDS,
                                             all_variants_seconds=ENUMERATION_TOTAL_SECONDS,
                                             maximum_variants=len(candidates), includes_test_host_startup=True)
        for variant in candidates:
            name = variant["name"]
            configuration = original.with_name("SDK06-" + nonce + "-" + name + ".xctestrun")
            binding = copied_configuration(original, configuration, variant, runtime=pair["runtime"])
            shutil.copyfile(configuration, args.evidence / (name + ".xctestrun"))
            output = args.evidence / (name + ".enumeration.json")
            record = dict(name=name, status="NOT_QUALIFIED", binding=binding, actual_product_tests_executed=0)
            receipt["probes"].append(record)
            command = enumeration_command(configuration, udid, output, args.evidence / (name + ".xcresult"), variant)
            _, outcome = runner.run(command, "enumerate-" + name,
                                    enumeration_budget(deadline, time.monotonic()), check=False)
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
    receipt["selector_hypothesis"] = dict(name=VARIANT_NAME, prior_run_id=PRIOR_RUN,
                                        plan_sha256=sha(args.control / PLAN),
                                        status_at_dispatch="UNQUALIFIED_ENUMERATION_HYPOTHESIS")
    result = execute(args, receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "run_id", "run_attempt", "actual_product_tests_executed", "app_builds")}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
