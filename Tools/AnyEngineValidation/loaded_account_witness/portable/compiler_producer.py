#!/usr/bin/env python3
"""Finite compiler-only producer. This program never receives Heart source or invokes Go."""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import resource
import shutil
import signal
import stat
import subprocess
import sys
import time

MIB = 1024 ** 2
GIB = 1024 ** 3
ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
BASE = "postgres@sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d"
BASE_PROOF = HERE.parent / "native-compiler-support.json"
BASE_PROOF_SHA = "ca681802575e0fd0d135be251184b89949dde0f46a957755ff2c019fa5013a76"
WORKFLOW = ".github/workflows/pinkha-loaded-account-arm64-compiler.yml"
OWN_PATHS = [
    "Tools/AnyEngineValidation/loaded_account_witness/portable/compiler_producer.py",
    "Tools/AnyEngineValidation/loaded_account_witness/portable/compiler-acquire.sh",
    "Tools/AnyEngineValidation/loaded_account_witness/portable/compiler-install.sh",
    "Tools/AnyEngineValidation/loaded_account_witness/portable/compiler-contract.json",
    "Tools/AnyEngineValidation/loaded_account_witness/native-compiler-support.json",
    WORKFLOW,
]
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
START_FREE = 8 * GIB
MIN_FREE = 2950000000
START_MEMORY = 9 * GIB
MIN_MEMORY = GIB
OUTPUT_CAP = 3 * GIB
TOTAL_SECONDS = 1200
RAW_CAP = 8 * MIB


