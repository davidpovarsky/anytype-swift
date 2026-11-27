"""Publish the reviewed CLOSED preparation on one owned, new sparse branch.

No App build, native invocation, simulator operation or shared cache mutation.
The owner already authorized scoped development commits and publication.
"""
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

BASE = "dc001f2f09c64997515b77147fca4bacbac31397"
BRANCH = "codex/chatgpt-wave15-wave2-native-renderer-hosted-20261127"
DONOR = Path("/mnt/development/projects/worktrees/anytype-wave2-native-core-hosted-20261127")
WT = Path("/mnt/development/projects/worktrees/anytype-wave2-native-renderer-hosted-20261127")
TOOLS = "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/native-renderer-hosted/"
DOCS = "docs/validation/20261127-wave2-native-renderer-hosted/"
RECEIPT = Path("/tmp/pinkha-wave2-native-renderer-hosted-source-20261127.json")
PINS = {
    "native_core_hosted_profile.py": "ebaf306487ba65e0119c728da676f22295e810806edc214237a31320322482e6",
    "combined_host_acceptance_app15.py": "8875e2b2a10ec5ba692bc37043c7260ac6d290df9208729be29b00d07071e566",
    "native-core-closed-profile.json": "3b2b39ac596c1a0237a9f1bba1781490dd5e91af541bb9785d8e3fb54a5d16b7",
    "prepare_renderer_hosted.py": "534a13315e1c423ad6ccf3b79811e99b172b4f6004d25c155ccfdf95697f91ea"
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def capacity():
    return {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize
            for p in ("/", "/mnt/development")}


def admit_capacity():
    result = capacity()
    # Parent-qualified bounded source phase: actual source+packet, a 16 MiB
    # Git increment allowance and 64 MiB source-operation margin. This neither
    # consumes nor modifies any compiler/native/runtime admission floor.
    require(source_budget is not None and min(result.values()) >= source_budget,
            "Measured source-only packet/Git/margin budget is unavailable; no cleanup")
    return result


def git(path, arguments, check=True, timeout=25):
    command = ["runuser", "-u", "ubuntu", "-g", "chatgpt-agent", "--", "git",
               "-c", "gc.auto=0", "-c", "maintenance.auto=false",
               "-c", "user.name=ChatGPT", "-c", "user.email=chatgpt@openai.com",
               "-C", str(path), *arguments]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    row = {"argv": command, "exitCode": result.returncode,
           "stdoutSHA256": sha(result.stdout), "stderr": result.stderr.decode(errors="replace")}
    if len(result.stdout) <= 16384:
        row["stdout"] = result.stdout.decode(errors="replace")
    report["commands"].append(row)
    require(not check or result.returncode == 0, "Git failed: " + " ".join(arguments))
    return result


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--packet", required=True, type=Path)
parser.add_argument("--packet-sha256", required=True)
args = parser.parse_args()
require(not RECEIPT.exists(), "Prior publication receipt must be preserved")
report = {
    "schema": "native-renderer-closed-source-publication/v1", "status": "RUNNING",
    "startedAt": time.time(), "base": BASE, "branch": BRANCH, "worktree": str(WT),
    "commands": [], "MacCommands": 0, "compilerInvocations": 0,
    "cacheWrites": 0, "nativeCalls": 0, "UIRuns": 0,
    "scope": "New downstream-owned Tools/docs only; no application source changes",
    "sourcePayloadLimitBytes": 1024 * 1024,
}
failure = None
source_budget = None
try:
    compressed = args.packet.read_bytes()
    require(sha(compressed) == args.packet_sha256, "Packet bytes changed")
    packet = json.loads(gzip.decompress(compressed))
    require(packet["schema"] == "native-renderer-closed-publication-packet/v1"
            and packet["base"] == BASE and packet["branch"] == BRANCH, "Unexpected publication basis")
    files = {}
    for name, record in packet["files"].items():
        require((name.startswith(TOOLS) or name.startswith(DOCS))
                and ".." not in Path(name).parts and not Path(name).is_absolute(),
                "Unexpected publication path")
        raw = base64.b64decode(record["base64"], validate=True)
        require(len(raw) == record["bytes"] and sha(raw) == record["sha256"], "Packet member changed")
        files[name] = raw
    payload = sum(map(len, files.values()))
    require(payload <= 1024 * 1024, "Packet exceeds the measured small-source envelope")
    for name, expected in PINS.items():
        require(sha(files[TOOLS + name]) == expected, "Wrong reviewed source: " + name)
    handoff = json.loads(files[DOCS + "handoff.json"])
    require(handoff["status"] == "SOURCE_REVIEWED_RUNTIME_CLOSED"
            and handoff["sourceDependency"] == BASE
            and handoff["readyForExecution"] is False, "Review/admission boundary changed")
    for item in handoff["reviews"]:
        require(sha(files[DOCS + item["path"]]) == item["sha256"], "Reviewed evidence bytes changed")
    require(set(handoff["files"]) == set(files) - {DOCS + "handoff.json"}, "Handoff inventory differs")
    for name, record in handoff["files"].items():
        require(record == {"bytes": len(files[name]), "sha256": sha(files[name])}, "Inventory mismatch")
    source_budget = payload + len(compressed) + 16 * 1024**2 + 64 * 1024**2
    report["sourceOperationBudget"] = {
        "materializedSourceBytes": payload, "uploadedPacketBytes": len(compressed),
        "gitIncrementAllowanceBytes": 16 * 1024**2, "sourceOperationMarginBytes": 64 * 1024**2,
        "requiredFreeBytes": source_budget,
        "authority": "Parent-qualified separate small-source phase after terminal old-source retirement; no build/runtime floor changed",
    }
    report.update(packetSHA256=args.packet_sha256, payloadBytes=payload,
                  fileCount=len(files), beforeCapacity=admit_capacity())
    require(not WT.exists(), "Existing worktree must be preserved")
    require(git(DONOR, ["rev-parse", "HEAD"]).stdout.decode().strip() == BASE, "Donor moved")
    require(git(DONOR, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout == b"", "Dirty donor")
    require(git(DONOR, ["show-ref", "--verify", "--quiet", "refs/heads/" + BRANCH], check=False).returncode == 1,
            "Existing branch must be preserved")
    for prefix in (TOOLS, DOCS):
        require(git(DONOR, ["ls-tree", "-r", "--name-only", BASE, "--", prefix]).stdout == b"",
                "Publication directory is not new")
    git(DONOR, ["worktree", "add", "--no-checkout", "-b", BRANCH, str(WT), BASE])
    require(sorted(p.name for p in WT.iterdir()) == [".git"], "New worktree is not empty")
    git(WT, ["sparse-checkout", "set", "--no-cone", "--skip-checks", "/AGENTS.md"])
    git(WT, ["read-tree", "-mu", "HEAD"])
    require(git(WT, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout == b"", "New sparse checkout changed")
    report["beforeWriteCapacity"] = admit_capacity()
    uid, gid = pwd.getpwnam("ubuntu").pw_uid, grp.getgrnam("chatgpt-agent").gr_gid
    for name, raw in sorted(files.items()):
        target = WT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        os.chmod(target, 0o644)
        os.chown(target, uid, gid)
        for parent in target.parents:
            if parent == WT:
                break
            os.chown(parent, uid, gid)
    git(WT, ["add", "--sparse", "--", *sorted(files)])
    git(WT, ["diff", "--cached", "--check"])
    require(set(git(WT, ["diff", "--cached", "--name-only"]).stdout.decode().splitlines()) == set(files),
            "Staged paths differ from the exact packet")
    report["beforeCommitCapacity"] = admit_capacity()
    git(WT, ["commit", "-m", "test(editor): select exact existing renderer suite through closed hosted consumer"])
    commit = git(WT, ["rev-parse", "HEAD"]).stdout.decode().strip()
    require(git(WT, ["rev-parse", "HEAD^"]).stdout.decode().strip() == BASE, "Wrong commit parent")
    require(git(WT, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout == b"", "Worktree is not clean")
    report.update(status="SOURCE_COMMITTED_RUNTIME_CLOSED_PENDING_PUSH", commit=commit,
                  tree=git(WT, ["rev-parse", "HEAD^{tree}"]).stdout.decode().strip(),
                  handoffSHA256=sha(files[DOCS + "handoff.json"]), worktreeClean=True,
                  finalCapacity=capacity())
except BaseException as error:
    failure = error
    report.update(status="FAIL_SOURCE_PUBLICATION", failure={"type": type(error).__name__, "message": str(error)})
finally:
    report["finishedAt"] = time.time()
    try:
        with RECEIPT.open("x") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    except BaseException as save_error:
        if failure is not None:
            failure.add_note("Secondary receipt write failure: " + repr(save_error))
        else:
            failure = save_error
print(json.dumps({k: v for k, v in report.items() if k != "commands"}, sort_keys=True))
if failure is not None:
    raise failure
