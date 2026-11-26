"""One exact ca7 App / 8aa complete UI pairing; never a claimed App rebuild."""
import ast
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

APP = "ca7cb16f91c3d5fc4f7c8c178369abc9276e9a07"
UI = "8aa603ddb179a98a711a1cb2208d556a498c602f"
UI_TREE = "54b01cffd038a28ffd7621f47514dbf2f31720f3"
FIX = "bdb5663b25287d1eb72fc2db003799d23ab4a9b9"
FILE = "PinkhaStage1Acceptance/Tests/HeartSourceCaptureAcceptanceUITests.swift"
BEFORE = "829a0697cb2433be859fce53288e341ac5025cd54396545f2ab6eeea86fae91c"
AFTER = "efb4508405851be56d2302c2cea84d337d5fa3ca5caa241d6f7a96bf2cc0b2f6"
PRODUCER = "c63a1aa11b72495229c4f6e667b2610d8ae8b9451e7353fdc184c70e180de0ba"
UI_MANIFEST = "8fc663f993ac31b18340ccc6e26c2e0cf34b14de9e5cbf72239f1021ebaa3a7b"
GIT_BUNDLE = "bd869c3766c6beb95d4a38d1d890bb6cdac499f280d85fd3dd42f64377244133"
APP_RESULT = "bacef644997739dafa5367f8b8cd49bf29dc5fe8b545dc4d3b6b45b77faa4705"
GENERATOR = "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
PROFILE = "original-ca7-app-c-source-ui-helper-isolation-8aa-v1"


def source_delta(c, before, after):
    c.require(c.sha(before) == BEFORE and c.sha(after) == AFTER,
              "Exact reviewed C UI helper bytes required")
    changes = ((b'isDigest(handoff)', b'Self.isDigest(handoff)'),
               (b'isDigest(fingerprint)', b'Self.isDigest(fingerprint)'),
               (b'private func isDigest(_ value: String)', b'private nonisolated static func isDigest(_ value: String)'))
    expected = before
    for original, replacement in changes:
        c.require(expected.count(original) == 1, "One original pure helper occurrence required")
        expected = expected.replace(original, replacement)
    c.require(expected == after, "Unrelated C assertions or UI behavior changed")
    return {"beforeSHA256": BEFORE, "afterSHA256": AFTER, "exactPureIsolationEdits": 3,
            "originalEAssertionsChanged": False, "CAssertionsChanged": False, "appSourceChanges": 0}


def without_modes(inventory):
    return {name: {key: value for key, value in row.items() if key != "mode"}
            for name, row in inventory.items() if row["kind"] != "directory"}


def entry_map(c, entries):
    c.require(isinstance(entries, list) and len(entries) == len({row["path"] for row in entries}),
              "Unique original product entries required")
    return {row["path"]: {key: value for key, value in row.items() if key != "path"} for row in entries}


