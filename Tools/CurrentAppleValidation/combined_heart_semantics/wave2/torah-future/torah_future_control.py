"""Closed future Torah source compatibility and one finite G03 UI lane.

The original shared consumer owns products, process supervision, descriptors,
enumeration, XCTest results and simulator retention. This module reuses those
authorities and never admits a new product through a source-only preparation.
"""
from __future__ import annotations

from pathlib import Path
import re

import torah_overflow_observations as overflow

PLAN, LANE, STARTUP_LANE = "torah-overflow-only", "torah-source-overflow", "properties"
SUPPORT = Path("Library/Application Support")
FIXTURE = "pinkha-native-derived-ui-fixture.json"
PREPARATION = "TorahNativeDerivedProductIntegrationTests/originalProductPipeline"
STARTUP_SOURCE_PATH = "PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift"
STARTUP_SOURCE_SHA = "c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906"
STARTUP_PROFILE_SHA = "6960a4f74aa6b582e783addf358cc1806728dffd520483336c877e473b63aeb9"
STARTUP_CONSUMER_SHA = "1cd58739742768bb8863c49797c1035292796c1cf7ab6de0e928a90be5bf95a6"
OBSERVATIONS_SHA = "cadd23e2aa1726bb01c7601c46a6f26072e2ecad4bd95a389154069f5d3f1e38"
FUTURE_SOURCE_COMMIT = None
FUTURE_COMMON_SHA256 = None
FUTURE_ADMISSION_SHA256 = None


def require_runtime_ready(admission, control_root):
    """Unconditionally closed before roots, product cloning or owned creation."""
    raise ValueError("FUTURE_TORAH_RUNTIME_CLOSED: exact future source, common intake and admission "
                     "remain unbound; source compatibility and observed current Git bytes are not products")


def ui_budget(consumer, target, methods):
    """Only the exact one published G03 selector uses its declared 480 seconds."""
    if overflow.METHOD in methods:
        consumer.shared_module.require(consumer.admission.get("plan") == PLAN
                                       and target == overflow.TARGET and methods == [overflow.METHOD],
                                       "G03 requires its one exact finite UI selection and plan")
        return {"default_seconds": overflow.ALLOWANCE, "maximum_seconds": overflow.ALLOWANCE,
                "method_seconds": {overflow.METHOD: overflow.ALLOWANCE},
                "total_method_seconds": overflow.ALLOWANCE,
                "scope": "PUBLISHED_G03_METHOD_EXECUTION_TIME_ALLOWANCE",
                "sourceSHA256": overflow.SOURCE_SHA, "originalRunUI27BudgetHelperChanged": False}
    return consumer.helpers["run_ui27"].selection_time_budget(target, methods)


def save_result(c, path, result, first=None):
    """A final evidence-write failure cannot replace the original stage failure."""
    try:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        c.write(path, result)
    except BaseException as exc:
        if first is None:
            raise
        result.setdefault("retentionErrors", []).append({"phase": "final-receipt-save", **c.error(exc)})
        if hasattr(first, "add_note"):
            first.add_note("G03 final receipt could not be saved: " + type(exc).__name__ + ": " + str(exc))
        raise first from exc
    if first is not None:
        raise first
    return result


