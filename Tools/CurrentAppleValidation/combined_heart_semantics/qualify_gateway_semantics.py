"""Verify exact current profile bindings; this executes no Apple or engine work."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile

import retain_owned_heart_account as retention


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    base = Path(__file__).parent
    original = (base / "combined_heart_semantics.py").read_bytes()
    current = (base / "combined_heart_semantics_gateway.py").read_bytes()
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

    assert ast.dump(ExactProfile().visit(ast.parse(original)), include_attributes=False) == ast.dump(
        ast.parse(current), include_attributes=False)
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
        "fixedProfileBindings": replacements, "entireControllerASTEquivalentAfterExactBindings": True,
        "observationPredicateASTEquivalent": True, "originalSixSelectorsAndDeadlinesUnchanged": True,
        "unresolvedExternalAndAbsoluteLinksRejected": external_controls,
        "AppleTestsExecuted": 0, "engineCalls": 0,
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
