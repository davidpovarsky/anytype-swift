#!/usr/bin/env python3
"""Read-only source/retained-wire proof; never builds or executes native code."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

PACKET = "docs/pinkha/torah-integration/native-owned-annotation-contract-20261123"
FIXTURE = PACKET + "/native/core/application/owned_annotation_export_native_test.go"
BASE = "8e91cea2a09d958e83e7f7c670c82248fd87a077"
AUTHORED = "bdcf6a310d8b29c523584f7bcddbe6d76fe5d1e1"
ENDPOINT = "53b52d380c3a87d25275bb391367b37eb5428d3d"
ENDPOINT_PATH = "docs/pinkha/torah-integration/native-schema-endpoint-runtime-20261123/native/clientlibrary/service/annotation_schema_endpoint_native_test.go"
GENERATION = "f9b37d7809c08a100a10417a7f699302c758ca8f"
GENERATION_PATH = "docs/pinkha/torah-integration/native-annotation-schema-rpc-generation-20261122/generated-run-45101449367/original-rpc-generation.zip"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60)

def fields(raw):
    """Read the bounded retained messages using actual generated protobuf tags."""
    assert len(raw) <= 65536
    def varint(offset):
        value = 0
        for shift in range(0, 70, 7):
            assert offset < len(raw)
            byte = raw[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value, offset
        raise AssertionError("Overlong retained varint")
    result, offset = {}, 0
    while offset < len(raw):
        tag, offset = varint(offset)
        number, wire = tag >> 3, tag & 7
        assert number > 0
        if wire == 0:
            value, offset = varint(offset)
        elif wire == 2:
            size, offset = varint(offset)
            assert offset + size <= len(raw)
            value = raw[offset:offset + size]
            offset += size
        elif wire in (1, 5):
            size = 8 if wire == 1 else 4
            assert offset + size <= len(raw)
            value = raw[offset:offset + size]
            offset += size
        else:
            raise AssertionError("Unexpected retained wire type")
        result.setdefault(number, []).append(value)
    return result

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control-root", required=True, type=Path)
    parser.add_argument("--original-repository", required=True, type=Path)
    args = parser.parse_args()
    root, original = args.control_root.resolve(), args.original_repository.resolve()
    head = git(root, "rev-parse", "HEAD").decode().strip()
    repair = root / PACKET / "slice-a/readiness-repair"
    current = (root / FIXTURE).read_bytes()
    assert current == git(root, "show", "HEAD:" + FIXTURE)
    assert current == git(original, "show", AUTHORED + ":" + FIXTURE)
    proof = json.loads((repair / "FIXTURE_SOURCE_CORRESPONDENCE.json").read_bytes())
    assert sha(current) == proof["after_sha256"]
    old = git(original, "show", BASE + ":" + FIXTURE)
    assert sha(old) == proof["before_sha256"]

    helpers = (repair / "INSERTED_HELPERS.go.txt").read_text()
    assert current.decode().count(helpers) == 1
    inverse = current.decode().replace(helpers, "", 1)
    for before, after in reversed(json.loads((repair / "REPAIR_REPLACEMENTS.json").read_bytes())):
        assert inverse.count(after) == 1
        inverse = inverse.replace(after, before, 1)
    assert inverse.encode() == old

    endpoint = git(original, "show", ENDPOINT + ":" + ENDPOINT_PATH)
    assert sha(endpoint) == proof["original_endpoint_fixture_sha256"]
    text = endpoint.decode()
    start = text.index("func (f *endpointFixture) waitReadiness(")
    end = text.index("\nfunc (f *endpointFixture) noSchemaRoots(", start)
    expected = text[start:end].replace("endpointFixture", "ownedExportFixture")
    expected = expected.replace("waitReadiness", "waitSchemaReadiness")
    expected = expected.replace("endpointNoError", "ownedExportNoError")
    expected = expected.replace("through the endpoint", "by export setup").rstrip()
    start = helpers.index("func (f *ownedExportFixture) waitSchemaReadiness(")
    assert helpers[start:].rstrip() == expected
    for path in ("native/core/block/import/owned_annotation_archive.go",
                 "native/core/block/import/owned_annotation_archive_test.go",
                 "slice-a/run_native_archive.py"):
        assert (root / PACKET / path).read_bytes() == git(original, "show", BASE + ":" + PACKET + "/" + path)

    # Authenticate the generated field definitions; this is retained-data decoding,
    # not a fabricated native response or a generated client implementation.
    generation_zip = git(original, "show", GENERATION + ":" + GENERATION_PATH)
    assert sha(generation_zip) == "ec13df1db9405ffa42b2ef76ec1bda7988ecee8dff1c3fcb1fd01c556a7cf80e"
    with zipfile.ZipFile(io.BytesIO(generation_zip)) as archive:
        generated = archive.read("generated/candidate/native/pb/commands.pb.go")
    assert sha(generated) == "387d03d13946c9ee5ae03d8fbfac85600010b384d524b3d7dc001484590937e9"
    declared = {
        "RpcAnnotationSchemaRegisterResponse": {"Error": 1, "Registration": 2},
        "RpcAnnotationSchemaRegisterResponseError": {"Code": 1, "Description": 2},
        "RpcAnnotationSchemaRegistration": {"AppAdmitted": 3, "Creations": 4, "TypeApplyInvoked": 5, "TypeApplyReturned": 6},
        "RpcAnnotationSchemaCreation": {"Before": 1, "After": 2, "Invoked": 3, "ReturnedObjectId": 4},
        "RpcAnnotationSchemaNativeObservation": {"Disposition": 1, "ObjectId": 4},
    }
    source = generated.decode()
    for name, expected_tags in declared.items():
        body = re.search(r"type " + name + r" struct \{(.*?)\n\}", source, re.S).group(1)
        actual = {m.group(1): int(m.group(2)) for m in re.finditer(
            r"(?m)^\s+(\w+)\s+.*?\x60protobuf:\"(?:bytes|varint),(\d+),", body)}
        assert all(actual.get(key) == number for key, number in expected_tags.items())
    archive_raw = (root / PACKET / "endpoint-run-45108043207/original-native-schema-endpoint.zip").read_bytes()
    assert sha(archive_raw) == "ee97925cb570ffaee7f89f6eef09ab6c907a720228a91b664bcb5c4877e20035"
    precedent = json.loads((repair / "AUTHENTIC_REGISTRATION_PRECEDENT.json").read_bytes())
    observations = []
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        index = json.loads(archive.read("EVIDENCE_INDEX.json"))["files"]
        by_path = {row["path"]: row for row in index}
        for row in precedent["actual_wire_history"]:
            raw = archive.read(row["path"])
            assert len(raw) == row["bytes"] == by_path[row["path"]]["bytes"]
            assert sha(raw) == row["sha256"] == by_path[row["path"]]["sha256"]
            outer = fields(raw)
            error, registration = fields(outer[1][0]), fields(outer[2][0])
            creations = [fields(value) for value in registration.get(4, [])]
            actual = {
                "path": row["path"], "error_code": error.get(1, [0])[0],
                "error_description": error.get(2, [b""])[0].decode(),
                "app_admitted": bool(registration.get(3, [0])[0]),
                "creation_rows": len(creations),
                "invoked_creation_rows": sum(value.get(3, [0])[0] for value in creations),
                "type_apply_invoked": bool(registration.get(5, [0])[0]),
                "type_apply_returned": bool(registration.get(6, [0])[0]),
            }
            if row["path"] == "registration-00.pb":
                before, after = fields(creations[-1][1][0]), fields(creations[-1][2][0])
                actual.update(last_creation_before_disposition=before.get(1, [0])[0],
                              last_creation_after_disposition=after.get(1, [0])[0],
                              last_creation_returned_id_matches_before=creations[-1].get(4) == before.get(4))
            assert all(row[key] == value for key, value in actual.items())
            observations.append(actual)

    print(json.dumps({
        "status": "SOURCE_CORRESPONDENCE_PASS", "checkout_sha": head,
        "fixture_source_commit": AUTHORED, "fixture_sha256": sha(current),
        "exact_fixture_inverse": True, "actual_original_readiness_body_match": True,
        "archive_product_and_tests_unchanged": True, "original_driver_unchanged": True,
        "actual_generated_tag_definitions_authenticated": True,
        "actual_prior_wire_history": observations, "native_cases_reexecuted": 0,
        "current_export_leaves_qualified": 0, "current_archive_leaves_qualified": 0,
        "native_import_activated": False, "provider_called": False,
    }, indent=2))

if __name__ == "__main__":
    main()
