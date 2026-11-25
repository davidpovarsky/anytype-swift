"""Retain original controller scopes and the separately executed composition controls.

Every normalization is tied to complete before/after bytes and exact AST
changes. Current module/native composition acceptance still requires Apple.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

EVIDENCE = "docs/validation/20261125-current-swift-composition"
REUSE = "Tools/PinkhaNativeDerived/coherent_apple/reuse_build.py"
INSTALLER = "Tools/PinkhaNativeDerived/install_verified_heart.py"
ADMISSION = "Tools/PinkhaNativeDerived/coherent_runtime_admission.py"
SOURCE_PATHS = frozenset({REUSE, INSTALLER, ADMISSION})
ADDED_CONSTANTS = frozenset({"COMPOSITION_STATUS", "COMPOSITION_PROFILE", "COMPOSITION_REVIEW_SOURCE",
    "ORIGINAL_MODULE_MAP_SHA", "CURRENT_MODULE_MAP_SHA", "COMPOSITION_CONTROL",
    "REVIEWED_MODULE_CHANGES", "REVIEWED_COMPOSITION_CONTROLS"})
ADDED_FUNCTIONS = frozenset({"module_sources", "reviewed_pairs", "current_module_lineage",
    "verify_current_composition", "verify_source_lineage", "validate_current_composition_record"})
UNEXECUTED_FUNCTIONS = frozenset({"validate_admission_lineage", "execute", "main"})
CONTINUATION = "codex/chatgpt-wave15-acceptance-continuation-20261122"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ast_digest(value):
    if isinstance(value, (str, bytes)):
        value = ast.parse(value)
    def canonical(node):
        if isinstance(node, ast.AST):
            return {"node": type(node).__name__, **{key: canonical(child) for key, child in ast.iter_fields(node)
                    if not (key == "type_params" and child == [])}}
        if isinstance(node, list):
            return [canonical(child) for child in node]
        if isinstance(node, bytes):
            return {"python_bytes_base64": base64.b64encode(node).decode()}
        if node is Ellipsis:
            return {"python_ellipsis": True}
        return node
    return sha(json.dumps(canonical(value), sort_keys=True, separators=(",", ":")).encode())


def read(root, relative, limit=16 * 1024**2):
    path = PurePosixPath(relative)
    require(relative and not path.is_absolute() and "\\" not in relative
            and all(part not in ("", ".", "..") for part in path.parts), "Invalid retained composition path")
    target = root / path
    require(target.resolve().is_relative_to(root) and not target.is_symlink()
            and not any(parent.is_symlink() for parent in target.parents if parent != root and parent.is_relative_to(root))
            and target.is_file() and 0 < target.stat().st_size <= limit, "Missing or unsafe composition input: " + relative)
    return target.read_bytes()


def named_nodes(tree):
    result = {}
    for node in tree.body:
        name = (node.name if isinstance(node, ast.FunctionDef) else
                node.targets[0].id if isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) else None)
        if name is not None:
            require(name not in result, "Repeated retained controller declaration")
            result[name] = node
    return result


def restore_retained_source(raw, original, review):
    path = review.get("path")
    require(path in SOURCE_PATHS and sha(raw) == review.get("after_sha256")
            and sha(original) == review.get("before_sha256")
            and ast_digest(original) == review.get("original_ast_sha256"),
            "Source differs from the exact reviewed composition before/after bytes")
    tree, old_tree = ast.parse(raw), ast.parse(original)
    nodes, old_nodes = named_nodes(tree), named_nodes(old_tree)
    if path == REUSE:
        expected_added = ADDED_CONSTANTS | ADDED_FUNCTIONS
        require(set(nodes) - set(old_nodes) == expected_added and set(old_nodes) <= set(nodes)
                and set(review.get("added_node_ast_sha256", {})) == expected_added,
                "Unexpected composition helper or constant scope")
        for name in sorted(expected_added):
            require(ast_digest(nodes[name]) == review["added_node_ast_sha256"][name],
                    "New composition helper/constant AST differs: " + name)
            tree.body.remove(nodes[name])
        require(set(review.get("new_unexecuted_body_ast_sha256", {})) == UNEXECUTED_FUNCTIONS,
                "Unexpected retained unexecuted function scope")
        for name in sorted(UNEXECUTED_FUNCTIONS):
            current, old = nodes[name], old_nodes[name]
            require(ast_digest(current.body) == review["new_unexecuted_body_ast_sha256"][name],
                    "New unexecuted function body differs: " + name)
            current.body = old.body
        function = nodes["validate_reuse_record"]
        branch = function.body[0]
        require(isinstance(branch, ast.If) and not branch.orelse
                and ast_digest(branch) == review.get("schema_two_branch_ast_sha256")
                and ast.unparse(branch.test) == "record.get('schemaVersion') == 2",
                "Exact schema-2 delegation branch differs")
        function.body.pop(0)
    elif path == INSTALLER:
        declaration = nodes["APPROVED_BRANCHES"]
        require(isinstance(declaration.value, ast.List)
                and ast_digest(declaration) == review.get("new_approved_branches_ast_sha256"),
                "Exact installer branch inventory differs")
        matches = [node for node in declaration.value.elts if isinstance(node, ast.Constant)
                   and node.value == CONTINUATION]
        require(len(matches) == 1, "Continuation branch is missing or repeated")
        declaration.value.elts.remove(matches[0])
    else:
        function = nodes.get("expected_producer_branch")
        require(function is not None and "expected_producer_branch" not in old_nodes
                and ast_digest(function) == review.get("new_branch_helper_ast_sha256"),
                "Exact producer branch helper differs")
        tree.body.remove(function)
        replacements = []
        for node in ast.walk(nodes["execute"]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "expected_producer_branch":
                require(ast_digest(node) == review.get("new_branch_call_ast_sha256")
                        and len(node.args) == 1 and not node.keywords,
                        "Exact producer branch call differs")
                replacements.append(node)
        require(len(replacements) == 1, "Producer branch call is missing or repeated")
        wanted = replacements[0]
        class RestoreCall(ast.NodeTransformer):
            def visit_Call(self, node):
                return wanted.args[0] if node is wanted else self.generic_visit(node)
        RestoreCall().visit(nodes["execute"])
    require(ast_digest(tree) == review["original_ast_sha256"],
            "Original tested AST/constants changed outside the exact reviewed composition extension")
    return original


def qualify(control, review_sha256, report_sha256):
    root = control.resolve()
    review_raw = read(root, EVIDENCE + "/source-review.json")
    report_raw = read(root, EVIDENCE + "/new-controls.json")
    require(sha(review_raw) == review_sha256 and sha(report_raw) == report_sha256,
            "Current composition review or executed-control report changed")
    review, report = json.loads(review_raw), json.loads(report_raw)
    entries = review.get("reviewed_sources", [])
    require(review.get("status") == "REVIEWED_EXACT_CURRENT_COMPOSITION_AND_RETAINED_AST"
            and len(entries) == 3 and {entry.get("path") for entry in entries} == SOURCE_PATHS,
            "Unexpected current composition retention scope")
    originals = {}
    for entry in entries:
        original = read(root, entry["original_path"])
        originals[entry["path"]] = restore_retained_source(read(root, entry["path"]), original, entry)
    require(report.get("status") == "PASS_AFFECTED_CURRENT_COMPOSITION_CONTROLS_ONLY"
            and report.get("passed") == 7 and report.get("failed") == report.get("skipped") == 0
            and report.get("unaffected_original_python_methods_executed") == 0
            and report.get("affected_current_composition_methods_executed") == 7
            and report.get("old_native_go_and_xctest_methods_executed") == 0
            and report.get("frameworks_built") == 0 and report.get("apple_execution") == "NOT_RUN",
            "New composition control execution scope differs")
    sources, inputs = report.get("source_sha256", {}), report.get("input_sha256", {})
    require(isinstance(sources, dict) and len(sources) == 11
            and isinstance(inputs, dict) and len(inputs) == 5,
            "Incomplete new composition control dependency inventory")
    for name, expected in (sources | inputs).items():
        require(re.fullmatch(r"[0-9a-f]{64}", expected or "")
                and sha(read(root, name)) == expected, "New composition control dependency/input changed: " + name)
    log = read(root, EVIDENCE + "/new-controls.log", 128 * 1024)
    require(sha(log) == report.get("log_sha256"), "New composition raw control log changed")
    text = log.decode("utf8")
    methods = re.findall(r"^(test_\w+) \(__main__\.CurrentCompositionControls\.\1\) \.\.\. ok$", text, re.M)
    require(len(methods) == len(set(methods)) == 7 and methods == report.get("methods")
            and re.search(r"\nRan 7 tests in [0-9.]+s\n\nOK\n\Z", text)
            and not re.search(r"FAIL|ERROR|SKIP|skipped", text), "New composition control outcomes differ")
    return dict(source_before=originals, receipt=dict(
        status="RETAINED_ORIGINAL_SCOPES_AND_SEPARATE_NEW_COMPOSITION_CONTROLS",
        review_sha256=review_sha256, report_sha256=report_sha256,
        normalized_sources=sorted(originals), new_control_methods=methods, new_control_methods_passed=7,
        tests_executed_this_run=0, frameworks_built_this_run=0, apple_execution="NOT_RUN",
        source_sha256=sources, input_sha256=inputs, verifier_sha256=sha(Path(__file__).read_bytes())))
