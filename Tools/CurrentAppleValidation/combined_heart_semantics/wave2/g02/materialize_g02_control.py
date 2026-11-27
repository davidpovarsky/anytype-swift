#!/usr/bin/env python3
"""Prepare a closed G02 derivative of the exact reviewed 13-file F consumer.

The current common intake/products are not repinned or copied. The derivative
contains the actual four-stage execution body but rejects G02 before common
product cloning or any simulator operation. A reviewed future successor must
bind the native adapter and actual matching complete App/UI producer.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ORIGINAL_HOST_SHA = "2e57294dc7a00d4302a9dd5f316b2419e75d6a08a4f55b47451d6c822335ec44"
NEW_FILES = ("g02_word_consumer.py", "g02_ui_receipts.py", "g02_native_phase.py", "g02-closed-profile.json")
NATIVE_ADAPTER_SHA = "072c57365a60ed812df8dfe6eb95d542194dbefa2069bb965a3633c9878faa63"


def require(value, reason):
    if not value: raise ValueError(reason)


def sha(value): return hashlib.sha256(value).hexdigest()


def changes():
    return (
        ("import torah_ui_consumer as torah_ui\n", "import torah_ui_consumer as torah_ui\nimport g02_word_consumer as g02\n"),
        ("PLANS = {\n", "PLANS = {\n    'g02-word-only': ('g02-word',),\n"),
        ("EXPECTED_TEST_PROFILES = {\n", "ORIGINAL_SERIES += ('g02-word',)\nEXPECTED_TEST_PROFILES = {\n"),
        ('budget = self.helpers["run_ui27"].selection_time_budget(target, methods)',
         'budget = g02.ui_budget(self, target, methods)'),
        ('            udid, language = self.create(lane, directory, editor=lane == "editor")\n',
         '            if lane == g02.LANE:\n'
         '                g02.require_runtime_ready(self.admission, Path(__file__).resolve().parent)\n'
         '            udid, language = self.create(g02.STARTUP_LANE if lane == g02.LANE else lane, directory, editor=lane == "editor")\n'),
        ('            if lane in torah_ui.UI_LANES:\n',
         '            if lane == g02.LANE:\n'
         '                result["actual"] = g02.run_word_lane(self, directory, udid)\n'
         '            elif lane in torah_ui.UI_LANES:\n'),
        ("'native_compiler_witness.py'}\n", "'native_compiler_witness.py', " + ", ".join(repr(name) for name in NEW_FILES) + "}\n"),
        ('    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")\n',
         '    if admission["plan"] == g02.PLAN:\n'
         '        g02.require_runtime_ready(admission, parent)\n'
         '    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")\n'),
    )


def nodes(text):
    top = {n.name: n for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    methods = {n.name: n for n in top["Consumer"].body if isinstance(n, ast.FunctionDef)}
    return top, methods


def source(text, node): return ast.get_source_segment(text, node)


def compose(original):
    require(sha(original) == ORIGINAL_HOST_SHA, "Exact published additive F consumer required")
    old = original.decode(); current = old
    for before, after in changes():
        require(current.count(before) == 1, "Unique G02 insertion required: " + before[:100])
        current = current.replace(before, after, 1)
    inverse = current
    for before, after in reversed(changes()):
        require(inverse.count(after) == 1, "Exact unique G02 inverse required")
        inverse = inverse.replace(after, before, 1)
    require(inverse == old, "G02 derivative must restore every original F byte")
    compile(current, "combined_host_acceptance_app15.py", "exec")
    old_top, old_methods = nodes(old); new_top, new_methods = nodes(current)
    untouched_functions = sorted(set(old_top) - {"Consumer", "main"})
    untouched_methods = sorted(set(old_methods) - {"execute_lane", "stage"})
    require(set(old_top) == set(new_top) and set(old_methods) == set(new_methods), "Unexpected original declarations changed")
    for name in untouched_functions:
        require(source(old, old_top[name]) == source(current, new_top[name]), "Original validator/helper changed: " + name)
    for name in untouched_methods:
        require(source(old, old_methods[name]) == source(current, new_methods[name]), "Original owned lifecycle/lanes changed: " + name)
    budget_before, budget_after = changes()[3]
    require(source(old, old_methods["stage"]).replace(budget_before, budget_after, 1) == source(current, new_methods["stage"]),
            "The original stage may change only its narrowly delegated UI budget expression")
    old_final = next(n for n in old_methods["execute_lane"].body if isinstance(n, ast.Try)).finalbody
    new_final = next(n for n in new_methods["execute_lane"].body if isinstance(n, ast.Try)).finalbody
    require([source(old, n) for n in old_final] == [source(current, n) for n in new_final],
            "Original preservation, shutdown, failure retention or final product integrity changed")
    proof = {"schema": "pinkha-g02-closed-control-inverse-v1", "status": "PASS_SOURCE_MATERIALIZATION_NOT_EXECUTION",
             "originalHostSHA256": sha(original), "materializedHostSHA256": sha(current.encode()),
             "inverseRestoresEveryOriginalByte": True, "unchangedFunctions": untouched_functions,
             "unchangedMethods": untouched_methods, "unchangedOwnedSimulatorFinally": True,
             "unchangedStageExceptTwoSelectorBudgetDispatch": True, "unchangedOriginalBudgetHelper": True,
             "newPlan": {"g02-word-only": ["g02-word"]}, "startupLane": "properties",
             "newControllerFiles": list(NEW_FILES), "original13FileClosureChangedInPlace": False,
             "commonProductAdmissionChanged": False, "nativeAdapterRequired": True, "runtimeReady": False,
             "AppBuilds": 0, "UIBuilds": 0, "XCTestInvocations": 0, "nativeCalls": 0}
    return current.encode(), proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-host", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Fresh source preparation directory required")
    current, proof = compose(args.original_host.read_bytes())
    here = Path(__file__).resolve().parent
    copies = {name: (here / name).read_bytes() for name in NEW_FILES}
    profile = json.loads(copies["g02-closed-profile.json"])
    require(profile.get("runtimeReady") is False
            and profile.get("nativeAdapter") == {"path": "g02_native_phase.py", "sha256": NATIVE_ADAPTER_SHA}
            and sha(copies["g02_native_phase.py"]) == NATIVE_ADAPTER_SHA
            and profile.get("actualFutureProducer") == "PENDING_SOURCE_FREEZE_AND_SUCCESSFUL_APP_AND_COMPLETE_UI",
            "Only the explicit closed future preparation may be materialized here")
    args.output.mkdir(parents=True, mode=0o700)
    (args.output / "combined_host_acceptance_app15.py").write_bytes(current)
    for name, data in copies.items(): (args.output / name).write_bytes(data)
    proof["newControllerHashes"] = {name: sha(raw) for name, raw in copies.items()}
    proof["nativeAdapterPresent"] = True
    (args.output / "materialization.json").write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__": main()
