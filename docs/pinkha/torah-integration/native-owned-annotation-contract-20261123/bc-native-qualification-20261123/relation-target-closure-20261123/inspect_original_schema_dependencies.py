#!/usr/bin/env python3
"""Inspect authenticated original protobuf export metadata; no native execution."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess
import zipfile

ROOT = Path("/mnt/development/projects/diagnostics/otzaria-native-schema-closure-repair-20261123/45270881714")
HEART = Path("/mnt/development/projects/worktrees/anytype-original-import-rpc-generation-ci-prep-20261123/build/Import-RPC-Inputs/heart")

def varint(raw, offset):
    value = 0
    for shift in range(0, 70, 7):
        assert offset < len(raw)
        byte = raw[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError("Oversized protobuf varint")

def fields(raw):
    assert len(raw) <= 4 * 1024**2
    result = {}
    offset = 0
    while offset < len(raw):
        tag, offset = varint(raw, offset)
        number, kind = tag >> 3, tag & 7
        assert number > 0
        if kind == 0:
            value, offset = varint(raw, offset)
        elif kind in (1, 2, 5):
            if kind == 2:
                size, offset = varint(raw, offset)
            else:
                size = 8 if kind == 1 else 4
            assert size <= len(raw) - offset
            value = raw[offset:offset + size]
            offset += size
        else:
            raise ValueError("Unsupported protobuf wire type")
        result.setdefault(number, []).append((kind, value))
    return result

def message(raw, field, optional=False):
    rows = fields(raw).get(field, [])
    if optional and not rows:
        return b""
    assert len(rows) == 1 and rows[0][0] == 2
    return rows[0][1]

def string_value(raw):
    return message(raw, 3).decode()

def snapshot_details(raw):
    # Exact original declarations: SnapshotWithType.snapshot=2;
    # Change.Snapshot.data=2; SmartBlockSnapshotBase.details=2.
    data = message(message(raw, 2), 2)
    details = {}
    for kind, entry in fields(message(data, 2)).get(1, []):
        assert kind == 2
        key = message(entry, 1).decode()
        assert key not in details
        details[key] = message(entry, 2)
    return data, details

def target_types(details):
    raw = details.get("relationFormatObjectTypes")
    if raw is None:
        return []
    values = fields(message(raw, 6)).get(1, [])
    assert all(kind == 2 for kind, _ in values)
    return [string_value(value) for _, value in values]

def differences(left, right, path=""):
    if type(left) is not type(right):
        return [{"path": path, "source": left, "target": right}]
    if isinstance(left, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                result.append({"path": path + "/" + key, "source": left.get(key), "target": right.get(key)})
            else:
                result.extend(differences(left[key], right[key], path + "/" + key))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [{"path": path, "source": left, "target": right}]
        return [item for i, (a, b) in enumerate(zip(left, right)) for item in differences(a, b, path + "/" + str(i))]
    return [] if left == right else [{"path": path, "source": left, "target": right}]

def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def inspect():
    original = subprocess.check_output(["sudo", "-u", "ubuntu", "-H", "git", "-C", str(HEART), "rev-parse", "HEAD"], text=True).strip()
    assert original == "d98420b1113536afd08cde6de9a5816f6d27ffff"
    receipt = json.loads((ROOT / "AUTHENTICATED_INTAKE.json").read_text())
    index = {row["path"]: row for row in receipt["verified_rows"]}
    def retained(name):
        raw = (ROOT / "selected" / name).read_bytes()
        assert identity(raw) == {key: index[name][key] for key in ("bytes", "sha256")}
        return raw
    specimens = {}
    failed_raw = None
    for name in ("text", "format", "nested", "attachment"):
        manifest = json.loads(retained("fixtures/source/" + name + "-manifest.json"))
        archive_path = ROOT / "selected/fixtures/source" / (name + ".zip")
        raw = retained("fixtures/source/" + name + ".zip")
        assert len(raw) == manifest["archive_bytes"] and hashlib.sha256(raw).hexdigest() == manifest["archive_sha256"]
        members = manifest["members"]
        ids = {row["object_id"] for row in members if row["kind"] == "snapshot"}
        dependencies = []
        with zipfile.ZipFile(archive_path) as archive:
            assert len(archive.namelist()) == len(set(archive.namelist()))
            assert set(archive.namelist()) == {row["name"] for row in members}
            assert archive.testzip() is None
            for row in members:
                raw = archive.read(row["name"])
                assert identity(raw) == {key: row[key] for key in ("bytes", "sha256")}
                if row["kind"] != "snapshot":
                    continue
                data, details = snapshot_details(raw)
                targets = target_types(details)
                if targets:
                    dependencies.append({"member": row["name"], "source_object_id": row["object_id"],
                        "source_key": message(data, 9, optional=True).decode(),
                        "target_ids": targets, "absent_exported_target_ids": [target for target in targets if target not in ids],
                        "raw_snapshot": identity(raw)})
                if name == "text" and row["unique_key"] == "iconImage":
                    failed_raw = {"target_ids": targets, "snapshot": identity(raw), "object_id": row["object_id"]}
        specimens[name] = {"archive": identity(archive_path.read_bytes()), "members_verified": len(members),
            "exported_type_keys": [row["unique_key"] for row in members if row["kind"] == "snapshot" and row["name"].startswith("types/")],
            "relation_target_dependencies": dependencies}
    diagnostic = json.loads(retained("fixtures/target-text/text-schema-comparison-diagnostic.json"))
    assert diagnostic["schema_key"] == "rel-iconImage" and diagnostic["normalized_source_status"] == diagnostic["normalized_target_status"] == "COMPLETE"
    assert failed_raw["object_id"] == diagnostic["source_object_id"]
    left = diagnostic["normalized_source_json_view"]
    right = diagnostic["normalized_target_json_view"]
    normalized_source = target_types(snapshot_details(base64.b64decode(diagnostic["normalized_source_protobuf"]))[1])
    normalized_target = target_types(snapshot_details(base64.b64decode(diagnostic["normalized_target_protobuf"]))[1])
    assert normalized_source == ["_missing_object"] and failed_raw["target_ids"] != normalized_source
    code_rows = []
    for name in ("core/block/export/collection.go", "core/block/object/objectcreator/relation.go",
                 "core/block/import/common/common.go", "pb/protos/snapshot.proto", "pb/protos/changes.proto",
                 "pkg/lib/pb/model/protos/models.proto", "pkg/lib/bundle/relations.json"):
        raw = subprocess.check_output(["sudo", "-u", "ubuntu", "-H", "git", "-C", str(HEART), "show", original + ":" + name])
        assert raw == (HEART / name).read_bytes()
        code_rows.append(dict(path=name, **identity(raw)))
    return {"schema": 1, "status": "AUTHENTIC_ORIGINAL_METADATA_DIAGNOSIS_ONLY", "native_execution": "NOT_RUN",
        "run": 45270881714, "source": "c6b4ebd03d25433b8a47073d84e2efa874c777ec",
        "original_heart": original, "original_source_rows": code_rows,
        "source_snapshot_before_normalization": failed_raw,
        "actual_normalized_source_target_ids": normalized_source,
        "actual_normalized_target_target_ids": normalized_target,
        "complete_json_view_differences": differences(left, right),
        "specimens": specimens,
        "causal_contract": [
            "Original objectcreator converts bundled target-type URLs to per-Space derived object IDs.",
            "Original derived exporter gathers type, targetObjectType and setOf but does not follow relationFormatObjectTypes after adding relations.",
            "The original strict comparison remaps only authenticated archive member identities.",
            "Original getNewObjectsIDForRelation maps an unmapped non-bundled CID to _missing_object; the raw exported source snapshot still contains its real CID."
        ],
        "repair_scope": "Close selected relation target-type dependencies through the original collector until the existing processed-ID set has no unseen target. No type names, CID mapping, comparator relaxation or source mutation."}

if __name__ == "__main__":
    result = inspect()
    destination = Path(__file__).with_name("AUTHENTIC_SCHEMA_DEPENDENCY_DIAGNOSIS.json")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"path": str(destination), **identity(destination.read_bytes()),
        "differences": result["complete_json_view_differences"],
        "missing": {name: [row for row in value["relation_target_dependencies"] if row["absent_exported_target_ids"]] for name, value in result["specimens"].items()}}, indent=2))
