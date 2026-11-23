"""Exact current-shared composition for the new tagged SDK continuation.

This module reads two original coherent controller outcomes as proof data.
It never imports their test module or re-executes an old control. The 300-file
original snapshot is an inventory; only its nine actually loaded source files
have the separately checked current-to-tested views below.
"""
import hashlib
import json

MANIFEST = "Tools/PinkhaSimulatorGate/sdk06-tagged-composition.json"
MANIFEST_SHA256 = "acdefbdbd9a5e10413ba7f7a7c7c0f3684a91e1b4d4851629cc0654948538879"
HISTORICAL_PATHS = frozenset((
    "Tools/PinkhaSimulatorGate/run_owned_single_lane.py",
    "Tools/PinkhaSimulatorGate/coherent_original_products.py",
    ".github/workflows/torah-inspector-ipados27.yml",
))
WORKFLOWS = frozenset((
    ".github/workflows/torah-inspector-ipados27.yml",
    ".github/workflows/pinkha-sdk06-tagged-continuation.yml",
))
PREFIX = "docs/validation/20261123-coherent-kernel-source-batch/"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def contract(root, read_regular):
    data, mode = read_regular(root, MANIFEST)
    require(digest(data) == MANIFEST_SHA256 and mode == "100644",
            "Unreviewed fixed current-shared composition")
    value = json.loads(data)
    require(value["schema"] == "sdk06-tagged-current-shared-composition-v1"
            and set(value["historical_inverses"]) == HISTORICAL_PATHS
            and set(value["executing_workflows"]) == WORKFLOWS
            and value["root_qualification"]["prefix"] == PREFIX
            and value["root_qualification"]["actual_loaded_count"] == 9,
            "Unknown current-shared composition boundary")
    return value


def inverse(data, before_sha256, after_sha256, hunks, relative):
    require(digest(data) == after_sha256, "Unadmitted current composition source: " + relative)
    recovered = data
    for hunk in reversed(hunks):
        before, after = hunk["before"].encode(), hunk["after"].encode()
        require(before != after and recovered.count(after) == 1,
                "Fixed composition inverse is missing or ambiguous: " + relative)
        recovered = recovered.replace(after, before, 1)
    require(digest(recovered) == before_sha256,
            "Composition inverse did not recover the whole tested file: " + relative)
    return recovered


def historical_bytes(relative, data, value):
    """Three exact views for old proof data; never an executable source override."""
    if relative not in HISTORICAL_PATHS:
        return data
    row = value["historical_inverses"][relative]
    return inverse(data, row["before_sha256"], row["after_sha256"], row["hunks"], relative)


