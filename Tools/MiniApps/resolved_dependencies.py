"""Bind Xcode's generated resolution files to the actual source and original macro."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

LOCKS = (
    "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
    "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcworkspace/xcshareddata/swiftpm/Package.resolved",
)
MACRO = {
    "identity": "equatable",
    "location": "https://github.com/ordo-one/equatable",
    "version": "1.4.1",
    "revision": "597c2bb34af0c51331eb3b5e705f942d8ee20daa",
    "target": "EquatableMacros",
}
ACTIVATION_ARGUMENTS = ["-skipMacroValidation"]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(app, *arguments):
    return subprocess.check_output(["git", "-C", str(app), *arguments])


def changed_paths(app):
    return sorted(git(app, "diff", "--name-only", "HEAD").decode().splitlines())


def canonical_location(value):
    return value.removesuffix("/").removesuffix(".git")


def lock_pins(data):
    value = json.loads(data)
    require(value.get("version") in (2, 3), "Unexpected Xcode resolution schema")
    pins = value.get("pins")
    require(isinstance(pins, list) and pins, "The actual resolved dependency graph is empty")
    result = {pin["identity"]: pin for pin in pins}
    require(len(result) == len(pins), "Duplicate resolved package identity")
    return result


def verify_macro(derived, pins):
    pin = pins.get(MACRO["identity"], {})
    require(canonical_location(pin.get("location", "")) == MACRO["location"]
            and pin.get("state", {}).get("version") == MACRO["version"]
            and pin.get("state", {}).get("revision") == MACRO["revision"],
            "The actual Equatable resolution differs from the original 1.4.1 source")
    checkout = Path(derived) / "SourcePackages/checkouts/equatable"
    require(checkout.is_dir(), "The original macro source checkout is missing")
    require(git(checkout, "rev-parse", "HEAD").decode().strip() == MACRO["revision"],
            "Macro checkout differs from the recorded resolved commit")
    require(not git(checkout, "diff", "--name-only", "HEAD").strip(),
            "The macro source checkout has tracked edits")
    manifests = {path.name: digest(path.read_bytes()) for path in sorted(checkout.glob("Package*.swift"))}
    require(manifests and any(MACRO["target"] in path.read_text() for path in checkout.glob("Package*.swift")),
            "The approved macro target is absent from its source manifest")
    return {**MACRO, "source_tree": git(checkout, "rev-parse", "HEAD^{tree}").decode().strip(),
            "manifest_sha256": manifests}


def record_resolution(app, evidence, derived, source_sha, run_id, run_attempt, stage, *, activation_arguments=None):
    app, evidence = Path(app), Path(evidence)
    require(stage in ("native", "ui"), "Unknown resolution stage")
    activation_arguments = ACTIVATION_ARGUMENTS if activation_arguments is None else activation_arguments
    require(activation_arguments in ([], ACTIVATION_ARGUMENTS), "Unreviewed macro activation")
    require(git(app, "rev-parse", "HEAD").decode().strip() == source_sha, "Resolution source changed")
    changes = changed_paths(app)
    require(set(changes) <= set(LOCKS), "Resolution changed application source outside declared lock files")
    previous_path = evidence / "dependency-resolution.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else None
    if previous:
        require(stage == "ui" and previous["stage"] == "native", "Unexpected resolution reuse")
        for item in previous["locks"]:
            require(digest((app / item["path"]).read_bytes()) == item["resolved_sha256"],
                    "UI resolution changed an already compiled native dependency lock")
    folder = evidence / "dependency-resolution" / stage
    folder.mkdir(parents=True, exist_ok=False)
    locks = []
    all_pins = {}
    for index, relative in enumerate(LOCKS):
        path = app / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        pins = lock_pins(data)
        for identity, pin in pins.items():
            if identity in all_pins:
                prior = all_pins[identity]
                require(pin["state"] == prior["state"]
                        and canonical_location(pin.get("location", "")) == canonical_location(prior.get("location", "")),
                        "Native and UI resolve different source for " + identity)
            all_pins[identity] = pin
        snapshot = folder / (str(index) + "-resolved.json")
        snapshot.write_bytes(data)
        tracked = bool(git(app, "ls-files", "--", relative).strip())
        original = git(app, "show", "HEAD:" + relative) if tracked else None
        original_path = folder / (str(index) + "-original.json")
        if original is not None:
            original_path.write_bytes(original)
        locks.append({"path": relative, "resolved_sha256": digest(data),
                      "resolved_snapshot": str(snapshot.relative_to(evidence)),
                      "original_sha256": digest(original) if original is not None else None,
                      "original_snapshot": str(original_path.relative_to(evidence)) if original is not None else None,
                      "pin_count": len(pins)})
    require(locks and locks[0]["path"] == LOCKS[0], "The native project's actual resolved lock is missing")
    macro = verify_macro(derived, all_pins)
    proof = {
        "status": "PINNED_MACRO_AND_RESOLUTION_RECORDED", "stage": stage,
        "source_sha": source_sha, "run_id": str(run_id), "run_attempt": str(run_attempt),
        "generated_tracked_deltas": changes, "locks": locks, "macro": macro,
        "activation_arguments": activation_arguments,
        "source_integrity": "TRACKED_RESOLUTION_DELTA_RECORDED" if changes else "TRACKED_SOURCE_CLEAN",
    }
    (folder / "tracked-resolution.patch").write_bytes(git(app, "diff", "HEAD", "--", *LOCKS))
    encoded = json.dumps(proof, indent=2) + "\n"
    (folder / "receipt.json").write_text(encoded)
    previous_path.write_text(encoded)
    return proof


def verify_recorded_resolution(app, evidence, derived, source_sha, run_id, run_attempt, *, activation_arguments=None):
    app, evidence = Path(app), Path(evidence)
    activation_arguments = ACTIVATION_ARGUMENTS if activation_arguments is None else activation_arguments
    require(activation_arguments in ([], ACTIVATION_ARGUMENTS), "Unreviewed macro activation")
    proof = json.loads((evidence / "dependency-resolution.json").read_text())
    require(proof["status"] == "PINNED_MACRO_AND_RESOLUTION_RECORDED"
            and proof["source_sha"] == source_sha and proof["run_id"] == str(run_id)
            and proof["run_attempt"] == str(run_attempt),
            "Generated dependency resolution is not bound to this source/run")
    changes = changed_paths(app)
    require(changes == proof["generated_tracked_deltas"] and set(changes) <= set(LOCKS),
            "Tracked source changed beyond its declared resolution delta")
    pins = {}
    for item in proof["locks"]:
        relative = item["path"]
        require(relative in LOCKS, "Unexpected generated dependency lock")
        actual = (app / relative).read_bytes()
        require(digest(actual) == item["resolved_sha256"]
                and (evidence / item["resolved_snapshot"]).read_bytes() == actual,
                "Actual resolved dependency bytes changed after build")
        if item["original_sha256"] is not None:
            original = git(app, "show", "HEAD:" + relative)
            require(digest(original) == item["original_sha256"]
                    and (evidence / item["original_snapshot"]).read_bytes() == original,
                    "Recorded original dependency lock differs from source")
        pins.update(lock_pins(actual))
    require(verify_macro(derived, pins) == proof["macro"]
            and proof["activation_arguments"] == activation_arguments,
            "Approved macro source/activation changed after build")
    return proof
