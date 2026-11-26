"""Exact current MiniApps86 producer admission for original App14 consumers.

This admits original compiled bytes and prepared Git source. It performs no
build, simulator operation, or acceptance test. The historical70eb route remains
separate in its original controller.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import plistlib
import subprocess
import sys

APP_SOURCE = "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
PRODUCER_SOURCE = "86a6dde354947be9329fe1e8f4d45a433fe488c4"
PRODUCER_MANIFEST = "2fa60b21a153cbe7f1cb6e036d308c0d93ddb60306516989841fd98941ee47ea"
PRODUCER_ARCHIVE = "732c24136209b2ac771bf845d66b25c550d56356c8866bd18c885a347dffc0b4"
SOURCE_REPOSITORY = Path("/Users/m1/development/anytype-root-active-20261125/miniapps-producer86-restore3/source")
PREPARATION = {
    "path": "Tools/MiniApps/producer-preparation-86a6dde3.json",
    "sha256": "d924cba9f09e2c2ef137a07cdbd68699d1ce6ff9873fd95dcfc7c6a0111005ed",
}
HELPERS = {
    "local_producer.py": "c83f8f2b6bd9e5d17723b3f335f5fc5a1da40a20aab78862a8b6299abef9586e",
    "local_producer_source.py": "90a3e3ce04843fd4e0a096fe42e1322c22688c340356016a12f3f5536767aca3",
    "simulator_entitlements.py": "aa1cfcd4f371dd25a637bc56ab281ef94f8bcdcc2bb415b9125dd0b0aa0b27a8",
}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_helpers(source):
    source = Path(source)
    require(source.is_absolute() and source.resolve() == source,
            "canonical_App14_source_required")
    head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=20, check=True).stdout.strip()
    require(head == APP_SOURCE, "exact_original_App14_source_required")
    root = source / "Tools/MiniApps"
    for name, expected in HELPERS.items():
        path = root / name
        require(path.is_file() and not path.is_symlink() and path.resolve() == path
                and digest(path) == expected, "original_companion_helper_changed:" + name)
    review = source / PREPARATION["path"]
    require(review.is_file() and not review.is_symlink()
            and digest(review) == PREPARATION["sha256"],
            "original_prepared_source_review_changed")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    loaded = {}
    for name in ("simulator_entitlements", "local_producer_source", "local_producer"):
        path = root / (name + ".py")
        existing = sys.modules.get(name)
        if existing is not None:
            require(Path(existing.__file__).resolve() == path,
                    "foreign_original_companion_helper:" + name)
            loaded[name] = existing
        else:
            specification = importlib.util.spec_from_file_location(name, path)
            value = importlib.util.module_from_spec(specification)
            sys.modules[name] = value
            specification.loader.exec_module(value)
            loaded[name] = value
        require(digest(Path(loaded[name].__file__)) == HELPERS[name + ".py"],
                "imported_original_companion_helper_changed:" + name)
    return loaded["local_producer"], loaded["simulator_entitlements"]


def admit(source, manifest_path, out, app, copy_command):
    """Return the original producer/module/root/inventory custody tuple.

    copy_command(argv, label, timeout) is the caller's owned command ledger.
    All source, build-log, signature and extracted-byte gates are the original
    compiled companion validator from the frozen App14 source.
    """
    source, manifest_path, out, app = map(Path, (source, manifest_path, out, app))
    require(manifest_path.is_absolute() and manifest_path.resolve() == manifest_path
            and manifest_path.is_file() and not manifest_path.is_symlink()
            and manifest_path.stat().st_size <= 8 * 1024**2,
            "bounded_original_companion_manifest_required")
    raw = manifest_path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PRODUCER_MANIFEST,
            "exact_current86_original_producer_manifest_required")
    original_manifest = json.loads(raw)
    require(original_manifest.get("producer_sha") == PRODUCER_SOURCE
            and original_manifest.get("archive_sha256") == PRODUCER_ARCHIVE,
            "current86_original_source_and_archive_required")
    producer_module, entitlements = load_helpers(source)
    original_root = manifest_path.parent
    original_inventory = producer_module.inventory(original_root)
    copied = out / "original-companion"
    require(not copied.exists(), "refuse_existing_companion_clone")
    copy_command(["cp", "-cRp", str(original_root), str(copied)],
                 "clone-original-companion86", 180)
    require(producer_module.inventory(original_root) == original_inventory
            == producer_module.inventory(copied),
            "original_current86_companion_changed_during_copy")
    copied_manifest = copied / manifest_path.name
    require(copied_manifest.read_bytes() == raw, "current86_manifest_copy_changed")
    pin = {
        "execution_origin": "local-mac", "run_id": None,
        "revision": PRODUCER_SOURCE, "repository": "davidpovarsky/hanlin-ai",
        "bundle_id": "com.itorah.hanlinminiapps",
        "local_manifest_path": str(copied_manifest),
        "local_manifest_sha256": PRODUCER_MANIFEST,
        "local_source_repository": str(SOURCE_REPOSITORY),
        "local_producer_preparation": dict(PREPARATION),
    }
    producer = producer_module.admit(source, out / "companion",
                                     out / "companion-evidence", pin)
    admitted = producer["source_admission"]
    require(admitted["status"] == "PASS_EXACT_PREPARED_PRODUCER_SOURCE"
            and admitted["verified_source_files"] == 7693
            and admitted["source_inventory_membership"] == "EXACT_ORIGINAL_DECLARATION"
            and admitted["producer_object_store_modified"] is False,
            "complete_original7693_prepared_source_required")
    info = plistlib.loads((app / "Info.plist").read_bytes())
    actual = entitlements.read_simulator_entitlements(app / info["CFBundleExecutable"])
    require(info["CFBundleIdentifier"] == "io.anytype.app"
            and "group.com.itorah.shared" in actual["entitlements"].get(
                "com.apple.security.application-groups", [])
            and any("anytype" in value.get("CFBundleURLSchemes", [])
                    for value in info.get("CFBundleURLTypes", [])),
            "actual_source_shared_group_and_return_scheme_required")
    require(manifest_path.read_bytes() == raw
            and producer_module.inventory(original_root) == original_inventory,
            "current86_original_changed_during_admission")
    record = {
        "protocol": "App14-original-MiniApps86-companion-v1",
        "status": "PASS_ORIGINAL_COMPILED_COMPANION_NOT_ACCEPTANCE",
        "appSourceCommit": APP_SOURCE, "originalManifestSHA256": PRODUCER_MANIFEST,
        "originalProducerSource": PRODUCER_SOURCE, "archiveSHA256": PRODUCER_ARCHIVE,
        "completeProducerInventory": original_inventory,
        "sourceAdmission": admitted, "helpers": dict(HELPERS),
        "actualSourceEntitlements": actual, "companionBuilds": 0, "tests": 0,
        "physicalSharing": "NOT_PROVEN_BY_SIMULATOR",
        "originalProducerAcceptanceClaimed": False,
    }
    (out / "companion-binding.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return producer, producer_module, original_root, original_inventory
