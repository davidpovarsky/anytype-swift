"""Finite evidence from the two unchanged, published Heart editor UI methods.

The original F stage owns execution/results. Typed intermediate observations
remain UI_STATE_ONLY; distinct-process cold UI readback is a separate claim.
No process, product, native API or selection setter is provided here.
"""
from __future__ import annotations

from pathlib import Path
import plistlib
import re

TARGET = "PinkhaStage1AcceptanceUITests"
SUITE = "PinkhaStage1AcceptanceUITests"
METHODS = {
    "split-merge": SUITE + "/testMiddleSplitMergeUndoRedoAndColdReopen",
    "range-replacement": SUITE + "/testPartialRangeReplacementUndoRedoAndColdReopen",
}
KINDS = ("pinkha", "note", "page")
PHASES = {
    "split-merge": ("split", "split-undo", "split-redo", "merge", "merge-undo", "merge-redo", "split-merge-cold-readback"),
    "range-replacement": ("partial-replacement", "replacement-undo", "replacement-redo", "replacement-cold-readback"),
}
FINALS = {"split-merge": "middle-split-merge-final", "range-replacement": "partial-replacement-final"}
ALLOWANCE = 1200
SOURCE_PATH = "PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift"
SOURCE_SHA = "c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906"
ORIGINAL_BYTES = 86201
ORIGINAL_SHA = "d4ffc25ee659e03bd4dd76b7847faf4fecf343630edf094c0bc02fe060f00850"
SUFFIX_SHA = "68ad800228afbbb8520151fd9991cd68f52dd3442a5b6984e1e9c5012adc7332"
SOURCE_PROOF_PATH = "docs/validation/20261127-wave2-editor-mutations/source-proof.json"
SOURCE_PROOF_SHA = "2cd96c0ad7a2ca02708920fd85259a8429175b25ab26aa460c022e0e49572fa8"
PREFIX = "editor-mutation-"
BODY_PREFIX = "pinkha.stage1.body."
STARTUP_PREFIX = "PINKHA_UI27_STARTUP_"
FIELDS = {"schema", "phase", "documentKind", "spaceID", "objectID", "token", "appLanguage",
          "requestedDeviceLanguage", "appPID", "expectedBlocks", "observedBlocks", "startupBindingSHA256",
          "rangeEvidence", "directNativeRangeObservation", "programmaticSelectionChanges",
          "persistedColdReadback", "saveEvidence"}


def qualify_source(c, raw, proof_raw):
    c.require(len(raw) == 103720 and c.sha(raw) == SOURCE_SHA
              and c.sha(raw[:ORIGINAL_BYTES]) == ORIGINAL_SHA and c.sha(raw[ORIGINAL_BYTES:]) == SUFFIX_SHA
              and c.sha(proof_raw) == SOURCE_PROOF_SHA,
              "Exact complete published editor append and original prefix/proof required")
    proof = c.decode(proof_raw)
    c.require(proof.get("sourcePath") == SOURCE_PATH and proof.get("sourceAfterSHA256") == SOURCE_SHA
              and proof.get("sourceBeforeSHA256") == ORIGINAL_SHA and proof.get("insertionSHA256") == SUFFIX_SHA
              and proof.get("inverseRestoresEveryOriginalByte") is True
              and proof.get("nativePreparationUnchanged") is True
              and proof.get("newTestMethods") == [value.split("/")[1] for value in METHODS.values()]
              and proof.get("newXCTestMethodCount") == 2 and proof.get("documentFlows") == 6
              and proof.get("perMethodExecutionAllowanceSeconds") == ALLOWANCE,
              "The original two-method/six-flow source contract changed")
    return {"sourcePath": SOURCE_PATH, "sourceSHA256": SOURCE_SHA, "originalPrefixSHA256": ORIGINAL_SHA,
            "appendSHA256": SUFFIX_SHA, "sourceProofSHA256": SOURCE_PROOF_SHA,
            "declaredMethods": 2, "declaredCases": 2, "documentFlows": 6,
            "actualCompiledEnumerationRequired": True, "testsExecuted": 0}


def selected_methods(c, methods):
    c.require(isinstance(methods, list) and methods in ([METHODS["split-merge"]],
              [METHODS["range-replacement"]], list(METHODS.values())),
              "Only the exact single-method or ordered two-method Heart selection is supported")
    return [kind for kind, method in METHODS.items() if method in methods]


