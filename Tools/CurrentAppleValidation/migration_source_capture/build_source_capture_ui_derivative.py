#!/usr/bin/env python3
"""Build only the complete original UI target with C's exact normal-space navigation delta."""
from __future__ import annotations
import argparse, ast, hashlib, importlib, json, os, plistlib, re, shutil, subprocess, sys, tarfile, time, traceback
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
CONTROL = Path("/Users/m1/builds/e-combined-current-20261125/control-c5bcf1c")
CONTROL_SHA = "21998d3f410871cb5833e0de1a1b80ef06f17c2a688d43eead239b60ee373ddf"
ADMISSION_SHA = "fd59d4b22102b06b4379429bfe893c0b7b3dabd38edc6ff0df9b34caf75b39ce"
APP_COMMIT = "ca7cb16f91c3d5fc4f7c8c178369abc9276e9a07"
ORIGINAL_UI_COMMIT = "8aa603ddb179a98a711a1cb2208d556a498c602f"
UI_COMMIT = "f6d3c9e14a38c2c039ad15fbcc3f85941ea05e31"
ARCHIVE_SHA = "6a90386ff9f3b54d7deb8476665b1920dbbb2b3c4722595ae8db1a45ad6bdd50"
MANIFEST_SHA = "12e1a91eac070ea8431e641604e33d5703978d1abb6f11e78ceda914dcf3b66f"
BUNDLE_SHA = "011da93af27fa7d616a0e3004fd8017d36dcffc1427d66b2224d5da0b651113b"
TEST = "PinkhaStage1Acceptance/Tests/HeartSourceCaptureAcceptanceUITests.swift"
TEST_SHA = "204591a62a3298c7f270314cf21ae31f31ce8a00e24d39e7f667e79cdba0e29e"
FLAGS = "$(inherited) -D DEBUG -D PINKHA_DUAL_ENGINE_RUNTIME -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1 -D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 -D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1"
NAVIGATION_HELPER = '''    private func openOriginalFixtureSpace() throws {
        // The real source action is deliberately disabled at SpaceHub until a
        // workspace is open. Use the exact original preparation's visible space
        // button; the subsequent native review must still prove both IDs.
        let name = "Mounted anchor disposable Space"
        let matches = app.buttons.matching(NSPredicate(
            format: "label == %@ OR label ENDSWITH %@", name, ", " + name))
        try require(matches.firstMatch.waitForExistence(timeout: remaining(15)), "original-space-button")
        try require(matches.count == 1, "original-space-button-ambiguous")
        try tap(matches.firstMatch)
    }

'''

def core():
    p = CONTROL / "combined_heart_semantics_gateway_derivative.py"
    if hashlib.sha256(p.read_bytes()).hexdigest() != CONTROL_SHA: raise ValueError("Original admission changed")
    sys.path.insert(0, str(CONTROL))
    c = importlib.import_module("combined_heart_semantics_gateway_derivative")
    c.require(Path(c.__file__).resolve() == p, "Foreign admission")
    return c

def inverse_navigation(c, corrected):
    c.require(corrected.count(NAVIGATION_HELPER) == 1
              and corrected.count("            try openOriginalFixtureSpace()\n") == 1,
              "Exact normal-space navigation delta required")
    return corrected.replace(NAVIGATION_HELPER, "").replace("            try openOriginalFixtureSpace()\n", "")

