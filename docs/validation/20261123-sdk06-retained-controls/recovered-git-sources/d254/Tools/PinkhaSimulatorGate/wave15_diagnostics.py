"""Small, non-authoritative diagnostics for the current owned UI execution.

No files, logs or artifacts are read here. Inputs are in-memory result/receipt
objects from the existing runner. Only fixed enums, bounded integers and booleans
can reach an annotation; selectors are replaced with zero-based selection indexes.
The caller retains every acceptance decision and original exception.
"""
import json
import re


NOT_RECORDED = "NOT_RECORDED"
MAX_SELECTORS = 32
MAX_FAILURES = 16
MAX_COUNT = 10000
MAX_ANNOTATION = 12000
LANES = ("inspector", "inspector-search", "properties", "properties-set",
         "canonical-properties", "editor", "quote-drop", "hanlin-native",
         "hanlin-selection", "remaining-release", "retained-heart-release", "startup")
BATCH_LANES = LANES[:6]


def _batch_lanes(profile):
    return ("editor", "quote-drop", "properties-set") if profile == "retained-heart-release" else BATCH_LANES
STATUSES = frozenset({"PASS", "FAIL", "RUNNING", "NOT_RUN", "CANCELLED", "DIAGNOSTIC_READ_FAILED",
    "LANE_PASS_ACCEPTANCE_REVIEW_PENDING", "LANE_FAILED_OBSERVED_TEST",
    "LANE_ABORTED_SETUP_OR_IDENTITY", "BATCH_ABORTED_SETUP_OR_IDENTITY",
    "BATCH_FAILED_OBSERVED_TESTS", "BATCH_BUDGET_EXHAUSTED", "BATCH_FAILED_CLEANUP",
    "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING", "NOT_RUN_SETUP", "NOT_RUN_BUDGET",
    "NOT_COMPLETED_SETUP_OR_IDENTITY", "IN_PROGRESS",
    "SMOKE_PASS_FULL_ACCEPTANCE_PENDING", "STARTUP_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING",
    "NATIVE_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING"})
PHASES = frozenset({"PREFLIGHT", "SETUP", "BUILD", "EXECUTION", "PREPARATION",
    "DEVICE_LANGUAGE_CONFIGURATION", "UI_BUILD", "UI_RUNTIME_PREPARATION", "UI",
    "SHARED_INPUTS_BEFORE_LANE", "LANE", "BUDGET_LIMIT", "COMPLETE"})
SOURCE_STAGES = frozenset({"BEFORE_BUILD", "AFTER_SOURCE_CACHE",
    "AFTER_APP_AND_NATIVE_TEST_BUILD", "AFTER_UI_PROJECT_GENERATION",
    "AFTER_UI_RUNNER_BUILD", "SHARED_INPUTS_BETWEEN_PHASES"})
METHOD_RESULTS = frozenset({"Passed", "Failed", "Skipped", "Expected Failure", "Not Run"})
ERROR_TYPES = {"CalledProcessError": "COMMAND_EXIT", "TimeoutExpired": "TIMEOUT",
    "TimeoutError": "TIMEOUT", "KeyboardInterrupt": "CANCELLATION",
    "CommandCancelled": "CANCELLATION", "TrackedSourceChanged": "SOURCE_IDENTITY",
    "SelectedXCTestFailed": "NAMED_XCTEST_FAILED", "SelectionFailure": "NAMED_XCTEST_FAILED",
    "AssertionError": "ASSERTION",
    "RuntimeError": "RUNTIME_ERROR", "ValueError": "INPUT_OR_RECORD",
    "KeyError": "INPUT_OR_RECORD", "TypeError": "INPUT_OR_RECORD",
    "JSONDecodeError": "INPUT_OR_RECORD", "OSError": "OS_ERROR",
    "FileNotFoundError": "OS_ERROR", "PermissionError": "OS_ERROR"}