def time_budget(c, target, methods):
    selected_methods(c, methods)
    c.require(target == TARGET, "Exact original Stage1 UI target required")
    return {"default_seconds": ALLOWANCE, "maximum_seconds": ALLOWANCE,
            "method_seconds": {method: ALLOWANCE for method in methods},
            "total_method_seconds": len(methods) * ALLOWANCE,
            "scope": "PUBLISHED_HEART_EDITOR_MUTATION_METHOD_ALLOWANCES",
            "sourceSHA256": SOURCE_SHA, "originalRunUI27BudgetHelperChanged": False}


def pinned(c, ref, maximum=65536):
    c.require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}
              and re.fullmatch(r"[0-9a-f]{64}", ref.get("sha256", "")) is not None,
              "Exact raw artifact path and SHA256 required")
    path = Path(ref["path"])
    c.require(path.is_absolute() and path.resolve() == path and path.is_file() and not path.is_symlink(),
              "Artifact must be a canonical physical file")
    raw = c.raw(path, maximum)
    c.require(c.sha(raw) == ref["sha256"], "Pinned original artifact changed")
    return raw


def reference(c, path):
    return {"path": str(path), "sha256": c.sha(c.raw(path))}


def fixture_binding(c, fixture_raw, startup, udid):
    import torah_ui_profile
    fixture = c.decode(fixture_raw)
    c.require(isinstance(fixture, dict), "Original Stage1 native fixture must be an object")
    envelope = torah_ui_profile.validate_startup_environment(startup, lane="editor", expected_space=fixture.get("spaceId"))
    c.require(envelope["simulatorUDID"].lower() == udid.lower()
              and envelope["fixtureSHA256"] == c.sha(fixture_raw)
              and envelope["fixtureFilename"] == "pinkha-stage1-acceptance-state.json",
              "The actual original editor preparation/fixture must belong to this owned device")
    documents = {kind: fixture[field] for kind, field in
                 (("pinkha", "pinkhaObjectId"), ("note", "noteObjectId"), ("page", "pageObjectId"))}
    c.require(all(isinstance(value, str) and value for value in documents.values()) and len(set(documents.values())) == 3,
              "Original three distinct editor document kinds are required")
    app_language = startup["PINKHA_UI27_APP_LANGUAGE"]
    device_language = startup["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"]
    c.require(app_language in ("he", "en") and device_language in ("he", "en") and app_language != device_language,
              "Original actual opposite-device-language editor scope required")
    return {"spaceID": fixture["spaceId"], "documents": documents, "appLanguage": app_language,
            "deviceLanguage": device_language, "startupBindingSHA256": c.sha(startup[STARTUP_PREFIX + "BINDING_JSON"].encode("utf-8")),
            "fixtureSHA256": c.sha(fixture_raw), "ownedUDID": udid,
            "preparationInvocationSHA256": envelope["preparationInvocationSHA256"],
            "controllerObservedSource": envelope["sourceSHA"], "controllerObservedRunID": envelope["runID"],
            "controllerObservedRunAttempt": envelope["runAttempt"], "nativeAuthenticationClaimed": False}


