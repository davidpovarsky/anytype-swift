#!/usr/bin/env python3
"""Build the complete UI target with the observed Channel Home onboarding preparation only."""
from __future__ import annotations
import argparse, ast, base64, hashlib, importlib, json, os, plistlib, re, shutil, subprocess, sys, tarfile, time, traceback
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
CONTROL = Path("/Users/m1/builds/e-combined-current-20261125/control-header6f")
CONTROL_SHA = "7adb3118bbf584d6475f1bffc483c2055994ce50ac3031471226762df23dc501"
ADMISSION_SHA = "82ede074604e6ac8e80f631dfd2d61e4f19fc54cd0a5a68c482fda6bc310e697"
APP_COMMIT = "6f1194f9b8c9540dea1187826dda6a256777dbbf"
ORIGINAL_UI_COMMIT = "6f1194f9b8c9540dea1187826dda6a256777dbbf"
UI_COMMIT = "3396d32fcf863f3d5a2c9e33f1e29ffdaf23dcaa"
ARCHIVE_SHA = "9431edf59ba7b39652c1d3ea5a53f34bfd615bbe5edd5c00ee5a8418f108caa5"
MANIFEST_SHA = "7ba97e13510b9ecce4bf68911cdc7966a6c86ffe6724dd14f714b20576f8c02e"
TEST = "PinkhaStage1Acceptance/Tests/HeartSourceCaptureAcceptanceUITests.swift"
TEST_SHA = "142a547283d3eefc8be1deca9a303e38c0bf238436b9f3e615f5e73848baa657"
FLAGS = "$(inherited) -D DEBUG -D PINKHA_DUAL_ENGINE_RUNTIME -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1 -D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 -D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1"
NAVIGATION_HELPER = "    private func dismissOriginalChannelHomeOnboardingIfPresent() throws {\n        // The original first-space flow presents this modal above the app's\n        // engine header. Decline its optional home creation through its actual\n        // UI; the subsequent source identity and capture assertions are unchanged.\n        let prompt = app.staticTexts[\"Add a Channel Home?\"]\n        guard prompt.waitForExistence(timeout: try remaining(5)) else { return }\n        let dismiss = app.buttons[\"Not now\"]\n        try require(dismiss.exists, \"original-channel-home-decline-missing\")\n        try tap(dismiss)\n        try require(prompt.waitForNonExistence(timeout: remaining(15)), \"original-channel-home-remained\")\n    }\n\n"

def core():
    p = CONTROL / "combined_heart_semantics_gateway.py"
    if hashlib.sha256(p.read_bytes()).hexdigest() != CONTROL_SHA: raise ValueError("Original admission changed")
    sys.path.insert(0, str(CONTROL))
    c = importlib.import_module("combined_heart_semantics_gateway")
    c.require(Path(c.__file__).resolve() == p, "Foreign admission")
    return c

def inverse_navigation(c, corrected):
    c.require(corrected.count(NAVIGATION_HELPER) == 1
              and corrected.count("            try dismissOriginalChannelHomeOnboardingIfPresent()\n") == 1,
              "Exact normal-space navigation delta required")
    return corrected.replace(NAVIGATION_HELPER, "").replace("            try dismissOriginalChannelHomeOnboardingIfPresent()\n", "")

