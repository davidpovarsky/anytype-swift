#!/usr/bin/env python3
"""Stream the original native8ac payload; never create a Mac archive/source copy.

The source archive arrives through an exclusive owner-only FIFO from the
already configured Oracle -> Mac SSH connection. Only that 26 MB compressed
original is held in RAM. Framework inputs are read from their original paths.
The unchanged native_inputs reader independently qualifies the downloaded
artifact on the hosted consumer before any App compiler is admitted.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import select
import shutil
import stat
import sys
import tarfile
import time
import traceback

sys.dont_write_bytecode = True
import native_inputs as native
import run as original

ARCHIVE_SHA = "c70592e4ae160cbb5cb8eda3cb1caed08f727476a5c9fac7c207593cd9315830"
ARCHIVE_BYTES = 26130845
ARCHIVE_INVENTORY_SHA = "c73969a9d53c80f18ba52c6d698f680eede9402442adfcf0378b1e41a79d4913"
ARCHIVE_QUALIFICATION_SHA = "bbe85c549f6a20f9eee0ec3ef758e30b4f3a08b8c396cebe338e1808c51d65b6"
SOURCE_BYTES = 89636647
SOURCE_COUNT = 4868
ARCHIVE_TOTAL = 90455638
ACTION_SHA = "ea165f8d65b6e75b540449e92b4886f43607fa02"
ACTION_BUNDLE_SHA = "0165b8a75330f3228f2c7a234b4ff8a107b9139c2b519147f4c8e9fe99b262d8"
RECEIPT_BUDGET = 8 * 1024 ** 2
FIFO_SECONDS = 600
POLICY = {
    "schema": "pinkha-original-native8ac-no-local-archive-v1",
    "originalSourceArchiveSHA256": ARCHIVE_SHA,
    "originalSourceArchiveBytes": ARCHIVE_BYTES,
    "originalArchiveInventorySHA256": ARCHIVE_INVENTORY_SHA,
    "originalArchiveQualificationSHA256": ARCHIVE_QUALIFICATION_SHA,
    "originalSourceArchivePath": "/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126/native-source-8ac407e75a4b.tar.gz",
    "artifactActionCommit": ACTION_SHA,
    "artifactActionBundleSHA256": ACTION_BUNDLE_SHA,
    "sourceMode": "qualified-original-archive-stream",
    "sourceFIFOTimeoutSeconds": FIFO_SECONDS,
    "operationTimeoutSeconds": 1500,
    "archiveDiskBytes": 0,
    "restoredSourceDiskBytes": 0,
    "maximumReceiptDiskBytes": RECEIPT_BUDGET,
    "artifactUploadConcurrency": 2,
    "maximumObservedCombinedRSSBytes": 768 * 1024 ** 2,
}

require = native.require


def data_json(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def write(path, value):
    data = data_json(value)
    require(len(data) <= RECEIPT_BUDGET, "Bounded stream receipt required")
    path = Path(path)
    temporary = path.with_name(path.name + ".writing")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    os.link(temporary, path)
    temporary.unlink()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def mtime_ns(member):
    value = Decimal(str(member.pax_headers.get("mtime", member.mtime))) * 1000000000
    require(value.is_finite() and value >= 0 and value == value.to_integral_value(),
            "Exact original archive timestamp required")
    return int(value)


def fd_state(state):
    return {"device": state.st_dev, "inode": state.st_ino, "bytes": state.st_size,
            "mode": stat.S_IMODE(state.st_mode), "mtimeNS": state.st_mtime_ns,
            "ctimeNS": state.st_ctime_ns, "uid": state.st_uid, "gid": state.st_gid}


def original_record(path):
    path = Path(path)
    require(path.resolve() == path and not path.is_symlink(), "Physical original native input required")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as file:
        before = os.fstat(file.fileno())
        require(stat.S_ISREG(before.st_mode), "Original native input must be regular")
        digest = hashlib.file_digest(file, "sha256").hexdigest()
        require(fd_state(before) == fd_state(os.fstat(file.fileno())) == fd_state(path.lstat()),
                "Original native input changed during FD hashing")
    custody = fd_state(before)
    return {"bytes": before.st_size, "sha256": digest, "mode": stat.S_IMODE(before.st_mode),
            "mtimeNS": before.st_mtime_ns}, custody


class HashedInput:
    def __init__(self, stream):
        self.stream, self.digest, self.count = stream, hashlib.sha256(), 0

    def read(self, count):
        data = self.stream.read(count)
        self.count += len(data)
        self.digest.update(data)
        return data


def qualify_archive(data, manifest_bytes):
    require(len(data) == ARCHIVE_BYTES and hashlib.sha256(data).hexdigest() == ARCHIVE_SHA,
            "Exact original archived source bytes required")
    require(hashlib.sha256(manifest_bytes).hexdigest() == native.MANIFEST_SHA,
            "Original native8ac manifest differs")
    manifest = json.loads(manifest_bytes)
    require(len(manifest["files"]) == SOURCE_COUNT
            and sum(r["bytes"] for r in manifest["files"].values()) == SOURCE_BYTES,
            "Original source count/bytes differ")
    expected = dict(manifest["files"])
    expected["source-manifest.json"] = {"bytes": len(manifest_bytes), "sha256": native.MANIFEST_SHA}
    rows, folded, total = {}, set(), 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r|gz") as archive:
        for member in archive:
            native.safe_relative(member.name)
            require(member.isfile() and member.mode == 0o644 and member.name in expected
                    and member.name not in rows and member.name.casefold() not in folded,
                    "Unexpected, duplicate or nonregular original source member")
            require(member.size == expected[member.name]["bytes"], "Source member size differs")
            digest = hashlib.sha256()
            count = 0
            with archive.extractfile(member) as stream:
                for chunk in iter(lambda: stream.read(1024 ** 2), b""):
                    count += len(chunk)
                    digest.update(chunk)
            require(count == member.size and digest.hexdigest() == expected[member.name]["sha256"],
                    "Original source member content differs")
            rows[member.name] = {"bytes": count, "sha256": digest.hexdigest(),
                                 "mode": member.mode, "mtimeNS": mtime_ns(member)}
            folded.add(member.name.casefold())
            total += count
            require(total <= ARCHIVE_TOTAL, "Original source expanded byte bound exceeded")
    require(set(rows) == set(expected) and total == ARCHIVE_TOTAL,
            "Original archived source closure is incomplete")
    inventory_sha = hashlib.sha256(data_json(rows)).hexdigest()
    require(inventory_sha == ARCHIVE_INVENTORY_SHA, "Original full source metadata inventory differs")
    return rows


def fifo_identity(path):
    path = Path(path)
    state = path.lstat()
    require(stat.S_ISFIFO(state.st_mode) and state.st_uid == os.geteuid()
            and stat.S_IMODE(state.st_mode) == 0o600 and path.parent.resolve() == path.parent,
            "Exact owner-only physical FIFO required")
    return {"path": str(path), "inode": state.st_ino, "device": state.st_dev,
            "uid": state.st_uid, "mode": stat.S_IMODE(state.st_mode)}


def receive_archive(path, expected_identity):
    require(fifo_identity(path) == expected_identity, "Source FIFO identity changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        require(os.fstat(descriptor).st_ino == expected_identity["inode"], "Source FIFO open raced")
        deadline, data, started = time.monotonic() + FIFO_SECONDS, bytearray(), False
        while True:
            require(time.monotonic() < deadline, "Original source FIFO deadline expired")
            ready, _, _ = select.select([descriptor], [], [], 1)
            if not ready:
                continue
            chunk = os.read(descriptor, min(1024 ** 2, ARCHIVE_BYTES + 1 - len(data)))
            if chunk:
                started = True
                data.extend(chunk)
                require(len(data) <= ARCHIVE_BYTES, "Original source FIFO exceeded its exact byte bound")
            elif started:
                break
            else:
                time.sleep(0.05)
        require(len(data) == ARCHIVE_BYTES and hashlib.sha256(data).hexdigest() == ARCHIVE_SHA,
                "Original source FIFO was incomplete or changed")
        require(fifo_identity(path) == expected_identity, "Source FIFO changed during transport")
        return data
    finally:
        os.close(descriptor)


class HashedOutput:
    def __init__(self, target):
        self.target, self.digest, self.count = target, hashlib.sha256(), 0

    def write(self, data):
        self.count += len(data)
        require(self.count <= native.MAX_UNPACKED_BYTES, "Compressed native stream bound exceeded")
        self.digest.update(data)
        self.target.write(data)
        return len(data)

    def flush(self):
        self.target.flush()


def add_member(archive, name, row, stream):
    native.safe_relative(name)
    member = tarfile.TarInfo(name)
    member.size, member.mode = row["bytes"], row["mode"]
    member.mtime = row["mtimeNS"] // 1000000000
    member.pax_headers = {"mtime": str(member.mtime) + "." + f'{row["mtimeNS"] % 1000000000:09d}'}
    archive.addfile(member, stream)


def stream_payload(files, before, source_archive, source_rows, qualification, custody=None):
    rows = dict(before)
    rows.update({"native-source/" + name: row for name, row in source_rows.items()
                 if name != "source-manifest.json"})
    require(len(rows) <= native.MAX_FILES and
            sum(row["bytes"] for row in rows.values()) <= native.MAX_UNPACKED_BYTES,
            "Original native payload closure exceeds its original bounds")
    manifest = {"schema": "pinkha-original-native8ac-transport-v1", "files": rows,
                "qualification": qualification, "nativeSourceManifestSHA256": native.MANIFEST_SHA,
                "nativeBuildsNow": 0, "testsExecuted": 0}
    manifest_bytes = data_json(manifest)
    output = HashedOutput(sys.stdout.buffer)
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0, compresslevel=1) as compressed:
        with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
            first = tarfile.TarInfo("payload-manifest.json")
            first.size, first.mode = len(manifest_bytes), 0o600
            archive.addfile(first, io.BytesIO(manifest_bytes))
            for name in sorted(files):
                with os.fdopen(os.open(files[name], os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
                    state = fd_state(os.fstat(stream.fileno()))
                    if custody is not None:
                        require(state == custody[name], "Original payload source FD identity changed")
                    hashed = HashedInput(stream)
                    add_member(archive, name, before[name], hashed)
                    require(hashed.count == before[name]["bytes"] and hashed.digest.hexdigest() == before[name]["sha256"],
                            "Bytes actually streamed differ from the original native input")
                    require(state == fd_state(os.fstat(stream.fileno())) == fd_state(files[name].lstat()),
                            "Original source FD/path changed while streaming")
            with tarfile.open(fileobj=io.BytesIO(source_archive), mode="r|gz") as source:
                for member in source:
                    if member.name != "source-manifest.json":
                        with source.extractfile(member) as stream:
                            add_member(archive, "native-source/" + member.name, source_rows[member.name], stream)
    output.flush()
    return {"bytes": output.count, "sha256": output.digest.hexdigest()}, manifest_bytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    control, root = args.control.resolve(), args.output
    require(sys.platform == "darwin" and os.geteuid() != 0
            and os.environ.get("RUNNER_ENVIRONMENT") == "self-hosted"
            and os.environ.get("RUNNER_NAME") == "pinkha-scaleway-mac"
            and os.environ.get("GITHUB_REPOSITORY") == original.REPOSITORY,
            "Existing owner Mac Actions context required")
    plan = original.read_plan(args.plan, args.plan_sha256, control, export=True)
    require(plan["nativeStream"] == POLICY, "Root-reviewed exact stream policy required")
    require(root.is_absolute() and root.parent.resolve() == root.parent
            and root.parent == Path(os.environ["RUNNER_TEMP"]).resolve()
            and root.name == "pinkha-native8ac-stream-export-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"],
            "Exact run-owned source stream output required")
    require(not root.exists() and not root.is_symlink(), "No repeat of a source stream claim")
    # This is a different read-only-source operation. It creates only bounded
    # receipts/FIFO metadata, not the archive/source files whose original
    # 2 GiB live floor remains unchanged in run.py export/build.
    free_before = shutil.disk_usage(root.parent).free
    require(free_before >= RECEIPT_BUDGET, "Bounded receipt storage is unavailable")
    root.mkdir(mode=0o700)
    fifo, identity = root / "original-source-archive.pipe", None
    primary_error = None
    started = time.time()
    try:
        paths = {key: Path(value) for key, value in plan["exportInputs"].items()}
        source_state = original.source_identity(paths["appSource"], plan["exportAppSourceSHA"], plan["exportAppSourceTree"])
        controls_before = original.control_identity(control, plan["controlCommit"])
        small = [paths["materialization"] / kind / "combined-gomobile-bind.log" for kind in native.SLICE_PINS]
        require(sum(path.stat().st_size for path in small) <= 16 * 1024 ** 2, "Original logs exceed bounded stream RAM")
        qualification = native.qualify(paths["materialization"], paths["framework"],
                                       paths["appSource"] / original.NATIVE_MANIFEST,
                                       paths["appSource"] / original.RUNTIME,
                                       paths["appSource"] / original.BRIDGE)
        files = {"source-manifest.json": paths["appSource"] / original.NATIVE_MANIFEST}
        for name in ("receipt.json", "framework-files.json"):
            files["native/" + name] = paths["materialization"] / name
        for kind in native.SLICE_PINS:
            for name in ("receipt.json", "combined-gomobile-bind.command.json", "combined-gomobile-bind.log"):
                files["native/" + kind + "/" + name] = paths["materialization"] / kind / name
        for name in native.file_inventory(paths["framework"]):
            files["Lib.xcframework/" + name] = paths["framework"] / name
        observed = {name: original_record(path) for name, path in sorted(files.items())}
        before = {name: row[0] for name, row in observed.items()}
        custody = {name: row[1] for name, row in observed.items()}
        write(root / "original-inputs-before.json", {name: {"path": str(files[name]), **row, "custody": custody[name]} for name, row in before.items()})
        write(root / "original-controls-before.json", controls_before)
        os.mkfifo(fifo, mode=0o600)
        identity = fifo_identity(fifo)
        write(root / "source-stream-ready.json", {
            "status": "READY_FOR_ONE_EXACT_ORACLE_SOURCE_STREAM_NOT_ARTIFACT_ACCEPTANCE",
            "runID": os.environ["GITHUB_RUN_ID"], "runAttempt": os.environ["GITHUB_RUN_ATTEMPT"],
            "controlCommit": plan["controlCommit"], "planSHA256": args.plan_sha256,
            "fifo": identity, "sourceArchiveSHA256": ARCHIVE_SHA, "sourceArchiveBytes": ARCHIVE_BYTES,
            "producerPID": os.getpid(), "timeoutSeconds": FIFO_SECONDS, "startedAt": started,
            "archiveDiskBytes": 0, "restoredSourceDiskBytes": 0, "freeBytesObserved": free_before,
        })
        source_archive = receive_archive(fifo, identity)
        source_rows = qualify_archive(source_archive, files["source-manifest.json"].read_bytes())
        write(root / "source-archive-qualified.json", {
            "status": "PASS_EXACT_ORIGINAL_SOURCE_ARCHIVE_IN_MEMORY_NOT_APP_ACCEPTANCE",
            "sourceArchiveSHA256": ARCHIVE_SHA, "sourceArchiveBytes": ARCHIVE_BYTES,
            "sourceFiles": SOURCE_COUNT, "sourceBytes": SOURCE_BYTES,
            "originalInventorySHA256": ARCHIVE_INVENTORY_SHA,
            "originalArchiveQualificationSHA256": ARCHIVE_QUALIFICATION_SHA,
            "controlCommit": plan["controlCommit"], "planSHA256": args.plan_sha256,
            "archiveDiskBytes": 0, "restoredSourceDiskBytes": 0,
        })
        payload, manifest_bytes = stream_payload(files, before, source_archive, source_rows, qualification, custody)
        observed_after = {name: original_record(path) for name, path in sorted(files.items())}
        after = {name: row[0] for name, row in observed_after.items()}
        require(observed == observed_after, "Original native inputs/FD custody changed while streaming")
        require(native.qualify(paths["materialization"], paths["framework"],
                               paths["appSource"] / original.NATIVE_MANIFEST,
                               paths["appSource"] / original.RUNTIME,
                               paths["appSource"] / original.BRIDGE) == qualification,
                "Original complete runtime/framework qualification changed")
        require(original.source_identity(paths["appSource"], plan["exportAppSourceSHA"], plan["exportAppSourceTree"]) == source_state,
                "Retained App source changed during stream")
        require(original.control_identity(control, plan["controlCommit"]) == controls_before,
                "Original executed stream controls changed")
        write(root / "original-inputs-after.json", {name: {"path": str(files[name]), **row, "custody": observed_after[name][1]} for name, row in after.items()})
        with (root / "payload-manifest.json").open("xb") as file:
            file.write(manifest_bytes)
        write(root / "receipt.json", {
            "status": "PASS_ORIGINAL_NATIVE8AC_STREAM_NOT_DOWNLOADED_ARTIFACT_OR_APP_ACCEPTANCE",
            "payload": payload, "payloadManifestSHA256": hashlib.sha256(manifest_bytes).hexdigest(),
            "files": len(before) + SOURCE_COUNT, "sourceBeforeEqualsAfter": True,
            "sourceArchiveSHA256": ARCHIVE_SHA, "sourceArchiveBytes": ARCHIVE_BYTES,
            "originalArchiveInventorySHA256": ARCHIVE_INVENTORY_SHA,
            "nativeSourceManifestSHA256": native.MANIFEST_SHA, "controlCommit": plan["controlCommit"],
            "rootPlan": original.ref(args.plan), "policy": POLICY,
            "nativeBuildsNow": 0, "testsExecuted": 0, "archiveDiskBytes": 0,
            "restoredSourceDiskBytes": 0, "startedAt": started, "finishedAt": time.time(),
        })
    except BaseException as error:
        primary_error = error
        try:
            write(root / "stream-failure.json", {"status": "FAIL_OR_INCOMPLETE_NATIVE_STREAM", "type": type(error).__name__,
                                                "reason": str(error), "traceback": traceback.format_exc(),
                                                "archiveDiskBytes": 0, "nativeBuildsNow": 0, "testsExecuted": 0})
        except BaseException as evidence_error:
            print("Original failure receipt could not be written: " + type(evidence_error).__name__, file=sys.stderr)
        raise
    finally:
        try:
            if identity is not None and fifo.exists():
                require(fifo_identity(fifo) == identity, "Refuse custody receipt for a replaced FIFO")
                write(root / "fifo-custody.json", {"status": "RETAINED_FOR_NODE_OWNER_AFTER_PROCESS_GROUP_DRAIN", "fifo": identity})
        except BaseException as custody_error:
            if primary_error is None:
                raise
            print("FIFO custody receipt also failed: " + type(custody_error).__name__, file=sys.stderr)


if __name__ == "__main__":
    main()
