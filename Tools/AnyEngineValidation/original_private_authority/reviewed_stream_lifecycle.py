#!/usr/bin/env python3
"""Qualify reviewed public verifier source against the exact original archive.

This is a separate, explicit custody route after the duplicate Oracle archive
was retired. It streams the unchanged Windows archive, hashes every compressed
byte, and interprets only source metadata and the original producer receipt.
It never restores/extracts an account, reads a mnemonic, or runs native code.
No compressed archive or full 22 MiB source manifest is written to Oracle.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import io
import json
import os
import select
import shutil
import signal
import stat
import subprocess
import tarfile
import time
import traceback

REMOTE = "C:/Users/DAVID/AppData/Local/SentinelX/anytapy-immutable-evidence/native-file-peer-45492064232-1/private-evidence.tar.gz"
ARCHIVE_BYTES = 106036361
ARCHIVE_SHA = "f85036744b0cb76ffecb4e29f752dd293a74a1f76c2d13c273df57691a4a8c64"
INDEX = Path("/var/lib/pinkha-w1-functional-migration-20261127/original156-source-custody2/private-original-index.json")
INDEX_SHA = "9e4fc63d587d194cf13fff4002329c25404490c166dd9ffc4fac9778767167b1"
RETIREMENT = Path("/var/lib/pinkha-w1-original156-retirement-20261127/attempt2/result.json")
RETIREMENT_SHA = "5d0dc7beab578f61d40eab4e9f466e936ca7f97903d5062fcb2844432d55303b"
RESTORE = RETIREMENT.parent / "restoration-map.json"
RESTORE_SHA = "f18df0bf23d585e31941d62910ee55ea673d51882c290260ad9f3d55832e82b5"
SOURCE_METADATA_SHA = "2a0a8807ffaae25b3596a387e47f42e5893d9a83ee64d161d029712d0acaced9"
SYNC = Path("/var/tmp/pinkha-e-cutover-current8ac-20261127/attempt2/source/sync")
ANYENC = Path("/root/go/pkg/mod/github.com/anyproto/any-store@v1.0.3/anyenc")
DELTAS = ["derived-source-v2.json", "native-whole-source-delta-v1.json", "native-file-peer-source-delta-v1.json",
          "native-type-namespace-peer-continuation-v1.json", "native-custom-schema-checkpoint-delta-v1.json"]
MEMBERS = ["private/source-metadata/manifest.json", "private/result.json"] + ["private/source-metadata/" + x for x in DELTAS]
FLOOR = 2 * 1024**3
ALLOWANCE = 32 * 1024**2
OUTPUT_CAP = 8 * 1024**2
DEADLINE = 90


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_frozen(path):
    """Read exact control/source bytes without changing retained access times."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        assert stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2
        data = source.read(before.st_size + 1)
        after = os.fstat(source.fileno())
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid", "st_size",
                  "st_atime_ns", "st_mtime_ns", "st_ctime_ns")
        assert all(getattr(before, key) == getattr(after, key) for key in fields)
        assert len(data) == before.st_size
        return data


def interrupted(signum, _frame):
    raise RuntimeError("source-stream controller interrupted by signal " + str(signum))


