"""Finite observations from the unchanged published G03 UI method.

The original Consumer.stage owns XCTest selection, execution and acceptance.
This helper binds its actual successful stage to four typed UI observations;
it never launches a process, admits a product or claims native persistence.
"""
from __future__ import annotations

from pathlib import Path
import plistlib
import re

TARGET = "PinkhaStage1AcceptanceUITests"
SUITE = "PinkhaTorahSourceOverflowAcceptanceUITests"
METHOD = SUITE + "/testHiddenSourceSelectionOpensExactReferenceAndReturnsToDocument"
ALLOWANCE = 480
PHASES = ("menu-choice", "selected-reference", "reader-content", "returned-document")
PREFIX = "PINKHA_UI27_STARTUP_"
ATTACHMENT_PREFIX = "source-overflow-"
CONTROLLER_KEYS = (
    "SOURCE_SHA", "RUN_ID", "RUN_ATTEMPT", "SIMULATOR_UDID", "LANE", "ADMISSION_SHA256",
    "PREPARATION_SHA256", "INVOCATION_SHA256", "OWNED_SIMULATOR_SHA256", "FIXTURE_SHA256",
)
SOURCE_PATH = "PinkhaStage1Acceptance/Tests/AnytypeComprehensiveAcceptanceUITests.swift"
SOURCE_SHA = "d7e512cb695695ea88e14bf8527d0051aeb9b315e40a7a52289a8f0b0323d6f3"
ORIGINAL_BYTES = 28068
ORIGINAL_SHA = "066d45e4ba7198c878bb457f2c2c9f6423609451f4a85ac07da4d5d3657c30ad"
OVERFLOW_BYTES = 15288
OVERFLOW_SHA = "f9f932463270a6e417e05ddd5819307d2ace8d5bc70bb4e7c0c0bbe8806283aa"
OVERFLOW_FULL_SHA = "e56a5f6839c9426bb0e70b274a3eaafbc3f850bc6343355bed92538723a28bb9"
WORD_SUFFIX_SHA = "fe889e034c5ffe1a3b30e06b4915cbbc7381a8517fa4471d1dd8a3e7570c09e9"


def qualify_source(c, raw):
    boundary = ORIGINAL_BYTES + OVERFLOW_BYTES
    c.require(isinstance(raw, bytes) and len(raw) == 78853 and c.sha(raw) == SOURCE_SHA
              and c.sha(raw[:ORIGINAL_BYTES]) == ORIGINAL_SHA
              and c.sha(raw[ORIGINAL_BYTES:boundary]) == OVERFLOW_SHA
              and c.sha(raw[:boundary]) == OVERFLOW_FULL_SHA
              and c.sha(raw[boundary:]) == WORD_SUFFIX_SHA,
              "Only the exact published original/G03/G02 source append chain is eligible")
    return {"sourcePath": SOURCE_PATH, "sourceSHA256": SOURCE_SHA,
            "originalBytes": ORIGINAL_BYTES, "originalSHA256": ORIGINAL_SHA,
            "overflowSuffixSHA256": OVERFLOW_SHA, "wordSuffixSHA256": WORD_SUFFIX_SHA,
            "selector": TARGET + "/" + METHOD, "declaredMethods": 1,
            "declaredCases": 1, "compiledEnumeration": "REQUIRED_FROM_ORIGINAL_STAGE"}


def pinned(c, ref, maximum=65536):
    c.require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}
              and re.fullmatch(r"[0-9a-f]{64}", ref.get("sha256", "")) is not None,
              "One exact raw artifact path and SHA256 required")
    path = Path(ref["path"])
    c.require(path.is_absolute() and path.resolve() == path and path.is_file() and not path.is_symlink(),
              "Artifact must be a canonical physical file")
    raw = c.raw(path, maximum)
    c.require(c.sha(raw) == ref["sha256"], "Original pinned artifact bytes changed")
    return raw


def reference(c, path):
    return {"path": str(path), "sha256": c.sha(c.raw(path))}


