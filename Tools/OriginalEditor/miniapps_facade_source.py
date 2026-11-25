"""Bind exactly the reviewed MiniApps Swift delta after the original revision SDK.

This source observation preserves historical qualifications. It grants neither
new native ABI semantics nor full SDK/editor acceptance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "a91d572cb2df2b05c7d93520732eecd7380294fd"
REVIEWED = "e2582894e9141f4a136823d4c7b4a011d1edbd80"
RELATIVE = "Tools/OriginalEditor/MiniApps/source_adoption.json"
FILES = (
    "Anytype/Sources/PresentationLayer/Common/UIKit/TextView/CustomTextView+UITextViewDelegate.swift",
    "Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/PreparedEditorPageSession.swift",
    "Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift",
    "Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageController.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorHost.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorSnapshot.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift",
)


def require(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60).decode().strip()


def observe(root, profile, historical_trees):
    binding = profile.get("miniapps_source_adoption")
    if binding is None:
        return None
    root = Path(root).resolve()
    path = root / RELATIVE
    require(binding.get("path") == RELATIVE and binding.get("reviewed_source") == REVIEWED
            and path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Unreviewed or aliased MiniApps source adoption")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == binding.get("sha256")
            and git(root, "hash-object", "--", RELATIVE) == git(root, "rev-parse", "HEAD:" + RELATIVE),
            "Committed MiniApps source adoption bytes differ")
    value = json.loads(raw)
    require(value.get("schema") == "miniapps.original-editor-source-adoption/1"
            and value.get("base_source") == BASE and value.get("reviewed_source") == REVIEWED
            and value.get("scope") == "SOURCE_ONLY_CURRENT_SDK_QUALIFICATION_REQUIRED"
            and value.get("native_acceptance_reused_by_this_document") is False,
            "MiniApps source provenance cannot grant native acceptance")
    rows = value.get("files", [])
    require([row.get("path") for row in rows] == list(FILES)
            and all(set(row) == {"path", "before_blob", "after_blob", "bytes", "sha256"} for row in rows),
            "MiniApps original source delta differs")
    products = tuple(historical_trees)
    for older, newer in [(BASE, REVIEWED), (REVIEWED, "HEAD")]:
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
                       check=True, timeout=60)
    base = {key: git(root, "rev-parse", BASE + ":" + key) for key in products}
    reviewed = {key: git(root, "rev-parse", REVIEWED + ":" + key) for key in products}
    require(base == historical_trees == value.get("base_product_trees")
            and reviewed == value.get("reviewed_product_trees")
            and all(reviewed[key] == base[key] for key in products
                    if key not in ("Anytype/Sources", "OriginalEditorFramework")),
            "MiniApps changed original native/generated/resource/module inputs")
    require(git(root, "diff", "--name-status", BASE, REVIEWED, "--", *products).splitlines()
            == ["M	" + name for name in FILES],
            "Unreviewed MiniApps source delta")
    from lifecycle_batch_source import observe as observe_lifecycle_batch
    lifecycle = observe_lifecycle_batch(root, profile, reviewed)
    current = lifecycle["reviewed_product_trees"] if lifecycle else reviewed
    changed_lifecycle = set(lifecycle["all_changed_paths"]) if lifecycle else set()
    require({key: git(root, "rev-parse", "HEAD:" + key) for key in products} == current,
            "Current product source differs from the reviewed MiniApps continuation")
    for row in rows:
        source = root / row["path"]
        require(source.is_file() and not source.is_symlink() and source.resolve() == source,
                "Missing or aliased MiniApps source")
        data = (subprocess.check_output(["git", "-C", str(root), "show", REVIEWED + ":" + row["path"]])
                if row["path"] in changed_lifecycle else source.read_bytes())
        observed_blob = (git(root, "rev-parse", REVIEWED + ":" + row["path"])
                         if row["path"] in changed_lifecycle else git(root, "hash-object", "--", row["path"]))
        require(row["before_blob"] == git(root, "rev-parse", BASE + ":" + row["path"])
                and row["after_blob"] == git(root, "rev-parse", REVIEWED + ":" + row["path"])
                and observed_blob == row["after_blob"]
                and len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Current MiniApps source bytes differ: " + row["path"])
    return {"schema": value["schema"], "status": "EXACT_MINIAPPS_SWIFT_SOURCE_OBSERVED",
            "base_source": BASE, "reviewed_source": REVIEWED,
            "adoption_sha256": binding["sha256"], "reviewed_product_trees": current,
            "historical_miniapps_product_trees": reviewed,
            **({"lifecycle_batch": lifecycle} if lifecycle else {}),
            "changed_files": rows, "all_changed_paths": sorted(set(FILES) | changed_lifecycle),
            "native_acceptance_reused_by_this_document": False,
            "sdk_compiler_and_runtime_acceptance": "NOT_GRANTED_BY_SOURCE_OBSERVATION"}
