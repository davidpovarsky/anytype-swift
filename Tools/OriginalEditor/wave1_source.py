"""Admit exact original product changes after the retained 75a98ba SDK.

This records current Swift source only. The historical SDK, native ABI, migration
and UI receipts retain their original identities and grant no new acceptance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "75a98ba98d6455eefc2c98113fa744b0f3c2e7bf"
REVIEWED = "efad6194ccf224eed61c4e2e71d104b5b078add3"
RELATIVE = "Tools/OriginalEditor/Wave1/product_source_adoption.json"
SCHEMA = "anytype.original-wave1-product-source-adoption/2"
PRODUCTS = ("Anytype/Sources", "Anytype/Resources", "Modules",
            "OriginalEditorFramework", "Dependencies/Middleware")
FILES = (
    'Anytype/Sources/Pinkha/Bootstrap/PinkhaBootstrapHook.swift',
    'Anytype/Sources/Pinkha/Bootstrap/PinkhaBootstrapStateManager.swift',
    'Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift',
    'Anytype/Sources/PresentationLayer/Auth/PrimaryAuthView/PrimaryAuthView.swift',
    'Anytype/Sources/PresentationLayer/Modules/ServerConfiguration/ServerConfigurationView.swift',
    'Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift',
    'Modules/PinkhaKit/Sources/PinkhaKit/Bootstrap/PinkhaBootstrapProtocols.swift',
    'Modules/PinkhaKit/Sources/PinkhaKit/Bootstrap/PinkhaSpaceBootstrapEngine.swift',
    'Modules/PinkhaKit/Sources/PinkhaKit/Schema/PinkhaSpaceManifest.swift',
    'Modules/PinkhaKit/Tests/PinkhaKitTests/PinkhaBootstrapRecoveryTests.swift',
    'OriginalEditorFramework/AnytypeOriginalAnnotationImport.swift',
    'OriginalEditorFramework/AnytypeOriginalAnnotationRevision.swift',
    'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift',
    'OriginalEditorFramework/AnytypeOriginalEditorSnapshot.swift',
    'OriginalEditorFramework/OriginalAnnotationNativeArchiveComparison.swift',
    'OriginalEditorFramework/OriginalEditorLocalAnnotationJournal.swift',
    'OriginalEditorFramework/OriginalEditorLocalAnnotationMaterialization.swift',
    'OriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift',
)
ADDED = frozenset({'Modules/PinkhaKit/Tests/PinkhaKitTests/PinkhaBootstrapRecoveryTests.swift'})


def require(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], timeout=60).decode().strip()


def validate_document(value, binding):
    require(set(binding) == {"path", "sha256", "reviewed_source"}
            and binding["path"] == RELATIVE and binding["reviewed_source"] == REVIEWED,
            "Unreviewed Wave 1 product source binding")
    require(set(value) == {"schema", "base_source", "reviewed_source",
                          "base_product_trees", "reviewed_product_trees",
                          "files", "scope", "native_acceptance_reused_by_this_document"}
            and value["schema"] == SCHEMA and value["base_source"] == BASE
            and value["reviewed_source"] == REVIEWED
            and value["scope"] == "SOURCE_ONLY_CURRENT_SDK_QUALIFICATION_REQUIRED"
            and value["native_acceptance_reused_by_this_document"] is False,
            "Wave 1 source identity or acceptance scope differs")
    require(set(value["base_product_trees"]) == set(PRODUCTS)
            and set(value["reviewed_product_trees"]) == set(PRODUCTS),
            "Wave 1 product tree closure differs")
    rows = value["files"]
    require([row.get("path") for row in rows] == list(FILES)
            and all(set(row) == {"path", "status", "before_blob", "after_blob", "bytes", "sha256"}
                    and row["status"] == ("A" if row["path"] in ADDED else "M")
                    and (row["before_blob"] is None) == (row["path"] in ADDED)
                    for row in rows),
            "Wave 1 exact source membership differs")
    return rows


def observe(root, binding, historical_trees=None):
    if binding is None:
        return None
    root = Path(root).resolve()
    document = root / RELATIVE
    require(document.is_file() and not document.is_symlink()
            and document.resolve() == document, "Missing or aliased Wave 1 source adoption")
    raw = document.read_bytes()
    value = json.loads(raw)
    rows = validate_document(value, binding)
    require(hashlib.sha256(raw).hexdigest() == binding["sha256"]
            and git(root, "hash-object", "--", RELATIVE)
                == git(root, "rev-parse", "HEAD:" + RELATIVE),
            "Committed Wave 1 source adoption differs")
    for older, newer in ((BASE, REVIEWED), (REVIEWED, "HEAD")):
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                        older, newer], check=True, timeout=60)
    before = {p: git(root, "rev-parse", BASE + ":" + p) for p in PRODUCTS}
    after = {p: git(root, "rev-parse", REVIEWED + ":" + p) for p in PRODUCTS}
    require(before == value["base_product_trees"]
            and (historical_trees is None or before == historical_trees)
            and after == value["reviewed_product_trees"],
            "Wave 1 recorded product trees differ from actual Git objects")
    require(all(before[p] == after[p] for p in ("Anytype/Resources", "Dependencies/Middleware")),
            "Wave 1 continuation changed original resource or native middleware input")
    require(all(name.endswith(".swift") for name in FILES),
            "Wave 1 exact continuation must contain reviewed Swift only")
    require(git(root, "diff", "--name-status", BASE, REVIEWED, "--", *PRODUCTS).splitlines()
            == [("A" if name in ADDED else "M") + "\t" + name for name in FILES],
            "Wave 1 product delta is not the exact reviewed Swift change")
    require({p: git(root, "rev-parse", "HEAD:" + p) for p in PRODUCTS} == after,
            "Current product tree differs from the exact Wave 1 continuation")
    require(not git(root, "status", "--porcelain", "--untracked-files=all", "--", *PRODUCTS),
            "Uncommitted or additional Wave 1 product source")
    for row in rows:
        name = row["path"]
        source = root / name
        require(source.is_file() and not source.is_symlink() and source.resolve() == source,
                "Missing or aliased Wave 1 source: " + name)
        data = source.read_bytes()
        require(row["before_blob"] == (None if name in ADDED else git(root, "rev-parse", BASE + ":" + name))
                and row["after_blob"] == git(root, "rev-parse", REVIEWED + ":" + name)
                and git(root, "hash-object", "--", name) == row["after_blob"]
                and len(data) == row["bytes"]
                and hashlib.sha256(data).hexdigest() == row["sha256"],
                "Current Wave 1 source bytes differ: " + name)
    return {"schema": SCHEMA, "base_source": BASE, "reviewed_source": REVIEWED,
            "adoption_sha256": binding["sha256"], "base_product_trees": before,
            "reviewed_product_trees": after, "all_changed_paths": list(FILES),
            "native_acceptance_reused_by_this_document": False,
            "sdk_compiler_and_runtime_acceptance": "NOT_GRANTED_BY_SOURCE_OBSERVATION"}


def historical_bytes(root, name, revision, continuation):
    """Read a historical row only after its replacement passed exact admission."""
    if continuation and name in continuation["all_changed_paths"]:
        expected = git(root, "rev-parse", revision + ":" + name)
        return subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", expected],
                                       timeout=60), expected
    return (Path(root) / name).read_bytes(), git(root, "hash-object", "--", name)
