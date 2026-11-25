"""Relocate only verified artifact paths in an owned SwiftPM cache clone."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re

def require(value, message):
    if not value:
        raise RuntimeError(message)

def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def inventory(root):
    root = root.resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            require(path.resolve().is_relative_to(root), "Artifact symlink escapes its own root")
            rows.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            rows.append({"path": relative, "kind": "file", "bytes": path.stat().st_size,
                         "sha256": digest(path), "mode": path.stat().st_mode & 0o777})
        else:
            require(path.is_dir(), "Special file in copied artifact")
    require(rows, "Copied artifact is empty")
    return rows

def relocate(root, seed, derived, evidence, work):
    root, seed, derived, evidence, work = map(Path, (root, seed, derived, evidence, work))
    donor = seed.parents[2]
    old_derived = seed.with_name("producer-derived")
    metadata = derived / "SourcePackages/workspace-state.json"
    original = metadata.read_bytes()
    require(original == (seed / "SourcePackages/workspace-state.json").read_bytes(),
            "Private cache metadata differs before path relocation")
    state = json.loads(original)
    rows = state["object"]["artifacts"]
    require(isinstance(rows, list) and rows, "No copied artifact metadata")
    proofs = []
    for row in rows:
        source_path = Path(row["path"])
        if row.get("source", {}).get("type") == "remote":
            prefix = next((p for p in (old_derived, seed) if source_path.is_relative_to(p)), None)
            require(prefix is not None, "Unreviewed donor artifact path")
            relative = source_path.relative_to(prefix)
            require(relative.parts[:2] == ("SourcePackages", "artifacts")
                    and ".." not in relative.parts, "Unexpected donor artifact namespace")
            checksum = row["source"].get("checksum", "")
            require(re.fullmatch(r"[0-9a-f]{64}", checksum) is not None,
                    "Missing original remote artifact checksum")
            original_artifact, target = seed / relative, derived / relative
        else:
            require(row.get("source") == {"type": "local"}
                    and row.get("targetName") == "Lib"
                    and row["packageRef"]["identity"] == "protobufmessages"
                    and source_path == donor / "Dependencies/Middleware/Lib.xcframework",
                    "Unreviewed local artifact relocation")
            original_artifact = source_path
            target = root / "Dependencies/Middleware/Lib.xcframework"
            old_location = row["packageRef"]["location"]
            require(old_location == str(donor / "Modules/ProtobufMessages"),
                    "Original native module path differs")
            row["packageRef"]["location"] = str(root / "Modules/ProtobufMessages")
        require(original_artifact.is_dir() and target.is_dir()
                and not original_artifact.is_symlink() and not target.is_symlink(),
                "Missing or aliased retained/copied artifact")
        before_files = inventory(original_artifact)
        require(inventory(target) == before_files, "Copied artifact bytes/modes differ from retained source")
        row["path"] = str(target)
        proofs.append({"target": row["targetName"], "original_metadata_path": str(source_path),
                       "verified_donor_path": str(original_artifact), "owned_path": str(target),
                       "source": row["source"], "files": before_files})
    output = (json.dumps(state, indent=2, sort_keys=True) + "\n").encode()
    (evidence / "swiftpm-workspace-state.before.json").write_bytes(original)
    (evidence / "swiftpm-workspace-state.relocated.json").write_bytes(output)
    metadata.write_bytes(output)
    # PIFCache is generated metadata with absolute paths, not a product. Preserve
    # the complete private copy and make Xcode regenerate it against current paths.
    pif = derived / "Build/Intermediates.noindex/XCBuildData/PIFCache"
    retired = None
    if pif.exists():
        pif_files = inventory(pif)
        retained = work / "retained-seed-build-metadata/PIFCache"
        require(not retained.exists(), "Refusing to overwrite retained PIF metadata")
        retained.parent.mkdir(parents=True)
        pif.rename(retained)
        retired = {"retained_path": str(retained), "files": pif_files}
    proof = {"status": "VERIFIED_PRIVATE_CACHE_PATHS_RELOCATED",
             "source_donor_unchanged": True, "grants_product_acceptance": False,
             "workspace_before_sha256": hashlib.sha256(original).hexdigest(),
             "workspace_after_sha256": hashlib.sha256(output).hexdigest(),
             "artifacts": proofs, "retained_pif": retired}
    (evidence / "swiftpm-artifact-path-relocation.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    return {"artifact_count": len(proofs), "source_donor_unchanged": True,
            "proof_sha256": digest(evidence / "swiftpm-artifact-path-relocation.json"),
            "grants_product_acceptance": False}

def verify_resolved_paths(root, derived, evidence):
    root, derived, evidence = map(Path, (root, derived, evidence))
    metadata = derived / "SourcePackages/workspace-state.json"
    state = json.loads(metadata.read_bytes())
    absolute_paths = []
    def visit(value, key):
        if isinstance(value, dict):
            for name, item in value.items():
                visit(item, key + "/" + name)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                visit(item, key + "/" + str(i))
        elif isinstance(value, str) and value.startswith("/"):
            path = Path(value)
            require(path.exists() and path.resolve().is_relative_to(root.resolve()),
                    "Resolved SwiftPM path is missing or outside the current owned source: " + key)
            absolute_paths.append({"key": key, "path": value})
    visit(state, "")
    require(absolute_paths, "No actual resolved artifact/dependency paths")
    proof = {"status": "ALL_RESOLVED_ABSOLUTE_PATHS_CURRENT_AND_PRESENT",
             "workspace_sha256": digest(metadata), "paths": absolute_paths,
             "grants_product_acceptance": False}
    (evidence / "swiftpm-current-path-admission.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    return proof
