"""Run existing Wave-15 UI suites on one fresh OS27 configuration.

A lane result is evidence for its named methods, not full-matrix or release
acceptance. The main controller runs a successful Home/document smoke first.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

import run_ui27 as shared

BRANCH = "codex/chatgpt-wave15-integration-20261118"
LANES = {
    "inspector": {
        "suite": "AnytypeComprehensiveAcceptanceUITests",
        "methods": shared.SMOKE + ["testDocumentSourceSearchEmptyAndClear", "testInspectorShowsIndexedRelatedDocument"],
        "preparation": "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
        "preparation_environment": {"PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
        "fixture": "pinkha-simulator-ui27-fixture.json",
    },
    "properties": {
        "suite": "PinkhaNativeDerivedAcceptanceUITests",
        "methods": ["testNativePropertiesPickerChipsSetMembershipAndRelaunch", "testSourceHeaderSelectionAndOverflow",
                    "testUniversalPageNoteCustomPropertiesAndMixedSet", "testRemainingNativeSourceFilterEditing",
                    "testRemainingUniversalTypePickersAndMixedSet"],
        "preparation": "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
        "preparation_environment": {"PINKHA_NATIVE_DERIVED_ACCEPTANCE": "1"},
        "fixture": "pinkha-native-derived-ui-fixture.json",
    },
    "editor": {
        "suite": "PinkhaStage1AcceptanceUITests",
        "methods": ["testAppWideDirectionPersistenceAndInteractiveBack", "testMultiBlockEnterCreationAndTypingLifecycle",
                    "testDocumentSourcesEntryOpensExistingSearch"],
        "preparation": "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
        "preparation_environment": {},
        "fixture": "pinkha-stage1-acceptance-state.json",
    },

    "canonical-properties": {
        "suite": "PinkhaTorahPropertiesAcceptanceUITests",
        "methods": ["testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes"],
        "preparation": "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
        "preparation_environment": {"PINKHA_PROPERTIES_PREPARE": "1"},
        "fixture": "pinkha-stage1-acceptance-state.json",
    },
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def plan(lane, device, language):
    require(lane in LANES, "Unknown acceptance lane")
    require(device in {"iphone", "ipad"} and language in {"en", "he"}, "Unknown actual configuration")
    require(lane == "editor" or language == "en",
            "Existing non-editor methods use English labels; do not report them as Hebrew acceptance")
    spec = LANES[lane]
    methods = [spec["suite"] + "/" + name for name in spec["methods"]]
    require(methods and len(methods) == len(set(methods)), "Empty or duplicate named UI selection")
    return dict(lane=lane, device_family=device, app_language=language,
                configuration_id=device + "-" + language + "-portrait-os27",
                methods=methods, expected_ui_executions=len(methods),
                preparation=spec["preparation"], expected_preparation_executions=1,
                release_accepted=False, full_matrix_accepted=False,
                device_language_verified=False)


def nonempty(value, name):
    require(isinstance(value, str) and bool(value.strip()), "Missing actual fixture " + name)
    return value


def fixture_environment(lane, value, language):
    nonempty(value.get("spaceId"), "Space")
    if lane in {"inspector", "properties"}:
        docs = value.get("universalDocuments", {})
        page = nonempty(docs.get("page"), "Page")
        source = nonempty(value.get("manySourcesDocument"), "source document")
        require(page != source, "Page and source document must be distinct")
        if lane == "properties":
            writing = value.get("documents", {})
            require(len(writing) == 3 and len(set(writing.values())) == 3
                    and all(isinstance(v, str) and v for v in writing.values()), "Missing distinct writing-type documents")
            nonempty(value.get("setId"), "native Set")
            nonempty(value.get("universalSetId"), "mixed Set")
        return {"PINKHA_NATIVE_UI_DISPOSABLE": "1", "PINKHA_NATIVE_UI_FIXTURE_JSON": json.dumps(value)}
    ids = [nonempty(value.get(key), key) for key in ("pinkhaObjectId", "noteObjectId", "pageObjectId")]
    require(len(set(ids)) == 3, "Editor fixtures must be three distinct native objects")
    return {
        "PINKHA_ACCEPTANCE_SPACE_ID": value["spaceId"],
        "PINKHA_ACCEPTANCE_PINKHA_ID": ids[0],
        "PINKHA_ACCEPTANCE_NOTE_ID": ids[1],
        "PINKHA_ACCEPTANCE_PAGE_ID": ids[2],
        "PINKHA_ACCEPTANCE_DIRECTION": "rtl" if language == "he" else "ltr",
        "PINKHA_ACCEPTANCE_DEVICE_LANGUAGE": "en" if language == "he" else "he",
    }


def property_environment(preparation, expected_space):
    marker = "PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON "
    observed = {}
    for path in sorted(preparation.glob("command-*.log")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if marker in line:
                value = json.loads(line.split(marker, 1)[1].strip())
                observed[json.dumps(value, sort_keys=True)] = value
    require(len(observed) == 1, "Expected one actual native property fixture")
    value = next(iter(observed.values()))
    require(value.get("PINKHA_PROPERTIES_SPACE_ID") == expected_space, "Property fixture belongs to another Space")
    require(value.get("PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED") == "1", "Disposable property fixture confirmation missing")
    ids = [nonempty(value.get("PINKHA_PROPERTIES_" + role + "_ID"), role) for role in ("CHIDDUSH", "ARTICLE", "RESEARCH")]
    require(len(set(ids)) == 3, "Property documents must be distinct")
    labels = json.loads(nonempty(value.get("PINKHA_PROPERTIES_NATIVE_PROPERTY_LABELS"), "native property labels"))
    require(all(isinstance(labels.get(i), list) and labels[i] for i in ids), "Native original property labels missing")
    value.update(PINKHA_PROPERTIES_SOURCE_QUERY="Genesis 1:1", PINKHA_PROPERTIES_SOURCE_LABEL="Genesis 1:1",
                 PINKHA_PROPERTIES_TOPIC_QUERY="Creation", PINKHA_PROPERTIES_TOPIC_LABEL="Creation")
    return value


def source_methods(app, selection):
    text = "\n".join(p.read_text(encoding="utf-8") for p in (app / "PinkhaStage1Acceptance/Tests").glob("*.swift"))
    for method in selection:
        suite, name = method.split("/")
        require("class " + suite + ":" in text and re.search(r"\bfunc\s+" + re.escape(name) + r"\s*\(", text),
                "Selected real UI method absent from tracked source: " + method)


def execute(args, receipt):
    require(platform.system() == "Darwin", "Actual Apple host required")
    app, evidence, derived = args.app.resolve(), args.evidence.resolve(), args.derived.resolve()
    selection = plan(args.lane, args.device, args.language)
    source_methods(app, selection["methods"])
    head = shared.git(app, "rev-parse", "HEAD")
    require(head == os.environ.get("GITHUB_SHA") and shared.git(app, "branch", "--show-current") == BRANCH,
            "Actual integration source identity differs")
    require(os.environ.get("GITHUB_RUN_ID", "").isdigit(), "Missing actual CI run identity")
    preflight = json.loads((evidence / "preflight/preflight.json").read_text())
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN"
            and preflight.get("source_sha") == head
            and preflight.get("run_id") == os.environ["GITHUB_RUN_ID"], "OS27 preflight is not from this source/run")
    selected = preflight["selected"][args.device]
    udid = selected["udid"]
    require(selected["name"] == "Pinkha-UI27-" + os.environ["GITHUB_RUN_ID"] + "-" + args.device,
            "Refuse a non-disposable simulator")
    installation = json.loads((evidence / "heart/heart-installation.json").read_text())
    require(installation.get("status") == "PASS" and installation.get("app_source_sha") == head
            and installation.get("marker") == shared.MARKER, "Exact native runtime was not installed")
    matrix = json.loads((app / "Tools/PinkhaSimulatorGate/required-coverage.json").read_text())
    identity = shared.candidate_identity(app, matrix)
    receipt.update(source_sha=head, run_id=os.environ["GITHUB_RUN_ID"], run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
                   kit_sha=shared.KIT, native_marker=shared.MARKER, selection=selection,
                   candidate_input_hashes=identity["hashes"], runtime_installation=installation, phase="BUILD")
    shared.write(evidence / "selection-plan.json", selection)
    shared.write(evidence / "execution.json", receipt)
    shared.command(["xcrun", "simctl", "boot", udid], app, evidence)
    shared.command(["xcrun", "simctl", "bootstatus", udid, "-b"], app, evidence)
    device_language = subprocess.run(["xcrun", "simctl", "spawn", udid, "defaults", "read", "-g", "AppleLanguages"],
                                    capture_output=True, text=True)
    shared.write(evidence / "device-language-observation.json",
                 dict(command_exit_code=device_language.returncode, observed=device_language.stdout,
                      error=device_language.stderr, requested_device_language_label=(("en" if args.language == "he" else "he")
                                                       if args.lane == "editor" else None),
                      acceptance=False))
    shared.prepare_source_cache(app, derived)
    flags = ["OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED", "ENABLE_TESTABILITY=YES",
             "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
             "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
    native_suite = LANES[args.lane]["preparation"].split("/")[0]
    base = ["xcodebuild", "build-for-testing", "-configuration", "Release-Anytype",
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO"]
    shared.command([*base, "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
                    "-derivedDataPath", str(derived), "-only-testing:AnytypeTests/" + native_suite, *flags], app, evidence)
    receipt.update(native_build_succeeded=True, native_build_flags=flags)
    built = derived / "Build/Products/Release-Anytype-iphonesimulator/Anytype.app"
    shared.verify_signed_simulator(built, evidence)
    shared.verify_runtime_copies(built, shared.MARKER.encode(), evidence)
    checkouts = derived / "SourcePackages/checkouts"
    kit = next(p for p in checkouts.iterdir() if p.name.casefold() == "torahinspectorkit")
    require(shared.git(kit, "rev-parse", "HEAD") == shared.KIT, "Actual Kit checkout differs")
    lock = json.loads((app / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").read_text())
    require(next(p["state"]["revision"] for p in lock["pins"] if p["identity"] == "torahinspectorkit") == shared.KIT,
            "Actual Kit lock differs")
    shared.write(evidence / "actual-package-pins.json", lock)
    before = shared.code_carriers(built)
    shared.write(evidence / "built-code-carriers.json", before)
    native_configuration = shared.test_configuration(derived / "Build/Products", "AnytypeTests")
    receipt["phase"] = "PREPARATION"
    preparation = shared.run_selection(app, native_configuration, "AnytypeTests", udid,
        [LANES[args.lane]["preparation"]], LANES[args.lane]["preparation_environment"], evidence / "preparation", "prepare")
    receipt["preparation"] = preparation
    shared.write(evidence / "execution.json", receipt)
    require(preparation["status"] == "PASS", "The actual native fixture did not pass")
    container = Path(subprocess.check_output(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "data"], text=True).strip())
    fixture = json.loads((container / "Library/Application Support" / LANES[args.lane]["fixture"]).read_text())
    environment = fixture_environment(args.lane, fixture, args.language)
    if args.lane == "canonical-properties":
        environment.update(property_environment(evidence / "preparation", fixture["spaceId"]))
    shared.write(evidence / "fixture-ids.json", fixture)
    project = shared.ui_only_project(app)
    ui_derived = derived.with_name(derived.name + "-ui")
    shared.command([*base, "-project", str(project), "-scheme", "PinkhaPrebuiltUI", "-derivedDataPath", str(ui_derived),
                    *["-only-testing:PinkhaStage1AcceptanceUITests/" + method for method in selection["methods"]], *flags], app, evidence)
    live = shared.live_runtime(udid, evidence, built, args.language, source_identity={
        "source_sha": head, "run_id": receipt["run_id"], "run_attempt": receipt["run_attempt"],
        "kit_sha": shared.KIT, "native_marker": shared.MARKER,
        "candidate_inputs_sha256": hashlib.sha256(json.dumps(identity["hashes"], sort_keys=True).encode()).hexdigest()})
    receipt["live_runtime_before_ui"] = live
    shared.install_ui_runner(udid, ui_derived / "Build/Products", app, evidence)
    configuration = shared.test_configuration(ui_derived / "Build/Products", "PinkhaStage1AcceptanceUITests")
    environment.update(PINKHA_UI27_APP_LANGUAGE=args.language, PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")
    if args.lane == "inspector":
        environment["PINKHA_UI27_EXPECTED_APP_PID"] = str(live["pid"])
    receipt["phase"] = "UI"
    shared.write(evidence / "execution.json", receipt)
    try:
        result = shared.run_selection(app, configuration, "PinkhaStage1AcceptanceUITests", udid,
            selection["methods"], environment, evidence / "ui", "wave15-" + args.lane, built)
        receipt["ui"] = result
    finally:
        shared.export_ui_console(udid, evidence)
    require(result["status"] == "PASS" and result["passed"] == selection["expected_ui_executions"],
            "Actual named UI selection did not pass")
    if args.lane == "inspector":
        receipt["ui_process_continuity"] = shared.verify_ui_process_continuity(
            evidence / "ui", "wave15-" + args.lane, live, selection["methods"])
    installed = Path(subprocess.check_output(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "app"], text=True).strip())
    after = shared.code_carriers(installed)
    shared.write(evidence / "post-ui-installed-code-carriers.json", after)
    require(before["sha256"] == after["sha256"], "Installed executable bytes changed during UI execution")
    require(shared.git(app, "rev-parse", "HEAD") == head, "Source changed during acceptance")
    receipt.update(status="LANE_PASS_ACCEPTANCE_REVIEW_PENDING", phase="COMPLETE",
                   passed_ui_methods=result["passed"], failed_ui_methods=0, skipped_ui_methods=0,
                   full_matrix_accepted=False, release_accepted=False,
                   limitations=["This result covers only its named methods and actual configuration.",
                                "Screenshots require visual review. IME/Undo/drop and other unselected criteria remain open.",
                                "Device-language mismatch and every relaunch's live mapping are not established by a requested label."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--lane", choices=list(LANES), required=True)
    parser.add_argument("--device", choices=["iphone", "ipad"], required=True)
    parser.add_argument("--language", choices=["en", "he"], required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    require(not (args.evidence / "execution.json").exists(), "Refuse stale execution evidence")
    receipt = dict(status="FAIL", phase="PREFLIGHT", full_matrix_accepted=False, release_accepted=False,
                   started_at=datetime.now(timezone.utc).isoformat())
    try:
        execute(args, receipt)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    if receipt.get("native_build_succeeded"):
        try:
            receipt["compiled_products"] = shared.capture_products(args.derived.resolve(), args.evidence,
                receipt["source_sha"], receipt["native_build_flags"])
        except Exception as error:
            receipt["compiled_products"] = dict(status="CAPTURE_FAILED_NO_BUILD_REUSE_ALLOWED", error=str(error))
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    shared.write(args.evidence / "execution.json", receipt)
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