class Refusal(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def decode(body):
    return json.loads(body, object_pairs_hook=unique)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def tuple_of(s):
    return {k: str(getattr(s, k)) for k in (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns")}


def file_row(path, cap):
    path = pathlib.Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        before = os.fstat(f.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "regular_single_file_required")
        require(before.st_size <= cap, "file_size_limit")
        h = hashlib.sha256()
        size = 0
        started = time.monotonic()
        while True:
            require(time.monotonic() - started <= 120, "file_hash_deadline")
            data = f.read(MIB)
            if not data:
                break
            size += len(data)
            require(size <= cap, "stream_file_limit")
            h.update(data)
        after = os.fstat(f.fileno())
    require(tuple_of(before) == tuple_of(after) == tuple_of(os.lstat(path)), "file_changed_during_hash")
    return {"path": str(path), "bytes": size, "sha256": h.hexdigest(), "physical": tuple_of(after)}


def save(path, value):
    body = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    require(len(body) <= 4 * MIB, "receipt_limit")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())


def memory_available():
    rows = pathlib.Path("/proc/meminfo").read_text().splitlines()
    return int(next(x.split()[1] for x in rows if x.startswith("MemAvailable:"))) * 1024


def usage(root):
    total = 0
    count = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            require(not (pathlib.Path(parent) / name).is_symlink(), "output_directory_link")
        for name in files:
            p = pathlib.Path(parent) / name
            s = p.lstat()
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, "output_special_entry")
            total += s.st_size
            count += 1
            require(count <= 4096 and total <= OUTPUT_CAP, "output_inventory_limit")
    return {"files": count, "logical_bytes": total}


def resources(root, start=False):
    s = os.statvfs(root)
    free = s.f_bavail * s.f_frsize
    mem = memory_available()
    require(free >= (START_FREE if start else MIN_FREE), "compiler_producer_disk_floor")
    require(mem >= (START_MEMORY if start else MIN_MEMORY), "compiler_producer_memory_floor")
    return {"free_bytes": free, "memory_available_bytes": mem, "outputs": usage(root)}


def group_absent(child):
    child.poll()
    try:
        os.killpg(child.pid, 0)
    except ProcessLookupError:
        return True
    return False


def stop_group(child):
    require(child.pid > 1, "invalid_owned_pid")
    if group_absent(child):
        return {"already_absent": True, "returncode": child.poll()}
    # start_new_session makes the owned Popen leader the process-group leader.
    for sig, seconds in ((signal.SIGTERM, 3), (signal.SIGKILL, 5)):
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            if group_absent(child):
                child.wait(timeout=1)
                return {"already_absent": False, "last_signal": int(sig), "returncode": child.returncode}
            time.sleep(0.1)
    raise Refusal("owned_cli_group_not_absent")


class Producer:
    def __init__(self, out, context):
        self.out = out
        self.context = context
        self.started = time.monotonic()
        self.commands = []
        self.containers = {}
        self.cleanups = []
        self.base_id = None
        self.contract = None
        self.executables = {}
        for name in ("git", "docker"):
            path = shutil.which(name, path=ENV["PATH"])
            require(path is not None, "missing_host_tool_" + name)
            self.executables[name] = str(pathlib.Path(path).resolve())
        self.labels = {
            "org.anytapy.scope": "loaded-account-compiler",
            "org.anytapy.run": context["run_id"],
            "org.anytapy.attempt": context["run_attempt"],
            "org.anytapy.source": context["source_sha"],
        }

    def command(self, name, argv, seconds, *, cleanup=False, accepted=(0,), file_cap=None):
        require(re.fullmatch(r"[a-z0-9-]+", name) is not None, "command_name")
        require(argv[0] in self.executables, "unexpected_host_command")
        argv = [self.executables[argv[0]], *argv[1:]]
        record = {"name": name, "argv": argv, "timeout_seconds": seconds, "started": False,
                  "primary_error": None, "cleanup_error": None}
        self.commands.append(record)
        index = len(self.commands) - 1
        prefix = self.out / "commands" / ("%03d-%s" % (index, name))
        stdout = prefix.with_suffix(".stdout")
        stderr = prefix.with_suffix(".stderr")
        started = time.monotonic()
        child = None
        error = None
        fo = fe = None
        try:
            fo = stdout.open("xb")
            fe = stderr.open("xb")
            if not cleanup:
                require(time.monotonic() - self.started < TOTAL_SECONDS, "producer_total_deadline")
                record["resources_before"] = resources(self.out)
            child = subprocess.Popen(argv, cwd=ROOT, env=ENV, stdin=subprocess.DEVNULL,
                                     stdout=fo, stderr=fe, start_new_session=True,
                                     preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (4 * GIB, 4 * GIB)))
            record.update(started=True, pid=child.pid, pgid=child.pid)
            try:
                observed_group = os.getpgid(child.pid)
            except ProcessLookupError:
                require(child.poll() is not None, "unexplained_owned_leader_absence")
            else:
                require(observed_group == child.pid, "owned_group_identity")
            while child.poll() is None:
                require(time.monotonic() - started < seconds, "command_timeout")
                require(stdout.stat().st_size <= RAW_CAP and stderr.stat().st_size <= RAW_CAP, "raw_output_limit")
                if file_cap is not None and file_cap[0].exists():
                    require(file_cap[0].stat().st_size <= file_cap[1], "image_archive_limit")
                if not cleanup:
                    require(time.monotonic() - self.started < TOTAL_SECONDS, "producer_total_deadline")
                    resources(self.out)
                time.sleep(0.25)
            record["returncode"] = child.wait()
            require(time.monotonic() - started <= seconds, "command_finished_after_deadline")
            require(stdout.stat().st_size <= RAW_CAP and stderr.stat().st_size <= RAW_CAP, "raw_output_limit")
            if not cleanup:
                require(time.monotonic() - self.started < TOTAL_SECONDS, "producer_total_deadline")
                record["resources_after"] = resources(self.out)
            require(child.returncode in accepted, "command_exit_%s" % child.returncode)
        except BaseException as exc:
            error = exc
            record["primary_error"] = {"type": type(exc).__name__, "message": str(exc)}
        finally:
            if child is not None:
                try:
                    record["owned_group_cleanup"] = stop_group(child)
                except BaseException as exc:
                    record["cleanup_error"] = {"type": type(exc).__name__, "message": str(exc)}
                    if error is None:
                        error = exc
            record["elapsed_seconds"] = time.monotonic() - started
            record["persistence_errors"] = []
            for label, operation in (
                ("stdout_flush", lambda: None if fo is None else (fo.flush(), os.fsync(fo.fileno()))),
                ("stderr_flush", lambda: None if fe is None else (fe.flush(), os.fsync(fe.fileno()))),
                ("stdout", lambda: file_row(stdout, RAW_CAP)),
                ("stderr", lambda: file_row(stderr, RAW_CAP)),
            ):
                try:
                    value = operation()
                    if label in ("stdout", "stderr"):
                        record[label] = value
                except BaseException as exc:
                    record["persistence_errors"].append({"phase": label, "type": type(exc).__name__, "message": str(exc)})
                    if error is None:
                        error = exc
            for label, stream in (("stdout_close", fo), ("stderr_close", fe)):
                if stream is None:
                    continue
                try:
                    stream.close()
                except BaseException as exc:
                    record["persistence_errors"].append({"phase": label, "type": type(exc).__name__, "message": str(exc)})
                    if error is None:
                        error = exc
            try:
                save(prefix.with_suffix(".json"), record)
            except BaseException as exc:
                record["persistence_errors"].append({"phase": "receipt", "type": type(exc).__name__, "message": str(exc)})
                if error is None:
                    error = exc
        if error is not None:
            raise error
        return stdout.read_bytes(), stderr.read_bytes(), record

    def git(self, name, args):
        out, _, _ = self.command(name, ["git", "-c", "core.packedGitWindowSize=16m",
                                      "-c", "core.packedGitLimit=64m", "-C", str(ROOT), *args], 20)
        return out

    def source_snapshot(self, phase):
        require(self.git(phase + "-head", ["rev-parse", "HEAD"]).decode().strip() == self.context["source_sha"],
                "github_actual_head_mismatch")
        require(self.git(phase + "-status", ["status", "--porcelain=v1", "--untracked-files=all"]) == b"",
                "controller_checkout_dirty")
        rows = {}
        for i, rel in enumerate(OWN_PATHS):
            body = self.git(phase + "-blob-%02d" % i, ["show", self.context["source_sha"] + ":" + rel])
            require(len(body) <= 128 * 1024, "source_blob_limit")
            row = file_row(ROOT / rel, 128 * 1024)
            require(row["bytes"] == len(body) and row["sha256"] == digest(body), "git_physical_source_mismatch")
            row["git_blob"] = self.git(phase + "-oid-%02d" % i,
                                     ["rev-parse", self.context["source_sha"] + ":" + rel]).decode().strip()
            rows[rel] = row
        save(self.out / ("source-" + phase + ".json"), rows)
        return rows

    def inspect(self, target, name, *, cleanup=False):
        out, _, _ = self.command(name, ["docker", "container", "inspect", target], 15, cleanup=cleanup)
        data = decode(out)
        require(isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict), "container_inspect_shape")
        return data[0]

    def check_container(self, kind, info):
        owned = self.containers[kind]
        require(info["Name"] == "/" + owned["name"], "container_name_mismatch")
        require(re.fullmatch(r"[0-9a-f]{64}", info["Id"]) is not None, "container_id_shape")
        if owned.get("cid"):
            require(info["Id"] == owned["cid"], "container_id_changed")
        require(info["Image"] == self.base_id and info["Config"]["Image"] == BASE, "container_base_identity")
        for key, value in self.labels.items():
            require(info["Config"]["Labels"].get(key) == value, "container_label_mismatch")
        require(info["Config"]["Labels"].get("org.anytapy.phase") == kind, "container_phase_mismatch")
        require(info["Config"]["Entrypoint"] == ["/bin/sh"], "container_entrypoint")
        require(info["Config"]["Cmd"] == ["/scripts/compiler-" + kind + ".sh"], "container_command")
        host = info["HostConfig"]
        require(host["NetworkMode"] == ("bridge" if kind == "acquire" else "none"), "container_network")
        require(host["Memory"] == 2 * GIB and host["MemorySwap"] == 2 * GIB
                and host["NanoCpus"] == 2000000000 and host["PidsLimit"] == 128, "container_resource_contract")
        require(host["LogConfig"]["Type"] == "none" and not host["Privileged"], "container_privilege_or_logging")
        require(isinstance(host["Binds"], list)
                and all(isinstance(value, str) for value in host["Binds"])
                and sorted(host["Binds"]) == sorted(owned["binds"]), "container_bindings")
        require(host["Tmpfs"] == {"/var/lib/postgresql/data": "rw,noexec,nosuid,nodev,size=16777216,mode=0700"},
                "postgres_volume_not_private_tmpfs")
        require(not host.get("Devices") and not host.get("CapAdd"), "container_extra_privileges")
        return info

    def run_container(self, kind, timeout):
        name = "pinkha-c-compiler-%s-%s-%s" % (self.context["run_id"], self.context["run_attempt"], kind)
        output = self.out / kind
        output.mkdir(mode=0o700)
        binds = [str(HERE) + ":/scripts:ro", str(output) + ":/out:rw"]
        if kind == "install":
            binds.append(str(self.out / "acquire") + ":/inputs:ro")
        owned = {"name": name, "binds": binds, "creation_attempted": False, "cid": None}
        self.containers[kind] = owned
        out, _, _ = self.command(kind + "-name-preflight",
                                ["docker", "container", "ls", "--all", "--no-trunc", "--format", "{{.Names}}"], 15)
        require(name not in out.decode().splitlines(), "owned_container_name_already_exists")
        args = ["docker", "create", "--name", name, "--platform", "linux/arm64",
                "--network", "bridge" if kind == "acquire" else "none",
                "--memory", str(2 * GIB), "--memory-swap", str(2 * GIB), "--cpus", "2",
                "--pids-limit", "128", "--log-driver", "none", "--stop-signal", "SIGTERM",
                "--tmpfs", "/var/lib/postgresql/data:rw,noexec,nosuid,nodev,size=16777216,mode=0700",
                "--entrypoint", "/bin/sh"]
        for key, value in {**self.labels, "org.anytapy.phase": kind}.items():
            args += ["--label", key + "=" + value]
        for binding in binds:
            args += ["--volume", binding]
        args += [BASE, "/scripts/compiler-" + kind + ".sh"]
        owned["creation_attempted"] = True
        save(self.out / (kind + "-create-intent.json"), owned)
        out, _, _ = self.command(kind + "-create", args, 30)
        cid = out.decode().strip()
        require(re.fullmatch(r"[0-9a-f]{64}", cid) is not None, "create_cid_shape")
        owned["cid"] = cid
        before = self.check_container(kind, self.inspect(cid, kind + "-inspect-before"))
        require(before["State"]["Status"] == "created" and not before["State"]["Running"], "new_container_not_created")
        self.command(kind + "-start", ["docker", "start", "--attach", cid], timeout)
        after = self.check_container(kind, self.inspect(cid, kind + "-inspect-after"))
        require(after["State"]["Status"] == "exited" and not after["State"]["Running"]
                and after["State"]["Pid"] == 0 and after["State"]["ExitCode"] == 0, "container_not_successfully_exited")
        owned["terminal"] = after["State"]
        return after

    def cleanup(self):
        for kind, owned in reversed(list(self.containers.items())):
            if not owned["creation_attempted"]:
                continue
            row = {"kind": kind, "name": owned["name"], "error": None}
            self.cleanups.append(row)
            try:
                # A successful exact-name listing distinguishes no create from an inspect error.
                names, _, _ = self.command(kind + "-cleanup-list",
                                           ["docker", "container", "ls", "--all", "--no-trunc", "--format", "{{.Names}}"],
                                           15, cleanup=True)
                if owned["name"] not in names.decode().splitlines():
                    require(owned["cid"] is None, "previous_container_disappeared")
                    row["status"] = "NOT_CREATED"
                    continue
                info = self.check_container(kind, self.inspect(owned["name"], kind + "-cleanup-before", cleanup=True))
                owned["cid"] = info["Id"]
                if info["State"]["Running"]:
                    self.command(kind + "-stop", ["docker", "stop", "--time", "10", info["Id"]], 20, cleanup=True)
                final = self.check_container(kind, self.inspect(info["Id"], kind + "-cleanup-final", cleanup=True))
                require(final["State"]["Running"] is False and final["State"]["Pid"] == 0, "owned_container_still_active")
                row.update(status="STOPPED", cid=info["Id"], state=final["State"],
                           retained_container=True, filesystem_custody="IMAGE_ARCHIVED_ONLY_IF_RECORDED")
            except BaseException as exc:
                row["error"] = {"type": type(exc).__name__, "message": str(exc)}
        save(self.out / "cleanup.json", self.cleanups)
        require(not any(x["error"] for x in self.cleanups), "compiler_container_cleanup_failed")

    def tree_map(self, root, cap, max_files):
        rows = {}
        total = 0
        for parent, dirs, files in os.walk(root, followlinks=False):
            for name in dirs:
                require(not (pathlib.Path(parent) / name).is_symlink(), "payload_directory_link")
            for name in sorted(files):
                p = pathlib.Path(parent) / name
                rel = p.relative_to(root).as_posix()
                require(rel not in rows and "\\" not in rel, "payload_name_collision")
                row = file_row(p, min(cap, 256 * MIB))
                total += row["bytes"]
                require(total <= cap and len(rows) < max_files, "payload_inventory_budget")
                rows[rel] = row
        return rows

    def image_inspect(self, target, name):
        out, _, _ = self.command(name, ["docker", "image", "inspect", target], 20)
        data = decode(out)
        require(isinstance(data, list) and len(data) == 1, "image_inspect_shape")
        return data[0]

    def produce(self):
        proof_bytes = BASE_PROOF.read_bytes()
        require(digest(proof_bytes) == BASE_PROOF_SHA, "original_image_proof_changed")
        proof = decode(proof_bytes)
        require(proof["status"] == "PASS_IMMUTABLE_IMAGE_TOOL_INVENTORY" and not proof["gcc_present"]
                and not proof["gpp_present"], "base_compiler_claim_changed")
        self.contract = decode((HERE / "compiler-contract.json").read_bytes())
        require(self.contract["base_image"] == BASE and self.contract["base_proof_sha256"] == BASE_PROOF_SHA,
                "compiler_contract_origin")
        self.command("docker-version", ["docker", "version", "--format", "{{json .}}"], 20)
        self.command("pull-fixed-base", ["docker", "pull", "--platform", "linux/arm64", BASE], 180)
        base = self.image_inspect(BASE, "base-image")
        require(base["Architecture"] == "arm64" and base["Os"] == "linux", "base_platform")
        require(BASE in base["RepoDigests"], "base_repository_digest")
        expected_layers = [x["diff_id"] for x in proof["layer_order"]]
        require(base["RootFS"]["Layers"] == expected_layers, "base_uncompressed_layer_identity")
        require(base["Config"]["Volumes"] == {"/var/lib/postgresql/data": {}}, "base_volume_contract")
        self.base_id = base["Id"]
        save(self.out / "base-binding.json", {
            "requested_oci_index": BASE, "actual_engine_image_id": self.base_id,
            "selected_arm64_manifest": "sha256:ddc1c45d23db7f0702f5a2727e28f24cbb75746f625c8c5083a190e50cf01740",
            "canonical_config": "sha256:31b7df755869f3d5b0a8a87e0f29ea85cac62a522f008681d304e311160d181f",
            "actual_inspection": base, "original_proof_sha256": BASE_PROOF_SHA})
        self.run_container("acquire", 300)
        acquired = self.tree_map(self.out / "acquire", 512 * MIB, 256)
        packages = {k: v for k, v in acquired.items() if k.startswith("packages/")}
        require(4 <= len(packages) <= 96 and all(re.fullmatch(r"packages/[A-Za-z0-9_.+~-]+\.apk", k) for k in packages),
                "package_file_set")
        require((self.out / "acquire/index-before.sha256").read_bytes() ==
                (self.out / "acquire/index-after.sha256").read_bytes(), "signed_index_changed_during_fetch")
        require((self.out / "acquire/phases.txt").read_text().splitlines() ==
                ["update", "fetch-recursive", "verify-signatures", "acquisition-complete"], "acquisition_phase_order")
        save(self.out / "acquired-inputs.json", acquired)
        self.run_container("install", 240)
        require(self.tree_map(self.out / "acquire", 512 * MIB, 256) == acquired, "acquired_input_changed_by_installer")
        installed = self.tree_map(self.out / "install", 32 * MIB, 128)
        before_keys = {k.removeprefix("keys-before/"): v["sha256"] for k, v in installed.items() if k.startswith("keys-before/")}
        after_keys = {k.removeprefix("keys-after/"): v["sha256"] for k, v in installed.items() if k.startswith("keys-after/")}
        acquired_keys = {k.removeprefix("base-keys/"): v["sha256"] for k, v in acquired.items() if k.startswith("base-keys/")}
        require(before_keys == after_keys == acquired_keys and len(before_keys) >= 1, "trusted_signing_keys_changed")
        require((self.out / "install/phases.txt").read_text().splitlines() ==
                ["verify-same-apks", "offline-install", "tool-observations", "installation-complete"], "installation_phase_order")
        tools = {}
        for line in (self.out / "install/tools.tsv").read_text().splitlines():
            fields = line.split("\t")
            require(len(fields) == 5 and fields[0] not in tools and re.fullmatch(r"[0-9a-f]{64}", fields[3]), "tool_observation_shape")
            require(fields[1].startswith("/usr/bin/") and fields[2].startswith("/usr/"), "compiler_tool_path")
            require(re.fullmatch(r"[0-7]{3,4}:[0-9]+:[0-9]+:[1-9][0-9]*", fields[4]), "compiler_tool_metadata")
            tools[fields[0]] = dict(zip(("name", "path", "resolved_path", "sha256", "mode_uid_gid_size"), fields))
        require(set(tools) == {"gcc", "g++", "cc", "c++", "ld", "as", "ar", "ranlib"}, "compiler_tool_set")
        for target in ("gcc-target.txt", "gpp-target.txt"):
            require((self.out / "install" / target).read_bytes() == b"aarch64-alpine-linux-musl\n", "compiler_target")
        package_versions = {}
        for block in (self.out / "install/installed-after.txt").read_text().split("\n\n"):
            fields = [line.split(":", 1) for line in block.splitlines() if line.startswith(("P:", "V:", "A:"))]
            values = dict(fields)
            if "P" in values:
                require(len(fields) == 3 and set(values) == {"P", "V", "A"} and values["P"] not in package_versions,
                        "installed_package_identity_shape")
                package_versions[values["P"]] = {"version": values["V"], "arch": values["A"]}
        require({"gcc", "g++", "musl-dev", "binutils"} <= set(package_versions), "required_compiler_packages_missing")
        support = []
        for line in (self.out / "install/compiler-support.tsv").read_text().splitlines():
            fields = line.split("\t")
            require(len(fields) == 5 and fields[1].startswith("/usr/") and fields[2].startswith("/usr/")
                    and re.fullmatch(r"[0-9a-f]{64}", fields[3]), "compiler_support_shape")
            support.append(fields)
        require(len(support) == 5 and {x[0] for x in support} == {"cc1", "cc1plus", "collect2", "lto1", "lto-wrapper"},
                "compiler_support_set")
        save(self.out / "installed-inputs.json", installed)
        save(self.out / "installed-packages.json", package_versions)
        tag = "anytapy-loaded-account-compiler:%s-%s" % (self.context["run_id"], self.context["run_attempt"])
        cid = self.containers["install"]["cid"]
        out, _, _ = self.command("commit-compiler-image",
                                ["docker", "commit", "--pause=false", "--change", "ENTRYPOINT []",
                                 "--change", 'CMD ["/bin/sh"]', cid, tag], 60)
        image_id = out.decode().strip()
        require(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id), "committed_image_id")
        image_info = self.image_inspect(image_id, "compiler-image")
        require(image_info["Id"] == image_id and image_info["Architecture"] == "arm64"
                and image_info["Os"] == "linux", "compiler_image_identity")
        require(image_info["RootFS"]["Layers"][:len(expected_layers)] == expected_layers
                and len(image_info["RootFS"]["Layers"]) == len(expected_layers) + 1, "compiler_base_layers")
        archive = self.out / "compiler-image.tar"
        self.command("save-compiler-image", ["docker", "image", "save", "--output", str(archive), image_id],
                     180, file_cap=(archive, 2 * GIB))
        original = file_row(archive, 2 * GIB)
        reread = file_row(archive, 2 * GIB)
        require(original == reread, "compiler_archive_independent_readback")
        save(self.out / "compiler-image-binding.json", {
            "image_id": image_id, "tag": tag, "inspection": image_info,
            "archive_original": original, "archive_independent_readback": reread,
            "tools": tools, "compiler_support": support, "installed_packages": package_versions,
            "package_installation_network": "none",
            "signature_verification_commands": ["acquire-start", "install-start"],
            "compiler_invocations": "version/target/program-path observations only",
            "c_cpp_compilations": 0, "go_queries": 0, "native_builds": 0, "native_tests": 0,
            "consumer_admission": False, "migration_authorization": False})
        return {"image_id": image_id, "archive": original, "tools": tools}


