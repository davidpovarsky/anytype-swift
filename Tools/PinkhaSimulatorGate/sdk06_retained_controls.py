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
ADMISSION_SHA256 = "cb510c5380851626195f68b380ffa02bd5f58fddc9274529d156350079add6be"
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


def reverse_scoped_edits(data, edits, expected_sha256):
    """Recover only an immutable reviewed view; never write modified source."""
    source = data.decode("utf-8")
    for edit in reversed(edits):
        old, new = edit["old"], edit["new"]
        require(isinstance(old, str) and isinstance(new, str) and bool(new)
                and source.count(new) == 1, "Ambiguous or missing fixed composition hunk")
        source = source.replace(new, old, 1)
    recovered = source.encode("utf-8")
    require(digest(recovered) == expected_sha256, "Fixed composition inverse differs from its reviewed source")
    ast.parse(source)
    return recovered


def focused_outcomes(events_raw, log_raw, result_raw):
    events, result = decode_json(events_raw), decode_json(result_raw)
    require(isinstance(events, list), "Original focused events must be a list")
    starts, outcomes, active = [], {}, None
    for event in events:
        name = event.get("name")
        require(isinstance(name, str) and name.count(".") == 2, "Malformed original focused method")
        if event.get("event") == "start":
            require(active is None and name not in starts, "Repeated or overlapping original focused method")
            starts.append(name)
            active = name
        else:
            require(event.get("event") == "terminal" and name == active
                    and event.get("status") in ("PASS", "FAIL", "ERROR"),
                    "Missing or invalid original focused terminal")
            outcomes[name] = event["status"]
            active = None
    require(active is None and len(starts) == len(outcomes) == result["tests_run"],
            "Original focused event count differs")
    raw_outcomes = {}
    for line in log_raw.decode("utf-8").splitlines():
        match = re.fullmatch(r"(test_\w+) \(([\w.]+)\) \.\.\. (ok|FAIL|ERROR)", line)
        if match:
            name = match.group(2)
            require(name.rsplit(".", 1)[-1] == match.group(1) and name not in raw_outcomes,
                    "Ambiguous original focused log identity")
            raw_outcomes[name] = "PASS" if match.group(3) == "ok" else match.group(3)
    require(raw_outcomes == outcomes, "Original focused event and raw named outcomes disagree")
    summaries = re.findall(r"^Ran (\d+) tests? in ([0-9.]+)s$", log_raw.decode("utf-8"), re.MULTILINE)
    require(len(summaries) == 1 and int(summaries[0][0]) == len(outcomes),
            "Original focused raw summary differs")
    failures = sum(value == "FAIL" for value in outcomes.values())
    errors = sum(value == "ERROR" for value in outcomes.values())
    require(result["failures"] == failures and result["errors"] == errors
            and result["source_unchanged"] is True
            and result["old_control_methods_executed"] == 0 and result["product_tests_executed"] == 0,
            "Original focused scope or source integrity differs")
    tail = log_raw.decode("utf-8").rstrip().splitlines()[-1]
    if failures or errors:
        labels = ([f"failures={failures}"] if failures else []) + ([f"errors={errors}"] if errors else [])
        require(result["status"] == "FAIL" and tail == "FAILED (" + ", ".join(labels) + ")",
                "Original failed focused attempt was relabelled")
    else:
        require(result["status"] == "PASS" and tail == "OK", "Original focused PASS terminal is missing")
    require(digest(log_raw) == result["logs_sha256"], "Original focused result/log binding differs")
    return outcomes


