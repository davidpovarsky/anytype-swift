"""Fresh construction for the explicit coherent original-Products continuation.

This proves controller-owned creation and ordering, never filesystem/container
absence. All command output references use .log, which the existing packager
retains. The qualified command wrapper retains combined stdout and stderr.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import time

import coherent_original_preflight as lifecycle
import wave15_batch as batch

PROTOCOL = "pinkha-coherent-owned-construction-v1"
APP_SOURCE = "d254a4a1ccd9288f585ff9374088cbaf965b36b4"
LANES = {"editor", "quote-drop", "properties-set"}
MAXIMUM = 2 * 1024**2


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(path, root, maximum=MAXIMUM):
    path, root = Path(path), Path(root).resolve()
    require(path.is_absolute() and path.resolve() == path and path.is_relative_to(root)
            and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= maximum, "Missing, escaped or unbounded construction original")
    return path.read_bytes()


def read(path, root):
    regular(path, root)
    return lifecycle.read(path)


def digest(path, root, maximum=MAXIMUM):
    return hashlib.sha256(regular(path, root, maximum)).hexdigest()


def original(path, value):
    require(not path.exists() and not path.is_symlink(), "Refuse an existing construction journal entry")
    lifecycle.save(path, value, original=True)


def identity(origin, intent, planned):
    require(intent.get("protocol") == "pinkha-coherent-original-products-continuation-v1"
            and intent.get("profile") == batch.COHERENT_HEART_PROFILE
            and intent.get("source_sha") == APP_SOURCE
            and intent.get("control_source_sha") == origin.control_sha
            and intent.get("run_id") == os.environ.get("GITHUB_RUN_ID")
            and intent.get("run_attempt") == os.environ.get("GITHUB_RUN_ATTEMPT")
            and origin.control_sha == os.environ.get("GITHUB_SHA"),
            "Construction must belong to this current two-origin run")
    require(re.fullmatch(r"[0-9a-f]{32}", intent.get("token", ""))
            and planned in intent.get("lane_devices", []) and planned.get("lane") in LANES
            and "udid" not in planned
            and planned.get("name") == "Pinkha-UI27-" + intent["run_id"] + "-batch-"
                + intent["token"] + "-" + planned["lane"],
            "Construction requires this exact planned nonce lane")
    return dict(protocol=PROTOCOL, control_source_sha=origin.control_sha, app_source_sha=APP_SOURCE,
                run_id=intent["run_id"], run_attempt=intent["run_attempt"], nonce=intent["token"],
                lane=planned["lane"], name=planned["name"],
                runtime_id=planned["runtime"]["identifier"], device_type=planned["device"]["identifier"])


def baseline(origin, intent, planned):
    path = origin.evidence / "batch-simulator-baseline.json"
    require(digest(path, origin.evidence) == intent.get("baseline_inventory_sha256"),
            "Original complete precreation inventory changed")
    value = read(path, origin.evidence)
    require(isinstance(value, dict) and isinstance(value.get("devices"), dict),
            "Complete precreation inventory is missing")
    ids, names = [], []
    for runtime, rows in value["devices"].items():
        require(isinstance(runtime, str) and runtime and isinstance(rows, list),
                "Invalid original inventory runtime")
        for row in rows:
            require(isinstance(row, dict) and batch.valid_udid(row.get("udid"))
                    and isinstance(row.get("name"), str), "Invalid original inventory device")
            ids.append(row["udid"].lower())
            names.append(row["name"])
    require(len(ids) <= 4096 and len(ids) == len(set(ids))
            and isinstance(intent.get("baseline_udids"), list)
            and all(batch.valid_udid(item) for item in intent["baseline_udids"])
            and sorted(ids) == sorted(item.lower() for item in intent["baseline_udids"])
            and planned["name"] not in names,
            "Complete baseline identity set or planned-name exclusion differs")
    return set(ids)


def command_runner(origin, directory):
    # This existing wrapper persists observed UUIDs before its group check.
    journal = directory / "command-journal.json"
    receipt = read(journal, origin.evidence) if journal.exists() else {}
    if receipt:
        require(isinstance(receipt.get("commands"), list)
                and [row.get("name") for row in receipt["commands"]] == ["create"]
                and receipt["commands"][0] == read(directory / "create.observation.json", origin.evidence),
                "Owned command journal was reset or contains an earlier operation")
    return lifecycle.Commands(origin.control, directory, receipt,
        lambda: lifecycle.save(journal, receipt))


def create(origin, intent, planned, directory):
    directory = directory.resolve()
    require(directory == origin.evidence / "lanes" / planned["lane"]
            and not directory.is_symlink(), "Construction directory is not the owned lane")
    bound = identity(origin, intent, planned)
    excluded = baseline(origin, intent, planned)
    intent_path = origin.evidence / "batch-intent.json"
    require(read(intent_path, origin.evidence) == intent, "Original batch intent differs")
    proof = directory / "construction"
    proof.mkdir(exist_ok=False)
    argv = ["xcrun", "simctl", "create", bound["name"], bound["device_type"], bound["runtime_id"]]
    original(proof / "intent.json", dict(**bound, argv=argv,
        batch_intent_sha256=digest(intent_path, origin.evidence),
        baseline_inventory_sha256=intent["baseline_inventory_sha256"],
        install_attempts=0, container_absence_proved=False))
    captured = {}

    def returned(path, record):
        # A real returned identity remains owned even if exit/group validation
        # fails later. It cannot qualify freshness unless the command passed.
        raw = regular(path, origin.evidence, 128)
        try:
            udid = raw.decode("ascii").strip()
        except UnicodeError:
            return
        if not batch.valid_udid(udid):
            return
        require(record.get("argv") == argv and udid.lower() not in excluded
                and udid.lower() not in origin._constructions,
                "Create returned a baseline, reused or incorrectly bound UUID")
        device = dict(planned, udid=udid)
        original(directory / "owned-simulator.json", device)
        original(proof / "created-proof.json", dict(**bound, udid=udid, argv=argv,
            original_command_sha256=digest(path.with_suffix(".command.json"), origin.evidence),
            output=dict(path="construction/create.log", bytes=len(raw),
                        sha256=hashlib.sha256(raw).hexdigest(), format="STDOUT_STDERR_COMBINED")))
        origin._constructions[udid.lower()] = dict(directory=directory, device=device,
            fresh_sha256=None, attempt_sha256=None, first_selection_consumed=False,
            native_preparation_passed=False)
        captured["device"] = device

    command_runner(origin, proof).run(argv, "create", 30, observe=returned)
    require("device" in captured, "Successful create did not return one owned UUID")
    verify_creation(origin, intent, captured["device"], directory)
    return captured["device"]


def verify_creation(origin, intent, device, directory):
    planned = {key: value for key, value in device.items() if key != "udid"}
    bound = identity(origin, intent, planned)
    excluded = baseline(origin, intent, planned)
    require(batch.valid_udid(device.get("udid")) and device["udid"].lower() not in excluded,
            "Construction UUID is missing or baseline")
    require(directory == origin.evidence / "lanes" / device["lane"], "Foreign construction directory")
    proof = directory / "construction"
    intention = read(proof / "intent.json", origin.evidence)
    returned = read(proof / "created-proof.json", origin.evidence)
    argv = ["xcrun", "simctl", "create", bound["name"], bound["device_type"], bound["runtime_id"]]
    require(all(intention.get(k) == v and returned.get(k) == v for k, v in bound.items())
            and intention.get("batch_intent_sha256") == digest(origin.evidence / "batch-intent.json", origin.evidence)
            and intention.get("baseline_inventory_sha256") == intent["baseline_inventory_sha256"]
            and intention.get("argv") == returned.get("argv") == argv
            and intention.get("install_attempts") == 0 and intention.get("container_absence_proved") is False
            and returned.get("udid") == device["udid"]
            and read(directory / "owned-simulator.json", origin.evidence) == device,
            "Original construction binding differs")
    command = read(proof / "create.command.json", origin.evidence)
    observed = read(proof / "create.observation.json", origin.evidence)
    raw = regular(proof / "create.log", origin.evidence, 128)
    require(returned.get("original_command_sha256") == digest(proof / "create.command.json", origin.evidence)
            and command.get("argv") == observed.get("argv") == argv
            and command.get("status") == observed.get("status") == "COMPLETE"
            and type(command.get("return_code")) is int and command["return_code"] == observed.get("return_code") == 0
            and command.get("timeout_seconds") == 30
            and observed.get("owned_group_quiescence", {}).get("status") == "PASS"
            and returned.get("output") == dict(path="construction/create.log", bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(), format="STDOUT_STDERR_COMBINED")
            and raw.decode("ascii").strip() == device["udid"], "Original successful create evidence differs")
    return bound


def confirm(origin, device, directory):
    intent = read(origin.evidence / "batch-intent.json", origin.evidence)
    bound = verify_creation(origin, intent, device, directory)
    state = origin._constructions.get(device["udid"].lower())
    commands = read(directory / "construction/command-journal.json", origin.evidence)
    require(commands.get("commands") == [
                read(directory / "construction/create.observation.json", origin.evidence)],
            "Construction has an earlier owned operation")
    require(state and state["device"] == device and state["directory"] == directory
            and not state["first_selection_consumed"] and state["fresh_sha256"] is None
            and not (directory / "construction/first-selection-attempt.json").exists(),
            "Construction cannot be reset or admitted after a selection attempt")
    ready = batch.validate_coherent_readiness(directory, device)
    require(ready["before"]["udid"] == device["udid"], "Readiness belongs to another UUID")
    receipt = dict(**bound, status="OWNED_CONSTRUCTION_VERIFIED_BEFORE_FIRST_NATIVE_SELECTION",
        simulator_udid=device["udid"], container_absence_proved=False,
        lookup="NOT_PERFORMED_CONSTRUCTION_CONTRACT",
        created_proof_sha256=digest(directory / "construction/created-proof.json", origin.evidence),
        readiness_receipt_sha256=digest(directory / "owned-readiness/readiness.json", origin.evidence),
        selection_plan_sha256=digest(directory / "selection-plan.json", origin.evidence),
        prior_owned_install_or_selection_attempts=0)
    original(directory / "fresh-container.json", receipt)
    state["fresh_sha256"] = digest(directory / "fresh-container.json", origin.evidence)
    return receipt


def selection_attempt(origin, context, configuration, blueprint, udid, selections, evidence, prefix):
    state = origin._constructions.get(udid.lower())
    require(state and state["device"] == context.device and context.profile == batch.COHERENT_HEART_PROFILE,
            "Selection lacks its live owned construction")
    directory = state["directory"]
    verify_creation(origin, read(origin.evidence / "batch-intent.json", origin.evidence),
                    state["device"], directory)
    batch.validate_coherent_readiness(directory, state["device"])
    fresh = read(directory / "fresh-container.json", origin.evidence)
    require(digest(directory / "fresh-container.json", origin.evidence) == state["fresh_sha256"],
            "Live construction receipt changed")
    if state["first_selection_consumed"]:
        require(prefix != "prepare" and state["native_preparation_passed"]
                and digest(directory / "construction/first-selection-attempt.json", origin.evidence) == state["attempt_sha256"],
                "First native selection cannot be reset or repeated")
        return False
    plan = read(directory / "selection-plan.json", origin.evidence)
    require(blueprint == "AnytypeTests" and selections == [plan.get("preparation")]
            and isinstance(plan.get("preparation"), str) and plan["preparation"]
            and prefix == "prepare" and evidence == directory / "preparation"
            and configuration == context.native_configuration
            and digest(directory / "selection-plan.json", origin.evidence) == fresh["selection_plan_sha256"],
            "First selection is not the exact original native preparation")
    state["first_selection_consumed"] = True
    record = dict(protocol=PROTOCOL, status="FIRST_NATIVE_SELECTION_ATTEMPT",
        control_source_sha=origin.control_sha, app_source_sha=APP_SOURCE,
        run_id=os.environ["GITHUB_RUN_ID"], run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
        simulator_udid=udid, blueprint=blueprint, methods=selections, prefix=prefix,
        configuration=str(configuration), configuration_sha256=digest(configuration, origin.app),
        fresh_receipt_sha256=state["fresh_sha256"], selection_plan_sha256=fresh["selection_plan_sha256"],
        installation_success_proved=False, product_pass_proved=False)
    original(directory / "construction/first-selection-attempt.json", record)
    state["attempt_sha256"] = digest(directory / "construction/first-selection-attempt.json", origin.evidence)
    return True


def preparation_returned(origin, udid, first, result):
    if first:
        state = origin._constructions[udid.lower()]
        require(state["first_selection_consumed"], "No first native attempt")
        state["native_preparation_passed"] = result.get("status") == "PASS"


def prepared_container(origin, context, udid, directory, preparation):
    state = origin._constructions.get(udid.lower())
    require(state and state["device"] == context.device and state["directory"] == directory
            and state["native_preparation_passed"] and preparation.get("status") == "PASS"
            and digest(directory / "construction/first-selection-attempt.json", origin.evidence) == state["attempt_sha256"],
            "Actual native preparation must pass before container observation")
    remaining = origin.args.deadline - time.monotonic()
    require(remaining > 0, "Owned worker deadline already expired")
    argv = ["xcrun", "simctl", "get_app_container", udid, batch.BUNDLE, "data"]
    path = command_runner(origin, directory / "construction").run(
        argv, "post-preparation-container", min(30, remaining))
    raw = regular(path, origin.evidence, 8192)
    text = raw.decode("utf-8").strip()
    require(text and "\n" not in text and "\r" not in text and Path(text).is_absolute(),
            "Actual container command did not return one absolute path")
    container = Path(text).resolve(strict=True)
    require(container.is_dir() and udid.lower() in {part.lower() for part in container.parts},
            "Actual prepared container belongs to another simulator")
    original(directory / "construction/post-preparation-container.json",
        dict(protocol=PROTOCOL, status="ACTUAL_CONTAINER_OBSERVED_AFTER_NATIVE_PREPARATION",
             simulator_udid=udid, container=str(container), native_preparation_status="PASS",
             first_selection_attempt_sha256=state["attempt_sha256"],
             command_sha256=digest(path.with_suffix(".command.json"), origin.evidence),
             output=dict(path="construction/post-preparation-container.log", bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(), format="STDOUT_STDERR_COMBINED")))
    return container


def validate_saved(origin, fresh, directory, device, intent):
    bound = verify_creation(origin, intent, device, directory)
    require(all(fresh.get(k) == v for k, v in bound.items())
            and fresh.get("status") == "OWNED_CONSTRUCTION_VERIFIED_BEFORE_FIRST_NATIVE_SELECTION"
            and fresh.get("simulator_udid") == device["udid"] and fresh.get("container_absence_proved") is False
            and fresh.get("lookup") == "NOT_PERFORMED_CONSTRUCTION_CONTRACT"
            and fresh.get("prior_owned_install_or_selection_attempts") == 0
            and fresh.get("created_proof_sha256") == digest(directory / "construction/created-proof.json", origin.evidence)
            and fresh.get("selection_plan_sha256") == digest(directory / "selection-plan.json", origin.evidence),
            "Saved construction contract differs")
    attempt = read(directory / "construction/first-selection-attempt.json", origin.evidence)
    plan = read(directory / "selection-plan.json", origin.evidence)
    require(attempt.get("protocol") == PROTOCOL and attempt.get("status") == "FIRST_NATIVE_SELECTION_ATTEMPT"
            and attempt.get("control_source_sha") == bound["control_source_sha"]
            and attempt.get("app_source_sha") == bound["app_source_sha"]
            and attempt.get("run_id") == bound["run_id"] and attempt.get("run_attempt") == bound["run_attempt"]
            and attempt.get("simulator_udid") == device["udid"]
            and attempt.get("blueprint") == "AnytypeTests" and attempt.get("prefix") == "prepare"
            and attempt.get("methods") == [plan["preparation"]]
            and attempt.get("configuration") == str(origin.context.native_configuration)
            and attempt.get("configuration_sha256") == digest(origin.context.native_configuration, origin.app)
            and attempt.get("fresh_receipt_sha256") == digest(directory / "fresh-container.json", origin.evidence)
            and attempt.get("selection_plan_sha256") == fresh["selection_plan_sha256"]
            and attempt.get("installation_success_proved") is False and attempt.get("product_pass_proved") is False,
            "Saved first native attempt differs")
    post = read(directory / "construction/post-preparation-container.json", origin.evidence)
    require(post.get("protocol") == PROTOCOL
            and post.get("status") == "ACTUAL_CONTAINER_OBSERVED_AFTER_NATIVE_PREPARATION"
            and post.get("simulator_udid") == device["udid"] and post.get("native_preparation_status") == "PASS"
            and post.get("first_selection_attempt_sha256") == digest(directory / "construction/first-selection-attempt.json", origin.evidence),
            "Passing lane lacks its actual post-preparation container")
    raw = regular(directory / "construction/post-preparation-container.log", origin.evidence, 8192)
    command = read(directory / "construction/post-preparation-container.command.json", origin.evidence)
    observation = read(directory / "construction/post-preparation-container.observation.json", origin.evidence)
    require(observation.get("owned_group_quiescence", {}).get("status") == "PASS"
            and observation.get("return_code") == 0 and observation.get("argv") == command.get("argv")
            and isinstance(command.get("timeout_seconds"), (float, int))
            and 0 < command["timeout_seconds"] <= 30, "Container observation did not finish within its owned cap")
    require(post.get("command_sha256") == digest(directory / "construction/post-preparation-container.command.json", origin.evidence)
            and command.get("argv") == ["xcrun", "simctl", "get_app_container", device["udid"], batch.BUNDLE, "data"]
            and command.get("return_code") == 0 and command.get("status") == "COMPLETE"
            and post.get("output") == dict(path="construction/post-preparation-container.log", bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(), format="STDOUT_STDERR_COMBINED")
            and str(Path(raw.decode("utf-8").strip()).resolve()) == post.get("container"),
            "Actual post-preparation container original changed")
    fixture = read(directory / "fixture-isolation.json", origin.evidence)
    require(fixture.get("container") == post["container"], "Observed native fixture uses another container")
