"""Build one exact recovered Any CLI for new C/E native acceptance only."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import tarfile
import time

ROOT = Path("/Users/m1/builds/pinkha-c-recovered-native-cli-20261125")
ARCHIVE_SHA = "9dba49012ea97598fa5fe693c500b01582ca75ac64e308f70732f3158e726b74"
MANIFEST_SHA = "d33fa2fb166aef89af0047ac23acf5c12fa108baec49566542cccd942a28f460"
GO = Path("/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go")
EMERGENCY = 2 * 1024**3
ESTIMATED_GROWTH = 612368384  # prior measured warmed CLI phase, including output/tmp/cache

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
    path.chmod(0o600)

def inventory(manifest):
    result = {}
    for source in manifest["sources"]:
        for relative, expected in source["inventory"].items():
            file = ROOT / "source" / source["prefix"] / relative
            require(file.resolve() == file and file.is_file(), "Canonical tracked source required")
            require(file.stat().st_size == expected["bytes"] and sha(file) == expected["sha256"],
                    "Original tracked native source differs")
            require(file.stat().st_mode & 0o777 == expected["mode"], "Original tracked mode differs")
            result[source["prefix"] + "/" + relative] = expected["sha256"]
    require(len(result) == 1583, "Complete original source closure required")
    return result

def main():
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Darwin arm64 required")
    require(ROOT.resolve() == ROOT and ROOT.is_dir(), "Existing newly owned root required")
    require(sha(ROOT / "source-any548-sdk195.tar.gz") == ARCHIVE_SHA, "Transferred exact archive required")
    output = ROOT / "build-attempt1"
    require(not output.exists() and not (ROOT / "source").exists(), "Fresh source and build attempt required")
    require(shutil.disk_usage(ROOT).free >= EMERGENCY + ESTIMATED_GROWTH, "Measured warmed build does not fit")
    output.mkdir(mode=0o700); (output / "tmp").mkdir(mode=0o700)
    (ROOT / "source").mkdir(mode=0o700)
    with tarfile.open(ROOT / "source-any548-sdk195.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == 1584 and len({m.name for m in members}) == len(members),
                "Exact complete source archive required")
        for member in members:
            p = Path(member.name)
            require(member.isfile() and not p.is_absolute() and ".." not in p.parts
                    and (member.name == "source-manifest.json" or member.name.startswith("any/")),
                    "Only original tracked source files are admitted")
        archive.extractall(ROOT / "source", filter="data")
        for member in members:
            (ROOT / "source" / member.name).chmod(member.mode)
    manifest_path = ROOT / "source/source-manifest.json"
    require(sha(manifest_path) == MANIFEST_SHA, "Original frozen source manifest differs")
    manifest = json.loads(manifest_path.read_bytes())
    require([(x["commit"], x["files"]) for x in manifest["sources"]] ==
            [("548f5cd0430a723bd26ea724daeb99991f68b9c9", 874),
             ("e195f6c07a053c6588e39ffe72ee4fc44cf3d953", 709)], "Exact Any and SDK revisions required")
    before = inventory(manifest)
    version = subprocess.check_output([str(GO), "version"], timeout=30).decode().strip()
    require(version == "go version go1.27.4 darwin/arm64", "Qualified original Go toolchain required")
    env = os.environ.copy()
    env.update(GOTOOLCHAIN="local", GOWORK="off", GOMAXPROCS="2", GOMEMLIMIT="2GiB",
               GOCACHE="/Users/m1/caches/anytapy-go1.27.4-build",
               GOMODCACHE="/Users/m1/caches/anytapy-go-mod",
               GOPROXY="file:///Users/m1/caches/go-mod/cache/download,https://proxy.golang.org,direct",
               GOTMPDIR=str(output / "tmp"), TMPDIR=str(output / "tmp"))
    require(all(Path(env[key]).is_dir() for key in ("GOCACHE", "GOMODCACHE")), "Existing qualified caches required")
    argv = [str(GO), "build", "-mod=readonly", "-p=2", "-o", str(ROOT / "any548"), "github.com/anyproto/any/cmd/any"]
    receipt = {"protocol": "pinkha-recovered-exact-native-cli-build-v1", "status": "FAIL",
               "controllerSHA256": sha(__file__), "sourceManifestSHA256": MANIFEST_SHA, "archiveSHA256": ARCHIVE_SHA,
               "toolchain": version, "sourceFiles": len(before), "sourceBefore": before,
               "argv": argv, "cwd": str(ROOT / "source/any"), "startedAt": time.time(),
               "testsExecuted": 0, "nativeAccountsCreated": 0, "newNativeAcceptance": False,
               "resourceRationale": {"estimatedWritableGrowthBytes": ESTIMATED_GROWTH, "emergencyBytes": EMERGENCY,
                                     "concurrency": "one coordinated p2/2GiB host CLI; no D Go producer"}}
    write(output / "command.json", receipt)
    stop = None
    process = None
    try:
        with (output / "original-go-build.log").open("xb") as stream:
            process = subprocess.Popen(argv, cwd=ROOT / "source/any", env=env,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            write(output / "started.json", {"pid": process.pid, "pgid": process.pid, "argv": argv})
            minimum = shutil.disk_usage(ROOT).free
            while process.poll() is None:
                minimum = min(minimum, shutil.disk_usage(ROOT).free)
                if minimum < EMERGENCY or time.time() - receipt["startedAt"] > 900:
                    stop = "OWNED_RESOURCE_OR_TIME_STOP"
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.wait()
                    break
                time.sleep(2)
        receipt.update(exitCode=process.returncode, guardStop=stop, minimumFreeBytes=minimum)
        require(process.returncode == 0 and stop is None, "Actual native CLI build did not complete")
        require(inventory(manifest) == before, "Original source changed during build")
        binary = ROOT / "any548"
        details = subprocess.check_output(["/usr/bin/file", str(binary)], timeout=30).decode().strip()
        require("Mach-O 64-bit executable arm64" in details, "Actual native host executable required")
        info = subprocess.check_output([str(GO), "version", "-m", str(binary)], timeout=30)
        (output / "original-binary-module-info.txt").write_bytes(info)
        receipt.update(status="PASS_BUILD_NOT_NATIVE_ACCEPTANCE", binarySHA256=sha(binary),
                       binaryBytes=binary.stat().st_size, binaryArchitecture=details,
                       moduleInfoSHA256=hashlib.sha256(info).hexdigest(), sourceAfter=inventory(manifest))
    except BaseException as exc:
        receipt["firstFailure"] = {"type": type(exc).__name__, "reason": str(exc)}
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
        raise
    finally:
        receipt["finishedAt"] = time.time()
        log = output / "original-go-build.log"
        if log.exists():
            receipt["originalLogSHA256"] = sha(log)
        write(output / "receipt.json", receipt)
        print(json.dumps({key: value for key, value in receipt.items()
                          if key not in ("sourceBefore", "sourceAfter")}, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