def source_proof(c, commands, admission, root, incoming):
    archive = incoming / "ui-source.tar.gz"
    c.require(c.digest(archive) == ARCHIVE_SHA, "Exact new UI source archive differs")
    source = root / "ui-source"; source.mkdir(mode=0o700)
    with tarfile.open(archive, "r:gz") as t:
        seen = set()
        for member in t.getmembers():
            name = PurePosixPath(member.name)
            c.require(member.isfile() and member.size <= 2 * 1024**2 and not name.is_absolute()
                      and all(x not in ("", ".", "..") for x in member.name.split("/"))
                      and member.name not in seen, "Unsafe or duplicate UI archive entry")
            seen.add(member.name)
            c.write_bytes(source / member.name, t.extractfile(member).read())
    manifest_path = source / "source.json"
    c.require(c.digest(manifest_path) == MANIFEST_SHA, "Exact original UI source manifest required")
    manifest = c.decode(c.raw(manifest_path))
    c.require(manifest["appSourceCommit"] == APP_COMMIT
              and manifest["originalUISourceCommit"] == ORIGINAL_UI_COMMIT
              and manifest["uiSourceCommit"] == UI_COMMIT
              and manifest["changedTestSources"] == [TEST], "Exact source-only derivative scope required")
    objects = manifest["gitObjects"]
    c.require(len(objects) == 12, "Bounded actual commit/tree closure required")
    def obj(oid, kind):
        row = objects[oid]; data = base64.b64decode(row["data"], validate=True)
        c.require(row["type"] == kind and hashlib.sha1(
            kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).hexdigest() == oid,
            "Actual original Git object identity differs")
        return data
    def tree(oid):
        data = obj(oid, "tree"); result = {}; offset = 0
        while offset < len(data):
            end = data.index(b"\0", offset)
            mode, name = data[offset:end].decode().split(" ", 1)
            c.require(name not in result and "/" not in name and name not in ("", ".", "..")
                      and end + 21 <= len(data), "Invalid original Git tree")
            result[name] = (mode, data[end+1:end+21].hex()); offset = end + 21
        return result
    original_commit = obj(ORIGINAL_UI_COMMIT, "commit").decode()
    new_commit = obj(UI_COMMIT, "commit").decode()
    c.require([x for x in new_commit.splitlines() if x.startswith("parent ")] ==
              ["parent " + ORIGINAL_UI_COMMIT], "Actual UI commit must have the original source as sole parent")
    original_tree = original_commit.splitlines()[0].removeprefix("tree ")
    new_tree = new_commit.splitlines()[0].removeprefix("tree ")
    def only_delta(old_id, new_id, parts):
        old, new = tree(old_id), tree(new_id)
        c.require(set(old) == set(new), "A source path was added or removed outside the exact helper")
        for name in old:
            c.require(old[name][0] == new[name][0], "A source mode changed")
            if name != parts[0]:
                c.require(old[name] == new[name], "Unreviewed source outside the exact UI file")
        if len(parts) > 1:
            c.require(old[parts[0]][0] == "40000", "Expected original Git directory")
            only_delta(old[parts[0]][1], new[parts[0]][1], parts[1:])
        else:
            c.require(old[parts[0]][0] == "100644" and old[parts[0]][1] != new[parts[0]][1],
                      "Only the original regular UI method file may change")
    only_delta(original_tree, new_tree, TEST.split("/"))
    def files(oid, prefix):
        result = {}
        for name, (mode, child) in tree(oid).items():
            path = prefix + "/" + name
            if mode == "40000": result.update(files(child, path))
            else:
                c.require(mode == "100644", "Original UI files must be ordinary regular Git blobs")
                result[path] = child
        return result
    old_blobs = files(tree(original_tree)["PinkhaStage1Acceptance"][1], "PinkhaStage1Acceptance")
    new_blobs = files(tree(new_tree)["PinkhaStage1Acceptance"][1], "PinkhaStage1Acceptance")
    rows = manifest["sourceFiles"]
    c.require(set(rows) == set(old_blobs) == set(new_blobs) and len(rows) == 12
              and seen == set(rows) | {"source.json"}, "Complete original twelve-file UI closure required")
    old_source = Path(admission["sourceRoot"])
    def blob(data): return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    baseline = root / "baseline-ui-source"; baseline.mkdir(mode=0o700)
    for name, row in rows.items():
        path = source / name; old_data = c.raw(old_source / name); data = c.raw(path)
        c.require(blob(old_data) == old_blobs[name] and blob(data) == new_blobs[name] == row["gitBlob"]
                  and len(data) == row["bytes"] and c.sha(data) == row["sha256"],
                  "Actual original/new UI Git bytes differ")
        c.write_bytes(baseline / name, old_data)
        if name != TEST: c.require(data == old_data, "Unreviewed other UI source change")
    c.require(c.digest(source / TEST) == TEST_SHA
              and inverse_navigation(c, (source / TEST).read_text()) == (old_source / TEST).read_text(),
              "Exact onboarding inverse must recover every original assertion")
    c.write(root / "evidence/ui-source-proof.json", {
        "status": "PASS_EXACT_UI_SOURCE_NOT_ACCEPTANCE", "appSourceCommit": APP_COMMIT,
        "originalUISourceCommit": ORIGINAL_UI_COMMIT, "uiSourceCommit": UI_COMMIT,
        "sourceManifestSHA256": MANIFEST_SHA, "sourceArchiveSHA256": ARCHIVE_SHA,
        "gitCommitTreeObjects": len(objects), "files": rows, "changedSources": [TEST],
        "exactNavigationInverse": True, "allOtherUISourcesByteIdentical": True,
        "originalAssertionsRemoved": 0})
    return source, rows


