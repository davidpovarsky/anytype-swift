"""Closed finite Heart editor dispatch using the original F owner and fixture.

Every plan starts with a fresh owned simulator and original native preparation.
Single-method recovery plans never resume an old or partially edited fixture.
There is no product/source override and no additional process supervisor.
"""
from __future__ import annotations

from pathlib import Path
import re

import heart_editor_observations as observations

STARTUP_LANE = "editor"
SUPPORT = Path("Library/Application Support")
FIXTURE = "pinkha-stage1-acceptance-state.json"
PREPARATION = "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState"
LANES = {
    "heart-editor-mutations": list(observations.METHODS.values()),
    "heart-editor-split-merge": [observations.METHODS["split-merge"]],
    "heart-editor-range-replacement": [observations.METHODS["range-replacement"]],
}
PLANS = {
    "heart-mutations-only": ("heart-editor-mutations",),
    "heart-split-merge-only": ("heart-editor-split-merge",),
    "heart-range-replacement-only": ("heart-editor-range-replacement",),
}
STARTUP_PROFILE_SHA = "6960a4f74aa6b582e783addf358cc1806728dffd520483336c877e473b63aeb9"
STARTUP_CONSUMER_SHA = "1cd58739742768bb8863c49797c1035292796c1cf7ab6de0e928a90be5bf95a6"
OBSERVATIONS_SHA = "693afa112eb0f2c54f89b1b2ba1b7f5f9b39bbbd811887a02993d39ae2534915"
FUTURE_SOURCE_COMMIT = None
FUTURE_COMMON_SHA256 = None
FUTURE_ADMISSION_SHA256 = None


def require_runtime_ready(admission, control_root):
    """No JSON flag or arbitrary source pin can open the pending runtime gate."""
    raise ValueError("HEART_EDITOR_RUNTIME_CLOSED: actual matching complete source, shared producer, "
                     "common intake and exact admission remain required; no product is admitted by this source preparation")


def ui_budget(consumer, target, methods):
    if any(method in observations.METHODS.values() for method in methods):
        plan = consumer.admission.get("plan")
        consumer.shared_module.require(plan in PLANS and methods == LANES[PLANS[plan][0]],
                                       "Exact finite Heart editor plan and ordered selection required")
        return observations.time_budget(consumer.shared_module, target, methods)
    return consumer.helpers["run_ui27"].selection_time_budget(target, methods)


def save_result(c, path, result, first=None):
    try:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        c.write(path, result)
    except BaseException as exc:
        if first is None:
            raise
        result.setdefault("retentionErrors", []).append({"phase": "final-receipt-save", **c.error(exc)})
        if hasattr(first, "add_note"):
            first.add_note("Heart editor final receipt could not be saved: " + type(exc).__name__ + ": " + str(exc))
        raise first from exc
    if first is not None:
        raise first
    return result


def source_contract(consumer, lane):
    """Read selected compiler witnesses subordinate to complete common admission."""
    import torah_ui_profile
    import torah_ui_consumer
    c, source = consumer.shared_module, consumer.source
    c.require(lane in LANES and consumer.admission.get("plan") in PLANS
              and PLANS[consumer.admission["plan"]] == (lane,)
              and consumer.admission.get("appLanguage") in ("he", "en")
              and consumer.admission.get("deviceFamily") in ("iphone", "ipad"),
              "One finite original editor configuration and selection required")
    for module, expected in ((torah_ui_profile, STARTUP_PROFILE_SHA),
                             (torah_ui_consumer, STARTUP_CONSUMER_SHA), (observations, OBSERVATIONS_SHA)):
        c.require(c.sha(c.raw(Path(module.__file__))) == expected, "Exact reviewed editor helper changed")
    startup = torah_ui_consumer.before_ui(consumer, STARTUP_LANE)
    spec = consumer.helpers["run_wave15_acceptance"].LANES[STARTUP_LANE]
    c.require(spec["preparation"] == PREPARATION and spec["fixture"] == FIXTURE,
              "Only the unchanged original Stage1 preparation and fixture are eligible")
    source_raw = c.raw(source / observations.SOURCE_PATH)
    selected = observations.qualify_source(c, source_raw, c.raw(source / observations.SOURCE_PROOF_PATH))
    admission = consumer.source_admission
    compiled = admission.get("sameInvocationAppAndUI", {})
    c.require(admission.get("commit") == consumer.binding["sourceSHA"]
              and re.fullmatch(r"[0-9a-f]{64}", admission.get("sourceStateSHA256", "")) is not None
              and compiled.get("sourceCommit") == consumer.binding["sourceSHA"]
              and compiled.get("completeCompilerGate") is True,
              "Actual complete common source/App/UI admission is missing")
    producer = c.decode(observations.pinned(c, consumer.admission["producerReceipt"], 8 * 1024**2))
    c.require(producer.get("uiCompilationProof") == compiled.get("uiCompilationProof")
              and producer.get("nativeCompilationProof") == compiled.get("nativeCompilationProof"),
              "Compiler pins must come from the already-admitted complete actual producer")
    proof = c.decode(observations.pinned(c, producer["uiCompilationProof"], 8 * 1024**2))
    c.require(proof.get("schema") == "pinkha-exact-ui-compiler-inputs-v1"
              and proof.get("status") == "PASS_EXACT_UI_COPY_PROJECT_AND_COMPILER_INPUTS_NOT_TEST_EXECUTION"
              and proof.get("sourceCommit") == consumer.binding["sourceSHA"] and proof.get("testsExecuted") == 0,
              "Actual complete UI compilation proof belongs to another source")
    rows = [row for row in proof.get("requiredSources", []) if row.get("repositoryPath") == observations.SOURCE_PATH]
    c.require(len(rows) == 1 and rows[0].get("sha256") == observations.SOURCE_SHA
              and rows[0].get("bytes") == len(source_raw), "Actual compiler omitted the exact integrated Stage1 source")
    compiled_path = Path(rows[0]["compiledPath"])
    c.require(compiled_path.is_absolute() and compiled_path.resolve() == compiled_path
              and not compiled_path.is_symlink() and c.raw(compiled_path) == source_raw,
              "The actual compiled UI copy differs from the admitted original source")
    return {"sourceCommit": consumer.binding["sourceSHA"], "sourceStateSHA256": admission["sourceStateSHA256"],
            "startupSource": startup, "selectedSource": selected, "selectedMethods": LANES[lane],
            "selectedMethodCount": len(LANES[lane]), "documentFlows": 3 * len(LANES[lane]),
            "uiCompilationProof": producer["uiCompilationProof"], "nativeCompilationProof": producer["nativeCompilationProof"],
            "selectedUICompilerRow": rows[0], "commonCompleteCompilerGateRequired": True, "testsExecutedByThisCheck": 0}


