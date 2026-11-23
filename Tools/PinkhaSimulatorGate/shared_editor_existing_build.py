"""Run reviewed editor, table and authority cases in the existing SDK06 build.

Keep each independent source/argument contract. Enumerate the compiled suites,
then verify the exact selected signatures before running any component test.
This wrapper never creates or restores an application build.
"""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from uuid import uuid4

HANLIN_TOOLS = Path(__file__).resolve().parents[1] / "Hanlin"
if str(HANLIN_TOOLS) not in sys.path:
    sys.path.insert(0, str(HANLIN_TOOLS))
import run_host_tests as host
import shared_editor_profile as editor
import shared_table_profile as table
import related_read_authority_profile as authority

LANE = "hanlin-native-shared-editor"
PROFILE = "shared-editor-table-and-related-authority"
PASS_STATUS = "SHARED_EDITOR_TABLE_AUTHORITY_COMPONENT_PASS"
RESULT_PREFIX = "shared-editor-table-authority"
SUITE = "TextBlockFocusLifecycleTests"
SUITES = (SUITE, table.SUITE, authority.SUITE)
EXPECTED_METHOD_COUNT = 23
DECLARED_CASE_COUNT = 32
COMPILED_DECLARATION_COUNT = 30


def source_contract(app):
    expected, hashes = host.expected_methods(app, host.HostTestProfile.SHARED_EDITOR)
    host.require(len(expected) == 10, "The existing ten-method shared-editor selection changed")
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    for profile, label in ((table, "table"), (authority, "related-read authority")):
        candidates = [name for name in tracked if name.casefold() == profile.SOURCE_PATH.casefold()]
        host.require(len(candidates) == 1, "Missing or case-colliding tracked " + label + " test source")
        actual, synced = app / candidates[0], app / profile.SOURCE_PATH
        host.require(synced.is_file() and actual.samefile(synced),
                     label + " test source is absent from the Xcode synchronized root")
        data = actual.read_bytes()
        methods = {profile.SUITE + "/" + name for name in profile.validate_source(data.decode("utf-8"))}
        host.require(not expected.intersection(methods), "Component method scopes overlap")
        expected.update(methods)
        hashes[candidates[0]] = hashlib.sha256(data).hexdigest()
    declarations = {}
    for path in hashes:
        suite = Path(path).stem
        for name, specification in host.core_profile.inspect_declarations(
                (app / path).read_text(encoding="utf-8")).items():
            method = suite + "/" + name
            signature = "(" + "".join(p["name"] + ":" for p in specification["parameters"]) + ")"
            declarations[method] = "AnytypeTests/" + method + signature
    excluded = set(declarations) - expected
    host.require(len(expected) == EXPECTED_METHOD_COUNT and len(declarations) == COMPILED_DECLARATION_COUNT and len(excluded) == 7,
                 "Reviewed editor/table/authority declaration or pending selection inventory changed")
    return {"methods": sorted(expected), "source_hashes": hashes,
            "expected_methods": EXPECTED_METHOD_COUNT, "declared_invocations": DECLARED_CASE_COUNT,
            "profile": PROFILE, "compiled_declarations": declarations,
            "unselected_existing_methods": sorted(excluded),
            "components": {"shared-editor": {"expected_methods": 10, "declared_invocations": 15},
                           "shared-table": {"expected_methods": 11, "declared_invocations": 14},
                           "related-read-authority": {"expected_methods": 2, "declared_invocations": 3}}}


def enumerated_identifiers(payload):
    """Read Xcode's flat JSON; preserve the returned full identifiers verbatim.

    Empty/error/ambiguous/unreviewed output never permits test execution. The
    original JSON is retained for review if a future Xcode changes this schema.
    """
    host.require(isinstance(payload, dict) and payload.get("errors") == [],
                 "Compiled test enumeration reported errors or an unknown schema")
    values = payload.get("values")
    host.require(isinstance(values, list) and len(values) == 1,
                 "Expected one compiled test enumeration configuration")
    value = values[0]
    host.require(isinstance(value, dict) and isinstance(value.get("testPlan"), str),
                 "Compiled test enumeration has no explicit test plan")
    inventories = {}
    for field in ("enabledTests", "disabledTests"):
        entries = value.get(field)
        host.require(isinstance(entries, list), "Unknown compiled " + field + " schema")
        identifiers = []
        for entry in entries:
            identifier = entry.get("identifier") if isinstance(entry, dict) else None
            host.require(isinstance(identifier, str) and identifier and not any(c.isspace() for c in identifier),
                         "Compiled enumeration has a malformed test identifier")
            identifiers.append(identifier)
        host.require(len(identifiers) == len(set(identifiers)), "Compiled enumeration repeats an identifier")
        inventories[field] = set(identifiers)
    host.require(inventories["enabledTests"], "Compiled enumeration selected zero tests")
    host.require(not inventories["enabledTests"].intersection(inventories["disabledTests"]),
                 "Compiled test is both enabled and disabled")
    return value["testPlan"], inventories["enabledTests"], inventories["disabledTests"]