def verify_frozen_composition(extension, files):
    require(extension["protocol"] == "sdk06-fixed-retained-composition-v1",
            "Unknown fixed SDK composition")
    require(digest(files[extension["manifest"]]) == extension["manifest_sha256"],
            "Original composition manifest binding differs")
    current = {}
    for path, expected in extension["current_inputs"].items():
        require(path in files and digest(files[path]) == expected, "Unbound composition dependency: " + path)
        current[path] = files[path]
    original_manifest = decode_json(files[extension["manifest"]])
    for path, expected in original_manifest["code_sha256"].items():
        require(path in current and digest(current[path]) == expected,
                "Frozen composition code/workflow binding differs")
    bases, versions = {}, {}
    for path, binding in extension["inverses"].items():
        data = current[path]
        for layer in binding["layers"]:
            data = reverse_scoped_edits(data, layer["edits"], layer["result_sha256"])
            versions[(path, layer["view"])] = data
        baseline = files[binding["baseline_snapshot"]]
        require(data == baseline and digest(data) == binding["baseline_sha256"],
                "Composition no longer recovers the exact retained baseline")
        bases[path] = data
    supervisor = "Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
    kernel = extension["kernel_view"]
    versions[(supervisor, "kernel-only")] = reverse_scoped_edits(
        current[supervisor], kernel["inverse_qualified_edits"], kernel["sha256"])
    require(versions[(supervisor, "kernel-only")] == files[kernel["snapshot"]],
            "Separately tested kernel view differs")
    for path, entry in extension["historical_source_views"].items():
        versions[(path, entry["view"])] = files[entry["snapshot"]]

    def view(path, label):
        require(label == "current" or (path, label) in versions, "Unreviewed historical composition view")
        return current[path] if label == "current" else versions[(path, label)]

    fixture = extension["selector_fixture_review"]
    previous = ast.parse(files[fixture["previous_snapshot"]].decode("utf-8"))
    present = ast.parse(current[fixture["path"]].decode("utf-8"))
    old_function = [node for node in previous.body
                    if isinstance(node, ast.FunctionDef) and node.name == "source_selection"]
    changed = [i for i, node in enumerate(present.body)
               if isinstance(node, ast.FunctionDef) and node.name == "source_selection"]
    require(len(old_function) == len(changed) == 1, "Changed selector fixture review boundary")
    present.body[changed[0]] = old_function[0]
    require(ast.dump(present, include_attributes=False) == ast.dump(previous, include_attributes=False),
            "Retained selector declarations/helpers changed beyond the failed fixture")

    outcomes, attempts = {}, {}
    for attempt in extension["attempts"]:
        ident = attempt["id"]
        require(ident not in outcomes, "Repeated focused attempt identity")
        result = decode_json(files[attempt["result"]])
        require(result["source_sha"] == attempt["source_sha"], "Focused attempt source changed")
        require(files[attempt["source_before"]] == files[attempt["source_after"]],
                "Original focused source changed during execution")
        before = decode_json(files[attempt["source_before"]])
        for path, expected in before.items():
            require(digest(view(path, attempt["source_views"].get(path, "current"))) == expected,
                    "Focused production/dependency source is not retained: " + path)
        actual = focused_outcomes(files[attempt["events"]], files[attempt["log"]], files[attempt["result"]])
        require(actual == attempt["outcomes"], "Focused named execution scope changed")
        outcomes[ident], attempts[ident] = actual, attempt

    qualified = []
    for name, binding in extension["qualified_methods"].items():
        ident, path = binding["attempt"], binding["test_path"]
        require(outcomes[ident].get(name) == "PASS", "A failed/unexecuted focused method cannot qualify")
        short = ".".join(name.rsplit(".", 2)[-2:])
        original = view(path, attempts[ident]["source_views"].get(path, "current"))
        require(test_declarations(original).get(short) == test_declarations(current[path]).get(short)
                == binding["declaration_sha256"], "Qualified focused declaration changed")
        qualified.append(name)
    require(len(qualified) == 27 and len(set(qualified)) == 27,
            "Expected separate 18 composition and nine kernel methods")
    first, repaired = outcomes["qualified-attempt1"], outcomes["qualified-attempt2"]
    require(sum(value == "PASS" for value in first.values()) == 11
            and {name for name, value in first.items() if value == "ERROR"} == set(repaired)
            and all(value == "PASS" for value in repaired.values()) and len(repaired) == 7,
            "The seven original errors or 11 retained passes were relabelled/repeated")
    require(len(outcomes["kernel-attempt1"]) == 9
            and all(value == "PASS" for value in outcomes["kernel-attempt1"].values()),
            "Kernel focused scope differs")
    return bases, {
        "status": "PASS_FIXED_CONTROLLER_COMPOSITION_ONLY",
        "original_composition_manifest_sha256": extension["manifest_sha256"],
        "current_source_inputs": extension["current_inputs"],
        "recovered_baseline_inputs": {path: digest(data) for path, data in bases.items()},
        "composition_methods_qualified": 18, "kernel_methods_qualified": 9,
        "original_failed_attempt_preserved": True, "retained_original_passes": 11,
        "repaired_former_errors": 7, "qualified_methods": sorted(qualified),
        "methods_executed_now": 0, "selector_admission_claimed": False, "product_acceptance_claimed": False,
    }