def build(args):
    c = core()
    c.require(sys.platform == "darwin" and sys.version_info >= (3, 11), "Qualified Mac Python required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent
              and not args.root.exists(), "Fresh private UI producer root")
    args.root.mkdir(mode=0o700); os.umask(0o077)
    evidence = args.root / "evidence"; evidence.mkdir(mode=0o700)
    commands = c.Commands(args.root / "commands", args.root)
    receipt = {"protocol": "pinkha-c-source-onboarding-ui-producer-v1", "status": "FAIL",
               "controllerSHA256": c.digest(Path(__file__)), "appSourceCommit": APP_COMMIT,
               "originalUISourceCommit": ORIGINAL_UI_COMMIT, "uiSourceCommit": UI_COMMIT,
               "appBuilds": 0, "nativeBuilds": 0, "testsExecuted": 0}
    built = {}
    try:
        admission_path = CONTROL / "admission6f1194.json"
        c.require(c.digest(admission_path) == ADMISSION_SHA, "Original exact product authority")
        admission = c.decode(c.raw(admission_path))
        mask = os.umask(0)
        try: receipt["originalProductAdmission"], built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
        finally: os.umask(mask)
        source, rows = source_proof(c, commands, admission, args.root, args.incoming)
        helper = Path(admission["sourceRoot"]) / "Tools/PinkhaNativeDerived/rerun_original_ui.py"
        functions = [n for n in ast.parse(helper.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "ui_only_project"]
        c.require(len(functions) == 1, "Original complete UI generator required")
        namespace = {"shutil": shutil, "re": re, "ET": ET}
        exec(compile(ast.get_source_segment(helper.read_text(), functions[0]), str(helper), "exec"), namespace)
        project = namespace["ui_only_project"](source)
        baseline_project = namespace["ui_only_project"](args.root / "baseline-ui-source")
        # Reproduce both complete projects with the same original generator.
        # Xcode's four empty SwiftPM cache directories are created explicitly.
        empty_cache = ["project.xcworkspace", "project.xcworkspace/xcshareddata",
                       "project.xcworkspace/xcshareddata/swiftpm",
                       "project.xcworkspace/xcshareddata/swiftpm/configuration"]
        for generated in (project, baseline_project):
            for name in empty_cache:
                (generated / name).mkdir(mode=0o755)
                (generated / name).chmod(0o755)
        project_before = c.inventory(project)
        c.require(c.inventory(baseline_project) == project_before,
                  "Exact original complete UI project must reproduce without target or setting changes")
        c.write(evidence / "generated-project.json", project_before)
        c.write(evidence / "generator.json", {"path": str(helper), "sha256": c.digest(helper),
                "generatedProject": str(project), "completeUIFiles": len(rows)})
        c.require(shutil.disk_usage(args.root).free > 2 * 1024**3 + 512 * 1024**2,
                  "Measured UI-only growth plus emergency floor required")
        settings = ["OTHER_SWIFT_FLAGS=" + FLAGS, "ENABLE_TESTABILITY=YES", "ONLY_ACTIVE_ARCH=YES", "ARCHS=arm64",
                    "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_ALLOWED=YES",
                    "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
        argv = ["xcodebuild", "build-for-testing", "-project", str(project), "-scheme", "PinkhaPrebuiltUI",
                "-configuration", "Debug-Anytype", "-destination", "generic/platform=iOS Simulator",
                "-derivedDataPath", str(args.root / "derived"), "-resultBundlePath", str(evidence / "UI.xcresult"),
                "-jobs", "2"] + settings
        mask = os.umask(0o022)
        try: log, result = commands.run(argv, "complete-ui-build", 600, checked=False)
        finally: os.umask(mask)
        receipt["uiCommand"] = result
        c.require(result["status"] == "PASS_COMMAND" and b"** TEST BUILD SUCCEEDED **" in c.raw(log, 64 * 1024**2),
                  "Actual complete UI build did not pass")
        c.require(all(c.digest(source / name) == row["sha256"] for name, row in rows.items())
                  and c.inventory(project) == project_before, "UI source/project changed during build")
        receipt["originalProductsAfter"] = {name: c.product_integrity(value) for name, value in built.items()}
        products = args.root / "derived/Build/Products"
        inventory = c.inventory(products)
        descriptors = list(products.glob("*.xctestrun"))
        c.require(len(descriptors) == 1, "Exactly one generated UI descriptor required")
        descriptor = descriptors[0]; decoded = plistlib.loads(c.raw(descriptor))
        blueprint = "PinkhaStage1AcceptanceUITests"
        c.require(set(decoded) == {"__xctestrun_metadata__", blueprint}
                  and decoded["__xctestrun_metadata__"]["FormatVersion"] == 1
                  and decoded[blueprint]["IsUITestBundle"] is True
                  and decoded[blueprint]["UseUITargetAppProvidedByTests"] is True
                  and not decoded[blueprint].get("SkipTestIdentifiers"), "Original UI launch contract differs")
        c.write(evidence / "ui-products.json", inventory)
        receipt.update(status="PASS_COMPLETE_UI_BUILD_ONLY_NOT_ACCEPTANCE",
            productRoot=str(products), productManifestSHA256=c.digest(evidence / "ui-products.json"),
            descriptorRelativePath=descriptor.name, descriptorSHA256=c.digest(descriptor),
            originalSelection=decoded[blueprint].get("OnlyTestIdentifiers", []),
            sourceManifestSHA256=MANIFEST_SHA, changedSources=[TEST],
            appProductsUnchanged=True, nativeRuntimeUnchanged=True)
    except BaseException as exc:
        receipt["firstFailure"] = c.error(exc)
        c.write(evidence / "private-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        receipt["ownedGroups"] = [{"pgid": group, "absentAtOriginalExit": group in commands.absent_groups}
                                  for group in commands.groups]
        if any(not row["absentAtOriginalExit"] for row in receipt["ownedGroups"]): receipt["status"] = "FAIL"
        c.write(evidence / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "receiptSHA256": c.digest(evidence / "receipt.json"),
                      "root": str(args.root), "firstFailure": receipt.get("firstFailure")}, sort_keys=True))
    return 0 if receipt["status"] == "PASS_COMPLETE_UI_BUILD_ONLY_NOT_ACCEPTANCE" else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--incoming", type=Path, required=True)
    raise SystemExit(build(parser.parse_args()))