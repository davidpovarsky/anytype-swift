"""Exact existing Wave-15 UIKit/Properties component scope, not UI acceptance."""
import hashlib
import json
from pathlib import Path
import re

SUITE_NAMES = (
    "PinkhaTextDirectionPersistenceTests",
    "PinkhaTextDirectionUIKitAdapterTests",
    "PinkhaTextBlockLeadingMarkerAdapterTests",
    "PinkhaNavigationGestureBridgeTests",
    "TorahNativeUIParityTests",
    "TextBlockFocusLifecycleTests",
)
MANIFEST_PATH = Path(__file__).with_name("wave15-core-tests.json")


class CoreEvidenceReviewPending(ValueError):
    """Retain actual xcresult when its case representation needs review."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_declarations(text):
    declarations = re.findall(
        r"@Test(?:\((.*?)\))?\s+func\s+(\w+)\s*\(([^)]*)\)", text, flags=re.S)
    require(len(declarations) == text.count("@Test"), "Unrecognized core test declaration")
    result = {}
    for attributes, name, parameters in declarations:
        require(name not in result, "Duplicate core test method")
        params = []
        if parameters.strip():
            for parameter in parameters.split(","):
                matched = re.fullmatch(r"\s*(\w+)\s*:\s*(Bool|Int|String)\s*", parameter)
                require(matched is not None, "Unreviewed core parameter declaration")
                params.append(dict(name=matched.group(1), type=matched.group(2)))
        collections = []
        if "arguments:" in attributes:
            remaining = attributes.split("arguments:", 1)[1].strip()
            decoder = json.JSONDecoder()
            while remaining:
                values, offset = decoder.raw_decode(remaining)
                require(isinstance(values, list) and values
                        and all(type(value) in {bool, int, str} for value in values),
                        "Only reviewed nonempty literal core argument arrays are supported")
                require(len({json.dumps(value, ensure_ascii=True) for value in values}) == len(values),
                        "Repeated literal core argument")
                collections.append(values)
                remaining = remaining[offset:].strip()
                if remaining:
                    require(remaining.startswith(","), "Unexpected core argument syntax")
                    remaining = remaining[1:].strip()
            require(1 <= len(collections) <= 2 and len(params) == len(collections),
                    "Core parameter collections differ from method signature")
            for parameter, values in zip(params, collections):
                expected_type = {"Bool": bool, "Int": int, "String": str}[parameter["type"]]
                require(all(type(value) is expected_type for value in values),
                        "Core literal argument types differ")
        else:
            require(not params, "Core parameterized method lacks reviewed literal arguments")
        count = 1
        for values in collections:
            count *= len(values)
        result[name] = dict(parameters=params, argument_collections=collections, case_count=count)
    return result


def source_digest(text):
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def load_manifest():
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    require(value.get("schema") == 1 and set(value.get("suites", {})) == set(SUITE_NAMES),
            "Core suite manifest differs from the reviewed scope")
    suites = value["suites"]
    require(sum(len(item["methods"]) for item in suites.values()) == 53
            and sum(method["case_count"] for item in suites.values()
                    for method in item["methods"].values()) == 78,
            "Core scope must contain53 functions and78 literal cases")
    return suites


def suite_counts():
    return {suite: len(value["methods"]) for suite, value in load_manifest().items()}


def validate_source(text, specification):
    require(source_digest(text) == specification["source_lf_sha256"],
            "Reviewed core test source changed; review its manifest before execution")
    actual = inspect_declarations(text)
    require(actual == specification["methods"], "Core declaration/argument inventory changed")
    return set(actual)


def validate_arguments(tree, expected):
    specifications = load_manifest()
    methods = {suite + "/" + name: spec for suite, data in specifications.items()
               for name, spec in data["methods"].items()}
    require(expected == set(methods), "Actual core selection differs from its reviewed inventory")
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
    if len(nodes) != len(methods):
        raise CoreEvidenceReviewPending("Unknown core method/argument tree; retain raw Apple results")
    actual, observed = {}, set()
    for node in nodes:
        identifier = node.get("nodeIdentifier")
        matches = [name for name, spec in methods.items()
                   if identifier in {name + "(" + "".join(p["name"] + ":" for p in spec["parameters"]) + ")",
                       "AnytypeTests/" + name + "(" + "".join(p["name"] + ":" for p in spec["parameters"]) + ")"}]
        require(len(matches) == 1 and matches[0] not in observed, "Unknown or repeated core method identity")
        method = matches[0]
        observed.add(method)
        require(node.get("result") == "Passed", "Core method did not pass")
        descendants = []
        def descend(child):
            require(isinstance(child, dict), "Malformed core execution descendant")
            descendants.append(child)
            children = child.get("children", [])
            require(isinstance(children, list), "Malformed core execution children")
            for value in children:
                descend(value)
        for child in node.get("children", []):
            descend(child)
        for child in descendants:
            if child.get("nodeType") not in {"Arguments", "Repetition", "Test Case Run"}:
                raise CoreEvidenceReviewPending("Unknown core case schema; retain raw Apple results")
            require(child.get("result") == "Passed", "Failed/skipped/unreported core argument execution")
        arguments = [child for child in descendants if child.get("nodeType") == "Arguments"]
        count = methods[method]["case_count"]
        if count == 1:
            require(not arguments, "Unexpected core argument cases")
            actual[method] = [dict(node_identifier=identifier, result="Passed")]
        else:
            if any(not isinstance(child.get("name"), str) or not child["name"] for child in arguments):
                raise CoreEvidenceReviewPending("Unknown argument display identities; retain raw Apple results")
            require(len(arguments) == count and len({child["name"] for child in arguments}) == count,
                    "Missing or duplicate actual core argument cases")
            actual[method] = [dict(node_identifier=identifier, argument_display=child["name"], result="Passed")
                              for child in arguments]
    require(observed == expected and sum(len(items) for items in actual.values()) == 78,
            "Incomplete source-bound core execution")
    return dict(actual_method_count=len(observed), declared_case_count=78, core_cases=actual,
                argument_evidence="DISTINCT_ACTUAL_CASES_BOUND_TO_EXACT_LITERAL_SOURCE_COLLECTIONS")
