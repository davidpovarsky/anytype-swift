#!/usr/bin/env python3
"""Retain exact completed App14 producer originals; no build, test, or account."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import tarfile
import time

ROOT = Path("/Users/m1/development/anytype-d-active-20261125/main14")
OUTPUT = ROOT / "original-build-retention1"
RECEIPT = "b6b3ba75809a9bebe6fbf2dbf77149def27cb1eabe1771f9d5d73108c56e00d6"
SOURCE = "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
SCOPES = {
    "app-products": ROOT / "app-derived/Build/Products",
    "ui-products": ROOT / "ui-derived/Build/Products",
    "producer": ROOT / "build14",
    "generated-ui": ROOT / "ui-source-build14",
    "controller": ROOT / "control-b9e9d2f3cce",
    "source-provenance": ROOT / "source-inputs76",
    "native-provenance": ROOT / "native-materialization-11619",
}
EXTRA = {
    "extra/producer-launch.json": ROOT / "producer-launch.json",
    "extra/cache-staging.json": ROOT / "cache-staging.json",
    "extra/dependency-materialization.json": ROOT / "dependency-materialization/receipt.json",
    "extra/sdk-source.json": ROOT / "source/Dependencies/Hanlin/.pinkha-source.json",
    "extra/Package.resolved": ROOT / "source/Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
}
FLOOR = 2 * 1024**3


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns)


def row(path):
    before = path.lstat()
    result = {"mode": stat.S_IMODE(before.st_mode), "mtimeNS": before.st_mtime_ns,
              "dev": before.st_dev, "inode": before.st_ino, "links": before.st_nlink}
    if stat.S_ISLNK(before.st_mode):
        result.update(kind="symlink", target=os.readlink(path))
    elif stat.S_ISDIR(before.st_mode):
        result.update(kind="directory")
    else:
        assert stat.S_ISREG(before.st_mode)
        result.update(kind="file", bytes=before.st_size, sha256=digest(path))
    assert identity(before) == identity(path.lstat()), str(path)
    return result


def inventory():
    rows = {}
    paths = {}
    for label, base in SCOPES.items():
        assert base.is_dir() and not base.is_symlink() and base.resolve() == base
        rows[label] = row(base); paths[label] = base
        for directory, dirs, files in os.walk(base, followlinks=False):
            for name in sorted(dirs + files):
                path = Path(directory) / name
                key = label + "/" + path.relative_to(base).as_posix()
                assert key not in rows
                entry = row(path)
                if entry["kind"] == "symlink":
                    resolved = (path.parent / entry["target"]).resolve()
                    assert resolved == base or base in resolved.parents
                rows[key] = entry; paths[key] = path
    for name, path in EXTRA.items():
        assert name not in rows and path.is_file() and not path.is_symlink()
        assert path.resolve() == path
        rows[name] = row(path); paths[name] = path
    return rows, paths


def main():
    assert not OUTPUT.exists()
    raw = (ROOT / "build14/receipt.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RECEIPT
    receipt = json.loads(raw)
    assert receipt["sourceCommit"] == SOURCE
    assert receipt["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
    assert receipt["sourceUnchanged"] is True and receipt["testsExecuted"] == 0
    for phase in ("app", "ui"):
        assert receipt[phase]["status"] == "PASS_BUILD_EXIT_0"
        assert receipt[phase]["exitCode"] == 0
        assert receipt[phase]["ownedProcessGroup"] == "ABSENT_ESRCH"
        assert digest(ROOT / "build14" / phase / "original.log") == receipt[phase]["logSHA256"]
    assert (ROOT / "build14/source-before.json").read_bytes() == (ROOT / "build14/source-after.json").read_bytes()
    assert digest(ROOT / "build14/products-all.json") == receipt["completeProductsInventory"]["sha256"]
    OUTPUT.mkdir(mode=0o700)
    started = time.time()
    before, paths = inventory()
    write(OUTPUT / "members-before.json", before)
    total = sum(r.get("bytes", 0) for r in before.values())
    initial_free = shutil.disk_usage(ROOT).free
    assert initial_free > total + FLOOR + 128 * 1024**2
    archive = OUTPUT / "originals.tar.gz"
    minimum = initial_free
    with tarfile.open(archive, "w:gz", compresslevel=1, format=tarfile.PAX_FORMAT) as target:
        archive.chmod(0o600)
        for index, (name, record) in enumerate(sorted(before.items())):
            free = shutil.disk_usage(ROOT).free
            minimum = min(minimum, free)
            assert free >= FLOOR, "owned retention disk floor"
            path = paths[name]
            current = path.lstat()
            assert (current.st_dev, current.st_ino, stat.S_IMODE(current.st_mode),
                    current.st_mtime_ns) == (record["dev"], record["inode"],
                                             record["mode"], record["mtimeNS"]), name
            info = tarfile.TarInfo(name)
            info.mode = record["mode"]
            info.mtime = current.st_mtime
            info.uid, info.gid = current.st_uid, current.st_gid
            if record["kind"] == "directory":
                info.type = tarfile.DIRTYPE; target.addfile(info)
            elif record["kind"] == "symlink":
                info.type = tarfile.SYMTYPE; info.linkname = record["target"]
                assert os.readlink(path) == info.linkname
                target.addfile(info)
            else:
                info.type = tarfile.REGTYPE; info.size = record["bytes"]
                with path.open("rb") as stream: target.addfile(info, stream)
            if index % 100 == 0:
                write(OUTPUT / "monitor.json", {
                    "membersWritten": index + 1, "totalMembers": len(before),
                    "archiveBytes": archive.stat().st_size, "minimumFreeBytes": minimum,
                    "elapsedSeconds": time.time() - started})
    after, _ = inventory()
    write(OUTPUT / "members-after.json", after)
    assert before == after
    result = {
        "protocol": "original-App14-build-retention-v1", "status": "PASS_ORIGINAL_BUILD_RETAINED",
        "sourceCommit": SOURCE, "producerReceiptSHA256": RECEIPT,
        "sourceBeforeAfterSHA256": digest(ROOT / "build14/source-before.json"),
        "members": len(before), "memberManifestSHA256": digest(OUTPUT / "members-before.json"),
        "scopeCounts": {label: sum(k == label or k.startswith(label + "/") for k in before)
                        for label in SCOPES},
        "sourceBytes": total, "archiveBytes": archive.stat().st_size,
        "archiveSHA256": digest(archive), "originalsUnchanged": True,
        "started": started, "finished": time.time(), "minimumFreeBytes": minimum,
        "AppBuilds": 0, "UIBuilds": 0, "nativeBuilds": 0, "tests": 0,
        "sourceBundleAlreadyRetained": "d9b19a646df1acf340388e9a0199aaefa1082785f75e3b4376c59014909176a5",
        "nativeAssemblyAlreadyRetained": "daaddb5a6f23cebb5c2d3c0efb1b18d221a4a1f55f3e0e451b5e64e755ec02d3",
        "SDKCanonicalArchiveAlreadyRetained": "c13a544949f857e18b50d7c68fa5a25baf66ba742f9e392408ab01001671946c",
        "acceptanceClaim": False,
    }
    write(OUTPUT / "receipt.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        if OUTPUT.exists():
            write(OUTPUT / "failure.json", {"status": "FAIL_RETAIN_ORIGINALS",
                "errorType": type(error).__name__, "error": str(error),
                "AppBuilds": 0, "tests": 0, "failed": time.time()})
        raise