def validate_metadata(c, records, selection, fixture):
    c.require(selection in METHODS and set(records) == set(KINDS), "Every selected original document flow required")
    result = {}
    for kind in KINDS:
        phases = records[kind]
        c.require(isinstance(phases, dict) and set(phases) == set(PHASES[selection]), "Exact finite phase chain required")
        first = phases[PHASES[selection][0]]
        c.require(isinstance(first, dict) and re.fullmatch(r"[0-9A-F]{8}", first.get("token", "")) is not None,
                  "Actual source-defined UUID-prefix token required")
        token = first["token"]
        guard_text, left, right = "Guard_" + token, "Left_" + token, "Right_" + token
        initial = first.get("observedBlocks")
        count = 3 if selection == "split-merge" else 2
        c.require(isinstance(initial, dict) and len(initial) == count
                  and all(isinstance(key, str) and key.startswith(BODY_PREFIX) and len(key) > len(BODY_PREFIX)
                          and isinstance(value, str) for key, value in initial.items()),
                  "Exact observed initial block identities and text required")
        def block_id(text):
            matches = [key for key, value in initial.items() if value == text]
            c.require(len(matches) == 1, "Each original guard/target/split text must have one distinct block identity")
            return matches[0]
        guard_id = block_id(guard_text)
        if selection == "split-merge":
            target_id, second_id = block_id(left), block_id(right)
            split = {guard_id: guard_text, target_id: left, second_id: right}
            joined = {guard_id: guard_text, target_id: left + right}
            expected = {phase: split if phase in ("split", "split-redo", "merge-undo") else joined
                        for phase in PHASES[selection]}
            ranges = {"split": "INFERRED_FROM_EXACT_PREFIX_SUFFIX_AFTER_REAL_RETURN",
                      "merge": "INFERRED_FROM_EXACT_MERGE_AFTER_REAL_COMMAND_A_LEFT_BACKSPACE"}
        else:
            target_id = block_id(left + "Z" + right)
            second_id = None
            edited = {guard_id: guard_text, target_id: left + "Z" + right}
            before = {guard_id: guard_text, target_id: left + "MIDDLE" + right}
            expected = {phase: before if phase == "replacement-undo" else edited for phase in PHASES[selection]}
            ranges = {"partial-replacement": "INFERRED_FROM_EXACT_UNCHANGED_PREFIX_SUFFIX_AFTER_REAL_SHIFT_RANGE"}
        c.require(type(first.get("appPID")) is int and first["appPID"] > 0, "Actual positive warm App PID required")
        warm_pid = first["appPID"]
        for phase in PHASES[selection]:
            row, cold = phases[phase], phase == PHASES[selection][-1]
            c.require(isinstance(row, dict) and set(row) == FIELDS | ({"previousPID"} if cold else set())
                      and row["schema"] == "pinkha-heart-editor-mutation-observation-v1"
                      and row["phase"] == phase and row["documentKind"] == kind
                      and row["spaceID"] == fixture["spaceID"] and row["objectID"] == fixture["documents"][kind]
                      and row["token"] == token and row["appLanguage"] == fixture["appLanguage"]
                      and row["requestedDeviceLanguage"] == fixture["deviceLanguage"]
                      and row["startupBindingSHA256"] == fixture["startupBindingSHA256"],
                      "Observed editor phase belongs to another fixture, document, token or startup")
            c.require(row["observedBlocks"] == row["expectedBlocks"] == expected[phase]
                      and row["rangeEvidence"] == ranges.get(phase, "NO_PRE_EDIT_RANGE_CLAIM")
                      and row["directNativeRangeObservation"] is False
                      and type(row["programmaticSelectionChanges"]) is int and row["programmaticSelectionChanges"] == 0
                      and row["persistedColdReadback"] is cold
                      and row["saveEvidence"] == ("DISTINCT_COLD_PROCESS_EXACT_ID_AND_TEXT_READBACK" if cold else "UI_STATE_ONLY"),
                      "Guard/target topology, inferred range or cold-save evidence changed")
            c.require(type(row["appPID"]) is int and row["appPID"] > 0, "Actual positive observed App PID required")
            if cold:
                c.require(type(row["previousPID"]) is int and row["previousPID"] == warm_pid and row["appPID"] != warm_pid,
                          "Persisted readback requires the exact previous warm PID and a distinct actual cold PID")
            else:
                c.require(row["appPID"] == warm_pid, "Intermediate observations must stay in their original warm process")
        result[kind] = {"spaceID": fixture["spaceID"], "objectID": fixture["documents"][kind], "token": token,
                        "guardBlockID": guard_id, "targetBlockID": target_id, "splitSecondBlockID": second_id,
                        "warmPID": warm_pid, "coldPID": phases[PHASES[selection][-1]]["appPID"],
                        "intermediateEvidence": "UI_STATE_ONLY", "persistedColdUIReadback": True,
                        "nativeAPIReadbackPerformed": False, "directNativeRangeObservation": False,
                        "observations": [phases[phase] for phase in PHASES[selection]]}
    return result