def loaded_sources():
    rows = {}
    for name, module in list(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if not value:
            continue
        path = pathlib.Path(value).resolve()
        if path.is_relative_to(ROOT):
            require(name == "__main__" and path == pathlib.Path(__file__).resolve(), "unexpected_repository_import")
            rows[name] = file_row(path, 128 * 1024)
    require(set(rows) == {"__main__"}, "missing_actual_producer_module")
    return rows


def context():
    require(os.geteuid() != 0 and platform.system() == "Linux" and platform.machine() == "aarch64", "fresh_linux_arm64_runner")
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted",
            "github_hosted_runner_required")
    require(os.environ.get("GITHUB_REPOSITORY") == "davidpovarsky/anytype-swift", "github_repository")
    require(os.environ.get("RUNNER_OS") == "Linux" and os.environ.get("RUNNER_ARCH") == "ARM64", "github_runner_platform")
    result = {k: os.environ.get(v, "") for k, v in {
        "source_sha": "GITHUB_SHA", "run_id": "GITHUB_RUN_ID", "run_attempt": "GITHUB_RUN_ATTEMPT",
        "ref": "GITHUB_REF", "job": "GITHUB_JOB", "workflow_ref": "GITHUB_WORKFLOW_REF"}.items()}
    require(re.fullmatch(r"[0-9a-f]{40}", result["source_sha"]) is not None, "github_source_sha")
    require(os.environ.get("EXPECTED_SOURCE_SHA") == result["source_sha"], "requested_source_sha")
    require(all(re.fullmatch(r"[1-9][0-9]*", result[k]) for k in ("run_id", "run_attempt")), "run_identity")
    require(result["ref"].startswith("refs/heads/") and result["job"] == "compiler", "compiler_workflow_context")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", required=True)
    parser.parse_args()
    os.umask(0o077)
    inherited_as = resource.getrlimit(resource.RLIMIT_AS)
    require(inherited_as[1] == resource.RLIM_INFINITY or inherited_as[1] >= 4 * GIB, "host_address_space_hard_limit")
    resource.setrlimit(resource.RLIMIT_AS, (512 * MIB, 4 * GIB))
    ctx = context()
    parent = pathlib.Path(os.environ["RUNNER_TEMP"])
    require(parent.is_dir() and parent.resolve() == parent, "runner_temp_canonical")
    out = parent / "pinkha-loaded-account-compiler"
    out.mkdir(mode=0o700)
    (out / "commands").mkdir(mode=0o700)
    result = {"schema": 1, "context": ctx, "inherited_address_space_limits": list(inherited_as),
              "controller_soft_address_space": 512 * MIB, "child_address_space": 4 * GIB, "status": "FAILED", "primary_error": None, "final_errors": [],
              "native_builds": 0, "native_tests": 0, "go_queries": 0, "consumer_admission": False,
              "account_or_semantic_authority": False, "destination_writes_permitted": False}
    p = Producer(out, ctx)
    before = None
    original_handlers = {}
    def interrupted(sig, _frame):
        raise Refusal("producer_signal_%s" % sig)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        original_handlers[sig] = signal.signal(sig, interrupted)
    try:
        result["resources_start"] = resources(out, start=True)
        before = p.source_snapshot("before")
        result["loaded_source_before"] = loaded_sources()
        result["host_tool_before"] = {name: file_row(path, 128 * MIB) for name, path in p.executables.items()}
        result["python_runtime"] = {"version": sys.version, "executable": file_row(pathlib.Path(sys.executable).resolve(), 128 * MIB)}
        result["compiler"] = p.produce()
    except BaseException as exc:
        result["primary_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        for label, operation in (
            ("owned_cleanup", p.cleanup),
            ("source_after", lambda: p.source_snapshot("after")),
            ("loaded_source_after", loaded_sources),
            ("host_tool_after", lambda: {name: file_row(path, 128 * MIB) for name, path in p.executables.items()}),
            ("final_resources", lambda: resources(out)),
        ):
            try:
                value = operation()
                result[label] = value
                if label == "source_after":
                    require(before is not None and value == before, "current_controller_source_changed")
                if label in ("loaded_source_after", "host_tool_after"):
                    require(value == result.get(label.replace("_after", "_before")), "executed_source_or_tool_changed")
            except BaseException as exc:
                result["final_errors"].append({"phase": label, "type": type(exc).__name__, "message": str(exc)})
        if result["primary_error"] is None and not result["final_errors"]:
            result["status"] = "COMPILER_PRODUCED_REQUIRES_INDEPENDENT_ARTIFACT_ADMISSION"
        result["commands"] = p.commands
        result["containers"] = p.containers
        result["elapsed_seconds"] = time.monotonic() - p.started
        result["public_evidence_scope"] = "package/source/tool/image data only; no credentials or native fixture"
        try:
            save(out / "result.json", result)
        except BaseException as exc:
            result["final_errors"].append({"phase": "final_result_persistence", "type": type(exc).__name__, "message": str(exc)})
            result["status"] = "FAILED"
        finally:
            for sig, handler in original_handlers.items():
                try:
                    signal.signal(sig, handler)
                except BaseException as exc:
                    result["final_errors"].append({"phase": "signal_restoration", "signal": int(sig),
                                                   "type": type(exc).__name__, "message": str(exc)})
                    result["status"] = "FAILED"
    print(json.dumps({"status": result["status"], "result": str(out / "result.json"),
                      "primary_error": result["primary_error"], "final_errors": result["final_errors"],
                      "native_builds": 0, "native_tests": 0}, sort_keys=True))
    return 0 if result["primary_error"] is None and not result["final_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