def absent(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True


def drain_group(process, seconds):
    """Reap the leader and wait for the entire owned group, not just waitpid."""
    deadline = time.monotonic() + seconds
    while True:
        code = process.poll()
        gone = absent(process.pid)
        if code is not None and gone:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def finish_group(process, result, already_observed_absent):
    row = {"role": "pinned-read-only-original-Windows-stream", "pid": process.pid,
           "exitCode": None, "groupPositivelyAbsent": False, "forcedCleanup": False}
    try:
        if already_observed_absent:
            # The completed group's positive absence was recorded at EOF and
            # exit 0. Never signal or re-probe that historical numeric PGID.
            row.update(exitCode=0, groupPositivelyAbsent=True,
                       absenceObservedAt="completed-stream-EOF-and-exit0")
            return
        row["forcedCleanup"] = process.poll() is None or not absent(process.pid)
        if row["forcedCleanup"]:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            if not drain_group(process, 5):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                assert drain_group(process, 5), "owned SSH group survived SIGKILL"
        row["exitCode"] = process.poll()
        row["groupPositivelyAbsent"] = absent(process.pid)
    except BaseException as error:
        result["errors"].append({"cleanup": str(error), "type": type(error).__name__})
        result["status"] = "FAIL"
        # A cleanup exception must not skip a second bounded attempt or receipt.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except BaseException as kill_error:
            result["errors"].append({"cleanupKill": str(kill_error), "type": type(kill_error).__name__})
        try:
            drain_group(process, 5)
            row["exitCode"] = process.poll()
            row["groupPositivelyAbsent"] = absent(process.pid)
        except BaseException as final_error:
            result["errors"].append({"cleanupFinalState": str(final_error), "type": type(final_error).__name__})
    finally:
        try:
            if process.stdout is not None:
                process.stdout.close()
        except BaseException as close_error:
            result["errors"].append({"cleanupPipe": str(close_error), "type": type(close_error).__name__})
            result["status"] = "FAIL"
        result["commands"].append(row)
        if row["forcedCleanup"] or row["exitCode"] != 0 or not row["groupPositivelyAbsent"]:
            result["status"] = "FAIL"


def process_guard(out, began):
    free = shutil.disk_usage(out).free
    assert free >= FLOOR, "unchanged 2 GiB root emergency floor"
    assert time.monotonic() - began <= DEADLINE, "bounded source-stream deadline"
    size = sum(p.stat().st_size for p in out.iterdir() if p.is_file())
    assert size <= OUTPUT_CAP, "bounded source-proof output"
    return free


class HashStream(io.RawIOBase):
    def __init__(self, pipe, out, began):
        self.pipe, self.out, self.began = pipe, out, began
        self.hasher, self.count, self.eof = hashlib.sha256(), 0, False
        self.minimum_free = shutil.disk_usage(out).free

    def readable(self):
        return True

    def read(self, count=-1):
        if self.eof:
            return b""
        count = min(count if count >= 0 else 1024 * 1024, 1024 * 1024)
        if count == 0:
            return b""
        while True:
            self.minimum_free = min(self.minimum_free, process_guard(self.out, self.began))
            ready, _, _ = select.select([self.pipe], [], [], 0.25)
            if ready:
                chunk = os.read(self.pipe.fileno(), count)
                self.count += len(chunk)
                assert self.count <= ARCHIVE_BYTES, "unexpected extra compressed archive bytes"
                self.hasher.update(chunk)
                if not chunk:
                    self.eof = True
                return chunk


def remote_command():
    # Open with FileShare.Read: no concurrent ordinary writer/delete handle is
    # admitted while the exact archived source is streamed. Only public file
    # metadata goes to stderr; stdout contains exactly the original bytes.
    script = r"""
$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue';
if ($env:COMPUTERNAME -ne 'DAVID_AND_GOLDY') { throw 'wrong original host' }
$p='__REMOTE__'; $f=Get-Item -LiteralPath $p;
if ($f.Length -ne __SIZE__) { throw 'wrong original archive length' }
$before=@{host=$env:COMPUTERNAME;path=$f.FullName;bytes=$f.Length;lastWriteTicks=$f.LastWriteTimeUtc.Ticks;creationTicks=$f.CreationTimeUtc.Ticks;attributes=[int]$f.Attributes};
$s=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);
try { $o=[Console]::OpenStandardOutput(); $b=New-Object byte[] 1048576; [long]$n=0;
  while (($r=$s.Read($b,0,$b.Length)) -gt 0) { $o.Write($b,0,$r); $n += $r }
  $o.Flush(); $f.Refresh();
  if ($n -ne __SIZE__ -or $f.Length -ne $before.bytes -or $f.LastWriteTimeUtc.Ticks -ne $before.lastWriteTicks -or $f.CreationTimeUtc.Ticks -ne $before.creationTicks -or [int]$f.Attributes -ne $before.attributes) { throw 'original archive metadata changed' }
  [Console]::Error.WriteLine((@{source=$before;streamedBytes=$n;readOnlySharedHandle=$true}|ConvertTo-Json -Compress -Depth 4));
} finally { $s.Dispose() }
""".replace("__REMOTE__", REMOTE).replace("__SIZE__", str(ARCHIVE_BYTES))
    encoded = base64.b64encode(script.encode("utf-16le")).decode()
    return ["sudo", "-n", "-u", "ubuntu", "ssh", "-T", "-o", "ControlMaster=no", "-o", "ControlPath=none",
            "-o", "ControlPersist=no", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=10", "david-win", "powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--reviewed-sources", required=True)
    parser.add_argument("--reviewed-sources-sha", required=True)
    args = parser.parse_args()
    out, pins_path = Path(args.output), Path(args.reviewed_sources)
    os.umask(0o077)
    assert not out.exists() and out.parent.is_dir()
    out.mkdir(mode=0o700)
    began = time.monotonic()
    result = {"status": "FAIL", "protocol": "pinkha-original156-detached-public-source-stream-v1",
              "compressedArchiveRestored": False, "accountExtracted": False, "accountOpened": False,
              "privateKeyDecoded": False, "nativeBuilds": 0, "nativeTests": 0, "commands": [], "errors": []}
    process, stream, controller_bytes = None, None, None
    completed_group_absent = False
    source_pins = []
    try:
        controller_bytes = read_frozen(Path(__file__))
        result["controllerSHA256"] = sha(controller_bytes)
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        previous_mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
        result["inheritedBlockedSignals"] = sorted(int(value) for value in previous_mask)
        result["controllerTerminationSignalsUnblocked"] = True
        assert shutil.disk_usage(out.parent).free >= FLOOR + ALLOWANCE, "initial root 2 GiB + 32 MiB source-stream admission"
        raw_index = read_frozen(INDEX)
        assert sha(raw_index) == INDEX_SHA
        assert sha(read_frozen(RETIREMENT)) == RETIREMENT_SHA
        assert sha(read_frozen(RESTORE)) == RESTORE_SHA
        original_index = {row["path"]: row for row in json.loads(raw_index)["members"]}
        pins_raw = read_frozen(pins_path)
        assert sha(pins_raw) == args.reviewed_sources_sha
        pins = json.loads(pins_raw)
        assert pins["status"] == "REVIEWED_SOURCE_ONLY_NOT_ORIGINAL_PROVENANCE_OR_NATIVE_QUALIFIED"
        assert pins["originalSyncCommit"] == "c005bd6cde8d8f8a6007c35f06894f3d89f9f07c"
        assert len(pins["files"]) >= 20
        for row in pins["files"]:
            assert row["scope"] in ("sync", "anyenc")
            name = Path(row["path"])
            assert not name.is_absolute() and ".." not in name.parts
            current = (SYNC if row["scope"] == "sync" else ANYENC) / name
            assert current.is_file() and not current.is_symlink()
            data = read_frozen(current)
            assert sha(data) == row["sha256"] and len(data) == row["bytes"]
            source_pins.append((current, row))
        selected = {}
        with (out / "source-stream-stderr.log").open("xb") as stderr:
            process = subprocess.Popen(remote_command(), stdout=subprocess.PIPE, stderr=stderr, start_new_session=True)
            stream = HashStream(process.stdout, out, began)
            with tarfile.open(fileobj=stream, mode="r|gz") as archive:
                for member in archive:
                    process_guard(out, began)
                    if member.name not in MEMBERS:
                        continue
                    assert member.name not in selected and member.isfile() and not member.issym() and not member.islnk()
                    expected = original_index[member.name]
                    assert member.size == expected["bytes"] and member.size <= 24 * 1024**2
                    data = archive.extractfile(member).read(member.size + 1)
                    assert len(data) == member.size and sha(data) == expected["sha256"]
                    selected[member.name] = data
            # Tar EOF is not sufficient: hash every remaining compressed byte
            # and require process EOF, exact count and positive group absence.
            while stream.read(1024 * 1024):
                pass
            process.wait(timeout=max(1, DEADLINE - int(time.monotonic() - began)))
        assert process.returncode == 0 and absent(process.pid)
        completed_group_absent = True
        assert stream.eof and stream.count == ARCHIVE_BYTES and stream.hasher.hexdigest() == ARCHIVE_SHA
        assert set(selected) == set(MEMBERS)
        stderr_raw = (out / "source-stream-stderr.log").read_bytes()
        assert len(stderr_raw) <= 16 * 1024
        remote = json.loads(stderr_raw)
        assert remote["source"]["host"] == "DAVID_AND_GOLDY" and remote["streamedBytes"] == ARCHIVE_BYTES
        assert remote["readOnlySharedHandle"] is True
        metadata_raw = selected["private/source-metadata/manifest.json"]
        assert sha(metadata_raw) == SOURCE_METADATA_SHA
        metadata = json.loads(metadata_raw)
        matches = []
        for current, row in source_pins:
            suffix = row["path"] if row["scope"] == "sync" else "anyenc/" + row["path"]
            found = [original for original in metadata["files"]["rows"] if original[0].endswith("/" + suffix)
                     and (row["scope"] != "sync" or
                          isinstance(original[6], dict) and original[6].get("commit") == pins["originalSyncCommit"])]
            assert len(found) == 1 and found[0][4] == row["sha256"]
            if row["scope"] == "sync":
                assert found[0][6]["commit"] == pins["originalSyncCommit"]
            matches.append(row | {"originalManifestPath": found[0][0], "originalAndReviewedSourceEqual": True})
        heart_commit, chain = "24dc6393b30e6d1d80ec28ff624060af9bb4327a", []
        for name in DELTAS:
            data = selected["private/source-metadata/" + name]
            delta = json.loads(data)
            assert delta["base_heart_commit"] == heart_commit
            changed = [row["path"] for row in delta.get("files", [])]
            if "path" in delta:
                changed.append(delta["path"])
            # These deltas explicitly advance Heart commits, not the pinned
            # any-sync repository. Bare go.mod/go.sum filenames also occur in
            # Heart and cannot select another repository's module authority.
            # Their exact any-sync commit/member hashes were joined above.
            assert not any(path.endswith(row["path"]) for path in changed for row in matches
                           if row["path"] not in ("go.mod", "go.sum"))
            heart_commit = delta["derived_heart_commit"]
            chain.append({"name": name, "sha256": sha(data), "derivedHeartCommit": heart_commit})
        producer = json.loads(selected["private/result.json"])
        assert heart_commit == "65caee9bfc386c2f9182564d6ad1eb2f02cfadd1"
        assert producer["heart_sha"] == heart_commit and producer["compiled_source_unchanged"] is True
        result.update(originalArchiveSHA256=ARCHIVE_SHA, streamedCompressedBytes=stream.count,
                      originalSourceMetadataSHA256=SOURCE_METADATA_SHA, sourceArchiveMetadata=remote,
                      selectedMetadataMembers=[{"path": n, "bytes": len(selected[n]), "sha256": sha(selected[n])} for n in MEMBERS],
                      originalSyncCommit=pins["originalSyncCommit"], originalHeartSourceChain=chain,
                      reviewedSourcesSHA256=args.reviewed_sources_sha, matchedOriginalSourceMembers=matches,
                      retirementReceiptSHA256=RETIREMENT_SHA, restorationMapSHA256=RESTORE_SHA)
        result["status"] = "PASS_ORIGINAL_PUBLIC_SOURCE_PROVENANCE_ONLY"
    except BaseException as error:
        result["status"] = "FAIL"
        result["errors"].append({"type": type(error).__name__, "message": str(error)})
        (out / "traceback.txt").write_text(traceback.format_exc())
    finally:
        # Finish bounded cleanup even if a second stop signal arrives meanwhile.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if process is not None:
            finish_group(process, result, completed_group_absent)
        try:
            for current, row in source_pins:
                data = read_frozen(current)
                assert sha(data) == row["sha256"] and len(data) == row["bytes"]
            assert sha(read_frozen(INDEX)) == INDEX_SHA
            assert sha(read_frozen(RETIREMENT)) == RETIREMENT_SHA
            assert sha(read_frozen(RESTORE)) == RESTORE_SHA
            assert sha(read_frozen(pins_path)) == args.reviewed_sources_sha
            result["currentSourcesAndCustodyControlsUnchanged"] = True
        except BaseException as error:
            result["status"] = "FAIL"
            result["errors"].append({"finalIntegrity": str(error), "type": type(error).__name__})
        result["seconds"] = round(time.monotonic() - began, 3)
        result["minimumRootFreeBytes"] = stream.minimum_free if stream is not None else shutil.disk_usage(out).free
        try:
            assert controller_bytes is not None and read_frozen(Path(__file__)) == controller_bytes
            (out / "controller.py").write_bytes(controller_bytes)
            result["controllerUnchanged"] = True
        except BaseException as error:
            result["status"] = "FAIL"
            result["errors"].append({"finalControllerIntegrity": str(error), "type": type(error).__name__})
        receipt = out / "result.json"
        receipt.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "result": str(receipt), "sha256": sha(receipt.read_bytes()),
                      "seconds": result["seconds"], "errors": result["errors"]}))
    return 0 if result["status"] == "PASS_ORIGINAL_PUBLIC_SOURCE_PROVENANCE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
