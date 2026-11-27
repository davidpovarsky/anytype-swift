#!/usr/bin/env python3
"""Add the reviewed Torah/editor prerequisites to the exact original F host.

This materializer changes no common product-admission function or product pin.
The separate Wave3 common intake must admit its actual frozen producer before
this host can execute any original method. No application work occurs here.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ORIGINAL_HOST_SHA256 = "e8776c517b57fffbe5e941be0df64eade3b4fcc6c5411aceffa56adaec0c681b"
NEW_PLANS = {
    "inspector-only": ("inspector",),
    "inspector-search-only": ("inspector-search",),
    "properties-only": ("properties",),
    "properties-set-only": ("properties-set",),
    "canonical-properties-only": ("canonical-properties",),
    "quote-drop-only": ("quote-drop",),
    "properties-hosted-only": ("properties-hosted",),
    "related-hosted-only": ("related-hosted",),
    "inspector-hosted-only": ("inspector-hosted",),
    "library-hosted-only": ("library-hosted",),
    "rtl-hosted-only": ("rtl-hosted",),
}
NEW_CONTROL_FILES = (
    "torah_ui_profile.py", "torah_ui_consumer.py", "torah_hosted_profile.py",
    "rtl_hosted_profile.py", "native_compiler_witness.py",
)
UNCHANGED_FUNCTIONS = (
    "freeze_helpers", "load_helpers", "scoped_descriptor", "exact_enumeration",
    "result_selection", "observe_owned_groups",
)
UNCHANGED_METHODS = (
    "command", "container", "installed", "create", "appearance", "stage",
    "read_private", "preserve", "pending", "freshness", "native_ui",
)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def changes():
    return (
        ("import combined_heart_semantics_current as shared\n",
         "import combined_heart_semantics_current as shared\nimport torah_ui_consumer as torah_ui\n"),
        ('    "return-controls-only": ("return-controls",),\n',
         '    "return-controls-only": ("return-controls",),\n' +
         "".join("    " + repr(name) + ": " + repr(lanes) + ",\n" for name, lanes in NEW_PLANS.items())),
        ("'t5-native-ui', 'focus-lifecycle')\n", "'t5-native-ui', 'focus-lifecycle', 'inspector', 'inspector-search', "
         "'properties', 'canonical-properties', 'properties-hosted', 'related-hosted', 'inspector-hosted', 'library-hosted', 'rtl-hosted')\n"),
        ('    if host_contract.get("kind") == "focus-lifecycle":\n',
         '    if host_contract.get("kind") == "rtl-hosted":\n'
         '        import rtl_hosted_profile\n'
         '        return rtl_hosted_profile.invocation_selectors(selectors, host_contract)\n'
         '    if host_contract.get("kind") in ("properties-hosted", "related-hosted", "inspector-hosted", "library-hosted"):\n'
         '        import torah_hosted_profile\n'
         '        return torah_hosted_profile.invocation_selectors(selectors, host_contract)\n'
         '    if host_contract.get("kind") == "focus-lifecycle":\n'),
        ('def host_validation_module(contract, helpers):\n',
         'def host_validation_module(contract, helpers):\n'
         '    if contract.get("kind") == "rtl-hosted":\n'
         '        import rtl_hosted_profile\n'
         '        return rtl_hosted_profile\n'
         '    if contract.get("kind") in ("properties-hosted", "related-hosted", "inspector-hosted", "library-hosted"):\n'
         '        import torah_hosted_profile\n'
         '        return torah_hosted_profile.validators(contract["kind"])\n'),
        ('        self.source = Path(admission["sourceRoot"])\n',
         '        self.source = Path(admission["sourceRoot"])\n'
         '        self.shared_module = shared\n'),
        ('    def wave(self, lane, directory, udid, language):\n',
         '    def wave(self, lane, directory, udid, language):\n'
         '        startup_source = torah_ui.before_ui(self, lane)\n'),
        ('        prep, _ = self.stage(directory, "preparation", udid, [spec["preparation"] + "()"], env)\n',
         '        prep, prep_path = self.stage(directory, "preparation", udid, [spec["preparation"] + "()"], env)\n'),
        ('        ui_env.update(PINKHA_UI27_APP_LANGUAGE=self.admission["appLanguage"], PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")\n',
         '        ui_env.update(PINKHA_UI27_APP_LANGUAGE=self.admission["appLanguage"], PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")\n'
         '        ui_env, startup_context = torah_ui.prepare_ui(self, lane, directory, udid, prep, prep_path, fixture_raw, ui_env)\n'),
        ('        ui_result, ui_path = self.stage(directory, "ui", udid, methods, ui_env, target=UI)\n',
         '        ui_result, ui_path = self.stage(directory, "ui", udid, methods, ui_env, target=UI)\n'
         '        startup = torah_ui.after_ui(self, lane, ui_path, startup_context, methods, startup_source)\n'),
        ('                   "deviceLanguage": language, "physicalDeviceAccepted": False, "visualReview": "PENDING"}\n',
         '                   "deviceLanguage": language, "physicalDeviceAccepted": False, "visualReview": "PENDING",\n'
         '                   "originalStartupPrerequisites": startup}\n'),
        ('            if lane in ("editor", "quote-drop", "properties-set"):\n',
         '            if lane in torah_ui.UI_LANES:\n'),
        ('            elif lane == "t5-host-actions":\n',
         '            elif lane in ("properties-hosted", "related-hosted", "inspector-hosted", "library-hosted", "rtl-hosted"):\n'
         '                import torah_hosted_profile\n'
         '                result["actual"] = torah_hosted_profile.run_hosted(self, lane, directory, udid)\n'
         '            elif lane == "t5-host-actions":\n'),
        ('"combined_t5_freshness_gateway.py", "focus_lifecycle_profile.py"}\n',
         '"combined_t5_freshness_gateway.py", "focus_lifecycle_profile.py",\n'
         '                      ' + ", ".join(repr(name) for name in NEW_CONTROL_FILES) + '}\n'),
        ('        consumer = None if args.admission_only else Consumer(args.root, admission, commands, built, app, helpers, binding)\n',
         '        consumer = None if args.admission_only else Consumer(args.root, admission, commands, built, app, helpers, binding)\n'
         '        if consumer is not None:\n'
         '            consumer.source_admission = source_proof\n'),
    )


def nodes(source):
    tree = ast.parse(source)
    top = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    methods = {node.name: node for node in top["Consumer"].body if isinstance(node, ast.FunctionDef)}
    return top, methods


def source_segment(source, node):
    return ast.get_source_segment(source, node)


def compose(original):
    require(sha(original) == ORIGINAL_HOST_SHA256, "Exact reviewed e877 original F host required")
    original_text = original.decode("utf-8")
    candidate = original_text
    for before, after in changes():
        require(candidate.count(before) == 1, "Unique additive host insertion required: " + before[:90])
        candidate = candidate.replace(before, after, 1)
    inverse = candidate
    for before, after in reversed(changes()):
        require(inverse.count(after) == 1, "Unique inverse insertion required")
        inverse = inverse.replace(after, before, 1)
    require(inverse == original_text, "Host inverse does not restore every original byte")
    compile(candidate, "combined_host_acceptance_app15.py", "exec")
    old_top, old_methods = nodes(original_text)
    new_top, new_methods = nodes(candidate)
    for name in UNCHANGED_FUNCTIONS:
        require(source_segment(original_text, old_top[name]) == source_segment(candidate, new_top[name]),
                "Original function changed: " + name)
    for name in UNCHANGED_METHODS:
        require(source_segment(original_text, old_methods[name]) == source_segment(candidate, new_methods[name]),
                "Original lifecycle/stage method changed: " + name)
    old_final = [node for node in old_methods["execute_lane"].body if isinstance(node, ast.Try)][0].finalbody
    new_final = [node for node in new_methods["execute_lane"].body if isinstance(node, ast.Try)][0].finalbody
    require([source_segment(original_text, node) for node in old_final] == [source_segment(candidate, node) for node in new_final],
            "Original owned-simulator retention/shutdown changed")
    def postflight(method):
        return [node for node in method.body if isinstance(node, ast.If)
                and ast.unparse(node.test) == "lane == 'properties-set'"][-1]
    require(source_segment(original_text, postflight(old_methods["wave"])) == source_segment(candidate, postflight(new_methods["wave"])),
            "Original mandatory Properties Set postflight changed")
    proof = dict(schema="pinkha-additive-torah-host-control-v1", status="PASS_SOURCE_MATERIALIZATION_NOT_EXECUTION",
                 originalHostSHA256=sha(original), materializedHostSHA256=sha(candidate.encode()),
                 inverseRestoresEveryOriginalByte=True, unchangedFunctions=list(UNCHANGED_FUNCTIONS),
                 unchangedMethods=list(UNCHANGED_METHODS), unchangedOwnedSimulatorFinally=True,
                 unchangedMandatoryPropertiesSetPostflight=True, addedPlans=NEW_PLANS,
                 addedControllerFiles=NEW_CONTROL_FILES, originalStageAndEnumerationUnchanged=True,
                 commonProductAdmissionChanged=False, runtimePinsChanged=False,
                 appBuilds=0, XCTestInvocations=0, nativeCalls=0, previousFailureEvidenceChanged=False)
    return candidate.encode("utf-8"), proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-host", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Materialized evidence directory must be new")
    require(args.original_host.is_file() and not args.original_host.is_symlink(), "Regular pinned original host required")
    candidate, proof = compose(args.original_host.read_bytes())
    args.output.mkdir(parents=True, mode=0o700)
    (args.output / "combined_host_acceptance_app15.py").write_bytes(candidate)
    (args.output / "materialization.json").write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n")
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
