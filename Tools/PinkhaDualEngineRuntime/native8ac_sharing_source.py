"""One exact additive sharing UI donor, independently bound through Git trees."""
import base64
import hashlib
import json
from pathlib import Path

DONOR = "dec2ecbb19ff6dab720866ef5a973058c47c7e91"
RELATIVE = "NativeApp/UITests/NativeLaunchTests.swift"
PINS = {
    "NativeLaunchTests.swift": "0b4cbd0663162801ed09f146fd531cc225539c7a6886317f4d9021fbff345b00",
    "git-path-proof.json": "1eb9cf9ff92fac74596a1c377c7b03969df38f140d649e3cdbe04cc8fe523843",
    "owner-sharing-ui-addition.swift": "918a91cf02250a1fdaa8b91ca570ebb64406f154988dffed0fcb90552292ad81",
    "source-addition.json": "d5af4e645339ff3ba924e6676c9ccff43aa558ac427882d3e9cec51e2cce3273",
}
SPEC = {"donorCommit": DONOR, "appSourceCommit": "379ca3568f247d2fc218ed63df24796d461713c0",
        "originalSHA256": "f7056f6f64144dffb9bca8420f543cf7ec78b2cc1b502e40b6c56abdc9dc0e95",
        "compiledSHA256": PINS["NativeLaunchTests.swift"], "additionSHA256": PINS["owner-sharing-ui-addition.swift"],
        "gitPathProofSHA256": PINS["git-path-proof.json"], "sourceProofSHA256": PINS["source-addition.json"],
        "additionOffset": 182918, "additionBytes": 7433, "applicationSourceChanges": 0,
        "originalMethodBytesUnchanged": True, "scope": "owner-invitation-confirm-cancel-revoke-cold-ui-only"}

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def qualify_bytes(original, files):
    require(set(files) == set(PINS), "exact_four_sharing_donor_inputs_required")
    require(all(sha(files[name]) == expected for name, expected in PINS.items()), "sharing_donor_bytes_changed")
    require(sha(original) == SPEC["originalSHA256"], "original_complete_NativeUI_source_required")
    candidate = files["NativeLaunchTests.swift"]
    addition = files["owner-sharing-ui-addition.swift"]
    offset = SPEC["additionOffset"]
    require(candidate[offset:offset+len(addition)] == addition and candidate.count(addition) == 1
            and candidate[:offset] + candidate[offset+len(addition):] == original,
            "sharing_addition_must_restore_every_original_byte")
    identity = json.loads(files["source-addition.json"])
    require(identity["compiledCandidateSHA256"] == sha(candidate)
            and identity["originalSHA256"] == sha(original)
            and identity["additionSHA256"] == sha(addition)
            and identity["offset"] == offset and identity["bytes"] == len(addition)
            and identity["inverseRestoresEveryOriginalByte"] is True
            and identity["applicationSourceChanges"] == identity["actualAppleTests"] == 0,
            "original_additive_sharing_source_proof_required")
    proof = json.loads(files["git-path-proof.json"])
    require(proof["commit"] == DONOR and proof["path"] == RELATIVE
            and proof["protocol"] == "pinkha-exact-git-commit-tree-file-v1", "exact_sharing_Git_commit_required")
    used = set()
    def object_bytes(oid, kind):
        row = proof["objects"][oid]
        require(row["kind"] == kind, "Git_object_kind_changed")
        data = base64.b64decode(row["rawBase64"], validate=True)
        require(hashlib.sha1((kind+" "+str(len(data))).encode()+b"\0"+data).hexdigest() == oid,
                "Git_object_identity_changed")
        used.add(oid)
        return data
    commit = object_bytes(DONOR, "commit")
    tree = commit.splitlines()[0].decode()
    require(tree.startswith("tree "), "original_Git_commit_tree_required")
    tree = tree[5:]
    trace = []
    components = RELATIVE.split("/")
    for index, component in enumerate(components):
        data = object_bytes(tree, "tree")
        position, found = 0, []
        while position < len(data):
            space = data.index(b" ", position)
            nul = data.index(b"\0", space)
            require(nul+21 <= len(data), "truncated_Git_tree")
            mode, name = data[position:space].decode(), data[space+1:nul].decode()
            oid = data[nul+1:nul+21].hex()
            position = nul+21
            if name == component:
                found.append((mode, oid))
        require(len(found) == 1, "unique_exact_Git_path_component_required")
        mode, oid = found[0]
        require(mode == ("100644" if index == len(components)-1 else "40000"), "Git_path_kind_changed")
        trace.append({"tree": tree, "component": component, "mode": mode, "object": oid})
        tree = oid
    require(set(proof["objects"]) == used and trace == proof["trace"] and tree == proof["blob"],
            "complete_exact_Git_path_required")
    require(hashlib.sha1(("blob "+str(len(candidate))).encode()+b"\0"+candidate).hexdigest() == tree
            and proof["fileSHA256"] == sha(candidate), "actual_Git_blob_must_equal_compiled_source")
    return candidate, dict(SPEC)

def load_source(source):
    root = Path(__file__).resolve().with_name("native-sharing-dec2-source")
    require(root.is_dir() and not root.is_symlink(), "closed_sharing_donor_directory_required")
    files = {}
    for name in PINS:
        path = root/name
        require(path.is_file() and not path.is_symlink() and root in path.resolve().parents,
                "closed_regular_sharing_donor_file_required")
        files[name] = path.read_bytes()
    return qualify_bytes((source/RELATIVE).read_bytes(), files)
