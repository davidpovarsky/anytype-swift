#!/usr/bin/env python3
"""Qualified native JSON view and genuine independent-account file transport."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
WHOLE = HERE.parent / "native_whole_source"
WHOLE_HELPER_SHA = "ecca61fb870d72afc51bcad8350c9ce0f2906f08cb403933f54220971f890f71"
BASE_HEART_SHA = "67381c31503518b4c0995b29aecd57c89799c6e8"
HEART_SHA = "973a4970f793230e6325e9f47ea9545f1b6282ad"
DELTA_SHA = "4321eb4f1afc3d991c81ee55b33ef2606d95741ba6ce7295cb5c0b82f4b45217"
JSON_METHOD = "TestLoadedAccountNativeSnapshotJSONView"
PEER_METHOD = "TestLoadedAccountRemoteFilePeer"
METHODS = [JSON_METHOD, PEER_METHOD]
PROTOCOL = "pinkha-native-source-file-peers-v1"

if hashlib.sha256((WHOLE / "run_native.py").read_bytes()).hexdigest() != WHOLE_HELPER_SHA:
    raise RuntimeError("qualified_whole_source_helper_changed")
spec = importlib.util.spec_from_file_location("qualified_whole_source_helpers", WHOLE / "run_native.py")
whole = importlib.util.module_from_spec(spec)
spec.loader.exec_module(whole)
native = whole.native
require, sha, save = native.require, native.sha, native.save
PORTABLE = whole.PORTABLE


def apply_peer_delta(root, snapshots, metadata):
    require(sha(HERE / "source-delta-v1.json") == DELTA_SHA, "peer_delta_identity")
    delta = json.loads((HERE / "source-delta-v1.json").read_bytes())
    require(delta["schema"] == "native-file-peer-source-delta-v1" and
            delta["base_heart_commit"] == BASE_HEART_SHA == whole.HEART_SHA and
            delta["derived_heart_commit"] == HEART_SHA and
            delta["additions"] == 6 and delta["existing_changes"] == 1,
            "peer_delta_lineage")
    expected = [
        "core/application/loaded_file_peer_fixture_test.go",
        "core/application/loaded_file_peer_test.go",
        "core/application/loaded_snapshot_json_test.go",
        "core/application/loaded_space_bundle.go",
        "core/application/loaded_space_prefetch.go",
        "core/block/export/native_raw_json.go",
        "core/files/native_prefetch.go",
    ]
    require([r["path"] for r in delta["files"]] == expected, "peer_delta_exact_scope")
    for row in delta["files"]:
        relative = native.relative_member(row["path"])
        source = HERE / "source" / relative
        native.checked_file(source, (row["bytes"], row["sha256"]))
        raw = source.read_bytes()
        require(row["mode"] == 0o644 and
                hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == row["git_blob_sha1"],
                "peer_source_git_blob")
        logical = str(native.HEART / relative)
        target = root / logical.lstrip("/")
        if row["operation"] == "A":
            require(logical not in snapshots and not target.exists() and not target.is_symlink(),
                    "peer_addition_overwrites_source")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as dst:
                dst.write(raw)
        else:
            require(row["operation"] == "M" and relative.as_posix() ==
                    "core/application/loaded_space_bundle.go" and
                    logical in snapshots and target.is_file() and not target.is_symlink(),
                    "peer_existing_change_scope")
            require(tuple(getattr(target.stat(), key) for key in native.FIELDS) == snapshots[logical],
                    "peer_before_physical_identity")
            native.checked_file(target, (row["before_bytes"], row["before_sha256"]))
            before = target.read_bytes()
            require(hashlib.sha1(b"blob " + str(len(before)).encode() + b"\0" + before).hexdigest() ==
                    row["before_git_blob_sha1"], "peer_before_git_blob")
            target.write_bytes(raw)
        target.chmod(0o644)
        native.checked_file(target, (row["bytes"], row["sha256"]))
        snapshots[logical] = tuple(getattr(target.stat(), key) for key in native.FIELDS)
    save(metadata / "native-file-peer-source-delta-v1.json", delta)
    return delta


def audit_one(stdout, method):
    text = stdout.read_text()
    require(re.findall(r"(?m)^=== RUN\s+(\S+)\s*$", text) == [method] and
            re.findall(r"(?m)^\s*--- PASS:\s+(\S+)\s+\(", text) == [method] and
            re.search(r"(?m)^PASS\s*$", text) and
            not re.search(r"(?m)^\s*--- (?:FAIL|SKIP):", text),
            "exact_new_native_method_required")
    return {"method": method, "named_method_pass": True, "stdout_sha256": sha(stdout)}


class RemoteFileRunner(native.Runner):
    def __init__(self):
        os.umask(0o077)
        self.base = Path(os.environ["RUNNER_TEMP"]) / "pinkha-native-file-peer"
        self.base.mkdir(mode=0o700)
        self.public, self.private = self.base / "public", self.base / "private"
        self.inputs, self.rootfs = self.base / "inputs", self.base / "rootfs"
        for path in (self.public, self.private, self.inputs, self.rootfs):
            path.mkdir(mode=0o700)
        for name in ("commands", "fixtures", "work", "products", "go-build",
                     "source-metadata", "image-data-empty", "peers"):
            (self.private / name).mkdir(mode=0o700)
        self.commands, self.names, self.peer_names = [], [], []
        self.network = None
        self.roles, self.inspect_counter = {}, 0
        self.nonce = secrets.token_hex(16)
        self.result = {
            "schema": "native-file-peer-portable-v1", "status": "RUNNING",
            "controller_sha": os.environ.get("GITHUB_SHA"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "heart_sha": HEART_SHA, "base_heart_sha": native.HEART_SHA,
            "context_heart_sha": native.DERIVED_HEART_SHA, "whole_source_heart_sha": BASE_HEART_SHA,
            "any_sync_sha": native.SYNC_SHA,
            "qualified_helper_sha256": whole.HELPER_SHA,
            "qualified_whole_helper_sha256": WHOLE_HELPER_SHA,
            "builds": 0, "selected_methods": METHODS, "executions": [],
            "networkPayloadVerified": False, "offlineFreshProcessVerified": False,
            "semanticCompleteness": False, "historySemanticsValidated": False,
            "fullSpaceMigrationComplete": False, "hasNativeSourceAdmission": False,
            "permitsDestinationWrites": False,
        }

    def prepare(self):
        require(os.getuid() == 1001 and platform.machine() == "aarch64",
                "qualified_runner_identity")
        require(os.environ.get("GITHUB_ACTIONS") == "true", "genuine_actions_required")
        controller = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        require(controller == os.environ["GITHUB_SHA"] == os.environ["EXPECTED_SOURCE_SHA"],
                "controller_identity")
        self.result["resources_before"] = self.guard(start=True)
        self.result["profile"] = {
            "compiler_network": "none", "peer_network": "owned internal Docker bridge",
            "fresh_disk_cache": True, "copied_warm_cache": False,
            "build_seconds": 1800, "peer_online_seconds": 1080, "reopen_seconds": 240,
            "container_cpus": 1, "container_memory_bytes": 4 * native.GIB,
            "independent_online_wallets": 2, "new_source_methods": METHODS,
        }
        compiler = self.download("PINKHA_NATIVE_COMPILER_URL", "compiler.zip", native.COMPILER)
        source = self.download("PINKHA_NATIVE_SOURCE_URL", "source.tar.gz", native.SOURCE)
        self.result["input_sha256"] = {"compiler": native.COMPILER[1], "source": native.SOURCE[1]}
        with zipfile.ZipFile(compiler) as archive:
            members = archive.infolist()
            require(len(members) == 215 and all(not row.is_dir() for row in members),
                    "compiler_member_census")
            for row in members:
                native.relative_member(row.filename)
            images = [row for row in members if Path(row.filename).name == "compiler-image.tar"]
            require(len(images) == 1 and images[0].file_size == native.IMAGE_TAR[0],
                    "compiler_image_member")
            image = self.inputs / "compiler-image.tar"
            with archive.open(images[0]) as src, image.open("xb") as dst:
                shutil.copyfileobj(src, dst, native.MIB)
        native.checked_file(image, native.IMAGE_TAR)
        self.snapshots, self.result["source"] = native.extract_source(
            source, self.rootfs, self.private / "source-metadata")
        self.result["source"]["context_derivation"] = native.apply_source_delta(
            self.rootfs, self.snapshots, PORTABLE, self.private / "source-metadata")
        self.result["source"]["whole_source_derivation"] = whole.apply_whole_source_delta(
            self.rootfs, self.snapshots, self.private / "source-metadata")
        self.result["source"]["file_peer_derivation"] = apply_peer_delta(
            self.rootfs, self.snapshots, self.private / "source-metadata")
        self.command("load-image", ["sudo", "-n", "docker", "load", "--input", str(image)], 180)
        _, out, _ = self.command("image-inspect", ["sudo", "-n", "docker", "image", "inspect", native.IMAGE], 30)
        info = json.loads(out.read_bytes())[0]
        require(info["Id"] == native.IMAGE and info["Architecture"] == "arm64" and info["Os"] == "linux",
                "qualified_image_identity")
        self.result["compiler_image"] = native.IMAGE
        self.binary = self.private / "products/native-file-peer.test"
        self.result["builds"] += 1
        rc, _, stderr = self.container("build", native.GOROOT / "bin/go",
            ["test", "-c", "-work", "-x", "-p=1", "-mod=readonly",
             "-modfile=" + str(native.ORIGINAL / "candidate.mod"), "-tags",
             native.TAGS + " pinkha_localstore_witness pinkha_native_file_peer_acceptance",
             "-o", str(self.binary), "./core/application"], build=True, seconds=1800)
        require(rc == 0, "native_file_peer_compile_failed")
        require(self.binary.is_file() and 0 < self.binary.stat().st_size < 256 * native.MIB,
                "native_binary_shape")
        with self.binary.open("rb") as stream:
            header = stream.read(20)
        require(header[:6] == b"\x7fELF\x02\x01" and int.from_bytes(header[18:20], "little") == 183,
                "actual_native_arm64_elf")
        work_names = re.findall(rb"(?m)^WORK=([^\r\n]+)$", stderr.read_bytes())
        require(len(work_names) == 1, "one_actual_generated_main_work")
        work = Path(work_names[0].decode())
        require(work.parent == self.private / "work" and re.fullmatch(r"go-build\d+", work.name) and
                work.is_dir() and not work.is_symlink(), "actual_work_scope")
        mains = list(work.glob("*/_testmain.go"))
        require(len(mains) == 1, "actual_generated_main_unique")
        main = mains[0]
        for method in METHODS:
            require(main.read_text().count('"' + method + '"') == 1, "actual_new_test_registration")
        shutil.copyfile(main, self.private / "generated-test-main.go")
        self.result["generated_main"] = {"sha256": sha(main), "bytes": main.stat().st_size,
                                         "origin": "actual -work build", "new_registration": METHODS}
        self.result["binary"] = {"sha256": sha(self.binary), "bytes": self.binary.stat().st_size}
        rc, out, _ = self.container("binary-buildinfo", native.GOROOT / "bin/go",
                                    ["version", "-m", str(self.binary)], seconds=30)
        require(rc == 0 and out.read_text().splitlines()[0] == str(self.binary) + ": go1.26.5",
                "actual_native_toolchain")
        rc, out, _ = self.container("binary-selected-list", self.binary,
            ["-test.list=^(" + "|".join(METHODS) + ")$"], seconds=30)
        require(rc == 0 and sorted(out.read_text().splitlines()) == sorted(METHODS),
                "actual_two_new_named_methods")
        self.result["actual_named_methods_sha256"] = sha(out)

    def json_view(self):
        rc, stdout, _ = self.container("native-json-view", self.binary,
            ["-test.v", "-test.run=^" + JSON_METHOD + "$", "-test.count=1", "-test.timeout=210s"])
        row = {"method": JSON_METHOD, "role": "separate LocalOnly JSON fixture", "exit_code": rc}
        self.result["executions"].append(row)
        require(rc == 0, "native_json_view_method_exit")
        row.update(audit_one(stdout, JSON_METHOD))
        root = self.private / "fixtures" / JSON_METHOD
        note = json.loads((root / "native-snapshot-json-view.json").read_bytes())
        count = note["capturedObjects"]
        require(count >= 2 and all(note[key] == count for key in (
            "actualNativeProtoRoundTrips", "deterministicViews", "originalPBMembersVerified",
            "privateJSONMembersVerified")) and note["rawSnapshotUnchanged"] is True,
            "native_json_view_actual_roundtrips")
        pair = note["privateConsumerTextPair"]
        require(pair["nativeCreatedTextOnly"] is True and pair["fileInfoAbsent"] is True and
                pair["fileKeysAbsent"] is True, "private_text_pair_scope")
        require(pair["protobufPath"] == "native-json-consumer-text.pb" and
                pair["jsonPath"] == "native-json-consumer-text.json", "private_text_pair_paths")
        for prefix in ("protobuf", "json"):
            native.checked_file(root / pair[prefix + "Path"],
                                (pair[prefix + "Bytes"], pair[prefix + "SHA256"]))
        envelope = json.loads((root / pair["jsonPath"]).read_bytes())
        require(envelope["Contract"] == "pinkha-native-snapshot-json-v1" and
                envelope["ObjectID"] == pair["objectID"] and
                envelope["SnapshotSHA256"] == pair["protobufSHA256"] and
                envelope["SnapshotBytes"] == pair["protobufBytes"] and
                envelope["Snapshot"]["fileInfo"] is None and
                envelope["Snapshot"]["fileKeys"] is None, "private_text_pair_original_binding")
        row["status"] = "PASS"
        self.result["nativeJSONView"] = {
            "status": "PASS", "capturedObjects": count, "receipt_sha256": sha(root / "native-snapshot-json-view.json"),
            "privateTextPair": {key: value for key, value in pair.items() if key != "objectID"},
        }

    def inspect(self, name, label, network, root, finished=False):
        _, out, _ = self.command(label, ["sudo", "-n", "docker", "inspect", name], 30)
        info = json.loads(out.read_bytes())[0]
        host, config, state = info["HostConfig"], info["Config"], info["State"]
        require(info["Image"] == native.IMAGE and host["ReadonlyRootfs"] and
                host["NetworkMode"] == network and config["User"] == "1001:1001" and
                host["Memory"] == 4 * native.GIB and host["MemorySwap"] == 4 * native.GIB and
                host["NanoCpus"] == 1_000_000_000 and host["PidsLimit"] == 256 and
                host["CapDrop"] == ["ALL"] and "no-new-privileges" in host["SecurityOpt"] and
                not state["OOMKilled"], "real_peer_container_profile")
        expected = sorted([
            (str(root), "/private", True),
            (str(self.binary), "/products/native-file-peer.test", False),
            (str(self.rootfs / str(native.LIBDIR).lstrip("/")), str(native.LIBDIR), False),
            (str(self.private / "image-data-empty"), "/var/lib/postgresql/data", False),
        ])
        actual = sorted((v["Source"], v["Destination"], v["RW"]) for v in info["Mounts"] if v["Type"] == "bind")
        require(actual == expected and set(host["Tmpfs"]) == {"/tmp"}, "peer_private_mount_isolation")
        if finished:
            require(not state["Running"] and state["ExitCode"] == 0, "native_peer_real_exit")
        else:
            require(state["Running"] and state["Pid"] > 0, "native_peer_running")
        return info

    def launch(self, role, phase, network):
        key = role + "-" + phase
        root = self.private / "peers" / role
        if phase == "online":
            root.mkdir(mode=0o700)
            (root / "account-root").mkdir(mode=0o700)
            save(root / "ownership.json", {"protocol": PROTOCOL, "nonce": self.nonce,
                                          "role": role, "synthetic_only": True})
        else:
            require(role == "member" and root.is_dir(), "only_member_own_store_reopen")
        name = "pinkha-file-peer-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"] + "-" + key
        self.names.append(name)
        self.peer_names.append(name)
        wrapper = ("/products/native-file-peer.test -test.v -test.run=^" + PEER_METHOD +
                   "$ -test.count=1 -test.timeout=" + ("1050s" if phase == "online" else "210s") +
                   " > /private/native-" + phase + ".stdout 2> /private/native-" + phase + ".stderr; "
                   "status=$?; printf '%s\\n' \"$status\" > /private/" + phase + ".exit.tmp; "
                   "mv /private/" + phase + ".exit.tmp /private/" + phase + ".exit; exit \"$status\"")
        argv = ["sudo", "-n", "docker", "run", "--detach", "--pull=never", "--name", name,
                "--network", network, "--read-only", "--log-driver", "none", "--user", "1001:1001",
                "--cpus", "1", "--memory", "4g", "--memory-swap", "4g", "--pids-limit", "256",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--workdir", "/private",
                "--tmpfs", "/tmp:rw,nosuid,noexec,size=64m,mode=1777", "--entrypoint", "/bin/sh"]
        mounts = [
            (root, "/private", True), (self.binary, "/products/native-file-peer.test", False),
            (self.rootfs / str(native.LIBDIR).lstrip("/"), str(native.LIBDIR), False),
            (self.private / "image-data-empty", "/var/lib/postgresql/data", False),
        ]
        for src, dst, write in mounts:
            require(src.exists() and not src.is_symlink(), "peer_mount_exists")
            argv += ["--mount", "type=bind,source=" + str(src) + ",target=" + dst + ("" if write else ",readonly")]
        for key_env, value in sorted({
            "GOMAXPROCS": "1", "GOMEMLIMIT": "3072MiB", "TMPDIR": "/tmp",
            "PINKHA_SOURCE_FILE_ROLE": role, "PINKHA_SOURCE_FILE_PHASE": phase,
            "PINKHA_SOURCE_FILE_NONCE": self.nonce,
        }.items()):
            argv += ["--env", key_env + "=" + value]
        argv += [native.IMAGE, "-c", wrapper]
        self.command("start-" + key, argv, 30)
        info = self.inspect(name, "inspect-" + key, network, root)
        self.roles[key] = {"name": name, "root": root, "network": network,
                           "hostPID": info["State"]["Pid"], "phase": phase, "role": role}
        return self.roles[key]

    def wait_phase(self, owned, label, seconds):
        root, phase, role = owned["root"], owned["phase"], owned["role"]
        path = root / (label + ".json")
        deadline = time.monotonic() + seconds
        while not path.exists():
            require(time.monotonic() < deadline, "native_peer_phase_deadline_" + role + "_" + label)
            exit_path = root / (phase + ".exit")
            require(not exit_path.exists(), "native_peer_exited_before_" + role + "_" + label)
            for suffix in ("stdout", "stderr"):
                log = root / ("native-" + phase + "." + suffix)
                require(not log.exists() or log.stat().st_size < 64 * native.MIB, "peer_log_budget")
            self.guard()
            time.sleep(0.25)
        require(path.is_file() and not path.is_symlink() and path.stat().st_size < 256 * 1024,
                "native_phase_receipt_shape")
        row = json.loads(path.read_bytes())
        require(row["protocol"] == PROTOCOL and row["nonce"] == self.nonce and
                row["role"] == role and row["phase"] == label and
                row["fullSpaceMigrationComplete"] is False and row["historySemanticsValidated"] is False,
                "native_owned_phase_binding")
        require(row["walletCreateCalls"] == (1 if phase == "online" else 0) and
                row["walletRecoverCalls"] == (0 if phase == "online" else 1),
                "native_wallet_call_counts")
        return row

    def command_phase(self, owned, label, **body):
        root = owned["root"]
        path = root / (label + ".command.json")
        require(not path.exists(), "owned_phase_not_replayed")
        payload = {"Protocol": PROTOCOL, "Nonce": self.nonce, "Phase": label, **body}
        tmp = root / (label + ".command.tmp")
        with tmp.open("xb") as stream:
            stream.write(json.dumps(payload, sort_keys=True).encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)

    def finished(self, owned):
        deadline = time.monotonic() + 60
        exit_path = owned["root"] / (owned["phase"] + ".exit")
        while not exit_path.exists():
            require(time.monotonic() < deadline, "native_peer_shutdown_deadline")
            time.sleep(0.2)
        require(exit_path.read_text().strip() == "0", "native_peer_binary_exit")
        self.inspect(owned["name"], "finished-" + owned["role"] + "-" + owned["phase"],
                     owned["network"], owned["root"], finished=True)
        audit = audit_one(owned["root"] / ("native-" + owned["phase"] + ".stdout"), PEER_METHOD)
        self.result["executions"].append({**audit, "role": owned["role"], "phase": owned["phase"],
                                          "status": "PASS", "exit_code": 0})

    def peers(self):
        self.network = "pinkha-file-peer-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]
        self.command("network-create", ["sudo", "-n", "docker", "network", "create", "--internal",
            "--driver", "bridge", "--label", "pinkha.owner=" + self.network, self.network], 30)
        _, out, _ = self.command("network-inspect", ["sudo", "-n", "docker", "network", "inspect", self.network], 30)
        info = json.loads(out.read_bytes())[0]
        require(info["Internal"] and info["Driver"] == "bridge" and
                info["Labels"]["pinkha.owner"] == self.network and not info["Containers"],
                "owned_internal_bridge")
        owner = self.launch("owner", "online", self.network)
        member = self.launch("member", "online", self.network)
        owner_row = self.wait_phase(owner, "identity", 210)
        member_row = self.wait_phase(member, "identity", 150)
        a, b = owner_row["identity"], member_row["identity"]
        require(set(a) == set(b) == {"AccountID", "PeerID", "IP", "Namespace", "Port", "PID"} and
                a["AccountID"] != b["AccountID"] and a["PeerID"] != b["PeerID"] and
                a["Namespace"] != b["Namespace"] and a["IP"] != b["IP"] and
                owner["hostPID"] != member["hostPID"], "actual_independent_native_accounts")
        source = owner_row["source"]
        require(set(source) == {"SpaceID", "PageID", "FileObjectID", "FileID", "Variants"} and
                len(source["Variants"]) == 1 and source["Variants"][0]["PlaintextBytes"] == 2 * native.MIB,
                "actual_owner_random_payload_contract")
        variant = source["Variants"][0]
        require(set(variant) == {"Path", "ContentID", "MetadataID", "MetadataSHA256", "PlaintextSHA256",
                                "MetadataBytes", "PlaintextBytes"} and variant["MetadataBytes"] > 0,
                "controller_transfers_only_identity_and_hash_expectations")
        self.command_phase(owner, "join", Peer=b)
        grant = self.wait_phase(owner, "grant", 90)
        require(grant["memberAccountID"] == b["AccountID"] and grant["aclHead"] and
                grant["memberPermission"] > 0, "actual_reader_grant")
        self.command_phase(member, "join", Peer=a, Source=source, ACLHead=grant["aclHead"])
        joined = self.wait_phase(member, "joined", 180)
        require(joined["actualNativeFileObjectID"] == source["FileObjectID"] and
                joined["actualNativeFileID"] == source["FileID"] and
                joined["aclHead"] == grant["aclHead"] and
                joined["memberPermission"] == grant["memberPermission"],
                "actual_native_tree_and_file_identity_delivered")
        self.command("network-disconnect", ["sudo", "-n", "docker", "network", "disconnect",
                                            self.network, member["name"]], 30)
        _, out, _ = self.command("network-cold-inspect", ["sudo", "-n", "docker", "network", "inspect", self.network], 30)
        cold_network = json.loads(out.read_bytes())[0]
        require(len(cold_network["Containers"]) == 1 and
                {v["Name"] for v in cold_network["Containers"].values()} == {owner["name"]},
                "receiver_disconnected_from_owned_bridge")
        self.command_phase(member, "cold")
        cold = self.wait_phase(member, "cold", 120)
        require(cold["actualIPv4"] in (None, []) and cold["missingLocalRoot"] is True and
                cold["explicitFileGap"] is True and
                cold["sourceReceipt"]["CurrentFilePayloadCompleteness"] is False,
                "actual_remote_only_file_refused_locally")
        self.command("network-reconnect", ["sudo", "-n", "docker", "network", "connect",
                                           self.network, member["name"]], 30)
        info = self.inspect(member["name"], "inspect-member-reconnected", self.network, member["root"])
        interfaces = info["NetworkSettings"]["Networks"]
        require(set(interfaces) == {self.network}, "one_owned_reconnected_interface")
        new_ip = interfaces[self.network]["IPAddress"]
        require(new_ip and new_ip != a["IP"], "actual_dynamic_reconnect_ip")
        reconnected = dict(b)
        reconnected["IP"] = new_ip
        self.command_phase(owner, "reroute", Peer=reconnected)
        self.wait_phase(owner, "rerouted", 60)
        self.command_phase(member, "prefetch", Peer=a)
        received = self.wait_phase(member, "received", 150)
        prefetch = received["prefetch"]
        require(received["networkPayloadVerified"] is True and
                received["fullPlaintextBytes"] == variant["PlaintextBytes"] and
                received["exactMetadataBytesVerified"] is True and
                received["nativeOwnerReferenceVerified"] is True and
                received["nativeJSONViewsVerified"] > 0 and
                prefetch["NativeFetches"] > 0 and
                all(prefetch[k] is True for k in (
                    "AccountSessionAuthorizedAtFinalRead", "CapturedFileIDsBoundToUnchangedCheckpoint",
                    "EveryFetchedBlockRereadFromLocalStore", "RequiresNewFrozenCapture")) and
                all(prefetch[k] is False for k in ("FilePayloadCompleteness", "HasNativeSourceAdmission",
                                                 "PermitsDestinationWrites")),
                "actual_authorized_rpc_and_full_payload_capture")
        self.command_phase(member, "stop")
        final_member = self.wait_phase(member, "final", 60)
        self.finished(member)
        self.command_phase(owner, "stop")
        final_owner = self.wait_phase(owner, "final", 60)
        self.finished(owner)
        require(final_member["accountStopped"] and final_member["testPassed"] and
                final_owner["accountStopped"] and final_owner["testPassed"], "native_accounts_stopped")
        reopen = self.launch("member", "reopen", "none")
        reopened = self.wait_phase(reopen, "reopen-final", 210)
        require(reopened["identity"]["AccountID"] == b["AccountID"] and
                reopened["identity"]["PeerID"] == b["PeerID"] and
                reopened["identity"]["Namespace"] not in (a["Namespace"], b["Namespace"]) and
                reopen["hostPID"] not in (owner["hostPID"], member["hostPID"]) and
                reopened["actualIPv4"] in (None, []) and
                reopened["offlineFreshProcess"] and reopened["testPassed"] and reopened["accountStopped"] and
                reopened["sourceSpaceID"] == source["SpaceID"] and
                reopened["fullPlaintextBytes"] == variant["PlaintextBytes"] and
                reopened["exactMetadataBytesVerified"] and reopened["nativeOwnerReferenceVerified"],
                "actual_offline_fresh_process_member_reopen")
        self.finished(reopen)
        self.result["networkPayloadVerified"] = True
        self.result["offlineFreshProcessVerified"] = True
        self.result["peerObservations"] = {
            "owner_account_sha256": hashlib.sha256(a["AccountID"].encode()).hexdigest(),
            "member_account_sha256": hashlib.sha256(b["AccountID"].encode()).hexdigest(),
            "distinct_wallets": True, "distinct_network_namespaces": True,
            "online_wallet_create_calls": 2, "online_wallet_recover_calls": 0,
            "reopen_own_wallet_recover_calls": 1, "copied_owner_wallet_or_store": False,
            "native_reader_grant": True, "native_file_object_delivered": True,
            "receiver_local_root_absent_before_prefetch": True,
            "native_fetches": prefetch["NativeFetches"],
            "each_fetched_block_reread_locally": True,
            "full_plaintext_sha256": variant["PlaintextSHA256"],
            "full_plaintext_bytes": variant["PlaintextBytes"],
            "exact_metadata_sha256": variant["MetadataSHA256"],
            "exact_metadata_bytes": variant["MetadataBytes"],
            "offline_fresh_process_reopen": True,
            "private_phase_receipts": {
                role + "/" + label: sha(self.private / "peers" / role / (label + ".json"))
                for role, labels in (("owner", ("identity", "grant", "rerouted", "final")),
                                      ("member", ("identity", "joined", "cold", "received", "final", "reopen-final")))
                for label in labels
            },
        }

    def execute(self):
        self.prepare()
        self.json_view()
        self.peers()
        for name, before in self.snapshots.items():
            path = self.rootfs / name.lstrip("/")
            require(tuple(getattr(path.stat(), key) for key in native.FIELDS) == before,
                    "readonly_compiled_source_changed")
        self.result["compiled_source_unchanged"] = True
        require(len(self.result["executions"]) == 4 and
                all(row["status"] == "PASS" for row in self.result["executions"]),
                "exact_new_json_and_three_peer_executions")
        self.result["status"] = "NATIVE_JSON_AND_REMOTE_FILE_PEERS_PASS"

    def finalize(self):
        cleanup = []
        for index, name in enumerate(self.peer_names):
            try:
                rc, _, _ = self.command("peer-cleanup-" + str(index),
                    ["sudo", "-n", "docker", "rm", "--force", name], 30, tolerate=True, guard=False)
                cleanup.append({"name": name, "returncode": rc})
            except Exception as exc:
                cleanup.append({"name": name, "error": type(exc).__name__})
        self.names = [name for name in self.names if name not in self.peer_names]
        self.result["peer_container_cleanup"] = cleanup
        if any(row.get("returncode") != 0 for row in cleanup):
            self.result.update(status="FAIL", peer_cleanup_error="owned_peer_container_cleanup_incomplete")
        if self.network:
            try:
                rc, _, _ = self.command("network-cleanup",
                    ["sudo", "-n", "docker", "network", "rm", self.network],
                    30, tolerate=True, guard=False)
                self.result["network_cleanup"] = {"name": self.network, "returncode": rc}
                if rc:
                    self.result.update(status="FAIL", network_cleanup_error="owned_internal_bridge_cleanup")
            except Exception as exc:
                self.result.update(status="FAIL", network_cleanup_error=type(exc).__name__)
        super().finalize()


def main():
    runner = RemoteFileRunner()
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
    print(json.dumps({key: runner.result.get(key) for key in
                      ("status", "error", "controller_sha", "run_id", "builds")}))
    return 0 if runner.result["status"] == "NATIVE_JSON_AND_REMOTE_FILE_PEERS_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
