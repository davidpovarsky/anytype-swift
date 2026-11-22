"""Exact additive native CAS source and selected-control evidence contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IMAGE = "golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
NATIVE_RUN = "45026227924"
PROOF = "docs/validation/20261122-coherent-heart-native-pass/original"
RETAINED = "retained-contract"
CONTRACT_LOG = "8b3b3a2a82240bae0c0833ddf7f5540e2f0a18185220017c51a58c7495c31d21"
CONTRACT_SOURCES = {
    "contract.go": "f15e9c4900e350605e9d71911adf50710e775b58aaa811d02be36e80976c52a8",
    "contract_test.go": "f72f5cd435d10efddc4c9deef0b4a8c7f689ee5aede70c64ee3a03a537c06179",
}
CONTRACT_METHODS = {
    "TestSemanticAnchorCaptureComparesEveryNativeMarkAndPreservesBytes",
    "TestSemanticAnchorCaptureRejectsUTF16AndIdentityAmbiguity",
    "TestSemanticAnchorCaptureRefusesExistingLinksAndDuplicateIdentity",
    "TestSemanticAnchorPostApplyComparisonKeepsEveryMarkAndDuplicate",
    "TestSemanticAnchorCaptureBoundsMalformedNativeMarks",
}
SOURCE_PATHS = frozenset({
    "pkg/lib/pinkha/semanticanchor/contract.go", "pkg/lib/pinkha/semanticanchor/contract_test.go",
    "core/block/editor/torahopsobject/semantic_anchor_lease.go", "core/block/editor/torahopsobject/semantic_anchor_lease_test.go",
    "core/block/editor/stext/pinkha_semantic_anchor.go", "core/block/editor/stext/pinkha_semantic_anchor_test.go",
    "core/block/editor/pinkha_semantic_anchor.go", "core/pinkha_semantic_anchor.go", "core/pinkha_semantic_anchor_test.go",
})
# Exact expected leaf cases. A parent with child cases is also required to run
# and pass; an unselected prior method or a skipped child is always a failure.
CASES = {
    "core/block/editor/stext": {
        "TestPinkhaSemanticAnchorTextCASRefusesPendingAndAllMarkConflicts": (
            "pending-text", "changed-text", "changed-unselected-mark", "added-mark", "new-state-hook-changes-text"),
        "TestPinkhaSemanticAnchorTextCASRequiresPostApplyStateAndNativeWitness": (
            "silent-noop", "error-before-mutation", "error-after-mutation", "missing-change-id", "post-mark-mutation",
            "native-witness-error", "authority-lost-after-apply"),
        "TestPinkhaSemanticAnchorTextCASPreservesMarksAndNormalApplyFlags": (),
        "TestPinkhaSemanticAnchorTextPublicEntryRequiresNativeLease": (),
    },
    "core/block/editor/torahopsobject": {
        "TestPinkhaSemanticAnchorLeaseRetainsNativeLocksAndOneCallStoredWitness": (),
        "TestPinkhaSemanticAnchorLeaseRejectsStaleDeletedOrphanAndDuplicateTargets": (
            "stale-cache", "native-deleted", "signed-settings-deleted", "orphan-block", "missing-block", "duplicate-marker"),
        "TestPinkhaSemanticAnchorLeaseRechecksSignedWriteAuthorityBeforeAndAfterCommit": (
            "before-native-write", "after-native-write"),
        "TestPinkhaSemanticAnchorLeaseRechecksHookGraphAndCancellation": (
            "duplicate-other-block", "stale-cache-after-borrow", "context-cancelled"),
    },
    "core": {"TestPinkhaSemanticAnchorNativeEntryRejectsInvalidOrCancelledBeforeAccount": ()},
}
LIMITS = dict(full_page_apply_acceptance="NOT_RUN", account_lifecycle_acceptance="NOT_RUN",
              wire_acceptance="NOT_RUN", apple_acceptance="NOT_RUN", editor02_acceptance="NOT_COMPLETE",
              atomic_acl_storage_transaction="NOT_CLAIMED", app_capability="OFF", old_test_methods_executed=0)


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected regular source/evidence: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2,
            "Missing/unsafe bounded JSON input")
    def unique(entries):
        value = {}
        for key, item in entries:
            require(key not in value, "Duplicate JSON field")
            value[key] = item
        return value
    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf8")
    temporary.replace(path)


def source_manifest():
    value = load(HERE / "native-source.json")
    require(value.get("schemaVersion") == 1 and value.get("base_heart_sha") == HEART
            and value.get("qualified_native_run") == NATIVE_RUN and value.get("source_kind") == "ADDITIVE_CANDIDATE_ONLY"
            and value.get("qualified_patch_sha256") == "2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00"
            and value.get("qualified_inventory_sha256") == "05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0"
            and value.get("qualified_native_files_unchanged") == 139 and value.get("additive_source_count") == 9
            and value.get("generated_wire_changed") is False
            and value.get("app_capability") == "OFF" and set(value.get("files", {})) == SOURCE_PATHS,
            "Another candidate or broader native source delta is not allowed")
    files = value["files"]
    observed = {path.relative_to(HERE / "native").as_posix(): digest(path)
                for path in (HERE / "native").rglob("*") if path.is_file() or path.is_symlink()}
    require(observed == files, "Candidate native file inventory differs")
    for name in files:
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts and "\\" not in name,
                "Unsafe candidate source path")
    return files


def outcomes(log, package, cases):
    require(log.is_file() and not log.is_symlink() and 0 < log.stat().st_size <= 32 * 1024**2,
            "Missing/unbounded original Go control output")
    expected = set(cases)
    leaves = set()
    for parent, children in cases.items():
        if children:
            expected.update(parent + "/" + child for child in children)
            leaves.update(parent + "/" + child for child in children)
        else:
            leaves.add(parent)
    runs, finished, package_pass = set(), set(), 0
    for line in log.read_text(encoding="utf8").splitlines():
        event = json.loads(line)
        require(event.get("Package") == package and event.get("Action") not in ("fail", "skip"),
                "Wrong package, failure or skipped native control")
        name, action = event.get("Test"), event.get("Action")
        if name is not None:
            require(name in expected, "An unselected prior or unknown test executed: " + name)
            if action == "run":
                require(name not in runs, "Native control was executed twice")
                runs.add(name)
            elif action == "pass":
                require(name in runs and name not in finished, "Missing/duplicate native control execution")
                finished.add(name)
        elif action == "pass":
            package_pass += 1
    require(runs == finished == expected and package_pass == 1, "Missing successful named native cases")
    return dict(top_level=len(cases), terminal=len(leaves), failed=0, skipped=0, methods=sorted(cases),
                terminals=sorted(leaves), sha256=digest(log))


def retained_contract():
    folder = HERE / RETAINED
    receipt = load(folder / "semantic-contract-receipt.json")
    log = folder / "semantic-contract-controls.jsonl"
    require(receipt.get("schema") == "pinkha-semantic-anchor-native-contract-v1"
            and receipt.get("go_version") == "go version go1.26.5 linux/amd64" and receipt.get("exit_code") == 0
            and set(receipt.get("passed", [])) == CONTRACT_METHODS and len(receipt["passed"]) == 5
            and receipt.get("failed") == [] and receipt.get("native_apply_executed") is False
            and type(receipt.get("old_tests_executed")) is int and receipt["old_tests_executed"] == 0
            and receipt.get("source_sha256") == CONTRACT_SOURCES and digest(log) == receipt.get("log_sha256") == CONTRACT_LOG,
            "Original five pure-contract controls changed or overstate their scope")
    for name, expected in CONTRACT_SOURCES.items():
        require(digest(HERE / "native/pkg/lib/pinkha/semanticanchor" / name) == expected,
                "Previously executed pure contract source changed")
    checked = outcomes(log, "command-line-arguments", {name: () for name in CONTRACT_METHODS})
    return dict(status="RETAINED_FIVE_PURE_CONTRACT_CONTROLS", receipt_sha256=digest(folder / "semantic-contract-receipt.json"),
                original_log_sha256=CONTRACT_LOG, original_source_sha256=CONTRACT_SOURCES,
                methods=checked["methods"], methods_executed_again=0, native_apply_executed=False)
