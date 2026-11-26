"""Admit the exact original MiniApps file-facade continuation as source only.

The original native ABI, resource and generated-source receipts stay unchanged.
This permits no current framework, file exchange, crash or editor acceptance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "52e73697bca9099f5926cee3fcfe447e1d70459b"
REVIEWED = "8099a027a8e216cf45207463222466ce6072dc6c"
RELATIVE = "Tools/OriginalEditor/MiniApps/native_files_source_adoption.json"
FILES = (
    "OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorSnapshot.swift",
    "OriginalEditorFramework/OriginalAnnotationNativeArchiveComparison.swift",
)


CURRENT_SOURCE = "9a870f9d38ec587474f7a73a31e227be1fb007c7"
CURRENT_RELATIVE = "Tools/OriginalEditor/MiniApps/current_native_annotation_source_adoption.json"
CURRENT_FILES = (
    "OriginalEditorFramework/AnytypeOriginalAnnotationLifecycle.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorQualificationRuntime.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationMaterialization.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationNativeBody.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift",
)


def require(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60).decode().strip()


def validate_document(value, binding):
    require(binding.get("path") == RELATIVE and binding.get("reviewed_source") == REVIEWED
            and value.get("schema") == "miniapps.original-native-files-source-adoption/1"
            and value.get("base_source") == BASE and value.get("reviewed_source") == REVIEWED,
            "Unreviewed original native-file source identity")
    rows = value.get("files", [])
    require([row.get("path") for row in rows] == list(FILES)
            and all(set(row) == {"path", "before_blob", "after_blob", "bytes", "sha256"}
                    for row in rows), "Original native-file source delta differs")
    require(value.get("scope") == "SOURCE_ONLY_CURRENT_SDK_QUALIFICATION_REQUIRED"
            and value.get("native_acceptance_reused_by_this_document") is False,
            "Original native-file source provenance cannot grant acceptance")
    return rows


def observe_saved_body_focus(root, binding, historical_trees, wave1=None):
    relative = "Tools/OriginalEditor/MiniApps/saved_body_focus_source_adoption.json"
    base = "b10eee2845859c03c534eed41e8682ad8cd5bff6"
    reviewed = "e973cc7432419778f0342624a3b7052055fd270d"
    products = tuple(historical_trees)
    document = root / relative
    require(document.is_file() and not document.is_symlink() and document.resolve() == document,
            "Missing or aliased original saved-body focus source adoption")
    raw = document.read_bytes()
    require(binding.get("path") == relative and binding.get("reviewed_source") == reviewed
            and hashlib.sha256(raw).hexdigest() == binding.get("sha256")
            and git(root, "hash-object", "--", relative) == git(root, "rev-parse", "HEAD:" + relative),
            "Committed original saved-body focus source adoption differs")
    value = json.loads(raw)
    require(value.get("schema") == "anytype.original-saved-body-focus-source-adoption/1"
            and value.get("base_source") == base and value.get("reviewed_source") == reviewed
            and value.get("scope") == "SOURCE_ONLY_CURRENT_SDK_QUALIFICATION_REQUIRED"
            and value.get("native_acceptance_reused_by_this_document") is False,
            "Unreviewed original saved-body focus source identity or scope")
    for older, newer in ((CURRENT_SOURCE, base), (base, reviewed), (reviewed, "HEAD")):
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
                       check=True, timeout=60)
    before = {key: git(root, "rev-parse", base + ":" + key) for key in products}
    after = {key: git(root, "rev-parse", reviewed + ":" + key) for key in products}
    require(before == historical_trees == value.get("base_product_trees")
            and after == value.get("reviewed_product_trees")
            and all(before[key] == after[key] for key in products
                    if key not in ("Anytype/Sources", "OriginalEditorFramework")),
            "Saved-body focus changed the original generated, resource or middleware source")
    changes = git(root, "diff", "--name-status", "-z", base, reviewed, "--", *products).split("\0")[:-1]
    rows = value.get("files", [])
    names = [row.get("path") for row in rows]
    require(len(rows) == len(set(names)) == 6
            and changes[::2] == ["M"] * 6 and changes[1::2] == names
            and all(set(row) == {"path", "before_blob", "after_blob", "bytes", "sha256"} for row in rows),
            "Original saved-body focus source delta differs")
    for row in rows:
        name = row["path"]
        path = root / name
        require(path.is_file() and not path.is_symlink() and path.resolve() == path,
                "Missing or aliased original saved-body focus source")
        from wave1_source import historical_bytes
        data, observed_blob = historical_bytes(root, name, reviewed, wave1)
        require(row["before_blob"] == git(root, "rev-parse", base + ":" + name)
                and row["after_blob"] == git(root, "rev-parse", reviewed + ":" + name)
                and observed_blob == row["after_blob"]
                and len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Current original saved-body focus bytes differ: " + name)
    return {"schema": value["schema"], "base_source": base, "reviewed_source": reviewed,
            "adoption_sha256": binding["sha256"], "reviewed_product_trees": after,
            "all_changed_paths": names, "native_acceptance_reused_by_this_document": False}


def observe_current_runtime(root, binding, historical_trees, focus_binding=None, wave1=None):
    products = tuple(historical_trees)
    document = root / CURRENT_RELATIVE
    require(document.is_file() and not document.is_symlink() and document.resolve() == document,
            "Missing or aliased original annotation runtime source adoption")
    raw = document.read_bytes()
    require(binding.get("path") == CURRENT_RELATIVE and binding.get("reviewed_source") == CURRENT_SOURCE
            and hashlib.sha256(raw).hexdigest() == binding.get("sha256")
            and git(root, "hash-object", "--", CURRENT_RELATIVE) == git(root, "rev-parse", "HEAD:" + CURRENT_RELATIVE),
            "Committed original annotation runtime source adoption differs")
    value = json.loads(raw)
    require(value.get("schema") == "anytype.original-annotation-runtime-source-adoption/1"
            and value.get("base_source") == REVIEWED and value.get("reviewed_source") == CURRENT_SOURCE
            and value.get("scope") == "SOURCE_ONLY_CURRENT_SDK_QUALIFICATION_REQUIRED"
            and value.get("native_acceptance_reused_by_this_document") is False,
            "Unreviewed annotation runtime source identity or scope")
    for older, newer in ((REVIEWED, CURRENT_SOURCE), (CURRENT_SOURCE, "HEAD")):
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
                       check=True, timeout=60)
    base = {key: git(root, "rev-parse", REVIEWED + ":" + key) for key in products}
    reviewed = {key: git(root, "rev-parse", CURRENT_SOURCE + ":" + key) for key in products}
    require(base == historical_trees == value.get("base_product_trees")
            and reviewed == value.get("reviewed_product_trees")
            and all(reviewed[key] == base[key] for key in products if key != "OriginalEditorFramework"),
            "Embedded annotation runtime changed generated, resource or middleware source")
    require(git(root, "diff", "--name-status", REVIEWED, CURRENT_SOURCE, "--", *products).splitlines()
            == ["M\t" + name for name in CURRENT_FILES],
            "Original annotation runtime source delta differs")
    focus = observe_saved_body_focus(root, focus_binding, reviewed, wave1) if focus_binding else None
    focus_paths = set(focus["all_changed_paths"]) if focus else set()
    rows = value.get("files", [])
    require([item.get("path") for item in rows] == list(CURRENT_FILES)
            and all(set(item) == {"path", "before_blob", "after_blob", "bytes", "sha256"} for item in rows),
            "Original annotation runtime file inventory differs")
    for row in rows:
        name = row["path"]
        source = root / name
        require(source.is_file() and not source.is_symlink() and source.resolve() == source,
                "Missing or aliased original annotation runtime source")
        verified_blob = git(root, "rev-parse", CURRENT_SOURCE + ":" + name)
        if name in focus_paths or (wave1 and name in wave1["all_changed_paths"]):
            data = subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", verified_blob], timeout=60)
            observed_blob = verified_blob
        else:
            data = source.read_bytes()
            observed_blob = git(root, "hash-object", "--", name)
        require(row["before_blob"] == git(root, "rev-parse", REVIEWED + ":" + name)
                and row["after_blob"] == verified_blob
                and observed_blob == row["after_blob"]
                and len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Current original annotation runtime source bytes differ: " + name)
    return {"schema": value["schema"], "status": "EXACT_ORIGINAL_ANNOTATION_RUNTIME_SOURCE_OBSERVED",
            "base_source": REVIEWED, "reviewed_source": CURRENT_SOURCE,
            "reviewed_product_trees": focus["reviewed_product_trees"] if focus else reviewed,
            "adoption_sha256": binding["sha256"], "changed_files": rows,
            "all_changed_paths": sorted(set(CURRENT_FILES) | focus_paths),
            **({"saved_body_focus": focus} if focus else {}),
            "native_acceptance_reused_by_this_document": False,
            "sdk_compiler_and_runtime_acceptance": "NOT_GRANTED_BY_SOURCE_OBSERVATION"}


def observe(root, profile, historical_trees):
    binding = profile.get("native_files_source_adoption")
    if binding is None:
        return None
    root = Path(root).resolve()
    path = root / RELATIVE
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Missing or aliased native-file source adoption")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == binding.get("sha256")
            and git(root, "hash-object", "--", RELATIVE) == git(root, "rev-parse", "HEAD:" + RELATIVE),
            "Committed native-file source adoption bytes differ")
    value = json.loads(raw)
    rows = validate_document(value, binding)
    products = tuple(historical_trees)
    for older, newer in [(BASE, REVIEWED), (REVIEWED, "HEAD")]:
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
                       check=True, timeout=60)
    base = {key: git(root, "rev-parse", BASE + ":" + key) for key in products}
    reviewed = {key: git(root, "rev-parse", REVIEWED + ":" + key) for key in products}
    require(base == historical_trees == value.get("base_product_trees")
            and reviewed == value.get("reviewed_product_trees")
            and all(reviewed[key] == base[key] for key in products if key != "OriginalEditorFramework"),
            "Native-file facade changed original native/generated/resource/application inputs")
    require(git(root, "diff", "--name-status", BASE, REVIEWED, "--", *products).splitlines()
            == ["M\t" + name for name in FILES], "Unreviewed native-file facade change")
    runtime_binding = profile.get("current_annotation_runtime_source_adoption")
    focus_binding = profile.get("saved_body_focus_source_adoption")
    require(runtime_binding or not focus_binding, "Saved-body focus requires the original annotation runtime")
    from wave1_source import observe as observe_wave1, historical_bytes
    wave1 = observe_wave1(root, profile.get("wave1_product_source_adoption"))
    runtime = (observe_current_runtime(root, runtime_binding, reviewed, focus_binding, wave1)
               if runtime_binding else None)
    current = runtime["reviewed_product_trees"] if runtime else reviewed
    if wave1:
        require(current == wave1["base_product_trees"],
                "Wave 1 continuation does not follow the admitted original product")
        current = wave1["reviewed_product_trees"]
    require({key: git(root, "rev-parse", "HEAD:" + key) for key in products} == current,
            "Current product source differs from reviewed native-file facade")
    for row in rows:
        source = root / row["path"]
        require(source.is_file() and not source.is_symlink() and source.resolve() == source,
                "Missing or aliased original native-file source")
        data, observed_blob = historical_bytes(root, row["path"], REVIEWED, wave1)
        require(row["before_blob"] == git(root, "rev-parse", BASE + ":" + row["path"])
                and row["after_blob"] == git(root, "rev-parse", REVIEWED + ":" + row["path"])
                and observed_blob == row["after_blob"]
                and len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Current native-file facade bytes differ: " + row["path"])
    return {"schema": value["schema"], "status": "EXACT_ORIGINAL_NATIVE_FILES_SWIFT_SOURCE_OBSERVED",
            "base_source": BASE, "reviewed_source": REVIEWED,
            "adoption_sha256": binding["sha256"], "reviewed_product_trees": current,
            "historical_native_file_product_trees": reviewed,
            **({"current_annotation_runtime": runtime} if runtime else {}),
            "changed_files": rows,
            "all_changed_paths": sorted(set(FILES)
                | (set(runtime["all_changed_paths"]) if runtime else set())
                | (set(wave1["all_changed_paths"]) if wave1 else set())),
            **({"wave1_product": wave1} if wave1 else {}),
            "native_acceptance_reused_by_this_document": False,
            "sdk_compiler_and_runtime_acceptance": "NOT_GRANTED_BY_SOURCE_OBSERVATION"}
