"""Focused controls for the explicitly authorized continuation consumer.

These are controller contracts, not Apple, native runtime or product tests.
Producer validation executes the existing implementation without a substitute.
The Wave-15 identity function is compiled from its exact AST to avoid loading
unrelated UI controllers; no omitted dependency participates in that function.
"""
import ast
import copy
import json
from pathlib import Path
import re
import unittest

import coherent_runtime_admission as admission
import heart_runtime_profile as profiles
import install_verified_heart as installer

CONTINUATION = "codex/chatgpt-wave15-acceptance-continuation-20261122"
SHARED = "codex/chatgpt-wave15-shared-20261121"
CANONICAL = "codex/chatgpt-wave15-canonical-hanlin-20261123"
SOURCE = "58b9de8f7a26d798e18e301ad1ed8be14f2a8c14"
REPOSITORY = "davidpovarsky/anytype-swift"


def wave15_identity():
    path = Path(__file__).resolve().parents[1] / "PinkhaSimulatorGate/run_wave15_acceptance.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    constants = {"BRANCH", "CONSUMER_BRANCH", "UI_RESUME_BRANCH", "SHARED_BRANCH",
                 "CONTINUATION_BRANCH", "APPROVED_BRANCHES"}
    functions = {"require", "require_source_identity"}
    nodes = [node for node in tree.body if
             (isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id in constants)
             or (isinstance(node, ast.FunctionDef) and node.name in functions)]
    if len(nodes) != len(constants) + len(functions):
        raise AssertionError("The exact reviewed Wave-15 identity closure changed")
    namespace = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


