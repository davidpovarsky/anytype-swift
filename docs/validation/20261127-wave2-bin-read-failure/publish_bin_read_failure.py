"""Publish the exact reviewed Bin failure correction and focused model tests.

This bounded source operation neither compiles nor invokes Native or a simulator.
"""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json, os, pwd, grp, subprocess, time
from pathlib import Path

BASE = "2207b131f45d305ba828c93deb0633e275e59cba"
BRANCH = "codex/chatgpt-wave15-wave2-bin-read-failure-20261127"
DONOR = Path("/mnt/development/projects/worktrees/anytype-wave2-attachment-storage-20261127")
DONOR_HEAD = "99f6194b41a030e2e164610913798d2d857cecdf"
WT = Path("/mnt/development/projects/worktrees/anytype-wave2-bin-read-failure-20261127")
SOURCE = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyLibraryPresentation.swift"
TEST_SOURCE = "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift"
VIEW_SOURCE = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryView.swift"
DOCS = "docs/validation/20261127-wave2-bin-read-failure/"
OLD = "f0675b0d2a0842ad87670640d5242da82c354aab96056c1b6d23ca8540b3dc17"
NEW = "3dd7517d2ecba44fe7568b16ed005a97489929f4a248c1899ad3d1c1864e66d4"
TEST_OLD = "e46dc67553d9e050c7955958cff56aac559c4d51eaa3b75e379029dd83f8d839"
TEST_NEW = "b242b8bdbe9f2c9c10c742d26ffe88b237b797b28dfd600e07b85f4e3c2a5494"
VIEW_OLD = "af2b406c5cf80f126e9684a0cc4bb673658329925188e264aa9746eeba4926c0"
VIEW_NEW = "3791fe7ccadbf5caf4d1a82b1f6cc8d497b5562db1c58ba346803a9ebf43fec1"
SOURCES = {SOURCE: (OLD, NEW), TEST_SOURCE: (TEST_OLD, TEST_NEW), VIEW_SOURCE: (VIEW_OLD, VIEW_NEW)}
GATE_PATH = "Tools/AnyEnginePort/verify_source_retention.py"
GATE_SHA = "f69d6a465db0517c5b41143c9b54aa275ecc6cbc63de6e9d20bc074d98feabf0"
PREFIX = Path("/tmp/pinkha-wave2-bin-read-failure-20261127")
RECEIPT = PREFIX.with_name(PREFIX.name + "-publication.json")
GATE_RESULT = PREFIX.with_name(PREFIX.name + "-source-retention.json")


def sha(value): return hashlib.sha256(value).hexdigest()
def pin(value): return {"bytes": len(value), "sha256": sha(value)}
def require(value, reason):
    if not value: raise RuntimeError(reason)