def qualified_profile_pair_outcomes(events_raw, log_raw, result_raw, methods, source_sha):
    """Admit only the original one-new/one-affected SDK profile pair."""
    result, events = decode_json(result_raw), decode_json(events_raw)
    require(result.get("source_sha") == source_sha and result.get("status") == "PASS"
            and result.get("tests_run") == 2 and result.get("failures") == result.get("errors") == 0
            and result.get("source_unchanged") is True, "Original SDK profile pair did not pass unchanged")
    require(result.get("old_control_methods_executed") == 1
            and result.get("directly_affected_control_methods_executed") == 1
            and result.get("new_control_methods_executed") == 1
            and result.get("other_previously_passed_methods_executed") == 0
            and result.get("original_18_suite_repeated") is False
            and result.get("original_kernel9_repeated") is False
            and result.get("product_tests_executed") == result.get("mac_builds") == 0,
            "Original SDK profile affected/new execution scope was relabelled")
    require(result.get("selected_methods") == methods and len(methods) == len(set(methods)) == 2,
            "Original SDK profile method selection differs")
    require(isinstance(events, list) and len(events) == 4, "Original SDK profile pair events differ")
    for index, name in enumerate(methods):
        start, terminal = events[2 * index:2 * index + 2]
        require(start.get("event") == "start" and start.get("name") == name
                and terminal == {"event": "terminal", "name": name, "status": "PASS"},
                "Original SDK profile named terminal is missing or changed")
    batches = unittest_batches(log_raw)
    require(len(batches) == 1 and batches[0]["count"] == 2
            and [entry["name"] for entry in batches[0]["methods"]]
                == [".".join(name.rsplit(".", 2)[-2:]) for name in methods]
            and digest(log_raw) == result.get("logs_sha256"),
            "Original SDK profile events/raw outcomes disagree")
    return list(methods)


