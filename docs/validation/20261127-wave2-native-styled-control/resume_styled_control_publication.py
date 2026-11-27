"""Resume only the owned source publication after exact diff-evidence encoding."""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import pwd
import grp
import subprocess
import time

BASE = "7380a797d13b279b6d19e43ade7af1929089b8ef"
BRANCH = "codex/chatgpt-wave15-wave2-native-styled-control-20261127"
WT = Path("/mnt/development/projects/worktrees/anytype-wave2-native-styled-control-20261127")
TOOLS = "Tools/CurrentAppleValidation/native_styled_closed/"
DOCS = "docs/validation/20261127-wave2-native-styled-control/"
OLD = Path("/var/lib/sentinelx/uploads/uploads/native-styled-closed-20261127/packet-8228.json.gz")
OLD_SHA = "8228adab10e68c9d59c293d9282141e2964d265b2d979ddd8b0f79c84236c815"
OLD_RECEIPT = Path("/tmp/pinkha-wave2-native-styled-control-source-20261127.json")
OLD_RECEIPT_SHA = "abbfa0b717bc200fd88ffc09022492e8f0c8ac2a88ad8f902f8104c0b0ce2008"
RECEIPT = Path("/tmp/pinkha-wave2-native-styled-control-source-resume-20261127.json")
DIFFS = ["runtime-post-popen-cleanup.diff", "runtime-owned-registry.diff", "generated-owned-registry-runner.diff"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def capacity():
    return {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in ("/", "/mnt/development")}


def admit():
    actual = capacity()
    require(min(actual.values()) >= report["requiredSourceOnlyFreeBytes"], "Source-only budget unavailable")
    return actual


def git(arguments, check=True):
    argv = ["runuser", "-u", "ubuntu", "-g", "chatgpt-agent", "--", "git",
            "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "user.name=ChatGPT",
            "-c", "user.email=chatgpt@openai.com", "-C", str(WT), *arguments]
    result = subprocess.run(argv, capture_output=True, timeout=25)
    row = {"argv": argv, "exitCode": result.returncode, "stdoutSHA256": sha(result.stdout),
           "stderr": result.stderr.decode(errors="replace")}
    if len(result.stdout) <= 16384:
        row["stdout"] = result.stdout.decode(errors="replace")
    report["commands"].append(row)
    require(not check or result.returncode == 0, "Git failed: " + " ".join(arguments))
    return result.stdout


def packet(path, expected):
    raw = path.read_bytes()
    require(sha(raw) == expected, "Exact packet changed")
    data = json.loads(gzip.decompress(raw))
    require(data["schema"] == "native-styled-closed-publication-packet/v1"
            and data["base"] == BASE and data["branch"] == BRANCH, "Wrong source basis")
    files = {}
    for name, item in data["files"].items():
        require((name.startswith(TOOLS) or name.startswith(DOCS))
                and ".." not in Path(name).parts and not Path(name).is_absolute(), "Wrong source path")
        content = base64.b64decode(item["base64"], validate=True)
        require(len(content) == item["bytes"] and sha(content) == item["sha256"], "Member changed")
        files[name] = content
    return raw, files


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--packet", required=True, type=Path)
parser.add_argument("--packet-sha256", required=True)
args = parser.parse_args()
require(not RECEIPT.exists(), "Retain any previous resume attempt")
report = {"schema": "native-styled-source-publication-resume/v1", "status": "RUNNING",
          "startedAt": time.time(), "base": BASE, "branch": BRANCH, "worktree": str(WT),
          "priorFailureReceiptSHA256": OLD_RECEIPT_SHA, "priorPacketSHA256": OLD_SHA,
          "commands": [], "AppleBuilds": 0, "UIRuns": 0, "nativeCalls": 0, "cacheWrites": 0}
failure = None
try:
    prior = OLD_RECEIPT.read_bytes()
    require(sha(prior) == OLD_RECEIPT_SHA and json.loads(prior)["status"] == "FAIL_SOURCE_PUBLICATION",
            "Original failed publication changed")
    old_raw, old = packet(OLD, OLD_SHA)
    new_raw, new = packet(args.packet, args.packet_sha256)
    payload = sum(map(len, new.values()))
    require(payload <= 1024**2, "Source payload exceeds original1MiB envelope")
    report.update(packetSHA256=args.packet_sha256, payloadBytes=payload, fileCount=len(new),
                  requiredSourceOnlyFreeBytes=payload + len(new_raw) + 16 * 1024**2 + 64 * 1024**2)
    report["beforeCapacity"] = admit()
    require(git(["rev-parse", "HEAD"]).decode().strip() == BASE, "Source head changed")
    require(git(["branch", "--show-current"]).decode().strip() == BRANCH, "Wrong owned branch")
    require(set(git(["diff", "--cached", "--name-only"]).decode().splitlines()) == set(old), "Staged ownership changed")
    require(git(["diff", "--name-only"]) == b"", "Unstaged changes must be preserved")
    require(git(["ls-files", "--others", "--exclude-standard"]) == b"", "Untracked work must be preserved")
    for name, raw in old.items():
        require((WT / name).read_bytes() == raw, "Prior staged bytes changed: " + name)
    require({n: r for n, r in old.items() if n.startswith(TOOLS)}
            == {n: r for n, r in new.items() if n.startswith(TOOLS)}, "Reviewed executable source changed")
    removed = set(old) - set(new)
    require(removed == {DOCS + name for name in DIFFS}, "Unexpected removal")
    encoded = json.loads(new[DOCS + "retained-exact-diffs.json"])
    for name in DIFFS:
        item = encoded["members"][name]
        require(item["utf8"].encode() == old[DOCS + name]
                and sha(old[DOCS + name]) == item["sha256"], "Original reviewed diff not exactly retained")
    handoff = json.loads(new[DOCS + "handoff.json"])
    require(handoff["status"] == "SOURCE_REVIEWED_RUNTIME_CLOSED" and not handoff["readyForExecution"], "Admission changed")
    require(set(handoff["files"]) == set(new) - {DOCS + "handoff.json"}, "Inventory differs")
    for name, item in handoff["files"].items():
        require(item == {"bytes": len(new[name]), "sha256": sha(new[name])}, "Handoff member differs")
    for item in handoff["reviews"]:
        name = DOCS + item["path"]
        require(new[name] == old[name] and sha(new[name]) == item["sha256"], "Independent review changed")
    report["changedPaths"] = sorted(n for n in set(old) | set(new) if old.get(n) != new.get(n))
    report["beforeWriteCapacity"] = admit()
    uid, gid = pwd.getpwnam("ubuntu").pw_uid, grp.getgrnam("chatgpt-agent").gr_gid
    for name in sorted(removed):
        (WT / name).unlink()  # Exact owned new copies; original bytes retained above and in old packet.
    for name, raw in new.items():
        if old.get(name) == raw:
            continue
        target = WT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        os.chmod(target, 0o644)
        os.chown(target, uid, gid)
        for parent in target.parents:
            if parent == WT:
                break
            os.chown(parent, uid, gid)
    git(["add", "--sparse", "-A", "--", TOOLS, DOCS])
    git(["diff", "--cached", "--check"])
    require(set(git(["diff", "--cached", "--name-only"]).decode().splitlines()) == set(new), "Final stage inventory differs")
    report["beforeCommitCapacity"] = admit()
    git(["commit", "-m", "test(ui): prepare closed native styled acceptance with owned command custody"])
    require(git(["rev-parse", "HEAD^"]).decode().strip() == BASE, "Commit ancestry changed")
    require(git(["status", "--porcelain=v1", "--untracked-files=all"]) == b"", "Worktree is not clean")
    report.update(status="SOURCE_COMMITTED_RUNTIME_CLOSED_PENDING_PUSH",
                  commit=git(["rev-parse", "HEAD"]).decode().strip(),
                  tree=git(["rev-parse", "HEAD^{tree}"]).decode().strip(),
                  handoffSHA256=sha(new[DOCS + "handoff.json"]), finalCapacity=capacity(),
                  reviewedExecutableBytesUnchanged=True, worktreeClean=True)
except BaseException as error:
    failure = error
    report.update(status="FAIL_SOURCE_PUBLICATION_RESUME", failure={"type": type(error).__name__, "message": str(error)})
finally:
    report["finishedAt"] = time.time()
    try:
        with RECEIPT.open("x") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    except BaseException as save_error:
        if failure is not None:
            failure.add_note("Secondary receipt save failure: " + repr(save_error))
        else:
            failure = save_error
print(json.dumps({k: v for k, v in report.items() if k != "commands"}, sort_keys=True))
if failure is not None:
    raise failure
