#!/usr/bin/env python3
"""Push one exact original archive over existing Oracle -> Mac pinned SSH.

This writes only to the already running job's exclusive FIFO. It never stages
the archive on Mac, creates a connection/credential, retries an upload, or
dispatches a workflow. The root supplies the actual admitted run and plan.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import time

ARCHIVE = Path("/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126/native-source-8ac407e75a4b.tar.gz")
ARCHIVE_SHA = "c70592e4ae160cbb5cb8eda3cb1caed08f727476a5c9fac7c207593cd9315830"
ARCHIVE_BYTES = 26130845
QUALIFICATION = Path("/tmp/pinkha-native8ac-original-archive-qualification339-1/receipt.json")
QUALIFICATION_SHA = "bbe85c549f6a20f9eee0ec3ef758e30b4f3a08b8c396cebe338e1808c51d65b6"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=15", "scaleway-mac"]


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def original_state():
    require(ARCHIVE.is_file() and not ARCHIVE.is_symlink() and ARCHIVE.resolve() == ARCHIVE,
            "Physical original Oracle source archive required")
    with os.fdopen(os.open(ARCHIVE, os.O_RDONLY | os.O_NOFOLLOW), "rb") as file:
        state = os.fstat(file.fileno())
        require(state.st_size == ARCHIVE_BYTES and hashlib.file_digest(file, "sha256").hexdigest() == ARCHIVE_SHA,
                "Original source archive bytes differ")
        after = os.fstat(file.fileno())
        named = ARCHIVE.lstat()
        fields = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns, row.st_mode)
        require(fields(state) == fields(after) == fields(named), "Original archive FD/path changed while hashing")
    return {"bytes": state.st_size, "sha256": ARCHIVE_SHA, "inode": state.st_ino,
            "device": state.st_dev, "mode": stat.S_IMODE(state.st_mode), "mtimeNS": state.st_mtime_ns}


REMOTE = r'''
import hashlib,json,os,select,stat,subprocess,sys,time
from pathlib import Path
p=Path(ROOT)
assert p.parent==Path('/Users/m1/builds/actions-anytype/_temp') and p.resolve()==p and p.is_dir()
ready_path=p/'source-stream-ready.json'; ready_bytes=ready_path.read_bytes(); r=json.loads(ready_bytes)
assert r['status']=='READY_FOR_ONE_EXACT_ORACLE_SOURCE_STREAM_NOT_ARTIFACT_ACCEPTANCE'
assert r['runID']==RUN and r['runAttempt']==ATTEMPT and r['controlCommit']==COMMIT and r['planSHA256']==PLAN
assert r['sourceArchiveSHA256']==ARCHIVE_SHA and r['sourceArchiveBytes']==ARCHIVE_BYTES
assert os.geteuid()!=0 and p.stat().st_uid==os.geteuid() and stat.S_IMODE(p.stat().st_mode)==0o700
assert 0<=time.time()-r['startedAt']<r['timeoutSeconds']
argv=subprocess.run(['/bin/ps','-p',str(r['producerPID']),'-o','args='],capture_output=True,text=True,check=True).stdout
assert 'hosted_shared_build/native_stream.py' in argv and '--output '+ROOT in argv
fifo=p/'original-source-archive.pipe'; s=fifo.lstat()
identity={'path':str(fifo),'inode':s.st_ino,'device':s.st_dev,'uid':s.st_uid,'mode':stat.S_IMODE(s.st_mode)}
assert stat.S_ISFIFO(s.st_mode) and identity==r['fifo'] and s.st_uid==os.geteuid() and identity['mode']==0o600
claim={'status':'CLAIMED_ONE_ORIGINAL_SOURCE_STREAM','runID':RUN,'runAttempt':ATTEMPT,'controlCommit':COMMIT,'planSHA256':PLAN,'readySHA256':hashlib.sha256(ready_bytes).hexdigest(),'fifo':identity,'startedAt':time.time()}
with os.fdopen(os.open(p/'source-relay.claim.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(claim,f,sort_keys=True);f.write('\n')
fd=None; count=0; h=hashlib.sha256(); deadline=time.monotonic()+180
try:
 fd=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
 assert os.fstat(fd).st_ino==s.st_ino and os.fstat(fd).st_dev==s.st_dev
 while True:
  assert time.monotonic()<deadline,'Owned source relay deadline expired'
  available,_,_=select.select([0],[],[],min(5,max(0,deadline-time.monotonic())))
  if not available:continue
  chunk=os.read(0,min(1024**2,ARCHIVE_BYTES+1-count))
  if not chunk:break
  count+=len(chunk);assert count<=ARCHIVE_BYTES
  h.update(chunk);remaining=memoryview(chunk)
  while remaining:
   assert time.monotonic()<deadline,'Owned FIFO relay write deadline expired'
   _,writable,_=select.select([],[fd],[],1)
   if writable:remaining=remaining[os.write(fd,remaining):]
 assert count==ARCHIVE_BYTES and h.hexdigest()==ARCHIVE_SHA
 assert fifo.lstat().st_ino==s.st_ino and ready_path.read_bytes()==ready_bytes
 result=dict(claim,status='PASS_ONE_EXACT_ORIGINAL_ARCHIVE_STREAMED_NOT_ARTIFACT_ACCEPTANCE',bytes=count,sha256=h.hexdigest(),archiveDiskBytes=0,restoredSourceDiskBytes=0,finishedAt=time.time())
 with os.fdopen(os.open(p/'source-relay.result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(result,f,sort_keys=True);f.write('\n')
 print(json.dumps(result))
finally:
 if fd is not None:os.close(fd)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--control-commit", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--self-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9]+", args.run_id) and re.fullmatch(r"[0-9]+", args.run_attempt)
            and re.fullmatch(r"[0-9a-f]{40}", args.control_commit)
            and re.fullmatch(r"[0-9a-f]{64}", args.plan_sha256)
            and digest(__file__) == args.self_sha256, "Exact admitted run/control/plan required")
    require(args.output.is_absolute() and args.output.parent.resolve() == args.output.parent
            and not args.output.exists() and not args.output.is_symlink(), "Fresh original relay evidence required")
    args.output.mkdir(mode=0o700)
    result = {"status": "FAIL_OR_INCOMPLETE_SOURCE_RELAY", "startedAt": time.time(),
              "runID": args.run_id, "runAttempt": args.run_attempt,
              "controlCommit": args.control_commit, "planSHA256": args.plan_sha256,
              "controllerSHA256": args.self_sha256, "archiveDiskBytesOnMac": 0,
              "workflowDispatches": 0, "sourceArchiveCopiedOnOracle": False}
    try:
        before = original_state()
        require(digest(QUALIFICATION) == QUALIFICATION_SHA, "Original complete source qualification differs")
        qualification = json.loads(QUALIFICATION.read_bytes())
        require(qualification["status"] == "PASS_ORIGINAL_ARCHIVE_SOURCE_CLOSURE_ONLY"
                and qualification["archive"]["sha256"] == ARCHIVE_SHA
                and qualification["sourceFiles"] == 4868, "Complete original source qualification is required")
        config = subprocess.run(["ssh", "-G", "scaleway-mac"], capture_output=True, text=True,
                                timeout=15, check=True).stdout
        effective = dict(line.split(" ", 1) for line in config.splitlines() if line.split(" ", 1)[0]
                         in {"user", "hostname", "port", "stricthostkeychecking", "hostkeyalias"})
        require(effective == {"user": "m1", "hostname": "62.210.195.226", "port": "22",
                              "stricthostkeychecking": "true", "hostkeyalias": "62.210.195.226"},
                "Existing pinned Mac SSH identity differs")
        result.update(sourceBefore=before, existingSSH=effective,
                      originalArchiveQualificationSHA256=QUALIFICATION_SHA)
        root = "/Users/m1/builds/actions-anytype/_temp/pinkha-native8ac-stream-export-" + args.run_id + "-" + args.run_attempt
        constants = {"ROOT": root, "RUN": args.run_id, "ATTEMPT": args.run_attempt,
                     "COMMIT": args.control_commit, "PLAN": args.plan_sha256,
                     "ARCHIVE_SHA": ARCHIVE_SHA, "ARCHIVE_BYTES": ARCHIVE_BYTES}
        script = "\n".join(key + "=" + repr(value) for key, value in constants.items()) + "\n" + REMOTE
        (args.output / "exact-remote-relay.py").write_text(script)
        command = "/opt/homebrew/bin/python3.12 -B -c " + shlex.quote(script)
        with os.fdopen(os.open(ARCHIVE, os.O_RDONLY | os.O_NOFOLLOW), "rb") as file:
            state = os.fstat(file.fileno())
            require((state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns) ==
                    (before["device"], before["inode"], before["bytes"], before["mtimeNS"]),
                    "Original archive FD identity changed before relay")
            call = subprocess.run(SSH + [command], stdin=file, capture_output=True, timeout=210)
            state_after = os.fstat(file.fileno())
            require((state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns) ==
                    (state_after.st_dev, state_after.st_ino, state_after.st_size, state_after.st_mtime_ns),
                    "Original archive FD changed during relay")
        (args.output / "relay.stdout").write_bytes(call.stdout)
        (args.output / "relay.stderr").write_bytes(call.stderr)
        result.update(exitCode=call.returncode, stdoutSHA256=hashlib.sha256(call.stdout).hexdigest(),
                      stderrSHA256=hashlib.sha256(call.stderr).hexdigest())
        require(call.returncode == 0, "Original relay failed; preserve partial custody and do not retry")
        remote = json.loads(call.stdout)
        require(remote["status"] == "PASS_ONE_EXACT_ORIGINAL_ARCHIVE_STREAMED_NOT_ARTIFACT_ACCEPTANCE"
                and remote["sha256"] == ARCHIVE_SHA and remote["bytes"] == ARCHIVE_BYTES,
                "Original source relay proof differs")
        after = original_state()
        require(before == after, "Original Oracle archive changed during relay")
        result.update(status="PASS_ORIGINAL_ARCHIVE_RELAY_NOT_ARTIFACT_ACCEPTANCE", sourceAfter=after, remote=remote)
    except BaseException as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        if isinstance(error, subprocess.TimeoutExpired):
            (args.output / "relay.timeout.stdout").write_bytes(error.stdout or b"")
            (args.output / "relay.timeout.stderr").write_bytes(error.stderr or b"")
            result["remoteCustodyState"] = "UNKNOWN_AFTER_SSH_TIMEOUT_NO_RETRY"
    result["finishedAt"] = time.time()
    receipt = args.output / "receipt.json"
    with receipt.open("x") as file:
        json.dump(result, file, indent=2, sort_keys=True)
        file.write("\n")
    print(json.dumps({"status": result["status"], "receipt": str(receipt), "sha256": digest(receipt)}))
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