def attachments(c, directory, udid, methods, fixture):
    selections = selected_methods(c, methods)
    c.require(directory.is_absolute() and directory.resolve() == directory and directory.is_dir()
              and not directory.is_symlink(), "Canonical original editor attachment directory required")
    labels = {}
    for selection in selections:
        method = METHODS[selection]
        for kind in KINDS:
            for phase in PHASES[selection]:
                for ext in (".json", ".txt", ".png"):
                    label = PREFIX + kind + "-" + phase + {".txt": "-ax", ".png": "-visual"}.get(ext, "")
                    labels[(method, label, ext)] = (selection, kind, phase, ext)
            if selection == "range-replacement":
                for ext in (".txt", ".png"):
                    label = PREFIX + kind + "-real-shift-selection" + ("-ax" if ext == ".txt" else "-visual")
                    labels[(method, label, ext)] = (selection, kind, "real-shift-selection", ext)
        for ext in (".txt", ".png"):
            label = PREFIX + FINALS[selection] + ("-ax" if ext == ".txt" else "-visual")
            labels[(method, label, ext)] = (selection, "final", "final", ext)
    raw_manifest = c.raw(directory / "manifest.json", 8 * 1024**2)
    manifest = c.decode(raw_manifest)
    c.require(isinstance(manifest, list), "Original xcresult exported manifest required")
    found, names = {}, set()
    records = {selection: {kind: {} for kind in KINDS} for selection in selections}
    for row in manifest:
        c.require(isinstance(row, dict) and isinstance(row.get("attachments", []), list), "Typed original manifest row required")
        for item in row.get("attachments", []):
            c.require(isinstance(item, dict), "Typed original attachment item required")
            human = item.get("suggestedHumanReadableName", "")
            if not isinstance(human, str) or not human.startswith(PREFIX):
                continue
            name = item.get("exportedFileName")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
                      "Editor attachment escaped its original export directory")
            ext = Path(name).suffix
            method = str(row.get("testIdentifier", "")).removeprefix(TARGET + "/").removesuffix("()")
            matches = [key for (selected, label, suffix), key in labels.items() if selected == method and suffix == ext
                       and re.fullmatch(re.escape(label) + r"(?:_[A-Za-z0-9-]+)*" + re.escape(ext), human)]
            c.require(len(matches) == 1 and method in methods and item.get("isAssociatedWithFailure") is False
                      and str(item.get("deviceId", "")).lower() == udid.lower(),
                      "Editor capture must belong to the exact successful selected method/device/phase")
            key, path = matches[0], directory / name
            c.require(key not in found and name not in names and path.resolve() == path and not path.is_symlink(),
                      "Duplicate or aliased editor observation")
            raw = c.raw(path, {".json": 65536, ".txt": 2 * 1024**2, ".png": 20 * 1024**2}[ext])
            c.require(bool(raw), "An original editor attachment is empty")
            ref = {"path": str(path), "sha256": c.sha(raw), "bytes": len(raw)}
            if ext == ".json":
                selection, kind, phase, _ = key
                records[selection][kind][phase] = c.decode(raw)
            elif ext == ".txt":
                raw.decode("utf-8")
            else:
                c.require(len(raw) >= 33 and raw[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                          and 0 < int.from_bytes(raw[16:20], "big") <= 16384
                          and 0 < int.from_bytes(raw[20:24], "big") <= 16384, "Bounded original PNG required")
                ref.update(width=int.from_bytes(raw[16:20], "big"), height=int.from_bytes(raw[20:24], "big"))
            found[key], names = ref, names | {name}
    c.require(set(found) == set(labels.values()), "Every original phase, selection and final capture is required")
    tests = {}
    for selection in selections:
        tests[METHODS[selection]] = {
            "documents": validate_metadata(c, records[selection], selection, fixture),
            "artifacts": {kind: {phase: {ext: ref for (s, k, p, ext), ref in found.items()
                                               if (s, k, p) == (selection, kind, phase)}
                                  for phase in sorted({p for s, k, p, _ in found if (s, k) == (selection, kind)})}
                          for kind in (*KINDS, "final")},
            "requiredArtifacts": 65 if selection == "split-merge" else 44,
            "declaredCases": 1, "documentFlows": 3,
        }
    return {"schema": "pinkha-heart-editor-mutation-observations-v1",
            "status": "PASS_TYPED_EDITOR_OBSERVATIONS_VISUAL_REVIEW_PENDING", "tests": tests,
            "manifest": {"path": str(directory / "manifest.json"), "sha256": c.sha(raw_manifest)},
            "artifactCount": len(found), "selectedMethodCount": len(methods), "documentFlows": 3 * len(methods),
            "directNativeRangeObservation": False, "programmaticSelectionChanges": 0,
            "nativeAPIReadbackPerformed": False, "wholeStoreAcceptance": False,
            "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}


def collect(consumer, stage_directory, udid, startup, methods, *, fixture_ref):
    """Call only after the original selected UI stage has actually passed."""
    c = consumer.shared_module
    selected_methods(c, methods)
    fixture = fixture_binding(c, pinned(c, fixture_ref), startup, udid)
    c.require(fixture["controllerObservedSource"] == consumer.binding["sourceSHA"]
              and fixture["controllerObservedRunID"] == consumer.binding["runID"]
              and fixture["controllerObservedRunAttempt"] == consumer.binding["runAttempt"],
              "The actual editor startup binding belongs to another admitted source/run")
    c.require(stage_directory.is_absolute() and stage_directory.resolve() == stage_directory,
              "Canonical original selected editor stage required")
    result_raw, invocation_raw = c.raw(stage_directory / "result.json"), c.raw(stage_directory / "invocation.json")
    result, invocation = c.decode(result_raw), c.decode(invocation_raw)
    argv = invocation.get("argv", [])
    c.require(result.get("status") == "PASS" and result.get("selected") == methods and result.get("testInvoked") is True
              and result.get("command_exit_code") == 0
              and (result.get("passed"), result.get("failed"), result.get("skipped")) == (len(methods), 0, 0)
              and result.get("originalTimeBudget") == time_budget(c, TARGET, methods)
              and invocation.get("binding") == consumer.binding
              and [value for value in argv if value.startswith("-only-testing:")]
                  == ["-only-testing:" + TARGET + "/" + method for method in methods]
              and argv.count("platform=iOS Simulator,id=" + udid) == 1
              and result.get("command", {}).get("argv") == argv
              and result["command"].get("status") == "PASS_COMMAND" and result["command"].get("exitCode") == 0
              and invocation.get("descriptorSHA256") == c.sha(c.raw(stage_directory / "bound.xctestrun"))
              and invocation.get("enumerationSHA256") == c.sha(c.raw(stage_directory / "enumeration.json")),
              "Exact original method count, descriptor, enumeration and successful command evidence required")
    for flag in ("-default-test-execution-time-allowance", "-maximum-test-execution-time-allowance"):
        c.require(argv.count(flag) == 1 and argv.index(flag) + 1 < len(argv) and argv[argv.index(flag) + 1] == str(ALLOWANCE),
                  "Exact published1200-second method allowance required")
    devices = result.get("actual_devices", [])
    c.require(len(devices) == 1 and str(devices[0].get("deviceId", "")).lower() == udid.lower()
              and devices[0].get("platform") == "iOS Simulator", "Actual selected result belongs to another owned device")
    command_directory = consumer.commands.root / (stage_directory.parent.name + "-" + stage_directory.name + "-test")
    c.require(c.decode(c.raw(command_directory / "result.json")) == result["command"]
              and b"** TEST EXECUTE SUCCEEDED **" in c.raw(command_directory / "original.log"),
              "Actual successful original command bytes are absent")
    target = plistlib.loads(c.raw(stage_directory / "bound.xctestrun"))[TARGET]
    environment = target.get("EnvironmentVariables", {})
    c.require(target.get("OnlyTestIdentifiers") == methods and all(environment.get(key) == value for key, value in startup.items())
              and not any(key.startswith("PINKHA_G02_") for key in environment),
              "Actual descriptor must preserve the complete original editor startup environment")
    proof = attachments(c, stage_directory / "private-attachments", udid, methods, fixture)
    proof.update(actualTest={"path": str(stage_directory / "result.json"), "sha256": c.sha(result_raw)},
                 invocation={"path": str(stage_directory / "invocation.json"), "sha256": c.sha(invocation_raw)},
                 fixture=fixture_ref, startupBindingSHA256=fixture["startupBindingSHA256"],
                 originalPreparationInvocationSHA256=fixture["preparationInvocationSHA256"],
                 actualUIInvocationSHA256=c.sha(invocation_raw))
    c.write(stage_directory / "heart-editor-observations.json", proof)
    return proof
