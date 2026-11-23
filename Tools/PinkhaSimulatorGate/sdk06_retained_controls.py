"""Fixed, source-bound reuse of already executed SDK controller controls.

This verifier runs no controller or product test. The original failed CI lanes
remain failed; only their individually named controller outcomes are retained.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat

ADMISSION_PATH = "Tools/PinkhaSimulatorGate/sdk06-retained-controls.json"
ADMISSION_SHA256 = "cc05f8cb2f95a41d65d5a4cdd01ac140bb4e6572d25e6476912bcc7fa3820e58"
SCHEMA = "pinkha-sdk06-retained-controller-controls-v1"


class RetainedControlError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise RetainedControlError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode_json(data):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate JSON identity: " + key)
            value[key] = item
        return value
    return json.loads(data, object_pairs_hook=pairs)


def read_bound(root, relative, expected=None):
    relative_path = PurePosixPath(relative)
    require(isinstance(relative, str) and relative_path.as_posix() == relative
            and not relative_path.is_absolute()
            and relative_path.parts and all(part not in ("", ".", "..")
                                            for part in relative_path.parts),
            "Unsafe retained-control path")
    path = root
    for component in relative_path.parts:
        path = path / component
        require(not path.is_symlink(), "Symlink in retained-control input: " + relative)
    require(path.is_file() and stat.S_ISREG(path.stat().st_mode),
            "Missing regular retained-control input: " + relative)
    data = path.read_bytes()
    if expected is not None:
        require(digest(data) == expected, "Unadmitted retained-control bytes: " + relative)
    return data


def declaration_bytes(source, node):
    return ("\n".join(source.splitlines()[node.lineno - 1:node.end_lineno]) + "\n").encode()


def test_declarations(data):
    source = data.decode("utf-8")
    tree = ast.parse(source)
    result = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_"):
                    name = node.name + "." + method.name
                    require(name not in result, "Duplicate current test declaration: " + name)
                    result[name] = digest(declaration_bytes(source, method))
    return result


def unittest_batches(data):
    """Read original named outcomes and their actual terminal, never summary only."""
    pending, batches, summary = [], [], None
    outcome = re.compile(r"^(test_\w+) \(([\w.]+)\) \.\.\. (.+)$")
    for number, raw in enumerate(data.decode("utf-8").splitlines(), 1):
        line = re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ", "", raw).strip()
        match = outcome.fullmatch(line)
        if match:
            require(summary is None, "Named outcome preceded the prior batch terminal")
            parts = match.group(2).rsplit(".", 2)
            require(len(parts) == 3 and parts[-1] == match.group(1),
                    "Unbound original unittest name")
            pending.append({"name": parts[-2] + "." + parts[-1],
                            "outcome": match.group(3), "line": number})
            continue
        match = re.fullmatch(r"Ran (\d+) tests? in ([0-9.]+)s", line)
        if match:
            require(summary is None and len(pending) == int(match.group(1)),
                    "Original named outcome count differs from terminal summary")
            require(len({item["name"] for item in pending}) == len(pending),
                    "Duplicate original named outcome")
            summary = {"count": int(match.group(1)), "seconds": match.group(2),
                       "summary_line": number}
            continue
        if summary is not None and (line == "OK" or line.startswith(("OK (", "FAILED", "ERROR"))):
            require(line == "OK" and all(item["outcome"] == "ok" for item in pending),
                    "Original controller batch did not pass every named method")
            batches.append({**summary, "terminal_line": number, "methods": pending})
            pending, summary = [], None
    require(not pending and summary is None, "Truncated original unittest batch")
    require(bool(batches), "No original named controller outcomes")
    return batches


def wave_scope(data):
    source = data.decode("utf-8")
    tree = ast.parse(source)
    constants = {"BRANCH", "CONSUMER_BRANCH", "UI_RESUME_BRANCH", "SHARED_BRANCH",
                 "CONTINUATION_BRANCH", "APPROVED_BRANCHES"}
    functions = {"require", "require_source_identity"}
    selected = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in constants:
                selected[node.targets[0].id] = declaration_bytes(source, node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            selected[node.name] = declaration_bytes(source, node)
        elif isinstance(node, ast.ClassDef) and node.name == "SelectionFailure":
            selected[node.name] = declaration_bytes(source, node)
    require(len(selected) == 9, "Changed retained Wave-15 identity closure")
    execute = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute"]
    require(len(execute) == 1, "Ambiguous Wave-15 execution function")
    nodes = execute[0].body
    starts = [i for i, node in enumerate(nodes) if isinstance(node, ast.Assign)
              and ast.unparse(node) == "receipt['phase'] = 'UI'"]
    require(len(starts) == 1, "Changed original UI region entry")
    start = starts[0]
    ends = [i for i in range(start, len(nodes)) if isinstance(nodes[i], ast.Try)
            and any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "export_ui_console" for node in ast.walk(nodes[i]))]
    require(bool(ends), "Changed original UI region finalization")
    selected["execute.UI_region"] = (
        "\n".join(source.splitlines()[nodes[start].lineno - 1:nodes[ends[0]].end_lineno]) + "\n").encode()
    return {name: digest(value) for name, value in sorted(selected.items())}


def namespace_tree(data):
    tree = ast.parse(data.decode("utf-8"))
    class Declarations(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            node = copy.deepcopy(node)
            node.body = [ast.Pass()]
            return node
        visit_AsyncFunctionDef = visit_FunctionDef
    return ast.dump(Declarations().visit(tree), include_attributes=False)


def observer_remainder(data, removed):
    tree = ast.parse(data.decode("utf-8"))
    found = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            body = []
            for method in node.body:
                name = node.name + "." + method.name if isinstance(method, ast.FunctionDef) else None
                if name in removed:
                    found.add(name)
                else:
                    body.append(method)
            node.body = body
    require(found == set(removed), "Observer replacement scope differs")
    return ast.dump(tree, include_attributes=False)


def verify_retained_controls(app: Path):
    root = Path(app).resolve(strict=True)
    require(root.is_dir(), "Retained controls need the actual source root")
    admission_raw = read_bound(root, ADMISSION_PATH, ADMISSION_SHA256)
    admission = decode_json(admission_raw)
    require(admission.get("schema") == SCHEMA and admission.get("current_control_methods") == 98,
            "Unknown retained-control admission")
    require(admission.get("new_controller_runs") == 0 and admission.get("product_tests") == 0,
            "Retained controls cannot claim new execution")
    files = {item["path"]: read_bound(root, item["path"], item["sha256"])
             for item in admission["proof_files"]}
    require(len(files) == len(admission["proof_files"]), "Duplicate proof path")
    sources = {}
    for item in admission["source_inputs"]:
        path = item["path"]
        require(path not in sources, "Duplicate admitted current source")
        current = read_bound(root, path, item["current_sha256"])
        original = files[item["original_snapshot"]]
        require(digest(original) == item["original_sha256"], "Original source snapshot identity differs")
        mode = item["retention"]
        if mode == "byte_identical":
            require(current == original, "Tested source/dependency bytes changed: " + path)
        elif mode == "wave_scoped":
            require(wave_scope(current) == wave_scope(original) == item["scopes"],
                    "Tested Wave-15 region changed")
            require(namespace_tree(current) == namespace_tree(original),
                    "Wave-15 import/declaration surface changed")
            for alternate in item.get("alternate_original_snapshots", []):
                older = files[alternate["path"]]
                require(digest(older) == alternate["sha256"]
                        and wave_scope(older) == item["scopes"]
                        and namespace_tree(older) == namespace_tree(current),
                        "Alternate original Wave-15 tested scope differs")
        elif mode == "import_surface_only":
            require(namespace_tree(current) == namespace_tree(original),
                    "Imported declaration surface changed")
        else:
            require(mode in {"qualified_observer_production", "qualified_observer_tests"},
                    "Unreviewed retained-source mode")
        sources[path] = current

    parsed_logs = {}
    actual_batches = {}
    for item in admission["batches"]:
        parsed = parsed_logs.setdefault(item["log"], unittest_batches(files[item["log"]]))
        require(len(parsed) == item["log_batch_count"], "Original log batch count changed")
        actual = parsed[item["batch_index"]]
        names = sorted(value["name"] for value in actual["methods"])
        require(actual["count"] == item["count"] and names == item["methods"],
                "Original named controller scope changed")
        require(actual["seconds"] == item["seconds"], "Original batch duration metadata differs")
        require(item["id"] not in actual_batches, "Duplicate original batch identity")
        actual_batches[item["id"]] = actual

    observer = admission["observer_extension"]
    review = decode_json(files[observer["review"]])
    require(review["source_base"] == admission["origins"]["hanlin"]["source_sha"]
            and review["actual_control_passes"] == 7 and review["old_controls_rerun"] == 0,
            "Observer qualification provenance changed")
    for path, expected in review["source_sha256"].items():
        require(path in sources and digest(sources[path]) == expected,
                "Observer current source differs from its actual new controls")
    tests_path = observer["test_path"]
    original_item = next(item for item in admission["source_inputs"] if item["path"] == tests_path)
    require(observer_remainder(sources[tests_path], observer["current_only_declarations"])
            == observer_remainder(files[original_item["original_snapshot"]], observer["retired_declarations"]),
            "Previously retained observer declarations/helpers changed")

    catalog = []
    for module in admission["modules"]:
        current = test_declarations(sources[module["path"]])
        require(current == module["current_declarations"], "Current controller method inventory changed")
        for name, binding in module["methods"].items():
            require(name in current and current[name] == binding["declaration_sha256"],
                    "Current method lacks exact source binding")
            proof = actual_batches[binding["batch"]]
            require(name in {value["name"] for value in proof["methods"]},
                    "Current method lacks its original named PASS")
            snapshot = files[binding["tested_source_snapshot"]]
            require(test_declarations(snapshot).get(name) == current[name],
                    "Current method declaration differs from the actually tested source")
            catalog.append({"module": module["path"], "method": name,
                            "proof_batch": binding["batch"],
                            "declaration_sha256": current[name]})
        require(set(module["methods"]) == set(current), "Unbound current controller method")
    require(len(catalog) == 98 and len({(x["module"], x["method"]) for x in catalog}) == 98,
            "Current retained controller count differs")

    original = decode_json(files[admission["origins"]["hanlin"]["execution"]])
    require(original["status"] == "FAIL" and original["source_sha"] == admission["origins"]["hanlin"]["source_sha"]
            and original["run_id"] == "45096079315" and original["run_attempt"] == "1",
            "Original Hanlin lane identity/conclusion changed")
    identity = decode_json(files[admission["origins"]["sdk"]["identity"]])
    require(identity["id"] == 137409920728 and identity["run_id"] == 45087685319
            and identity["run_attempt"] == 1 and identity["conclusion"] == "failure"
            and identity["head_sha"] == admission["origins"]["sdk"]["source_sha"],
            "Original SDK lane identity/conclusion changed")
    inventory = {item["path"]: item["current_sha256"] for item in admission["source_inputs"]}
    return {"schema": SCHEMA, "status": "PASS_RETAINED_CONTROLLER_CONTROLS_ONLY",
            "source_root": str(root), "admission_sha256": digest(admission_raw),
            "current_control_methods": 98, "retained_original_methods": 91,
            "qualified_observer_methods": 7, "retired_historical_methods": 1,
            "controller_methods_executed_now": 0, "product_tests_executed_now": 0,
            "original_lane_conclusions": {"45096079315": "FAIL", "45087685319": "failure"},
            "source_inputs": inventory, "original_proof_batches": admission["batches"],
            "origins": admission["origins"], "current_catalog": catalog,
            "source_inventory_sha256": digest(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()),
            "scope_limit": "Controller evidence only; no original lane success, current XCTest, build or runtime acceptance."}