def scoped_configuration(original, destination, identifiers, shared):
    """Restrict an owned v2 copy, retaining the exact target/product settings.

    OnlyTestIdentifiers is target-relative. Keeping the copy beside the original
    preserves __TESTROOT__; the original xctestrun is never written. Filtering
    the plist avoids relying only on CLI filters during Xcode enumeration.
    """
    host.require(destination.parent.resolve() == original.parent.resolve()
                 and destination != original and not destination.exists() and not destination.is_symlink(),
                 "Fresh sibling component xctestrun required")
    value = plistlib.loads(original.read_bytes())
    host.require(isinstance(value, dict)
                 and value.get("__xctestrun_metadata__", {}).get("FormatVersion") == 2,
                 "Only the reviewed Xcode v2 test configuration is supported")
    configurations = value.get("TestConfigurations")
    host.require(isinstance(configurations, list) and len(configurations) == 1
                 and isinstance(configurations[0], dict)
                 and configurations[0].get("IsEnabled", True) is True,
                 "Expected one enabled original test configuration")
    targets = configurations[0].get("TestTargets")
    host.require(isinstance(targets, list) and all(isinstance(target, dict) for target in targets),
                 "Unknown Xcode test-target structure")
    selected = [target for target in targets if target.get("BlueprintName") == "AnytypeTests"]
    host.require(len(selected) == 1 and selected[0].get("IsEnabled", True) is True
                 and isinstance(selected[0].get("TestHostPath"), str)
                 and isinstance(selected[0].get("TestBundlePath"), str),
                 "Expected one enabled actual AnytypeTests target")
    target = selected[0]
    host.require(identifiers and len(set(identifiers)) == len(identifiers)
                 and all(identifier.startswith("AnytypeTests/") for identifier in identifiers),
                 "Scoped configuration identifiers must belong to AnytypeTests")
    target["OnlyTestIdentifiers"] = [identifier.removeprefix("AnytypeTests/") for identifier in identifiers]
    # Preserve existing SkipTestIdentifiers and all non-selection fields. A
    # disabled requested method must fail enumeration, never be re-enabled.
    configurations[0]["TestTargets"] = selected
    with destination.open("xb") as output:
        plistlib.dump(value, output, sort_keys=False)
    return {"path": str(destination), "sha256": shared.digest(destination),
            "original_sha256": shared.digest(original), "format_version": 2,
            "target": "AnytypeTests", "only_test_identifiers": target["OnlyTestIdentifiers"],
            "other_targets_removed_from_copy": [item.get("BlueprintName") for item in targets if item is not target]}


def xcode_method_selectors(identifiers, declarations):
    """Map reviewed compiled identities to unambiguous Xcode method filters.

    Xcode27 enumeration returned full parameter signatures, but those strings
    selected none of the eight parameterized methods in run45047827580. Use
    target/suite/method for those filters only. Full signatures remain the
    required enumeration and result identities; no argument case is removed.
    """
    by_method = {}
    for identifier in declarations:
        match = re.fullmatch(r"(AnytypeTests/([A-Za-z_][A-Za-z0-9_]*)/[A-Za-z_][A-Za-z0-9_]*)"
                             r"\((?:[A-Za-z_][A-Za-z0-9_]*:)*\)", identifier)
        host.require(match is not None and match.group(2) in SUITES,
                     "Unreviewed compiled component signature")
        method = match.group(1)
        host.require(method not in by_method, "Ambiguous compiled method selector")
        by_method[method] = identifier
    host.require(identifiers and len(set(identifiers)) == len(identifiers)
                 and set(identifiers).issubset(set(by_method.values())),
                 "Method selectors require unique reviewed compiled identities")
    return [identifier if identifier.endswith("()") else identifier.split("(", 1)[0]
            for identifier in identifiers]


