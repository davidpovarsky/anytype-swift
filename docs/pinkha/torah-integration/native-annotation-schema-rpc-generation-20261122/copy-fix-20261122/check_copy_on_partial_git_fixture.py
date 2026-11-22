#!/usr/bin/env python3
"""Exercise only the checkout copier against a real local partial Git fixture."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
helper = root / "packet/copy_materialized_checkout.py"
owned = Path(tempfile.mkdtemp(prefix="partial-git-copy-control-", dir=root))
record = {"scope": "Local Git preparation controls only; no product, generator, native or app execution.",
          "helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(), "commands": []}
env = os.environ.copy()
env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"})
env.pop("GIT_NO_LAZY_FETCH", None)


def run(label, argv, cwd, expected=0):
    done = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    record["commands"].append({"label": label, "argv": [str(x) for x in argv], "returncode": done.returncode,
                               "stdout": done.stdout.decode(), "stderr": done.stderr.decode()})
    if expected is not None:
        assert done.returncode == expected, (label, done.returncode, done.stderr.decode())
    return done.stdout.decode().strip()


try:
    record["git_version"] = run("git-version", ["git", "--version"], owned)
    remote = owned / "local-origin"
    remote.mkdir()
    run("init", ["git", "init", "--initial-branch=fixture"], remote)
    (remote / "keep").mkdir()
    (remote / "omit").mkdir()
    (remote / "keep/input.txt").write_bytes(b"materialized original bytes\n")
    (remote / "omit/unfetched.bin").write_bytes(b"unmaterialized original bytes\n" * 1000)
    run("stage", ["git", "add", "."], remote)
    run("commit", ["git", "-c", "user.name=Local preparation fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "Isolated partial Git fixture"], remote)
    head = run("head", ["git", "rev-parse", "HEAD"], remote)
    run("allow-filter", ["git", "config", "uploadpack.allowFilter", "true"], remote)
    source = owned / "partial-input"
    run("partial-clone", ["git", "clone", "--filter=blob:none", "--no-checkout", remote.as_uri(), str(source)], owned)
    run("sparse-scope", ["git", "sparse-checkout", "set", "--no-cone", "/keep/"], source)
    run("materialize", ["git", "checkout", "--detach", head], source)
    env["GIT_NO_LAZY_FETCH"] = "1"
    missing_before = run("missing-before", ["git", "rev-list", "--objects", "--missing=print", "HEAD"], source)
    assert any(line.startswith("?") for line in missing_before.splitlines())
    assert not (source / "omit/unfetched.bin").exists()
    # The source remote is now unavailable, so a hidden fetch cannot rescue a copy.
    remote.rename(owned / "origin-offline")
    run("old-local-clone-diagnostic", ["git", "clone", "--no-hardlinks", "--no-checkout", str(source), str(owned / "old-copy")], owned, expected=None)
    old_error = record["commands"][-1]["stderr"]
    old_clone_code = record["commands"][-1]["returncode"]
    assert old_clone_code in (0, 128)
    old_failure_reproduced = old_clone_code == 128 and "promisor" in old_error and "lazy fetching disabled" in old_error
    copies = {}
    for lane in ("baseline", "candidate"):
        target = owned / lane
        receipt = owned / (lane + ".json")
        run(lane + "-copy", [sys.executable, "-I", str(helper), "--source", str(source), "--target", str(target), "--expected-head", head, "--receipt", str(receipt)], owned)
        copies[lane] = json.loads(receipt.read_bytes())
    assert copies["baseline"]["inventory_sha256"] == copies["candidate"]["inventory_sha256"]
    assert run("missing-after", ["git", "rev-list", "--objects", "--missing=print", "HEAD"], source) == missing_before
    original = (source / "keep/input.txt").read_bytes()
    (owned / "candidate/keep/input.txt").write_bytes(b"owned candidate mutation\n")
    assert (source / "keep/input.txt").read_bytes() == original
    assert (owned / "baseline/keep/input.txt").read_bytes() == original
    alternate = source / ".git/objects/info/alternates"
    alternate.parent.mkdir(parents=True, exist_ok=True)
    alternate.write_text(str(owned / "origin-offline/.git/objects") + "\n")
    rejected = owned / "rejected-copy"
    run("reject-alternates", [sys.executable, "-I", str(helper), "--source", str(source), "--target", str(rejected), "--expected-head", head, "--receipt", str(owned / "rejected.json")], owned, expected=1)
    assert not rejected.exists()
    assert "shared or alternate Git storage is refused" in record["commands"][-1]["stderr"]
    record.update({"status": "LOCAL_GIT_PREPARATION_CONTROLS_PASS", "copies": copies,
                   "old_failure_reproduced": old_failure_reproduced,
                   "old_clone_diagnostic_scope": "This local Git/fixture is not the original Actions environment; its clone outcome does not override the retained actual failure.",
                   "unfetched_blob_remained_unfetched": True,
                   "candidate_mutation_isolated": True, "shared_storage_rejected_before_target_creation": True,
                   "native_or_generator_executions": 0})
except BaseException as error:
    record.update({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)})
    raise
finally:
    shutil.rmtree(owned)
    record["owned_fixture_removed"] = not owned.exists()
    (root / "LOCAL_PARTIAL_GIT_COPY_CONTROLS.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: value for key, value in record.items() if key not in ("commands", "copies")}))
