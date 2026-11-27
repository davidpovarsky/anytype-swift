"""Read-only hosted G02 phase adapter under the shared closed product gate.

No build, account bootstrap, mutation contract or replacement native model is
introduced. The actual compiled Swift reader owns the semantic comparison;
this module binds its selected XCTest, raw input/output receipts and lifecycle.
"""
from __future__ import annotations

from pathlib import Path
import plistlib
import re

import g02_ui_receipts as ui
import g02_word_consumer as lane

TARGET = "AnytypeTests"
METHOD = "TorahWritingPropertiesReadbackTests/observeOriginalWritingProperties"
ALLOWANCE = 300  # Preserve the original Consumer.stage native-method default.
SOURCE_PATH = lane.NATIVE_SOURCE_PATH
SOURCE_SHA = lane.NATIVE_SOURCE_SHA
ORIGINAL_BYTES = lane.NATIVE_ORIGINAL_BYTES
ORIGINAL_SHA = lane.NATIVE_ORIGINAL_SHA
SUFFIX_SHA = "0f8623ee17de978b5c9994e0df63880755c879434f19ba90b07b1c238564b62a"
WITNESS_SHA = "aaa408805488d0d15646569359d698527f58bfa597ad82177ab6c06a6986e4dd"
RTL_SHA = "80ebc56005110ee78615322f56b876b5b6fd4fae23975b86d249ae05ebcac8ea"
DISABLED_FLAGS = (
    "PINKHA_NATIVE_DERIVED_ACCEPTANCE", "PINKHA_PREPARE_TYPE_PRESERVATION",
    "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION", "PINKHA_SIMULATOR_UI_DISPOSABLE",
    "PINKHA_HANLIN_NATIVE_PREPARATION", "PINKHA_PREPARE_HANLIN_SELECTION_UI",
    "PINKHA_PROPERTIES_PREPARE", "PINKHA_T5_UI_PREPARATION", "PINKHA_T5_APPLE_PAIR",
)
CLOCK_KEYS = ["lastModifiedDate", "lastOpenedDate", "lastUsedDate"]
SCOPE = "THREE_WRITING_OBJECTS_PROPERTIES_NOT_WHOLE_STORE_BYTES"
MAXIMUM = 4 * 1024**2


def qualify_native_source(c, raw):
    c.require(c.sha(raw) == SOURCE_SHA and c.sha(raw[:ORIGINAL_BYTES]) == ORIGINAL_SHA
              and c.sha(raw[ORIGINAL_BYTES:]) == SUFFIX_SHA
              and raw.count(b"struct TorahWritingPropertiesReadbackTests {") == 1
              and raw.count(b"func observeOriginalWritingProperties() async throws {") == 1,
              "Exact published native reader and unchanged original preparation required")
    return {"sourcePath": SOURCE_PATH, "sourceSHA256": SOURCE_SHA, "originalPreparationSHA256": ORIGINAL_SHA,
            "suffixSHA256": SUFFIX_SHA, "method": TARGET + "/" + METHOD, "methods": 1, "casesPerInvocation": 1,
            "AppleCompilationProvenByThisSourceCheck": False}


def source_contract(consumer):
    import native_compiler_witness as witness
    c = consumer.shared_module
    declared = qualify_native_source(c, c.raw(consumer.source / SOURCE_PATH))
    witness_path = Path(witness.__file__).resolve()
    rtl_path = witness_path.parent / "rtl_hosted_profile.py"
    c.require(c.sha(c.raw(witness_path)) == WITNESS_SHA and c.sha(c.raw(rtl_path)) == RTL_SHA,
              "Original native compiler witness and reviewed RTL dependency changed")
    compiled = consumer.source_admission.get("sameInvocationAppAndUI", {})
    c.require(consumer.source_admission.get("commit") == consumer.binding["sourceSHA"]
              and compiled.get("sourceCommit") == consumer.binding["sourceSHA"]
              and compiled.get("completeCompilerGate") is True,
              "Shared common source/App/UI admission must precede the native phase")
    producer = c.decode(ui.pinned(c, consumer.admission["producerReceipt"], 8 * 1024**2))
    pin = producer.get("nativeCompilationProof")
    c.require(pin == compiled.get("nativeCompilationProof"), "Native proof must be the actual admitted producer ref")
    proof = witness.verify_native_compiler_sources(consumer.source, source_commit=consumer.binding["sourceSHA"],
               native_compilation_proof=pin, expected_sources={SOURCE_PATH: SOURCE_SHA}, rtl_profile_path=rtl_path)
    return {"declaration": declared, "compiledSource": proof, "nativeCompilationProof": pin,
            "sourceCommit": consumer.binding["sourceSHA"], "witnessSHA256": WITNESS_SHA,
            "testsExecutedByThisCheck": 0}


