"""Verify retained M17 evidence without rerunning Xcode, preparation or tests."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"
RUN = "44976915323"
HEAD = "0c183ed56c24ba3db34a6e11a52504b89efd9db0"
SOURCE = "813fbe79c1b325ee21a8c2be78bb86577f44bf6c"
LOCK_BLOB = "99a5b952aab40cb3d5ffe03153c9cf8c07ed341b"


def read(name):
    return json.loads((EVIDENCE / name).read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


archive = ROOT / "artifact-original.zip"
assert archive.stat().st_size == 313527
assert sha(archive.read_bytes()) == "d6a20ad46fdc0ca33d21bd310c0aed9b0b2777ee0f15b70210a04ac0b585ae81"
with zipfile.ZipFile(archive) as zipped:
    assert zipped.testzip() is None
    assert len(zipped.infolist()) == 61
    for entry in zipped.infolist():
        assert (EVIDENCE / entry.filename).read_bytes() == zipped.read(entry.filename)

report = read("RESOLUTION.json")
assert report["run_id"] == RUN and report["run_attempt"] == "1"
assert report["workflow_sha"] == HEAD and report["source"] == SOURCE
assert report["status"] == "ACTUAL_XCODE_STRICT_PACKAGE_GRAPH_ACCEPTED_NO_BUILD"
assert report["resolution_path"] == {
    "automatic_resolution_invocations": 0,
    "mode": "ORIGINAL_STRICT_RESOLVER_ACCEPTED",
    "strict_resolution_invocations": 1,
}
assert report["tests_executed"] == 0
assert report["application_or_framework_compilation_executed"] is False
assert report["native_acceptance"] == "NOT_RUN"

locks = ["Package.resolved.original", "Package.resolved.seed", "Package.resolved.xcode-output",
         "Package.resolved.last-observed-project", "Package.resolved.last-observed-workspace"]
lock_bytes = (EVIDENCE / locks[0]).read_bytes()
for name in locks:
    assert (EVIDENCE / name).read_bytes() == lock_bytes
lock = json.loads(lock_bytes)
assert lock["version"] == 2 and "originHash" not in lock
assert len(lock["pins"]) == 17
pins = {entry["identity"]: entry for entry in lock["pins"]}
assert len(pins) == 17
assert hashlib.sha1(b"blob " + str(len(lock_bytes)).encode() + b"\0" + lock_bytes).hexdigest() == LOCK_BLOB
assert sha(lock_bytes) == report["output_sha256"]

commands = {}
for path in sorted(EVIDENCE.glob("*.command.json")):
    label = path.name.removesuffix(".command.json")
    command = read(path.name)
    assert command["returncode"] == 0 and command["timed_out"] is False, label
    for stream in ["stdout", "stderr"]:
        assert sha((EVIDENCE / (label + "." + stream + ".log")).read_bytes()) == command[stream + "_sha256"], (label, stream)
    assert not set(command["argv"]) & {"build", "build-for-testing", "test", "test-without-building", "archive"}
    commands[label] = command
strict = commands["actual-strict-first"]
assert strict["argv"][:6] == ["xcodebuild", "-resolvePackageDependencies", "-workspace", "Maktabah.xcworkspace", "-scheme", "Maktabah-iOS"]
assert strict["argv"][-1] == "-onlyUsePackageVersionsFromResolvedFile"
assert strict["timeout_seconds"] == 1800
assert len([c for c in commands.values() if "-resolvePackageDependencies" in c["argv"]]) == 1
assert (EVIDENCE / "actual-strict-first.stderr.log").read_bytes() == b""
assert "resolved source packages:" in (EVIDENCE / "actual-strict-first.stdout.log").read_text()
assert (EVIDENCE / "xcode-version.stdout.log").read_text().strip() == "Xcode 27.0\nBuild version 27A266a"
assert (EVIDENCE / "sdk-version.stdout.log").read_text().strip() == "27.0"

checkouts = read("actual-package-checkouts.json")
assert checkouts["all_actual_checkout_files_tracked"] is True
assert checkouts["locked_but_not_materialized"] == []
assert set(checkouts["checkouts"]) == set(pins)
for name, checkout in checkouts["checkouts"].items():
    assert checkout["revision"] == pins[name]["state"]["revision"]
    assert len(checkout["package_manifest_sha256"]) == 64

before = read("source-before.json")
after = read("source-after.json")
attempt = read("source-after-attempt.json")
assert before["sha"] == after["sha"] == attempt["sha"] == SOURCE
assert before["tree"] == after["tree"] == attempt["tree"]
original_graph = read("graph-before-preparation.json")
prepared_graph = read("graph-prepared.json")
final_graph = read("graph-after.json")
assert prepared_graph == final_graph == after["actual_graph_inputs"] == attempt["actual_graph_inputs"]
assert set(original_graph) == set(prepared_graph)
assert [path for path in original_graph if original_graph[path] != prepared_graph[path]] == ["Maktabah.xcodeproj/project.pbxproj"]
assert after["tracked_changes"] == ["Maktabah.xcodeproj/project.pbxproj", "Source/PrivacyInfo.xcprivacy"]

workspace = read("workspace-graph-prepared.json")
assert workspace == read("workspace-graph-after.json")
assert (EVIDENCE / "workspace-graph-prepared.json").read_bytes() == (EVIDENCE / "workspace-graph-after.json").read_bytes()
assert workspace["project_references"] == ["group:Maktabah.xcodeproj", "group:Pods/Pods.xcodeproj"]
assert workspace["app_package_references"] == read("project-package-references-original.json")
assert workspace["pods_has_additional_swift_package_references"] is False
assert workspace["pods_package_graph"]["references"] == {}
assert all(not owner["packageReferences"] and not owner["packageProductDependencies"]
           for owner in workspace["pods_package_graph"]["owners"].values())
assert len(workspace["files"]) == 268
generated_project = (EVIDENCE / "original-preparation/generated-Maktabah-project.pbxproj").read_bytes()
assert sha(generated_project) == prepared_graph["Maktabah.xcodeproj/project.pbxproj"]["sha256"]

hanlin = read("hanlin-final.json")
assert hanlin["sha"] == "e00498e33f106cc43be0476ffa2e09329c8ca300"
assert hanlin["verified_files"] == len(hanlin["git_blobs"]) == 424
for name in ["original-preparation/hanlin-sdk-inputs.json", "original-preparation/hanlin-sdk-inputs-after.json"]:
    earlier = read(name)
    assert earlier["sha"] == hanlin["sha"]
    assert earlier["git_blobs"] == hanlin["git_blobs"]
    assert earlier["manifest_sha256"] == hanlin["manifest_sha256"]

preparation = read("original-preparation/preparation.json")
assert preparation["app_build_executed"] is False
privacy = preparation["generated_configuration"][0]
assert privacy["all_original_reasons_retained"] and privacy["all_other_declarations_unchanged"]
assert sha((EVIDENCE / "original-preparation/privacy-original.xcprivacy").read_bytes()) == privacy["original_sha256"]
assert sha((EVIDENCE / "original-preparation/privacy-generated.xcprivacy").read_bytes()) == privacy["compiled_sha256"]
for added in privacy["added_reasons"]:
    for witness in added["dependency_inputs"]:
        assert sha((EVIDENCE / "original-preparation" / witness["artifact_path"]).read_bytes()) == witness["sha256"]

source_receipt_path = ROOT / "COMMITTED_SOURCE_VERIFICATION.json"
source_receipt = json.loads(source_receipt_path.read_bytes())
assert source_receipt["status"] == "EXACT_IMMUTABLE_GIT_OBJECTS_MATCH_ARCHIVED_SOURCE_INPUTS"
assert source_receipt["source"] == SOURCE and source_receipt["tree"] == before["tree"]
assert source_receipt["verified_input_count"] == len(source_receipt["files"]) == 23
source_records = {row["path"]: {k: v for k, v in row.items() if k != "path"} for row in source_receipt["files"]}
assert all(source_records[name] == value for name, value in before["inputs"].items())
assert all(source_records[name] == value for name, value in original_graph.items())
result = {
    "status": "ORIGINAL_M17_STRICT_RESOLUTION_VERIFIED_NO_BUILD",
    "run_id": int(RUN), "attempt": 1, "workflow_sha": HEAD, "consumer_source": SOURCE,
    "artifact_id": 14736187053, "artifact_sha256": sha(archive.read_bytes()),
    "archive_members_verified": 61,
    "original_preparation_seconds": commands["original-workspace-preparation"]["elapsed_seconds"],
    "strict_resolver_seconds": strict["elapsed_seconds"], "strict_resolver_exit": 0,
    "strict_invocations": 1, "automatic_invocations": 0,
    "original_pin_objects_preserved": 17, "actual_checkout_revisions_verified": 17,
    "five_lock_copies_byte_identical": True, "lock_git_blob": LOCK_BLOB,
    "lock_sha256": sha(lock_bytes), "lock_version": 2, "originHash": None,
    "package_lock_change_required": False,
    "workspace_input_records_unchanged": 268,
    "app_package_owner_records_unchanged": len(workspace["app_package_references"]["owners"]),
    "app_package_reference_records_unchanged": len(workspace["app_package_references"]["references"]),
    "pods_swift_references_and_attachments_empty": True,
    "tracked_graph_records_unchanged_after_preparation": len(final_graph),
    "source_head_and_tree_unchanged": True,
    "hanlin_exact_files_before_after": 424,
    "source_build_inputs_git_verification": {
        "status": source_receipt["status"], "verified_input_count": 23,
        "receipt_sha256": sha(source_receipt_path.read_bytes()),
    },
    "tests_reexecuted": 0, "application_builds": 0, "native_acceptance": "NOT_RUN",
    "reuse_scope": "Exact813f dependency graph and original preparation closure only; newer source requires explicit input-identity comparison",
}
(ROOT / "INDEPENDENT_ARTIFACT_AUDIT.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
