"""Admit only the separately reviewed 21-file closed lifecycle, visibility and local batch continuation.

Historical generated/native qualification remains unchanged. This observation is
source provenance; the current SDK still needs real compiler/runtime acceptance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "34b8a7c5ddb34e9287acdb5c189849eeac8cff86"
REVIEWED = "86d738c662c332cec370cee6a09dd434808dbeb9"
RELATIVE = "Tools/OriginalEditor/LifecycleBatch/source_adoption.json"
PRODUCTS = ("Anytype/Sources", "Anytype/Resources", "Modules",
            "OriginalEditorFramework", "Dependencies/Middleware")
ADDED = ('Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationSearchVisibility.swift', 'OriginalEditorFramework/AnytypeOriginalAnnotationLifecycle.swift', 'OriginalEditorFramework/AnytypeOriginalAnnotationRevision.swift', 'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotationBatch.swift')
FILES = ('Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationImport.swift', 'Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationSearchVisibility.swift', 'Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift', 'Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift', 'Anytype/Sources/ServiceLayer/Object/CrossSpaceSearch/CrossSpaceSearchService.swift', 'Anytype/Sources/ServiceLayer/Object/Search/SearchService.swift', 'Anytype/Sources/ServiceLayer/Object/SearchWithMeta/SearchWithMetaService.swift', 'Anytype/Sources/ServiceLayer/Subscriptions/RecentSubscriptionService.swift', 'OriginalEditorFramework/AnytypeOriginalAnnotationImport.swift', 'OriginalEditorFramework/AnytypeOriginalAnnotationLifecycle.swift', 'OriginalEditorFramework/AnytypeOriginalAnnotationRevision.swift', 'OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift', 'OriginalEditorFramework/AnytypeOriginalEditorHost.swift', 'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift', 'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotationBatch.swift', 'OriginalEditorFramework/AnytypeOriginalEditorSnapshot.swift', 'OriginalEditorFramework/OriginalAnnotationNativeArchiveComparison.swift', 'OriginalEditorFramework/OriginalEditorLocalAnnotationJournal.swift', 'OriginalEditorFramework/OriginalEditorLocalAnnotationMaterialization.swift', 'OriginalEditorFramework/OriginalEditorLocalAnnotationNativeBody.swift', 'OriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift')


def require(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60).decode().strip()


def validate_document(value, binding):
    require(value.get("schema") == "otzaria.annotation-lifecycle-source-adoption/1"
            and value.get("base_source") == BASE and value.get("reviewed_source") == REVIEWED
            and binding.get("path") == RELATIVE
            and binding.get("reviewed_source") == REVIEWED,
            "Unreviewed annotation-exchange source identity")
    rows = value.get("files", [])
    require([r.get("path") for r in rows] == list(FILES)
            and all(set(r) == {"path", "before_blob", "after_blob", "bytes", "sha256"}
                    for r in rows), "Annotation-exchange source delta differs")
    require(value.get("scope") == "SOURCE_ONLY_CURRENT_SDK_QUALIFICATION_REQUIRED"
            and value.get("native_acceptance_reused_by_this_document") is False,
            "Facade source provenance must not claim native qualification")
    return rows


def observe(root, profile, historical_trees):
    binding = profile.get("annotation_lifecycle_source_adoption")
    if binding is None:
        return None
    root = Path(root).resolve()
    path = root / RELATIVE
    require(path.is_file() and not path.is_symlink()
            and path.resolve() == path, "Missing or aliased facade source adoption")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == binding.get("sha256")
            and git(root, "hash-object", "--", RELATIVE)
                == git(root, "rev-parse", "HEAD:" + RELATIVE),
            "Committed facade source adoption bytes differ")
    value = json.loads(raw)
    rows = validate_document(value, binding)
    from additive_facade_source import validate_document as validate_historical
    prior = root / "Tools/OriginalEditor/AnnotationExchange/source_adoption.json"
    prior_hash = "218d880efa27bef5e437af03f76196d0458309cddf596959bcd9df30ee11fd93"
    require(prior.is_file() and not prior.is_symlink()
            and hashlib.sha256(prior.read_bytes()).hexdigest() == prior_hash
            and value.get("historical_annotation_exchange_adoption_sha256") == prior_hash,
            "Historical annotation source evidence changed")
    validate_historical(json.loads(prior.read_bytes()), profile["annotation_exchange_source_adoption"])
    for older, newer in [(BASE, REVIEWED), (REVIEWED, "HEAD")]:
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
                       check=True, timeout=60)
    base = {p: git(root, "rev-parse", BASE + ":" + p) for p in PRODUCTS}
    reviewed = {p: git(root, "rev-parse", REVIEWED + ":" + p) for p in PRODUCTS}
    require(base == historical_trees == value.get("base_product_trees"),
            "Historical facade/native source identity differs")
    require(reviewed == value.get("reviewed_product_trees")
            and all(reviewed[p] == base[p] for p in PRODUCTS if p not in ("OriginalEditorFramework", "Anytype/Sources")),
            "Revision continuation changed generated/native/resource inputs")
    delta = git(root, "diff", "--name-status", BASE, REVIEWED, "--", *PRODUCTS).splitlines()
    require(delta == [("A\t" if p in ADDED else "M\t") + p for p in FILES], "Unreviewed product change in facade continuation")
    require({p: git(root, "rev-parse", "HEAD:" + p) for p in PRODUCTS} == reviewed,
            "Current product source differs from reviewed facade continuation")
    for row in rows:
        p = root / row["path"]
        require(p.is_file() and not p.is_symlink() and p.resolve() == p,
                "Missing/aliased reviewed facade source")
        data = p.read_bytes()
        require(row["before_blob"] == (None if row["path"] in ADDED else git(root, "rev-parse", BASE + ":" + row["path"]))
                and row["after_blob"] == git(root, "rev-parse", REVIEWED + ":" + row["path"])
                and git(root, "hash-object", "--", row["path"]) == row["after_blob"]
                and len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Reviewed facade source bytes differ: " + row["path"])
    return {"schema": value["schema"], "status": "EXACT_ADDITIVE_FACADE_SOURCE_OBSERVED",
            "base_source": BASE, "reviewed_source": REVIEWED,
            "adoption_sha256": binding["sha256"], "reviewed_product_trees": reviewed,
            "changed_files": rows, "native_acceptance_reused_by_this_document": False,
            "sdk_compiler_and_runtime_acceptance": "NOT_GRANTED_BY_SOURCE_OBSERVATION"}
