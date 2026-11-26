#!/usr/bin/env python3
"""Build the complete original UI with exact opted-in fresh-account Warning navigation."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
import combined_heart_semantics_current as c
import fresh_warning_ui_profile as profile

c.require(c.digest(Path(c.__file__)) == "73ee947386ac6115ec7b1d75d74b1590a68a033000b311329fb8824c15691239",
          "Exact original App13 source and command gateway required")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-source", type=Path, required=True)
    parser.add_argument("--producer-admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon required")
    a = c.raw(args.producer_admission)
    c.require(c.sha(a) == args.admission_sha256, "Original reviewed combined producer admission differs")
    admission = c.decode(a); original = c.decode(c.pinned(admission["producerReceipt"]))
    c.require(admission["sourceCommit"] == original["sourceCommit"] == profile.BASE
              and original["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
              and original["sourceUnchanged"] is True and original["testsExecuted"] == 0,
              "Actual original app plus complete UI producer required")
    c.require(subprocess.check_output(["git", "-C", str(args.app_source), "rev-parse", "HEAD"], timeout=30).decode().strip() == profile.BASE
              and not subprocess.check_output(["git", "-C", str(args.app_source), "status", "--porcelain"], timeout=30).strip(),
              "Immutable actual app source must remain clean exact App13")
    original_copy = profile.admit_original_ui_copy(c, admission, original, args.app_source)
    candidate = c.raw(args.candidate)
    delta = profile.source_delta(c, c.raw(args.app_source / profile.FILE), candidate)
    generator = c.raw(args.generator)
    c.require(c.sha(generator) == profile.GENERATOR, "Exact reviewed original full UI generator required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned UI build root required")
    args.root.mkdir(mode=0o700)
    source = args.root / "source"; source.mkdir(mode=0o700)
    receipt = {"status": "FAIL", "appSourceCommit": profile.BASE, "uiTestChangeCommit": profile.CHANGE,
               "originalProducerReceiptSHA256": admission["producerReceipt"]["sha256"],
               "generatorSHA256": profile.GENERATOR, "generatorCommit": profile.GENERATOR_COMMIT,
               "builderSHA256": c.digest(Path(__file__)), "profileSHA256": c.digest(Path(profile.__file__)),
               "sourceDelta": delta, "uiSourceRoot": str(source), "originalUICopy": original_copy,
               "sameCommitForAppAndUITests": False, "uiSourceComposition": "original12files-plus-exact-fresh-account-warning-delta", "uiBuilds": 0, "appBuilds": 0, "nativeBuilds": 0, "testsExecuted": 0}
    try:
        names = subprocess.check_output(["git", "-C", str(args.app_source), "ls-files", "-z", "PinkhaStage1Acceptance"], timeout=30).decode().split("\0")
        names = sorted(n for n in names if n)
        c.require(len(names) == 12 and profile.FILE in names, "Full original UI source inventory differs")
        originals = {}
        for name in names:
            value = c.raw(args.app_source / name)
            c.require(value == subprocess.check_output(["git", "-C", str(args.app_source), "show", profile.BASE + ":" + name], timeout=30),
                      "Original tracked UI source changed")
            originals[name] = c.sha(value)
            c.write_bytes(source / name, candidate if name == profile.FILE else value)
        receipt["originalTrackedFiles"] = originals
        c.write_bytes(args.root / "original-ui-generator.py", generator)
        sys.path.insert(0, str(args.app_source / "Tools/PinkhaNativeDerived"))
        spec = importlib.util.spec_from_file_location("reviewed_original_ui_generator", args.root / "original-ui-generator.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        project = module.ui_only_project(source)
        commands = c.Commands(args.root / "commands", source)
        listing, listed = commands.run(["xcodebuild", "-list", "-project", str(project), "-json"], "original-ui-project-list", 120)
        project_info = c.decode(c.raw(listing))
        c.require(project_info.get("project", {}).get("targets") == ["PinkhaStage1AcceptanceUITests"]
                  and project_info["project"].get("schemes") == ["PinkhaPrebuiltUI"],
                  "Generated project must expose only the complete original independent UI target")
        receipt["projectAdmission"] = {"command": listed, "project": project_info}
        before = c.inventory(source); c.write(args.root / "source-before.json", before)
        c.write_bytes(args.root / "candidate-source.swift", candidate)
        derived = args.root / "derived"
        command = copy.deepcopy(original["ui"]["argv"])
        bundle = args.root / "original-build.xcresult"
        for flag, value in (("-project", str(project)), ("-derivedDataPath", str(derived)), ("-resultBundlePath", str(bundle))):
            c.require(command.count(flag) == 1, "Original complete UI command format differs")
            command[command.index(flag) + 1] = value
        receipt.update(derivedDataRoot=str(derived), buildXCResult=str(bundle))
        c.require(shutil.disk_usage(args.root).free > 3 * 1024**3, "UI-only build allowance needs3GiB free")
        receipt["uiBuilds"] = 1
        log, result = commands.run(command, "ui-only-build", 1200, checked=False)
        receipt["command"] = result
        after = c.inventory(source); c.write(args.root / "source-after.json", after)
        c.require(before == after and result["status"] == "PASS_COMMAND" and result["ownedGroupPresentAfterExit"] is False,
                  "Original full UI-only build failed or source/process identity changed")
        c.require(b"** TEST BUILD SUCCEEDED **" in c.raw(log) and b"HeartSourceCaptureAcceptanceUITests.swift" in c.raw(log),
                  "Actual helper compilation and successful full UI terminal missing")
        products = derived / "Build/Products"
        manifest = c.inventory(products); c.write(args.root / "products-all.json", manifest)
        descriptor = products / "PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun"
        c.require(descriptor.is_file(), "Actual original full UI descriptor missing")
        receipt.update(sourceBeforeSHA256=c.digest(args.root / "source-before.json"), sourceAfterSHA256=c.digest(args.root / "source-after.json"),
                       productsRoot=str(products), productsManifestSHA256=c.digest(args.root / "products-all.json"),
                       descriptorSHA256=c.digest(descriptor), status=profile.STATUS)
    except BaseException as exc:
        receipt["firstFailure"] = c.error(exc)
    finally:
        c.write(args.root / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(args.root / "receipt.json"), "firstFailure": receipt.get("firstFailure")}))
    return 0 if receipt["status"] == profile.STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