def phase_environment(c, phase, startup, fixture_raw, udid, seed_raw, *, baseline_raw=None, unlink_raw=None):
    c.require(phase in ("baseline", "postflight"), "One explicit native G02 phase required")
    fixture, controller = ui.fixture_binding(c, fixture_raw, startup, udid)
    c.require("SIMULATOR_UDID" not in startup
              and not any(key.startswith("PINKHA_G02_") for key in startup),
              "Native phase must receive the original startup environment, not a prior phase override")
    seed = c.decode(seed_raw)
    c.require(seed.get("schema") == "pinkha-g02-word-ui-observation-v1" and seed.get("phase") == "seed-complete"
              and seed.get("spaceID") == fixture["spaceId"] and seed.get("controller") == controller
              and seed.get("nativeIdentifiersEstablishedByThisUIStage") is False
              and set(seed.get("documents", {})) == set(ui.ROLES), "Actual original seed-complete handoff required")
    for role in ui.ROLES:
        row = seed["documents"][role]
        c.require(row.get("objectID") == fixture["documents"][role] and row.get("typeID") == fixture["types"][role]
                  and row.get("name") == fixture["names"][fixture["documents"][role]]
                  and row.get("sourceLabel") == fixture["sourceLabel"] and row.get("topicLabel") == fixture["topicLabel"]
                  and ui._string(row.get("wordLabel")) and row.get("tagPropertyName") in {"Tag", "Tags"}
                  and row.get("tagName") == "G02 " + role + " " + controller["TOKEN"][:8],
                  "Seed UI belongs to another real writing identity or observed value")
    result = dict(startup)
    result.update({key: "0" for key in DISABLED_FLAGS})
    result.update(PINKHA_TYPE_PRESERVATION_POSTFLIGHT="0", PINKHA_G02_NATIVE_READBACK="1", PINKHA_G02_NATIVE_PHASE=phase,
                  PINKHA_G02_SEED_UI_JSON=seed_raw.decode("utf-8"), PINKHA_G02_SEED_UI_SHA256=c.sha(seed_raw))
    if phase == "baseline":
        c.require(baseline_raw is None and unlink_raw is None, "Baseline cannot consume a previous readback or unlink receipt")
    else:
        c.require(isinstance(baseline_raw, bytes) and isinstance(unlink_raw, bytes), "Postflight requires actual full baseline and unlink bytes")
        baseline, unlink = c.decode(baseline_raw), c.decode(unlink_raw)
        validate_receipt(c, baseline, "baseline", "PASS_BASELINE_READ_ONLY", fixture, controller, c.sha(seed_raw))
        c.require(unlink.get("schema") == "pinkha-g02-word-ui-observation-v1" and unlink.get("phase") == "unlink-complete"
                  and unlink.get("controller") == controller and unlink.get("spaceID") == fixture["spaceId"]
                  and unlink.get("nativeBaselineSHA256") == c.sha(baseline_raw)
                  and unlink.get("seedUIReceiptSHA256") == c.sha(seed_raw)
                  and unlink.get("nativePersistencePostflightRequired") is True
                  and set(unlink.get("documents", {})) == set(ui.ROLES), "Unlink UI must bind this exact actual baseline and seed")
        result.update(PINKHA_G02_BASELINE_SHA256=c.sha(baseline_raw), PINKHA_G02_UNLINK_UI_JSON=unlink_raw.decode("utf-8"),
                      PINKHA_G02_UNLINK_UI_SHA256=c.sha(unlink_raw))
    c.require(all(result[key] == startup[key] for key in startup), "Native phase changed original startup provenance")
    return result, fixture, controller