def source_contract(consumer):
    """Select actual compiler rows only after the complete shared admission."""
    import torah_ui_profile
    import torah_ui_consumer
    c, source = consumer.shared_module, consumer.source
    c.require(consumer.admission.get("plan") == PLAN
              and consumer.admission.get("appLanguage") == "en"
              and consumer.admission.get("deviceFamily") == "ipad",
              "The finite original G03 lane requires an English owned iPad admission")
    for module, expected in ((torah_ui_profile, STARTUP_PROFILE_SHA),
                             (torah_ui_consumer, STARTUP_CONSUMER_SHA), (overflow, OBSERVATIONS_SHA)):
        c.require(c.sha(c.raw(Path(module.__file__))) == expected, "Exact reviewed Torah source helper changed")
    startup_source = torah_ui_consumer.before_ui(consumer, STARTUP_LANE)
    spec = consumer.helpers["run_wave15_acceptance"].LANES[STARTUP_LANE]
    c.require(spec["preparation"] == PREPARATION and spec["fixture"] == FIXTURE,
              "G03 reuses only the original NativeDerived preparation and fixture")
    ui_raw, warning_raw = c.raw(source / overflow.SOURCE_PATH), c.raw(source / STARTUP_SOURCE_PATH)
    selected_source = overflow.qualify_source(c, ui_raw)
    c.require(c.sha(warning_raw) == STARTUP_SOURCE_SHA, "Only the exact integrated Stage1 append is eligible")
    admission = consumer.source_admission
    compiled = admission.get("sameInvocationAppAndUI", {})
    c.require(admission.get("commit") == consumer.binding["sourceSHA"]
              and re.fullmatch(r"[0-9a-f]{64}", admission.get("sourceStateSHA256", "")) is not None
              and compiled.get("sourceCommit") == consumer.binding["sourceSHA"]
              and compiled.get("completeCompilerGate") is True,
              "Actual common source and complete App/UI compiler admission is missing")
    producer = c.decode(overflow.pinned(c, consumer.admission["producerReceipt"], 8 * 1024**2))
    c.require(producer.get("uiCompilationProof") == compiled.get("uiCompilationProof")
              and producer.get("nativeCompilationProof") == compiled.get("nativeCompilationProof"),
              "Selected compiler refs must come from the already-admitted actual producer")
    proof = c.decode(overflow.pinned(c, producer["uiCompilationProof"], 8 * 1024**2))
    c.require(proof.get("schema") == "pinkha-exact-ui-compiler-inputs-v1"
              and proof.get("status") == "PASS_EXACT_UI_COPY_PROJECT_AND_COMPILER_INPUTS_NOT_TEST_EXECUTION"
              and proof.get("sourceCommit") == consumer.binding["sourceSHA"] and proof.get("testsExecuted") == 0,
              "Original complete Stage1 UI compiler proof is not for the admitted source")
    # The shared gate retains all original project/FileList/swiftc witnesses.
    # These two selected rows are subordinate to that complete admission.
    witnesses = {}
    for relative, data in ((overflow.SOURCE_PATH, ui_raw), (STARTUP_SOURCE_PATH, warning_raw)):
        rows = [row for row in proof.get("requiredSources", []) if row.get("repositoryPath") == relative]
        c.require(len(rows) == 1 and rows[0].get("sha256") == c.sha(data) and rows[0].get("bytes") == len(data),
                  "Actual shared compiler omitted the selected G03 or startup source")
        row = rows[0]
        path = Path(row["compiledPath"])
        c.require(path.is_absolute() and path.resolve() == path and not path.is_symlink() and c.raw(path) == data,
                  "Actually compiled UI copy differs from the admitted selected source")
        witnesses[relative] = row
    return {"sourceCommit": consumer.binding["sourceSHA"], "sourceStateSHA256": admission["sourceStateSHA256"],
            "startupSource": startup_source, "selectedSource": selected_source,
            "uiCompilationProof": producer["uiCompilationProof"],
            "nativeCompilationProof": producer["nativeCompilationProof"],
            "selectedUICompilerRows": witnesses, "commonCompleteCompilerGateRequired": True,
            "testsExecutedByThisCheck": 0}


def run_overflow_lane(consumer, directory, udid):
    """One original preparation and unchanged G03 method on its owned fixture."""
    require_runtime_ready(consumer.admission, Path(__file__).resolve().parent)
    import torah_ui_consumer
    c, original = consumer.shared_module, consumer.helpers["run_wave15_acceptance"]
    before = source_contract(consumer)
    result = {"status": "FAIL", "sourceContract": before, "preparation": {"status": "NOT_RUN"},
              "ui": {"status": "NOT_RUN"}, "builds": 0, "nativePersistenceAccepted": False,
              "fullPropertiesAcceptance": False, "physicalDevice": "NOT_RUN", "visualReview": "PENDING"}
    first = None
    try:
        environment = original.preparation_environment(STARTUP_LANE, consumer.binding["sourceSHA"],
                                                       consumer.binding["runID"], consumer.binding["runAttempt"])
        prepared, prep_path = consumer.stage(directory, "preparation", udid, [PREPARATION + "()"], environment)
        result["preparation"] = prepared
        fixture_raw, container = consumer.read_private(udid, SUPPORT / FIXTURE, directory / "private",
                                                        LANE + "-fixture", maximum=65536)
        fixture_ref = overflow.reference(c, directory / "private" / FIXTURE)
        environment = original.fixture_environment(STARTUP_LANE, c.decode(fixture_raw), "en")
        environment.update(PINKHA_UI27_APP_LANGUAGE="en", PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")
        startup, context = torah_ui_consumer.prepare_ui(consumer, STARTUP_LANE, directory, udid,
                                                       prepared, prep_path, fixture_raw, environment)
        overflow.fixture_binding(c, fixture_raw, startup, udid)
        result["startupBinding"] = context["envelope"]
        methods = [overflow.METHOD]
        original.source_methods(consumer.source, methods)
        ui_result, ui_path = consumer.stage(directory, "ui", udid, methods, startup, target=overflow.TARGET)
        result["ui"] = ui_result
        result["originalStartupPrerequisites"] = torah_ui_consumer.after_ui(
            consumer, STARTUP_LANE, ui_path, context, methods, before["startupSource"])
        result["observations"] = overflow.collect(consumer, ui_path, udid, startup, fixture_ref=fixture_ref)
        current = consumer.container(udid, "data", LANE + "-fixture-after")
        c.require(current == container and c.raw(current / SUPPORT / FIXTURE, 65536) == fixture_raw,
                  "Original fixture/container changed across G03 UI selection")
        c.require(source_contract(consumer) == before, "G03 source/compiler witnesses changed during execution")
        result["fixture"] = fixture_ref
        result["status"] = "PASS_G03_FUNCTIONAL_SCOPE_VISUAL_REVIEW_PENDING"
    except BaseException as exc:
        first = exc
        result["firstFailure"] = c.error(exc)
    return save_result(c, directory / "g03-overflow.json", result, first)
