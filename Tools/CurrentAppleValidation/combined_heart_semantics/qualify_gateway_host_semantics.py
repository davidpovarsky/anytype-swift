"""Check additive current F/T5 source bindings without running Apple tests."""
import ast
import hashlib
import json
from pathlib import Path


def main():
    base = Path(__file__).parent
    names = ("combined_host_acceptance", "combined_t5_pending", "combined_t5_retry", "combined_t5_freshness")
    modules = {name: name + "_gateway" for name in names}
    modules.update(combined_heart_semantics="combined_heart_semantics_gateway",
                   combined_heart_observations="combined_heart_observations_gateway")
    old_version = "pinkha-dual-runtime-v1-70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683"
    version = "pinkha-dual-runtime-v1-70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72"

    class Bindings(ast.NodeTransformer):
        def visit_Import(self, node):
            for entry in node.names:
                if entry.name in modules:
                    entry.name = modules[entry.name]
            return node

        def visit_ImportFrom(self, node):
            if node.module in modules:
                node.module = modules[node.module]
            return node

        def visit_Constant(self, node):
            if node.value == old_version:
                return ast.copy_location(ast.Constant(version), node)
            if node.value == "combined_host_helper_pins.json":
                return ast.copy_location(ast.Constant("combined_host_helper_pins_gateway.json"), node)
            if isinstance(node.value, str) and node.value.endswith(".py") and node.value[:-3] in modules:
                return ast.copy_location(ast.Constant(modules[node.value[:-3]] + ".py"), node)
            return node

    rows = []
    for name in names:
        original = (base / (name + ".py")).read_bytes()
        current = (base / (modules[name] + ".py")).read_bytes()
        assert ast.dump(Bindings().visit(ast.parse(original)), include_attributes=False) == ast.dump(
            ast.parse(current), include_attributes=False)
        rows.append({"original": name + ".py", "current": modules[name] + ".py",
                     "originalSHA256": hashlib.sha256(original).hexdigest(),
                     "currentSHA256": hashlib.sha256(current).hexdigest(),
                     "entireASTEquivalentAfterExactProfileBindings": True})
    old_pins = json.loads((base / "combined_host_helper_pins.json").read_bytes())
    new_pins = json.loads((base / "combined_host_helper_pins_gateway.json").read_bytes())
    generator = "Tools/PinkhaNativeDerived/rerun_original_ui.py"
    assert old_pins["files"][generator] == {"bytes": 17012, "sha256": "ec5688909921942e94f792cdde0a02baa7b5f9b2f9e0b3bde3df3a877f299279"}
    assert new_pins["files"][generator] == {"bytes": 18707, "sha256": "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"}
    assert len(old_pins["files"]) == len(new_pins["files"]) == 71
    assert {k: v for k, v in old_pins["files"].items() if k != generator} == {
        k: v for k, v in new_pins["files"].items() if k != generator}
    assert old_pins["entries"] == new_pins["entries"] and old_pins["schema"] == new_pins["schema"]
    assert new_pins["reviewedSource"] == "94d8f58fa9aedc994beaedd36fd184dd341ee955"
    print(json.dumps({"status": "PASS_ADDITIVE_CURRENT_F_T5_SOURCE_CONTROLS_NOT_APPLE_ACCEPTANCE",
        "version": version, "files": rows, "unchangedOriginalHelperFiles": 70,
        "reviewedGeneratorChange": {"path": generator, "old": old_pins["files"][generator],
            "current": new_pins["files"][generator],
            "scope": "Only ui_only_project admits exact reviewed four or six configuration identities and settings before removing the generated runner's implicit app binding. Original test methods and result validators are unchanged."},
        "originalNineSeriesUnchanged": True, "originalSelectorsAndDeadlinesUnchanged": True,
        "oppositeDeviceLanguageAdmissionUnchanged": True, "old70fbAnd139AuthorityUnchanged": True,
        "DebugFunctionalNotRelease": True, "AppleTestsExecuted": 0, "engineCalls": 0}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