ERROR_CATEGORIES = frozenset(ERROR_TYPES.values()) | {"UNCLASSIFIED"}
FAILURE_CATEGORIES = frozenset({"TEXT_ECHO", "CARET", "NATIVE_PERSISTENCE",
    "RETURN", "FOCUS", "WINDOW", "TIMEOUT", "ASSERTION", "UNCLASSIFIED"})
_SELECTOR = re.compile(r"[A-Za-z_][A-Za-z_0-9]*/[A-Za-z_][A-Za-z_0-9]*(?:\(\))?\Z")


def _record(value):
    return value if type(value) is dict else {}


def _enum(value, allowed, default=NOT_RECORDED):
    return value if type(value) is str and value in allowed else default


def _integer(value, minimum=0, maximum=MAX_COUNT):
    return value if type(value) is int and minimum <= value <= maximum else NOT_RECORDED


def _boolean(value):
    return value if type(value) is bool else NOT_RECORDED


def _selector(value):
    if type(value) is str and len(value) <= 512 and _SELECTOR.fullmatch(value):
        return value.removesuffix("()")
    return None


def _selected(value):
    if type(value) is not list or not 1 <= len(value) <= MAX_SELECTORS:
        return None
    names = [_selector(item) for item in value]
    return names if None not in names and len(set(names)) == len(names) else None


def _error_category(value):
    if value is None:
        return NOT_RECORDED
    return ERROR_TYPES.get(value, "UNCLASSIFIED") if type(value) is str else "UNCLASSIFIED"


def _failure_category(value):
    if type(value) is not str:
        return "UNCLASSIFIED"
    # Only inspected assertion prefixes are classified. Evaluated values and
    # source paths are neither copied nor used to build output strings.
    text = value[:2048]
    prefixes = (
        ("Expectation failed: textView.text == line", "TEXT_ECHO"),
        ("Expectation failed: textView.selectedRange == NSRange(", "CARET"),
        ("Expectation failed: emptyCaret.midX > textView.bounds.midX", "CARET"),
        ("Expectation failed: document.infoContainer.recursiveChildren(of: objectId).filter", "NATIVE_PERSISTENCE"),
        ("Expectation failed: !acceptedReturn", "RETURN"),
        ("Issue recorded: The real editor did not focus a distinct empty block; phase=return-after-line-", "RETURN"),
        ("Expectation failed: textView.window != nil && textView.window === controller.view.window", "WINDOW"),
        ("Expectation failed: responders.count == 1 && responders.first === textView", "FOCUS"),
        ("Expectation failed: controller.firstResponderView === textView", "FOCUS"),
        ("Expectation failed: !UITextView().isFirstResponder", "FOCUS"),
        ("Expectation failed: inputReady", "FOCUS"),
        ("Issue recorded: The real editor did not focus a distinct empty block;", "FOCUS"),
        ("Caught error: .missingFocusedBlock", "FOCUS"),
        ("Test exceeded execution time allowance", "TIMEOUT"),
        ("Test exceeded maximum execution time allowance", "TIMEOUT"),
        ("Test timed out after ", "TIMEOUT"),
        ("Expectation failed:", "ASSERTION"),
        ("XCTAssert", "ASSERTION"),
    )
    return next((category for prefix, category in prefixes if text.startswith(prefix)), "UNCLASSIFIED")


