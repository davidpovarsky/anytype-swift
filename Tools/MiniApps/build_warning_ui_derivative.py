#!/usr/bin/env python3
"""Build only the complete original UI bundle with real warning navigation."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = "6f1194f9b8c9540dea1187826dda6a256777dbbf"
DONOR = "a3e3b21455e7ff517d34b0b16c897fed8845fc22"
CHANGED = "PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift"
OLD_SHA = "a91c52db975b108deddb7f0a71180083a1ee1c65aaaeef58a70ec181e99b6985"
NEW_SHA = "19728bf3a2fc56451ae3a3cbd2b9850847898ed4324e86518942f358147a36ec"
CORE_SHA = "7adb3118bbf584d6475f1bffc483c2055994ce50ac3031471226762df23dc501"
COMMAND_SHA = "62574ac6c02151b22309dcf093f062ff21a670d88db31c472de27521f1a2fd8e"
GENERATOR_SHA = "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"


def require(value, message):
    if not value: raise RuntimeError(message)


def sha(value): return hashlib.sha256(value).hexdigest()


def module(path, name, pin):
    require(sha(path.read_bytes()) == pin, "exact reviewed helper required")
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "git-repo", "original-source", "core", "command-control"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    require(all(p.is_absolute() and p.resolve() == p for p in
                (args.root, args.git_repo, args.original_source, args.core, args.command_control)),
            "canonical owned source paths required")
    require(not args.root.exists(), "fresh UI-only build root required")
    c = module(args.core, "original_warning_ui_core", CORE_SHA)
    custody = module(args.command_control, "original_warning_ui_commands", COMMAND_SHA)
    args.root.mkdir(mode=0o700)
    os.umask(0o022)
    evidence = args.root / "evidence"; evidence.mkdir(mode=0o700)
    commands = custody.command_custody_class(c)(args.root / "commands", args.root)
    result = {"protocol": "pinkha-miniapps-original-warning-ui-producer-v1", "status": "FAIL",
              "appSourceCommit": BASE, "uiSourceCommit": DONOR, "controllerSHA256": c.digest(Path(__file__).resolve()),
              "appBuilds": 0, "nativeBuilds": 0, "testsExecuted": 0}
    try:
        require(git(args.git_repo, "show", "-s", "--format=%P", DONOR).decode().strip() == BASE,
                "exact one-parent original App UI derivative required")
        require(git(args.git_repo, "diff", "--name-only", BASE, DONOR).decode().splitlines() == [CHANGED],
                "only observed warning navigation may differ")
        source = args.root / "ui-source"; old_source = args.root / "reference-source"
        source.mkdir(); old_source.mkdir()
        files = {}
        entries = git(args.git_repo, "ls-tree", "-rz", DONOR, "PinkhaStage1Acceptance").split(b"\0")
        for entry in entries:
            if not entry: continue
            identity, raw_name = entry.split(b"\t", 1)
            mode, kind, blob = identity.decode().split()
            name = raw_name.decode()
            require(mode == "100644" and kind == "blob" and name.startswith("PinkhaStage1Acceptance/")
                    and ".." not in Path(name).parts, "regular original UI input required")
            value = git(args.git_repo, "cat-file", "blob", blob)
            old = git(args.git_repo, "show", BASE + ":" + name)
            require(hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest() == blob,
                    "original Git blob binding differs")
            require((args.original_source / name).read_bytes() == old, "retained original UI source changed")
            if name != CHANGED: require(value == old, "another original UI source changed")
            else:
                require(sha(old) == OLD_SHA and sha(value) == NEW_SHA, "exact reviewed warning delta required")
                start = value.index(b"        // A real qualified custom middleware may present the original safety\n")
                end = value.index(b"        let ready = source.descendants(matching: .any).matching(NSPredicate(\n", start)
                require(value[:start] + value[end:] == old, "every original assertion and method must remain byte-identical")
            for root, content in ((source, value), (old_source, old)):
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream: stream.write(content)
            files[name] = {"gitBlob": blob, "bytes": len(value), "sha256": sha(value), "originalSHA256": sha(old)}
        require(len(files) == 12 and CHANGED in files, "complete twelve original UI files required")
        c.write(evidence / "source-proof.json", {"appSourceCommit": BASE, "uiSourceCommit": DONOR,
            "tree": git(args.git_repo, "rev-parse", DONOR + "^{tree}").decode().strip(),
            "files": files, "onlyChangedSource": CHANGED, "exactInverseRestoresOriginal": True,
            "originalAssertionsRemoved": 0})
        helper = args.original_source / "Tools/PinkhaNativeDerived/rerun_original_ui.py"
        require(c.digest(helper) == GENERATOR_SHA, "original complete UI generator changed")
        syntax = ast.parse(helper.read_text())
        functions = [n for n in syntax.body if isinstance(n, ast.FunctionDef) and n.name == "ui_only_project"]
        require(len(functions) == 1, "one original pure project generator required")
        namespace = {"re": re, "shutil": shutil, "ET": ET}
        # Execute the exact reviewed pure function only. Its body/AST is not
        # rewritten; unrelated original CLI imports need not initialize here.
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(helper), "exec"), namespace)
        project = namespace["ui_only_project"](source)
        reference = namespace["ui_only_project"](old_source)
        require(c.inventory(project) == c.inventory(reference), "complete original generated UI target changed")
        c.write(evidence / "generator.json", {"originalFileSHA256": GENERATOR_SHA,
            "originalFunctionASTSHA256": sha(ast.dump(functions[0], include_attributes=False).encode()),
            "exactOriginalFunctionBody": True, "originalCompleteTargetPreserved": True})
        c.write(evidence / "project.json", c.inventory(project))
        argv = ["xcodebuild", "build-for-testing", "-project", str(project), "-scheme", "PinkhaPrebuiltUI",
            "-configuration", "Debug-Anytype", "-destination", "generic/platform=iOS Simulator",
            "-derivedDataPath", str(args.root / "derived"), "-resultBundlePath", str(args.root / "Build.xcresult"),
            "-jobs", "4", "OTHER_SWIFT_FLAGS=$(inherited) -D DEBUG -D PINKHA_DUAL_ENGINE_RUNTIME -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1 -D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 -D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1",
            "ENABLE_TESTABILITY=YES", "ONLY_ACTIVE_ARCH=YES", "ARCHS=arm64", "SWIFT_OPTIMIZATION_LEVEL=-Onone",
            "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
        log, command = commands.run(argv, "complete-ui-build", 900)
        require(command["exitCode"] == 0 and b"** TEST BUILD SUCCEEDED **" in c.raw(log, 64 * 1024**2),
                "actual original full UI build must pass")
        require(all(c.digest(source / name) == row["sha256"] for name, row in files.items()), "compiled source changed")
        products = args.root / "derived/Build/Products"; manifest = c.inventory(products)
        c.write(evidence / "products.json", manifest)
        descriptors = list(products.glob("*.xctestrun"));require(len(descriptors) == 1, "one complete UI descriptor required")
        result.update(status="PASS_COMPLETE_UI_BUILD_ONLY_NOT_ACCEPTANCE", uiCommand=command,
            sourceProofSHA256=c.digest(evidence / "source-proof.json"), sourceFiles=12,
            originalAppSourceUntouched=True, generatorSHA256=c.digest(evidence / "generator.json"),
            productManifestSHA256=c.digest(evidence / "products.json"), productRoot=str(products),
            descriptorRelativePath=descriptors[0].name, descriptorSHA256=c.digest(descriptors[0]))
    except BaseException as exc:
        result["firstFailure"] = {"type": type(exc).__name__, "reason": str(exc)}
        raise
    finally:
        result["ownedGroups"] = [{"pgid": pgid, "absentAtOriginalExit": pgid in commands.absent_groups}
                                 for pgid in sorted(commands.groups)]
        c.write(evidence / "receipt.json", result)
        print(json.dumps({k: v for k, v in result.items() if k != "uiCommand"}, sort_keys=True), flush=True)


if __name__ == "__main__": main()