def source_proof(c, commands, admission, root, incoming):
    archive, bundle = incoming / "ui-source.tar.gz", incoming / "ui-source.bundle"
    c.require(c.digest(archive) == ARCHIVE_SHA and c.digest(bundle) == BUNDLE_SHA, "UI source artifact differs")
    original = admission["currentUIHelperDerivative"]
    git_root = root / "source-proof.git"
    commands.run(["git", "clone", "--mirror", "--no-hardlinks", original["uiGitProofRoot"], str(git_root)],
                 "clone-original-source-proof", 60)
    commands.run(["git", "--git-dir=" + str(git_root), "bundle", "verify", str(bundle)], "verify-ui-source-bundle", 30)
    commands.run(["git", "--git-dir=" + str(git_root), "fetch", str(bundle),
                  "refs/heads/codex/chatgpt-source-capture-ui-20261125:refs/heads/c-source-ui"],
                 "import-exact-ui-source", 30)
    def git(*args):
        return subprocess.check_output(["git", "--git-dir=" + str(git_root), *args], timeout=30)
    c.require(git("rev-parse", "refs/heads/c-source-ui").decode().strip() == UI_COMMIT
              and git("rev-parse", UI_COMMIT + "^").decode().strip() == ORIGINAL_UI_COMMIT,
              "Exact UI commit and original parent required")
    source = root / "ui-source"
    source.mkdir(mode=0o700)
    with tarfile.open(archive, "r:gz") as t:
        seen = set()
        for member in t.getmembers():
            name = PurePosixPath(member.name)
            c.require(member.isfile() and member.size <= 2 * 1024**2 and not name.is_absolute()
                      and all(x not in ("", ".", "..") for x in member.name.split("/"))
                      and member.name not in seen, "Unsafe or duplicate UI source archive entry")
            seen.add(member.name)
            c.write_bytes(source / member.name, t.extractfile(member).read())
    manifest_path = source / "source.json"
    c.require(c.digest(manifest_path) == MANIFEST_SHA, "Source manifest differs")
    manifest = c.decode(c.raw(manifest_path))
    c.require(manifest["appSourceCommit"] == APP_COMMIT
              and manifest["originalUISourceCommit"] == ORIGINAL_UI_COMMIT
              and manifest["uiSourceCommit"] == UI_COMMIT
              and manifest["changedTestSources"] == [TEST], "UI source identity differs")
    rows = manifest["sourceFiles"]
    tracked = set(git("ls-tree", "-r", "--name-only", UI_COMMIT, "PinkhaStage1Acceptance").decode().splitlines())
    c.require(set(rows) == tracked and seen == tracked | {"source.json"} and len(rows) == 12,
              "Complete original UI source set required")
    old_source = Path(original["uiSourceRoot"])
    for name, row in rows.items():
        path = source / name
        c.require(path.stat().st_size == row["bytes"] and c.digest(path) == row["sha256"]
                  and git("rev-parse", UI_COMMIT + ":" + name).decode().strip() == row["gitBlob"]
                  and git("show", UI_COMMIT + ":" + name) == c.raw(path),
                  "UI Git/source bytes differ")
        if name != TEST: c.require(c.raw(path) == c.raw(old_source / name), "Unreviewed other UI source change")
    c.require(c.digest(source / TEST) == TEST_SHA
              and inverse_navigation(c, (source / TEST).read_text()) == (old_source / TEST).read_text(),
              "Navigation inverse does not recover actual original UI source")
    c.write(root / "evidence/ui-source-proof.json", {
        "status": "PASS_EXACT_UI_SOURCE_NOT_ACCEPTANCE", "appSourceCommit": APP_COMMIT,
        "originalUISourceCommit": ORIGINAL_UI_COMMIT, "uiSourceCommit": UI_COMMIT,
        "sourceManifestSHA256": MANIFEST_SHA, "sourceArchiveSHA256": ARCHIVE_SHA,
        "gitBundleSHA256": BUNDLE_SHA, "files": rows, "changedSources": [TEST],
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
    receipt = {"protocol": "pinkha-c-source-navigation-ui-producer-v1", "status": "FAIL",
               "controllerSHA256": c.digest(Path(__file__)), "appSourceCommit": APP_COMMIT,
               "originalUISourceCommit": ORIGINAL_UI_COMMIT, "uiSourceCommit": UI_COMMIT,
               "appBuilds": 0, "nativeBuilds": 0, "testsExecuted": 0}
    built = {}
    try:
        admission_path = CONTROL / "admission-ca7-ui8aa.json"
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
        # The original successful Xcode invocation retained only these four
        # empty SwiftPM cache directories inside its generated project. Create
        # the identical empty structure before comparing the full post-build
        # project inventory; no generated source or target is changed.
        old_project = Path(admission["currentUIHelperDerivative"]["uiSourceRoot"]) / "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj"
        empty_cache = ["project.xcworkspace", "project.xcworkspace/xcshareddata",
                       "project.xcworkspace/xcshareddata/swiftpm",
                       "project.xcworkspace/xcshareddata/swiftpm/configuration"]
        original_tree = c.inventory(old_project)
        current_tree = c.inventory(project)
        c.require(set(original_tree) - set(current_tree) == set(empty_cache)
                  and all(original_tree[name]["kind"] == "directory" for name in empty_cache),
                  "Original generated empty project cache shape differs")
        for name in empty_cache:
            path = project / name
            path.mkdir(mode=original_tree[name]["mode"])
            path.chmod(original_tree[name]["mode"])
        project_before = c.inventory(project)
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
