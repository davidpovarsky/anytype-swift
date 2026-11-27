"""Closed, finite handoff for the two existing NativeUI accessibility methods.

This module starts no process, changes no setting and admits no product or test.
The sole Native23 runner owns source/products, descriptor, original result,
OwnedCommands and finally restoration. These are subordinate evidence checks.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import uuid


TARGET = "PinkhaAnyNativeUITests"
SOURCE_SHA256 = "8d58c41e8907019bf67088900bb5c35843562edd669422573c1280f800500e86"
SOURCE_PROOF_SHA256 = "63cadf150de799d104d8fb769b08578b3ddad3bb05f21fba232617ef2e550cf1"
ADDITION_SHA256 = "98c68f7e1d9ab0617218ae38e290cc6ddf1842d42f41bda680001e7c752d4317"
STYLED_HELPER_SHA256 = "71c376659d34b7065d152f22c41f2ded731d4527d0231375a3e688a31e7f4f02"
RTL_HELPER_SHA256 = "58c240a703a757291822073f82d84627ac5e3fedd9a0a8daf60c961a33c384ae"
AUDIT = "testNativeLibraryAndEditorAccessibilityAuditAtRequestedContentSize"
VOICEOVER = "testNativeVoiceOverTraversalSpeaksCurrentNativeContent"
EXPANDED = "accessibility-extra-extra-extra-large"
BODY = "שלום נגישות. Native speech marker."
MARKER = "native speech marker"
PREFIX = "native-accessibility-"
FINAL_PREFIX = "PRIVATE-native-accessibility-final-"
PLANS = {
    "accessibility-audit-large": {"method": AUDIT, "contentSize": "large", "allowance": 900},
    "accessibility-audit-expanded": {"method": AUDIT, "contentSize": EXPANDED, "allowance": 900},
    "accessibility-voiceover-large": {"method": VOICEOVER, "contentSize": "large", "allowance": 900},
}
PHASES = {
    AUDIT: ("library-before-audit", "editor-before-audit", "audits-returned"),
    VOICEOVER: ("voiceover-before-enable", "voiceover-returned", "voiceover-trace"),
}
CONTEXT_KEYS = {"schema", "runID", "appSourceCommit", "uiSourceCommit", "simulatorUDID", "ownedScope",
                "method", "appLanguage", "osLanguage", "contentSize", "appearance", "deviceFamily",
                "settingsReadbackSHA256"}
OBSERVATION_KEYS = {"schema", "phase", "invocation", "runnerProcessID", "runnerSimulatorUDID",
                    "appLaunchArguments", "spaceName", "documentName", "blockIdentifier", "bodySHA256",
                    "actualOSPreferencesAuthority", "visualReview"}


def require_runtime_ready(c):
    """No JSON ready flag or arbitrary source pin can open this preparation."""
    c.require(False, "Accessibility plans are CLOSED pending a reviewed exact Native23 runner, successful products and actual admission")


def plan(c, stage):
    c.require(stage in PLANS, "Only the three finite original accessibility cells are defined")
    return dict(PLANS[stage], selector=TARGET + "/NativeLaunchTests/" + PLANS[stage]["method"],
                runtimeReady=False, originalMethodCount=1, originalLiteralCaseCount=1,
                originalCommandAllowanceSeconds=PLANS[stage]["allowance"] + 300,
                sourceSHA256=SOURCE_SHA256, originalResultAuthorityRequired=True)


def _dependencies(c):
    # Exact existing siblings are materialized by the Native23 owner. File
    # custody and command lifecycle reuse the original helpers. PNG shape uses
    # the same finite predicate, with these two methods' different exact names.
    import native_styled_observations as original
    import native_rtl_matrix as rtl
    for module, expected in ((original, STYLED_HELPER_SHA256), (rtl, RTL_HELPER_SHA256)):
        path = Path(module.__file__)
        c.require(path.is_absolute() and path.resolve() == path and not path.is_symlink()
                  and path.parent == Path(__file__).resolve().parent and c.digest(path) == expected,
                  "Exact reviewed existing Native23/RTL helper sibling required")
    return original, rtl


def _settings_helpers(c, rtl, provided):
    c.require(isinstance(provided, dict) and set(provided) == set(rtl.HELPERS),
              "The existing source-qualified RTL helper closure is required")
    first = provided["validate_device_language"]
    c.require(hasattr(first, "__code__"), "Original loaded language function required")
    path = Path(first.__code__.co_filename)
    c.require(path.is_absolute() and path.resolve() == path and len(path.parents) > 2,
              "Actual pinned original helper source path required")
    source = path.parents[2]
    for name, spec in rtl.HELPERS.items():
        c.require(hasattr(provided[name], "__code__")
                  and Path(provided[name].__code__.co_filename) == source / spec["path"],
                  "One original source-qualified helper closure required")
    # Reuse the exact existing file/declaration validator and its returned
    # functions, rather than accepting arbitrary callback implementations.
    verified, _ = rtl.original_helpers(c, source)
    return verified


def _context(c, context, udid, stage):
    spec = plan(c, stage)
    c.require(isinstance(context, dict) and set(context) == CONTEXT_KEYS
              and all(isinstance(v, str) for v in context.values()), "Exactly the original13 string context fields required")
    def valid_uuid(value):
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError, TypeError):
            return None
    c.require(context["schema"] == "native-accessibility-invocation/v1"
              and context["method"] == spec["method"] and context["contentSize"] == spec["contentSize"]
              and valid_uuid(context["runID"]) is not None and valid_uuid(context["ownedScope"]) is not None
              and valid_uuid(udid) is not None and valid_uuid(context["simulatorUDID"]) == valid_uuid(udid)
              and re.fullmatch(r"[0-9a-f]{40}", context["appSourceCommit"]) is not None
              and context["appSourceCommit"] == context["uiSourceCommit"]
              and re.fullmatch(r"[0-9a-f]{64}", context["settingsReadbackSHA256"]) is not None
              and context["appLanguage"] in ("he", "en") and context["osLanguage"] in ("he", "en")
              and context["appLanguage"] != context["osLanguage"]
              and context["appearance"] in ("light", "dark") and context["deviceFamily"] in ("iphone", "ipad"),
              "Fixed same-source, opposite-language, owned-device accessibility context required")
    return spec


def environment(c, context_raw, udid, stage):
    """Only two new descriptor/runner values; original disposable flag stays1."""
    c.require(isinstance(context_raw, bytes) and 0 < len(context_raw) <= 16384, "Bounded original raw invocation JSON required")
    _context(c, c.decode(context_raw), udid, stage)
    return {"PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_JSON": context_raw.decode("utf-8"),
            "PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_SHA256": c.sha(context_raw)}


def _command(c, original, out, label, argv, limit):
    pins = {}
    for key, suffix in (("command", ".command.json"), ("result", ".result.json"), ("processExit", ".process-exit.json")):
        _, pins[key] = original._read(c, out / (label + suffix), 2 * 1024**2)
    proof = original._command(c, out, label, pins, argv, with_log=False)
    raw, log_ref = original._read(c, out / (label + ".log"), limit, allow_empty=True)
    result = c.decode(c.raw(out / (label + ".result.json"), 2 * 1024**2))
    c.require(c.sha(raw) == result["logSHA256"], "Actual original command output changed")
    return proof, raw, log_ref


def _readbacks(c, original, out, context, settings_helpers, prefix, size):
    """Re-read actual stdout using the already-pinned original validators."""
    c.require(set(settings_helpers) == {"validate_device_language", "actual_setting", "code_carriers"},
              "Original RTL helper closure, loaded by the source-qualified owner, required")
    udid = context["simulatorUDID"]
    record, raw, log = _command(c, original, out, prefix + "-language-readback",
        ["xcrun", "simctl", "spawn", udid, "defaults", "export", "NSGlobalDomain", "-"], 1024**2)
    language = settings_helpers["validate_device_language"](raw, context["appLanguage"])
    commands = {"language": dict(record, log=log)}
    presentation = {}
    for key, expected in (("appearance", context["appearance"]), ("content_size", size)):
        record, raw, log = _command(c, original, out, prefix + "-" + key.replace("_", "-") + "-readback",
            ["xcrun", "simctl", "ui", udid, key], 4096)
        presentation[key] = settings_helpers["actual_setting"](raw.decode("utf-8"), expected, key)
        commands[key] = dict(record, log=log)
    c.require(language["app_language"] == context["appLanguage"]
              and language["device_language"] == context["osLanguage"], "Actual original opposite device language differs")
    value = {"language": language, "presentation": presentation, "ownedUDID": udid,
             "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}
    return value, commands


def readback_record(c, out, configuration, udid, stage, phase, *, settings_helpers):
    """Return a record from existing logs only; the owner retains its raw JSON."""
    original, rtl = _dependencies(c)
    spec = plan(c, stage)
    c.require(isinstance(configuration, dict) and set(configuration) == {
        "schema", "appLanguage", "deviceFamily", "deviceType", "appearance", "contentSize"
    } and configuration["schema"] == "pinkha-native-rtl-cell-v1"
        and configuration["appLanguage"] in ("he", "en")
        and configuration["deviceFamily"] in ("iphone", "ipad")
        and configuration["appearance"] in ("light", "dark") and configuration["contentSize"] == "large"
        and isinstance(configuration["deviceType"], str)
        and re.fullmatch(r"com\.apple\.CoreSimulator\.SimDeviceType\.[A-Za-z0-9-]+", configuration["deviceType"])
        and original._uuid(udid) is not None, "Actual original pinned RTL base cell and owned device required")
    c.require(phase in ("before", "after") or (phase == "restored" and spec["contentSize"] == EXPANDED),
              "Finite selected OS readback phase required")
    # The pre-record must exist before its hash enters the original13 context;
    # this API therefore uses the already-qualified base cell, with no fake pin.
    context = {"simulatorUDID": udid, "appLanguage": configuration["appLanguage"],
               "osLanguage": "en" if configuration["appLanguage"] == "he" else "he",
               "appearance": configuration["appearance"]}
    size = "large" if phase == "restored" else spec["contentSize"]
    prefix = "rtl-before" if phase == "before" and size == "large" else "accessibility-" + phase
    return _readbacks(c, original, out, context, _settings_helpers(c, rtl, settings_helpers), prefix, size)[0]


def _settings(c, original, out, context, stage, settings_helpers):
    # These checks qualify retained command custody; they do not issue commands.
    before = "rtl-before" if context["contentSize"] == "large" else "accessibility-before"
    records, intervals = {}, {}
    phases = [(before, context["contentSize"]), ("accessibility-after", context["contentSize"])]
    if context["contentSize"] == EXPANDED:
        phases = [("rtl-before", "large")] + phases + [("accessibility-restored", "large")]
    for prefix, size in phases:
        expected, commands = _readbacks(c, original, out, context, settings_helpers, prefix, size)
        raw, retained = original._read(c, out / (prefix + "-environment.json"), 16384)
        c.require(c.decode(raw) == expected, "Retained settings are not the actual original readbacks")
        if prefix == before:
            c.require(c.sha(raw) == context["settingsReadbackSHA256"], "Invocation did not bind selected pre-test settings")
        records[prefix] = {"environment": retained, "commands": commands}
        intervals[prefix] = (min(x["start"] for x in commands.values()), max(x["end"] for x in commands.values()))
    pins = {}
    for key, suffix in (("command", ".command.json"), ("result", ".result.json"), ("processExit", ".process-exit.json")):
        _, pins[key] = original._read(c, out / ("execute" + suffix), 2 * 1024**2)
    execution = original._command(c, out, "execute", pins, with_log=False)
    argv = execution["argv"]
    c.require(argv.count("-only-testing:" + TARGET + "/NativeLaunchTests/" + context["method"]) == 1
              and len([arg for arg in argv if arg.startswith("-only-testing:")]) == 1
              and "test-without-building" in argv
              and intervals[before][1] <= execution["start"] <= execution["end"] <= intervals["accessibility-after"][0],
              "Actual selected single-method execution must be between its before/after OS readbacks")
    for flag, expected in (("-destination", "platform=iOS Simulator,id=" + context["simulatorUDID"]),
                           ("-default-test-execution-time-allowance", "900"),
                           ("-maximum-test-execution-time-allowance", "900"),
                           ("-xctestrun", str(out / "Selected.xctestrun"))):
        c.require(argv.count(flag) == 1 and argv.index(flag) + 1 < len(argv)
                  and argv[argv.index(flag) + 1] == expected, "Original accessibility execution flag changed: " + flag)
    restoration = None
    if context["contentSize"] == EXPANDED:
        set_proof, _, set_log = _command(c, original, out, "accessibility-set-content-size",
            ["xcrun", "simctl", "ui", context["simulatorUDID"], "content_size", EXPANDED], 4096)
        restore_proof, _, restore_log = _command(c, original, out, "accessibility-restore-content-size",
            ["xcrun", "simctl", "ui", context["simulatorUDID"], "content_size", "large"], 4096)
        c.require(intervals["rtl-before"][1] <= set_proof["start"] <= set_proof["end"] <= intervals[before][0]
                  and intervals["accessibility-after"][1] <= restore_proof["start"] <= restore_proof["end"]
                  <= intervals["accessibility-restored"][0], "Owned expanded-setting and finally-restoration order differs")
        restoration = {"set": dict(set_proof, log=set_log), "restore": dict(restore_proof, log=restore_log)}
    return {"readbacks": records, "executionCommand": execution, "expandedSettingRestoration": restoration}


def _attachments(c, original, directory, udid, method):
    labels = []
    for phase in PHASES[method]:
        labels.extend([(PREFIX + phase, phase, "context", ".json"),
                       (PREFIX + phase + "-private-ax", phase, "ax", ".txt"),
                       (PREFIX + phase, phase, "screen", ".png")])
    if method == AUDIT:
        labels.extend((PREFIX + phase + "-audit", phase + "-audit", "audit", ".json") for phase in ("library", "editor"))
    labels.extend((FINAL_PREFIX + method + "-" + kind, "final", kind, ext)
                  for kind, ext in (("context", ".json"), ("ax", ".txt"), ("screen", ".png")))
    raw, manifest_ref = original._read(c, directory / "manifest.json", 8 * 1024**2)
    manifest = c.decode(raw)
    c.require(isinstance(manifest, list), "Original xcresult attachment manifest required")
    found, values, paths = {}, {}, set()
    for row in manifest:
        c.require(isinstance(row, dict) and isinstance(row.get("attachments", []), list), "Original typed manifest row required")
        for item in row.get("attachments", []):
            c.require(isinstance(item, dict), "Original typed attachment item required")
            human = str(item.get("suggestedHumanReadableName", ""))
            if not human.startswith((PREFIX, FINAL_PREFIX)):
                continue
            matches = [(phase, kind, ext) for label, phase, kind, ext in labels
                       if re.fullmatch(re.escape(label) + r"(?:_[A-Za-z0-9-]+)*" + re.escape(ext), human)]
            name = item.get("exportedFileName")
            test = str(row.get("testIdentifier", "")).removeprefix(TARGET + "/").removesuffix("()")
            c.require(len(matches) == 1 and isinstance(name, str) and Path(name).name == name
                      and name not in ("", ".", "..") and test == "NativeLaunchTests/" + method
                      and original._uuid(item.get("deviceId")) == original._uuid(udid)
                      and item.get("isAssociatedWithFailure") is False,
                      "Accessibility attachment must belong to the exact successful selected method/device")
            phase, kind, ext = matches[0]
            key = (phase, kind)
            c.require(Path(name).suffix == ext and key not in found and name not in paths,
                      "Duplicate, aliased or mistyped original accessibility attachment")
            limit = {"context": 1024**2, "audit": 1024**2, "ax": 131080, "screen": 20 * 1024**2}[kind]
            data, ref = original._read(c, directory / name, limit)
            if ext == ".json":
                values[key] = c.decode(data)
                c.require(isinstance(values[key], dict), "Exact named accessibility JSON object required")
            elif ext == ".txt":
                data.decode("utf-8")
            else:
                c.require(len(data) >= 33 and data[:8] == b"\x89PNG\r\n\x1a\n"
                          and data[8:16] == b"\x00\x00\x00\rIHDR"
                          and 0 < int.from_bytes(data[16:20], "big") <= 16384
                          and 0 < int.from_bytes(data[20:24], "big") <= 16384, "Actual bounded original PNG required")
                ref.update(width=int.from_bytes(data[16:20], "big"), height=int.from_bytes(data[20:24], "big"))
            found[key], paths = ref, paths | {name}
    c.require(set(found) == {(phase, kind) for _, phase, kind, _ in labels},
              "Every exact accessibility capture/audit and final private trio is required")
    return manifest_ref, found, values


def _observations(c, original, values, context):
    method = context["method"]
    scope = str(uuid.UUID(context["ownedScope"])).upper()
    expected_launch = ["--native-ui-tests", "--native-ui-test-scope", scope, "-AppleLanguages",
                       "(en,he)" if context["appLanguage"] == "en" else "(he,en)",
                       "-AppleLocale", "en_US" if context["appLanguage"] == "en" else "he_IL"]
    seen, pids, block_ids, rows = {}, set(), set(), set()
    trace_keys = {"initialVoiceOverEnabled", "enableAttempted", "enabledObserved", "disabledObserved",
                  "completedTraversal", "cleanupFailures", "trace", "maximumSearchForwardMoves", "maximumForwardMoves",
                  "maximumSpeechOperations", "traversalBudgetSeconds", "traversalElapsedSeconds", "speechMatchRule",
                  "focusedAccessibilityIdentifierObserved", "acceptanceAuthority"}
    for phase in PHASES[method]:
        value = values[(phase, "context")]
        extra = {"hierarchyRowIdentifier"} if method == AUDIT else set()
        if phase == "audits-returned":
            extra |= {"auditTypes", "acceptanceAuthority"}
        if phase == "voiceover-returned":
            extra |= {"observedUtterance", "focusedAccessibilityIdentifierObserved"}
        if phase == "voiceover-trace":
            extra |= trace_keys
        c.require(set(value) == OBSERVATION_KEYS | extra and value["schema"] == "native-accessibility-ui-observation/v1"
                  and value["phase"] == phase and value["invocation"] == context
                  and original._positive(value["runnerProcessID"])
                  and original._uuid(value["runnerSimulatorUDID"]) == original._uuid(context["simulatorUDID"])
                  and value["appLaunchArguments"] == expected_launch
                  and value["spaceName"] == "Accessibility Space " + scope[:8]
                  and value["documentName"] == "Accessibility Document " + scope[:8]
                  and original._bounded_string(value["blockIdentifier"], 4096)
                  and value["blockIdentifier"].startswith("any-native-block-")
                  and len(value["blockIdentifier"]) > len("any-native-block-")
                  and value["bodySHA256"] == c.sha(BODY.encode("utf-8"))
                  and value["actualOSPreferencesAuthority"] == "bound-controller-pre-and-post-readbacks"
                  and value["visualReview"] == "PENDING", "Actual source-defined accessibility fixture/context changed")
        if method == AUDIT:
            row = value["hierarchyRowIdentifier"]
            c.require(original._bounded_string(row, 4096) and row.startswith("any-native-hierarchy-row-")
                      and len(row) > len("any-native-hierarchy-row-"), "Actual Library object-row identity required")
            rows.add(row)
        if "acceptanceAuthority" in extra:
            c.require(value["acceptanceAuthority"] == "original-xctest-result-and-visual-review", "Original result authority changed")
        pids.add(value["runnerProcessID"]); block_ids.add(value["blockIdentifier"]); seen[phase] = value
    c.require(len(pids) == len(block_ids) == 1 and (method != AUDIT or len(rows) == 1),
              "All captures must retain the same actual runner/block/object-row identity")
    if method == AUDIT:
        c.require(seen["audits-returned"]["auditTypes"] == "all", "Original complete audit scope required")
        for phase in ("library", "editor"):
            value = values[(phase + "-audit", "audit")]
            c.require(set(value) == {"schema", "invocation", "phase", "auditTypes", "ignoredIssues", "issues"}
                      and value["schema"] == "native-accessibility-audit-observation/v1"
                      and value["invocation"] == context and value["phase"] == phase
                      and value["auditTypes"] == "all" and type(value["ignoredIssues"]) is int
                      and value["ignoredIssues"] == 0 and value["issues"] == [],
                      "Both actual all-type audits must retain zero ignored issues and zero reported issues")
    else:
        _voiceover(c, seen)
    return {"runnerProcessID": next(iter(pids)), "blockIdentifier": next(iter(block_ids)),
            "hierarchyRowIdentifier": next(iter(rows)) if rows else None,
            "fixtureBodySHA256": c.sha(BODY.encode("utf-8")), "focusedAccessibilityIdentifierObserved": False}


def _voiceover(c, seen):
    value = seen["voiceover-trace"]
    c.require(value["initialVoiceOverEnabled"] is False
              and all(value[key] is True for key in ("enableAttempted", "enabledObserved", "disabledObserved", "completedTraversal"))
              and value["cleanupFailures"] == [] and value["focusedAccessibilityIdentifierObserved"] is False
              and type(value["maximumSearchForwardMoves"]) is int and value["maximumSearchForwardMoves"] == 24
              and type(value["maximumForwardMoves"]) is int and value["maximumForwardMoves"] == 25
              and type(value["maximumSpeechOperations"]) is int and value["maximumSpeechOperations"] == 29
              and value["traversalBudgetSeconds"] == 60
              and value["speechMatchRule"] == "normalized utterance contains the fixture phrase: " + MARKER,
              "Public VoiceOver initial-disabled, enable/traversal/disable and exact finite budgets required")
    trace = value["trace"]
    c.require(isinstance(trace, list) and 5 <= len(trace) <= 29, "Only the original bounded speech trace is accepted")
    searches = len(trace) - 5
    expected = ["currentSpeech.initial"] + ["moveForward.search." + str(i) for i in range(1, searches + 1)]
    expected += ["currentSpeech.target", "moveForward.afterTarget", "moveBackward.returnToTarget", "currentSpeech.returnedTarget"]
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    spoken, prior = [], 0
    for row, action in zip(trace, expected):
        c.require(isinstance(row, dict) and set(row) == {"action", "utterance", "operationSeconds", "elapsedSeconds"}
                  and row["action"] == action and isinstance(row["utterance"], str)
                  and 0 < len(row["utterance"].encode("utf-8")) <= 16384 and row["utterance"].strip()
                  and finite(row["operationSeconds"]) and finite(row["elapsedSeconds"])
                  and prior <= row["elapsedSeconds"] <= 60
                  and row["operationSeconds"] <= row["elapsedSeconds"] - prior + 0.000001,
                  "Actual successful public speech operations must retain their original order, text and bounded timing")
        prior = row["elapsedSeconds"]
        spoken.append(" ".join(row["utterance"].lower().split()))
    c.require(all(MARKER not in speech for speech in spoken[:searches])
              and MARKER in spoken[searches] and MARKER in spoken[-4]
              and MARKER not in spoken[-3] and spoken[-3] != spoken[-4]
              and MARKER in spoken[-2] and MARKER in spoken[-1]
              and seen["voiceover-returned"]["observedUtterance"] == spoken[-1]
              and seen["voiceover-returned"]["focusedAccessibilityIdentifierObserved"] is False
              and finite(value["traversalElapsedSeconds"]) and value["traversalElapsedSeconds"] >= prior,
              "Actual fixture speech must be reached, advanced, returned and independently confirmed")


def attachments(c, directory: Path, udid: str, context: dict, stage: str, *, settings_helpers):
    """Collect only after the original sole runner qualifies its one-case result."""
    c.require(directory.is_absolute() and directory.resolve() == directory and not directory.is_symlink()
              and directory.is_dir(), "Canonical private original attachment directory required")
    original, rtl = _dependencies(c)
    spec = _context(c, context, udid, stage)
    raw, invocation = original._read(c, directory.parent / "accessibility-invocation.json", 16384)
    c.require(c.decode(raw) == context, "Raw retained original invocation differs")
    settings = _settings(c, original, directory.parent, context, stage, _settings_helpers(c, rtl, settings_helpers))
    manifest, found, values = _attachments(c, original, directory, udid, spec["method"])
    metadata = _observations(c, original, values, context)
    final = values[("final", "context")]
    c.require(set(final) == {"schema", "invocation", "caseReachedEnd", "appStateBeforeTermination", "runnerSimulatorUDID",
                             "captureRequiresCompletedOnboarding", "contentsPrivate", "captureBeforeTermination"}
              and final["schema"] == "native-accessibility-private-final/v1" and final["invocation"] == context
              and final["caseReachedEnd"] is True and original._bounded_string(final["appStateBeforeTermination"], 1024)
              and original._uuid(final["runnerSimulatorUDID"]) == original._uuid(udid)
              and final["captureRequiresCompletedOnboarding"] is False and final["contentsPrivate"] is True
              and final["captureBeforeTermination"] is True, "Original successful final private context/AX/PNG required")
    return {"schema": "native-accessibility-observation-collection/v1",
            "status": "OBSERVATIONS_MATCH_SOURCE_VISUAL_REVIEW_PENDING", "stage": stage,
            "selector": TARGET + "/NativeLaunchTests/" + spec["method"], "executionTimeAllowanceSeconds": 900,
            "invocation": invocation, "manifest": manifest, "settings": settings, "metadata": metadata,
            "phases": {phase: {kind: found[(phase, kind)] for kind in ("context", "ax", "screen")}
                       for phase in PHASES[spec["method"]]},
            "audits": {phase: found[(phase + "-audit", "audit")] for phase in ("library", "editor")}
                      if spec["method"] == AUDIT else {},
            "final": {kind: found[("final", kind)] for kind in ("context", "ax", "screen")},
            "originalResultAuthority": "Unchanged sole NativeUI runner: exact one-case XCTest, descriptor, process exit and device",
            "standaloneProductOrXCTestAcceptance": False, "visualReview": "PENDING", "physicalDevice": "NOT_RUN",
            "manualVoiceOver": "NOT_RUN", "focusedAccessibilityIdentifierObserved": False,
            "extraNativeCalls": 0, "controllerVoiceOverToggles": 0, "contentsPrivate": True}
