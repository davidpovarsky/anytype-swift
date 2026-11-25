"""Bind the exact committed original lifecycle/batch source after MiniApps.

The historical ABI/generator evidence is retained. These Swift source hashes
authorize no new native operation or SDK/editor acceptance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "e2582894e9141f4a136823d4c7b4a011d1edbd80"
REVIEWED = "aea88bf9434fb787909a4e671f038f292e9b6a09"
RELATIVE = "Tools/OriginalEditor/MiniApps/lifecycle_batch_source_adoption.json"
FILES = (
    "Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationSearchVisibility.swift",
    "Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift",
    "Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift",
    "Anytype/Sources/ServiceLayer/Object/CrossSpaceSearch/CrossSpaceSearchService.swift",
    "Anytype/Sources/ServiceLayer/Object/Search/SearchService.swift",
    "Anytype/Sources/ServiceLayer/Object/SearchWithMeta/SearchWithMetaService.swift",
    "Anytype/Sources/ServiceLayer/Subscriptions/RecentSubscriptionService.swift",
    "OriginalEditorFramework/AnytypeOriginalAnnotationImport.swift",
    "OriginalEditorFramework/AnytypeOriginalAnnotationLifecycle.swift",
    "OriginalEditorFramework/AnytypeOriginalAnnotationRevision.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotationBatch.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationJournal.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationNativeBody.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift",
)
ADDED = {FILES[0], FILES[8], FILES[11]}


def require(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60).decode().strip()


def observe(root, profile, historical_trees):
    binding = profile.get("lifecycle_batch_source_adoption")
    if binding is None:
        return None
    root = Path(root).resolve()
    path = root / RELATIVE
    require(binding.get("path") == RELATIVE and binding.get("reviewed_source") == REVIEWED
            and path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Unreviewed or aliased lifecycle/batch source adoption")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == binding.get("sha256")
            and git(root, "hash-object", "--", RELATIVE) == git(root, "rev-parse", "HEAD:" + RELATIVE),
            "Committed lifecycle/batch source adoption bytes differ")
    value = json.loads(raw)
    require(value.get("schema") == "miniapps.original-lifecycle-batch-source-adoption/1"
            and value.get("base_source") == BASE and value.get("reviewed_source") == REVIEWED
            and value.get("scope") == "SOURCE_ONLY_CURRENT_SDK_QUALIFICATION_REQUIRED"
            and value.get("native_acceptance_reused_by_this_document") is False,
            "Lifecycle/batch source provenance cannot grant native acceptance")
    rows = value.get("files", [])
    require([row.get("path") for row in rows] == list(FILES)
            and all(set(row) == {"path", "before_blob", "after_blob", "bytes", "sha256"} for row in rows),
            "Lifecycle/batch source delta differs")
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
            "Lifecycle/batch changed original native/generated/resource/module inputs")
    require(git(root, "diff", "--name-status", BASE, REVIEWED, "--", *products).splitlines()
            == [("A\t" if name in ADDED else "M\t") + name for name in FILES],
            "Unreviewed lifecycle/batch source delta")
    from native_files_source import observe as observe_native_files
    native_files = observe_native_files(root, profile, reviewed)
    current = native_files["reviewed_product_trees"] if native_files else reviewed
    changed_files = set(native_files["all_changed_paths"]) if native_files else set()
    require({key: git(root, "rev-parse", "HEAD:" + key) for key in products} == current,
            "Current product source differs from reviewed lifecycle/batch continuation")
    for row in rows:
        source = root / row["path"]
        require(source.is_file() and not source.is_symlink() and source.resolve() == source,
                "Missing or aliased lifecycle/batch source")
        data = (subprocess.check_output(["git", "-C", str(root), "show", REVIEWED + ":" + row["path"]])
                if row["path"] in changed_files else source.read_bytes())
        observed_blob = (git(root, "rev-parse", REVIEWED + ":" + row["path"])
                         if row["path"] in changed_files else git(root, "hash-object", "--", row["path"]))
        before = None if row["path"] in ADDED else git(root, "rev-parse", BASE + ":" + row["path"])
        require(row["before_blob"] == before
                and row["after_blob"] == git(root, "rev-parse", REVIEWED + ":" + row["path"])
                and observed_blob == row["after_blob"]
                and len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Current lifecycle/batch source bytes differ: " + row["path"])
    return {"schema": value["schema"], "status": "EXACT_ORIGINAL_LIFECYCLE_BATCH_SWIFT_SOURCE_OBSERVED",
            "base_source": BASE, "reviewed_source": REVIEWED,
            "adoption_sha256": binding["sha256"], "reviewed_product_trees": current,
            "historical_lifecycle_product_trees": reviewed,
            **({"native_files": native_files} if native_files else {}),
            "all_changed_paths": sorted(set(FILES) | changed_files),
            "changed_files": rows, "native_acceptance_reused_by_this_document": False,
            "sdk_compiler_and_runtime_acceptance": "NOT_GRANTED_BY_SOURCE_OBSERVATION"}
