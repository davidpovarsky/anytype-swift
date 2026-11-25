"""Strict original-app/new-UI pairing for one reviewed continuation menu helper."""
from pathlib import Path
import copy
import json
import subprocess

BASE = "0c5ffc51cdeb480194fdd4d5e396a602d04d5d78"
CHANGE = "5fcc6d9b996166028ccf844ef95a5a873b3c9028"
FILE = "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift"
BEFORE = "0a56eef1eaa4a9df1bfd23d5828032792d982d3f0b12fd6719d11ceebc57a812"
AFTER = "062b9d76498da7e5d49d0dbd05442d84f5aa7e7353234fe4d27eb88645b203bd"
GENERATOR = "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
GENERATOR_COMMIT = "0b9c5d75fec8fa4f4e17266010f7d79a47c08b87"
BUILDER = "e3e45f29d5fb408adcc8361110af933886238482874e6bbbed5c14c2f3796c2d"
PROFILE = "original-heart0c5-command-a-replacement-preparation-5fcc6d-v1"
STATUS = "PASS_CURRENT_UI_ONLY_REAL_SELECT_ALL_NOT_ACCEPTANCE"


PRODUCER = "3375dd50d6855d3e75b95975ec78966ae0e5de5fb64a525fee4c0fae345fe0dc"
ORIGINAL_UI_COPY = "9b3b63424dd29e2823ab4d191be1689638933a5be5d595156c032f88c2f81975"


def admit_original_ui_copy(c, admission, producer, source):
    c.require(admission["producerReceipt"]["sha256"] == PRODUCER,
              "Exact original build12 receipt required")
    copy_path = Path(admission["producerReceipt"]["path"]).parent / "original-ui-copy.json"
    c.require(c.digest(copy_path) == ORIGINAL_UI_COPY, "Original complete UI source-copy receipt changed")
    copied = c.decode(c.raw(copy_path))
    argv = producer["ui"]["argv"]
    c.require(copied["generatorSHA256"] == GENERATOR and argv.count("-project") == 1
              and argv[argv.index("-project") + 1] == copied["generatedProject"],
              "The actual UI build did not use the original generated project")
    names = sorted(n for n in subprocess.check_output(["git", "-C", str(source), "ls-files", "-z", "PinkhaStage1Acceptance"], timeout=30).decode().split("\0") if n)
    c.require(len(names) == 12 and copied["copiedFiles"] ==
              [{"path": n, "sha256": c.digest(source / n)} for n in names],
              "All twelve actual copied UI inputs must equal the frozen original source")
    return {"receiptSHA256": ORIGINAL_UI_COPY, "generatorSHA256": GENERATOR,
            "trackedOriginalUIFiles": 12, "originalProjectCommandBound": True}


def source_delta(c, before, after):
    c.require(c.sha(before) == BEFORE and c.sha(after) == AFTER, "Exact original/replacement UI source required")
    path = Path(__file__).with_name("replacement-ui-source-identity.json")
    raw = c.raw(path)
    c.require(c.sha(raw) == "f69225dbb1b9b2cfc66db9a6f8cd0714b8975145c05b607b1d86ec183b1b9fbe",
              "Reviewed exact inverse delta identity required")
    identity = c.decode(raw)
    old, new = identity["removedBytes"].encode(), identity["addedBytes"].encode()
    c.require(identity["baseAppCommit"] == BASE and identity["file"] == FILE
              and identity["beforeSHA256"] == BEFORE and identity["afterSHA256"] == AFTER
              and before.count(old) == after.count(new) == 1 and after.replace(new, old, 1) == before,
              "Every original byte outside the real selection preparation must remain exact")
    return {"beforeSHA256": BEFORE, "afterSHA256": AFTER, "inverseDeltaRestoresEntireOriginalFile": True,
            "originalOutcomeAssertionsChanged": False, "appSourcesChanged": 0,
            "realCommandARequired": True, "passiveNativeFullRangeRequiredBeforeActualTyping": True,
            "programmaticSelectionChanges": 0, "identitySHA256": c.sha(raw)}