def selection_observation(result, summary=None):
    """Return observations, not a replacement result or acceptance verdict."""
    result, summary = _record(result), _record(summary)
    names = _selected(result.get("selected"))
    actual = result.get("actual_methods")
    methods = {}
    unexpected = NOT_RECORDED
    if names is not None and type(actual) is dict and len(actual) <= MAX_COUNT:
        unexpected = 0
        for name, outcome in actual.items():
            normalized = _selector(name)
            if normalized not in names:
                unexpected += 1
            elif normalized in methods:
                # Ambiguous normalized identifiers must not be reported Passed.
                methods[normalized] = NOT_RECORDED
                unexpected += 1
            else:
                methods[normalized] = _enum(outcome, METHOD_RESULTS)
    failures = summary.get("testFailures")
    rows, omitted = [], NOT_RECORDED
    if type(failures) is list:
        omitted = _integer(max(0, len(failures) - MAX_FAILURES))
        for item in failures[:MAX_FAILURES]:
            item = _record(item)
            name = _selector(item.get("testIdentifierString"))
            index = names.index(name) if names is not None and name in names else NOT_RECORDED
            rows.append({"selector_index": index, "category": _failure_category(item.get("failureText"))})
    return {"schema": 1, "kind": "SELECTION", "diagnostic_only": True,
        "reported_status": _enum(result.get("status"), STATUSES),
        "phase": _enum(result.get("phase"), PHASES),
        "expected_count": len(names) if names is not None else NOT_RECORDED,
        "command_exit_code": _integer(result.get("command_exit_code"), -255, 255),
        "error_category": _error_category(result.get("error_type")),
        "reported_counts": {key: _integer(result.get(key)) for key in ("passed", "failed", "skipped")},
        "summary_counts": {key: _integer(summary.get(source)) for key, source in
            (("total", "totalTestCount"), ("passed", "passedTests"), ("failed", "failedTests"), ("skipped", "skippedTests"))},
        "selector_results": [{"selector_index": index, "result": methods.get(name, NOT_RECORDED)}
                             for index, name in enumerate(names or [])],
        "unexpected_method_count": unexpected, "failures": rows,
        "omitted_failure_count": omitted}


def _project_selection(value):
    """Revalidate saved public diagnostics; never forward an arbitrary object."""
    value = _record(value)
    if (type(value.get("schema")) is not int or value.get("schema") != 1
            or value.get("kind") != "SELECTION" or value.get("diagnostic_only") is not True):
        return NOT_RECORDED
    count = _integer(value.get("expected_count"), 1, MAX_SELECTORS)
    maximum = count - 1 if type(count) is int else -1
    methods, failures = [], []
    raw_methods = value.get("selector_results")
    if type(raw_methods) is list and len(raw_methods) <= MAX_SELECTORS:
        for item in raw_methods:
            item = _record(item)
            methods.append({"selector_index": _integer(item.get("selector_index"), 0, maximum),
                            "result": _enum(item.get("result"), METHOD_RESULTS)})
    raw_failures = value.get("failures")
    if type(raw_failures) is list:
        for item in raw_failures[:MAX_FAILURES]:
            item = _record(item)
            failures.append({"selector_index": _integer(item.get("selector_index"), 0, maximum),
                             "category": _enum(item.get("category"), FAILURE_CATEGORIES, "UNCLASSIFIED")})
    omitted = _integer(value.get("omitted_failure_count"))
    if type(raw_failures) is list and len(raw_failures) > MAX_FAILURES:
        omitted = _integer(omitted + len(raw_failures) - MAX_FAILURES) if type(omitted) is int else NOT_RECORDED
    return {"schema": 1, "kind": "SELECTION", "diagnostic_only": True,
        "reported_status": _enum(value.get("reported_status"), STATUSES),
        "phase": _enum(value.get("phase"), PHASES), "expected_count": count,
        "command_exit_code": _integer(value.get("command_exit_code"), -255, 255),
        "error_category": _enum(value.get("error_category"), ERROR_CATEGORIES),
        "reported_counts": {key: _integer(_record(value.get("reported_counts")).get(key))
                            for key in ("passed", "failed", "skipped")},
        "summary_counts": {key: _integer(_record(value.get("summary_counts")).get(key))
                           for key in ("total", "passed", "failed", "skipped")},
        "selector_results": methods,
        "unexpected_method_count": _integer(value.get("unexpected_method_count")),
        "failures": failures, "omitted_failure_count": omitted}