def fixture_binding(c, fixture_raw, startup_environment, udid):
    import torah_ui_profile
    fixture = c.decode(fixture_raw)
    c.require(isinstance(fixture, dict), "Original native fixture must be an object")
    torah_ui_profile.validate_startup_environment(startup_environment, lane="properties",
                                                   expected_space=fixture.get("spaceId"))
    controller = {key: startup_environment.get(PREFIX + key) for key in CONTROLLER_KEYS}
    c.require(controller["SIMULATOR_UDID"].lower() == udid.lower()
              and controller["LANE"] == "properties"
              and controller["FIXTURE_SHA256"] == c.sha(fixture_raw)
              and c.decode(startup_environment["PINKHA_NATIVE_UI_FIXTURE_JSON"]) == fixture
              and startup_environment["PINKHA_UI27_APP_LANGUAGE"] == "en",
              "G03 must consume the actual original Properties fixture and English owned simulator")
    c.require(all(isinstance(fixture.get(k), str) and fixture[k]
                  for k in ("spaceId", "manySourcesDocument")), "Original Space and twelve-source document required")
    headers = fixture.get("sourceHeaderCases")
    c.require(isinstance(headers, list) and all(isinstance(row, dict) for row in headers),
              "Original native source-header cases required")
    selected = [row for row in headers if type(row.get("count")) is int and row["count"] == 12]
    expected = {"Genesis 2:" + str(number) for number in range(1, 13)}
    c.require(len(selected) == 1 and selected[0].get("objectId") == fixture["manySourcesDocument"]
              and isinstance(selected[0].get("labels"), list) and len(selected[0]["labels"]) == 12
              and all(isinstance(label, str) for label in selected[0]["labels"])
              and set(selected[0]["labels"]) == expected,
              "Only the original distinct twelve canonical references can establish hidden selection")
    return fixture, controller


def validate_metadata(c, records, fixture, controller):
    c.require(set(records) == set(PHASES), "All four exact G03 observations required")
    fields = {"schema", "phase", "spaceID", "objectID", "controllerProvenance", "controller",
              "selectedReference", "visibleBefore", "hiddenReferences", "observedMenu",
              "observedSelectedHeading", "readerIdentifier", "readerText", "visibleAfter",
              "associationMutationRequestedByThisCase", "evidenceScope"}
    expected = {"Genesis 2:" + str(number) for number in range(1, 13)}
    baseline = records[PHASES[0]]
    c.require(isinstance(baseline, dict), "Typed first G03 observation required")
    before = baseline.get("visibleBefore")
    c.require(isinstance(before, dict) and len(before) == 2
              and all(isinstance(key, str) and key.startswith("torah-document-source-chip-")
                      and len(key) > len("torah-document-source-chip-") for key in before)
              and all(isinstance(value, str) for value in before.values())
              and len(set(before.values())) == 2 and set(before.values()) <= expected,
              "Two distinct original visible source chip identities and labels required")
    hidden = sorted(expected - set(before.values()))
    selected = baseline.get("selectedReference")
    c.require(isinstance(selected, str) and selected in hidden, "Selected reference must be one of the hidden ten")
    for phase in PHASES:
        row = records[phase]
        c.require(isinstance(row, dict) and set(row) == fields
                  and row.get("schema") == "pinkha-source-overflow-ui-observation-v1"
                  and row.get("phase") == phase
                  and row.get("spaceID") == fixture["spaceId"]
                  and row.get("objectID") == fixture["manySourcesDocument"]
                  and row.get("controllerProvenance") == "CONTROLLER_OWNED_SIMULATOR_AFTER_ORIGINAL_NATIVE_PREPARATION"
                  and row.get("controller") == controller
                  and row.get("associationMutationRequestedByThisCase") is False
                  and row.get("evidenceScope") == "OBSERVED_UI_ONLY",
                  "G03 observation source/run/fixture/controller scope changed")
        c.require(row["visibleBefore"] == before and row["hiddenReferences"] == hidden
                  and row["observedMenu"] == hidden and row["selectedReference"] == selected,
                  "G03 lost or substituted the original hidden/visible source selection")
        c.require(row["observedSelectedHeading"] == ("" if phase == "menu-choice" else selected),
                  "Exact selected Inspector heading must precede the full reader")
        if phase == "reader-content":
            text = row["readerText"]
            c.require(row["readerIdentifier"] == "torah-reader-segment-" + selected
                      and isinstance(text, str) and text == text.strip() and bool(text) and text != selected,
                      "The selected full reader must contain actual text for the same exact segment")
        else:
            c.require(row["readerIdentifier"] == row["readerText"] == "",
                      "A different phase cannot supply reader-content evidence")
        c.require(row["visibleAfter"] == (before if phase == "returned-document" else {}),
                  "Returning must preserve the exact original source chip identities and labels")
    return {"spaceID": fixture["spaceId"], "objectID": fixture["manySourcesDocument"],
            "selectedReference": selected, "visibleBeforeAndAfter": before,
            "hiddenReferences": hidden, "observations": [records[phase] for phase in PHASES],
            "evidenceScope": "OBSERVED_UI_ONLY", "nativePersistenceAccepted": False}