def validate_receipt(c, value, phase, status, fixture, controller, seed_sha, *, baseline_sha=None, unlink_sha=None):
    required = {"schema", "status", "phase", "controller", "fixtureSHA256", "seedUIReceiptSHA256", "processID",
                "directories", "verifierCallsMutationAPI", "scope", "permittedClockKeys", "state"}
    c.require(isinstance(value, dict) and required <= value.keys()
              and set(value) <= required | {"nativeBaselineSHA256", "unlinkUIReceiptSHA256"}
              and value["schema"] == "pinkha-g02-word-native-readback-v1" and value["status"] == status and value["phase"] == phase
              and value["controller"] == controller and value["fixtureSHA256"] == controller["FIXTURE_SHA256"]
              and value["seedUIReceiptSHA256"] == seed_sha and value.get("nativeBaselineSHA256") == baseline_sha
              and value.get("unlinkUIReceiptSHA256") == unlink_sha
              and ui._pid(value["processID"]) and value["verifierCallsMutationAPI"] is False
              and value["scope"] == SCOPE and value["permittedClockKeys"] == CLOCK_KEYS,
              "Native receipt phase, controller, raw input hashes, process or scope differs")
    state = value["state"]
    c.require(isinstance(state, dict) and ui._string(state.get("accountID"))
              and state.get("spaceID") == fixture["spaceId"]
              and ui._string(state.get("canonicalPropertyKey")) and ui._string(state.get("canonicalPropertyID"))
              and set(state.get("documents", {})) == set(ui.ROLES)
              and set(value["directories"]) == {"container", "middleware"}, "Native receipt lacks the actual original account/Space/three-document state")
    for role in ui.ROLES:
        doc = state["documents"][role]
        native = doc.get("native", {})
        c.require(native.get("objectID") == fixture["documents"][role] and native.get("spaceID") == fixture["spaceId"]
                  and native.get("typeID") == fixture["types"][role] and native.get("name") == fixture["names"][fixture["documents"][role]]
                  and isinstance(native.get("fields"), dict) and ui._string(native.get("protobufDetailsJSON"), MAXIMUM)
                  and native.get("protobufDetailsSHA256") == c.sha(native["protobufDetailsJSON"].encode())
                  and ui._string(doc.get("canonicalRaw"), 1024**2)
                  and doc.get("canonicalSHA256") == c.sha(doc["canonicalRaw"].encode())
                  and isinstance(doc.get("projections"), dict) and ui._string(doc.get("tag", {}).get("objectID")),
                  "Actual native writing object/raw detail/canonical/Tag evidence differs")
    return value


def native_invocation(consumer, stage, udid, environment):
    c = consumer.shared_module
    result_raw, invocation_raw = c.raw(stage / "result.json"), c.raw(stage / "invocation.json")
    result, invocation = c.decode(result_raw), c.decode(invocation_raw)
    argv = invocation.get("argv", [])
    c.require(result.get("status") == "PASS" and result.get("testInvoked") is True
              and result.get("selected") == [METHOD] and result.get("command_exit_code") == 0
              and (result.get("passed"), result.get("failed"), result.get("skipped")) == (1, 0, 0)
              and invocation.get("binding") == consumer.binding
              and [v for v in argv if v.startswith("-only-testing:")] == ["-only-testing:" + TARGET + "/" + METHOD + "()"]
              and argv.count("platform=iOS Simulator,id=" + udid) == 1
              and result.get("command", {}).get("argv") == argv
              and result["command"].get("status") == "PASS_COMMAND" and result["command"].get("exitCode") == 0,
              "Actual single native G02 XCTest invocation/result required")
    for flag in ("-default-test-execution-time-allowance", "-maximum-test-execution-time-allowance"):
        c.require(argv.count(flag) == 1 and argv[argv.index(flag) + 1] == str(ALLOWANCE), "Original native stage allowance differs")
    descriptor = c.raw(stage / "bound.xctestrun")
    c.require(invocation.get("descriptorSHA256") == c.sha(descriptor)
              and invocation.get("enumerationSHA256") == c.sha(c.raw(stage / "enumeration.json")), "Native descriptor/enumeration bytes changed")
    targets = plistlib.loads(descriptor)["TestConfigurations"][0]["TestTargets"]
    c.require(len(targets) == 1 and targets[0].get("OnlyTestIdentifiers") == [METHOD + "()"]
              and all(targets[0].get("EnvironmentVariables", {}).get(key) == value for key, value in environment.items()),
              "Actual native descriptor changed the phase or original disabled preparation flags")
    command = consumer.commands.root / (stage.parent.name + "-" + stage.name + "-test")
    c.require(c.decode(c.raw(command / "result.json")) == result["command"]
              and b"** TEST EXECUTE SUCCEEDED **" in c.raw(command / "original.log"), "Original native success command bytes missing")
    devices = result.get("actual_devices", [])
    c.require(len(devices) == 1 and str(devices[0].get("deviceId", "")).lower() == udid.lower()
              and devices[0].get("platform") == "iOS Simulator", "Native result belongs to another actual simulator")
    return {"actualTest": {"path": str(stage / "result.json"), "sha256": c.sha(result_raw)},
            "invocation": {"path": str(stage / "invocation.json"), "sha256": c.sha(invocation_raw)}}