def encoded(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
def capacity():
    return {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in ("/", "/mnt/development")}
def admit_capacity():
    state = capacity()
    require(source_budget is not None and min(state.values()) >= source_budget,
            "Measured source-only packet/Git/margin budget is unavailable; no cleanup")
    return state
def git(path, args, check=True, timeout=25):
    argv = ["runuser", "-u", "ubuntu", "-g", "chatgpt-agent", "--", "git",
            "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "user.name=ChatGPT",
            "-c", "user.email=chatgpt@openai.com", "-C", str(path), *args]
    result = subprocess.run(argv, capture_output=True, timeout=timeout)
    row = {"argv": argv, "exitCode": result.returncode,
           "stdoutSHA256": sha(result.stdout), "stderr": result.stderr.decode(errors="replace")}
    if len(result.stdout) <= 16384: row["stdout"] = result.stdout.decode(errors="replace")
    report["commands"].append(row)
    require(not check or result.returncode == 0, "Git failed: " + " ".join(args))
    return result


p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--packet", type=Path, required=True)
p.add_argument("--packet-sha256", required=True)
args = p.parse_args()
require(not RECEIPT.exists() and not GATE_RESULT.exists(), "Retain prior publication/evidence")
report = {"schema": "wave2-bin-read-failure-source-publication/v1", "status": "RUNNING",
          "startedAt": time.time(), "base": BASE, "branch": BRANCH, "worktree": str(WT),
          "commands": [], "compilerInvocations": 0, "compilerCacheWrites": 0,
          "nativeCalls": 0, "simulatorOperations": 0, "scope": "Bin failure model/List correction, two focused test methods and source evidence"}
failure = None
source_budget = None
try:
    data = args.packet.read_bytes()
    require(sha(data) == args.packet_sha256, "Packet bytes changed")
    packet = json.loads(gzip.decompress(data))
    require(packet["schema"] == "native-bin-read-failure-source-packet/v1" and
            packet["base"] == BASE and packet["branch"] == BRANCH, "Unexpected source basis")
    files = {}
    for name, record in packet["files"].items():
        require((name in SOURCES or name.startswith(DOCS)) and ".." not in Path(name).parts
                and not Path(name).is_absolute(), "Unexpected source-publication path")
        raw = base64.b64decode(record["base64"], validate=True)
        require(pin(raw) == {k: record[k] for k in ("bytes", "sha256")}, "Packet member changed")
        files[name] = raw
    for name, (old, new) in SOURCES.items():
        require(sha(files[name]) == new and
                sha(files[DOCS + "original/" + Path(name).name]) == old, "Frozen source/preimage changed")
    handoff = json.loads(files[DOCS + "handoff.json"])
    require(handoff["status"] == "SOURCE_REVIEWED_APP_RUNTIME_NOT_RUN" and handoff["base"] == BASE,
            "Source review/runtime boundary changed")
    for role in ("root", "torah"):
        name = "root-source-review.json" if role == "root" else "torah-independent-review.json"
        raw = files[DOCS + name]
        require(sha(raw) == handoff["sourceReviews"][role] and
                all(new in raw.decode() for _, new in SOURCES.values()), "Review changed")
    require(set(handoff["files"]) == set(files) - {DOCS + "handoff.json"}, "Inventory differs")
    for name, expected in handoff["files"].items(): require(pin(files[name]) == expected, "Inventory hash differs")
    payload = sum(map(len, files.values()))
    require(payload <= 1024 * 1024, "Source-only payload exceeds authorized envelope")
    source_budget = payload + len(data) + 16 * 1024**2 + 64 * 1024**2
    report["sourceOperationBudget"] = {"materializedSourceBytes": payload, "packetBytes": len(data),
        "gitIncrementAllowanceBytes": 16 * 1024**2, "sourceOperationMarginBytes": 64 * 1024**2,
        "requiredFreeBytes": source_budget, "runtimeOrCompilerFloorChanged": False}
    report.update(beforeCapacity=admit_capacity(), fileCount=len(files), payloadBytes=payload,
                  packetSHA256=args.packet_sha256)
    require(not WT.exists(), "Existing worktree must be preserved")
    require(git(DONOR, ["rev-parse", "HEAD"]).stdout.decode().strip() == DONOR_HEAD, "Owned donor moved")
    require(git(DONOR, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout == b"", "Dirty donor")
    require(git(DONOR, ["show-ref", "--verify", "--quiet", "refs/heads/" + BRANCH], check=False).returncode == 1,
            "Existing branch must be preserved")
    for name, (old, _) in SOURCES.items():
        require(sha(git(DONOR, ["show", BASE + ":" + name]).stdout) == old, "Actual immutable preimage differs")
    require(git(DONOR, ["ls-tree", "-r", "--name-only", BASE, "--", DOCS]).stdout == b"", "Evidence directory exists")
    git(DONOR, ["worktree", "add", "--no-checkout", "-b", BRANCH, str(WT), BASE])
    require(sorted(x.name for x in WT.iterdir()) == [".git"], "New worktree is not empty")
    git(WT, ["sparse-checkout", "set", "--no-cone", "--skip-checks", "/AGENTS.md", "/" + SOURCE,
             "/" + TEST_SOURCE, "/" + VIEW_SOURCE, "/" + GATE_PATH])
    git(WT, ["read-tree", "-mu", "HEAD"])
    require(git(WT, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout == b"", "Sparse checkout changed")
    for name, (old, _) in SOURCES.items():
        require(sha((WT / name).read_bytes()) == old, "Materialized source preimage differs")
    require(sha((WT / GATE_PATH).read_bytes()) == GATE_SHA, "Original retention gate differs")
    report["beforeWriteCapacity"] = admit_capacity()
    uid, gid = pwd.getpwnam("ubuntu").pw_uid, grp.getgrnam("chatgpt-agent").gr_gid
    for name, raw in sorted(files.items()):
        target = WT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if name in SOURCES:
            temporary = target.with_name(target.name + ".wave2-new")
            with temporary.open("xb") as stream: stream.write(raw)
            os.chmod(temporary, 0o644); os.chown(temporary, uid, gid)
            os.replace(temporary, target)
        else:
            with target.open("xb") as stream: stream.write(raw)
            os.chmod(target, 0o644); os.chown(target, uid, gid)
        for parent in target.parents:
            if parent == WT: break
            os.chown(parent, uid, gid)
    git(WT, ["add", "--sparse", "--", *sorted(files)])
    git(WT, ["diff", "--cached", "--check"])
    require(set(git(WT, ["diff", "--cached", "--name-only"]).stdout.decode().splitlines()) == set(files),
            "Staged source paths differ")
    tree = git(WT, ["write-tree"]).stdout.decode().strip()
    gate_command = ["runuser", "-u", "ubuntu", "-g", "chatgpt-agent", "--", "python3", str(WT / GATE_PATH),
                    "--base", "586c98bcc17dee425664224e508fc0e8df277678", "--ref", tree, "--output", str(GATE_RESULT)]
    started = time.time()
    gate = subprocess.run(gate_command, capture_output=True, timeout=40)
    report["retentionGate"] = {"argv": gate_command, "startedAt": started, "finishedAt": time.time(),
        "exitCode": gate.returncode, "controllerSHA256": GATE_SHA, "checkedTree": tree}
    for suffix, raw in ((".stdout", gate.stdout), (".stderr", gate.stderr)):
        path = GATE_RESULT.with_suffix(GATE_RESULT.suffix + suffix)
        with path.open("xb") as stream: stream.write(raw)
        report["retentionGate"][suffix[1:]] = {"path": str(path), **pin(raw)}
    if GATE_RESULT.is_file(): report["retentionGate"]["receipt"] = {"path": str(GATE_RESULT), **pin(GATE_RESULT.read_bytes())}
    require(gate.returncode == 0 and GATE_RESULT.is_file(), "Original source-retention gate failed")
    result = json.loads(GATE_RESULT.read_bytes())
    require(result["sourceRetentionPassed"] is True and not result["inventoryErrors"]
            and not result["unreviewedChangedExistingFiles"] and result["checkedTree"] == tree,
            "Retention result did not qualify the staged source tree")
    report["retentionGate"]["reviewedRefactors"] = len(result["reviewedRefactors"])
    report["beforeCommitCapacity"] = admit_capacity()
    git(WT, ["commit", "-m", "fix(ui): clear stale Bin rows after a current read failure"])
    commit = git(WT, ["rev-parse", "HEAD"]).stdout.decode().strip()
    require(git(WT, ["rev-parse", "HEAD^"]).stdout.decode().strip() == BASE, "Wrong source parent")
    require(git(WT, ["rev-parse", "HEAD^{tree}"]).stdout.decode().strip() == tree, "Commit tree differs from original gate")
    require(git(WT, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout == b"", "Worktree is not clean")
    report.update(status="SOURCE_COMMITTED_RUNTIME_NOT_RUN_PENDING_PUSH", commit=commit, tree=tree,
                  worktreeClean=True, handoffSHA256=sha(files[DOCS + "handoff.json"]), finalCapacity=capacity())
except BaseException as error:
    failure = error
    report.update(status="FAIL_SOURCE_PUBLICATION", failure={"type": type(error).__name__, "message": str(error)})
finally:
    report["finishedAt"] = time.time()
    try:
        with RECEIPT.open("xb") as stream: stream.write(encoded(report))
    except BaseException as save_error:
        if failure is not None: failure.add_note("Secondary receipt failure: " + repr(save_error))
        else: failure = save_error
print(json.dumps({k: v for k, v in report.items() if k != "commands"}, sort_keys=True))
if failure is not None: raise failure