def enumerate_selection(app, base, evidence, shared, source):
    declaration_ids = set(source["compiled_declarations"].values())
    selected_source_ids = {source["compiled_declarations"][method] for method in source["methods"]}
    host.require(len(selected_source_ids) == EXPECTED_METHOD_COUNT,
                 "Pending component source selection does not identify23 methods")
    discovery_path = evidence / "compiled-suite-enumeration.json"
    selected_path = evidence / "compiled-selected-enumeration.json"
    original = Path(base[base.index("-xctestrun") + 1])
    selection_nonce = uuid4().hex
    prefix = "UI27-" + evidence.name + "-" + selection_nonce
    discovery_configuration = original.with_name(prefix + "-discovery.xctestrun")
    selected_configuration = original.with_name(prefix + "-selected.xctestrun")

    def enumerate_to(path, configuration, selectors):
        binding = scoped_configuration(original, configuration, selectors, shared)
        shared.write(evidence / (path.stem + "-configuration.json"), binding)
        scoped = list(base)
        scoped[scoped.index("-xctestrun") + 1] = str(configuration)
        command = [*scoped, *["-only-testing:" + identifier for identifier in selectors],
                   "-enumerate-tests", "-test-enumeration-style", "flat",
                   "-test-enumeration-format", "json", "-test-enumeration-output-path", str(path)]
        host.command(command, app, evidence)
        host.require(path.is_file(), "Xcode did not write compiled test enumeration")
        host.require(shared.digest(configuration) == binding["sha256"]
                     and shared.digest(original) == binding["original_sha256"],
                     "Component xctestrun changed during enumeration")
        return command, binding, enumerated_identifiers(json.loads(path.read_text(encoding="utf-8")))

    discovery_command, discovery_binding, (plan, discovered, disabled) = enumerate_to(
        discovery_path, discovery_configuration, ["AnytypeTests/" + suite for suite in SUITES])
    host.require(discovered == declaration_ids and not declaration_ids.intersection(disabled),
                 "Compiled suites differ from the exact30 source declarations")
    # Preserve actual full signatures for equality/result checks. Outbound
    # parameterized filters use Xcode's method selector grammar, independently
    # qualified by another original enumeration before any test can execute.
    selected = sorted(identifier for identifier in discovered if identifier in selected_source_ids)
    selectors = xcode_method_selectors(selected, discovered)
    selected_command, selected_binding, (selected_plan, observed, disabled) = enumerate_to(
        selected_path, selected_configuration, selectors)
    host.require(selected_plan == plan and observed == set(selected) and not observed.intersection(disabled),
                 "Compiled pending selection differs from the exact23 methods; no tests executed")
    host.require(len(selected) == EXPECTED_METHOD_COUNT,
                 "Compiled pending selection does not contain23 methods")
    return {"status": "EXACT_COMPILED_SELECTION_VERIFIED", "test_plan": plan, "selection_nonce": selection_nonce,
            "selected_identifiers": selected, "selected_method_count": len(selected),
            "xcode_method_selectors": selectors,
            "selector_identity_binding": dict(zip(selectors, selected)),
            "enumerated_source_method_count": len(discovered),
            "unselected_identifiers": sorted(discovered - observed),
            "discovery_command": discovery_command, "selected_command": selected_command,
            "discovery_configuration": discovery_binding, "selected_configuration": selected_binding,
            "discovery_sha256": shared.digest(discovery_path),
            "selected_sha256": shared.digest(selected_path), "tests_executed": 0}


def validate_results(summary, tree, expected, udid):
    # The default host validator checks the original combined summary, actual
    # destination and every method identity without applying a single profile's
    # count assumptions. Original case nodes then enter each component's own unchanged case validator.
    actual = host.validate_results(summary, tree, expected, udid)
    nodes = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(tree)
    components = {}
    for label, suite, validator in (("shared-editor", SUITE, editor.validate_arguments),
                                    ("shared-table", table.SUITE, table.validate_arguments),
                                    ("related-read-authority", authority.SUITE, authority.validate_arguments)):
        methods = {name for name in expected if name.split("/", 1)[0] == suite}
        selected = [node for node in nodes if any(re.search(
            r"(?:^|/)" + re.escape(name) + r"(?:\(|/|$)", node["nodeIdentifier"]) for name in methods)]
        host.require(len(selected) == len(methods), "Component has missing or duplicate actual method nodes")
        components[label] = validator(selected, methods)
    host.require(len(nodes) == EXPECTED_METHOD_COUNT
                 and sum(part["actual_method_count"] for part in components.values()) == EXPECTED_METHOD_COUNT
                 and sum(part["declared_case_count"] for part in components.values()) == DECLARED_CASE_COUNT,
                 "Combined editor/table/authority method or literal-case execution differs")
    host.require(actual["counts"]["totalTestCount"] in {EXPECTED_METHOD_COUNT, DECLARED_CASE_COUNT},
                 "Combined summary differs from exact23 methods or32 argument cases")
    actual.update(components=components, actual_method_count=EXPECTED_METHOD_COUNT,
                  declared_case_count=DECLARED_CASE_COUNT)
    return actual


