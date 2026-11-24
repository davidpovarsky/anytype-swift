#!/usr/bin/env python3
"""Consume the original qualified inputs and run the four pending native controls.

Only safe receipts and an encrypted private evidence archive leave the runner.
Source snapshots, compiler inputs and existing native assertions are immutable.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request
import urllib.parse
import zipfile

GIB = 1024 ** 3
MIB = 1024 ** 2
COMPILER = (618081186, "9804f35c068e01cc90e9eca1edc08820dda9892b1d7f8db10e18d2724f57ef94")
SOURCE = (369332584, "bf746ea6bd965927d0e17b0d59772a55bc7542ab80629d97d4dd8ae8193c2f04")
IMAGE_TAR = (528820224, "80497b93ed0cc6432b9351669c0f2757119f7e7975190566c73b38044fde33f2")
IMAGE = "sha256:a65540a5628f185087f6c567ca5ea465f76d79026dc1919239c55409c6c9a1f7"
MANIFEST_SHA = "2a0a8807ffaae25b3596a387e47f42e5893d9a83ee64d161d029712d0acaced9"
AUDITOR_SHA = "49ce372e9a4bf22c8b513409c570aae1d8c9f0053a6ce218c461483c4c4d42ea"
GENERATED_SHA = "749604e1b5eba79ed351a8f0a09bdd64aca9412d833b887adc5140cb42515715"
HEART_SHA = "24dc6393b30e6d1d80ec28ff624060af9bb4327a"
SYNC_SHA = "c005bd6cde8d8f8a6007c35f06894f3d89f9f07c"
HEART = Path("/mnt/development/projects/worktrees/anytype-heart-loaded-account-witness-20261123")
SYNC = Path("/mnt/development/projects/worktrees/any-sync-loaded-account-witness-20261123")
ORIGINAL = Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123/Tools/AnyEngineValidation/loaded_account_witness")
GOROOT = Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/toolchains/go1.26.5/go")
CACHE = Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/attempt4/cache")
LIBDIR = Path("/mnt/development/projects/worktrees/anytype-heart-semantic-page-20261123/deps/libs/linux-arm64-musl")
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg pinkha_loaded_account_witness pinkha_loaded_account_witness_acceptance"
METHODS = [
    "TestLoadedAccountWitnessBindsActualAccountSessionAndHead",
    "TestLoadedAccountWitnessRefusesUnboundSessionsAndLoadFallback",
    "TestLoadedAccountWitnessACLAndSessionCancellationReleaseActualLocks",
    "TestLoadedAccountWitnessRejectsForeignOwnerStoredHeadAndStoppedApp",
]
FIELDS = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(MIB), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_file(path, expected):
    require(path.is_file() and not path.is_symlink(), "input_not_regular")
    require((path.stat().st_size, sha(path)) == expected, "input_identity_mismatch")


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)


def relative_member(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and not p.is_absolute() and str(p) == name and
            "\\" not in name and "\0" not in name and
            all(v not in (".", "..") for v in p.parts), "unsafe_archive_member")
    return p


def extract_source(archive, root, metadata):
    """Stream each regular entry; compare all source bytes with the pinned manifest."""
    observed = {}
    total = 0
    with tarfile.open(archive, mode="r|gz") as source:
        for member in source:
            p = relative_member(member.name)
            require(member.isfile() and not member.issym() and not member.islnk(), "nonregular_source_entry")
            require(0 <= member.size <= 512 * MIB and member.name not in observed, "source_entry_budget_or_duplicate")
            require(p.parts[0] in ("rootfs", "metadata"), "source_entry_root")
            if p.parts[0] == "metadata":
                require(member.name in ("metadata/start.json", "metadata/manifest.json", "metadata/final.json") and
                        member.size <= 32 * MIB, "source_metadata_budget")
                target = metadata / p.name
            else:
                target = root / Path(*p.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            gh = hashlib.sha1(("blob " + str(member.size) + "\0").encode())
            read = 0
            with source.extractfile(member) as src, target.open("xb") as dst:
                for chunk in iter(lambda: src.read(MIB), b""):
                    read += len(chunk)
                    require(read <= member.size, "source_entry_overrun")
                    h.update(chunk)
                    gh.update(chunk)
                    dst.write(chunk)
            require(read == member.size, "source_entry_truncated")
            target.chmod(member.mode & 0o777)
            observed[member.name] = {"sha256": h.hexdigest(), "bytes": read,
                                     "git_sha1": gh.hexdigest(), "mode": member.mode & 0o777}
            total += read
            require(len(observed) <= 59829 and total <= 1250 * MIB, "source_archive_budget")
    checked_file(metadata / "manifest.json", (22617055, MANIFEST_SHA))
    manifest = json.loads((metadata / "manifest.json").read_bytes())
    final = json.loads((metadata / "final.json").read_bytes())
    require(manifest["heart_commit"] == HEART_SHA and manifest["any_sync_commit"] == SYNC_SHA and
            manifest["selected_methods"] == METHODS, "source_native_identity")
    require(final["status"] == "SOURCE_EXPORTED" and final["manifest_sha256"] == MANIFEST_SHA and
            final["files"] == 59826 and final["logical_bytes"] == 1204807504, "source_export_result")
    table = manifest["files"]
    require(table["schema"] == "loaded-account-source-file-columns-v1" and len(table["rows"]) == 59826,
            "source_manifest_shape")
    expected = set()
    selected = 0
    logical = 0
    snapshots = {}
    for name, physical, kind, values, digest, has_git, origin, retained, extra in table["rows"]:
        require(name.startswith("/"), "source_absolute_origin")
        key = "rootfs/" + name.lstrip("/")
        relative_member(key)
        require(key not in expected, "source_manifest_duplicate")
        expected.add(key)
        actual = observed[key]
        if kind == "native_git_blob_only":
            size, mode = extra["git_bytes"], extra["archive_mode"]
        else:
            info = dict(zip(FIELDS, values))
            size, mode = int(info["st_size"]), stat.S_IMODE(int(info["st_mode"]))
        require(actual["sha256"] == digest and actual["bytes"] == size and actual["mode"] == mode,
                "source_file_origin_mismatch")
        if has_git:
            require(actual["git_sha1"] == origin["git_blob_sha1"] and
                    bool(mode & 0o111) == (origin["git_mode"] == "100755"), "native_git_blob_mismatch")
        p = root / name.lstrip("/")
        snapshots[name] = tuple(getattr(p.stat(), k) for k in FIELDS)
        logical += size
        selected += retained
    require(set(observed) == expected | {"metadata/start.json", "metadata/manifest.json", "metadata/final.json"} and
            logical == 1204807504 and selected == 11626, "source_exact_census")
    return snapshots, {"files": len(expected), "logical_bytes": logical,
                       "retained_graph_files": selected, "manifest_sha256": MANIFEST_SHA,
                       "original_physical_identity_reused": False}


def generated_main(work_root, stderr):
    """Bind Go's actual -work directory; never assume a cache object is generated source."""
    matches = re.findall(rb"(?m)^WORK=([^\r\n]+)$", stderr.read_bytes())
    require(len(matches) == 1, "single_actual_go_work_required")
    work = Path(matches[0].decode("utf-8", "strict"))
    require(work.parent == work_root and re.fullmatch(r"go-build\d+", work.name) and
            work.is_dir() and not work.is_symlink(), "actual_go_work_scope")
    candidates = list(work.glob("*/_testmain.go"))
    exact = [p for p in candidates if p.is_file() and not p.is_symlink() and
             p.stat().st_size == 3282 and sha(p) == GENERATED_SHA]
    require(len(candidates) == 1 and len(exact) == 1, "actual_generated_main_identity")
    return exact[0]


