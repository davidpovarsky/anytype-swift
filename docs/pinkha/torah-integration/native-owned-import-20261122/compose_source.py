"""Compose only the three frozen, reviewed owned-import source layers.

The seven existing preimages are byte-bound to the already observed original
module compile. This script creates a proposal; it never touches a checkout.
"""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
OUT = ROOT / "composition"
OUT.mkdir(exist_ok=True)


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


preimages = json.loads((ROOT / "PREIMAGE_COMPILED_SOURCE_BINDING.json").read_bytes())
assert preimages["status"] == "PASS_EXACT_PREIMAGE_MATCH_TO_PRIOR_ACTUAL_MODULE_COMPILE"
preimages = {entry["path"]: entry for entry in preimages["source_preimages"]}
layers = [
    (ROOT / "candidate/SOURCE_MANIFEST.json", ROOT / "candidate/native", "owned-uploader"),
    (ROOT / "import-layer/SOURCE_MANIFEST.json", ROOT / "import-layer/candidate/native", "owned-importer"),
    (ROOT / "provider-admission/SOURCE_MANIFEST.json", ROOT / "provider-admission/candidate/native", "owned-provider-observation"),
]
selected = {}
for manifest, native, name in layers:
    for entry in json.loads(manifest.read_bytes()):
        source = native / entry["path"]
        data = source.read_bytes()
        actual = identity(data)
        assert actual["bytes"] == entry["bytes"] and actual["sha256"] == entry["sha256"]
        if entry["path"] in selected:
            assert entry["path"] == "core/block/import/owned_import_dependencies.go"
            assert selected[entry["path"]]["identity"]["sha256"] == entry["preimage_sha256"]
        selected[entry["path"]] = {"source": source, "data": data, "identity": actual, "layer": name}

assert len(selected) == 15
rows, patch = [], []
for path, value in sorted(selected.items()):
    data = value["data"]
    target = OUT / "native" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    before = b""
    preimage = preimages.get(path)
    if preimage:
        before = (WORKSPACE / preimage["local_path"]).read_bytes()
        assert identity(before)["sha256"] == preimage["sha256"]
    rows.append({"path": path, **value["identity"], "source_layer": value["layer"],
                 "source_path": str(value["source"].relative_to(WORKSPACE)),
                 "preimage": identity(before) if preimage else None})
    patch.extend(difflib.unified_diff(before.decode().splitlines(True), data.decode().splitlines(True),
        fromfile="a/" + path if before else "/dev/null", tofile="b/" + path))
assert len([r for r in rows if r["preimage"]]) == 7
(OUT / "SOURCE_MANIFEST.json").write_text(json.dumps(rows, indent=2) + "\n")
(OUT / "owned-import.patch").write_text("".join(patch))
(OUT / "COMPOSITION.json").write_text(json.dumps({
    "status": "SOURCE_ONLY_NO_ACTIVATION",
    "source_files": 15, "existing_preimages": 7, "new_files": 8,
    "source_layers": [{"path": str(manifest.relative_to(WORKSPACE)), **identity(manifest.read_bytes())} for manifest, _, _ in layers],
    "original_heart": "d98420b1113536afd08cde6de9a5816f6d27ffff",
    "required_compatible_origin_commit": "13f63c2dff32ff8ca6b864748843822fcdd0d004",
    "required_compatible_origin_tree": "90cc6f5adbbcc9f01f38b24766378d38adc0f453",
    "preimage_actual_compile_run": 45047489968,
    "ordinary_request_and_constructor_unchanged": True,
    "r14_remap_and_mapping_capture_bodies_unchanged": True,
    "source_conflict_resolution": "Only owned_import_dependencies.go takes the reviewed provider-admission afterimage. All other exact frozen files are copied unchanged.",
    "native_import_route_enabled": False,
    "account_lifetime_admission_enabled": False,
    "body_or_ack_authority": False,
}, indent=2) + "\n")
print(json.dumps({"files": len(rows), "manifest": identity((OUT / "SOURCE_MANIFEST.json").read_bytes()),
                  "patch": identity((OUT / "owned-import.patch").read_bytes())}))
