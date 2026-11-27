#!/usr/bin/env python3
"""Materialize a separate CLOSED two-method Heart editor F13 successor.

The common qualifier is never copied or repinned. The original stage, result
parsers and lifecycle stay exact except finite dispatch and budget delegation.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ORIGINAL_HOST_SHA = "2e57294dc7a00d4302a9dd5f316b2419e75d6a08a4f55b47451d6c822335ec44"
STARTUP_PROFILE_SHA = "6960a4f74aa6b582e783addf358cc1806728dffd520483336c877e473b63aeb9"
NEW_FILES = ("heart_editor_control.py", "heart_editor_observations.py", "heart-editor-closed-profile.json")
PAYLOAD = {
    "heart_editor_control.py": "7701368077ee2dac305574b5559546e04f5db6a653d15919a9294a9feff351e3",
    "heart_editor_observations.py": "693afa112eb0f2c54f89b1b2ba1b7f5f9b39bbbd811887a02993d39ae2534915",
    "heart-editor-closed-profile.json": "1fd8ab33fe4b55d07f66f1c0c1b8290a72aeb433198241cb7516520609a23d23",
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def changes():
    return (
        ("import torah_ui_consumer as torah_ui\n", "import torah_ui_consumer as torah_ui\nimport heart_editor_control as heart_editor\n"),
        ("PLANS = {\n", "PLANS = {\n"
         "    'heart-mutations-only': ('heart-editor-mutations',),\n"
         "    'heart-split-merge-only': ('heart-editor-split-merge',),\n"
         "    'heart-range-replacement-only': ('heart-editor-range-replacement',),\n"),
        ("EXPECTED_TEST_PROFILES = {\n",
         "ORIGINAL_SERIES += ('heart-editor-mutations', 'heart-editor-split-merge', 'heart-editor-range-replacement')\nEXPECTED_TEST_PROFILES = {\n"),
        ('budget = self.helpers["run_ui27"].selection_time_budget(target, methods)',
         'budget = heart_editor.ui_budget(self, target, methods)'),
        ('    def execute_lane(self, lane):\n',
         '    def execute_lane(self, lane):\n'
         '        heart_editor.require_runtime_ready(self.admission, Path(__file__).resolve().parent)\n'),
        ('            udid, language = self.create(lane, directory, editor=lane == "editor")\n',
         '            udid, language = self.create(heart_editor.STARTUP_LANE if lane in heart_editor.LANES else lane, directory, editor=lane == "editor" or lane in heart_editor.LANES)\n'),
        ('            if lane in torah_ui.UI_LANES:\n',
         '            if lane in heart_editor.LANES:\n'
         '                result["actual"] = heart_editor.run_lane(self, lane, directory, udid, language)\n'
         '            elif lane in torah_ui.UI_LANES:\n'),
        ("'native_compiler_witness.py'}\n", "'native_compiler_witness.py', " + ", ".join(repr(name) for name in NEW_FILES) + "}\n"),
        ('    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")\n',
         '    heart_editor.require_runtime_ready(admission, parent)\n'
         '    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")\n'),
    )


def declarations(text):
    return {node.name: node for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def segment(text, node):
    return ast.get_source_segment(text, node)


def compose(original):
    require(sha(original) == ORIGINAL_HOST_SHA, "Exact published F13 host required")
    old = original.decode("utf-8")
    current = old
    for before, after in changes():
        require(current.count(before) == 1, "Exact unique finite Heart insertion required")
        current = current.replace(before, after, 1)
    inverse = current
    for before, after in reversed(changes()):
        require(inverse.count(after) == 1, "Exact unique finite Heart inverse required")
        inverse = inverse.replace(after, before, 1)
    require(inverse == old, "The Heart successor must restore every original F byte")
    a, b = declarations(old), declarations(current)
    require(set(a) == set(b), "Original host declarations changed")
    old_methods = {n.name: n for n in a["Consumer"].body if isinstance(n, ast.FunctionDef)}
    new_methods = {n.name: n for n in b["Consumer"].body if isinstance(n, ast.FunctionDef)}
    require(set(old_methods) == set(new_methods), "Original Consumer declaration inventory changed")
    functions = sorted(set(a) - {"Consumer", "main"})
    methods = sorted(set(old_methods) - {"execute_lane", "stage"})
    for name in functions:
        require(segment(old, a[name]) == segment(current, b[name]), "Original validator/helper changed: " + name)
    for name in methods:
        require(segment(old, old_methods[name]) == segment(current, new_methods[name]), "Original lane/lifecycle changed: " + name)
    before, after = changes()[3]
    require(segment(old, old_methods["stage"]).replace(before, after, 1) == segment(current, new_methods["stage"]),
            "Original stage may change only the two-selector finite budget delegation")
    for old_node, new_node in ((a["main"], b["main"]), (old_methods["execute_lane"], new_methods["execute_lane"])):
        left = next(n for n in old_node.body if isinstance(n, ast.Try)).finalbody
        right = next(n for n in new_node.body if isinstance(n, ast.Try)).finalbody
        require([segment(old, n) for n in left] == [segment(current, n) for n in right],
                "Original main/owned-lane finally changed")
    return current.encode(), {
        "originalHostSHA256": sha(original), "candidateHostSHA256": sha(current.encode()), "fullInverse": True,
        "edits": [{"before": before, "after": after} for before, after in changes()],
        "unchangedOriginalFunctions": functions, "unchangedOriginalMethods": methods,
        "originalStageOnlyTwoSelectorBudgetDelegationChanged": True,
        "originalMainAndOwnedLaneFinallyUnchanged": True,
        "originalCreateFreshnessAndActualOppositeLanguageChecksUnchanged": True,
        "originalThirteenTorahAndFourEditorSelectionsUnchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-host", type=Path, required=True)
    parser.add_argument("--startup-profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Fresh separate source materialization required")
    host, inverse = compose(args.original_host.read_bytes())
    startup = args.startup_profile.read_bytes()
    require(sha(startup) == STARTUP_PROFILE_SHA, "Exact separately reviewed/published startup profile required")
    here = Path(__file__).resolve().parent
    payload = {name: (here / name).read_bytes() for name in NEW_FILES}
    require(all(sha(payload[name]) == expected for name, expected in PAYLOAD.items()), "Exact reviewed finite Heart payload changed")
    closed = json.loads(payload["heart-editor-closed-profile.json"])
    require(closed["runtimeReady"] is False and all(closed[key] is None for key in
            ("futureSourceCommit", "futureCommonIntake", "actualProducerReceipt", "actualSharedAdmission")),
            "Future source/common/producer/admission must remain unbound")
    args.output.mkdir(parents=True, mode=0o700)
    (args.output / "combined_host_acceptance_app15.py").write_bytes(host)
    (args.output / "torah_ui_profile.py").write_bytes(startup)
    for name, raw in payload.items():
        (args.output / name).write_bytes(raw)
    proof = {"schema": "pinkha-heart-editor-closed-materialization-v1", "status": "SOURCE_ONLY_RUNTIME_CLOSED",
             "materializerSHA256": sha(Path(__file__).read_bytes()), "host": inverse,
             "startupProfileSHA256": sha(startup), "startupProfilePublishedCommit": "a5ce10b1c73223906d102b6d4f08dcc381d9a34d",
             "payloadSHA256": {name: sha(raw) for name, raw in payload.items()},
             "closureFileCount": 16, "originalF13AndOtherDerivativesUnchangedInPlace": True,
             "commonIntakeCopiedOrRepinned": False, "newProcessManager": False,
             "newMethods": 2, "newXCTestCases": 2, "newDocumentFlows": 6,
             "singleMethodCommandAllowanceSeconds": 1500, "combinedCommandAllowanceSeconds": 2700,
             "allThreePlansUseNewOwnedSimulatorAndOriginalPreparation": True,
             "runtimeReady": False, "appleInvocations": 0, "nativeCalls": 0, "XCTestMethodsExecuted": 0}
    (args.output / "materialization.json").write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": proof["status"], "hostSHA256": sha(host),
                      "materializerSHA256": proof["materializerSHA256"],
                      "materializationSHA256": sha((args.output / "materialization.json").read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
