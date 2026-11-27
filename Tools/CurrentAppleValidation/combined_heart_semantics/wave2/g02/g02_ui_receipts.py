"""Finite observations from the two original G02 UI stages; launches nothing.

The shared consumer must first admit the actual App/complete UI products, run
the exact selected XCTest and preserve its original result. These checks bind
the kept attachments to that result and the original native fixture. Rendered
values are UI evidence only; the separate native baseline/postflight establishes
persisted values and actual canonical/Tag identities.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import plistlib
import re

TARGET = "PinkhaStage1AcceptanceUITests"
SUITE = "PinkhaTorahWordUnlinkAcceptanceUITests"
METHODS = {
    "seed": SUITE + "/testSeedOriginalWordUnlinkFixturesThroughProperties",
    "unlink": SUITE + "/testChangedQueryPickerCancelThenWordUnlinkAndColdReopenForAllWritingTypes",
}
ALLOWANCES = {"seed": 900, "unlink": 600}
ROLES = ("chiddush", "article", "research")
PHASES = {
    "seed": tuple("seed-" + role for role in ROLES) + ("seed-complete",),
    "unlink": tuple(prefix + "-" + role for role in ROLES
                    for prefix in ("cancel-query", "cancelled", "unlinked-warm", "cold-reopen")) + ("unlink-complete",),
}
CONTROLLER_KEYS = (
    "SOURCE_SHA", "RUN_ID", "RUN_ATTEMPT", "TOKEN", "SIMULATOR_UDID", "LANE",
    "ADMISSION_SHA256", "PREPARATION_SHA256", "INVOCATION_SHA256",
    "OWNED_SIMULATOR_SHA256", "FIXTURE_SHA256",
)
PREFIX = "PINKHA_UI27_STARTUP_"
ATTACHMENT_PREFIX = "word-unlink-"
SOURCE_PATH = "PinkhaStage1Acceptance/Tests/AnytypeComprehensiveAcceptanceUITests.swift"
SOURCE_SHA = "d7e512cb695695ea88e14bf8527d0051aeb9b315e40a7a52289a8f0b0323d6f3"
SOURCE_PROOF_PATH = "docs/validation/20261127-wave2-torah-word-unlink-ui/source-inverse.json"
SOURCE_PROOF_SHA = "044e5e138f392b8e65207f3c114a8ef38a0529ee9b4efc3a5af1c76b87ab73b6"
PREFIX_BYTES = 43356
PREFIX_SHA = "e56a5f6839c9426bb0e70b274a3eaafbc3f850bc6343355bed92538723a28bb9"
SUFFIX_SHA = "fe889e034c5ffe1a3b30e06b4915cbbc7381a8517fa4471d1dd8a3e7570c09e9"
SOURCE_PROPERTY, TOPIC_PROPERTY, WORD_PROPERTY = "מקור/ות", "נושא", "מילה / ערך"
EMPTY_WORD = "Select options"
EVIDENCE_SCOPE = "OBSERVED_UI_ONLY_NATIVE_BASELINE_AND_POSTFLIGHT_SEPARATE"
PROVENANCE = "CONTROLLER_OWNED_SIMULATOR_AFTER_ORIGINAL_NATIVE_PREPARATION"


def qualify_source(c, current, proof_raw):
    c.require(c.sha(current) == SOURCE_SHA and c.sha(proof_raw) == SOURCE_PROOF_SHA,
              "Exact published G02 UI source and inverse proof required")
    proof = c.decode(proof_raw)
    original, suffix = current[:PREFIX_BYTES], current[PREFIX_BYTES:]
    methods = re.findall(rb"^    func (test\w+)\(", current, re.M)
    old = re.findall(rb"^    func (test\w+)\(", original, re.M)
    added = [METHODS[phase].split("/")[1] for phase in ("seed", "unlink")]
    c.require(c.sha(original) == PREFIX_SHA and c.sha(suffix) == SUFFIX_SHA
              and proof.get("baseSHA256") == PREFIX_SHA and proof.get("candidateSHA256") == SOURCE_SHA
              and proof.get("appendSHA256") == SUFFIX_SHA
              and proof.get("entireOriginalAndG03PrefixByteIdentical") is True
              and proof.get("baseMethods") == [name.decode() for name in old]
              and proof.get("newMethods") == added and proof.get("newXCTestCases") == 2
              and methods == old + [name.encode() for name in added] and len(old) == 7,
              "G02 must preserve the complete original and G03 source prefix")
    return {"sourcePath": SOURCE_PATH, "sourceSHA256": SOURCE_SHA, "originalAndG03SHA256": PREFIX_SHA,
            "appendSHA256": SUFFIX_SHA, "inverseProofSHA256": SOURCE_PROOF_SHA,
            "methods": [TARGET + "/" + METHODS[p] for p in ("seed", "unlink")],
            "methodCount": 2, "caseCount": 2, "rolesPerMethod": list(ROLES),
            "AppleCompilationProvenByThisCheck": False, "XCTestExecutedByThisCheck": False}


def ui_time_budget(blueprint, selections):
    """Only these two source-pinned selectors override the original 300s default."""
    phases = [phase for phase, method in METHODS.items() if selections == [method]]
    if blueprint != TARGET or len(phases) != 1:
        raise ValueError("Only one exact G02 UI selector may use its declared allowance")
    seconds = ALLOWANCES[phases[0]]
    return {"default_seconds": seconds, "maximum_seconds": seconds,
            "method_seconds": {selections[0]: seconds}, "total_method_seconds": seconds,
            "scope": "PUBLISHED_G02_METHOD_EXECUTION_TIME_ALLOWANCE",
            "sourceSHA256": SOURCE_SHA, "originalRunUI27BudgetHelperChanged": False}


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
    torah_ui_profile.validate_startup_environment(startup_environment, lane="properties", expected_space=fixture.get("spaceId"))
    controller = {key: startup_environment.get(PREFIX + key) for key in CONTROLLER_KEYS}
    c.require(controller["SIMULATOR_UDID"].lower() == udid.lower()
              and controller["FIXTURE_SHA256"] == c.sha(fixture_raw)
              and c.decode(startup_environment["PINKHA_NATIVE_UI_FIXTURE_JSON"]) == fixture
              and startup_environment["PINKHA_UI27_APP_LANGUAGE"] == "en",
              "Original raw native fixture, semantic UI JSON, owned simulator or language differs")
    c.require(set(fixture.get("documents", {})) == set(ROLES)
              and len(set(fixture["documents"].values())) == 3
              and len({fixture.get("types", {}).get(role) for role in ROLES}) == 3
              and {SOURCE_PROPERTY, TOPIC_PROPERTY, WORD_PROPERTY} <= set(fixture.get("nativeProperties", [])),
              "The three original writing documents, Types and native property titles are required")
    for role in ROLES:
        obj, typ = fixture["documents"][role], fixture["types"][role]
        type_choice = fixture.get("typeSwitch", {}).get("types", {}).get(role, {})
        c.require(_string(obj) and _string(typ) and _string(fixture.get("names", {}).get(obj))
                  and type_choice.get("id") == typ and _string(type_choice.get("label"))
                  and _string(type_choice.get("propertyName")), "Original writing identity or Type metadata missing")
    c.require(_string(fixture.get("sourceLabel")) and _string(fixture.get("topicLabel")),
              "Real prepared Source and Topic labels required")
    return fixture, controller


def _string(value, maximum=65536):
    return isinstance(value, str) and 0 < len(value) <= maximum


def _pid(value):
    return type(value) is int and 0 < value <= 2**31 - 1


def _rows(c, rows, fixture, role, word, tag_property, tag_name):
    type_choice = fixture["typeSwitch"]["types"][role]
    expected = {SOURCE_PROPERTY: fixture["sourceLabel"], TOPIC_PROPERTY: fixture["topicLabel"],
                WORD_PROPERTY: word, tag_property: tag_name}
    c.require(type_choice["propertyName"] not in expected and isinstance(rows, dict)
              and set(rows) == set(expected) | {type_choice["propertyName"]}
              and all(rows.get(key) == value for key, value in expected.items())
              and _string(rows.get(type_choice["propertyName"]))
              and type_choice["label"] in rows[type_choice["propertyName"]],
              "Actual rendered Source/Topic/Word/Tag/native Type observations differ")


def validate_metadata(c, phase, records, fixture, controller, *, baseline=None, seed_sha=None):
    c.require(phase in PHASES and set(records) == set(PHASES[phase]), "Exact finite G02 phase set required")
    common = {"schema", "phase", "spaceID", "controller", "evidenceScope", "controllerProvenance", "observedAtUTC"}
    for label, record in records.items():
        c.require(isinstance(record, dict) and common <= record.keys()
                  and record["schema"] == "pinkha-g02-word-ui-observation-v1" and record["phase"] == label
                  and record["spaceID"] == fixture["spaceId"] and record["controller"] == controller
                  and record["evidenceScope"] == EVIDENCE_SCOPE and record["controllerProvenance"] == PROVENANCE
                  and isinstance(record["observedAtUTC"], str)
                  and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", record["observedAtUTC"]) is not None,
                  "G02 phase belongs to another fixture, controller, scope or observation")
        datetime.fromisoformat(record["observedAtUTC"].replace("Z", "+00:00"))
    completed = records[phase + "-complete"]
    c.require(isinstance(completed.get("documents"), dict) and set(completed["documents"]) == set(ROLES),
              "All three real writing documents must complete this UI stage")
    if phase == "seed":
        c.require(set(completed) == common | {"documents", "nativeIdentifiersEstablishedByThisUIStage"}
                  and completed["nativeIdentifiersEstablishedByThisUIStage"] is False,
                  "UI seed cannot establish persisted canonical or Tag identifiers")
        for role in ROLES:
            row = records["seed-" + role]
            doc = completed["documents"][role]
            expected_keys = {"objectID", "typeID", "name", "sourceLabel", "topicLabel", "wordLabel",
                             "sourceAction", "topicAction", "wordAction", "tagPropertyName", "tagName", "observedRows", "appPID"}
            c.require(set(row) == common | {"role", "document"} and row["role"] == role and row["document"] == doc
                      and set(doc) == expected_keys and doc["objectID"] == fixture["documents"][role]
                      and doc["typeID"] == fixture["types"][role] and doc["name"] == fixture["names"][doc["objectID"]]
                      and doc["sourceLabel"] == fixture["sourceLabel"] and doc["topicLabel"] == fixture["topicLabel"]
                      and _string(doc["wordLabel"]) and doc["wordLabel"].strip() == doc["wordLabel"]
                      and doc["wordLabel"] not in {EMPTY_WORD, SOURCE_PROPERTY, TOPIC_PROPERTY, WORD_PROPERTY}
                      and "torah1|" not in doc["wordLabel"] and doc["tagPropertyName"] in {"Tag", "Tags"}
                      and doc["tagName"] == "G02 " + role + " " + controller["TOKEN"][:8]
                      and _pid(doc["appPID"]), "UI seed document, actual label or process observation differs")
            c.require(all(doc[key] in {"LINKED_THROUGH_ORIGINAL_PICKER", "OBSERVED_EXISTING_SOLE_SELECTION"}
                          for key in ("sourceAction", "topicAction", "wordAction")), "Unreviewed canonical seed action")
            _rows(c, doc["observedRows"], fixture, role, doc["wordLabel"], doc["tagPropertyName"], doc["tagName"])
    else:
        c.require(isinstance(baseline, dict) and baseline.get("schema") == "pinkha-g02-word-native-ui-baseline-v1"
                  and baseline.get("spaceID") == fixture["spaceId"] and baseline.get("controller") == controller
                  and baseline.get("seedUIReceiptSHA256") == seed_sha
                  and re.fullmatch(r"[0-9a-f]{64}", baseline.get("nativeBaselineSHA256", "")) is not None
                  and set(baseline.get("documents", {})) == set(ROLES), "Actual compact native baseline is not this seed/fixture")
        c.require(set(completed) == common | {"documents", "nativeBaselineSHA256", "seedUIReceiptSHA256", "nativePersistencePostflightRequired"}
                  and completed["nativeBaselineSHA256"] == baseline["nativeBaselineSHA256"]
                  and completed["seedUIReceiptSHA256"] == seed_sha
                  and completed["nativePersistencePostflightRequired"] is True, "Native postflight binding is missing")
        for role in ROLES:
            base, doc = baseline["documents"][role], completed["documents"][role]
            c.require(base.get("objectID") == fixture["documents"][role] and base.get("typeID") == fixture["types"][role]
                      and base.get("name") == fixture["names"][fixture["documents"][role]]
                      and base.get("sourceLabel") == fixture["sourceLabel"] and base.get("topicLabel") == fixture["topicLabel"]
                      and all(_string(base.get(k)) for k in ("wordRecordID", "wordIdentity", "wordLabel", "tagID"))
                      and base.get("tagPropertyName") in {"Tag", "Tags"}
                      and base.get("tagName") == "G02 " + role + " " + controller["TOKEN"][:8],
                      "Native compact baseline carries another writing identity/value")
            c.require(set(doc) == {"objectID", "typeID", "name", "wordRecordIDFromNativeBaseline",
                                  "wordIdentityFromNativeBaseline", "tagIDFromNativeBaseline", "observedRows", "previousPID", "appPID"}
                      and all(doc[k] == base[k] for k in ("objectID", "typeID", "name"))
                      and doc["wordRecordIDFromNativeBaseline"] == base["wordRecordID"]
                      and doc["wordIdentityFromNativeBaseline"] == base["wordIdentity"]
                      and doc["tagIDFromNativeBaseline"] == base["tagID"]
                      and _pid(doc["previousPID"]) and _pid(doc["appPID"]) and doc["previousPID"] != doc["appPID"],
                      "Unlink must retain the actual native identity and reopen in a distinct App process")
            _rows(c, doc["observedRows"], fixture, role, EMPTY_WORD, base["tagPropertyName"], base["tagName"])
            query, cancelled, warm, cold = [records[p + "-" + role] for p in ("cancel-query", "cancelled", "unlinked-warm", "cold-reopen")]
            c.require(set(query) == common | {"role", "query", "wordRecordIDFromNativeBaseline", "wordIdentityFromNativeBaseline"}
                      and query["role"] == role and query["query"] == "G02 cancel " + controller["TOKEN"][:8]
                      and query["wordRecordIDFromNativeBaseline"] == base["wordRecordID"]
                      and query["wordIdentityFromNativeBaseline"] == base["wordIdentity"], "Changed-query Word identity differs")
            c.require(set(cancelled) == common | {"role", "observedRows", "wordRecordIDFromNativeBaseline", "cancelMechanism"}
                      and cancelled["role"] == role and cancelled["wordRecordIDFromNativeBaseline"] == base["wordRecordID"]
                      and cancelled["cancelMechanism"] == "DISMISS_CHANGED_QUERY_PICKER_WITHOUT_LINK_OR_UNLINK",
                      "Cancellation must close the actual changed-query picker without mutation")
            _rows(c, cancelled["observedRows"], fixture, role, base["wordLabel"], base["tagPropertyName"], base["tagName"])
            c.require(set(warm) == common | {"role", "wordRecordIDFromNativeBaseline", "wordIdentityFromNativeBaseline", "confirmationDialogExpected"}
                      and warm["role"] == role and warm["wordRecordIDFromNativeBaseline"] == base["wordRecordID"]
                      and warm["wordIdentityFromNativeBaseline"] == base["wordIdentity"] and warm["confirmationDialogExpected"] is False,
                      "Immediate Remove link must keep the exact selected Word identity")
            c.require(set(cold) == common | {"role", "document"} and cold["role"] == role and cold["document"] == doc,
                      "Complete result differs from the actual per-document cold observation")
    return {"spaceID": fixture["spaceId"], "documents": completed["documents"], "phaseOrder": list(PHASES[phase]),
            "controller": controller, "scope": EVIDENCE_SCOPE, "visualReview": "PENDING", "nativePersistenceAccepted": False}


def attachments(c, directory, udid, phase, fixture, controller, *, baseline_raw=None, seed_sha=None):
    c.require(phase in METHODS and directory.is_absolute() and directory.resolve() == directory
              and not directory.is_symlink(), "Canonical original G02 attachment directory required")
    manifest_raw = c.raw(directory / "manifest.json", 8 * 1024**2)
    manifest = c.decode(manifest_raw)
    c.require(isinstance(manifest, list), "Actual xcresult attachment manifest required")
    expected = {(label, kind) for label in PHASES[phase] for kind in (".json", ".txt", ".png")}
    expected |= {(phase + "-final", kind) for kind in (".txt", ".png")}
    if phase == "unlink": expected.add(("native-ui-baseline", ".json"))
    labels = {(ATTACHMENT_PREFIX + label + ({".txt": "-ax", ".png": "-visual"}.get(kind, "")), kind): (label, kind)
              for label, kind in expected}
    found, names, records = {}, set(), {}
    for row in manifest:
        c.require(isinstance(row, dict) and isinstance(row.get("attachments", []), list), "Typed original attachment rows required")
        for item in row.get("attachments", []):
            human = item.get("suggestedHumanReadableName", "")
            if not isinstance(human, str) or not human.startswith(ATTACHMENT_PREFIX): continue
            name = item.get("exportedFileName")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."), "G02 attachment path escaped")
            kind = Path(name).suffix
            matches = [key for (label, ext), key in labels.items() if ext == kind
                       and re.fullmatch(re.escape(label) + r"(?:_[A-Za-z0-9-]+)*" + re.escape(ext), human)]
            test = str(row.get("testIdentifier", "")).removeprefix(TARGET + "/").removesuffix("()")
            c.require(len(matches) == 1 and test == METHODS[phase] and item.get("isAssociatedWithFailure") is False
                      and str(item.get("deviceId", "")).lower() == udid.lower(), "G02 attachment belongs to another method/device/phase or failed observation")
            key, path = matches[0], directory / name
            c.require(key not in found and name not in names and path.resolve() == path and not path.is_symlink(), "Duplicate or aliased G02 observation")
            raw = c.raw(path, {".json": 65536, ".txt": 2 * 1024**2, ".png": 20 * 1024**2}[kind])
            c.require(bool(raw), "Empty original G02 attachment")
            value = {"path": str(path), "sha256": c.sha(raw), "bytes": len(raw)}
            if kind == ".json":
                if key[0] == "native-ui-baseline":
                    c.require(isinstance(baseline_raw, bytes) and raw == baseline_raw, "UI did not consume the exact actual native compact baseline bytes")
                else: records[key[0]] = c.decode(raw)
            elif kind == ".png":
                c.require(len(raw) >= 33 and raw[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                          and 0 < int.from_bytes(raw[16:20], "big") <= 16384
                          and 0 < int.from_bytes(raw[20:24], "big") <= 16384, "Bounded original PNG screenshot required")
                value.update(width=int.from_bytes(raw[16:20], "big"), height=int.from_bytes(raw[20:24], "big"))
            else: raw.decode("utf-8")
            found[key] = value; names.add(name)
    c.require(set(found) == expected, "Every G02 phase JSON/AX/PNG plus final AX/PNG must be retained")
    metadata = validate_metadata(c, phase, records, fixture, controller,
                                 baseline=c.decode(baseline_raw) if baseline_raw is not None else None, seed_sha=seed_sha)
    complete = found[(phase + "-complete", ".json")]
    return {"status": "PASS_G02_UI_OBSERVATIONS_VISUAL_AND_NATIVE_REVIEW_PENDING", "phase": phase,
            "manifest": {"path": str(directory / "manifest.json"), "sha256": c.sha(manifest_raw)},
            "completion": {key: complete[key] for key in ("path", "sha256")}, "metadata": metadata,
            "artifacts": {label: {kind: found[(label, kind)] for p, kind in sorted(found) if p == label}
                          for label in sorted({key[0] for key in found})},
            "visualReview": "PENDING", "nativePersistenceAccepted": False, "physicalDevice": "NOT_RUN"}


def collect_ui_phase(consumer, stage_directory, udid, phase, startup_environment, *, fixture_ref, baseline_ref=None, seed_ui_ref=None):
    """Call only after the original Consumer.stage returned actual PASS."""
    c = consumer.shared_module
    fixture_raw = pinned(c, fixture_ref)
    fixture, controller = fixture_binding(c, fixture_raw, startup_environment, udid)
    c.require(phase in METHODS and stage_directory.is_absolute() and stage_directory.resolve() == stage_directory,
              "One original actual G02 UI stage required")
    result_raw, invocation_raw = c.raw(stage_directory / "result.json"), c.raw(stage_directory / "invocation.json")
    result, invocation = c.decode(result_raw), c.decode(invocation_raw)
    argv = invocation.get("argv", [])
    c.require(result.get("status") == "PASS" and result.get("selected") == [METHODS[phase]]
              and result.get("testInvoked") is True and result.get("command_exit_code") == 0
              and (result.get("passed"), result.get("failed"), result.get("skipped")) == (1, 0, 0)
              and invocation.get("binding") == consumer.binding
              and [v for v in argv if v.startswith("-only-testing:")] == ["-only-testing:" + TARGET + "/" + METHODS[phase]]
              and argv.count("platform=iOS Simulator,id=" + udid) == 1
              and result.get("command", {}).get("argv") == argv
              and result["command"].get("status") == "PASS_COMMAND" and result["command"].get("exitCode") == 0
              and invocation.get("descriptorSHA256") == c.sha(c.raw(stage_directory / "bound.xctestrun"))
              and invocation.get("enumerationSHA256") == c.sha(c.raw(stage_directory / "enumeration.json")),
              "Exact original one-case UI execution/invocation evidence required before collection")
    for flag in ("-default-test-execution-time-allowance", "-maximum-test-execution-time-allowance"):
        c.require(argv.count(flag) == 1 and argv[argv.index(flag) + 1] == str(ALLOWANCES[phase]),
                  "Original declared G02 execution allowance differs")
    devices = result.get("actual_devices", [])
    c.require(len(devices) == 1 and str(devices[0].get("deviceId", "")).lower() == udid.lower()
              and devices[0].get("platform") == "iOS Simulator", "Original result uses a different owned device")
    command_directory = consumer.commands.root / (stage_directory.parent.name + "-" + stage_directory.name + "-test")
    c.require(c.decode(c.raw(command_directory / "result.json")) == result["command"]
              and b"** TEST EXECUTE SUCCEEDED **" in c.raw(command_directory / "original.log"),
              "Original successful UI command bytes are missing")
    baseline_raw = pinned(c, baseline_ref) if baseline_ref is not None else None
    seed_raw = pinned(c, seed_ui_ref) if seed_ui_ref is not None else None
    c.require((phase == "seed" and baseline_raw is None and seed_raw is None)
              or (phase == "unlink" and baseline_raw is not None and seed_raw is not None), "G02 phase handoff refs differ")
    target = plistlib.loads(c.raw(stage_directory / "bound.xctestrun"))[TARGET]
    environment = target.get("EnvironmentVariables", {})
    c.require(target.get("OnlyTestIdentifiers") == [METHODS[phase]]
              and all(environment.get(key) == value for key, value in startup_environment.items())
              and environment.get("PINKHA_G02_UI_PHASE") == phase,
              "Actual selected descriptor did not carry the original bound UI environment")
    if phase == "unlink":
        c.require(environment.get("PINKHA_G02_BASELINE_UI_JSON", "").encode("utf-8") == baseline_raw
                  and environment.get("PINKHA_G02_BASELINE_UI_SHA256") == c.sha(baseline_raw),
                  "Actual unlink descriptor did not carry the exact native compact baseline")
    else:
        c.require(not any(key.startswith("PINKHA_G02_BASELINE_") for key in environment),
                  "Seed descriptor cannot consume a prior native baseline")
    proof = attachments(c, stage_directory / "private-attachments", udid, phase, fixture, controller,
                        baseline_raw=baseline_raw, seed_sha=c.sha(seed_raw) if seed_raw is not None else None)
    proof.update(actualTest={"path": str(stage_directory / "result.json"), "sha256": c.sha(result_raw)},
                 invocation={"path": str(stage_directory / "invocation.json"), "sha256": c.sha(invocation_raw)},
                 fixture=fixture_ref, originalPreparationInvocationSHA256=controller["INVOCATION_SHA256"],
                 actualPhaseInvocationSHA256=c.sha(invocation_raw))
    c.write(stage_directory / "g02-ui-receipts.json", proof)
    return proof
