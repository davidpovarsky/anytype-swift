"""Read-only source/evidence comparison. No resolver, compiler, tests, or Git."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / "m17_resolution_44976915323"
BASE = "813fbe79c1b325ee21a8c2be78bb86577f44bf6c"
APP = "385ee84a8acb3fbc3c013c0977417b61fd3d8a17"
META = "46a185242b28b71d4b6d253747f2b8d46e4189a0"


def read(path):
    return json.loads(path.read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def content_identity(row):
    return {key: row[key] for key in ("mode", "type", "sha", "size") if key in row}


trees = {}
for label, commit in (("baseline", BASE), ("application", APP), ("metadata", META)):
    result = read(ROOT / "github" / (label + "-tree.json"))
    assert result["sha"] == commit and result["truncated"] is False
    rows = {row["path"]: row for row in result["tree"]}
    assert len(rows) == len(result["tree"])
    trees[label] = rows

retrieved = []
for row in read(ROOT / "github/BLOB_RETRIEVALS.json"):
    suffix = ".pbxproj" if row["label"].startswith("project-") else ".json" if row["label"].startswith("inputs-") else ".py"
    path = ROOT / "source" / (row["label"] + suffix)
    data = path.read_bytes()
    assert blob(data) == row["git_blob"]
    retrieved.append(row | {"bytes": len(data), "sha256": sha(data), "local_path": str(path.relative_to(ROOT))})

expected = read(OLD / "expected-git-inputs.json")
assert expected["source"] == BASE
input_comparison = []
for path, original in expected["inputs"].items():
    old, current, metadata = (trees[label][path] for label in ("baseline", "application", "metadata"))
    assert old["sha"] == original["git_blob"] and old["size"] == original["bytes"]
    input_comparison.append({"path": path, "baseline_git_blob": old["sha"],
                             "application_git_blob": current["sha"], "metadata_git_blob": metadata["sha"],
                             "application_identical": content_identity(old) == content_identity(current),
                             "metadata_identical": content_identity(old) == content_identity(metadata)})
changed = [row["path"] for row in input_comparison if not row["application_identical"]]
assert changed == ["Maktabah.xcodeproj/project.pbxproj", "Scripts/CI/hq-stage2-focused-apple.inputs.json"]

old_project = (ROOT / "source/project-baseline.pbxproj").read_bytes()
new_project = (ROOT / "source/project-application.pbxproj").read_bytes()
lines = list(difflib.unified_diff(old_project.decode().splitlines(True), new_project.decode().splitlines(True)))
added = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
removed = [line for line in lines if line.startswith("-") and not line.startswith("---")]
assert len(added) == 8 and not removed and all("AnnotationCloudImportIdentity.swift" in line for line in added)
assert new_project.decode().splitlines(True) != old_project.decode().splitlines(True)
assert "".join(line for line in new_project.decode().splitlines(True) if line not in added).encode() == old_project

section_results = []
for name in ("XCLocalSwiftPackageReference", "XCRemoteSwiftPackageReference", "XCSwiftPackageProductDependency",
             "PBXProject", "PBXNativeTarget", "XCBuildConfiguration", "XCConfigurationList"):
    expression = rb"/\* Begin " + name.encode() + rb" section \*/.*?/\* End " + name.encode() + rb" section \*/"
    old_sections = re.findall(expression, old_project, re.S)
    new_sections = re.findall(expression, new_project, re.S)
    assert len(old_sections) == len(new_sections) == 1 and old_sections == new_sections
    section_results.append({"section": name, "bytes": len(old_sections[0]), "sha256": sha(old_sections[0]),
                            "entire_section_bytes_identical": True})
package_graph = read(OLD / "evidence/project-package-references-original.json")
assert len(package_graph["references"]) == 36 and len(package_graph["owners"]) == 7
assert all(row["isa"] in ("PBXProject", "PBXNativeTarget") for row in package_graph["owners"].values())

manifest_membership = {}
for label, rows in trees.items():
    manifest_membership[label] = {path: content_identity(row) for path, row in rows.items()
                                  if path.startswith(("Source/", "Vendor/")) and
                                  path.endswith(("/Package.swift", "/Package.resolved"))}
assert manifest_membership["baseline"] == manifest_membership["application"] == manifest_membership["metadata"]
local_paths = sorted(row["relativePath"] for row in package_graph["references"].values()
                     if row["isa"] == "XCLocalSwiftPackageReference")
assert len(local_paths) == 7
local_package_trees = []
local_package_source_changes = []
for path in local_paths:
    if path.startswith("Vendor/HanlinSDK/"):
        continue
    identities = [content_identity(trees[label][path]) for label in trees]
    assert identities[1] == identities[2]
    members = [{name: content_identity(row) for name, row in trees[label].items()
                if name.startswith(path + "/") and row["type"] != "tree"}
               for label in ("baseline", "application")]
    assert set(members[0]) == set(members[1])
    for name in sorted(members[0]):
        if members[0][name] != members[1][name]:
            local_package_source_changes.append({"path": name, "baseline": members[0][name], "application": members[1][name]})
    local_package_trees.append({"path": path, "baseline_tree": trees["baseline"][path]["sha"],
                               "application_tree": trees["application"][path]["sha"],
                               "entire_tree_identical": identities[0] == identities[1],
                               "file_membership_identical": True})
assert len(local_package_source_changes) == 1
assert local_package_source_changes[0]["path"] == "Source/ChavrusaText/Dependencies/CommandPalette/Sources/CommandPalette/Views/CommandPaletteView.swift"
palette_old = (ROOT / "source/command-palette-baseline.swift").read_bytes()
palette_new = (ROOT / "source/command-palette-application.swift").read_bytes()
assert blob(palette_old) == local_package_source_changes[0]["baseline"]["sha"]
assert blob(palette_new) == local_package_source_changes[0]["application"]["sha"]
palette_diff = "".join(difflib.unified_diff(palette_old.decode().splitlines(True), palette_new.decode().splitlines(True),
                                         "CommandPaletteView.swift@813f", "CommandPaletteView.swift@385ee"))
(ROOT / "source/command-palette-source.diff").write_text(palette_diff)

preparation_paths = [".gitmodules", "Podfile", "Source/GoogleService-Info.plist", "Source/iOS-Info.plist",
                     "Source/PrivacyInfo.xcprivacy", "Scripts/CI/hq-stage2-focused-apple.py",
                     "Scripts/CI/prepare-hanlin-sdk.py", "Scripts/CI/prepare-pinned-sharp-libvips.py",
                     "Vendor", "Vendor/SefariaMobile", "Vendor/SefariaMobile/Upstream", "Vendor/HanlinSDK"]
preparation_inputs = []
for path in preparation_paths:
    identities = [content_identity(trees[label][path]) for label in trees]
    assert identities[0] == identities[1] == identities[2]
    preparation_inputs.append({"path": path, **identities[0], "identical_at_all_three_commits": True})
assert all("Podfile.lock" not in rows for rows in trees.values())

configs = {label: read(ROOT / "source" / ("inputs-" + label + ".json"))
           for label in ("baseline", "application", "metadata")}
driver = (ROOT / "source/preparation-driver.py").read_text()
syntax = ast.parse(driver)
preparation_functions = ["prepare_original_hanlin", "prepare_react_sources", "install_real_pods", "audit_generated_privacy"]
function_records = []
config_keys = set()
for name in preparation_functions:
    node = next(node for node in syntax.body if isinstance(node, ast.FunctionDef) and node.name == name)
    segment = ast.get_source_segment(driver, node).encode()
    keys = {node.slice.value for node in ast.walk(node)
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "config"
            and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)}
    config_keys |= keys
    function_records.append({"name": name, "bytes": len(segment), "sha256": sha(segment), "config_keys": sorted(keys)})
assert config_keys == {"hanlin_gitlink", "sefaria_gitlink"}
for key in config_keys:
    assert len({config[key] for config in configs.values()}) == 1
config_diff_keys = {key for key in configs["baseline"] if configs["baseline"][key] != configs["metadata"][key]}
assert config_diff_keys == {"application_source_sha", "application_trees", "otzaria_test_additions_sha256"}
assert configs["metadata"]["application_source_sha"] == APP
for path, digest in configs["metadata"]["application_trees"].items():
    assert trees["application"][path]["sha"] == trees["metadata"][path]["sha"] == digest

hanlin = read(OLD / "evidence/original-preparation/hanlin-sdk-inputs.json")
assert hanlin == read(OLD / "evidence/original-preparation/hanlin-sdk-inputs-after.json") == read(OLD / "evidence/hanlin-final.json")
actual_hanlin = read(ROOT / "github/hanlin-package-tree.json")
assert actual_hanlin["requested_sha"] == configs["metadata"]["hanlin_gitlink"] == hanlin["sha"]
assert actual_hanlin["complete_response_truncated"] is False
hanlin_blobs = {row["path"]: row["sha"] for row in actual_hanlin["tree"] if row["type"] == "blob"}
assert hanlin_blobs == hanlin["git_blobs"] and len(hanlin_blobs) == hanlin["verified_files"] == 424

lock = (OLD / "evidence/Package.resolved.original").read_bytes()
lock_path = "Maktabah.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
assert all(trees[label][lock_path]["sha"] == blob(lock) for label in trees)
pins = read(OLD / "evidence/Package.resolved.original")
assert pins["version"] == 2 and len(pins["pins"]) == 17
for name in ("Package.resolved.xcode-output", "Package.resolved.seed", "Package.resolved.last-observed-project", "Package.resolved.last-observed-workspace"):
    assert (OLD / "evidence" / name).read_bytes() == lock
resolution = read(OLD / "evidence/RESOLUTION.json")
assert resolution["status"] == "ACTUAL_XCODE_STRICT_PACKAGE_GRAPH_ACCEPTED_NO_BUILD" and resolution["source"] == BASE
before_workspace = read(OLD / "evidence/workspace-graph-prepared.json")
after_workspace = read(OLD / "evidence/workspace-graph-after.json")
assert before_workspace == after_workspace and len(before_workspace["files"]) == 268
assert before_workspace["app_package_references"] == package_graph
assert before_workspace["pods_has_additional_swift_package_references"] is False

result = {
    "status": "PASS_SOURCE_BOUND_17_PACKAGE_GRAPH_IDENTITY_HISTORICAL_RESOLUTION_REUSABLE",
    "source": {"historical": BASE, "application": APP, "execution_metadata": META,
               "request_asana_story": "1220765861889338"},
    "historical_evidence": {"run_id": 44976915323, "attempt": 1,
        "commit": "538b2c9ca153c81a593faa08fab3b6a080d428e8", "artifact_id": 14736187053,
        "artifact_sha256": sha((OLD / "artifact-original.zip").read_bytes()),
        "resolution_receipt_sha256": sha((OLD / "evidence/RESOLUTION.json").read_bytes()),
        "parent_review_sha256": sha((OLD / "ROOT_ARTIFACT_REVIEW.json").read_bytes()),
        "strict_invocations": 1, "automatic_resolution": 0, "strict_replays": 0},
    "retrieved_source_blobs": retrieved,
    "archived_committed_inputs": {"count": 23, "identical": 21, "changed": changed, "files": input_comparison},
    "project_delta": {"added_lines": added, "removed_lines": 0,
                      "meaning": "One original Swift source registered in three existing app targets; no package/project-owner/target-owner/build-settings delta.",
                      "unchanged_sections": section_results},
    "package_graph": {"references_and_products": 36, "owning_project_and_target_objects": 7,
                      "all_owning_attachment_arrays_identical": True, "local_reference_paths": local_paths,
                      "source_vendor_manifest_membership": manifest_membership["baseline"],
                      "four_non_Hanlin_local_package_trees": local_package_trees,
                      "changed_compiled_local_package_source": local_package_source_changes,
                      "no_whole_CommandPalette_compiled_source_reuse_claim": True,
                      "lock_git_blob": blob(lock), "lock_sha256": sha(lock), "lock_version": 2,
                      "exact_pin_count": 17, "all_original_pin_objects_identical": True},
    "preparation": {"inputs": preparation_inputs, "whole_stage2_driver_identical": True,
                    "functions": function_records, "consumed_config_keys": sorted(config_keys),
                    "consumed_config_values_identical": True, "Podfile_lock_committed": False,
                    "generated_Pods_lock_and_workspace_current_bytes": "NOT_OBSERVED_NO_PREPARATION_EXECUTED"},
    "metadata": {"changed_keys": sorted(config_diff_keys),
                 "application_commit_embedded_source": configs["application"]["application_source_sha"],
                 "execution_metadata_embedded_source": configs["metadata"]["application_source_sha"],
                 "execution_metadata_trees_match_actual_application": True,
                 "scope": "Use46a as the current execution binding; A's embedded manifest is the preceding5f checkpoint, not a fresh self-binding."},
    "hanlin": {"source": hanlin["sha"], "exact_files": 424, "membership_and_git_blobs_identical": True,
               "historical_before_after_final_identical": True, "current_Git_source_verified": True},
    "reuse_admission": {"historical_strict_17_resolution": "REUSE_WITH_EXACT_SCOPE",
                       "historical_complete_268_workspace_byte_stamp": "NOT_TRANSFERRED",
                       "application_code_equivalence": False, "new_app_build_or_Native_credit": False,
                       "new_preparation_and_build_existing_gates": "STILL_REQUIRED",
                       "conditions": ["Same exact package graph/lock/local manifests/Hanlin and reviewed original preparation route.",
                                      "Historical toolchain remains Xcode27.0/Swift6.4, Node22.23.4/Ruby3.3.14/CocoaPods1.17.0; this audit does not observe a new runner.",
                                      "Current generated workspace/Podfile.lock/privacy/provider output must be checked by the normal new preparation/build gates.",
                                      "Any later SDK distribution, package/pin/manifests/owning-array/preparation change needs its own identity review."]},
    "actions": {"Actions_queries": 0, "watchers_created": 0, "secret_reads_or_writes": 0,
                "Git_mutations": 0, "resolver_runs": 0, "compiler_runs": 0, "test_runs": 0,
                "application_or_repository_source_edits": 0},
}
(ROOT / "M17_REUSE_AUDIT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"status": result["status"], "original_inputs": 23, "byte_identical": 21,
                  "pins": 17, "package_objects": 36, "owners": 7, "hanlin_files": 424,
                  "source_registration_added_lines": 8, "workspace_stamp_transferred": False,
                  "audit_sha256": sha((ROOT / "M17_REUSE_AUDIT.json").read_bytes())}))
