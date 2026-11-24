"""Archive the complete original XCTest product closure after each genuine build.

Closure traversal is adapted from the reviewed Otzaria exporter at
34d4201abe35fdedd1bd74e1009469edf791445b, Scripts/CI/otzaria-miniapps-native.py.
Each Anytype stage keeps its original configurations and exact build receipt.
Export is preservation, not UI acceptance or physical signing qualification.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import tarfile


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def product_closure(products, configurations):
    """Recompute all original XCTest references and relative-link targets on disk."""
    products = Path(products).resolve(strict=True)
    configurations = [Path(path).resolve(strict=True) for path in configurations]
    require(configurations and len(set(configurations)) == len(configurations), "Missing/duplicate original test configuration")
    require(all(path.parent == products and path.suffix == ".xctestrun" for path in configurations),
            "Original test configurations must belong to this exact Products directory")
    roots = list(configurations)
    references, platform_references = [], []

    def include_product(path):
        path = Path(path)
        require(path.is_absolute(), "Original native product reference is not absolute")
        # Retain the lexical reference used by the unchanged xctestrun. Resolving
        # it here would omit a directly referenced framework/app alias from tar.
        path = Path(os.path.normpath(path))
        resolved = path.resolve(strict=True)
        require(path.is_relative_to(products) and path != products
                and resolved.is_relative_to(products) and resolved != products,
                "An original native product reference is outside Products")
        if any(path == root or path.is_relative_to(root) for root in roots):
            return
        parts = path.relative_to(products).parts
        whole = products.joinpath(*parts[:2]) if len(parts) > 1 else path
        ancestor = products
        for part in parts[:2]:
            ancestor = ancestor / part
            if ancestor.is_symlink():
                whole = ancestor
                break
        roots[:] = [root for root in roots if not root.is_relative_to(whole)]
        roots.append(whole)

    def reference_path(value, host):
        if value.startswith(("__PLATFORMS__/", "__DEVELOPER_DIR__/")):
            platform_references.append(value)
            return None
        if "__TESTHOST__" in value:
            require(host is not None, "Original test-host placeholder has no host")
            value = value.replace("__TESTHOST__", str(host))
        value = value.replace("__TESTROOT__", str(products))
        require(re.search(r"__[A-Z][A-Z0-9_]*__", value) is None,
                "Unresolved original XCTest product placeholder")
        path = Path(value)
        require(path.is_absolute(), "Original XCTest product reference is not absolute")
        return Path(os.path.normpath(path))

    product_keys = {"TestBundlePath", "TestHostPath", "UITargetAppPath", "DependentProductPaths", "ProductPath"}

    def collect(value, host=None):
        if isinstance(value, dict):
            if isinstance(value.get("TestHostPath"), str):
                host = reference_path(value["TestHostPath"], host)
            for key, item in value.items():
                if key in product_keys:
                    for raw in item if isinstance(item, list) else [item]:
                        require(isinstance(raw, str), "Invalid original XCTest product reference")
                        path = reference_path(raw, host)
                        if path is not None:
                            include_product(path)
                            references.append(path.relative_to(products).as_posix())
                else:
                    collect(item, host)
        elif isinstance(value, list):
            for item in value:
                collect(item, host)

    for path in configurations:
        collect(plistlib.loads(path.read_bytes()))
    require(references, "Original test configurations contain no actual products")
    def members(top):
        # A top-level product alias is archived as a link; its target is added
        # separately. Do not inventory descendants that tar will not store here.
        return [top, *sorted(top.rglob("*"))] if top.is_dir() and not top.is_symlink() else [top]

    visited = set()
    while True:
        pending = [root for root in roots if root not in visited]
        if not pending:
            break
        for top in pending:
            visited.add(top)
            for path in members(top):
                if path.is_symlink():
                    require(not Path(os.readlink(path)).is_absolute(),
                            "Native product has a nonportable absolute symlink")
                    include_product(path.parent / os.readlink(path))
    roots.sort()
    entries = {}
    for top in roots:
        for path in members(top):
            relative = path.relative_to(products).as_posix()
            if path.is_symlink():
                require(path.resolve(strict=True).is_relative_to(products), "Native symlink leaves Products")
                entries[relative] = {"kind": "symlink", "target": os.readlink(path)}
            elif path.is_file():
                entries[relative] = {"kind": "file", "bytes": path.stat().st_size,
                    "mode": path.stat().st_mode & 0o777, "sha256": digest(path)}
            elif path.is_dir():
                entries[relative] = {"kind": "directory", "mode": path.stat().st_mode & 0o777}
            else:
                raise RuntimeError("Unexpected native product file type")
    return roots, entries, sorted(set(references)), sorted(set(platform_references))


def export_built_products(products, configurations, destination, build_receipt):
    products, destination = Path(products).resolve(strict=True), Path(destination)
    require(build_receipt.get("native_build_succeeded") is True,
            "Only a genuinely successful native build may export products")
    for key in ("source_sha", "run_id", "run_attempt", "configuration", "producer_pin",
                "native_binding", "dependency_resolution", "source_profile_sha256", "selected_methods"):
        require(build_receipt.get(key) is not None, "Missing original build identity: " + key)
    require(not destination.exists(), "An earlier authentic product export must not be overwritten")
    configurations = [Path(path).resolve(strict=True) for path in configurations]
    roots, entries, references, platform_references = product_closure(products, configurations)
    destination.mkdir(parents=True)
    receipt_bytes = (json.dumps(build_receipt, ensure_ascii=False, indent=2) + "\n").encode()
    (destination / "original-build-receipt.json").write_bytes(receipt_bytes)
    archive = destination / "BuildProducts.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=1, dereference=False) as output:
        for path in roots:
            output.add(path, arcname=path.relative_to(products).as_posix(), recursive=True)
    manifest = {
        "schema_version": 1, "status": "ACTUAL_BUILT_SIMULATOR_PRODUCTS_EXPORTED",
        "source_sha": build_receipt["source_sha"], "run_id": build_receipt["run_id"],
        "run_attempt": build_receipt["run_attempt"], "configuration": build_receipt["configuration"],
        "build_status_at_export": build_receipt["status"],
        "original_build_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "archive_name": archive.name, "archive_bytes": archive.stat().st_size, "archive_sha256": digest(archive),
        "files": entries, "original_xctestrun": [path.name for path in configurations],
        "exported_product_roots": [path.relative_to(products).as_posix() for path in roots],
        "original_test_product_references": sorted(set(references)),
        "xcode_platform_provided_references": sorted(set(platform_references)),
        "native_ui_acceptance": "NOT_RUN_AT_EXPORT", "physical_sharing": "NOT_PROVEN_BY_SIMULATOR"}
    manifest_path = destination / "native-products-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {"manifest": str(manifest_path), "manifest_sha256": digest(manifest_path),
            "archive": str(archive), "archive_sha256": manifest["archive_sha256"],
            "original_build_receipt_sha256": manifest["original_build_receipt_sha256"]}