def attachments(c, directory, udid, fixture, controller):
    c.require(directory.is_absolute() and directory.resolve() == directory and not directory.is_symlink(),
              "Canonical original G03 attachment directory required")
    manifest_raw = c.raw(directory / "manifest.json", 8 * 1024**2)
    manifest = c.decode(manifest_raw)
    c.require(isinstance(manifest, list), "Actual xcresult attachment manifest required")
    expected = {(phase, kind) for phase in PHASES for kind in (".json", ".txt", ".png")}
    expected |= {("final", ".txt"), ("final", ".png")}
    labels = {(ATTACHMENT_PREFIX + label + {".txt": "-ax", ".png": "-visual"}.get(kind, ""), kind): (label, kind)
              for label, kind in expected}
    found, names, records = {}, set(), {}
    for row in manifest:
        c.require(isinstance(row, dict) and isinstance(row.get("attachments", []), list),
                  "Typed original attachment rows required")
        for item in row.get("attachments", []):
            c.require(isinstance(item, dict), "Typed original attachment required")
            human = item.get("suggestedHumanReadableName", "")
            if not isinstance(human, str) or not human.startswith(ATTACHMENT_PREFIX):
                continue
            name = item.get("exportedFileName")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
                      "G03 attachment path escaped")
            kind = Path(name).suffix
            matches = [key for (label, ext), key in labels.items() if ext == kind
                       and re.fullmatch(re.escape(label) + r"(?:_[A-Za-z0-9-]+)*" + re.escape(ext), human)]
            test = str(row.get("testIdentifier", "")).removeprefix(TARGET + "/").removesuffix("()")
            c.require(len(matches) == 1 and test == METHOD and item.get("isAssociatedWithFailure") is False
                      and str(item.get("deviceId", "")).lower() == udid.lower(),
                      "G03 attachment belongs to another method/device/phase or failed observation")
            key, path = matches[0], directory / name
            c.require(key not in found and name not in names and path.resolve() == path and not path.is_symlink(),
                      "Duplicate or aliased G03 observation")
            raw = c.raw(path, {".json": 65536, ".txt": 2 * 1024**2, ".png": 20 * 1024**2}[kind])
            c.require(bool(raw), "Empty original G03 attachment")
            value = {"path": str(path), "sha256": c.sha(raw), "bytes": len(raw)}
            if kind == ".json":
                records[key[0]] = c.decode(raw)
            elif kind == ".png":
                c.require(len(raw) >= 33 and raw[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                          and 0 < int.from_bytes(raw[16:20], "big") <= 16384
                          and 0 < int.from_bytes(raw[20:24], "big") <= 16384,
                          "Bounded original PNG screenshot required")
                value.update(width=int.from_bytes(raw[16:20], "big"), height=int.from_bytes(raw[20:24], "big"))
            else:
                raw.decode("utf-8")
            found[key] = value
            names.add(name)
    c.require(set(found) == expected, "Every G03 phase JSON/AX/PNG and final AX/PNG must be retained")
    metadata = validate_metadata(c, records, fixture, controller)
    return {"status": "PASS_G03_UI_OBSERVATIONS_VISUAL_REVIEW_PENDING", "metadata": metadata,
            "manifest": {"path": str(directory / "manifest.json"), "sha256": c.sha(manifest_raw)},
            "artifacts": {label: {kind: found[(label, kind)] for phase, kind in sorted(found) if phase == label}
                          for label in sorted({key[0] for key in found})},
            "visualReview": "PENDING", "nativePersistenceAccepted": False, "physicalDevice": "NOT_RUN"}


def collect(consumer, stage_directory, udid, startup_environment, *, fixture_ref):
    """Call only after the unchanged original Consumer.stage returns PASS."""
    c = consumer.shared_module
    fixture_raw = pinned(c, fixture_ref)
    fixture, controller = fixture_binding(c, fixture_raw, startup_environment, udid)
    c.require(stage_directory.is_absolute() and stage_directory.resolve() == stage_directory,
              "One original actual G03 UI stage required")
    result_raw, invocation_raw = c.raw(stage_directory / "result.json"), c.raw(stage_directory / "invocation.json")
    result, invocation = c.decode(result_raw), c.decode(invocation_raw)
    argv = invocation.get("argv", [])
    c.require(result.get("status") == "PASS" and result.get("selected") == [METHOD]
              and result.get("testInvoked") is True and result.get("command_exit_code") == 0
              and (result.get("passed"), result.get("failed"), result.get("skipped")) == (1, 0, 0)
              and invocation.get("binding") == consumer.binding
              and [value for value in argv if value.startswith("-only-testing:")] == ["-only-testing:" + TARGET + "/" + METHOD]
              and argv.count("platform=iOS Simulator,id=" + udid) == 1
              and result.get("command", {}).get("argv") == argv
              and result["command"].get("status") == "PASS_COMMAND" and result["command"].get("exitCode") == 0
              and invocation.get("descriptorSHA256") == c.sha(c.raw(stage_directory / "bound.xctestrun"))
              and invocation.get("enumerationSHA256") == c.sha(c.raw(stage_directory / "enumeration.json")),
              "Exact original one-case UI execution/invocation evidence required before collection")
    for flag in ("-default-test-execution-time-allowance", "-maximum-test-execution-time-allowance"):
        c.require(argv.count(flag) == 1 and argv[argv.index(flag) + 1] == str(ALLOWANCE),
                  "Original declared G03 execution allowance differs")
    devices = result.get("actual_devices", [])
    c.require(len(devices) == 1 and str(devices[0].get("deviceId", "")).lower() == udid.lower()
              and devices[0].get("platform") == "iOS Simulator", "Original result uses a different owned device")
    command_directory = consumer.commands.root / (stage_directory.parent.name + "-" + stage_directory.name + "-test")
    c.require(c.decode(c.raw(command_directory / "result.json")) == result["command"]
              and b"** TEST EXECUTE SUCCEEDED **" in c.raw(command_directory / "original.log"),
              "Original successful UI command bytes are missing")
    target = plistlib.loads(c.raw(stage_directory / "bound.xctestrun"))[TARGET]
    environment = target.get("EnvironmentVariables", {})
    c.require(target.get("OnlyTestIdentifiers") == [METHOD]
              and all(environment.get(key) == value for key, value in startup_environment.items())
              and not any(key.startswith("PINKHA_G02_") for key in environment),
              "Actual G03 descriptor did not carry the exact original startup fixture environment")
    proof = attachments(c, stage_directory / "private-attachments", udid, fixture, controller)
    proof.update(actualTest={"path": str(stage_directory / "result.json"), "sha256": c.sha(result_raw)},
                 invocation={"path": str(stage_directory / "invocation.json"), "sha256": c.sha(invocation_raw)},
                 fixture=fixture_ref, originalPreparationInvocationSHA256=controller["INVOCATION_SHA256"],
                 actualPhaseInvocationSHA256=c.sha(invocation_raw))
    c.write(stage_directory / "g03-ui-observations.json", proof)
    return proof