def qualified_kernel_profile_view(admission, files):
    """Recover the one exact preceding admission; actual new bytes stay pinned."""
    key = "sdk_qualified_kernel_profile_addendum"
    extension = admission[key]
    require(extension["protocol"] == "sdk06-qualified-kernel-profile-fixed-v1"
            and extension["profile"] == "sdk06-qualified",
            "Unknown fixed SDK-qualified kernel profile")
    production = "Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
    fixture = "Tools/PinkhaSimulatorGate/test_sdk06_qualified_lifecycle.py"
    new_test = "Tools/PinkhaSimulatorGate/test_sdk06_qualified_kernel_profile.py"
    require(set(extension["inverses"]) == {production, fixture}, "SDK profile inverse scope differs")
    require(extension["inverses"][production]["edits"] == [{
        "old": '    if cleanup_profile == "sdk06-enumeration":\n',
        "new": '    if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified"):\n'}],
        "Only the exact SDK-qualified predicate alias is admitted")
    prior = decode_json(files[extension["prior_admission_snapshot"]])
    require(digest(files[extension["prior_admission_snapshot"]]) == extension["prior_admission_sha256"],
            "Original fixed composition admission changed")
    normalized = decode_json(json.dumps(admission).encode())
    normalized.pop(key)
    additions = extension["proof_additions"]
    require(len(additions) == len(set(additions))
            and all(path == new_test or path.startswith(
                "docs/validation/20261123-sdk06-qualified-kernel-profile/") for path in additions),
            "SDK profile proof scope is not the fixed additive boundary")
    normalized["proof_files"] = [row for row in normalized["proof_files"] if row["path"] not in additions]
    for row in normalized["proof_files"]:
        if row["path"] in extension["inverses"]:
            row["sha256"] = extension["inverses"][row["path"]]["before_sha256"]
    for row in normalized["source_inputs"]:
        if row["path"] == production:
            row["current_sha256"] = extension["inverses"][production]["before_sha256"]
    require(normalized == prior, "Existing fixed admission changed outside the reviewed profile addendum")

    prior_files = dict(files)
    for path, binding in extension["inverses"].items():
        require(digest(files[path]) == binding["current_sha256"], "Current SDK profile source differs")
        restored = reverse_scoped_edits(files[path], binding["edits"], binding["before_sha256"])
        require(restored == files[binding["snapshot"]], "Original SDK profile source view differs")
        prior_files[path] = restored
    proof = extension["original_pair"]
    require(files[proof["source_before"]] == files[proof["source_after"]],
            "Original SDK profile pair changed source during execution")
    tested = decode_json(files[proof["source_before"]])
    require(tested == extension["tested_inputs"] and len(tested) == 44,
            "Original SDK profile dependency closure differs")
    for path, expected in tested.items():
        require(path in files and digest(files[path]) == expected,
                "Untested SDK profile source/dependency: " + path)
    methods = qualified_profile_pair_outcomes(files[proof["events"]], files[proof["log"]],
        files[proof["result"]], proof["methods"], proof["source_sha"])
    affected = proof["methods"][0]
    require(affected == "test_sdk06_qualified_lifecycle.QualifiedLifecycleControls."
            "test_explicit_sdk_quiescence_uses_same_ten_seconds_and_rejects_late_zero"
            and proof["methods"][1] == "test_sdk06_qualified_kernel_profile.QualifiedKernelProfileControls."
            "test_sdk_qualified_kernel_wiring_preserves_identity_fallback_and_original_deadline",
            "Unknown SDK profile affected/new method")
    previous_tree = ast.parse(prior_files[fixture].decode("utf-8"))
    current_tree = ast.parse(files[fixture].decode("utf-8"))
    def method(tree):
        klass = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                     and node.name == "QualifiedLifecycleControls")
        found = [(index, node) for index, node in enumerate(klass.body)
                 if isinstance(node, ast.FunctionDef) and node.name == affected.rsplit(".", 1)[-1]]
        require(len(found) == 1, "Affected SDK lifecycle method is missing or repeated")
        return klass, found[0]
    old_class, (_, original) = method(previous_tree)
    current_class, (index, _) = method(current_tree)
    current_class.body[index] = original
    require(ast.dump(previous_tree, include_attributes=False) == ast.dump(current_tree, include_attributes=False),
            "Other original lifecycle declarations/helpers changed")
    for path, full_name in ((fixture, methods[0]), (new_test, methods[1])):
        short = ".".join(full_name.rsplit(".", 2)[-2:])
        require(test_declarations(files[path]).get(short) == proof["declaration_sha256"][full_name],
                "Original SDK profile named declaration differs")
    require(len(test_declarations(files[new_test])) == 1, "Unexecuted SDK profile controls were added")
    return prior, prior_files, {
        "status": "PASS_FIXED_SDK_QUALIFIED_KERNEL_PROFILE_ONLY",
        "profile": "sdk06-qualified", "source_scope": "EXACT_NEW_PROFILE_AND_AFFECTED_FIXTURE",
        "qualified_source_sha": proof["source_sha"], "current_tested_inputs": tested,
        "historical_composition_methods_preserved": 18,
        "unchanged_original_composition_methods_retained": 17,
        "directly_affected_composition_methods_requalified": 1,
        "new_profile_methods_qualified": 1, "current_composition_methods_qualified": 19,
        "original_kernel_methods_retained": 9, "original_18_history_relabelled": False,
        "qualified_methods": methods, "current_source_inputs": {
            path: digest(files[path]) for path in (production, fixture, new_test)},
        "recovered_prior_sources": {path: digest(prior_files[path]) for path in extension["inverses"]},
        "methods_executed_now": 0, "selector_admission_claimed": False, "product_acceptance_claimed": False,
    }


