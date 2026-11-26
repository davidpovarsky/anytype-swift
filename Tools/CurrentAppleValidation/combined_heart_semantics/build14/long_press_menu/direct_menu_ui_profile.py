"""Strict original-app/new-UI pairing for one reviewed continuation menu helper."""
from pathlib import Path
import copy
import json
import subprocess

BASE = "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
CHANGE = "bfc5646efcaea558190ae5aa55d76b13fe5624d5"
FILE = "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift"
BEFORE = "935d722957539a1499816295cac97d369618a77fe33e27b9f9e42d90fbb8cff8"
AFTER = "fa8d8504faa08fb8abbe30110f1ec4debe92384daf7bd943554db62bc477c0d5"
GENERATOR = "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
GENERATOR_COMMIT = "0b9c5d75fec8fa4f4e17266010f7d79a47c08b87"
BUILDER = "ddb0aa992c3d0f3388fd008d526ccee8cfd67374db847187342274272f3eca4d"
PROFILE = "original-heart-app14-long-press-menu-selection-v1"
STATUS = "PASS_APP14_UI_ONLY_LONG_PRESS_MENU_SELECTION_NOT_ACCEPTANCE"


PRODUCER = "b6b3ba75809a9bebe6fbf2dbf77149def27cb1eabe1771f9d5d73108c56e00d6"
ORIGINAL_UI_COPY = "be4b6678269a7789a483b7cc7078a2a9e1957d164efdb114c143de1ab1856229"


def admit_original_ui_copy(c, admission, producer, source):
    c.require(admission["producerReceipt"]["sha256"] == PRODUCER,
              "Exact original App14 receipt required")
    copy_path = Path(admission["producerReceipt"]["path"]).parent / "original-ui-copy.json"
    c.require(c.digest(copy_path) == ORIGINAL_UI_COPY, "Original complete UI source-copy receipt changed")
    copied = c.decode(c.raw(copy_path))
    argv = producer["ui"]["argv"]
    c.require(copied["generatorSHA256"] == GENERATOR and argv.count("-project") == 1
              and argv[argv.index("-project") + 1] == copied["generatedProject"],
              "The actual UI build did not use the original generated project")
    names = sorted(n for n in subprocess.check_output(["git", "-C", str(source), "ls-files", "-z", "PinkhaStage1Acceptance"], timeout=30).decode().split("\0") if n)
    c.require(subprocess.check_output(["git", "-C", str(source), "rev-parse", CHANGE + "^"], timeout=30).decode().strip() == BASE
              and subprocess.check_output(["git", "-C", str(source), "diff", "--name-only", BASE, CHANGE], timeout=30).decode().splitlines() == [FILE]
              and c.sha(subprocess.check_output(["git", "-C", str(source), "show", CHANGE + ":" + FILE], timeout=30)) == AFTER,
              "Exact sole-parent one-file Git-derived preparation required")
    c.require(len(names) == 12 and copied["copiedFiles"] ==
              [{"path": n, "sha256": c.digest(source / n)} for n in names],
              "All twelve actual copied UI inputs must equal the frozen original source")
    return {"receiptSHA256": ORIGINAL_UI_COPY, "generatorSHA256": GENERATOR,
            "trackedOriginalUIFiles": 12, "originalProjectCommandBound": True}


def source_delta(c, before, after):
    c.require(c.sha(before) == BEFORE and c.sha(after) == AFTER, "Exact App14/reviewed direct-selection source required")
    raw = c.raw(Path(__file__).with_name("direct-menu-source-identity.json"))
    c.require(c.sha(raw) == "5efa96d9a2214b80caf1474ea60e6c09c8d57900f6743851f86f1c2c848e37f6", "Exact reviewed direct-selection-only inverse required")
    identity = c.decode(raw)
    old, new = identity["removedBytes"].encode(), identity["addedBytes"].encode()
    c.require(identity["schema"] == "pinkha-app14-long-press-native-menu-selection-v1"
              and identity["baseAppCommit"] == BASE and identity["uiChangeCommit"] == CHANGE
              and identity["file"] == FILE and identity["beforeSHA256"] == BEFORE
              and identity["afterSHA256"] == AFTER and before.count(old) == after.count(new) == 1
              and after.replace(new, old, 1) == before and identity["originalOutcomeAssertionsChanged"] is False
              and identity["firstOriginalMenuRoutePreserved"] is True
              and identity["appChanges"] == identity["nativeChanges"] == 0,
              "All original assertions and every other source byte must remain exact")
    return {"beforeSHA256": BEFORE, "afterSHA256": AFTER, "inverseDeltaRestoresEntireOriginalFile": True,
            "originalOutcomeAssertionsChanged": False, "appSourcesChanged": 0,
            "firstOriginalMenuRoutePreserved": True, "originalNativeSourcesMenuActionRequired": True,
            "programmaticSelectionChanges": 0, "identitySHA256": c.sha(raw)}


def qualify(c, admission, original_source, original_producer):
    row = admission["directMenuUIOverride"]
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
              and receipt.get("uiSourceComposition") == "original12files-plus-exact-first-menu-long-press",
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
                  "Original app/UI base source differs from exact App14")
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