class ContinuationBranchTests(unittest.TestCase):
    def test_exact_consumer_branch_head_and_ref_are_still_required(self):
        identity = wave15_identity()
        self.assertIn(CONTINUATION, installer.APPROVED_BRANCHES)
        verify = identity["require_source_identity"]
        for branch in identity["APPROVED_BRANCHES"]:
            verify(SOURCE, SOURCE, branch, "refs/heads/" + branch)
        for branch, head, ref in (
            (CONTINUATION + "-unreviewed", SOURCE, "refs/heads/" + CONTINUATION + "-unreviewed"),
            (CONTINUATION, SOURCE, "refs/heads/" + SHARED),
            (CONTINUATION, "0" * 40, "refs/heads/" + CONTINUATION),
            (SHARED, SOURCE, "refs/heads/" + CONTINUATION),
        ):
            with self.subTest(branch=branch, head=head, ref=ref), self.assertRaises(ValueError):
                verify(head, SOURCE, branch, ref)
        self.assertNotIn(CONTINUATION + "-unreviewed", installer.APPROVED_BRANCHES)

    def test_continuation_maps_only_to_the_original_shared_producer(self):
        original = {
            "id": 45046643716, "status": "completed", "conclusion": "success",
            "head_sha": SOURCE, "run_attempt": 1,
            "path": ".github/workflows/torah-inspector-ipados27.yml", "event": "workflow_dispatch",
            "head_branch": SHARED, "repository": {"full_name": REPOSITORY},
            "display_title": "Pinkha coherent-heart-apple · " + SOURCE,
        }
        def verify(value, consumer):
            return profiles.validate_producer(value, "45046643716", REPOSITORY,
                                              admission.expected_producer_branch(consumer), profiles.COHERENT)
        shared_result = verify(original, SHARED)
        self.assertEqual(verify(original, CONTINUATION), shared_result)
        self.assertEqual(shared_result["source_branch"], SHARED)
        self.assertEqual(shared_result["source_sha"], SOURCE)
        for branch in installer.APPROVED_BRANCHES:
            if branch not in (CONTINUATION, CANONICAL):
                self.assertEqual(admission.expected_producer_branch(branch), branch)
        for field, value in (
            ("head_branch", CONTINUATION), ("head_branch", CONTINUATION + "-unreviewed"),
            ("id", 45046643717), ("status", "in_progress"), ("conclusion", "failure"),
            ("head_sha", "unbound"), ("run_attempt", 0), ("event", "push"),
            ("path", ".github/workflows/unreviewed.yml"),
            ("repository", {"full_name": "unreviewed/anytype-swift"}),
            ("display_title", "Pinkha coherent-heart-apple · " + "0" * 40),
        ):
            changed = copy.deepcopy(original)
            changed[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                verify(changed, CONTINUATION)
        with self.assertRaises(RuntimeError):
            verify(original, CONTINUATION + "-unreviewed")


class CanonicalConsumerBranchTests(unittest.TestCase):
    def test_exact_native_and_component_candidate_identity_is_required(self):
        native_identity = wave15_identity()["require_source_identity"]
        source = Path(__file__).resolve().parents[1] / "Hanlin/run_host_tests.py"
        tree = ast.parse(source.read_text())
        constants = {"BRANCH", "CONSUMER_BRANCH", "ANY_ENGINE_BRANCH", "UI_RESUME_BRANCH", "SHARED_BRANCH", "APPROVED_BRANCHES"}
        functions = {"require", "require_identity"}
        nodes = [node for node in tree.body if
                 (isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name) and node.targets[0].id in constants)
                 or (isinstance(node, ast.FunctionDef) and node.name in functions)]
        self.assertEqual(len(nodes), len(constants) + len(functions))
        namespace = {"re": re}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
        component_identity = namespace["require_identity"]
        self.assertIn(CANONICAL, installer.APPROVED_BRANCHES)
        native_identity(SOURCE, SOURCE, CANONICAL, "refs/heads/" + CANONICAL)
        component_identity(SOURCE, SOURCE, CANONICAL, CANONICAL, "45091223011", "1")
        for branch, head, ref in (
            (CANONICAL + "-unreviewed", SOURCE, "refs/heads/" + CANONICAL + "-unreviewed"),
            (CANONICAL, SOURCE, "refs/heads/" + SHARED),
            (CANONICAL, "0" * 40, "refs/heads/" + CANONICAL),
        ):
            with self.subTest(branch=branch, head=head), self.assertRaises(ValueError):
                native_identity(head, SOURCE, branch, ref)
        for actual, expected, head in ((CANONICAL, SHARED, SOURCE), (SHARED, CANONICAL, SOURCE),
                                      (CANONICAL, CANONICAL, "0" * 40),
                                      (CANONICAL + "-unreviewed", CANONICAL + "-unreviewed", SOURCE)):
            with self.subTest(actual=actual, expected=expected), self.assertRaises(ValueError):
                component_identity(head, SOURCE, actual, expected, "45091223011", "1")
        self.assertNotIn(CANONICAL + "-unreviewed", installer.APPROVED_BRANCHES)

    def test_original_current_producer_remains_bound_to_shared_branch(self):
        root = Path(__file__).resolve().parents[2]
        path = root / "docs/validation/20261123-canonical-native-admission/producer-current.json"
        original = json.loads(path.read_text())
        def verify(value, consumer=CANONICAL):
            return profiles.validate_producer(value, "45091223011", REPOSITORY,
                                               admission.expected_producer_branch(consumer), profiles.COHERENT)
        current = verify(original)
        self.assertEqual(current, verify(original, SHARED))
        self.assertEqual(current["source_sha"], "8b08033135f7cb508e813ab1d47d81c255037c07")
        self.assertEqual(current["source_branch"], SHARED)
        for field, value in (("head_branch", CANONICAL), ("id", 45091223012),
                             ("conclusion", "failure"), ("run_attempt", 0),
                             ("head_sha", "0" * 40), ("path", ".github/workflows/unreviewed.yml")):
            changed = copy.deepcopy(original)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                verify(changed)
        with self.assertRaises(RuntimeError):
            verify(original, CANONICAL + "-unreviewed")


if __name__ == "__main__":
    unittest.main()
