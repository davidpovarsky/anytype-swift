#!/usr/bin/env python3
"""Source equivalence and rejection controls; executes no Apple build or tests."""
import argparse
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
import combined_heart_semantics as c
import semantic_source_menu_override as p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def git_file(commit, name):
        return subprocess.check_output(["git", "-C", str(args.source), "show", commit + ":" + name], timeout=30)
    original = git_file(p.BASE, p.FILE)
    candidate = git_file(p.CHANGE, p.FILE)
    delta = p.source_delta(c, original, candidate)
    c.require(c.sha(git_file(p.GENERATOR_COMMIT, "Tools/PinkhaNativeDerived/rerun_original_ui.py")) == p.GENERATOR,
              "Actual original producer generator source changed")
    c.require(c.digest(Path(p.__file__).with_name("build_semantic_menu_ui.py")) == p.BUILDER,
              "Exact builder pin differs")
    denied = []
    for label, before, after in (
        ("changed-original", original + b"\n", candidate),
        ("changed-reviewed-ui", original, candidate + b"\n"),
        ("old-unfixed-ui", original, original),
    ):
        try:
            p.source_delta(c, before, after)
        except ValueError:
            denied.append(label)
        else:
            raise ValueError("Source override accepted: " + label)
    receipt = {"status": p.STATUS, "appSourceCommit": p.BASE, "uiTestChangeCommit": p.CHANGE,
               "uiBuilds": 1, "appBuilds": 0, "nativeBuilds": 0, "testsExecuted": 0,
               "originalProducerReceiptSHA256": "a" * 64, "generatorSHA256": p.GENERATOR,
               "generatorCommit": p.GENERATOR_COMMIT}
    admission = {"schema": "pinkha-combined-heart-semantics-admission-v1", "sourceCommit": p.BASE,
                 "producerReceipt": {"sha256": "a" * 64},
                 "menuPagingUIOverride": {"profile": p.PROFILE, "receipt": {}}}
    invalid = [("uiBuilds", 0), ("uiBuilds", 2), ("uiBuilds", True), ("appBuilds", 1),
               ("appBuilds", False), ("nativeBuilds", 1), ("testsExecuted", 1),
               ("testsExecuted", False), ("appSourceCommit", "b" * 40),
               ("uiTestChangeCommit", p.BASE), ("generatorSHA256", "b" * 64)]
    for key, value in invalid:
        changed = dict(receipt, **{key: value})
        with patch.object(c, "pinned", return_value=json.dumps(changed).encode()):
            try:
                p.qualify(c, admission, Path("/not-used"), {})
            except ValueError as exc:
                c.require(str(exc) == "Actual reviewed independent complete UI build receipt required",
                          "Bad receipt was rejected after its intended admission boundary")
                denied.append(key + "=" + repr(value))
            else:
                raise ValueError("Bad UI producer receipt was accepted")
    for schema in ("pinkha-combined-host-acceptance-admission-v1", "unknown"):
        changed = copy.deepcopy(admission); changed["schema"] = schema
        try:
            p.qualify(c, changed, Path("/not-used"), {})
        except ValueError as exc:
            c.require(str(exc) == "One explicit original-app/source-menu UI-only pairing required",
                      "Foreign admission reached file reads")
            denied.append("schema=" + schema)
        else:
            raise ValueError("Foreign scope allowed the E override")
    name = "Tools/CurrentAppleValidation/combined_heart_semantics/combined_heart_semantics.py"
    baseline = ast.parse(git_file("ca6781f6ad8c32bdee132cfec3c3a5f2504a9dc9", name))
    current = ast.parse(c.raw(Path(c.__file__)))
    old_fn = next(n for n in baseline.body if isinstance(n, ast.FunctionDef) and n.name == "admit_and_clone_products")
    new_fn = copy.deepcopy(next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == old_fn.name))
    optional = [n for n in new_fn.body if isinstance(n, ast.If)
                and ast.dump(n.test) == ast.dump(ast.parse('"menuPagingUIOverride" in admission', mode="eval").body)]
    c.require(len(optional) == 1, "One explicit optional E-only admission branch required")
    new_fn.body.remove(optional[0])
    c.require(ast.dump(old_fn, include_attributes=False) == ast.dump(new_fn, include_attributes=False),
              "Original app/native/source/products admission changed outside explicit UI-only extension")
    result = {"status": "PASS_SOURCE_EQUIVALENCE_AND_NEGATIVE_CONTROLS_NOT_APPLE_ACCEPTANCE",
              "originalAppSource": p.BASE, "reviewedUITestChange": p.CHANGE, "sourceDelta": delta,
              "originalAdmissionUnchangedWithoutOptionalEOverride": True,
              "deniedCases": denied, "deniedCaseCount": len(denied),
              "AppleBuilds": 0, "nativeCalls": 0, "XCTestMethodsExecuted": 0,
              "controllerSHA256": c.digest(Path(c.__file__)), "profileSHA256": c.digest(Path(p.__file__)),
              "builderSHA256": p.BUILDER}
    c.write(args.output, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
