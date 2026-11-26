#!/usr/bin/env python3
"""Reproduce seven registry descriptors from recovered original source.

This is a pure registry/codecs executable. It does not open an account or space,
replace historical captured files, or admit a destination migration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time
import traceback

ARCHIVE_SHA = "bf746ea6bd965927d0e17b0d59772a55bc7542ab80629d97d4dd8ae8193c2f04"
MANIFEST_SHA = "2a0a8807ffaae25b3596a387e47f42e5893d9a83ee64d161d029712d0acaced9"
HEART = "/mnt/development/projects/worktrees/anytype-heart-loaded-account-witness-20261123"
SYNC = "/mnt/development/projects/worktrees/any-sync-loaded-account-witness-20261123"
CACHE = "/mnt/development/projects/evidence/semantic-page-20261123-arm64/attempt4/cache/go-mod"
GOROOT = "/mnt/development/projects/evidence/semantic-page-20261123-arm64/toolchains/go1.26.5/go"
ORIGINAL_MOD = "/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123/Tools/AnyEngineValidation/loaded_account_witness/candidate.mod"
HEART_BASE = "24dc6393b30e6d1d80ec28ff624060af9bb4327a"
HEART_COMMIT = "65caee9bfc386c2f9182564d6ad1eb2f02cfadd1"
BINARY_SHA = "0755ceb488fe11b917bc3161090755926eb8f217d976aa405df71c4d25aea5e7"
C_REPO = Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
HEART_REPO = Path("/mnt/development/projects/worktrees/anytype-heart-native-default-source-20261124")
BASE = Path("/mnt/development/projects/evidence/c-source-asset-recovery-20261126")
RECOVERED = BASE / "original-python-extraction1"
ROOTFS = RECOVERED / "rootfs"
EXPORTER_SHA = "a1b923e276d154c5d57f482846fc24ab9087112f234acfdf4b07521cb3be4cd9"
KEYS = ["analyticsSpaceId", "apiObjectKey", "headerRelationsLayout", "homepage",
        "migrationObjectContext", "orderId", "relationFormatIncludeTime"]
FLOOR = 2 * 1024**3

def require(value, message):
    if not value:
        raise ValueError(message)

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def raw(path, maximum=512 * 1024**2):
    require(path.is_absolute() and path.resolve() == path, "Canonical input required")
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 0 <= before.st_size <= maximum, "Bounded original regular input required")
    value = path.read_bytes()
    after = path.lstat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode)
            and len(value) == before.st_size, "Input changed during read")
    return value

def write(path, value):
    payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)

def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory=" + str(HEART_REPO),
                                   "-C", str(HEART_REPO), *args], timeout=30)

def entries(manifest):
    require(manifest["files"]["schema"] == "loaded-account-source-file-columns-v1",
            "Original source columns required")
    rows = {}
    for name, physical, kind, values, sha, has_git, origin, retained, extra in manifest["files"]["rows"]:
        require(name.startswith("/") and ".." not in Path(name).parts and name not in rows,
                "Closed original absolute source member required")
        if kind == "native_git_blob_only":
            size, mode = extra["git_bytes"], extra["archive_mode"]
        else:
            size, mode = int(values[6]), stat.S_IMODE(int(values[2]))
        rows[name] = {"sha256": sha, "bytes": size, "mode": mode,
                      "git": origin if has_git else None, "kind": kind}
    require(len(rows) == 59826 and sum(v["bytes"] for v in rows.values()) == 1204807504,
            "Original complete source census required")
    return rows

def check_member(path, row):
    require(path.resolve() == path and path.is_file() and not path.is_symlink(),
            "Original source member is absent or aliased")
    before = path.lstat()
    require(before.st_size == row["bytes"] and stat.S_IMODE(before.st_mode) == row["mode"],
            "Original source size/mode differs")
    require(digest(path) == row["sha256"], "Original source bytes differ")
    after = path.lstat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode),
            "Source member changed during hashing")
    return {"bytes": after.st_size, "mode": stat.S_IMODE(after.st_mode),
            "sha256": row["sha256"], "device": after.st_dev, "inode": after.st_ino}

def producer_authority():
    relative = "Tools/AnyEngineValidation/native_file_peer/retained-scheduling-45492064232/producer-result.json"
    expected = subprocess.check_output(["git", "-c", "safe.directory=" + str(C_REPO), "-C", str(C_REPO),
        "show", "012ec3fb2b4248ae4882dc3792e531d914b26994:" + relative], timeout=30)
    require(raw(C_REPO / relative, 4 * 1024**2) == expected, "Exact retained original producer required")
    p = json.loads(expected)
    require(p["heart_sha"] == HEART_COMMIT and p["base_heart_sha"] == HEART_BASE
            and p["source"]["manifest_sha256"] == MANIFEST_SHA
            and p["input_sha256"]["source"] == ARCHIVE_SHA
            and p["binary"]["sha256"] == BINARY_SHA and p["binary"]["bytes"] == 166478528
            and p["compiled_source_unchanged"] is True
            and str(p["run_id"]) == "45492064232" and str(p["run_attempt"]) == "1",
            "Original source, producer, binary and run binding differs")
    stages = ["context_derivation", "whole_source_derivation", "file_peer_derivation",
              "namespace_peer_continuation", "custom_schema_checkpoint_continuation"]
    prior = HEART_BASE
    proof = []
    for key in stages:
        stage = p["source"][key]
        require(stage["base_heart_commit"] == prior, "Original source derivation chain differs")
        current = stage["derived_heart_commit"]
        actual_paths = git("diff", "--name-only", prior, current).decode().splitlines()
        declared = [v["path"] for v in stage["files"]] if "files" in stage else [stage["path"]]
        require(sorted(actual_paths) == sorted(declared), "Undeclared original source delta")
        for row in stage.get("files", []):
            value = git("show", current + ":" + row["path"])
            require(len(value) == row["bytes"] and hashlib.sha256(value).hexdigest() == row["sha256"],
                    "Actual derived Git bytes differ from original producer")
            if "before_sha256" in row:
                require(hashlib.sha256(git("show", prior + ":" + row["path"])).hexdigest() == row["before_sha256"],
                        "Original delta predecessor differs")
        if "files" not in stage:
            before = git("show", prior + ":" + stage["path"])
            after = git("show", current + ":" + stage["path"])
            require(hashlib.sha256(before).hexdigest() == stage["before_sha256"]
                    and hashlib.sha256(after).hexdigest() == stage["after_sha256"],
                    "Original first source derivation differs")
        proof.append({"stage": key, "base": prior, "derived": current, "changedPaths": actual_paths})
        prior = current
    require(prior == HEART_COMMIT, "Original final native source differs")
    tree = {}
    for item in git("ls-tree", "-rz", "--full-tree", HEART_COMMIT).split(b"\0"):
        if not item:
            continue
        meta, name = item.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if kind == "blob":
            tree[name.decode()] = {"gitMode": mode, "gitBlobSHA1": sha}
    return p, {"producerSHA256": hashlib.sha256(expected).hexdigest(), "originalProducerStatus": p["status"],
               "originalNativeBinarySHA256": BINARY_SHA, "sourceDerivations": proof}, tree

class Commands:
    def __init__(self, root):
        self.root = root
        self.rows = []
        self.live = None
        self.absent = set()

    def run(self, label, argv, cwd, env, seconds):
        require(self.live is None and shutil.disk_usage(self.root).free >= FLOOR, "Own phase capacity unavailable")
        output = self.root / (label + ".log")
        require(not output.exists(), "Original command log must be new")
        began = time.time()
        row = {"label": label, "argv": argv, "cwd": str(cwd), "startedAt": began, "status": "FAIL"}
        self.rows.append(row)
        error = None
        with output.open("xb") as stream:
            child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            self.live = child
            row["pid"] = row["pgid"] = child.pid
            write(self.root / (label + "-started.json"), row)
            try:
                while child.poll() is None:
                    if time.time() - began > seconds or shutil.disk_usage(self.root).free < FLOOR:
                        raise RuntimeError("Owned command deadline or emergency free-space stop")
                    time.sleep(0.25)
                row["exitCode"] = child.returncode
                row["childReaped"] = True
                # Observe once, never signal after the child has been reaped.
                try:
                    os.killpg(child.pid, 0)
                    row["groupPresentAfterExit"] = True
                except ProcessLookupError:
                    self.absent.add(child.pid)
                    row["groupPresentAfterExit"] = False
                require(row["exitCode"] == 0 and row["groupPresentAfterExit"] is False,
                        "Original component command failed or retained an owned group")
                row["status"] = "PASS"
            except BaseException as exc:
                error = exc
                row["error"] = {"type": type(exc).__name__, "message": str(exc)}
            finally:
                if child.poll() is None and child.pid not in self.absent:
                    try:
                        os.killpg(child.pid, 0)
                    except ProcessLookupError:
                        self.absent.add(child.pid)
                    else:
                        os.killpg(child.pid, signal.SIGTERM)
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                            child.wait(timeout=10)
                    row["stoppedOwnedLiveChild"] = True
                self.live = None
                row.update(finishedAt=time.time(), seconds=round(time.time()-began, 3),
                           logSHA256=digest(output), logBytes=output.stat().st_size,
                           noSignalsAfterReap=True)
                write(self.root / (label + "-result.json"), row)
        if error is not None:
            raise error
        return output

def decoded_values(raw_text):
    decoder = json.JSONDecoder()
    result = []
    offset = 0
    while offset < len(raw_text):
        while offset < len(raw_text) and raw_text[offset].isspace():
            offset += 1
        if offset == len(raw_text):
            break
        value, offset = decoder.raw_decode(raw_text, offset)
        result.append(value)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    require(args.root.is_absolute() and args.root.parent == BASE
            and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
            "New bounded private exporter root required")
    args.root.mkdir(mode=0o700)
    os.umask(0o077)
    result = {"protocol": "pinkha-original-source-compiled-definition-recovery-v1", "status": "FAIL",
        "originalCapturedMembersReplaced": False, "sourceAdmission": False, "destinationWrites": False,
        "accountOrSpaceCalls": 0, "nativeEngineBuilds": 0,
        "originalSourceArchiveSHA256": ARCHIVE_SHA, "originalSourceManifestSHA256": MANIFEST_SHA,
        "heartCommit": HEART_COMMIT, "originalNativeBinarySHA256": BINARY_SHA,
        "controllerSHA256": digest(Path(__file__))}
    commands = Commands(args.root)
    inputs = {}
    selected = {}
    try:
        require(digest(BASE / "source-bundle.tar.gz.partial") == ARCHIVE_SHA, "Original archive changed")
        manifest_raw = raw(RECOVERED / "metadata/manifest.json", 32 * 1024**2)
        require(hashlib.sha256(manifest_raw).hexdigest() == MANIFEST_SHA, "Original source manifest changed")
        manifest = json.loads(manifest_raw)
        rows = entries(manifest)
        producer, result["originalProducerAuthority"], git_tree = producer_authority()
        original_cache = ROOTFS / CACHE.lstrip("/")
        cache_rows = {name: row for name, row in rows.items() if name.startswith(CACHE + "/")}
        clone_bytes = sum(row["bytes"] for row in cache_rows.values())
        require(clone_bytes == 846196573 and len(cache_rows) == 41679, "Original complete module-cache census differs")
        estimate = clone_bytes + 512 * 1024**2
        available = shutil.disk_usage(args.root).free
        require(available >= estimate + FLOOR, "Measured source-cache and pure compiler phase unavailable")
        result["resourcePolicy"] = {"freeBytesBefore": available, "measuredModuleCloneBytes": clone_bytes,
            "additionalPureCompileEstimateBytes": 512 * 1024**2, "emergencyFreeBytes": FLOOR,
            "goJobs": 1, "runtimeCores": 2, "reason": "Two-core Oracle host concurrently running one E Go component; own original source-cache copy and pure Go registry model/compiler only."}
        clone = args.root / "go-mod"
        clone.mkdir(mode=0o700)
        for index, (name, row) in enumerate(sorted(cache_rows.items())):
            original = ROOTFS / name.lstrip("/")
            check_member(original, row)
            target = clone / Path(name).relative_to(CACHE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            check_member(target, row)
            if index % 256 == 0:
                require(shutil.disk_usage(args.root).free >= FLOOR, "Own cache-copy emergency stop")
        result["originalModuleCacheCopy"] = {"files": len(cache_rows), "bytes": clone_bytes,
            "allOriginalHashesAndModesMatched": True, "originalCacheWritableUse": False}
        mod = ROOTFS / ORIGINAL_MOD.lstrip("/")
        mod_raw = raw(mod)
        check_member(mod, rows[ORIGINAL_MOD])
        old = ("replace github.com/anyproto/any-sync => " + SYNC).encode()
        new = ("replace github.com/anyproto/any-sync => " + str(ROOTFS / SYNC.lstrip("/"))).encode()
        require(mod_raw.count(old) == 1, "Exactly one original local sync replacement required")
        candidate = args.root / "candidate.mod"
        candidate.write_bytes(mod_raw.replace(old, new))
        source_sum = mod.with_suffix(".sum")
        candidate.with_suffix(".sum").write_bytes(raw(source_sum))
        require(candidate.read_bytes().replace(new, old) == mod_raw, "Module relocation inverse failed")
        inputs[str(candidate)] = digest(candidate)
        inputs[str(candidate.with_suffix(".sum"))] = digest(candidate.with_suffix(".sum"))
        exporter = Path(__file__).with_name("exporter.go")
        exporter_raw = raw(exporter, 64 * 1024)
        require(hashlib.sha256(exporter_raw).hexdigest() == EXPORTER_SHA, "Exact registry-only exporter required")
        main_go = args.root / "exporter.go"
        main_go.write_bytes(exporter_raw)
        inputs[str(main_go)] = EXPORTER_SHA
        work = args.root / "work"; work.mkdir()
        cache = args.root / "go-build"; cache.mkdir()
        goroot = ROOTFS / GOROOT.lstrip("/")
        go = goroot / "bin/go"
        check_member(go, rows[GOROOT + "/bin/go"])
        env = dict(os.environ)
        env.pop("ANYTYPE_EXTRA_RELATIONS", None)
        env.update(GOROOT=str(goroot), GOTOOLCHAIN="local", GOWORK="off", GOFLAGS="-mod=readonly -p=1",
            GOOS="linux", GOARCH="arm64", CGO_ENABLED="0", GOEXPERIMENT="",
            GOPROXY="off", GOSUMDB="off", GOMODCACHE=str(clone), GOCACHE=str(cache),
            GOPATH=str(work / "gopath"), GOTMPDIR=str(work), TMPDIR=str(work),
            GOMAXPROCS="2", GOMEMLIMIT="2GiB", GOTELEMETRY="off")
        heart = ROOTFS / HEART.lstrip("/")
        version = commands.run("original-go-version", [str(go), "version"], heart, env, 10)
        require(version.read_text().strip() == "go version go1.26.5 linux/arm64", "Original toolchain differs")
        result["toolchain"] = {"version": version.read_text().strip(), "sha256": digest(go),
            "CGO_ENABLED": "0", "scope": "pure registry/codecs reproduction, not original native test binary"}
        listing = commands.run("actual-dependencies", [str(go), "list", "-deps", "-json",
            "-modfile=" + str(candidate), str(main_go)], heart, env, 120)
        packages = decoded_values(listing.read_text())
        used = {}
        for package in packages:
            require(not package.get("Error") and not package.get("DepsErrors"), "Actual Go dependency graph has errors")
            directory = Path(package["Dir"])
            for field in ("GoFiles", "CgoFiles", "CFiles", "HFiles", "SFiles", "SysoFiles", "EmbedFiles"):
                for relative in package.get(field, []):
                    path = directory / relative
                    if path == main_go:
                        continue
                    if path.is_relative_to(clone):
                        original_name = CACHE + "/" + str(path.relative_to(clone))
                    else:
                        require(path.is_relative_to(ROOTFS), "Dependency escaped original recovered source closure")
                        original_name = "/" + str(path.relative_to(ROOTFS))
                    require(original_name in rows, "Actual dependency is absent from original full source manifest")
                    row = rows[original_name]
                    info = check_member(path, row)
                    if original_name.startswith(HEART + "/"):
                        relative_heart = original_name[len(HEART)+1:]
                        require(row["git"] is not None and relative_heart in git_tree
                                and row["git"]["git_blob_sha1"] == git_tree[relative_heart]["gitBlobSHA1"],
                                "Original compiled registry dependency differs at actual historical65ca")
                        info["historicalGitBlobSHA1"] = git_tree[relative_heart]["gitBlobSHA1"]
                    used[original_name] = info
                    selected[str(path)] = row
        require(any(name.endswith("/pkg/lib/bundle/relation.gen.go") for name in used)
                and any(name.endswith("/pkg/lib/pb/model/models.pb.go") for name in used),
                "Original registry and generated model must actually compile")
        write(args.root / "compiled-inputs.json", used)
        result["compiledInputFiles"] = len(used)
        result["compiledInputsSHA256"] = digest(args.root / "compiled-inputs.json")
        binary = args.root / "recovered-descriptor-exporter"
        commands.run("build-registry-exporter", [str(go), "build", "-modfile=" + str(candidate),
            "-o", str(binary), str(main_go)], heart, env, 420)
        result["pureRegistryExporterBuilds"] = 1
        result["binary"] = {"sha256": digest(binary), "bytes": binary.stat().st_size}
        commands.run("export-seven", [str(binary), str(args.root / "descriptors")], args.root, env, 30)
        output = json.loads(raw(args.root / "descriptors/export.json", 65536))
        require(output["Contract"] == "pinkha-recovered-compiled-definition-export-v1"
                and output["OriginalCapturedMember"] is False and output["AccountOrSpaceOpened"] is False
                and output["DestinationWrites"] is False
                and output["ProtobufDecodeEqualsRegistry"] is True
                and output["JSONDecodeEqualsRegistry"] is True
                and output["RegistryUnchangedAfterExport"] is True
                and [v["Key"] for v in output["Descriptors"]] == KEYS,
                "Actual exact seven original registry codec outputs required")
        all_files = {"export.json"}
        for descriptor in output["Descriptors"]:
            require(descriptor["Kind"] == "property" and descriptor["ProtobufMessage"] == "anytype.model.Relation",
                    "Original registry output kind differs")
            for field, extension in (("Protobuf", ".pb"), ("JSONView", ".json")):
                member = descriptor[field]
                expected = hashlib.sha256(("property:" + descriptor["Key"]).encode()).hexdigest() + extension
                require(member["Path"] == expected and expected not in all_files, "Closed descriptor path required")
                all_files.add(expected)
                value = raw(args.root / "descriptors" / expected, 4 * 1024**2)
                require(len(value) == member["Bytes"] and hashlib.sha256(value).hexdigest() == member["SHA256"],
                        "Actual recovered descriptor bytes differ")
        require({p.name for p in (args.root / "descriptors").iterdir()} == all_files, "Unexpected descriptor member")
        for name, row in selected.items():
            check_member(Path(name), row)
        for name, sha in inputs.items():
            require(digest(Path(name)) == sha, "Actual exporter or module metadata changed")
        # The full historical recovered source tree stays independent and exact.
        for index, (name, row) in enumerate(rows.items()):
            check_member(ROOTFS / name.lstrip("/"), row)
            if index % 512 == 0:
                require(shutil.disk_usage(args.root).free >= FLOOR, "Own final-verification emergency stop")
        require(digest(RECOVERED / "metadata/manifest.json") == MANIFEST_SHA,
                "Original manifest changed")
        result.update(status="PASS_RECOVERED_ORIGINAL_SEVEN_DESCRIPTORS_NOT_CAPTURED_MEMBERS",
            original59826SourceFilesUnchanged=True, originalCompiledWireAndFullDecodedModelEqual=True,
            descriptors=output["Descriptors"], exportManifestSHA256=digest(args.root / "descriptors/export.json"))
    except BaseException as exc:
        result["firstFailure"] = {"type": type(exc).__name__, "message": str(exc)}
        (args.root / "failure.txt").write_text(traceback.format_exc())
    finally:
        result["commands"] = commands.rows
        result["sourceAdmission"] = False
        result["destinationWrites"] = False
        write(args.root / "receipt.json", result)
    print(json.dumps({k: result.get(k) for k in ("status", "firstFailure", "compiledInputFiles", "binary",
        "original59826SourceFilesUnchanged", "exportManifestSHA256")}, sort_keys=True))
    return 0 if result["status"] == "PASS_RECOVERED_ORIGINAL_SEVEN_DESCRIPTORS_NOT_CAPTURED_MEMBERS" else 1

if __name__ == "__main__":
    def interrupted(signum, frame):
        raise RuntimeError("owned_exporter_interrupted_" + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    raise SystemExit(main())
