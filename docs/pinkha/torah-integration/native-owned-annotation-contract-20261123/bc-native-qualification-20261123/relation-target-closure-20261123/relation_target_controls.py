"""Eight original relation target-type closure controls on the shared export binary."""
import hashlib
import json
from pathlib import Path

PACKAGE = "github.com/anyproto/anytype-heart/core/block/export"
GROUP = {
    "parent": "TestOtzariaRelationTargetTypeExportClosure",
    "leaves": [
        "direct_arbitrary_type", "ordered_multiple_types", "transitive_type_constraint",
        "recommended_only_relation", "cycle_visits_each_type_once",
        "unselected_definition_and_scalar_id_are_not_followed",
        "empty_constraint_adds_no_type", "target_read_error_is_propagated",
    ],
}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def case_intake(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 8 * 1024 * 1024,
            "Relation-target control JSON log absent, unsafe or beyond bound")
    events = [json.loads(line) for line in path.read_text().splitlines()]
    require(all(isinstance(event, dict) for event in events), "Relation-target JSON event is not an object")
    names = {GROUP["parent"]} | {GROUP["parent"] + "/" + leaf for leaf in GROUP["leaves"]}
    rows = {}
    for name in sorted(names):
        actions = [event.get("Action") for event in events
                   if event.get("Package") == PACKAGE and event.get("Test") == name]
        terminals = [action for action in actions if action in ("pass", "fail", "skip")]
        rows[name] = {
            "run_count": actions.count("run"), "terminal_actions": terminals,
            "status": terminals[0].upper() if len(terminals) == 1 else
                      ("NOT_RUN" if "run" not in actions else "NO_UNIQUE_TERMINAL"),
        }
    unexpected = sorted({
        str((event.get("Package"), event.get("Test")))
        for event in events
        if event.get("Package") != PACKAGE or (event.get("Test") and event["Test"] not in names)
    })
    package_terminals = [event.get("Action") for event in events
                         if event.get("Package") == PACKAGE and not event.get("Test")
                         and event.get("Action") in ("pass", "fail", "skip")]
    passed = not unexpected and package_terminals == ["pass"] and all(
        row["run_count"] == 1 and row["terminal_actions"] == ["pass"] for row in rows.values())
    leaves = [row for name, row in rows.items() if name != GROUP["parent"]]
    return {
        "status": "PASS" if passed else "FAIL_OR_INCOMPLETE",
        "package": PACKAGE, "parent": rows[GROUP["parent"]], "cases": rows,
        "leaf_count": 8,
        "leaf_pass": sum(row["status"] == "PASS" for row in leaves),
        "leaf_fail": sum(row["status"] == "FAIL" for row in leaves),
        "leaf_skip": sum(row["status"] == "SKIP" for row in leaves),
        "leaf_not_run": sum(row["status"] == "NOT_RUN" for row in leaves),
        "unexpected_events": unexpected, "package_terminal_actions": package_terminals,
        "json_events": len(events),
    }


def existing_export_binary(*, commands, go, heart, work, record):
    path = Path(record["path"])
    require(path == work / "schema-closure-controls/export.test"
            and path.resolve().is_relative_to(work.resolve())
            and path.is_file() and not path.is_symlink() and path.stat().st_size > 0
            and path.stat().st_size == record["bytes"] and digest(path) == record["sha256"]
            and record["package"] == PACKAGE,
            "Existing current-union export binary identity differs")
    receipt = record["compile_command"]
    require(commands.items.count(receipt) == 1
            and receipt["argv"] == [go, "test", "-c", "-p", "2", "-o", str(path), "./core/block/export"]
            and receipt["cwd"] == str(heart) and receipt["status"] == "TERMINAL"
            and receipt["returncode"] == receipt["effective_returncode"] == 0
            and receipt["timed_out"] is False and receipt["start_new_session"] is True
            and any(item.get("drained") is True for item in receipt["cleanup"]),
            "Export binary has no exact successful current-owner compile receipt")
    return path


def run_controls(*, commands, go, heart, work, evidence, declaration, repair, binary_record):
    heart, work, evidence = map(Path, (heart, work, evidence))
    require(repair["new_control_group"] == GROUP and repair["new_control_leaf_count"] == 8,
            "Reviewed relation-target control selectors differ")
    receipt = evidence / "RELATION_TARGET_CLOSURE_CONTROLS.json"
    require(not receipt.exists(), "Preserve an existing relation-target control execution")
    report = {
        "status": "STARTED_NOT_ACCEPTED", "leaf_count": 8, "cases": "NOT_RUN",
        "actual_compiler_inputs": [], "binary": binary_record,
        "existing_current_union_binary_reused": True, "additional_compile_invocations": 0,
        "runtime_results_reused": False, "production_import_activated": False,
    }
    write_json(receipt, report)
    binary = None
    try:
        require({row["native_path"] for row in repair["inputs"]} == {
            "core/block/export/collection.go",
            "core/block/export/owned_annotation_relation_target_closure_test.go"},
            "Reviewed relation-target source inventory differs")
        declared = {row["path"]: row for row in declaration["files"]}
        for row in repair["inputs"]:
            path = (heart / row["native_path"]).resolve()
            actual = declared.get(str(path))
            require(actual is not None and path.is_relative_to(heart.resolve())
                    and path.is_file() and not path.is_symlink()
                    and path.stat().st_size == actual["bytes"] == row["bytes"]
                    and actual["sha256"] == row["sha256"] == digest(path),
                    "Actual relation-target compiler input differs")
            report["actual_compiler_inputs"].append({
                "path": row["native_path"], "bytes": row["bytes"], "sha256": row["sha256"]})
        binary = existing_export_binary(commands=commands, go=go, heart=heart, work=work,
                                        record=binary_record)
        write_json(receipt, report)
        code, output, _ = commands.run("execute-original-relation-target-closure", [
            go, "tool", "test2json", "-t", "-p", PACKAGE, str(binary),
            "-test.v=test2json", "-test.run=^" + GROUP["parent"] + "$",
            "-test.count=1", "-test.timeout=5m"], heart, 330)
        report["execution_command"] = dict(commands.items[-1])
        report["effective_command_returncode"] = code
        intake = case_intake(output)
        report.update(intake)
        require(code == 0 and intake["status"] == "PASS" and intake["leaf_pass"] == 8,
                "Original relation-target closure controls did not all pass")
    except BaseException as error:
        report.update(status="FAIL_OR_INCOMPLETE", error_type=type(error).__name__, error=str(error))
    finally:
        try:
            require(binary is not None and binary.is_file() and not binary.is_symlink()
                    and binary.stat().st_size == binary_record["bytes"]
                    and digest(binary) == binary_record["sha256"],
                    "Existing export binary changed after relation-target controls")
            for row in repair["inputs"]:
                path = heart / row["native_path"]
                require(path.is_file() and not path.is_symlink()
                        and path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
                        "Relation-target compiler source changed after controls")
            require(commands.owned_groups_drained, "Relation-target owned command group not drained")
            report["post_input_and_binary_stability"] = "PASS"
        except BaseException as error:
            report.update(status="FAIL_OR_INCOMPLETE",
                          post_input_and_binary_stability="FAIL",
                          stability_error_type=type(error).__name__, stability_error=str(error))
        write_json(receipt, report)
    return report
