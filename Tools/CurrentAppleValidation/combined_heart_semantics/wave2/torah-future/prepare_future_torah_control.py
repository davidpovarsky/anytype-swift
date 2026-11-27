#!/usr/bin/env python3
"""Prepare exact CLOSED Torah source successors from the published F13 controls.

No common intake or App product is repinned. The original13 UI selections and
startup/lifecycle bodies remain exact; one finite G03 dispatch is additive.
The G02 companion changes only its startup-profile SHA literal in a separate
output directory, leaving the published four-stage consumer bodies unchanged.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ORIGINAL_HOST_SHA = "2e57294dc7a00d4302a9dd5f316b2419e75d6a08a4f55b47451d6c822335ec44"
ORIGINAL_PROFILE_SHA = "188fd2470d720a350718969c6bdd17250c107cbe2ceab2a1c72aa2508d00e0b3"
PROFILE_SHA = "6960a4f74aa6b582e783addf358cc1806728dffd520483336c877e473b63aeb9"
SOURCE_INVERSE_SHA = "6efa087677993cd5b4d98b3c03cc9c335354d5c01d5faace2064978ebf16810f"
G02_ORIGINAL_SHA = "7bc7c513cbaa0bcfcb98af6fd48c2fa4f391f15708c404fb2a7ef00ca91e55ac"
G02_SUCCESSOR_SHA = "d8f3b0509fff4dc369440831d23c70c5b124c0fa63e08b2d87702da428eca0b5"
NEW_FILES = ("torah_future_control.py", "torah_overflow_observations.py", "torah-future-closed-profile.json")
PAYLOAD = {
    "torah_future_control.py": "a1d864d5e7257faf1444af1c0335388c6f784d76afb75c6ec3578c7fed707747",
    "torah_overflow_observations.py": "cadd23e2aa1726bb01c7601c46a6f26072e2ecad4bd95a389154069f5d3f1e38",
    "torah-future-closed-profile.json": "d45c21aab18e5b736b511c3ec9bbb25d93ff346b1456f5ea938d65663c8bb49d",
    "torah_ui_profile.py": PROFILE_SHA,
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def changes():
    return (
        ("import torah_ui_consumer as torah_ui\n", "import torah_ui_consumer as torah_ui\nimport torah_future_control as future_torah\n"),
        ("PLANS = {\n", "PLANS = {\n    'torah-overflow-only': ('torah-source-overflow',),\n"),
        ("EXPECTED_TEST_PROFILES = {\n", "ORIGINAL_SERIES += ('torah-source-overflow',)\nEXPECTED_TEST_PROFILES = {\n"),
        ('budget = self.helpers["run_ui27"].selection_time_budget(target, methods)',
         'budget = future_torah.ui_budget(self, target, methods)'),
        ('    def execute_lane(self, lane):\n',
         '    def execute_lane(self, lane):\n'
         '        future_torah.require_runtime_ready(self.admission, Path(__file__).resolve().parent)\n'),
        ('            udid, language = self.create(lane, directory, editor=lane == "editor")\n',
         '            udid, language = self.create(future_torah.STARTUP_LANE if lane == future_torah.LANE else lane, directory, editor=lane == "editor")\n'),
        ('            if lane in torah_ui.UI_LANES:\n',
         '            if lane == future_torah.LANE:\n'
         '                result["actual"] = future_torah.run_overflow_lane(self, directory, udid)\n'
         '            elif lane in torah_ui.UI_LANES:\n'),
        ("'native_compiler_witness.py'}\n", "'native_compiler_witness.py', " + ", ".join(repr(name) for name in NEW_FILES) + "}\n"),
        ('    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")\n',
         '    future_torah.require_runtime_ready(admission, parent)\n'
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
        require(current.count(before) == 1, "Unique exact future Torah insertion required")
        current = current.replace(before, after, 1)
    restored = current
    for before, after in reversed(changes()):
        require(restored.count(after) == 1, "Unique exact future Torah inverse required")
        restored = restored.replace(after, before, 1)
    require(restored == old, "Future Torah host must restore every original byte")
    old_top, new_top = declarations(old), declarations(current)
    require(set(old_top) == set(new_top), "Original top-level declaration inventory changed")
    old_methods = {n.name: n for n in old_top["Consumer"].body if isinstance(n, ast.FunctionDef)}
    new_methods = {n.name: n for n in new_top["Consumer"].body if isinstance(n, ast.FunctionDef)}
    require(set(old_methods) == set(new_methods), "Original Consumer declaration inventory changed")
    unchanged_functions = sorted(set(old_top) - {"main", "Consumer"})
    unchanged_methods = sorted(set(old_methods) - {"execute_lane", "stage"})
    for name in unchanged_functions:
        require(segment(old, old_top[name]) == segment(current, new_top[name]), "Original helper/validator changed: " + name)
    for name in unchanged_methods:
        require(segment(old, old_methods[name]) == segment(current, new_methods[name]), "Original lane/lifecycle changed: " + name)
    budget_before, budget_after = changes()[3]
    require(segment(old, old_methods["stage"]).replace(budget_before, budget_after, 1)
            == segment(current, new_methods["stage"]), "Original stage may change only its one-selector UI budget delegation")
    for old_node, new_node in ((old_methods["execute_lane"], new_methods["execute_lane"]),
                               (old_top["main"], new_top["main"])):
        old_final = next(n for n in old_node.body if isinstance(n, ast.Try)).finalbody
        new_final = next(n for n in new_node.body if isinstance(n, ast.Try)).finalbody
        require([segment(old, n) for n in old_final] == [segment(current, n) for n in new_final],
                "Original retention/shutdown/group cleanup/product-integrity finally changed")
    return current.encode(), {
        "originalHostSHA256": sha(original), "candidateHostSHA256": sha(current.encode()),
        "exactFullInverse": True, "edits": [{"before": a, "after": b} for a, b in changes()],
        "unchangedOriginalFunctions": unchanged_functions, "unchangedOriginalMethods": unchanged_methods,
        "originalStageOnlyOneSelectorBudgetDelegationChanged": True,
        "originalMainAndOwnedLaneFinallyUnchanged": True,
        "originalCanonicalConsoleInspectorContinuityAndPropertiesSetPostflightUnchanged": True,
    }


def profile_inverse(original, candidate, inverse):
    require(sha(original) == ORIGINAL_PROFILE_SHA and sha(candidate) == PROFILE_SHA
            and sha(inverse) == SOURCE_INVERSE_SHA, "Exact reviewed source profile/inverse bytes required")
    proof = json.loads(inverse)
    old, current = original.decode("utf-8"), candidate.decode("utf-8")
    for row in reversed(proof["profileEdits"]):
        require(current.count(row["after"]) == 1, "Exact profile inverse occurrence changed")
        current = current.replace(row["after"], row["before"], 1)
    require(current == old, "Source compatibility must restore the complete original profile")
    a, b = declarations(old), declarations(candidate.decode("utf-8"))
    require(set(b) - set(a) == {"reviewed_original_ui_inverse"}
            and [name for name in a if segment(old, a[name]) != segment(candidate.decode("utf-8"), b[name])]
                == ["reviewed_ui_sources"], "Original startup console/environment/selector code changed")
    return proof


def g02_literal_successor(original):
    require(sha(original) == G02_ORIGINAL_SHA, "Exact separately published G02 consumer required")
    before = 'STARTUP_PROFILE_SHA = "' + ORIGINAL_PROFILE_SHA + '"'
    after = 'STARTUP_PROFILE_SHA = "' + PROFILE_SHA + '"'
    text = original.decode("utf-8")
    require(text.count(before) == 1, "Exact sole G02 profile dependency literal required")
    candidate = text.replace(before, after, 1)
    require(candidate.replace(after, before, 1) == text and sha(candidate.encode()) == G02_SUCCESSOR_SHA,
            "G02 successor must be the exact single literal change")
    a, b = declarations(text), declarations(candidate)
    require(set(a) == set(b) and all(segment(text, a[name]) == segment(candidate, b[name]) for name in a),
            "G02 source/phase/retention/gate body changed")
    return candidate.encode(), {"originalSHA256": G02_ORIGINAL_SHA, "candidateSHA256": G02_SUCCESSOR_SHA,
                                "before": before, "after": after, "exactSingleLiteralInverse": True,
                                "allFunctionBodiesUnchanged": True, "runtimeGateRemainsClosed": True,
                                "original17FileClosureShapeUnchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-host", type=Path, required=True)
    parser.add_argument("--original-profile", type=Path, required=True)
    parser.add_argument("--source-inverse", type=Path, required=True)
    parser.add_argument("--g02-original-consumer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "A fresh isolated source-preparation directory is required")
    host, host_proof = compose(args.original_host.read_bytes())
    here = Path(__file__).resolve().parent
    payload = {name: (here / name).read_bytes() for name in PAYLOAD}
    require(all(sha(payload[name]) == expected for name, expected in PAYLOAD.items()), "Exact reviewed future payload changed")
    source_proof = profile_inverse(args.original_profile.read_bytes(), payload["torah_ui_profile.py"], args.source_inverse.read_bytes())
    g02, g02_proof = g02_literal_successor(args.g02_original_consumer.read_bytes())
    closed = json.loads(payload["torah-future-closed-profile.json"])
    require(closed["runtimeReady"] is False and all(closed[key] is None for key in
            ("futureSourceCommit", "futureCommonIntake", "actualProducerReceipt", "actualSharedAdmission")),
            "All future runtime source/common/product/admission pins must remain null")
    args.output.mkdir(parents=True, mode=0o700)
    (args.output / "combined_host_acceptance_app15.py").write_bytes(host)
    for name, value in payload.items():
        (args.output / name).write_bytes(value)
    dependency = args.output / "g02-dependency-successor"
    dependency.mkdir(mode=0o700)
    (dependency / "g02_word_consumer.py").write_bytes(g02)
    proof = {"schema": "pinkha-future-torah-closed-materialization-v1", "status": "SOURCE_ONLY_RUNTIME_CLOSED",
             "materializerSHA256": sha(Path(__file__).read_bytes()), "host": host_proof,
             "sourceProfileInverseSHA256": sha(args.source_inverse.read_bytes()),
             "sourceProfile": {key: source_proof[key] for key in
                ("originalProfileSHA256", "candidateProfileSHA256", "Stage1SHA256", "ComprehensiveSHA256",
                 "Stage1OriginalPrefixSHA256", "Stage1ExactSuffixSHA256", "exactProfileInverse")},
             "payloadSHA256": {name: sha(value) for name, value in payload.items()}, "g02Dependency": g02_proof,
             "futureTorahClosureFiles": 16, "oldF13NotModifiedInPlace": True,
             "g02Existing17FileHostAndNativeAdapterUnchanged": True,
             "oldNativeCore15FileControlNotComposedHere": True,
             "commonIntakeCopiedOrRepinned": False, "runtimeReady": False,
             "appleInvocations": 0, "nativeCalls": 0, "XCTestMethodsExecuted": 0}
    (args.output / "materialization.json").write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": proof["status"], "hostSHA256": sha(host), "materializerSHA256": proof["materializerSHA256"],
                      "materializationSHA256": sha((args.output / "materialization.json").read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