def retain_outputs(consumer, stage, udid, phase, filenames, result, first):
    c = consumer.shared_module
    # Preserve every actual emitted receipt, including the pre-comparison
    # observation on a failed test. Never replace the first XCTest failure.
    for key, name in filenames.items():
        try:
            current = consumer.container(udid, "data", "g02-" + phase + "-retain-" + key)
            path = current / lane.SUPPORT / name
            if not path.exists():
                c.require(first is not None, "Successful native G02 phase omitted " + key)
                continue
            value, _ = consumer.read_private(udid, lane.SUPPORT / name, stage / "private", "g02-" + phase + "-" + key,
                                             maximum=65536 if key == "uiBaseline" else MAXIMUM)
            result[key] = {"path": str(stage / "private" / name), "sha256": c.sha(value)}
        except BaseException as exc:
            result["retentionErrors"].append({"artifact": key, **c.error(exc)})
            if first is None: first = exc; result["firstFailure"] = c.error(exc)
    return first


def run_native_phase(consumer, directory, udid, phase, startup_environment, seed_ui_ref, *, baseline_ref=None, unlink_ui_ref=None):
    lane.require_runtime_ready(consumer.admission, Path(__file__).resolve().parent)
    c = consumer.shared_module
    c.require(phase in ("baseline", "postflight"), "Only the two explicitly gated native phases are supported")
    before = source_contract(consumer)
    c.require(tuple(consumer.helpers["type_preservation"].DISABLED_FLAGS) == DISABLED_FLAGS,
              "Original preparation/account-disable flags changed")
    container = consumer.container(udid, "data", "g02-" + phase + "-fixture-container")
    fixture_raw = c.raw(container / lane.SUPPORT / lane.FIXTURE, 65536)
    seed_raw = ui.pinned(c, seed_ui_ref)
    baseline_raw = ui.pinned(c, baseline_ref, MAXIMUM) if baseline_ref is not None else None
    unlink_raw = ui.pinned(c, unlink_ui_ref) if unlink_ui_ref is not None else None
    environment, fixture, controller = phase_environment(c, phase, startup_environment, fixture_raw, udid, seed_raw,
                                                        baseline_raw=baseline_raw, unlink_raw=unlink_raw)
    token = controller["TOKEN"]
    filenames = {"observed": "pinkha-g02-word-native-" + phase + "-observed-" + token + ".json"}
    if phase == "baseline":
        filenames.update(baseline="pinkha-g02-word-native-baseline-" + token + ".json",
                         uiBaseline="pinkha-g02-word-ui-baseline-" + token + ".json")
    else:
        filenames["postflight"] = "pinkha-g02-word-native-postflight-" + token + ".json"
        c.require(c.raw(container / lane.SUPPORT / ("pinkha-g02-word-native-baseline-" + token + ".json"), MAXIMUM) == baseline_raw,
                  "Retained native baseline differs from the original file in this owned App")
    for name in filenames.values():
        path = container / lane.SUPPORT / name
        c.require(not path.exists() and not path.is_symlink(), "Refuse stale native G02 output before the actual invocation")
    stage = directory / ("native-" + phase)
    c.require(not stage.exists(), "Native G02 stage evidence must be fresh")
    result = {"status": "FAIL", "phase": phase, "sourceContract": before, "seedUI": seed_ui_ref,
              "firstFailure": None, "retentionErrors": [], "actualNativeSemanticComparisonOwnedByCompiledSwift": True,
              "wholeNativeStoreBytesAccepted": False, "physicalDevice": "NOT_RUN"}
    if phase == "postflight": result.update(baseline=baseline_ref, unlinkUI=unlink_ui_ref)
    first = None
    try:
        consumer.stage(directory, "native-" + phase, udid, [METHOD + "()"], environment, target=TARGET, allowance=ALLOWANCE)
        result.update(native_invocation(consumer, stage, udid, environment))
    except BaseException as exc:
        first = exc; result["firstFailure"] = c.error(exc)
    first = retain_outputs(consumer, stage, udid, phase, filenames, result, first)
    try:
        if first is None:
            args = dict(baseline_sha=c.sha(baseline_raw) if baseline_raw is not None else None,
                        unlink_sha=c.sha(unlink_raw) if unlink_raw is not None else None)
            observed = c.decode(ui.pinned(c, result["observed"], MAXIMUM))
            validate_receipt(c, observed, phase, "OBSERVED_NATIVE_STATE_NOT_ACCEPTANCE", fixture, controller, c.sha(seed_raw), **args)
            accepted_key = "baseline" if phase == "baseline" else "postflight"
            accepted = c.decode(ui.pinned(c, result[accepted_key], MAXIMUM))
            status = "PASS_BASELINE_READ_ONLY" if phase == "baseline" else "PASS_EXACT_DOCUMENT_WORD_UNLINK_NATIVE_READBACK"
            validate_receipt(c, accepted, phase, status, fixture, controller, c.sha(seed_raw), **args)
            c.require({k: v for k, v in observed.items() if k != "status"} == {k: v for k, v in accepted.items() if k != "status"},
                      "Accepted native receipt differs from the actual retained pre-comparison observation")
            current = consumer.container(udid, "data", "g02-" + phase + "-qualified-container")
            preservation = consumer.helpers["type_preservation"]
            directories = {"container": preservation.directory_identity(current),
                           "middleware": preservation.directory_identity(current / preservation.STORE)}
            for key, identity in directories.items(): preservation.validate_directory(accepted["directories"][key], identity)
            result["controllerDirectories"] = directories
            if phase == "baseline":
                compact = c.decode(ui.pinned(c, result["uiBaseline"]))
                c.require(compact.get("schema") == "pinkha-g02-word-native-ui-baseline-v1"
                          and compact.get("nativeBaselineSHA256") == result["baseline"]["sha256"]
                          and compact.get("seedUIReceiptSHA256") == seed_ui_ref["sha256"]
                          and compact.get("controller") == controller and compact.get("spaceID") == fixture["spaceId"]
                          and set(compact.get("documents", {})) == set(ui.ROLES), "Compact native-to-UI handoff is foreign or incomplete")
                for role in ui.ROLES:
                    doc, native = compact["documents"][role], accepted["state"]["documents"][role]
                    c.require(all(doc.get(k) == native["native"].get(k) for k in ("objectID", "typeID", "name"))
                              and doc.get("tagID") == native["tag"]["objectID"]
                              and doc.get("tagName") == native["tag"]["name"]
                              and doc.get("sourceLabel") == fixture["sourceLabel"] and doc.get("topicLabel") == fixture["topicLabel"]
                              and doc.get("wordLabel") == c.decode(seed_raw)["documents"][role]["wordLabel"]
                              and all(ui._string(doc.get(k)) for k in ("wordRecordID", "wordIdentity", "tagPropertyName")),
                              "Compact handoff does not describe the same actual native/seed document")
            else:
                baseline = c.decode(baseline_raw)
                c.require(accepted["directories"] == baseline["directories"]
                          and accepted["processID"] != baseline["processID"]
                          and accepted["state"]["accountID"] == baseline["state"]["accountID"],
                          "Native postflight relocated the original account/store or reused the baseline process")
            c.require(c.raw(current / lane.SUPPORT / lane.FIXTURE, 65536) == fixture_raw,
                      "Original raw fixture changed across the native phase")
            c.require(source_contract(consumer) == before, "Native selected source/compiler witness changed during execution")
            result["status"] = "PASS_G02_NATIVE_" + phase.upper() + "_READBACK"
    except BaseException as exc:
        if first is None: first = exc; result["firstFailure"] = c.error(exc)
        else: result["retentionErrors"].append({"phase": "qualification", **c.error(exc)})
    return lane.save_result(c, stage / "g02-native-phase.json", result, first)