def fixed_dependency_control_outcomes(kind, record, events, log_raw, methods):
    """Read only three fixed original batches; never turn snapshots into tests."""
    if kind == "coherent-nested":
        # The original child diagnostic shares the second method line. Retain
        # its pinned raw bytes and the actual following unittest outcome.
        require(hashlib.sha256(log_raw).hexdigest() ==
                "27efe77166d4ec098b9008a4b3727c5dd49c55dd5922f513d67beca577aa8700",
                "Original coherent nested diagnostic log differs")
        diagnostic = b'COHERENT_ORIGINAL_CWD_CONTROL {"coherentOwnedPID": 2215159, "coherentReturnCode": 0, "defaultOriginalCwdFieldAbsent": true, "defaultOwnedPID": 2215162, "nestedCleanup": "PASS", "nestedGroupsChecked": 1, "originalBytesUnchangedAfterNestedCleanup": true, "originalCwdMatchesActualProcess": true, "originalSHA256": "52068f76fcc1faeaa601a3f6c485a9ad8686a0053bddd48240ef61a4efcd8a62", "productTestsExecuted": 0}\n'
        require(log_raw.count(diagnostic + b"ok\n") == 1,
                "Original coherent nested diagnostic and following ok differ")
        log_raw = log_raw.replace(diagnostic, b"", 1)
    batches = unittest_batches(log_raw)
    require(len(batches) == 1 and batches[0]["count"] == len(methods)
            and [entry["name"] for entry in batches[0]["methods"]] ==
                [".".join(name.rsplit(".", 2)[-2:]) for name in methods],
            "Dependency raw named outcomes differ")
    require(record.get("status") == "PASS", "Original dependency control batch did not pass")
    if kind == "basename-consumer":
        require(record.get("source_sha") == "51dd4936221bcbf802b0bf1bcd54853337e0df3b"
                and record.get("tests_run") == 2 and record.get("method_ids") == methods
                and record.get("new_control_methods_executed") == 2
                and record.get("old_control_methods_executed") == 0
                and record.get("actual_product_tests_executed") == record.get("app_builds") == 0
                and record.get("failures") == record.get("errors") == 0
                and record.get("selector_admission_created") is False
                and record.get("source_unchanged") is True,
                "Basename consumer scope was relabelled")
        require(events == [event for name in methods for event in
                ({"event": "START", "test_id": name}, {"event": "PASS", "test_id": name})],
                "Basename consumer named terminals differ")
    elif kind == "coherent-nested":
        require(record.get("source_commit") == "9980c31979bce6898bd1bf2f57b88a415e60d0d9"
                and record.get("tests_run") == 2 and record.get("exception") is None
                and record.get("old_controls_executed") == record.get("product_tests_executed") ==
                    record.get("simulator_commands_executed") == 0
                and record.get("source_before_after_unchanged") is True
                and events == record.get("methods")
                and [row.get("id") for row in events] == methods
                and all(row.get("outcome") == "PASS" for row in events),
                "Coherent nested named outcomes or execution scope differ")
    else:
        require(kind == "coherent-lookup" and len(methods) == 1
                and record.get("source") == "20e90f32cc4071e775f5547dd5b93df78e7f54a3"
                and record.get("method") == methods[0]
                and record.get("new_control_methods") == 1
                and record.get("old_control_methods") == record.get("product_methods") ==
                    record.get("actual_simulator_queries") == 0
                and record.get("errors") == record.get("failures") == record.get("skips") == 0
                and record.get("subcases_passed") == 5 and record.get("before_after_unchanged") is True,
                "Coherent lookup scope was relabelled")
        expected = [{"event": "START", "test": methods[0]}]
        expected += [{"event": "SUBCASE_PASS", "test": methods[0] + " (status='" + status + "')"}
                     for status in ("RETURNED", "RETURNED", "TIMED_OUT", "OS_ERROR", "INTERRUPTED")]
        expected += [{"event": "PASS", "test": methods[0]}]
        require(events == expected, "Coherent lookup five original observations differ")
    return list(methods)


