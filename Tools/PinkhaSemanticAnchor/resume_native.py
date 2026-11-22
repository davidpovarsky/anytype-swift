"""Retain exact passing scopes from failed native CAS run 45050652738."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile

import contract

PROOF_REL = "docs/validation/20261122-semantic-anchor-native-witness-repair"
ORIGINAL_RUN = "45050652738"
ORIGINAL_COMMIT = "4e76dba6f6ff714e3d25e382013495a11ac9267a"
ORIGINAL_ARTIFACT = 14765710346
ORIGINAL_ZIP_SHA = "cfb8bb71b4f35ea8fa057848d6d74b283114580a16009277b7cd6127ef427a30"
OLD_MANIFEST_SHA = "3e85e4b8ebe66c03e0ff95c45f55fc01d2e77fe1f14ad7895c72957b0f97af77"
NEW_MANIFEST_SHA = "51c3b76b0ff6cc737c7a4660fa87c7314f568bdf842c1ab8e568cbbab25a916a"
LEASE = "core/block/editor/torahopsobject"
STEXT = "core/block/editor/stext"
FAILED_METHOD = "TestPinkhaSemanticAnchorLeaseRetainsNativeLocksAndOneCallStoredWitness"
CORE_METHOD = "TestPinkhaSemanticAnchorNativeEntryRejectsInvalidOrCancelledBeforeAccount"
NATIVE_CHANGES = {
    LEASE + "/semantic_anchor_lease.go": (
        "2d8f45987436eee782067d558ac9afe4ca26c6296f5d3e9cbecc07f0fb7caa8b",
        "598e2fc9cd1173414f6e2afc1cd54672b7ec6fe72d1c4eda9a9687949677b814"),
    LEASE + "/semantic_anchor_lease_test.go": (
        "374d8f56756a55f98ec402eae9b0f1bc11ba6ca3cdc99b85ef6190c5292fa784",
        "6f41ff861de0f7973fe62f0e05c5c12bd387bf1630839ce6981fabdecfb4f306"),
}
RETAINED_CASES = {
    STEXT: contract.CASES[STEXT],
    LEASE: {name: children for name, children in contract.CASES[LEASE].items() if name != FAILED_METHOD},
}
SELECTED_CASES = {LEASE: {FAILED_METHOD: ()}, "core": {CORE_METHOD: ()}}


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def function_bytes(source, name):
    """Bounded declaration extraction, respecting Go strings and comments."""
    matches = list(re.finditer(rb"^func " + name.encode() + rb"\(", source, re.MULTILINE))
    contract.require(len(matches) == 1, "Expected one reviewed Go declaration: " + name)
    start = matches[0].start()
    opening = source.index(b"{", matches[0].end())
    depth, index, state = 0, opening, "code"
    while index < len(source):
        char, pair = source[index:index + 1], source[index:index + 2]
        if state in ('"', "'"):
            if char == b"\\":
                index += 2
                continue
            if char == state.encode():
                state = "code"
        elif state == "`":
            if char == b"`":
                state = "code"
        elif state == "line":
            if char == b"\n":
                state = "code"
        elif state == "block":
            if pair == b"*/":
                state = "code"
                index += 2
                continue
        elif pair in (b"//", b"/*"):
            state = "line" if pair == b"//" else "block"
            index += 2
            continue
        elif char in (b'"', b"'", b"`"):
            state = char.decode()
        elif char == b"{":
            depth += 1
        elif char == b"}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise ValueError("Unterminated reviewed Go declaration")


def reviewed_native_sources():
    proof = contract.ROOT / PROOF_REL
    sources = {}
    for name, (before, after) in NATIVE_CHANGES.items():
        original = proof / ("original-" + PurePosixPath(name).name)
        current = contract.HERE / "native" / name
        contract.require(contract.digest(original) == before and contract.digest(current) == after,
                         "Another native witness repair is not reviewed")
        sources[name] = (original.read_bytes(), current.read_bytes())
    original, current = sources[LEASE + "/semantic_anchor_lease.go"]
    marker = b"\nfunc VerifySemanticAnchorNativeChange("
    contract.require(original.split(marker)[0] == current.split(marker)[0],
                     "Capture, lifetime, graph or borrow declarations changed")
    original_witness = function_bytes(original, "VerifySemanticAnchorNativeChange")
    current_witness = function_bytes(current, "VerifySemanticAnchorNativeChange")
    unchanged_prefix = original_witness.split(b"\n\tif !semanticanchor.ValidIdentity", 1)[0]
    contract.require(unchanged_prefix == current_witness.split(b"\n\tstorage := tree.Storage()", 1)[0],
                     "The retained authority-denial path changed")
    original, current = sources[LEASE + "/semantic_anchor_lease_test.go"]
    marker = b"\nfunc " + FAILED_METHOD.encode() + b"("
    contract.require(original.split(marker)[0] == current.split(marker)[0],
                     "Original native fixture, imports or cache adapters changed")
    declarations = {}
    for name in set(RETAINED_CASES[LEASE]) | {"semanticApplyACL", "semanticDowngradeOwner"}:
        before, after = function_bytes(original, name), function_bytes(current, name)
        contract.require(before == after, "A retained native test/dependency changed: " + name)
        declarations[name] = digest_bytes(after)
    # Only the originally failed method calls the added controlled storage
    # wrappers. Existing named methods and subcase identities remain exactly9/27.
    observed = re.findall(rb"^func (Test\w+)\(t \*testing.T\)", current, re.MULTILINE)
    contract.require(set(name.decode() for name in observed) == set(contract.CASES[LEASE])
                     and len(observed) == len(contract.CASES[LEASE]), "Unexpected native method addition")
    contract.require(contract.digest(contract.HERE / "native-source.json") == NEW_MANIFEST_SHA,
                     "Another native candidate inventory is not reviewed")
    return dict(native_changes={name: {"before_sha256": old, "after_sha256": new}
                                for name, (old, new) in NATIVE_CHANGES.items()},
                unchanged_lease_declarations=declarations,
                unchanged_witness_pre_authority_prefix_sha256=digest_bytes(unchanged_prefix),
                retained_path_scope="stext uses its unchanged controlled witness; lease denial paths exit before changed storage checks",
                full_page_apply_acceptance="NOT_RUN")


def reviewed_controller_inputs(before, current):
    changes = {"native/" + name: pair for name, pair in NATIVE_CHANGES.items()} | {
        "native-source.json": (OLD_MANIFEST_SHA, NEW_MANIFEST_SHA)}
    contract.require(set(before) == set(current), "Original controller dependency set changed")
    for name in before:
        expected = changes.get(name)
        contract.require((before[name], current[name]) == expected if expected else before[name] == current[name],
                         "Unreviewed controller input changed: " + name)
    review = reviewed_native_sources()
    return dict(status="RETAINED_UNCHANGED_CONTROLLER_LOGIC_WITH_EXACT_REVIEWED_NATIVE_INPUT_REPAIR",
                changed_input_hashes={name: {"before_sha256": old, "after_sha256": new}
                                     for name, (old, new) in changes.items()}, source_review=review,
                controller_methods_rerun=0)


def original_archive():
    path = contract.ROOT / PROOF_REL / "original-evidence.zip"
    contract.require(contract.digest(path) == ORIGINAL_ZIP_SHA and path.stat().st_size == 56906,
                     "Original failed native artifact changed")
    entries = {}
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            name, relative = item.filename, PurePosixPath(item.filename)
            contract.require(not item.is_dir() and not relative.is_absolute() and ".." not in relative.parts
                             and "\\" not in name and name not in entries and str(relative) == name
                             and not stat.S_ISLNK(item.external_attr >> 16) and item.file_size <= 2 * 1024**2,
                             "Unsafe or repeated original evidence entry")
            entries[name] = archive.read(item)
    contract.require(len(entries) == 27 and "execute-core.log" not in entries,
                     "Another original native execution scope is not admitted")
    return entries


def validate_run(value):
    contract.require(str(value.get("id")) == ORIGINAL_RUN and value.get("head_sha") == ORIGINAL_COMMIT
                     and value.get("status") == "completed" and value.get("conclusion") == "failure"
                     and value.get("run_attempt") == 1 and value.get("event") == "workflow_dispatch"
                     and value.get("head_branch") == "codex/chatgpt-wave15-shared-20261121"
                     and value.get("path") == ".github/workflows/torah-inspector-ipados27.yml"
                     and value.get("repository", {}).get("full_name") == "davidpovarsky/anytype-swift"
                     and value.get("head_repository", {}).get("full_name") == "davidpovarsky/anytype-swift",
                     "Wrong original failed native producer run")


def partial_lease_outcome(data):
    cases = contract.CASES[LEASE]
    expected = set(cases) | {parent + "/" + child for parent, children in cases.items() for child in children}
    runs, passes, failures, package_failures = set(), set(), set(), 0
    for line in data.decode().splitlines():
        event = json.loads(line)
        name, action = event.get("Test"), event.get("Action")
        contract.require(event.get("Package") == "github.com/anyproto/anytype-heart/" + LEASE
                         and action in {"start", "run", "output", "pass", "fail"},
                         "Unknown, skipped or foreign original native event")
        if name is None:
            contract.require(action != "pass", "Original lease package was not wholly successful")
            package_failures += int(action == "fail")
            continue
        contract.require(name in expected, "Unselected original native method")
        if action == "run":
            contract.require(name not in runs, "Repeated original native method")
            runs.add(name)
        elif action in {"pass", "fail"}:
            contract.require(name in runs and name not in passes | failures, "Missing/repeated original outcome")
            (passes if action == "pass" else failures).add(name)
    contract.require(runs == expected and passes == expected - {FAILED_METHOD}
                     and failures == {FAILED_METHOD} and package_failures == 1,
                     "Original package has another failed/missing scope")
    retained = RETAINED_CASES[LEASE]
    leaves = sorted(parent + "/" + child for parent, children in retained.items() for child in children)
    return dict(top_level=3, terminal=11, failed=0, skipped=0, methods=sorted(retained), terminals=leaves,
                sha256=digest_bytes(data), original_package_status="FAIL_ONE_EXCLUDED_METHOD",
                excluded_failed_method=FAILED_METHOD, original_run_id=ORIGINAL_RUN, methods_executed_again=0)


def retain(run_metadata, qualified_native139, additions, evidence):
    validate_run(run_metadata)
    review = reviewed_native_sources()
    entries = original_archive()
    original = json.loads(entries["receipt.json"])
    before = json.loads(entries["candidate-source-before.json"])
    source_after_stext = json.loads(entries["source-after-stext.json"])
    original_additions = json.loads(entries["candidate-additions.json"])
    contract.require(original.get("status") == "FAIL" and original.get("run_id") == ORIGINAL_RUN
                     and original.get("run_attempt") == "1" and original.get("app_sha") == ORIGINAL_COMMIT
                     and original.get("error") == "Native command failed: execute-torahopsobject.log"
                     and original.get("old_test_methods_executed") == 0 and original.get("app_capability") == "OFF",
                     "Wrong original native failure")
    contract.require(json.loads(entries["qualified139-source-before.json"]) == qualified_native139
                     and len(qualified_native139) == 139 and before == source_after_stext
                     and before == qualified_native139 | original_additions["files"]
                     and digest_bytes(entries["candidate-additions.json"]) == OLD_MANIFEST_SHA,
                     "Original signed139/native candidate provenance changed")
    contract.require(set(additions) == set(original_additions["files"]) == contract.SOURCE_PATHS,
                     "A broader native candidate cannot retain these scopes")
    for name, old in original_additions["files"].items():
        pair = NATIVE_CHANGES.get(name)
        contract.require((old, additions[name]) == pair if pair else additions[name] == old,
                         "A native dependency outside the reviewed witness repair changed")
    commands = {entry["name"]: entry for entry in original["commands"]}
    for label in ("stext", "torahopsobject", "core"):
        contract.require(commands["compile-" + label]["status"] == "PASS_EXIT_0",
                         "Original packages did not all compile")
    for label in ("stext", "torahopsobject"):
        entry = commands["execute-" + label]
        contract.require(entry["log_sha256"] == digest_bytes(entries["execute-" + label + ".log"])
                         and entry["status"] == ("PASS_EXIT_0" if label == "stext" else "FAIL"),
                         "Original selected execution/log differs")
    contract.require("execute-core" not in commands, "Core method was already executed")
    target = evidence / "retained-native-original"
    contract.require(not target.exists(), "Fresh original-native evidence destination required")
    target.mkdir(parents=True)
    for name, data in entries.items():
        output = target / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
    shutil.copyfile(contract.ROOT / PROOF_REL / "original-evidence.zip", evidence / "original-native-component-evidence.zip")
    st = contract.outcomes(target / "execute-stext.log", "github.com/anyproto/anytype-heart/" + STEXT, contract.CASES[STEXT])
    contract.require(st == original["qualified_partial_results"][STEXT]
                     and json.loads(entries["qualified-partial-results.json"]) == {STEXT: st},
                     "Original qualified component receipt differs")
    st.update(original_run_id=ORIGINAL_RUN, original_package_status="PASS", methods_executed_again=0)
    results = {STEXT: st, LEASE: partial_lease_outcome(entries["execute-torahopsobject.log"])}
    value = dict(status="RETAINED_SEVEN_NATIVE_METHODS_25_TERMINAL_CASES", original_run_id=ORIGINAL_RUN,
                 original_commit=ORIGINAL_COMMIT, original_artifact_id=ORIGINAL_ARTIFACT,
                 original_artifact_zip_sha256=ORIGINAL_ZIP_SHA, retained_methods=7, retained_terminal_cases=25,
                 retained_methods_executed_again=0, original_all_three_packages_compiled=True,
                 original_binary_hashes=original["built_control_binaries"], original_source_after_stext_sha256=source_after_stext,
                 original_lease_post_execution_source_guard="NOT_REACHED_AFTER_FAILED_PACKAGE",
                 source_bound_execution_basis="All148 source hashes checked after each compile; exact named original binary executions and unchanged reviewed declaration paths",
                 current_source_review=review, results=results,
                 remaining_selection=SELECTED_CASES, full_page_apply_acceptance="NOT_RUN")
    contract.save(evidence / "retained-native-components.json", value)
    return value


def combine(retained, executed):
    contract.require(not set(retained["methods"]) & set(executed["methods"])
                     and not set(retained["terminals"]) & set(executed["terminals"]),
                     "A previously passed native scope was executed again")
    return dict(top_level=retained["top_level"] + executed["top_level"], terminal=retained["terminal"] + executed["terminal"],
                failed=0, skipped=0, methods=sorted(retained["methods"] + executed["methods"]),
                terminals=sorted(retained["terminals"] + executed["terminals"]),
                retained_original=retained, executed_current=executed)