class Runner:
    def __init__(self):
        os.umask(0o077)
        self.base = Path(os.environ["RUNNER_TEMP"]) / "pinkha-loaded-account-native"
        self.base.mkdir(mode=0o700)
        self.public = self.base / "public"
        self.private = self.base / "private"
        self.inputs = self.base / "inputs"
        self.rootfs = self.base / "rootfs"
        for p in (self.public, self.private, self.inputs, self.rootfs):
            p.mkdir(mode=0o700)
        for n in ("commands", "fixtures", "work", "products", "go-build", "source-metadata", "image-data-empty"):
            (self.private / n).mkdir(mode=0o700)
        self.commands = []
        self.names = []
        self.result = {"schema": "loaded-account-portable-native-v1", "status": "RUNNING",
                       "controller_sha": os.environ.get("GITHUB_SHA"),
                       "run_id": os.environ.get("GITHUB_RUN_ID"),
                       "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                       "heart_sha": HEART_SHA, "any_sync_sha": SYNC_SHA,
                       "selected_methods": METHODS, "methods": [], "builds": 0,
                       "semanticCompleteness": False, "filePayloadCompleteness": False,
                       "hasNativeSourceAdmission": False, "permitsDestinationWrites": False}

    def guard(self, start=False):
        mem = int(re.search(r"(?m)^MemAvailable:\s+(\d+)", Path("/proc/meminfo").read_text())[1]) * 1024
        disk = shutil.disk_usage(self.base).free
        require(mem >= (9 * GIB if start else GIB), "host_memory_floor")
        require(disk >= (12 * GIB if start else 2 * GIB), "host_disk_floor")
        return {"available_memory": mem, "free_disk": disk}

    def command(self, label, args, seconds, *, tolerate=False, guard=True):
        require(len(self.commands) < 48, "command_budget")
        out = self.private / "commands" / (label + ".stdout")
        err = self.private / "commands" / (label + ".stderr")
        record = {"label": label, "argv": args, "seconds_limit": seconds}
        self.commands.append(record)
        started = time.monotonic()
        with out.open("xb") as stdout, err.open("xb") as stderr:
            p = subprocess.Popen(args, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                while p.poll() is None:
                    require(time.monotonic() - started < seconds, "command_deadline_" + label)
                    require(out.stat().st_size + err.stat().st_size < 64 * MIB, "command_output_budget")
                    if guard:
                        self.guard()
                    time.sleep(2)
            except BaseException:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(10)
                raise
        record.update(returncode=p.returncode, elapsed=round(time.monotonic() - started, 3),
                      stdout_sha256=sha(out), stderr_sha256=sha(err))
        save(self.private / "commands.json", self.commands)
        require(tolerate or p.returncode == 0, "command_failed_" + label)
        return p.returncode, out, err

    def download(self, env, name, expected):
        url = os.environ.pop(env)
        require(url.startswith("https://") and urllib.parse.urlsplit(url).hostname == "release-assets.githubusercontent.com",
                "private_carrier_signed_origin")
        target = self.inputs / name
        h = hashlib.sha256()
        count = 0
        try:
            with urllib.request.urlopen(url, timeout=60) as response, target.open("xb") as out:
                require(response.status == 200, "private_carrier_http_status")
                for chunk in iter(lambda: response.read(MIB), b""):
                    count += len(chunk)
                    require(count <= expected[0], "private_carrier_size_overrun")
                    h.update(chunk)
                    out.write(chunk)
        except Exception as exc:
            raise RuntimeError("private_carrier_download_" + type(exc).__name__) from None
        require((count, h.hexdigest()) == expected, "private_carrier_input_mismatch")
        return target

    def container(self, label, entry, args, *, build=False, seconds=240):
        name = "pinkha-loaded-native-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"] + "-" + label
        self.names.append(name)
        argv = ["sudo", "-n", "docker", "run", "--pull=never", "--name", name,
                "--network", "none", "--read-only", "--log-driver", "none", "--user", "1001:1001",
                "--cpus", "1", "--memory", "4g", "--memory-swap", "4g", "--pids-limit", "256",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--workdir", str(HEART),
                "--entrypoint", str(entry)]
        mounts = [(self.rootfs / str(p).lstrip("/"), p, False) for p in (HEART, SYNC, ORIGINAL, GOROOT, LIBDIR, CACHE / "go-mod")]
        mounts += [(self.private / "go-build", CACHE / "go-build", build),
                   (self.private / "work", self.private / "work", True),
                   (self.private / "work", Path("/tmp"), True),
                   (self.private / "products", self.private / "products", build),
                   (self.private / "fixtures", self.private / "fixtures", True),
                   (self.private / "image-data-empty", Path("/var/lib/postgresql/data"), False)]
        for src, dst, write in mounts:
            require(src.is_dir() and not src.is_symlink(), "mount_source_missing")
            argv += ["--mount", "type=bind,source=" + str(src) + ",target=" + str(dst) + ("" if write else ",readonly")]
        env = {"CGO_ENABLED": "1", "CC": "gcc", "CXX": "g++", "GOOS": "linux", "GOARCH": "arm64",
               "GOMAXPROCS": "1", "GOMEMLIMIT": "3072MiB", "GOTOOLCHAIN": "local", "GOWORK": "off",
               "GOFLAGS": "-mod=readonly -p=1", "GOEXPERIMENT": "", "GOPROXY": "off", "GOSUMDB": "off",
               "GOMODCACHE": str(CACHE / "go-mod"), "GOCACHE": str(CACHE / "go-build"),
               "GOPATH": str(self.private / "work/gopath"), "GOTMPDIR": str(self.private / "work"),
               "TMPDIR": str(self.private / "work"), "HOME": str(self.private / "work/home"),
               "CGO_LDFLAGS": "-L" + str(LIBDIR),
               "PATH": str(GOROOT / "bin") + ":/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
               "PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT": str(self.private / "fixtures")}
        for k, v in sorted(env.items()):
            argv += ["--env", k + "=" + v]
        argv += [IMAGE, *args]
        rc, stdout, stderr = self.command(label, argv, seconds, tolerate=True)
        _, inspection, _ = self.command(label + "-inspect", ["sudo", "-n", "docker", "inspect", name], 30)
        info = json.loads(inspection.read_bytes())[0]
        require(info["Image"] == IMAGE and info["HostConfig"]["ReadonlyRootfs"] and
                info["HostConfig"]["NetworkMode"] == "none" and info["Config"]["User"] == "1001:1001" and
                not info["State"]["OOMKilled"] and not info["State"]["Running"] and
                info["State"]["ExitCode"] == rc, "native_container_state")
        expected_mounts = sorted((str(dst), write) for _, dst, write in mounts)
        actual_mounts = sorted((v["Destination"], v["RW"]) for v in info["Mounts"])
        require(actual_mounts == expected_mounts, "native_container_mounts")
        return rc, stdout, stderr

    def execute(self):
        require(os.getuid() == 1001 and platform.machine() == "aarch64", "qualified_runner_identity")
        self.result["resources_before"] = self.guard(start=True)
        self.result["profile"] = {"fresh_disk_cache": True, "copied_warm_cache": False,
                                  "build_seconds": 3000, "test_seconds": 240,
                                  "container_memory_bytes": 4 * GIB, "container_cpus": 1}
        here = Path(__file__).resolve().parent
        controller = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        require(controller == os.environ["GITHUB_SHA"] == os.environ["EXPECTED_SOURCE_SHA"], "controller_commit")
        checked_file(here.parent / "native_audit.py", ((here.parent / "native_audit.py").stat().st_size, AUDITOR_SHA))
        compiler = self.download("PINKHA_NATIVE_COMPILER_URL", "compiler.zip", COMPILER)
        source = self.download("PINKHA_NATIVE_SOURCE_URL", "source.tar.gz", SOURCE)
        self.result["input_sha256"] = {"compiler": COMPILER[1], "source": SOURCE[1]}
        with zipfile.ZipFile(compiler) as archive:
            members = archive.infolist()
            require(len(members) == 215 and all(not v.is_dir() for v in members), "compiler_member_census")
            for v in members:
                relative_member(v.filename)
            candidates = [v for v in members if PurePosixPath(v.filename).name == "compiler-image.tar"]
            require(len(candidates) == 1 and candidates[0].file_size == IMAGE_TAR[0], "compiler_image_member")
            image = self.inputs / "compiler-image.tar"
            with archive.open(candidates[0]) as src, image.open("xb") as dst:
                shutil.copyfileobj(src, dst, MIB)
        checked_file(image, IMAGE_TAR)
        self.snapshots, self.result["source"] = extract_source(source, self.rootfs, self.private / "source-metadata")
        self.command("load-image", ["sudo", "-n", "docker", "load", "--input", str(image)], 180)
        _, out, _ = self.command("image-inspect", ["sudo", "-n", "docker", "image", "inspect", IMAGE], 30)
        imageinfo = json.loads(out.read_bytes())[0]
        require(imageinfo["Id"] == IMAGE and imageinfo["Architecture"] == "arm64" and imageinfo["Os"] == "linux", "qualified_image_identity")
        self.result["compiler_image"] = IMAGE
        binary = self.private / "products/loaded-account.test"
        self.result["builds"] += 1
        rc, _, stderr = self.container("build", GOROOT / "bin/go",
            ["test", "-c", "-work", "-x", "-p=1", "-mod=readonly", "-modfile=" + str(ORIGINAL / "candidate.mod"),
             "-tags", TAGS, "-o", str(binary), "./core/application"], build=True, seconds=3000)
        require(rc == 0, "native_compile_failed")
        require(binary.is_file() and 0 < binary.stat().st_size <= 256 * MIB, "native_binary_shape")
        with binary.open("rb") as f:
            header = f.read(20)
            require(header[:6] == b"\x7fELF\x02\x01" and int.from_bytes(header[18:20], "little") == 183,
                    "native_binary_arm64_elf")
        main = generated_main(self.private / "work", stderr)
        shutil.copyfile(main, self.private / "generated-test-main.go")
        self.result["generated_main"] = {"path": str(main), "sha256": GENERATED_SHA, "bytes": 3282,
                                         "origin": "actual -work build directory"}
        self.result["binary"] = {"bytes": binary.stat().st_size, "sha256": sha(binary)}
        rc, out, _ = self.container("binary-buildinfo", GOROOT / "bin/go", ["version", "-m", str(binary)], seconds=30)
        require(rc == 0 and out.read_text().splitlines()[0] == str(binary) + ": go1.26.5", "actual_binary_toolchain")
        module_spec = importlib.util.spec_from_file_location("original_native_auditor", here.parent / "native_audit.py")
        auditor = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(auditor)
        require(auditor.METHODS == METHODS, "original_native_method_selection")
        for index, method in enumerate(METHODS, 1):
            row = {"method": method, "status": "FAIL"}
            self.result["methods"].append(row)
            rc, stdout, _ = self.container("method-" + str(index), binary,
                ["-test.v", "-test.run=^" + method + "$", "-test.count=1", "-test.timeout=210s"])
            row["exit_code"] = rc
            try:
                require(rc == 0, "native_method_exit")
                row["audit"] = auditor.audit_method(self.private / "fixtures", stdout, method)
                row["status"] = "PASS"
            except Exception as exc:
                row["error"] = str(exc)
        for name, before in self.snapshots.items():
            path = self.rootfs / name.lstrip("/")
            require(tuple(getattr(path.stat(), k) for k in FIELDS) == before, "readonly_source_changed")
        self.result["source_unchanged"] = True
        require(len(self.result["methods"]) == 4 and all(v["status"] == "PASS" for v in self.result["methods"]), "native_four_method_acceptance")
        self.result["status"] = "FOUR_NATIVE_METHODS_PASS"

    def finalize(self):
        cleanup = []
        for index, name in enumerate(self.names):
            try:
                rc, _, _ = self.command("cleanup-" + str(index), ["sudo", "-n", "docker", "rm", "--force", name], 30, tolerate=True, guard=False)
                cleanup.append({"name": name, "returncode": rc})
            except Exception as exc:
                cleanup.append({"name": name, "error": type(exc).__name__})
        self.result["container_cleanup"] = cleanup
        if any(v.get("returncode") != 0 for v in cleanup):
            self.result.update(status="FAIL", cleanup_error="owned_container_cleanup_incomplete")
        self.result["command_count"] = len(self.commands)
        save(self.private / "result.json", self.result)
        # Preserve raw logs, original fixtures, binary and actual generated main. Source/compiler bytes
        # already have immutable private carrier copies; the newly built cache is disposable.
        tar_path = self.base / "private-evidence.tar.gz"
        with tarfile.open(tar_path, "w:gz", compresslevel=3) as archive:
            for path in sorted(self.private.iterdir()):
                if path.name not in ("go-build", "work"):
                    archive.add(path, arcname="private/" + path.name, recursive=True)
        encrypted = self.public / "private-evidence.cms"
        pem = Path(__file__).resolve().parent / "custody-recipient.pem"
        self.command("encrypt-private", ["openssl", "cms", "-encrypt", "-binary", "-aes-256-gcm", "-outform", "DER",
            "-in", str(tar_path), "-out", str(encrypted), "-recip", str(pem),
            "-keyopt", "rsa_padding_mode:oaep", "-keyopt", "rsa_oaep_md:sha256"], 180, guard=False)
        self.result["private_custody"] = {"encryption": "CMS AES-256-GCM RSA-OAEP-SHA256", "plaintext_sha256": sha(tar_path),
                                          "plaintext_bytes": tar_path.stat().st_size, "ciphertext_sha256": sha(encrypted),
                                          "ciphertext_bytes": encrypted.stat().st_size, "recipient_sha256": sha(pem),
                                          "recipient_readback": "PENDING_PRIVATE_RECIPIENT"}
        save(self.public / "result.json", self.result)


def main():
    runner = Runner()
    def interrupted(signum, frame):
        raise RuntimeError("interrupted_signal_" + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        runner.execute()
    except BaseException as exc:
        runner.result.update(status="FAIL", error_type=type(exc).__name__, error=str(exc))
    finally:
        try:
            runner.finalize()
        except Exception as exc:
            runner.result.update(status="FAIL", custody_error_type=type(exc).__name__)
            save(runner.public / "result.json", runner.result)
    print(json.dumps({k: runner.result.get(k) for k in ("status", "error", "controller_sha", "run_id", "builds")}))
    return 0 if runner.result["status"] == "FOUR_NATIVE_METHODS_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