def post_profile_dependency_view(admission, files):
    """Recover the fixed da6 view while separately binding every new branch."""
    key = "post_profile_dependency_addendum"
    extension = admission[key]
    require(extension["protocol"] == "sdk06-post-profile-fixed-dependencies-v1"
            and extension["prior_admission_sha256"] ==
                "544cd791e86207c2f57a07bfc19effce104e6a258a20eca6655b874eec8bcbe4",
            "Unknown fixed post-profile dependency origin")
    prior_raw = files[extension["prior_admission_snapshot"]]
    require(digest(prior_raw) == extension["prior_admission_sha256"],
            "Original profile admission changed")
    prior = decode_json(prior_raw)
    normalized = decode_json(json.dumps(admission).encode())
    normalized.pop(key)
    additions = extension["proof_additions"]
    permitted_tools = {
        "Tools/PinkhaSimulatorGate/sdk06_basename_enumeration_probe.py",
        "Tools/PinkhaSimulatorGate/sdk06-basename-probe-plan.json",
        "Tools/PinkhaSimulatorGate/test_sdk06_basename_enumeration_probe.py",
        "Tools/PinkhaSimulatorGate/test_sdk06_qualified_basename_selector.py",
        "Tools/PinkhaSimulatorGate/coherent_heart_release.py",
        "Tools/PinkhaSimulatorGate/run_t5_apple_pair.py",
        "Tools/PinkhaSimulatorGate/coherent_container_observation.py",
        "Tools/PinkhaSimulatorGate/test_coherent_container_observation.py",
        "Tools/PinkhaSimulatorGate/test_coherent_original_nested_cleanup.py",
        "Tools/PinkhaSimulatorGate/test_sdk06_dependency_composition.py",
        ".github/workflows/pinkha-sdk06-basename-probe.yml",
        ".github/workflows/torah-inspector-ipados27.yml",
    }
    permitted_prefixes = (
        "docs/validation/20261123-sdk06-post-profile-composition/",
        "docs/validation/20261123-sdk06-qualified-basename-selector/",
        "docs/validation/20261123-sdk06-basename-probe/",
        "docs/validation/20261123-coherent-nested-repair/",
        "docs/validation/20261123-coherent-container-observation/",
    )
    require(len(additions) == len(set(additions))
            and all(path in permitted_tools or path.startswith(permitted_prefixes) for path in additions),
            "Unreviewed dependency proof addition")
    normalized["proof_files"] = [row for row in normalized["proof_files"] if row["path"] not in additions]
    for row in normalized["proof_files"]:
        if row["path"] in extension["inverses"]:
            row["sha256"] = extension["inverses"][row["path"]]["before_sha256"]
    require(normalized == prior, "Existing profile admission changed outside exact dependency additions")

    selector = "Tools/PinkhaSimulatorGate/sdk06_qualified_selector.py"
    wave = "Tools/PinkhaSimulatorGate/wave15_batch.py"
    supervisor = "Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
    shared = "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"
    released = {
        wave, "Tools/PinkhaSimulatorGate/coherent_heart_release.py",
        "Tools/PinkhaSimulatorGate/coherent_original_products.py",
        "Tools/PinkhaSimulatorGate/run_t5_apple_pair.py",
    }
    require(set(extension["inverses"]) == released | {selector},
            "Only the exact five composed dependency sources may differ")
    selector_review = decode_json(files[extension["selector_source_review"]])
    release_review = decode_json(files[extension["release_exact_edits"]])
    lookup_review = decode_json(files[extension["lookup_qualification"]])
    expected = {selector: [{"old": row["before"], "new": row["after"]}
                           for row in selector_review["exact_source_edits"]]}
    for row in release_review["edits"]:
        require(row["path"] in released, "Unexpected Release source inverse")
        expected.setdefault(row["path"], []).append({"old": row["before"], "new": row["after"]})
    lookup = lookup_review["batch_exact_inverse"]
    lookup_edit = {"old": lookup["before"], "new": lookup["after"]}
    expected[wave].append(lookup_edit)
    require(selector_review["full_inverse_exact"] is True
            and release_review["base"] == "67809875752085047a395be4a751ace5dcbc7ad8"
            and lookup["before_sha256"] == "795ecec97eeeacea37d6dea05dc038f487c90f526c251c59823221d5157231da"
            and lookup["after_sha256"] == "0b743b54a62610d9cdb2b92a97e73b479ba347e241c1fa29eb8b8baa348aa5a0",
            "The reviewed dependency source origins differ")
    prior_files = dict(files)
    for path, binding in extension["inverses"].items():
        require(binding["edits"] == expected[path] and digest(files[path]) == binding["current_sha256"],
                "Composed source or exact inverse changed")
        restored = reverse_scoped_edits(files[path], binding["edits"], binding["before_sha256"])
        require(restored == files[binding["snapshot"]], "Composed dependency did not recover exact prior bytes")
        prior_files[path] = restored

    # These are precisely the already reviewed SDK-only inverses. No AST/name
    # deletion or arbitrary source exclusion is used.
    sdk_wave = prior["composition_extension"]["inverses"][wave]["layers"]
    require(len(sdk_wave) == 1, "Unexpected SDK batch inverse layers")
    lookup_wave = reverse_scoped_edits(files[wave], sdk_wave[0]["edits"], lookup["after_sha256"])
    nested_wave = reverse_scoped_edits(lookup_wave, [lookup_edit], lookup["before_sha256"])
    baseline = {}
    for path in (supervisor, shared):
        data = prior_files[path]
        profile_binding = prior["sdk_qualified_kernel_profile_addendum"]["inverses"].get(path)
        if profile_binding is not None:
            data = reverse_scoped_edits(data, profile_binding["edits"], profile_binding["before_sha256"])
        binding = prior["composition_extension"]["inverses"][path]
        for layer in binding["layers"]:
            data = reverse_scoped_edits(data, layer["edits"], layer["result_sha256"])
        require(data == files[binding["baseline_snapshot"]], "Original exercised dependency baseline differs")
        baseline[path] = data

    original_workflows = extension["original_workflow_snapshots"]
    require(set(original_workflows) == {
        ".github/workflows/pinkha-sdk06-basename-probe.yml",
        ".github/workflows/torah-inspector-ipados27.yml"},
        "Only the two original workflow data identities may use snapshots")
    require(set(extension["batches"]) == {"basename-consumer", "coherent-nested", "coherent-lookup"},
            "Unknown dependency qualification batch")
    reports = {}
    for kind, proof in extension["batches"].items():
        require(files[proof["source_before"]] == files[proof["source_after"]],
                "Original dependency sources changed during execution")
        before = decode_json(files[proof["source_before"]])
        record = decode_json(files[proof["receipt"]])
        events = decode_json(files[proof["events"]])
        methods = fixed_dependency_control_outcomes(kind, record, events, files[proof["log"]], proof["methods"])
        if kind == "coherent-nested":
            require(len(before) == 184 and record["source_inputs"] == 184
                    and len(record["loaded_inputs"]) == 19,
                    "Original184 inventory or actual19 loaded scope differs")
            checked = record["loaded_inputs"]
            require(all(before.get(path) == checksum for path, checksum in checked.items()),
                    "Loaded Release source does not belong to its unchanged original snapshot")
            views = {path: files[path] for path in checked}
            views.update({wave: nested_wave, supervisor: baseline[supervisor], shared: baseline[shared]})
            labels = {wave: "EXACT_ROOT_LOOKUP_AND_SDK_ALIAS_INVERSES",
                      supervisor: "EXACT_ORIGINAL_COHERENT_BRANCH_BASELINE",
                      shared: "EXACT_ORIGINAL_SHARED_EDITOR_BASELINE"}
            original_count, loaded_count = 184, 19
            require(record["log_sha256"] == digest(files[proof["log"]])
                    and record["events_sha256"] == digest(files[proof["events"]]),
                    "Original Release named log/event linkage changed")
        else:
            checked = {path: row["sha256"] for path, row in before["files"].items()}
            labels = {}
            if kind == "basename-consumer":
                require(before["source_sha"] == record["source_sha"]
                        and len(checked) == record["source_input_count"] == 29
                        and len(before["loaded_modules"]) == record["loaded_source_count"] == 17,
                        "Original basename29/17 source closure differs")
                views = {path: prior_files[path] if path in released else files[path] for path in checked}
                labels.update({path: "EXACT_PRE_RELEASE_DEPENDENCY_VIEW" for path in checked if path in released})
                for path, snapshot in original_workflows.items():
                    views[path] = files[snapshot]
                    labels[path] = "ORIGINAL_OPAQUE_GIT_BLOB_DATA_NOT_CURRENT_WORKFLOW_EXECUTION"
                original_count, loaded_count = 29, 17
            else:
                require(before["source"] == record["source"] and len(checked) == record["input_count"] == 4
                        and len(before["loaded"]) == record["loaded_source_count"] == 2,
                        "Original coherent lookup4/2 closure differs")
                views = {path: files[path] for path in checked}
                views[wave] = lookup_wave
                labels[wave] = "EXACT_SDK_ALIAS_INVERSE_ONLY"
                original_count, loaded_count = 4, 2
            loaded = before["loaded_modules"] if kind == "basename-consumer" else before["loaded"]
            require(all(path in checked and row["sha256"] == checked[path] for path, row in loaded.items()),
                    "Original loaded source is outside its recorded snapshot")
        require(set(views) == set(checked), "Unreviewed dependency view input")
        for path, checksum in checked.items():
            require(digest(views[path]) == checksum, "Untested dependency branch bytes: " + path)
        declarations = test_declarations(files[proof["test_path"]])
        require(len(declarations) == len(methods)
                and {".".join(name.rsplit(".", 2)[-2:]) for name in methods} == set(declarations),
                "Dependency test declaration inventory differs")
        require(declarations == proof["declarations"], "Named dependency control source changed")
        reports[kind] = {
            "qualified_methods": methods, "original_source_inventory": original_count,
            "actual_loaded_sources": loaded_count, "bound_scope_sha256": checked,
            "explicit_source_views": labels, "methods_executed_now": 0,
        }
    return prior, prior_files, {
        "status": "PASS_FIXED_POST_PROFILE_DEPENDENCY_COMPOSITION_ONLY",
        "current_dependency_inputs": {path: digest(files[path]) for path in extension["inverses"]},
        "recovered_prior_inputs": {path: digest(prior_files[path]) for path in extension["inverses"]},
        "original_composition_history": 18, "retained_profile_composition_methods": 19,
        "new_basename_consumer_methods": 2, "current_sdk_composition_methods": 21,
        "separate_coherent_dependency_methods": 3, "retained_kernel_methods": 9,
        "original_controller_methods_retained": 98, "original_lane_failures_preserved": True,
        "batches": reports, "methods_executed_now": 0,
        "selector_admission_claimed": False, "product_acceptance_claimed": False,
    }


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
    historical_admission, historical_files, profile_receipt = admission, files, None
    dependency_receipt = None
    if admission.get("post_profile_dependency_addendum") is not None:
        historical_admission, historical_files, dependency_receipt = post_profile_dependency_view(admission, files)
    if historical_admission.get("sdk_qualified_kernel_profile_addendum") is not None:
        historical_admission, historical_files, profile_receipt = qualified_kernel_profile_view(
            historical_admission, historical_files)
    composed_bases, composition_receipt = ({}, None)
    if historical_admission.get("composition_extension") is not None:
        composed_bases, composition_receipt = verify_frozen_composition(
            historical_admission["composition_extension"], historical_files)
    if profile_receipt is not None:
        composition_receipt["source_scope"] = "HISTORICAL_FROZEN_COMPOSITION"
        composition_receipt["historical_source_inputs"] = composition_receipt.pop("current_source_inputs")
    if dependency_receipt is not None:
        require(profile_receipt is not None, "Fixed dependency composition requires its retained profile origin")
        profile_receipt["historical_tested_inputs"] = profile_receipt.pop("current_tested_inputs")
        profile_receipt["source_scope"] = "HISTORICAL_PROFILE_DEPENDENCY_VIEW"
    sources = {}
    for item in admission["source_inputs"]:
        path = item["path"]
        require(path not in sources, "Duplicate admitted current source")
        current = read_bound(root, path, item["current_sha256"])
        if path in composed_bases:
            require(digest(composed_bases[path]) == item["composition_base_sha256"],
                    "Retained dependency baseline is not the admitted composition view")
            current = composed_bases[path]
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
            "fixed_composition": composition_receipt,
            "sdk_qualified_kernel_profile": profile_receipt,
            "qualified_dependency_composition": dependency_receipt,
            "source_inventory_sha256": digest(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()),
            "scope_limit": "Controller evidence only; no original lane success, current XCTest, build or runtime acceptance."}