def original_language_proof(consumer, directory, udid, language):
    """Re-read original create() evidence; this function issues no OS command."""
    c, original = consumer.shared_module, consumer.helpers["run_wave15_acceptance"]
    c.require(isinstance(language, dict), "Original verified editor device-language result required")
    record = directory / "device-language-observation.json"
    c.require(c.decode(c.raw(record)) == language, "Original device-language observation changed")
    command = consumer.commands.root / "editor-language-readback"
    result = c.decode(c.raw(command / "result.json"))
    c.require(result.get("status") == "PASS_COMMAND" and result.get("exitCode") == 0
              and result.get("argv") == ["xcrun", "simctl", "spawn", udid, "defaults", "export", "NSGlobalDomain", "-"],
              "Actual original language command belongs to another owned device")
    stdout = c.raw(command / "original.log", 1024**2)
    c.require(original.validate_device_language(stdout, consumer.admission["appLanguage"]) == language,
              "Requested opposite language differs from the actual original OS readback")
    return {"environment": observations.reference(c, record), "command": observations.reference(c, command / "result.json"),
            "stdout": observations.reference(c, command / "original.log"), "observed": language}


def run_lane(consumer, lane, directory, udid, language):
    """Always prepare a fresh fixture, including either single-method recovery."""
    require_runtime_ready(consumer.admission, Path(__file__).resolve().parent)
    import torah_ui_consumer
    c, original = consumer.shared_module, consumer.helpers["run_wave15_acceptance"]
    before = source_contract(consumer, lane)
    methods = list(LANES[lane])
    result = {"status": "FAIL", "sourceContract": before, "preparation": {"status": "NOT_RUN"}, "ui": {"status": "NOT_RUN"},
              "freshOriginalFixtureRequired": True, "selectedMethods": methods, "builds": 0,
              "intermediateEvidence": "UI_STATE_ONLY", "directNativeRangeObservation": False,
              "wholeStoreAcceptance": False, "fullFAcceptance": False, "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}
    first = None
    try:
        result["initialDeviceLanguage"] = original_language_proof(consumer, directory, udid, language)
        environment = original.preparation_environment(STARTUP_LANE, consumer.binding["sourceSHA"],
                                                       consumer.binding["runID"], consumer.binding["runAttempt"])
        prepared, prep_path = consumer.stage(directory, "preparation", udid, [PREPARATION + "()"], environment)
        result["preparation"] = prepared
        fixture_raw, container = consumer.read_private(udid, SUPPORT / FIXTURE, directory / "private",
                                                       lane + "-fixture", maximum=65536)
        fixture_ref = observations.reference(c, directory / "private" / FIXTURE)
        environment = original.fixture_environment(STARTUP_LANE, c.decode(fixture_raw), consumer.admission["appLanguage"],
                                                    language["device_language"])
        environment.update(PINKHA_UI27_APP_LANGUAGE=consumer.admission["appLanguage"], PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")
        startup, context = torah_ui_consumer.prepare_ui(consumer, STARTUP_LANE, directory, udid,
                                                       prepared, prep_path, fixture_raw, environment)
        observations.fixture_binding(c, fixture_raw, startup, udid)
        result["startupBinding"] = context["envelope"]
        original.source_methods(consumer.source, methods)
        actual, ui_path = consumer.stage(directory, "ui", udid, methods, startup, target=observations.TARGET)
        result["ui"] = actual
        result["originalStartupPrerequisites"] = torah_ui_consumer.after_ui(
            consumer, STARTUP_LANE, ui_path, context, methods, before["startupSource"])
        result["observations"] = observations.collect(consumer, ui_path, udid, startup, methods, fixture_ref=fixture_ref)
        current = consumer.container(udid, "data", lane + "-fixture-after")
        c.require(current == container and c.raw(current / SUPPORT / FIXTURE, 65536) == fixture_raw,
                  "The original owned fixture/container changed across the editor methods")
        c.require(source_contract(consumer, lane) == before, "Actual admitted source/compiler evidence changed during the UI stage")
        result["fixture"] = fixture_ref
        result["status"] = "PASS_SELECTED_HEART_EDITOR_FUNCTIONAL_SCOPE_VISUAL_REVIEW_PENDING"
    except BaseException as exc:
        first = exc
        result["firstFailure"] = c.error(exc)
    return save_result(c, directory / "heart-editor-mutations.json", result, first)
