"""Strict App13/new-UI pairing for one opted-in original fresh-account Warning."""
from pathlib import Path
import copy
import json
import subprocess

BASE = "e540cd7e01b497f1b3173ae2e68b43ade0b00b6f"
CHANGE = "19307349e0ef469e7d4637132ada529072e1a0c0"
FILE = "PinkhaStage1Acceptance/Tests/HeartSourceCaptureAcceptanceUITests.swift"
BEFORE = "272dd5ce3620eafc4a1411f51f38d799041a0f535a46cafc97f6972c26407727"
AFTER = "c9f5a63f49c2f1a73232d05c0a6238109b4f5f1fcf0ddf699f0d68d24e1faff0"
GENERATOR = "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
GENERATOR_COMMIT = "0b9c5d75fec8fa4f4e17266010f7d79a47c08b87"
BUILDER = "9a97c6890d759cd47ac8a3ad68e970b89d7aa9ec843cb1fd64b794cfad41f5e8"
PROFILE = "original-heart-app13-fresh-capture-warning-193073-v1"
STATUS = "PASS_APP13_UI_ONLY_FRESH_CAPTURE_WARNING_NOT_ACCEPTANCE"


PRODUCER = "9dd4ff92984d0411f77ef1e62ae0e1d010790373b2da0f911b3b0e38ca7c4e43"
ORIGINAL_UI_COPY = "8e37c07393a6079afc9dacd871ddb9cc2ea9a31ec612afe64e2fd804b90f52cf"


def admit_original_ui_copy(c, admission, producer, source):
    c.require(admission["producerReceipt"]["sha256"] == PRODUCER,
              "Exact original App13 receipt required")
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
    c.require(c.sha(before) == BEFORE and c.sha(after) == AFTER, "Exact App13/reviewed fresh Warning source required")
    raw = c.raw(Path(__file__).with_name("fresh-warning-ui-source-identity.json"))
    c.require(c.sha(raw) == "9a1f895e49fbec4f6f81e3dbcbf20a9ced2c75ac5a8073c5be1cc994598c628f", "Exact reviewed full-file inverse required")
    identity = c.decode(raw)
    c.require(identity["schema"] == "pinkha-exact-heart-capture-fresh-warning-delta-v1"
              and identity["baseAppCommit"] == identity["soleParent"] == BASE
              and identity["uiChangeCommit"] == CHANGE and identity["file"] == FILE
              and identity["beforeSHA256"] == BEFORE and identity["afterSHA256"] == AFTER
              and identity["originalOutcomeAssertionsChanged"] is False
              and identity["captureAndCloseAssertionsPreserved"] is True
              and identity["normalUIWarningOnly"] is True
              and identity["appChanges"] == identity["nativeChanges"] == 0,
              "Original capture/close assertions and sole-parent source authority must remain exact")
    before_lines, after_lines = before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True)
    restored = after_lines[:]
    for part in reversed(identity["segments"]):
        i, j, k, l = (part[key] for key in ("beforeLineStart", "beforeLineEnd", "afterLineStart", "afterLineEnd"))
        c.require("".join(before_lines[i:j]) == part["removedBytes"]
                  and "".join(after_lines[k:l]) == part["addedBytes"], "Exact reviewed source hunk differs")
        restored[k:l] = part["removedBytes"].splitlines(keepends=True)
    c.require("".join(restored).encode() == before, "Inverse must restore the complete original C UI file")
    pairs = identity["all12OriginalUISources"]
    c.require(len(pairs) == 12 and pairs[FILE] == {"beforeSHA256": BEFORE, "afterSHA256": AFTER}
              and all(v["beforeSHA256"] == v["afterSHA256"] for key, v in pairs.items() if key != FILE),
              "All eleven unrelated original UI files must remain byte-identical")
    return {"beforeSHA256": BEFORE, "afterSHA256": AFTER, "inverseDeltaRestoresEntireOriginalFile": True,
            "originalOutcomeAssertionsChanged": False, "appSourcesChanged": 0,
            "captureAndCloseAssertionsPreserved": True, "explicitFreshAccountOptInRequired": True,
            "identitySHA256": c.sha(raw)}


def qualify(c, admission, original_source, original_producer):
    row = admission["freshWarningUIOverride"]
    c.require(admission.get("schema") == "pinkha-combined-heart-semantics-admission-v1"
              and admission["sourceCommit"] == BASE and row.get("profile") == PROFILE,
              "One explicit App13/fresh-account Warning UI-only pairing required")
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
              and receipt.get("uiSourceComposition") == "original12files-plus-exact-fresh-account-warning-delta",
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
                  "Original app/UI base source differs from exact App13")
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
              and b"** TEST BUILD SUCCEEDED **" in log and b"HeartSourceCaptureAcceptanceUITests.swift" in log,
              "Original new helper compilation and successful full UI stdout required")
    products = admission["products"]["ui"]
    manifest = c.decode(c.pinned(products["manifest"]))
    c.require(products["root"] == receipt["productsRoot"]
              and products["manifest"]["sha256"] == receipt["productsManifestSHA256"]
              and c.inventory(Path(products["root"])) == manifest
              and products["descriptorSHA256"] == receipt["descriptorSHA256"]
              and products["descriptorRelativePath"] == "PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun"
              and products["originalSelection"] == [], "Original independent complete UI Products differ")
    return {"status": "PASS_EXACT_UI_ONLY_FRESH_WARNING_SOURCE_AND_PRODUCTS", "appSourceCommit": BASE,
            "uiTestChangeCommit": CHANGE, "uiReceiptSHA256": c.sha(receipt_raw), "sourceDelta": delta,
            "actualTestsExecutedByThisQualification": 0, "appRebuilds": 0}

