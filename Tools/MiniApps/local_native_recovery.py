"""Admit byte-exact recovered native inputs without claiming a missing transport ZIP.

The original native command/source/receipt and every real payload byte remain
mandatory. This route is local-only and keeps the historical original paths.
It neither recompiles native code nor converts recovery into runtime acceptance.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import tarfile

REVIEW = "Tools/MiniApps/native70f_recovery.json"
SCHEMA = "miniapps.original-native-recovery/1"
SOURCE = "6f1194f9b8c9540dea1187826dda6a256777dbbf"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def regular(root, relative, expected):
    part = PurePosixPath(relative)
    require(not part.is_absolute() and ".." not in part.parts and str(part) == relative,
            "Noncanonical recovered native member")
    path = root / relative
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and path.stat().st_size == expected["bytes"] and sha(path) == expected["sha256"],
            "Recovered original native member differs: " + relative)
    return path


def validate_review(value, policy, app):
    require(value.get("schema") == SCHEMA and value.get("original_evidence_source") == SOURCE
            and value.get("source_manifest_sha256") == policy["source_manifest_sha256"]
            and value.get("original_simulator_zip_sha256") == policy["archive_sha256"]
            and value.get("original_simulator_zip_status") == "MISSING_NOT_VERIFIED"
            and value.get("new_native_tests_executed") == 0
            and value.get("new_build_claimed") is False,
            "Recovered input cannot relabel source, archive or native acceptance")
    root = Path(value["recovery_root"])
    require(root == app.parent / "materialization/native70f-recovery"
            and root.is_absolute() and root.resolve() == root and not root.is_symlink(),
            "Unowned native recovery directory")
    expected = {
        "simulator": "/Users/m1/builds/pinkha-dual-native-v1-70f0b2a66286-simulator",
        "device": "/Users/m1/builds/pinkha-dual-native-v1-70f0b2a66286-device",
    }
    require(value.get("original_roots") == expected and policy["root"] == expected["simulator"],
            "Original native root identity changed")
    return root


def admit(app, policy):
    app = Path(app)
    binding = policy.get("recovered_input")
    require(policy.get("schema") == "miniapps.original-local-native/3"
            and isinstance(binding, dict) and set(binding) == {"path", "sha256"}
            and binding["path"] == REVIEW, "Unreviewed recovered native input binding")
    path = app / REVIEW
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and sha(path) == binding["sha256"], "Committed native recovery review differs")
    original = subprocess.check_output(["git", "-c", "gc.auto=0", "-C", str(app), "show", "HEAD:" + REVIEW])
    require(original == path.read_bytes(), "Recovery review is not the actual committed source")
    value = json.loads(original)
    root = validate_review(value, policy, app)
    inventory_row = value["original_evidence_inventory"]
    inventory_path = regular(app, inventory_row["path"], inventory_row)
    raw_inventory = subprocess.check_output(["git", "-c", "gc.auto=0", "-C", str(app),
        "show", SOURCE + ":" + inventory_row["path"]])
    require(raw_inventory == inventory_path.read_bytes(),
            "Recovered proof lost its original committed evidence inventory")
    inventory = json.loads(raw_inventory)
    require(len(inventory) == 151, "Incomplete original native proof membership")
    archive = regular(root, value["original_evidence_archive"]["path"], value["original_evidence_archive"])
    with tarfile.open(archive, "r:gz") as stream:
        members = [entry for entry in stream.getmembers() if entry.isfile()]
        require(len(members) == len(inventory) and {entry.name for entry in members} == set(inventory)
                and all(entry.isfile() or entry.isdir() for entry in stream.getmembers()),
                "Original raw proof archive membership changed")
        for entry in members:
            data = stream.extractfile(entry).read()
            require({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} == inventory[entry.name],
                    "Original native proof archive bytes differ: " + entry.name)
            regular(root, entry.name, inventory[entry.name])
    source_archive = regular(root, value["original_source_archive"]["path"], value["original_source_archive"])
    require(sha(source_archive) == policy["source_archive_sha256"], "Recovered original source archive differs")
    from local_native_input import exact_files
    payloads = {}
    for role in ("simulator", "device"):
        directory = root / role
        expected = json.loads((directory / "framework-files.json").read_bytes())
        require(len(expected) == 10, "Original native slice inventory is incomplete")
        payloads[role] = exact_files(directory / "Lib.xcframework", expected)
        regular(directory, "native-source.tar.gz", value["original_source_archive"])
        manifest = directory / "source/source-manifest.json"
        require(sha(manifest) == policy["source_manifest_sha256"],
                "Recovered original native source manifest differs")
        require(not (directory / "Lib.xcframework.zip").exists()
                and not (directory / "Lib.xcframework.zip").is_symlink(),
                "A replacement ZIP cannot be presented as the missing original transport")
    return {"status": "EXACT_ORIGINAL_PAYLOAD_AND_PROOF_RECOVERED_TRANSPORT_MISSING",
            "review_sha256": binding["sha256"], "original_evidence_source": SOURCE,
            "original_raw_proof_archive_sha256": sha(archive),
            "original_source_archive_sha256": sha(source_archive),
            "original_simulator_zip_sha256": policy["archive_sha256"],
            "original_simulator_zip_status": "MISSING_NOT_VERIFIED",
            "original_roots": value["original_roots"],
            "recovered_roots": {role: str(root / role) for role in ("simulator", "device")},
            "raw_evidence_members_verified": len(inventory),
            "original_slice_payloads": payloads, "new_native_tests_executed": 0,
            "new_build_claimed": False}


def recovered_receipt(original_path, recovery):
    original_path = Path(original_path)
    matches = []
    for role, original in recovery["original_roots"].items():
        base = Path(original)
        if original_path.is_relative_to(base):
            matches.append(Path(recovery["recovered_roots"][role]) / original_path.relative_to(base))
    require(len(matches) == 1, "Receipt is outside the exact original recovered native roots")
    path = matches[0]
    require(path.resolve() == path and not path.is_symlink() and path.is_file(),
            "Recovered original receipt is absent or aliased")
    return path
