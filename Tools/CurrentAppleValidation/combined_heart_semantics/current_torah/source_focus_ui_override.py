"""Strict original-app/new-UI pairing for one reviewed continuation menu helper."""
from pathlib import Path
import copy
import json
import subprocess

BASE = "5c05a612e4054a4adfa7f812343be6a15871cc89"
CHANGE = "719d13c258764dd6401d4e0892446b2ce6f7edfa"
FILE = "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift"
BEFORE = "ad442d34641371b44d9cab5ff63dcb8f9a7ba96eededac6f73b993634bdcef39"
AFTER = "0a56eef1eaa4a9df1bfd23d5828032792d982d3f0b12fd6719d11ceebc57a812"
GENERATOR = "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
GENERATOR_COMMIT = "0b9c5d75fec8fa4f4e17266010f7d79a47c08b87"
BUILDER = "bac04adb0fbd42adcbf0f7727a11b23447f65584a8b8060f6943e2dfbfeeedb9"
PROFILE = "original-heart5c05-double-tap-focus-preparation-719d13-v1"
STATUS = "PASS_CURRENT_UI_ONLY_RESTORED_FOCUS_NOT_ACCEPTANCE"


PRODUCER = "2ed88ba57b925a7136519374e8c687aae6a3a670dd51ba8aaddf735415a811f4"
ORIGINAL_UI_COPY = "77dbb85844c3fe95945f45011cc87754f19b2eba29f82a91f14a583f3744e239"


def admit_original_ui_copy(c, admission, producer, source):
    c.require(admission["producerReceipt"]["sha256"] == PRODUCER,
              "Exact original build10 receipt required")
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
    c.require(c.sha(before) == BEFORE and c.sha(after) == AFTER, "Exact original and focused diagnostic UI source required")
    original = b'        let input = semanticText("Anchor")\n        try tap(input)\n        input.typeKey(.rightArrow, modifierFlags: [])'
    replacement = b'        let input = semanticText("Anchor")\n        // A single tap on the marked link navigates to Sources. Use the native\n        // double tap to regain text focus before the original caret collapse\n        // and word selection. Every keyboard/edit assertion remains real.\n        try requireHittable(input)\n        input.doubleTap()\n        input.typeKey(.rightArrow, modifierFlags: [])'
    diagnostic = b'    /// Preparation diagnostic only. It changes no content or association and\n    /// cannot stand in for the original link/edit/cold-open acceptance method.\n    func testDiagnoseExistingSemanticAnchorFocusAfterSourceDismissal() throws {\n        _ = try admitSemanticSourceContinuation(phase: "linked")\n        try launchSemanticSourceContinuation(expectedText: "Anchor")\n        try openSelectedSemanticSources(text: "Anchor")\n        try requireHittable(semanticSourceAssociation("Genesis 1:1"))\n        XCTAssertEqual(semanticSourceAssociations("Genesis 1:1").count, 1)\n        try dismissSemanticSourceSheet()\n        let input = semanticText("Anchor")\n        try requireHittable(input)\n        input.doubleTap()\n        let beforeKey = XCTAttachment(string: app.debugDescription)\n        beforeKey.name = "heart-semantic-focus-before-real-key-ax"\n        beforeKey.lifetime = .keepAlways; add(beforeKey)\n        attach("heart-semantic-focus-before-real-key")\n        input.typeKey(.rightArrow, modifierFlags: [])\n        input.doubleTap()\n        XCTAssertEqual(input.value as? String, "Anchor")\n        XCTAssertFalse(semanticSourceSearch.exists)\n        attach("heart-semantic-focus-after-real-reselection")\n    }\n\n'
    c.require(before.count(original) == after.count(replacement) == after.count(diagnostic) == 1
              and after.replace(diagnostic, b"", 1).replace(replacement, original, 1) == before,
              "All original assertions and every other original source byte must remain exact")
    return {"beforeSHA256": BEFORE, "afterSHA256": AFTER,
            "inverseDeltaRestoresEntireOriginalFile": True, "originalAssertionsChanged": False,
            "appSourcesChanged": 0, "realKeyboardArrowDoubleTapAndTypingUnchanged": True,
            "additiveFocusDiagnosticGrantsNoAcceptance": True}


def qualify(c, admission, original_source, original_producer):
    row = admission["sourceFocusUIOverride"]
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
              and receipt.get("uiSourceComposition") == "original12files-plus-exact-one-preparation-delta",
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
                  "Original app/UI base source differs from exact5c05")
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
    return {"status": "PASS_EXACT_UI_ONLY_FOCUS_PREPARATION_SOURCE_AND_PRODUCTS", "appSourceCommit": BASE,
            "uiTestChangeCommit": CHANGE, "uiReceiptSHA256": c.sha(receipt_raw), "sourceDelta": delta,
            "actualTestsExecutedByThisQualification": 0, "appRebuilds": 0}