def admit(root, read_regular):
    value = contract(root, read_regular)
    current, raw = {}, {}
    for relative, row in value["current_bound_inputs"].items():
        data, mode = read_regular(root, relative)
        require(digest(data) == row["sha256"] and len(data) == row["bytes"]
                and mode == row["git_mode"], "Fixed original composition input changed: " + relative)
        raw[relative] = data
        current[relative] = dict(sha256=digest(data), git_mode=mode)
    for relative, expected in value["executing_workflows"].items():
        data, mode = read_regular(root, relative)
        require(data and digest(data) == expected and mode == "100644",
                "The actual executable workflow differs from its independent pin")
        current[relative] = dict(sha256=digest(data), git_mode=mode)
    historical = {}
    for relative, row in value["historical_inverses"].items():
        data, mode = read_regular(root, relative)
        require(mode == "100644", "Composed source mode changed")
        recovered = historical_bytes(relative, data, value)
        historical[relative] = dict(actual_current_sha256=digest(data),
            historical_view_sha256=digest(recovered), kind=row["kind"])
        current[relative] = dict(sha256=digest(data), git_mode=mode)
    reference = value["root_qualification"]
    loaded = json.loads(raw[PREFIX + "attempt1/loaded-source-map.json"])
    source_before = raw[PREFIX + "attempt1/source-before.json"]
    require(source_before == raw[PREFIX + "attempt1/source-after.json"],
            "Original coherent source snapshots differ")
    snapshot = json.loads(source_before)
    require(len(snapshot) == reference["snapshot_source_count"] == 300
            and set(loaded) == set(reference["actual_loaded_sources"]) and len(loaded) == 9,
            "Original inventory and actual loaded closure were conflated")
    views = {}
    for relative, row in reference["actual_loaded_sources"].items():
        data, mode = read_regular(root, relative)
        require(mode == "100644", "Original loaded-source mode changed")
        recovered = inverse(data, row["tested_sha256"], row["current_sha256"], row["inverses"], relative)
        expected = row["tested_sha256"]
        require(loaded[relative]["sha256"] == loaded[relative]["gitSHA256"] == expected
                and loaded[relative]["matchesFrozenGit"] is True
                and snapshot[relative]["sha256"] == expected
                and snapshot[relative]["gitMode"] == mode,
                "Original actual imported source differs from its frozen source inventory")
        current[relative] = dict(sha256=digest(data), git_mode=mode)
        views[relative] = dict(actual_current_sha256=digest(data),
            original_loaded_sha256=digest(recovered), classification=row["classification"])
    qualification = json.loads(raw[PREFIX + "qualification.json"])
    result = json.loads(raw[PREFIX + "attempt1/result.json"])
    audit = json.loads(raw[PREFIX + "attempt1/audit.json"])
    review = json.loads(raw[PREFIX + "root-review.json"])
    events = json.loads(raw[PREFIX + "attempt1/events.json"])
    names = reference["actual_method_names"]
    require(len(names) == 2 and events == reference["original_events"]
            == qualification["actualNamedEvents"] == review["events"] == audit["actualNamedEvents"]
            and [(item["event"], item["method"]) for item in events]
            == [(kind, name) for name in names for kind in ("START", "PASS")],
            "Two exact original named coherent outcomes are required")
    # The full original log is pinned, including the diagnostic line followed
    # by a real standalone 'ok'. Do not synthesize or normalize a test outcome.
    require(raw[PREFIX + "attempt1/controls.log"].decode() == reference["original_log"],
            "Original named log or its actual following ok changed")
    require(result["passed"] is True and result["testsRun"] == 2
            and result["evidenceError"] is None and result["runnerError"] is None
            and all(result[name] == 0 for name in ("errors", "failures", "skips",
                "AppleMethodsExecuted", "newBuilds", "oldControllerMethodsExecuted"))
            and result["sourceUnchanged"] is True and result["sourceInputs"] == 300
            and result["sourceCommit"] == reference["source_commit"],
            "Original result does not qualify exactly two controller methods")
    require(qualification["status"] == "TWO_NEW_COHERENT_CONTROLLER_METHODS_PASS"
            and qualification["actualMethods"] == 2
            and qualification["sourceUnchanged"] is True and qualification["sourceInputs"] == 300
            and all(qualification[name] == 0 for name in ("errors", "failures", "skips",
                "AppleProductMethodsExecuted", "newBuilds", "oldControllerMethodsExecuted"))
            and review["status"] == "INDEPENDENT_ROOT_REVIEW_PASS"
            and review["allSourcePhysicalAndFrozenGitMatch"] is True
            and qualification["loadedRepositoryModules"] == result["loadedRepositoryModules"]
                == review["loadedRepositoryModules"] == loaded,
            "Original independent coherent source/outcome audit changed")
    for name, expected in qualification["originals"].items():
        require(digest(raw[PREFIX + "attempt1/" + name]) == expected,
                "Original coherent receipt linkage changed")
    command = json.loads(raw[PREFIX + "attempt1/owned-command-originals/new-coherent-command.command.json"])
    original = json.loads(raw[PREFIX + "attempt1/owned-command-originals/new-coherent-command.owned.command.json"])
    group = command["owned_group_quiescence"]
    kernel = group["kernel_group_observation"]
    require(command == review["actualOwnedCommand"] and command["status"] == "SUCCESS"
            and command["return_code"] == original["return_code"] == 0
            and command["controller_process_id"] == original["worker_pid"] == group["pgid"] == kernel["pgid"]
            and command["cwd"] == original["cwd"] and command["argv"] == original["argv"]
            and original["status"] == "COMPLETE" and group["status"] == "PASS"
            and group["absence_source"] == "KERNEL_ESRCH" and group["budget_seconds"] == 10
            and group["live_members"] == group["observations"] == 0
            and group["timeout_observations"] == []
            and kernel["operation"] == "os.killpg" and kernel["signal"] == 0
            and kernel["outcome"] == "ABSENT_ESRCH" and kernel["errno"] == 3
            and kernel["before_monotonic"] <= kernel["after_monotonic"] <= kernel["deadline_monotonic"],
            "Original owned-group absence or deadline evidence changed")
    data, mode = read_regular(root, MANIFEST)
    current[MANIFEST] = dict(sha256=digest(data), git_mode=mode)
    return dict(status="RETAINED_ORIGINAL_COHERENT_CONTROLLER_PROOF_ONLY",
        manifest_sha256=MANIFEST_SHA256, shared_origin=value["shared_origin"],
        actual_current_inputs=dict(sorted(current.items())),
        executing_workflows=value["executing_workflows"], historical_inverse_views=historical,
        original_coherent_methods=names, original_actual_loaded_source_views=views,
        original_source_inventory_count=300, original_actual_loaded_count=9,
        original_inventory_is_exercised_coverage=False,
        coherent_reader_caller_scope="STATIC_CALLER_BINDING_NOT_AN_ACTUAL_LOADED_METHOD_CLAIM",
        original_root_review_sha256=digest(raw[PREFIX + "root-review.json"]),
        old_controller_methods_executed_now=0, current_selector_qualified=False,
        workflow_view_executed=False, product_acceptance_claimed=False)
