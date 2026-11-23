"""Focused controls for the reviewed original export/restrictions source repair."""
import hashlib
import json
from pathlib import Path

GROUPS = {
    "github.com/anyproto/anytype-heart/core/block/export": {
        "parent": "TestOtzariaObjectTypeDataviewExportClosure",
        "leaves": ["object_type_original_hidden_column", "plain_page_does_not_gain_type_closure"],
    },
    "github.com/anyproto/anytype-heart/core/block/import": {
        "parent": "TestOtzariaOriginalSchemaRestrictionSemantics",
        "leaves": [
            "original_diff_nil_empty_no_event", "replayed_nil_matches_exported_empty",
            "refuse_changed_read", "refuse_changed_edit", "refuse_changed_remove",
            "refuse_changed_drag", "refuse_changed_drop_on",
            "refuse_changed_hidden_relation", "refuse_changed_nested_body",
        ],
    },
}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def case_intake(path, package):
    path = Path(path)
    require(package in GROUPS and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= 8 * 1024 * 1024,
            "Focused schema control JSON log absent, unsafe or beyond bound")
    events = [json.loads(line) for line in path.read_text().splitlines()]
    group = GROUPS[package]
    names = {group["parent"]} | {group["parent"] + "/" + leaf for leaf in group["leaves"]}
    rows = {}
    for name in sorted(names):
        actions = [event.get("Action") for event in events
                   if event.get("Package") == package and event.get("Test") == name]
        terminals = [action for action in actions if action in ("pass", "fail", "skip")]
        rows[name] = {
            "run_count": actions.count("run"), "terminal_actions": terminals,
            "status": terminals[0].upper() if len(terminals) == 1 else
                      ("NOT_RUN" if "run" not in actions else "NO_UNIQUE_TERMINAL"),
        }
    unexpected = sorted({
        str((event.get("Package"), event.get("Test")))
        for event in events
        if event.get("Package") != package or
           (event.get("Test") and event["Test"] not in names)
    })
    package_terminals = [event.get("Action") for event in events
                         if event.get("Package") == package and not event.get("Test")
                         and event.get("Action") in ("pass", "fail", "skip")]
    passed = not unexpected and package_terminals == ["pass"] and all(
        row["run_count"] == 1 and row["terminal_actions"] == ["pass"]
        for row in rows.values())
    leaf_rows = [row for name, row in rows.items() if name != group["parent"]]
    return {
        "status": "PASS" if passed else "FAIL_OR_INCOMPLETE",
        "package": package, "parent": rows[group["parent"]], "cases": rows,
        "leaf_count": len(group["leaves"]),
        "leaf_pass": sum(row["status"] == "PASS" for row in leaf_rows),
        "leaf_fail": sum(row["status"] == "FAIL" for row in leaf_rows),
        "leaf_skip": sum(row["status"] == "SKIP" for row in leaf_rows),
        "leaf_not_run": sum(row["status"] == "NOT_RUN" for row in leaf_rows),
        "unexpected_events": unexpected, "package_terminal_actions": package_terminals,
        "json_events": len(events),
    }


def run_controls(*, commands, go, heart, work, evidence, declaration, repair):
    heart, work, evidence = map(Path, (heart, work, evidence))
    require(repair["new_control_groups"] == GROUPS and repair["new_control_leaf_count"] == 11,
            "Reviewed source-repair selector inventory differs")
    directory = work / "schema-closure-controls"
    directory.mkdir()
    declared = {row["path"]: row for row in declaration["files"]}
    inputs = []
    for row in repair["inputs"]:
        path = (heart / row["native_path"]).resolve()
        actual = declared.get(str(path))
        require(actual is not None and path.is_file() and not path.is_symlink()
                and path.stat().st_size == row["bytes"]
                and actual["bytes"] == row["bytes"]
                and actual["sha256"] == row["sha256"] == digest(path),
                "Actual declared schema-repair compiler source differs")
        inputs.append({"path": row["native_path"], "bytes": row["bytes"], "sha256": row["sha256"]})
    report = {
        "status": "STARTED_NOT_ACCEPTED", "leaf_count": 11,
        "groups": {}, "actual_compiler_inputs": inputs, "binaries": [],
        "production_import_activated": False,
    }
    receipt = evidence / "SCHEMA_CLOSURE_CONTROLS.json"
    write_json(receipt, report)
    binaries = []
    for package, group in GROUPS.items():
        relative = "./" + package.removeprefix("github.com/anyproto/anytype-heart/")
        label = package.rsplit("/", 1)[1]
        binary = directory / (label + ".test")
        argv = [go, "test", "-c", "-p", "2", "-o", str(binary), relative]
        commands.require("compile-schema-control-" + label, argv, heart, 1800)
        compile_receipt = dict(commands.items[-1])
        require(binary.is_file() and not binary.is_symlink() and binary.stat().st_size > 0,
                "Original schema control compiler emitted no owned binary")
        record = {"package": package, "path": str(binary), "bytes": binary.stat().st_size,
                  "sha256": digest(binary), "compile_command": compile_receipt,
                  "retained_in_artifact": False}
        binaries.append((binary, record))
        report["binaries"].append(record)
        commands.require("schema-control-buildinfo-" + label,
                         [go, "version", "-m", str(binary)], heart, 30)
        write_json(receipt, report)
        code, output, _ = commands.run("execute-schema-control-" + label, [
            go, "tool", "test2json", "-t", "-p", package, str(binary),
            "-test.v=test2json", "-test.run=^" + group["parent"] + "$",
            "-test.count=1", "-test.timeout=5m",
        ], heart, 330)
        intake = case_intake(output, package)
        intake["effective_command_returncode"] = code
        intake["binary_unchanged"] = digest(binary) == record["sha256"]
        report["groups"][package] = intake
        write_json(receipt, report)
    for row in repair["inputs"]:
        require(digest(heart / row["native_path"]) == row["sha256"],
                "Schema-repair source changed after focused controls")
    report["status"] = "PASS" if all(
        row["status"] == "PASS" and row["effective_command_returncode"] == 0
        and row["binary_unchanged"] for row in report["groups"].values()
    ) and len(report["groups"]) == len(GROUPS) and commands.owned_groups_drained else "FAIL_OR_INCOMPLETE"
    report["leaf_pass"] = sum(row["leaf_pass"] for row in report["groups"].values())
    report["leaf_fail"] = sum(row["leaf_fail"] for row in report["groups"].values())
    report["leaf_skip"] = sum(row["leaf_skip"] for row in report["groups"].values())
    report["leaf_not_run"] = sum(row["leaf_not_run"] for row in report["groups"].values())
    write_json(receipt, report)
    return report, binaries
