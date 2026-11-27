"""Closed future four-stage G02 lane using the shared owned-fixture lifecycle.

This preparation deliberately cannot admit or run on the current 8f2 products.
After an actual future App and complete UI producer includes both published
test files, a reviewed derivative must bind its exact common intake and native
phase adapter. There is no command-line, environment or JSON readiness override.
"""
from __future__ import annotations

from pathlib import Path
import re

import g02_ui_receipts as ui

PLAN, LANE, STARTUP_LANE = "g02-word-only", "g02-word", "properties"
SUPPORT = Path("Library/Application Support")
FIXTURE = "pinkha-native-derived-ui-fixture.json"
PREPARATION = "TorahNativeDerivedProductIntegrationTests/originalProductPipeline"
NATIVE_SOURCE_PATH = "AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift"
NATIVE_SOURCE_SHA = "b453fafed2e5e5737ef04524b6add7c4bf0019cf99a03c6137151039f38171ed"
NATIVE_ORIGINAL_SHA = "7ec7ef47c53c02e61b0cccb05ab7f4f58b3824368d84883aadee6767ff24ab85"
NATIVE_ORIGINAL_BYTES = 84286
STARTUP_SOURCE_PATH = "PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift"
STARTUP_PREFIX_BYTES = 86201
STARTUP_PREFIX_SHA = "d4ffc25ee659e03bd4dd76b7847faf4fecf343630edf094c0bc02fe060f00850"
ORIGINAL_HELPERS = {
    "run_wave15_acceptance": "f99b1c04efeee2be45459b49d8c71fd8207039c97be4578cd6f2dfc8d29bb283",
    "run_ui27": "87e0972ee6852d1fdb34d82afa5dde346baf836afaa8419203b647e7d3e21ca7",
}
STARTUP_PROFILE_SHA = "16e65f6a5fe338e384c45f67bde3a294bc49dbf4346d6d300f70aa735a025549"
STARTUP_CONSUMER_SHA = "1cd58739742768bb8863c49797c1035292796c1cf7ab6de0e928a90be5bf95a6"
PHASE_ORDER = ("ui-seed", "native-baseline", "ui-unlink", "native-postflight")


def require_runtime_ready(admission, control_root):
    """Intentionally closed before common cloning, simulator creation or XCTest."""
    raise ValueError("G02_RUNTIME_CLOSED: native phase adapter pin and an actual common-admitted future "
                     "App/complete UI producer containing d7e512 + b453fa are required; current 8f2 is not eligible")


def ui_budget(consumer, target, methods):
    if any(method in ui.METHODS.values() for method in methods):
        consumer.shared_module.require(consumer.admission.get("plan") == PLAN,
                                       "G02 selectors require their own finite four-stage plan")
        return ui.ui_time_budget(target, methods)
    return consumer.helpers["run_ui27"].selection_time_budget(target, methods)


def save_result(c, path, result, first=None):
    """A later receipt/directory failure must not mask the first stage failure."""
    try:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        c.write(path, result)
    except BaseException as exc:
        if first is None:
            raise
        result.setdefault("retentionErrors", []).append({"phase": "final-receipt-save", **c.error(exc)})
        if hasattr(first, "add_note"):
            first.add_note("G02 final receipt could not be saved: " + type(exc).__name__ + ": " + str(exc))
        raise first from exc
    if first is not None:
        raise first
    return result