def execute(app, configuration, udid, expected_app, evidence, shared, *, selector_plan=None):
    host.require(not evidence.exists() or not any(evidence.iterdir()),
                 "Refuse stale shared-editor component evidence")
    evidence.mkdir(parents=True, exist_ok=True)
    source = source_contract(app)
    built, app_executable, test_bundle, test_executable = host.xctest_products(configuration)
    host.require(built.resolve() == expected_app.resolve(),
                 "Shared-editor components must use the SDK06 app build")
    hashes = {"app_executable": shared.digest(app_executable),
              "test_executable": shared.digest(test_executable),
              "xctestrun": shared.digest(configuration)}
    selected_configuration = None

    def verify_binding():
        host.require(source_contract(app) == source, "Shared-editor/table/authority source changed during execution")
        host.require(shared.digest(app_executable) == hashes["app_executable"]
                     and shared.digest(test_executable) == hashes["test_executable"]
                     and shared.digest(configuration) == hashes["xctestrun"],
                     "Shared-editor built products changed during execution")
        if selected_configuration is not None:
            host.require(shared.digest(Path(selected_configuration["path"])) == selected_configuration["sha256"],
                         "Selected component xctestrun changed during execution")

    bundle = evidence / "SharedEditorTableAuthority.xcresult"
    base = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
            "-destination", "platform=iOS Simulator,id=" + udid,
            "-parallel-testing-enabled", "NO"]
    receipt = {"status": "FAIL", "phase": "ENUMERATION_PRECHECK", "profile": PROFILE,
               "build_mode": "SAME_JOB_EXISTING_SDK06_BUILD", "additional_app_builds": 0,
               "source": source, "built_products": hashes}
    shared.write(evidence / "execution.json", receipt)
    try:
        if selector_plan is None:
            enumeration = enumerate_selection(app, base, evidence, shared, source)
        else:
            from sdk06_qualified_selector import QualifiedSelectorPlan
            host.require(isinstance(selector_plan, QualifiedSelectorPlan), "A sealed actual selector plan is required")
            enumeration = selector_plan.enumerate_current(app, base, evidence, shared, source)
        receipt["enumeration"] = enumeration
        selected_configuration = enumeration["selected_configuration"]
        verify_binding()
        selected_base = list(base)
        selected_base[selected_base.index("-xctestrun") + 1] = selected_configuration["path"]
        if selector_plan is None:
            command = [*selected_base, *["-only-testing:" + identifier for identifier in enumeration["xcode_method_selectors"]],
                       "-resultBundlePath", str(bundle)]
        else:
            command = [*selected_base, *selector_plan.execution_arguments(enumeration),
                       "-resultBundlePath", str(bundle)]
        receipt.update(phase="EXECUTION", command=command)
        shared.write(evidence / "execution.json", receipt)
        shared.run_xctest(command, app, evidence, bundle, RESULT_PREFIX,
                          command_runner=host.command)
        summary_path = evidence / (RESULT_PREFIX + "-summary.json")
        tree_path = evidence / (RESULT_PREFIX + "-tests.json")
        actual = validate_results(json.loads(summary_path.read_text()), json.loads(tree_path.read_text()),
                                  set(source["methods"]), udid)
        verify_binding()
        raw_summary_hash = shared.digest(summary_path)
        raw_tests_hash = shared.digest(tree_path)
        component_receipts = {}
        for label, component in actual["components"].items():
            methods = sorted(component["core_cases"])
            path = evidence / ("component-" + label + ".json")
            component_receipt = {
                "status": "SOURCE_BOUND_COMPONENT_PASS", "component": label,
                "build_mode": "SAME_JOB_EXISTING_SDK06_BUILD", "additional_app_builds": 0,
                "methods": methods, "actual": component,
                "source_hashes": source["source_hashes"], "built_products": hashes,
                "raw_summary_sha256": raw_summary_hash, "raw_tests_sha256": raw_tests_hash,
                "real_native_persistence_accepted": False,
            }
            shared.write(path, component_receipt)
            component_receipts[label] = {"path": str(path), "sha256": shared.digest(path)}
        receipt.update(status=PASS_STATUS, phase="COMPLETE", actual=actual,
                       component_receipts=component_receipts,
                       raw_summary_sha256=raw_summary_hash, raw_tests_sha256=raw_tests_hash,
                       real_native_persistence_accepted=False)
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        shared.write(evidence / "execution.json", receipt)
    return receipt
