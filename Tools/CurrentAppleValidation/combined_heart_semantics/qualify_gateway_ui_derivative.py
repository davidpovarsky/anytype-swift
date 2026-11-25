"""Verify exact current profile bindings; this executes no Apple or engine work."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import retain_owned_heart_account as retention
import current_ui_helper_derivative as ui_derivative


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-delta-before", type=Path, required=True)
    parser.add_argument("--source-delta-after", type=Path, required=True)
    args = parser.parse_args()
    base = Path(__file__).parent
    original = (base / "combined_heart_semantics.py").read_bytes()
    current = (base / "combined_heart_semantics_gateway_derivative.py").read_bytes()
    old_observation = (base / "combined_heart_observations.py").read_bytes()
    observation = (base / "combined_heart_observations_gateway.py").read_bytes()
    assert digest(old_observation) == "5fdb87695e37226833503a3f8e6ab3347b689859cb8f241493a876a054e3611d"
    replacements = {
        "70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683": "70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72",
        "08f8b8dab68ed21cabec955fbde1323983f02f549dd67aa3e2e4d11c4f818bfc": "c3374a58dffb64658fe6840ee9bd2711a4b1bf8c449c32da5bd51ede4901cece",
        "bb5582d3f0b9bc17b909ade4751904fd7b2fee2d066fea50b7a1ef913a8fe513": "ffc47556534ee279d01bb771c6d49637766e8828bd872cce739e541d8ce4f124",
        "67edd8f955524044428bf583b51f2357ca290e5ded0aacd8def0dff92f6b1521": "0ae5a1476c899b1790f01a2a3b4118034e848d8ad8dcf2d97f12104f7387f798",
        digest(old_observation): digest(observation),
        "combined_heart_observations.py": "combined_heart_observations_gateway.py",
        "combined_heart_observations": "combined_heart_observations_gateway",
    }

    class ExactProfile(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value in replacements:
                return ast.copy_location(ast.Constant(value=replacements[node.value]), node)
            return node

    derivative_insert = '''    expected_ui_commit = admission["sourceCommit"]
    derivative_proof = None
    if "currentUIHelperDerivative" in admission:
        require("menuPagingUIOverride" not in admission, "Distinct original UI derivations cannot be combined")
        helper = Path(__file__).with_name("current_ui_helper_derivative.py")
        require(digest(helper) == CURRENT_UI_DERIVATIVE_HELPER, "Exact reviewed current UI derivative authority required")
        import current_ui_helper_derivative as ui_derivative
        require(Path(ui_derivative.__file__).resolve() == helper.resolve(), "Foreign current UI derivative authority")
        derivative_proof = ui_derivative.qualify(sys.modules[__name__], admission, original_source, build_receipt, evidence)
        expected_ui_commit = derivative_proof["actualUISourceCommit"]
        write(evidence / "current-ui-helper-derivative-admission.json", derivative_proof)
'''
    helper_sha = digest((base / "current_ui_helper_derivative.py").read_bytes())
    assert helper_sha == "1c313b0ffc97855c330d6a7db4d0d6bfc6e75af6954993d14e23a49d9558bddc"
    inverses = (
        ('CURRENT_UI_DERIVATIVE_HELPER = "' + helper_sha + '"\n', ''),
        (derivative_insert, ''),
        ('step["sourceCommit"] == (expected_ui_commit if kind == "ui" else admission["sourceCommit"])',
         'step["sourceCommit"] == admission["sourceCommit"]'),
        ('    if derivative_proof is not None:\n        source_proof["currentUIHelperDerivative"] = derivative_proof\n', ''),
    )
    normalized_current = current.decode()
    for addition, original_value in inverses:
        assert normalized_current.count(addition) == 1
        normalized_current = normalized_current.replace(addition, original_value)
    assert ast.dump(ExactProfile().visit(ast.parse(original)), include_attributes=False) == ast.dump(
        ast.parse(normalized_current), include_attributes=False)
    def required(value, message):
        if not value:
            raise ValueError(message)
    authority = SimpleNamespace(sha=digest, require=required)
    before, after = args.source_delta_before.read_bytes(), args.source_delta_after.read_bytes()
    source_delta = ui_derivative.source_delta(authority, before, after)
    rejected = []
    for label, older, newer in (
        ("unrelated-original-change", before + b"\n", after),
        ("unrelated-fixed-change", before, after + b"\n"),
        ("missing-isolation-fix", before, before),
        ("reversed-source-pair", after, before),
        ("changed-original-assertion", before, after.replace(b"objects > 0", b"objects >= 0", 1)),
    ):
        assert (older, newer) != (before, after)
        try:
            ui_derivative.source_delta(authority, older, newer)
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError("Foreign UI source pair accepted: " + label)
    predicates = []
    for text in (old_observation, observation):
        node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "observations")
        predicates.append(ast.dump(node, include_attributes=False))
    assert predicates[0] == predicates[1]
    external_controls = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        inside = root / "account"; inside.mkdir()
        (inside / "database").write_bytes(b"original shutdown database bytes")
        (inside / "relative").symlink_to("database")
        assert retention.inventory(inside)["relative"]["target"] == "database"
        for label, target in (("external", root / "foreign"), ("absolute", inside / "database")):
            (root / "foreign").write_bytes(b"outside unretained root")
            link = inside / label
            link.symlink_to(target)
            try:
                retention.inventory(inside)
            except ValueError:
                external_controls.append(label)
            else:
                raise AssertionError("Unresolved private account link was accepted")
            link.unlink()
    assert external_controls == ["external", "absolute"]
    result = {
        "status": "PASS_EXACT_PROFILE_AND_PRIVATE_RETENTION_CONTROLS_NOT_APPLE_ACCEPTANCE",
        "oldControllerSHA256": digest(original), "currentControllerSHA256": digest(current),
        "oldObservationsSHA256": digest(old_observation), "currentObservationsSHA256": digest(observation),
        "retentionHelperSHA256": digest((base / "retain_owned_heart_account.py").read_bytes()),
        "fixedProfileBindings": replacements, "entireControllerASTEquivalentAfterExactBindingsAndReviewedDerivativeInverse": True,
        "exactDerivativeRoutingInverseEdits": len(inverses), "uiDerivativeHelperSHA256": helper_sha,
        "actualSourceDelta": source_delta, "foreignUISourcePairsRejected": rejected,
        "observationPredicateASTEquivalent": True, "originalSixSelectorsAndDeadlinesUnchanged": True,
        "unresolvedExternalAndAbsoluteLinksRejected": external_controls,
        "AppleTestsExecuted": 0, "engineCalls": 0,
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