def source_contract(consumer):
    """Read exact selected bytes after the future common gate; never admit products."""
    import torah_ui_profile
    import torah_ui_consumer
    c, source = consumer.shared_module, consumer.source
    c.require(consumer.admission.get("appLanguage") == "en"
              and consumer.admission.get("deviceFamily") == "ipad"
              and consumer.admission.get("plan") == PLAN,
              "This finite future G02 lane is English on one owned iPad simulator")
    for name, sha in ORIGINAL_HELPERS.items():
        c.require(c.sha(c.raw(Path(consumer.helpers[name].__file__))) == sha, "Original G02 execution helper changed: " + name)
    c.require(c.sha(c.raw(Path(torah_ui_profile.__file__))) == STARTUP_PROFILE_SHA
              and c.sha(c.raw(Path(torah_ui_consumer.__file__))) == STARTUP_CONSUMER_SHA,
              "Original controller-observed startup helpers must remain byte-identical")
    spec = consumer.helpers["run_wave15_acceptance"].LANES[STARTUP_LANE]
    c.require(spec["preparation"] == PREPARATION and spec["fixture"] == FIXTURE,
              "G02 may reuse only the original NativeDerived preparation/fixture")
    ui_source = c.raw(source / ui.SOURCE_PATH)
    inverse = ui.qualify_source(c, ui_source, c.raw(source / ui.SOURCE_PROOF_PATH))
    native_source, startup_source = c.raw(source / NATIVE_SOURCE_PATH), c.raw(source / STARTUP_SOURCE_PATH)
    c.require(c.sha(native_source) == NATIVE_SOURCE_SHA
              and c.sha(native_source[:NATIVE_ORIGINAL_BYTES]) == NATIVE_ORIGINAL_SHA,
              "Future read-only native companion must preserve the complete original preparation")
    c.require(c.sha(startup_source[:STARTUP_PREFIX_BYTES]) == STARTUP_PREFIX_SHA
              and startup_source.count(b"enum PinkhaDisposableStartupWarning {") == 1,
              "Original exact-warning admission and Properties helper prefix changed")
    admission = consumer.source_admission
    compiled = admission.get("sameInvocationAppAndUI", {})
    c.require(admission.get("commit") == consumer.binding["sourceSHA"]
              and re.fullmatch(r"[0-9a-f]{64}", admission.get("sourceStateSHA256", "")) is not None
              and compiled.get("sourceCommit") == consumer.binding["sourceSHA"]
              and compiled.get("completeCompilerGate") is True,
              "Actual common source and complete App/UI compiler admission is missing")
    producer = c.decode(ui.pinned(c, consumer.admission["producerReceipt"], 8 * 1024**2))
    c.require(producer.get("uiCompilationProof") == compiled.get("uiCompilationProof")
              and producer.get("nativeCompilationProof") == compiled.get("nativeCompilationProof"),
              "Selected compiler refs must come from the already-admitted actual producer")
    proof = c.decode(ui.pinned(c, producer["uiCompilationProof"], 8 * 1024**2))
    c.require(proof.get("schema") == "pinkha-exact-ui-compiler-inputs-v1"
              and proof.get("status") == "PASS_EXACT_UI_COPY_PROJECT_AND_COMPILER_INPUTS_NOT_TEST_EXECUTION"
              and proof.get("sourceCommit") == consumer.binding["sourceSHA"] and proof.get("testsExecuted") == 0,
              "Original complete Stage1 UI compiler proof is not for this admitted source")
    # The common gate has already checked every physical source/copy/FileList
    # and original swiftc log line. This selects two required rows from that
    # complete proof without substituting declaration-only source enumeration.
    witnesses = {}
    for relative, source_bytes in ((ui.SOURCE_PATH, ui_source), (STARTUP_SOURCE_PATH, startup_source)):
        matches = [row for row in proof.get("requiredSources", []) if row.get("repositoryPath") == relative]
        c.require(len(matches) == 1 and matches[0].get("sha256") == c.sha(source_bytes)
                  and matches[0].get("bytes") == len(source_bytes), "Actual shared UI compiler omitted the selected G02/startup bytes")
        row = matches[0]
        compiled_path = Path(row["compiledPath"])
        c.require(compiled_path.is_absolute() and compiled_path.resolve() == compiled_path
                  and not compiled_path.is_symlink() and c.raw(compiled_path) == source_bytes,
                  "Actually compiled UI copy differs from admitted selected source")
        witnesses[relative] = row
    return {"uiSource": inverse, "nativeSourceSHA256": NATIVE_SOURCE_SHA,
            "originalNativePreparationSHA256": NATIVE_ORIGINAL_SHA,
            "startupPrefixSHA256": STARTUP_PREFIX_SHA, "sourceCommit": consumer.binding["sourceSHA"],
            "sourceStateSHA256": admission["sourceStateSHA256"], "uiCompilationProof": producer["uiCompilationProof"],
            "nativeCompilationProof": producer["nativeCompilationProof"], "selectedUICompilerRows": witnesses,
            "commonCompleteCompilerGateRequired": True, "testsExecutedByThisCheck": 0}


def lifecycle_boundary(consumer, directory, udid, label, fixture_raw, prior=None):
    """Reuse original stopped-App and directory identity readers; never kill it."""
    c, preservation = consumer.shared_module, consumer.helpers["type_preservation"]
    installed = consumer.installed(udid, LANE + "-" + label)
    stopped = preservation.assert_app_stopped(udid, Path(installed["installedApp"]))
    container = consumer.container(udid, "data", LANE + "-" + label + "-data")
    current = c.raw(container / SUPPORT / FIXTURE, 65536)
    c.require(current == fixture_raw, "Original native fixture changed across G02 stages")
    identities = {"container": preservation.directory_identity(container),
                  "middleware": preservation.directory_identity(container / preservation.STORE)}
    if prior is not None:
        c.require(identities == prior["directories"], "G02 native store or container was recreated/relocated")
    proof = {"status": "PASS_OWNED_APP_STOPPED_AND_ORIGINAL_DIRECTORIES_RETAINED", "stageBoundary": label,
             "udid": udid, "originalFixtureSHA256": c.sha(fixture_raw), "installedOriginalCode": installed,
             "stoppedApp": stopped, "directories": identities,
             "wholeStoreBytePreservationClaimed": False, "nativeSemanticReadbackSeparate": True}
    path = directory / ("boundary-" + label + ".json")
    c.write(path, proof)
    return proof, ui.reference(c, path)


