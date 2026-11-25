"""Admit a released, genuinely qualified owned cache for compilation only.

The original source/distribution remain immutable. Current source, original ABI,
compiler, API, binary import and runtime gates still execute independently.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
POLICY = HERE / "MiniApps/qualified_cache_seed.json"

def require(value, message):
    if not value:
        raise RuntimeError(message)

def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def read_exact(root, row):
    path = root / row["path"]
    require(path.resolve() == path and path.is_file() and not path.is_symlink(),
            "Qualified cache proof is missing or aliased")
    require(sha(path) == row["sha256"], "Qualified cache proof bytes changed")
    return json.loads(path.read_text())

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def verify(root, seed, before, installation, evidence):
    root, seed, evidence = map(lambda p: Path(p).resolve(), (root, seed, evidence))
    policy = json.loads(POLICY.read_text())
    require(policy["schema"] == "otzaria.qualified-compiler-cache/1",
            "Unknown qualified compiler cache policy")
    donor = Path(policy["root"])
    require(donor.resolve() == donor and donor != root
            and seed == donor / policy["seed_relative_path"] and seed.is_dir(),
            "Cache is not the reviewed released producer")
    require(git(donor, "rev-parse", "HEAD") == policy["source_sha"]
            and not git(donor, "diff", "--name-only", "HEAD"),
            "Original qualified source is no longer frozen")
    proofs = {name: read_exact(donor, row) for name, row in policy["proofs"].items()}
    qualified, execution = proofs["qualification"], proofs["execution"]
    require(qualified["status"] == execution["status"]
            == "ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS"
            and qualified["original_framework_build"] == execution["original_framework_build"] == "PASS"
            and qualified["external_consumer_build"] == execution["external_consumer_build"] == "PASS"
            and qualified["source_sha"] == execution["source_sha"] == policy["source_sha"],
            "Cache producer lacks the original complete qualification")
    original = proofs["source_before"]
    require(original == proofs["source_after"]
            and original["head_sha"] == policy["source_sha"]
            and qualified["execution_identity"] == execution["execution_identity"]
            == original["execution_identity"],
            "Qualified cache source/execution binding differs")
    require(qualified["shared_runtime_ownership"]["status"]
            == "PASS_OBSERVED_SINGLE_SHARED_IMPLEMENTATIONS",
            "Qualified cache lacks observed binary ownership")
    descriptor = proofs["descriptor"]
    identity = original["execution_identity"]
    require(descriptor == identity["local_execution"]
            and policy["proofs"]["descriptor"]["sha256"] == identity["local_execution_sha256"],
            "Original genuine execution identity differs")
    env = dict(os.environ)
    for key in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        env.pop(key, None)
    env.update(OTZARIA_LOCAL_EXECUTION=str(donor / policy["proofs"]["descriptor"]["path"]),
               OTZARIA_LOCAL_EXECUTION_SHA256=policy["proofs"]["descriptor"]["sha256"],
               PYTHONDONTWRITEBYTECODE="1")
    probe = ("import json,sys; from pathlib import Path; "
             "sys.path.insert(0,sys.argv[1]+'/Tools/OriginalEditor'); "
             "from framework_profile import source_observation; "
             "print(json.dumps(source_observation(Path(sys.argv[1])),sort_keys=True))")
    actual_original = json.loads(subprocess.check_output(
        [os.sys.executable, "-B", "-c", probe, str(donor)], env=env, text=True))
    require(actual_original == original, "Frozen original source no longer matches qualification")
    for key in ("original_trees", "framework_facade_sources", "public_host_contract_sha256"):
        require(before[key] == original[key], "New current framework changed beyond reviewed shared packages: " + key)
    for relative in ("Anytype.xcodeproj/project.pbxproj",
                     "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
                     "OriginalEditorFramework"):
        require(git(root, "rev-parse", "HEAD:" + relative)
                == git(donor, "rev-parse", "HEAD:" + relative),
                "Original project, lock or facade changed beyond cache reuse scope")
    require(qualified["heart"]["lib_files"] == installation["lib_files"]
            and qualified["heart"]["abi_reuse"]["donor_source_sha"]
            == installation["abi_reuse"]["donor_source_sha"]
            == policy["native_abi_source_sha"],
            "Current SDK uses a different original native ABI")
    old_shared = json.loads((donor / "Dependencies/Hanlin/.pinkha-source.json").read_text())
    new_shared = json.loads((root / "Dependencies/Hanlin/.pinkha-source.json").read_text())
    require(old_shared["revision"] == policy["previous_hanlin"]
            and new_shared["revision"] == policy["current_hanlin"],
            "Shared package source revision differs from reviewed correction")
    changed = sorted(p for p in set(old_shared["files"]) | set(new_shared["files"])
                     if old_shared["files"].get(p) != new_shared["files"].get(p))
    require(changed == policy["changed_shared_files"],
            "Shared package delta exceeds the reviewed original correction")
    relative = "Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor"
    expected = proofs["distribution"]["files"][relative]
    binary = seed / "Build/Products/Debug-Anytype-iphonesimulator/AnytypeOriginalEditor.framework/AnytypeOriginalEditor"
    require(binary.is_file() and sha(binary) == expected["sha256"],
            "Retained producer binary differs from its qualified distribution")
    result = {"status": "QUALIFIED_OWNED_CACHE_INPUT_ONLY", "source_root": str(donor),
              "source_sha": policy["source_sha"], "seed": str(seed),
              "policy_sha256": sha(POLICY), "proofs": policy["proofs"],
              "current_source_sha": before["head_sha"], "shared_files_to_recompile": changed,
              "native_abi_source_sha": policy["native_abi_source_sha"],
              "new_sdk_acceptance_granted": False, "native_tests_rerun": False}
    (evidence / "qualified-cache-input.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result

def relocate_git(seed, derived, evidence):
    """Rebase copied Git alternates only after complete object-store equality."""
    seed, derived, evidence = map(Path, (seed, derived, evidence))
    old_derived = seed.with_name("producer-derived")
    records = []
    verified = {}
    for path in sorted((derived / "SourcePackages/checkouts").glob("*/.git/objects/info/alternates")):
        require(not path.is_symlink() and path.resolve().is_relative_to(derived.resolve()),
                "Aliased copied Git metadata")
        relative = path.relative_to(derived)
        original = path.read_bytes()
        require(original == (seed / relative).read_bytes(), "Copied Git alternates changed before admission")
        target_lines = []
        for line in original.decode().splitlines():
            old = Path(line)
            prefix = next((p for p in (seed, old_derived) if old.is_relative_to(p)), None)
            require(prefix is not None, "Unreviewed Git alternate outside released cache")
            suffix = old.relative_to(prefix)
            require(suffix.parts[:2] == ("SourcePackages", "repositories")
                    and suffix.parts[-1] == "objects" and ".." not in suffix.parts,
                    "Unexpected Git object store")
            retained, copied = seed / suffix, derived / suffix
            if str(suffix) not in verified:
                def members(folder):
                    require(folder.is_dir() and not folder.is_symlink(), "Missing copied Git object store")
                    rows = {}
                    for member in folder.rglob("*"):
                        require(not member.is_symlink(), "Aliased copied Git object")
                        require(member.is_dir() or member.is_file(), "Special copied Git object")
                        if member.is_file():
                            rows[member.relative_to(folder).as_posix()] = (member.stat().st_size, sha(member))
                    return rows
                left, right = members(retained), members(copied)
                require(left and left == right, "Copied Git objects differ from the released cache")
                verified[str(suffix)] = {"files": len(left), "inventory_sha256":
                    hashlib.sha256(json.dumps(left, sort_keys=True).encode()).hexdigest()}
            target_lines.append(str(copied))
        output = ("\n".join(target_lines) + "\n").encode()
        mode = path.stat().st_mode & 0o777
        path.chmod(mode | 0o200)
        path.write_bytes(output)
        path.chmod(mode)
        records.append({"path": relative.as_posix(), "original_text": original.decode(),
                        "before_sha256": hashlib.sha256(original).hexdigest(),
                        "after_sha256": hashlib.sha256(output).hexdigest(), "mode": mode})
    require(records, "No copied Git checkout alternates were admitted")
    result = {"status": "VERIFIED_PRIVATE_GIT_ALTERNATES_RELOCATED", "source_donor_unchanged": True,
              "metadata": records, "object_stores": verified, "grants_product_acceptance": False}
    (evidence / "qualified-cache-git-relocation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
