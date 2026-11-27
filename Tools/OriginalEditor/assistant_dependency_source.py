"""Bind the original assistant source and its exact added package closure.

A reviewed source/lock transition grants no resolver, compiler or runtime credit.
The ordinary original native resolver must still reproduce all committed pins.
"""
import hashlib
import json
from pathlib import Path
import subprocess

OWNER = "ae86bf287a9df4fee32ea4c1a76c6eb78cadbb01"
BASE = "f145d6205b3ca7c8eb947779c6a1fa130246b93b"
HANLIN = "9bcdecfc829d446a773a78b249e894e204b1bcaa"
ROUTE = "Tools/Hanlin/assistant_component_route.json"
PIN = "Tools/Hanlin/source.json"
LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
ADDED = frozenset({"bitbytedata", "eventsource", "swcompression", "swift-nio",
                   "swift-sdk", "swift-system", "swift-tree-sitter",
                   "tree-sitter", "tree-sitter-bash"})
OWNED_INPUTS = (
    ROUTE, PIN, LOCK, "Tools/Hanlin/prepare_sdk.py",
    "Tools/Hanlin/assistant_native_artifacts.json", "Modules/Logger/Package.swift",
    "Anytype.xcodeproj/project.pbxproj",
    "Tools/OriginalEditor/SharedRuntime/verify_framework_ownership.py",
)

def require(value, message):
    if not value:
        raise ValueError(message)

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60)

def validate_pin_transition(before, after, transition):
    def indexed(document, count):
        rows = document.get("pins", [])
        require(len(rows) == count, "Original assistant pin inventory differs")
        values = {row["identity"]: row for row in rows}
        require(len(values) == len(rows), "Repeated original dependency identity")
        return values
    left, right = indexed(before, 58), indexed(after, 67)
    require(set(right) - set(left) == ADDED and not set(left) - set(right),
            "Unreviewed added or removed original dependency")
    changed = {key for key in set(left) & set(right) if left[key] != right[key]}
    require(changed == {"swift-log"}, "Unreviewed original shared dependency changed")
    require(transition["beforePinCount"] == 58 and transition["afterPinCount"] == 67
            and transition["retainedPinCount"] == 57
            and set(transition["added"]) == ADDED
            and set(transition["changed"]) == {"swift-log"},
            "Original assistant closure review differs")
    require({key: right[key] for key in ADDED} == transition["added"]
            and transition["changed"]["swift-log"] == {
                "before": left["swift-log"], "after": right["swift-log"]},
            "Original assistant exact package revision or requirement differs")
    require(right["swift-log"]["state"] == {
                "revision": "96a2f8a0fa41e9e09af4585e2724c4e825410b91", "version": "1.6.2"},
            "Original shared Logging pin differs")
    return {"retained": 57, "added": sorted(ADDED), "changed": ["swift-log"],
            "current_pin_count": 67, "resolver_acceptance": "NOT_GRANTED_BY_SOURCE_REVIEW"}

def observe(root, binding):
    root = Path(root).resolve()
    expected = git(root, "show", OWNER + ":" + ROUTE)
    require(binding == {"path": ROUTE, "sha256": hashlib.sha256(expected).hexdigest(),
                        "owner_source": OWNER, "hanlin_source": HANLIN},
            "Unreviewed original assistant source binding")
    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", OWNER, "HEAD"],
                   check=True, timeout=60)
    observed = {}
    for name in OWNED_INPUTS:
        path = root / name
        require(path.is_file() and not path.is_symlink() and path.resolve() == path,
                "Missing or aliased original assistant source: " + name)
        data = path.read_bytes()
        require(data == git(root, "show", OWNER + ":" + name)
                and git(root, "hash-object", "--", name).strip()
                    == git(root, "rev-parse", "HEAD:" + name).strip(),
                "Original assistant source differs from reviewed owner: " + name)
        observed[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    route = json.loads(expected)
    require(route["schemaVersion"] == 1
            and route["hanlinSourceRevision"] == HANLIN
            and route["owner"] == "AnytypeOriginalEditor"
            and route["product"] == "HanlinAssistantCapabilities"
            and route["originalAppTargetUnchanged"] is True,
            "Original assistant implementation owner differs")
    source = json.loads((root / PIN).read_text())
    require(source["revision"] == HANLIN
            and source["assistantCapabilities"]["layout"] == "nested"
            and source["assistantCapabilities"]["product"] == route["product"],
            "Original assistant package source differs")
    before = git(root, "show", BASE + ":" + LOCK)
    after = (root / LOCK).read_bytes()
    transition = route["dependencyLock"]
    require(hashlib.sha256(before).hexdigest() == transition["beforeSHA256"]
            and hashlib.sha256(after).hexdigest() == transition["afterSHA256"],
            "Original exact lock bytes differ")
    pins = validate_pin_transition(json.loads(before), json.loads(after), transition)
    return {"schema": "anytype.original-assistant-dependency-source/1",
            "owner_source": OWNER, "hanlin_source": HANLIN,
            "source_inputs": observed, "package_transition": pins,
            "compiled_or_live_acceptance": "NOT_GRANTED_BY_SOURCE_REVIEW"}