def execution_observation(receipt, lane):
    receipt = _record(receipt)
    change = _record(receipt.get("tracked_source_change"))
    statuses = _record(receipt.get("lane_statuses"))
    batch_lanes = _batch_lanes(lane)
    return {"schema": 1, "kind": "EXECUTION", "diagnostic_only": True,
        "lane": _enum(lane, LANES), "current_lane": _enum(receipt.get("current_lane"), batch_lanes),
        "reported_status": _enum(receipt.get("status"), STATUSES),
        "phase": _enum(receipt.get("phase"), PHASES),
        "error_category": _error_category(receipt.get("error_type")),
        "native_build_succeeded": _boolean(receipt.get("native_build_succeeded")),
        "tracked_source_changed": True if change else NOT_RECORDED,
        "source_change_stage": _enum(change.get("stage"), SOURCE_STAGES),
        "changed_path_count": _integer(change.get("changed_path_count")),
        "lane_statuses": [{"lane_index": index, "reported_status": _enum(statuses.get(name), STATUSES)}
                          for index, name in enumerate(batch_lanes)],
        "preparation": _project_selection(_record(receipt.get("preparation")).get("public_diagnostics")),
        "ui": _project_selection(_record(receipt.get("ui")).get("public_diagnostics"))}


def _project_execution(value):
    value = _record(value)
    if (type(value.get("schema")) is not int or value.get("schema") != 1
            or value.get("kind") != "EXECUTION" or value.get("diagnostic_only") is not True):
        return NOT_RECORDED
    statuses = {}
    batch_lanes = _batch_lanes(value.get("lane"))
    raw = value.get("lane_statuses")
    if type(raw) is list and len(raw) == len(batch_lanes):
        for index, item in enumerate(raw):
            item = _record(item)
            if type(item.get("lane_index")) is int and item["lane_index"] == index:
                statuses[batch_lanes[index]] = _enum(item.get("reported_status"), STATUSES)
    return {"schema": 1, "kind": "EXECUTION", "diagnostic_only": True,
        "lane": _enum(value.get("lane"), LANES), "current_lane": _enum(value.get("current_lane"), batch_lanes),
        "reported_status": _enum(value.get("reported_status"), STATUSES),
        "phase": _enum(value.get("phase"), PHASES),
        "error_category": _enum(value.get("error_category"), ERROR_CATEGORIES),
        "native_build_succeeded": _boolean(value.get("native_build_succeeded")),
        "tracked_source_changed": True if value.get("tracked_source_changed") is True else NOT_RECORDED,
        "source_change_stage": _enum(value.get("source_change_stage"), SOURCE_STAGES),
        "changed_path_count": _integer(value.get("changed_path_count")),
        "lane_statuses": [{"lane_index": index, "reported_status": _enum(statuses.get(name), STATUSES)}
                          for index, name in enumerate(batch_lanes)],
        "preparation": _project_selection(value.get("preparation")),
        "ui": _project_selection(value.get("ui"))}


def _emit(producer, projector, *args):
    # A broken serializer/output stream must not mask the runner's exception.
    # Interruptions are deliberately not caught: caller cancellation remains live.
    try:
        observation = projector(producer(*args))
        if type(observation) is not dict:
            return None
        payload = json.dumps(observation, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        if len(payload) > MAX_ANNOTATION:
            return None
        level = "notice" if observation["reported_status"] in {
            "PASS", "LANE_PASS_ACCEPTANCE_REVIEW_PENDING", "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING",
            "SMOKE_PASS_FULL_ACCEPTANCE_PENDING", "STARTUP_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING",
            "NATIVE_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING"} else "warning"
        payload = payload.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::" + level + " title=Pinkha UI diagnostic::" + payload, flush=True)
        return observation
    except Exception:
        return None


def emit_selection(result, summary=None):
    return _emit(selection_observation, _project_selection, result, summary)


def emit_execution(receipt, lane):
    return _emit(execution_observation, _project_execution, receipt, lane)
