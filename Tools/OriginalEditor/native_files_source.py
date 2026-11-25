"""Admit the exact original MiniApps file-facade continuation as source only.

The original native ABI, resource and generated-source receipts stay unchanged.
This permits no current framework, file exchange, crash or editor acceptance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "52e73697bca9099f5926cee3fcfe447e1d70459b"
REVIEWED = "3a6b4153b21c77d1a85a36e02dec326434966722"
RELATIVE = "Tools/OriginalEditor/MiniApps/native_files_source_adoption.json"
FILES = (
    "OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorSnapshot.swift",
    "OriginalEditorFramework/OriginalAnnotationNativeArchiveComparison.swift",
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
    require({key: git(root, "rev-parse", "HEAD:" + key) for key in products} == reviewed,
            "Current product source differs from reviewed native-file facade")
    for row in rows:
        source = root / row["path"]
        require(source.is_file() and not source.is_symlink() and source.resolve() == source,
                "Missing or aliased original native-file source")
        data = source.read_bytes()
        require(row["before_blob"] == git(root, "rev-parse", BASE + ":" + row["path"])
                and row["after_blob"] == git(root, "rev-parse", REVIEWED + ":" + row["path"])
                and git(root, "hash-object", "--", row["path"]) == row["after_blob"]
                and len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Current native-file facade bytes differ: " + row["path"])
    return {"schema": value["schema"], "status": "EXACT_ORIGINAL_NATIVE_FILES_SWIFT_SOURCE_OBSERVED",
            "base_source": BASE, "reviewed_source": REVIEWED,
            "adoption_sha256": binding["sha256"], "reviewed_product_trees": reviewed,
            "changed_files": rows, "all_changed_paths": list(FILES),
            "native_acceptance_reused_by_this_document": False,
            "sdk_compiler_and_runtime_acceptance": "NOT_GRANTED_BY_SOURCE_OBSERVATION"}