def qualify(c, admission, original_source, original_producer):
    row = admission["replacementSelectionUIOverride"]
    c.require(admission.get("schema") == "pinkha-combined-heart-semantics-admission-v1"
              and admission["sourceCommit"] == BASE and row.get("profile") == PROFILE,
              "One explicit original-app/source-menu UI-only pairing required")
    receipt_raw = c.pinned(row["receipt"]); receipt = c.decode(receipt_raw)
    c.require(receipt.get("status") == STATUS and receipt.get("appSourceCommit") == BASE
              and receipt.get("uiTestChangeCommit") == CHANGE and receipt.get("uiBuilds") == 1
              and all(type(receipt.get(key)) is int for key in ("uiBuilds", "appBuilds", "nativeBuilds", "testsExecuted"))
              and receipt.get("appBuilds") == receipt.get("nativeBuilds") == receipt.get("testsExecuted") == 0
              and receipt.get("originalProducerReceiptSHA256") == admission["producerReceipt"]["sha256"]
              and receipt.get("generatorSHA256") == GENERATOR and receipt.get("generatorCommit") == GENERATOR_COMMIT,
              "Actual reviewed independent complete UI build receipt required")
    c.require(receipt.get("profileSHA256") == c.digest(Path(__file__))
              and receipt.get("sameCommitForAppAndUITests") is False
              and receipt.get("uiSourceComposition") == "original12files-plus-exact-one-selection-preparation-delta",
              "Explicit original-App/changed-UI composition must remain exact")
    c.require(receipt.get("originalUICopy") == admit_original_ui_copy(c, admission, original_producer, original_source),
              "Original successful complete UI source-copy provenance differs")
    builder = c.pinned(row["builderSource"])
    c.require(c.sha(builder) == BUILDER == receipt.get("builderSHA256"),
              "Actual reviewed UI-only builder source differs")
    base_source = c.raw(original_source / FILE)
    candidate = c.pinned(row["candidateSource"])
    delta = source_delta(c, base_source, candidate)
    before = c.decode(c.pinned(row["sourceBefore"])); after = c.decode(c.pinned(row["sourceAfter"]))
    c.require(before == after and receipt.get("sourceBeforeSHA256") == row["sourceBefore"]["sha256"]
              and receipt.get("sourceAfterSHA256") == row["sourceAfter"]["sha256"], "Actual UI source changed during compilation")
    source_root = Path(receipt["uiSourceRoot"])
    c.require(c.inventory(source_root) == before, "Original UI build source changed after compilation")
    c.require(c.digest(source_root.parent / "original-ui-generator.py") == GENERATOR,
              "Actual frozen UI generator bytes differ")
    listing = receipt["projectAdmission"]
    listing_log = c.pinned(row["projectListLog"])
    listing_command = listing["command"]
    c.require(listing_command.get("argv") == ["xcodebuild", "-list", "-project",
              str(source_root / "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj"), "-json"]
              and listing_command.get("status") == "PASS_COMMAND" and listing_command.get("exitCode") == 0
              and listing_command.get("ownedGroupPresentAfterExit") is False
              and listing_command.get("cwd") == str(source_root)
              and listing_command.get("logSHA256") == c.sha(listing_log)
              and listing_command.get("logBytes") == len(listing_log)
              and c.decode(listing_log) == listing["project"]
              and listing["project"].get("project", {}).get("targets") == ["PinkhaStage1AcceptanceUITests"]
              and listing["project"]["project"].get("schemes") == ["PinkhaPrebuiltUI"],
              "Actual independent full UI-only project admission differs")
    tracked = subprocess.check_output(["git", "-C", str(original_source), "ls-files", "-z", "PinkhaStage1Acceptance"], timeout=30).decode().split("\0")
    tracked = sorted(n for n in tracked if n)
    c.require(len(tracked) == 12 and FILE in tracked and sorted(receipt["originalTrackedFiles"]) == tracked,
              "Complete original tracked UI source inventory required")
    for name in tracked:
        original = c.raw(original_source / name)
        c.require(original == subprocess.check_output(["git", "-C", str(original_source), "show", BASE + ":" + name], timeout=30),
                  "Original app/UI base source differs from exact0c5ffc51")
        c.require(receipt["originalTrackedFiles"][name] == c.sha(original), "Original UI file provenance differs")
        c.require(c.raw(source_root / name) == (candidate if name == FILE else original), "An unrelated original UI assertion/file changed")
    actual = receipt["command"]
    expected = copy.deepcopy(original_producer["ui"]["argv"])
    for flag, value in (("-project", str(source_root / "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj")),
                        ("-derivedDataPath", receipt["derivedDataRoot"]), ("-resultBundlePath", receipt["buildXCResult"])):
        c.require(expected.count(flag) == 1, "Original complete UI command schema differs")
        expected[expected.index(flag) + 1] = value
    c.require(actual.get("argv") == expected and actual.get("status") == "PASS_COMMAND" and actual.get("exitCode") == 0
              and actual.get("ownedGroupPresentAfterExit") is False and actual.get("cwd") == str(source_root),
              "Actual complete UI-only build command/outcome differs from original")
    log = c.pinned(row["buildLog"])
    c.require(actual.get("logSHA256") == c.sha(log) and actual.get("logBytes") == len(log)
              and b"** TEST BUILD SUCCEEDED **" in log and b"SemanticAnchorPage154MountedUITests.swift" in log,
              "Original new helper compilation and successful full UI stdout required")
    products = admission["products"]["ui"]
    manifest = c.decode(c.pinned(products["manifest"]))
    c.require(products["root"] == receipt["productsRoot"]
              and products["manifest"]["sha256"] == receipt["productsManifestSHA256"]
              and c.inventory(Path(products["root"])) == manifest
              and products["descriptorSHA256"] == receipt["descriptorSHA256"]
              and products["descriptorRelativePath"] == "PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun"
              and products["originalSelection"] == [], "Original independent complete UI Products differ")
    return {"status": "PASS_EXACT_UI_ONLY_SELECTION_PREPARATION_SOURCE_AND_PRODUCTS", "appSourceCommit": BASE,
            "uiTestChangeCommit": CHANGE, "uiReceiptSHA256": c.sha(receipt_raw), "sourceDelta": delta,
            "actualTestsExecutedByThisQualification": 0, "appRebuilds": 0}