def qualify(c, admission, source, producer, evidence):
    row = admission["currentUIHelperDerivative"]
    c.require(row.get("profile") == PROFILE and admission["sourceCommit"] == APP
              and admission["producerReceipt"]["sha256"] == PRODUCER,
              "Exact original App and actual UI-only continuation required")
    c.require(producer.get("sameCommitForAppAndUITests") is False
              and type(producer.get("appBuildsThisContinuation")) is int
              and producer["appBuildsThisContinuation"] == 0
              and producer.get("appProductsUnchangedDuringUIContinuation") is True
              and producer["app"]["sourceCommit"] == APP and producer["ui"]["sourceCommit"] == UI,
              "Mixed source provenance must remain explicit without a claimed App rebuild")
    original_app_raw = c.pinned(row["originalAppResult"])
    c.require(c.sha(original_app_raw) == APP_RESULT == producer["originalAppResult"]["sha256"]
              and c.decode(original_app_raw) == producer["app"], "Original successful App result was changed")
    manifest_raw = c.pinned(row["uiSourceManifest"])
    c.require(c.sha(manifest_raw) == UI_MANIFEST == producer["uiSourceDerivative"]["manifestSHA256"],
              "Actual Git-derived UI source manifest changed")
    manifest = c.decode(manifest_raw)
    c.require(manifest.get("schema") == "unified-original-ui-helper-derivative/v1"
              and manifest["appSourceCommit"] == APP and manifest["uiSourceCommit"] == UI
              and manifest["fixOriginalCommit"] == FIX and manifest["changedTestSources"] == [FILE]
              and manifest["allOtherTrackedUIFilesByteIdenticalToAppCommit"] is True
              and producer["uiSourceDerivative"] == {"allOtherUITestSourcesByteIdentical": True,
                  "changedTestSources": [FILE], "inverseDeltaRestoresOriginalFile": True,
                  "manifestSHA256": UI_MANIFEST, "sourceCommit": UI}, "UI derivative scope changed")
    c.require(c.sha(c.pinned(row["uiGitBundle"])) == GIT_BUNDLE, "Original UI Git proof bundle changed")
    git_root = Path(row["uiGitProofRoot"])
    c.require(git_root.is_absolute() and git_root.resolve() == git_root and git_root.is_dir(), "Owned UI Git proof root required")
    def git(*args):
        return subprocess.check_output(["git", "--git-dir", str(git_root), *args], timeout=30)
    c.require(git("rev-parse", UI + "^{tree}").decode().strip() == UI_TREE, "Exact fixed UI Git tree required")
    changed = git("diff", "--name-only", APP, UI).decode().splitlines()
    c.require(FILE in changed and all(name == FILE or name.startswith(
        "docs/validation/20261125-unified-main94d-native-acceptance/") for name in changed),
        "Compiled App or unrelated code differs in the UI source commit")
    def tracked(commit):
        return [x for x in git("ls-tree", "-r", "--name-only", "-z", commit, "PinkhaStage1Acceptance").decode().split("\0") if x]
    names = tracked(APP)
    c.require(len(names) == 12 and set(names) == set(tracked(UI)) == set(manifest["sourceFiles"]),
              "Complete original twelve-file UI tree required")
    ui_root = Path(row["uiSourceRoot"])
    c.require(ui_root.is_absolute() and ui_root.resolve() == ui_root, "Canonical original compiled UI source root required")
    delta = None
    for name in names:
        before, after = git("show", APP + ":" + name), git("show", UI + ":" + name)
        c.require(c.raw(source / name) == before, "Original App checkout UI file differs from ca7")
        actual = c.raw(ui_root / name)
        c.require(actual == after and manifest["sourceFiles"][name] == {"bytes": len(after), "sha256": c.sha(after)},
                  "Actual compiled UI input differs from its exact committed source")
        if name == FILE:
            delta = source_delta(c, before, after)
        else:
            c.require(before == after, "An unrelated original UI method or project changed")
    c.require(c.digest(ui_root / "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift") ==
              "ad442d34641371b44d9cab5ff63dcb8f9a7ba96eededac6f73b993634bdcef39",
              "Original six-stage E UI assertions/helper changed")
    original_copy = c.decode(c.pinned(row["originalUICopy"]))
    c.require(original_copy.get("explicitDerivative") is True
              and original_copy["appSourceCommit"] == APP and original_copy["uiSourceCommit"] == UI
              and original_copy["generatorSHA256"] == GENERATOR and len(original_copy["copiedFiles"]) == len(names) and
              {entry["path"]: entry["sha256"] for entry in original_copy["copiedFiles"]} ==
              {name: item["sha256"] for name, item in manifest["sourceFiles"].items()},
              "Actual complete UI copy/generator provenance differs")
    # Reproduce only the pure, reviewed project transformation in a private
    # directory. This compiles nothing and never changes the actual UI source.
    generator = c.raw(source / "Tools/PinkhaNativeDerived/rerun_original_ui.py")
    c.require(c.sha(generator) == GENERATOR, "Original UI-only generator source changed")
    function = next(n for n in ast.parse(generator).body if isinstance(n, ast.FunctionDef) and n.name == "ui_only_project")
    scope = {"shutil": shutil, "re": re, "ET": ET}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "reviewed-ui-project-generator", "exec"), scope)
    reproduction = evidence / "private-ui-project-reproduction"
    reproduction.mkdir(mode=0o700)
    for name in names:
        c.write_bytes(reproduction / name, c.raw(ui_root / name))
    generated = scope["ui_only_project"](reproduction)
    actual_generated = ui_root / "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj"
    for path in generated.rglob("*"):
        if path.is_file():
            c.require(c.raw(path) == c.raw(actual_generated / path.relative_to(generated)),
                      "Actual generated project/scheme differs from the original reviewed transformation")
    expected_schemes = sorted(p.relative_to(generated).as_posix() for p in generated.rglob("*.xcscheme"))
    c.require(expected_schemes == sorted(p.relative_to(actual_generated).as_posix() for p in actual_generated.rglob("*.xcscheme")),
              "Unexpected generated UI scheme")
    before_products = c.decode(c.pinned(row["appProductsBefore"]))
    all_products_raw = c.pinned(row["completeProducts"])
    all_products = c.decode(all_products_raw)
    c.require(c.sha(all_products_raw) == producer["completeProductsInventory"]["sha256"]
              and before_products == all_products["app-derived"], "Original App products changed during the UI-only continuation")
    for kind, label in (("app", "app-derived"), ("ui", "ui-derived")):
        products = admission["products"][kind]
        admitted = c.decode(c.pinned(products["manifest"]))
        c.require(without_modes(admitted) == entry_map(c, all_products[label]["entries"]),
                  "Admitted product manifest differs from complete original producer inventory")
    return {"status": "PASS_EXACT_CA7_APP_8AA_COMPLETE_UI_DERIVATIVE", "appSourceCommit": APP,
            "actualUISourceCommit": UI, "sameCommitForAppAndUITests": False,
            "originalAppResultSHA256": APP_RESULT, "uiSourceManifestSHA256": UI_MANIFEST,
            "originalUIFiles": len(names), "sourceDelta": delta,
            "originalEUIFileByteIdentical": True, "generatedProjectAndSchemeReproduction": "PASS",
            "appProductsUnchangedDuringUIOnlyContinuation": True,
            "appRebuilds": 0, "testsExecutedByThisQualification": 0}
