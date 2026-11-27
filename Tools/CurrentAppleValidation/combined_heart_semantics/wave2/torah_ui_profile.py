"""Original Torah UI selection and controller-observed startup binding.

No product admission, native preparation, simulator operation or UI execution is
performed here. Call only from the shared consumer after its common product
admission, newly owned simulator creation, original preparation PASS and exact
private-file read have succeeded. Legacy native fixture bytes stay unchanged.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess

SCHEMA = "pinkha-controller-observed-native-ui-fixture-v1"
PROVENANCE = "CONTROLLER_OWNED_SIMULATOR_AFTER_ORIGINAL_NATIVE_PREPARATION"
PREFIX = "PINKHA_UI27_STARTUP_"
UI_TARGET = "PinkhaStage1AcceptanceUITests"
UI_SOURCE_HASHES = {
    "PinkhaStage1Acceptance/Tests/AnytypeComprehensiveAcceptanceUITests.swift":
        "066d45e4ba7198c878bb457f2c2c9f6423609451f4a85ac07da4d5d3657c30ad",
    "PinkhaStage1Acceptance/Tests/PinkhaTorahQuoteAcceptanceUITests.swift":
        "66c18c084ed66baf9b58d45b094e985127e77f8b627fc924f67be7201125f219",
    "PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift":
        "61e8b2a35e96c0f6ff31cbf9f5efb81b3b40197906961186aed275f48fdeb03a",
}
LANES = {
    "inspector": {
        "suite": "AnytypeComprehensiveAcceptanceUITests",
        "methods": ["testObjectAddPropertyButtonAndPickerSearch", "testDocumentSourceSearchPresentation",
                    "testSourceChipOpensAndClosesInspector", "testDocumentSourceSearchEmptyAndClear",
                    "testInspectorShowsIndexedRelatedDocument"],
        "preparation": "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
        "fixture": "pinkha-simulator-ui27-fixture.json",
    },
    "inspector-search": {
        "suite": "AnytypeComprehensiveAcceptanceUITests",
        "methods": ["testInspectorEmbeddedSearchOpenReturnAndDocumentLink"],
        "preparation": "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
        "fixture": "pinkha-simulator-ui27-fixture.json",
    },
    "quote-drop": {
        "suite": "PinkhaTorahQuoteAcceptanceUITests",
        "methods": ["testNativeQuoteUndoRedoDragAndRelaunch"],
        "preparation": "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
        "fixture": "pinkha-simulator-ui27-fixture.json",
    },
    "properties": {
        "suite": "PinkhaNativeDerivedAcceptanceUITests",
        "methods": ["testNativePropertiesPickerChipsSetMembershipAndRelaunch", "testSourceHeaderSelectionAndOverflow",
                    "testUniversalPageNoteCustomPropertiesAndMixedSet"],
        "preparation": "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
        "fixture": "pinkha-native-derived-ui-fixture.json",
    },
    "properties-set": {
        "suite": "PinkhaNativeDerivedAcceptanceUITests",
        "methods": ["testRemainingNativeSourceFilterEditing", "testRemainingUniversalTypePickersAndMixedSet"],
        "preparation": "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
        "fixture": "pinkha-native-derived-ui-fixture.json",
    },
    "canonical-properties": {
        "suite": "PinkhaTorahPropertiesAcceptanceUITests",
        "methods": ["testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes"],
        "preparation": "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
        "fixture": "pinkha-stage1-acceptance-state.json",
    },
}
EXPECTED = {
    "SOURCE_SHA": "sourceSHA", "RUN_ID": "runID", "RUN_ATTEMPT": "runAttempt", "TOKEN": "token",
    "SIMULATOR_UDID": "simulatorUDID", "LANE": "lane", "ADMISSION_SHA256": "admissionSHA256",
    "PREPARATION_SHA256": "preparationReceiptSHA256", "INVOCATION_SHA256": "preparationInvocationSHA256",
    "CANONICAL_CONSOLE_SHA256": "canonicalPreparationConsoleSHA256",
    "OWNED_SIMULATOR_SHA256": "ownedSimulatorReceiptSHA256", "FIXTURE_SHA256": "fixtureSHA256",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def decode(value):
    def unique(rows):
        result = {}
        for key, item in rows:
            require(key not in result, "Duplicate JSON key")
            result[key] = item
        return result
    return json.loads(value, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def inspect_original_lanes(original):
    for lane, specification in LANES.items():
        require(all(original.LANES[lane].get(key) == value for key, value in specification.items()),
                "Original Torah lane changed: " + lane)
    methods = [spec["suite"] + "/" + name for spec in LANES.values() for name in spec["methods"]]
    require(len(methods) == len(set(methods)) == 13, "Original thirteen UI methods required")
    return {"methods": methods, "ui_method_count": 13, "native_preparation_count": 6,
            "properties_set_postflight_count": 1, "tests_executed": 0}


def reviewed_ui_sources(app, *, source_commit):
    """Additive source check; the common qualifier owns actual UI compilation."""
    app = Path(app)
    require(re.fullmatch(r"[0-9a-f]{40}", source_commit or "") is not None, "Exact admitted source commit required")
    require(subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"]).decode().strip() == source_commit,
            "UI source checkout differs from admitted producer")
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    for relative, expected in UI_SOURCE_HASHES.items():
        candidates = [name for name in tracked if name.casefold() == relative.casefold()]
        selected = app / relative
        require(len(candidates) == 1 and selected.is_file() and not selected.is_symlink()
                and selected.resolve().is_relative_to(app.resolve()) and (app / candidates[0]).samefile(selected),
                "Exact synchronized UI source is absent or aliased: " + relative)
        require(sha(selected.read_bytes()) == expected, "Reviewed startup/UI source changed: " + relative)
    return {"source_commit": source_commit, "source_hashes": UI_SOURCE_HASHES, "tests_executed": 0,
            "compiler_admission_owner": "shared exact Wave3 producer qualifier"}


def validate_startup_environment(environment, *, lane, expected_space):
    """Portable binding controls; Swift independently checks it before Continue."""
    require(lane in LANES and environment.get("PINKHA_NATIVE_UI_DISPOSABLE") == "1", "Unsupported or non-disposable UI lane")
    raw = environment.get(PREFIX + "BINDING_JSON", "").encode("utf-8")
    require(0 < len(raw) <= 262144, "Missing or oversized startup binding")
    value = decode(raw)
    require(value.get("schema") == SCHEMA and value.get("provenance") == PROVENANCE and value.get("lane") == lane,
            "Startup provenance or lane differs")
    require(all(environment.get(PREFIX + suffix) == value.get(key) for suffix, key in EXPECTED.items()),
            "Startup controller environment differs")
    for key, pattern in {"sourceSHA": r"[0-9a-f]{40}", "runID": r"[0-9]+", "runAttempt": r"[0-9]+",
                         "token": r"[0-9a-f]{32}", "simulatorUDID": r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"}.items():
        require(re.fullmatch(pattern, value.get(key, "")) is not None, "Invalid startup identity: " + key)
    for key in ("admissionSHA256", "preparationReceiptSHA256", "preparationInvocationSHA256",
                "ownedSimulatorReceiptSHA256", "fixtureSHA256"):
        require(re.fullmatch(r"[0-9a-f]{64}", value.get(key, "")) is not None, "Missing evidence hash: " + key)
    spec = LANES[lane]
    require(value.get("fixtureFilename") == spec["fixture"] and value.get("preparationIdentifier") == spec["preparation"],
            "Original native fixture or preparation changed")
    fixture_raw = base64.b64decode(value.get("fixtureBase64", ""), validate=True)
    require(0 < len(fixture_raw) <= 65536 and sha(fixture_raw) == value["fixtureSHA256"], "Original native fixture bytes changed")
    fixture = decode(fixture_raw)
    require(isinstance(fixture, dict) and isinstance(expected_space, str) and expected_space
            and fixture.get("spaceId") == expected_space, "Original fixture belongs to another Space")
    selected = value.get("uiEnvironment")
    require(isinstance(selected, dict) and selected and all(isinstance(k, str) and isinstance(v, str)
            and not k.startswith(PREFIX) and environment.get(k) == v for k, v in selected.items()),
            "Original UI fixture environment changed")
    require(selected.get("PINKHA_NATIVE_UI_DISPOSABLE") == "1" and selected.get("PINKHA_UI27_APP_LANGUAGE") == "en"
            and selected.get("PINKHA_UI27_SELECTION_SCOPE") == "WAVE15_ACCEPTANCE", "Original English disposable scope required")
    if lane == "canonical-properties":
        require(re.fullmatch(r"[0-9a-f]{64}", value.get("canonicalPreparationConsoleSHA256", "")) is not None,
                "Original canonical preparation console evidence is missing")
        require(selected.get("PINKHA_PROPERTIES_SPACE_ID") == expected_space
                and selected.get("PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED") == "1", "Canonical native fixture Space differs")
        ids = [selected.get("PINKHA_PROPERTIES_" + role + "_ID") for role in ("CHIDDUSH", "ARTICLE", "RESEARCH")]
        require(all(isinstance(i, str) and i for i in ids) and len(set(ids)) == 3, "Three distinct original writing documents required")
    else:
        require(value.get("canonicalPreparationConsoleSHA256") == "", "Unexpected canonical preparation console")
        require(decode(selected.get("PINKHA_NATIVE_UI_FIXTURE_JSON", "null")) == fixture, "UI and original native fixture IDs differ")
    if lane in {"inspector", "inspector-search"}:
        require(re.fullmatch(r"[1-9][0-9]*", selected.get("PINKHA_UI27_EXPECTED_APP_PID", "")) is not None,
                "Mapped Inspector prelaunch PID is missing")
    return value


def startup_environment(*, lane, fixture_raw, ui_environment, preparation_raw, invocation_raw,
                        admission_raw, owned_simulator_raw, binding, udid, token, code_carriers_sha256,
                        canonical_console_raw=None):
    """Build a binding only from the shared consumer's preserved original bytes.

    admission_raw is the exact admitted input, not a new product-admission
    mechanism. Call this after admit_and_clone_products, create, stage(PASS),
    read_private, and (for Inspector) real prelaunch mapping have all succeeded.
    """
    require(lane in LANES, "Only the six original Torah UI lanes are supported")
    spec = LANES[lane]
    require(isinstance(fixture_raw, bytes) and 0 < len(fixture_raw) <= 65536, "Original bounded fixture bytes required")
    admission, prepared, invocation, owned = map(decode, (admission_raw, preparation_raw, invocation_raw, owned_simulator_raw))
    require(admission.get("schema") == "pinkha-combined-host-acceptance-admission-v1"
            and admission.get("executionEnvironment") == "SentinelX-owned-Mac"
            and admission.get("sourceCommit") == binding.get("sourceSHA") and admission.get("appLanguage") == "en",
            "Original admitted source and English UI required")
    require(invocation.get("binding") == binding and invocation.get("argv", []).count("platform=iOS Simulator,id=" + udid) == 1
            and invocation["argv"].count("-only-testing:AnytypeTests/" + spec["preparation"] + "()") == 1,
            "Original successful preparation was not bound to this source/run/owned simulator")
    require(prepared.get("status") == "PASS" and prepared.get("testInvoked") is True
            and prepared.get("selected") == [spec["preparation"]] and prepared.get("command_exit_code") == 0
            and (prepared.get("passed"), prepared.get("failed"), prepared.get("skipped")) == (1, 0, 0),
            "Exactly one original successful preparation is required")
    devices = prepared.get("actual_devices", [])
    require(len(devices) == 1 and devices[0].get("deviceId", "").lower() == udid.lower()
            and devices[0].get("platform") == "iOS Simulator", "Preparation ran on a different device")
    require(re.fullmatch(r"[0-9a-f]{64}", code_carriers_sha256 or "") is not None
            and prepared.get("installedOriginalCode", {}).get("codeCarriersSHA256") == code_carriers_sha256,
            "Preparation did not preserve the admitted original executable bytes")
    require(owned.get("udid") == udid and owned.get("name") == "F-Combined-" + binding["nonce"] + "-" + lane
            and owned.get("deviceType") == admission.get("deviceType")
            and owned.get("deviceFamily") == admission.get("deviceFamily"), "Fresh owned simulator receipt differs")
    require(not any(key.startswith(PREFIX) for key in ui_environment), "Startup binding may not replace prior evidence")
    require(ui_environment.get("PINKHA_NATIVE_UI_DISPOSABLE") == "1" or
            (lane == "canonical-properties" and ui_environment.get("PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED") == "1"),
            "Original fixture did not confirm disposable native or isolated canonical scope")
    ui_environment = dict(ui_environment, PINKHA_NATIVE_UI_DISPOSABLE="1")
    console_sha = ""
    if lane == "canonical-properties":
        # The three writing IDs come from the actual native console marker, not
        # the separate Stage1 editor fixture. The caller also retains and invokes
        # original.property_environment on this exact log, without rewriting it.
        require(isinstance(canonical_console_raw, bytes) and canonical_console_raw, "Original canonical console is missing")
        marker = "PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON "
        observed = {}
        for line in canonical_console_raw.decode("utf-8", errors="replace").splitlines():
            if marker in line:
                value = decode(line.split(marker, 1)[1].strip())
                observed[encode(value)] = value
        require(len(observed) == 1, "Exactly one actual canonical property console fixture required")
        native_environment = next(iter(observed.values()))
        required = {"PINKHA_PROPERTIES_" + suffix for suffix in (
            "SPACE_ID", "ISOLATED_SPACE_CONFIRMED", "CHIDDUSH_ID", "ARTICLE_ID", "RESEARCH_ID", "NATIVE_PROPERTY_LABELS")}
        require(isinstance(native_environment, dict) and required <= native_environment.keys()
                and all(isinstance(value, str) and ui_environment.get(key) == value for key, value in native_environment.items()),
                "Canonical writing IDs/environment differ from the actual native preparation console")
        console_sha = sha(canonical_console_raw)
    else:
        require(canonical_console_raw is None, "Canonical console supplied to another lane")
    envelope = dict(schema=SCHEMA, provenance=PROVENANCE, lane=lane, sourceSHA=binding["sourceSHA"],
                    runID=binding["runID"], runAttempt=binding["runAttempt"], token=token, simulatorUDID=udid,
                    admissionSHA256=sha(admission_raw), preparationReceiptSHA256=sha(preparation_raw),
                    preparationInvocationSHA256=sha(invocation_raw), ownedSimulatorReceiptSHA256=sha(owned_simulator_raw),
                    canonicalPreparationConsoleSHA256=console_sha,
                    preparationIdentifier=spec["preparation"], fixtureFilename=spec["fixture"],
                    fixtureSHA256=sha(fixture_raw), fixtureBase64=base64.b64encode(fixture_raw).decode("ascii"),
                    uiEnvironment=ui_environment)
    result = {**ui_environment, PREFIX + "BINDING_JSON": encode(envelope).decode("utf-8"),
              **{PREFIX + suffix: envelope[key] for suffix, key in EXPECTED.items()}}
    validate_startup_environment(result, lane=lane, expected_space=decode(fixture_raw).get("spaceId"))
    return result