def qualify_selection(c, policy, commands, evidence, private, device, fixture, binding):
    import math
    import re
    directory = evidence / "linked-ui/private-attachments"
    selector = c.STAGES["linked-ui"]
    raw, origin = policy.attachment(directory, "heart-semantic-source-replacement-selection",
                                    selector, device, maximum=65536)
    value = c.decode(raw)
    c.require(set(value) == {"protocol", "sourceSHA", "runID", "runAttempt", "nonce",
                            "selectionStartedUptime", "beforeTypingUptime", "expectedUTF16Length",
                            "expectedTextSHA256", "realCommandA", "programmaticSelectionChanges"}
              and value["protocol"] == "heart-semantic-source-real-replacement-selection-v1"
              and all(value[key] == binding[key] == fixture[key] for key in ("sourceSHA", "runID", "runAttempt", "nonce"))
              and type(value["expectedUTF16Length"]) is int and value["expectedUTF16Length"] == 6
              and value["expectedTextSHA256"] == c.sha(b"Anchor") and value["realCommandA"] is True
              and type(value["programmaticSelectionChanges"]) is int and value["programmaticSelectionChanges"] == 0,
              "Actual original-method real keyboard selection witness differs")
    start, end = value["selectionStartedUptime"], value["beforeTypingUptime"]
    c.require(all(type(x) in (int, float) and math.isfinite(x) for x in (start, end))
              and 0 < start < end and end - start <= 20,
              "A bounded actual selection-to-typing interval is required")
    ax, ax_origin = policy.attachment(directory, "heart-semantic-source-replacement-selection-ax",
                                      selector, device, maximum=256 * 1024)
    text = ax.decode()
    app_pids = set(re.findall(r"Application, [^\n]*\bpid: (\d+)", text))
    focused = re.findall(r"[^\n]*TextView,[^\n]*value: Anchor, Keyboard Focused[^\n]*", text)
    c.require(len(app_pids) == len(focused) == 1, "Exactly one focused original Anchor input and actual App PID required")
    pid = int(next(iter(app_pids)))
    observed = c.app_file(commands, device, private, "pinkha-semantic-source-entry-" + str(pid) + ".json",
                          "preserve-real-replacement-native-selection", maximum=65536)
    trace = c.decode(observed)
    c.require(trace["protocol"] == "pinkha-heart-semantic-source-entry-observation-v1"
              and trace["processID"] == pid and all(trace[key] == binding[key] for key in binding)
              and trace["capacityReached"] is False and trace["originalMountedObserverEnabled"] is False
              and trace["extraEngineCalls"] == trace["selectionChanges"] == trace["menuDismissals"]
              == trace["automaticRetries"] == 0, "Passive native input observation identity/scope differs")
    events = trace["events"]
    c.require(1 <= len(events) < 64 and all(type(e.get("uptime")) in (int, float)
              and math.isfinite(e["uptime"]) for e in events)
              and all(events[i]["uptime"] <= events[i+1]["uptime"] for i in range(len(events)-1)),
              "Original chronological untruncated native events required")
    interval = [e for e in events if start <= e["uptime"] <= end]
    selection = [e for e in interval if e["stage"] == "source-menu-input"]
    c.require(len(selection) >= 1, "Actual native full selection must be observed before typing")
    identities = {e["state"]["inputIdentity"] for e in selection}
    c.require(len(identities) == 1, "Selection observations came from different UIKit inputs")
    selected = next(iter(identities))
    states = [e["state"] for e in interval if e["state"].get("inputIdentity") == selected
              and e["uptime"] >= selection[-1]["uptime"]]
    c.require(states and all(s["firstResponder"] is True and s["windowPresent"] is True
              and s["editable"] is True and type(s["selectedLength"]) is int
              and s["selectedLength"] == 6 for s in states),
              "Full original six-unit selection was lost before actual keyboard replacement")
    c.require(len([e for e in events if e["stage"] == "source-menu-handler" and e["uptime"] < start]) == 1
              and not any(e["stage"] == "source-menu-handler" for e in interval),
              "The selection preparation unexpectedly reopened Sources")
    visual, visual_origin = policy.attachment(directory, "heart-semantic-source-replacement-selection-visual",
                                              selector, device, maximum=2 * 1024**2)
    return {"status": "PASS_REAL_KEYBOARD_SELECTION_WITH_PASSIVE_NATIVE_RANGE",
            "selectionWitnessSHA256": c.sha(raw), "nativeObservationSHA256": c.sha(observed),
            "nativeObservationBytes": len(observed), "beforeTypingAXSHA256": c.sha(ax),
            "visualSHA256": c.sha(visual), "actualAppPID": pid, "focusedInputCount": 1,
            "nativeFullRangeObservations": len(selection), "expectedUTF16Range": {"location": 0, "length": 6},
            "realCommandA": True, "programmaticSelectionChanges": 0, "extraEngineCalls": 0,
            "originalMethodOutcomeAssertionsChanged": False}