def run_word_lane(consumer, directory, udid):
    """One original preparation then four stages; no accepted historical replay."""
    require_runtime_ready(consumer.admission, Path(__file__).resolve().parent)
    # The source adapter is pinned by the reviewed future control closure;
    # actual matching product admission remains a separate closed prerequisite.
    import g02_native_phase
    import torah_ui_consumer
    c, original = consumer.shared_module, consumer.helpers["run_wave15_acceptance"]
    before = source_contract(consumer)
    result = {"status": "FAIL", "phaseOrder": list(PHASE_ORDER), "sourceContract": before,
              "preparation": {"status": "NOT_RUN"}, "stages": {p: {"status": "NOT_RUN"} for p in PHASE_ORDER},
              "boundaries": {}, "builds": 0, "nativeEngineContractChanges": False,
              "physicalDevice": "NOT_RUN", "visualReview": "PENDING", "fullPropertiesAcceptance": False}
    private = directory / "private"; private.mkdir(mode=0o700)
    first = None
    try:
        environment = original.preparation_environment(STARTUP_LANE, consumer.binding["sourceSHA"], consumer.binding["runID"], consumer.binding["runAttempt"])
        prep, prep_path = consumer.stage(directory, "preparation", udid, [PREPARATION + "()"], environment)
        result["preparation"] = prep
        fixture_raw, _ = consumer.read_private(udid, SUPPORT / FIXTURE, private, LANE + "-fixture", maximum=65536)
        fixture_ref = ui.reference(c, private / FIXTURE)
        ui_environment = original.fixture_environment(STARTUP_LANE, c.decode(fixture_raw), "en")
        ui_environment.update(PINKHA_UI27_APP_LANGUAGE="en", PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")
        startup, startup_context = torah_ui_consumer.prepare_ui(consumer, STARTUP_LANE, directory, udid, prep, prep_path, fixture_raw, ui_environment)
        ui.fixture_binding(c, fixture_raw, startup, udid)
        result["startupBinding"] = startup_context["envelope"]
        baseline_boundary, result["boundaries"]["preparation"] = lifecycle_boundary(consumer, directory, udid, "preparation", fixture_raw)

        _, seed_path = consumer.stage(directory, "ui-seed", udid, [ui.METHODS["seed"]], dict(startup, PINKHA_G02_UI_PHASE="seed"), target=ui.TARGET)
        seed = ui.collect_ui_phase(consumer, seed_path, udid, "seed", startup, fixture_ref=fixture_ref)
        result["stages"]["ui-seed"] = seed
        _, result["boundaries"]["ui-seed"] = lifecycle_boundary(consumer, directory, udid, "ui-seed", fixture_raw, baseline_boundary)
        c.write(directory / "g02-checkpoint-ui-seed.json", result)

        native = g02_native_phase.run_native_phase(consumer, directory, udid, "baseline", startup, seed["completion"])
        result["stages"]["native-baseline"] = native
        _, result["boundaries"]["native-baseline"] = lifecycle_boundary(consumer, directory, udid, "native-baseline", fixture_raw, baseline_boundary)
        compact = ui.pinned(c, native["uiBaseline"])
        c.require(c.decode(compact).get("seedUIReceiptSHA256") == seed["completion"]["sha256"]
                  and c.decode(compact).get("nativeBaselineSHA256") == native["baseline"]["sha256"],
                  "Native compact handoff must bind the actual full baseline and seed bytes")
        c.write(directory / "g02-checkpoint-native-baseline.json", result)

        environment = dict(startup, PINKHA_G02_UI_PHASE="unlink", PINKHA_G02_BASELINE_UI_JSON=compact.decode("utf-8"),
                           PINKHA_G02_BASELINE_UI_SHA256=c.sha(compact))
        _, unlink_path = consumer.stage(directory, "ui-unlink", udid, [ui.METHODS["unlink"]], environment, target=ui.TARGET)
        unlink = ui.collect_ui_phase(consumer, unlink_path, udid, "unlink", startup, fixture_ref=fixture_ref,
                                     baseline_ref=native["uiBaseline"], seed_ui_ref=seed["completion"])
        result["stages"]["ui-unlink"] = unlink
        _, result["boundaries"]["ui-unlink"] = lifecycle_boundary(consumer, directory, udid, "ui-unlink", fixture_raw, baseline_boundary)
        c.write(directory / "g02-checkpoint-ui-unlink.json", result)

        postflight = g02_native_phase.run_native_phase(consumer, directory, udid, "postflight", startup, seed["completion"],
                                                        baseline_ref=native["baseline"], unlink_ui_ref=unlink["completion"])
        result["stages"]["native-postflight"] = postflight
        _, result["boundaries"]["native-postflight"] = lifecycle_boundary(consumer, directory, udid, "native-postflight", fixture_raw, baseline_boundary)
        c.require(source_contract(consumer) == before, "G02 admitted source/compiler witnesses changed during execution")
        result["status"] = "PASS_G02_FOUR_STAGE_FUNCTIONAL_SCOPE_VISUAL_REVIEW_PENDING"
    except BaseException as exc:
        first = exc; result["firstFailure"] = c.error(exc)
    return save_result(c, directory / "g02-four-stage.json", result, first)
