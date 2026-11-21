"""Run the reviewed editor and table cases in the existing SDK06 Debug build.

Keep the original two source/argument contracts. Enumerate the compiled suites,
then verify the exact selected signatures before running any component test.
This wrapper never creates or restores an application build.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HANLIN_TOOLS = Path(__file__).resolve().parents[1] / "Hanlin"
if str(HANLIN_TOOLS) not in sys.path:
    sys.path.insert(0, str(HANLIN_TOOLS))
import run_host_tests as host
import shared_editor_profile as editor
import shared_table_profile as table

LANE = "hanlin-native-shared-editor"
PROFILE = "shared-editor-and-table"
PASS_STATUS = "SHARED_EDITOR_TABLE_COMPONENT_PASS"
RESULT_PREFIX = "shared-editor-table"
SUITE = "TextBlockFocusLifecycleTests"
SUITES = (SUITE, table.SUITE)
EXPECTED_METHOD_COUNT = 21
DECLARED_CASE_COUNT = 29


def source_contract(app):
    expected, hashes = host.expected_methods(app, host.HostTestProfile.SHARED_EDITOR)
    host.require(len(expected) == 10, "The existing ten-method shared-editor selection changed")
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    candidates = [name for name in tracked if name.casefold() == table.SOURCE_PATH.casefold()]
    host.require(len(candidates) == 1, "Missing or case-colliding tracked table test source")
    actual, synced = app / candidates[0], app / table.SOURCE_PATH
    host.require(synced.is_file() and actual.samefile(synced),
                 "Table test source is absent from the Xcode synchronized root")
    data = actual.read_bytes()
    table_methods = {table.SUITE + "/" + name for name in table.validate_source(data.decode("utf-8"))}
    host.require(not expected.intersection(table_methods), "Editor and table method scopes overlap")
    expected.update(table_methods)
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
    host.require(len(expected) == EXPECTED_METHOD_COUNT and len(declarations) == 28 and len(excluded) == 7,
                 "Reviewed editor/table declaration or pending selection inventory changed")
    return {"methods": sorted(expected), "source_hashes": hashes,
            "expected_methods": EXPECTED_METHOD_COUNT, "declared_invocations": DECLARED_CASE_COUNT,
            "profile": PROFILE, "compiled_declarations": declarations,
            "unselected_existing_methods": sorted(excluded),
            "components": {"shared-editor": {"expected_methods": 10, "declared_invocations": 15},
                           "shared-table": {"expected_methods": 11, "declared_invocations": 14}}}


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


def enumerate_selection(app, base, evidence, shared, source):
    declaration_ids = set(source["compiled_declarations"].values())
    selected_source_ids = {source["compiled_declarations"][method] for method in source["methods"]}
    host.require(len(selected_source_ids) == EXPECTED_METHOD_COUNT,
                 "Pending component source selection does not identify21 methods")
    discovery_path = evidence / "compiled-suite-enumeration.json"
    selected_path = evidence / "compiled-selected-enumeration.json"

    def enumerate_to(path, selectors):
        command = [*base, *["-only-testing:" + identifier for identifier in selectors],
                   "-enumerate-tests", "-test-enumeration-style", "flat",
                   "-test-enumeration-format", "json", "-test-enumeration-output-path", str(path)]
        host.command(command, app, evidence)
        host.require(path.is_file(), "Xcode did not write compiled test enumeration")
        return command, enumerated_identifiers(json.loads(path.read_text(encoding="utf-8")))

    discovery_command, (plan, discovered, disabled) = enumerate_to(
        discovery_path, ["AnytypeTests/" + suite for suite in SUITES])
    host.require(discovered == declaration_ids and not declaration_ids.intersection(disabled),
                 "Compiled suites differ from the exact28 source declarations")
    # Reuse actual returned strings. Source signatures are equality checks, not
    # guessed only-testing filters; in particular bare Swift method names are
    # never sent to Xcode.
    selected = sorted(identifier for identifier in discovered if identifier in selected_source_ids)
    selected_command, (selected_plan, observed, disabled) = enumerate_to(selected_path, selected)
    host.require(selected_plan == plan and observed == set(selected) and not observed.intersection(disabled),
                 "Compiled pending selection differs from the exact21 methods; no tests executed")
    host.require(len(selected) == EXPECTED_METHOD_COUNT,
                 "Compiled pending selection does not contain21 methods")
    return {"status": "EXACT_COMPILED_SELECTION_VERIFIED", "test_plan": plan,
            "selected_identifiers": selected, "selected_method_count": len(selected),
            "enumerated_source_method_count": len(discovered),
            "unselected_identifiers": sorted(discovered - observed),
            "discovery_command": discovery_command, "selected_command": selected_command,
            "discovery_sha256": shared.digest(discovery_path),
            "selected_sha256": shared.digest(selected_path), "tests_executed": 0}


def validate_results(summary, tree, expected, udid):
    # The default host validator checks the original combined summary, actual
    # destination and every method identity without applying a single profile's
    # count assumptions. Original case nodes then enter both unchanged contracts.
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
                                    ("shared-table", table.SUITE, table.validate_arguments)):
        methods = {name for name in expected if name.split("/", 1)[0] == suite}
        selected = [node for node in nodes if any(re.search(
            r"(?:^|/)" + re.escape(name) + r"(?:\(|/|$)", node["nodeIdentifier"]) for name in methods)]
        host.require(len(selected) == len(methods), "Component has missing or duplicate actual method nodes")
        components[label] = validator(selected, methods)
    host.require(len(nodes) == EXPECTED_METHOD_COUNT
                 and sum(part["actual_method_count"] for part in components.values()) == EXPECTED_METHOD_COUNT
                 and sum(part["declared_case_count"] for part in components.values()) == DECLARED_CASE_COUNT,
                 "Combined editor/table method or literal-case execution differs")
    host.require(actual["counts"]["totalTestCount"] in {EXPECTED_METHOD_COUNT, DECLARED_CASE_COUNT},
                 "Combined summary differs from exact21 methods or29 argument cases")
    actual.update(components=components, actual_method_count=EXPECTED_METHOD_COUNT,
                  declared_case_count=DECLARED_CASE_COUNT)
    return actual


def execute(app, configuration, udid, expected_app, evidence, shared):
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

    def verify_binding():
        host.require(source_contract(app) == source, "Shared-editor/table source changed during execution")
        host.require(shared.digest(app_executable) == hashes["app_executable"]
                     and shared.digest(test_executable) == hashes["test_executable"]
                     and shared.digest(configuration) == hashes["xctestrun"],
                     "Shared-editor built products changed during execution")

    bundle = evidence / "SharedEditorTable.xcresult"
    base = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
            "-destination", "platform=iOS Simulator,id=" + udid,
            "-parallel-testing-enabled", "NO"]
    receipt = {"status": "FAIL", "phase": "ENUMERATION_PRECHECK", "profile": PROFILE,
               "build_mode": "SAME_JOB_EXISTING_SDK06_BUILD", "additional_app_builds": 0,
               "source": source, "built_products": hashes}
    shared.write(evidence / "execution.json", receipt)
    try:
        enumeration = enumerate_selection(app, base, evidence, shared, source)
        receipt["enumeration"] = enumeration
        verify_binding()
        command = [*base, *["-only-testing:" + identifier for identifier in enumeration["selected_identifiers"]],
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
        receipt.update(status=PASS_STATUS, phase="COMPLETE", actual=actual,
                       raw_summary_sha256=shared.digest(summary_path), raw_tests_sha256=shared.digest(tree_path),
                       real_native_persistence_accepted=False)
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        shared.write(evidence / "execution.json", receipt)
    return receipt
