#!/usr/bin/env python3
"""New native schemas and failed file-peer continuation; JSON/namespace proofs retained."""
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
WHOLE_HELPER_SHA = '6cd5829e0fae7398ecbb712b5a1a322f15a0b6d1be73d5fc8fd4998f3405f7c5'
BASE_HEART_SHA = '117bb74ece968cac02abb81c5cc49a418a98a60a'
INITIAL_HEART_SHA = 'd2696b36d169f57f1bcb03c055384e5ec944d930'
NAMESPACE_HEART_SHA = 'efd0d2d44e871966bf3c8edcc18db73a00ec699c'
HEART_SHA = '65caee9bfc386c2f9182564d6ad1eb2f02cfadd1'
SCHEMA_DELTA_SHA = '315b63e0496cf260691c6fae367a555f143209cf3e35f45da9302836ce5ba8cb'
CONTINUATION_DELTA_SHA = 'aa971ebd0d2ae37f9344524d0f2750520aed27083c9e992e3014f347294bd391'
DELTA_SHA = 'cfddb35c2f7a28f55028f1e2985522c1de1b562a3a51d0c74dcf266b3d99c6d7'
JSON_METHOD = "TestLoadedAccountNativeSnapshotJSONView"
PEER_METHOD = "TestLoadedAccountRemoteFilePeer"
NAMESPACE_METHOD = "TestLoadedAccountCapturedTypeNamespaces"

CUSTOM_METHOD = "TestLoadedAccountCustomSchemaSource"
RETRY_METHOD = "TestLoadedAccountCaptureRetryBoundary"
METHODS = [RETRY_METHOD, CUSTOM_METHOD, PEER_METHOD]
RETRY_CASES = [
    "typed-change-starts-fresh-attempt",
    "authority-census-path-payload-errors-stop",
    "matching-error-text-does-not-retry",
    "wrapped-or-composite-marker-does-not-retry",
    "rejected-partial-value-does-not-retry",
    "attempt-cap-remains-terminal",
    "expired-original-deadline-starts-no-attempt",
    "cancellation-prevents-next-attempt",
]

NAMESPACE_CASES = [
    "actual-native-snapshot-closure",
    "native-and-legacy-urls-join-captured-key",
    "native-id-is-not-snapshot-type-key",
    "missing-type-url-remains-explicit",
    "duplicate-type-aliases-remain-explicit",
    "colliding-key-blocks-bundled-fallback",
    "type-url-object-id-alias-refused",
    "empty-and-foreign-prefixes-refused",
]
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
            delta["derived_heart_commit"] == INITIAL_HEART_SHA and
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



def apply_continuation_delta(root, snapshots, metadata):
    descriptor = HERE / "namespace-peer-continuation-v1.json"
    require(sha(descriptor) == CONTINUATION_DELTA_SHA, "continuation_delta_identity")
    delta = json.loads(descriptor.read_bytes())
    require(delta["schema"] == "native-type-namespace-peer-continuation-v1" and
            delta["base_heart_commit"] == INITIAL_HEART_SHA and
            delta["derived_heart_commit"] == NAMESPACE_HEART_SHA and
            delta["additions"] == 1 and delta["existing_changes"] == 2,
            "continuation_delta_lineage")
    expected = {
        "core/application/loaded_file_peer_test.go": "M",
        "core/application/loaded_type_namespace_test.go": "A",
        "pkg/lib/anyblockjson/storeresolver/captured.go": "M",
    }
    require([row["path"] for row in delta["files"]] == sorted(expected),
            "continuation_exact_scope")
    for row in delta["files"]:
        relative = native.relative_member(row["path"])
        require(row["operation"] == expected[relative.as_posix()] and row["mode"] == 0o644,
                "continuation_operation")
        source = HERE / "continuation-source" / relative
        native.checked_file(source, (row["bytes"], row["sha256"]))
        raw = source.read_bytes()
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() ==
                row["git_blob_sha1"], "continuation_source_git_blob")
        logical = str(native.HEART / relative)
        target = root / logical.lstrip("/")
        if row["operation"] == "A":
            require(logical not in snapshots and not target.exists() and not target.is_symlink(),
                    "continuation_addition_overwrites_source")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
        else:
            require(logical in snapshots and target.is_file() and not target.is_symlink(),
                    "continuation_existing_source_required")
            require(tuple(getattr(target.stat(), key) for key in native.FIELDS) == snapshots[logical],
                    "continuation_before_physical_identity")
            native.checked_file(target, (row["before_bytes"], row["before_sha256"]))
            before = target.read_bytes()
            require(hashlib.sha1(b"blob " + str(len(before)).encode() + b"\0" + before).hexdigest() ==
                    row["before_git_blob_sha1"], "continuation_before_git_blob")
            target.write_bytes(raw)
        target.chmod(0o644)
        native.checked_file(target, (row["bytes"], row["sha256"]))
        snapshots[logical] = tuple(getattr(target.stat(), key) for key in native.FIELDS)
    save(metadata / "native-type-namespace-peer-continuation-v1.json", delta)
    return delta


def retained_json_view():
    producer_path = HERE / "retained-json-45472745870" / "producer-result.json"
    recipient_path = HERE / "retained-json-45472745870" / "recipient-readback.json"
    native.checked_file(producer_path, (15097, "6db5baf8714b7e16fae0239849b7ff375fb838c4cf60b20573eedf01d257fc14"))
    native.checked_file(recipient_path, (1783, "ee7f5d50455e34069045d8bcf641143e42afcc76925b2535804bc5bf780bb64f"))
    original = json.loads(producer_path.read_bytes())
    recipient = json.loads(recipient_path.read_bytes())
    require(original["status"] == "FAIL" and original["error"] ==
            "native_peer_exited_before_member_joined" and
            original["controller_sha"] == "fb5b40a5e91c68520d0f2921600a9f04b1e25439" and
            original["run_id"] == "45472745870" and original["run_attempt"] == "1" and
            original["heart_sha"] == INITIAL_HEART_SHA,
            "retained_original_partial_failure_identity")
    require(len(original["executions"]) == 1, "retained_exact_original_execution")
    execution = original["executions"][0]
    require(execution["method"] == JSON_METHOD and execution["exit_code"] == 0 and
            execution["named_method_pass"] is True and execution["status"] == "PASS" and
            execution["stdout_sha256"] == "a51e4c1fb9057844dfa2e4a229636509938cacc1c8ee4e5f99e01197f2c0b9d3",
            "retained_json_method_pass")
    require(recipient["format"] == "native-file-peer-json-recipient-readback-v1" and
            recipient["runId"] == original["run_id"] and
            recipient["controllerSHA"] == original["controller_sha"] and
            recipient["nativeSourceSHA"] == INITIAL_HEART_SHA and
            recipient["producerStatus"] == "FAIL" and recipient["producerResultUnmodified"] is True and
            recipient["recipientSourceJSONStatus"] == recipient["actualNativeJSONMethod"] == "PASS" and
            recipient["regularOriginalsHashed"] == 796 and
            recipient["originalCommandStreamsVerified"] == 46 and
            recipient["allDeclaredSourceMembersVerified"] == 291 and
            recipient["nativeJSONKnownFieldRoundTrips"] == 144,
            "retained_independent_json_custody")
    return {
        "status": "RETAINED_ORIGINAL_SCOPE_PASS", "run_id": original["run_id"],
        "run_attempt": original["run_attempt"], "controller_sha": original["controller_sha"],
        "heart_sha": INITIAL_HEART_SHA, "method": JSON_METHOD,
        "rerun": False, "producer_overall_status": "FAIL",
        "producer_result_sha256": sha(producer_path),
        "recipient_readback_sha256": sha(recipient_path),
        "captured_objects": 144, "original_declared_source_members": 291,
        "stdout_sha256": execution["stdout_sha256"],
        "native_json_receipt_sha256": original["nativeJSONView"]["receipt_sha256"],
    }


def apply_schema_checkpoint_delta(root, snapshots, metadata):
    descriptor = HERE / "custom-schema-checkpoint-v1.json"
    require(sha(descriptor) == SCHEMA_DELTA_SHA, "schema_checkpoint_delta_identity")
    delta = json.loads(descriptor.read_bytes())
    require(delta["schema"] == "native-custom-schema-checkpoint-delta-v1" and
            delta["base_heart_commit"] == NAMESPACE_HEART_SHA and
            delta["derived_heart_commit"] == HEART_SHA and
            delta["additions"] == 2 and delta["existing_changes"] == 2,
            "schema_checkpoint_delta_lineage")
    expected = {
        "core/application/loaded_capture_retry_test.go": "A",
        "core/application/loaded_custom_schema_source_test.go": "A",
        "core/application/loaded_file_peer_test.go": "M",
        "core/application/loaded_space_witness.go": "M",
    }
    require([row["path"] for row in delta["files"]] == sorted(expected),
            "schema_checkpoint_exact_scope")
    for row in delta["files"]:
        relative = native.relative_member(row["path"])
        require(row["operation"] == expected[relative.as_posix()] and row["mode"] == 0o644,
                "schema_checkpoint_operation")
        source = HERE / "schema-source" / relative
        native.checked_file(source, (row["bytes"], row["sha256"]))
        raw = source.read_bytes()
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() ==
                row["git_blob_sha1"], "schema_checkpoint_source_git_blob")
        logical = str(native.HEART / relative)
        target = root / logical.lstrip("/")
        if row["operation"] == "A":
            require(logical not in snapshots and not target.exists() and not target.is_symlink(),
                    "schema_checkpoint_addition_overwrites_source")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
        else:
            require(logical in snapshots and target.is_file() and not target.is_symlink(),
                    "schema_checkpoint_existing_source_required")
            require(tuple(getattr(target.stat(), key) for key in native.FIELDS) == snapshots[logical],
                    "schema_checkpoint_before_physical_identity")
            native.checked_file(target, (row["before_bytes"], row["before_sha256"]))
            before = target.read_bytes()
            require(hashlib.sha1(b"blob " + str(len(before)).encode() + b"\0" + before).hexdigest() ==
                    row["before_git_blob_sha1"], "schema_checkpoint_before_git_blob")
            target.write_bytes(raw)
        target.chmod(0o644)
        native.checked_file(target, (row["bytes"], row["sha256"]))
        snapshots[logical] = tuple(getattr(target.stat(), key) for key in native.FIELDS)
    save(metadata / "native-custom-schema-checkpoint-delta-v1.json", delta)
    return delta


def retained_namespace():
    producer_path = HERE / "retained-namespace-45480331496" / "producer-result.json"
    recipient_path = HERE / "retained-namespace-45480331496" / "recipient-readback.json"
    native.checked_file(producer_path, (135252, "1c23d4596849ea7d66da10557d686273dd5eeb29c59aaa8f52bbf9142f280742"))
    native.checked_file(recipient_path, (2085, "0b36936e7a56bb33fe65a0e7a1db3ad6cc75987fb2fb16e48a92f117e375aa62"))
    original = json.loads(producer_path.read_bytes())
    recipient = json.loads(recipient_path.read_bytes())
    require(original["status"] == "FAIL" and original["error"] ==
            "native_peer_exited_before_owner_identity" and
            original["controller_sha"] == "5f28ece7bc62615f0954c64861f756baf6f4115e" and
            original["run_id"] == "45480331496" and original["run_attempt"] == "1" and
            original["heart_sha"] == NAMESPACE_HEART_SHA and len(original["executions"]) == 1,
            "retained_namespace_original_identity")
    execution = original["executions"][0]
    namespace = original["capturedTypeNamespace"]
    require(execution["method"] == NAMESPACE_METHOD and execution["exit_code"] == 0 and
            execution["status"] == "PASS" and execution["named_method_pass"] is True and
            execution["subtests"] == 8 and namespace["status"] == "PASS" and
            namespace["closed_resolver_unmapped"] == 0 and namespace["raw_snapshots_unchanged"] is True and
            namespace["native_type_urls"] == 142 and namespace["native_type_definitions"] == 19 and
            execution["stdout_sha256"] == "145c0063a455e95276731ab10f273ed1fee9eea5e349187a4a4ec11d62f3b037",
            "retained_actual_namespace_method_pass")
    require(recipient["format"] == "pinkha-native-file-peer-recipient-readback-v1" and
            recipient["status"] == "PASS" and recipient["runId"] == original["run_id"] and
            recipient["controllerSHA"] == original["controller_sha"] and
            recipient["nativeSourceSHA"] == NAMESPACE_HEART_SHA and
            recipient["producerStatus"] == "FAIL" and
            recipient["publicResultSHA256"] == sha(producer_path) and
            recipient["privateRegularOriginals"] == 486 and
            recipient["originalCommandStreams"] == 46 and
            recipient["nativeNamespace"]["manifestDeclaredMembers"] == 287 and
            recipient["nativeNamespace"]["snapshotObjects"] == 143 and
            recipient["nativeNamespace"]["nativeTrees"] == 144 and
            recipient["nativeNamespace"]["closedResolverUnmapped"] == 0,
            "retained_independent_namespace_custody")
    return {
        "status": "RETAINED_ORIGINAL_SCOPE_PASS", "run_id": original["run_id"],
        "run_attempt": original["run_attempt"], "controller_sha": original["controller_sha"],
        "heart_sha": NAMESPACE_HEART_SHA, "method": NAMESPACE_METHOD, "subtests": 8,
        "rerun": False, "producer_overall_status": "FAIL", "closed_resolver_unmapped": 0,
        "producer_result_sha256": sha(producer_path),
        "recipient_readback_sha256": sha(recipient_path),
        "captured_objects": 143, "original_declared_source_members": 287,
        "stdout_sha256": execution["stdout_sha256"],
        "native_namespace_receipt_sha256": namespace["receipt_sha256"],
    }


def audit_capture_attempts(directory, prefix, stage):
    paths = sorted(directory.glob(prefix + "*.json"))
    require(1 <= len(paths) <= 3, "bounded_original_capture_attempt_count")
    observations = []
    for number, path in enumerate(paths, 1):
        require(path.name == prefix + str(number) + ".json" and path.is_file() and
                not path.is_symlink(), "immutable_capture_attempt_member")
        row = json.loads(path.read_bytes())
        note = row["attempt"]
        require(row["contract"] == "pinkha-native-source-capture-attempt-v1" and
                row["attemptLimit"] == 3 and row["stage"] == stage and
                row["newCaptureRequiredAfterRefusal"] is True and note["Attempt"] == number,
                "original_capture_attempt_contract")
        if number < len(paths):
            require(note["Outcome"] == "checkpoint-changed" and
                    "native source checkpoint changed during capture" in note["Error"],
                    "only_typed_checkpoint_change_precedes_success")
        else:
            require(note["Outcome"] == "capture-returned" and note["Error"] == "",
                    "last_attempt_returns_fresh_capture")
        observations.append({"attempt": number, "outcome": note["Outcome"], "sha256": sha(path)})
    return observations


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
            "schema": "native-file-peer-portable-v3", "status": "RUNNING",
            "controller_sha": os.environ.get("GITHUB_SHA"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "heart_sha": HEART_SHA, "base_heart_sha": native.HEART_SHA,
            "context_heart_sha": native.DERIVED_HEART_SHA, "whole_source_heart_sha": BASE_HEART_SHA,
            "initial_file_peer_heart_sha": INITIAL_HEART_SHA,
            "retained_namespace_heart_sha": NAMESPACE_HEART_SHA,
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
        self.result["retainedNativeJSONView"] = retained_json_view()
        self.result["retainedCapturedTypeNamespace"] = retained_namespace()
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
        self.result["source"]["namespace_peer_continuation"] = apply_continuation_delta(
            self.rootfs, self.snapshots, self.private / "source-metadata")

        self.result["source"]["custom_schema_checkpoint_continuation"] = apply_schema_checkpoint_delta(
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
                "actual_three_selected_named_methods")
        self.result["actual_named_methods_sha256"] = sha(out)


    def retry_boundaries(self):
        rc, stdout, _ = self.container("native-capture-retry-boundaries", self.binary,
            ["-test.v", "-test.run=^" + RETRY_METHOD + "$", "-test.count=1", "-test.timeout=15s"],
            seconds=30)
        row = {"method": RETRY_METHOD, "role": "fixture scheduling controls only", "exit_code": rc,
               "native_source_capture_proof": False}
        self.result["executions"].append(row)
        require(rc == 0, "capture_retry_scheduling_method_exit")
        text = stdout.read_text()
        expected = [RETRY_METHOD] + [RETRY_METHOD + "/" + name for name in RETRY_CASES]
        runs = re.findall(r"(?m)^=== RUN\s+(\S+)\s*$", text)
        passes = re.findall(r"(?m)^\s*--- PASS:\s+(\S+)\s+\(", text)
        require(runs == expected and sorted(passes) == sorted(expected) and
                len(passes) == len(expected) and re.search(r"(?m)^PASS\s*$", text) and
                not re.search(r"(?m)^\s*--- (?:FAIL|SKIP):", text),
                "exact_eight_capture_scheduling_cases")
        row.update(status="PASS", named_method_pass=True, subtests=8, stdout_sha256=sha(stdout))
        self.result["captureScheduling"] = {
            "status": "PASS", "method": RETRY_METHOD, "subtests": 8, "attempt_limit": 3,
            "original_deadline_preserved": True, "native_source_capture_proof": False,
            "stdout_sha256": sha(stdout),
        }

    def custom_schema(self):
        rc, stdout, _ = self.container("native-custom-schema", self.binary,
            ["-test.v", "-test.run=^" + CUSTOM_METHOD + "$", "-test.count=1", "-test.timeout=210s"],
            seconds=240)
        row = {"method": CUSTOM_METHOD, "role": "new actual native definitions and current values", "exit_code": rc}
        self.result["executions"].append(row)
        require(rc == 0, "native_custom_schema_method_exit")
        row.update(audit_one(stdout, CUSTOM_METHOD))
        root = self.private / "fixtures" / CUSTOM_METHOD
        note_path = root / "native-custom-schema-source.json"
        note = json.loads(note_path.read_bytes())
        count = note["capturedObjects"]
        receipt = note["sourceReceipt"]
        require(note["contract"] == "pinkha-native-custom-schema-source-v1" and
                note["customIdentityCount"] == 14 and len(note["properties"]) == 7 and
                len(note["options"]) == 4 and count >= 14 and
                receipt["CapturedObjects"] == count and receipt["ClosedResolverUnmapped"] == 0 and
                note["originalPBAndJSONMembersVerified"] == count and
                all(note[key] is True for key in (
                    "nativeDefinitionsAndCurrentValuesVerified", "emptyAndDefaultValuesVerified",
                    "orderedNativeIdentitiesVerified")) and
                note["wholeSpaceSemanticMigrationComplete"] is False and
                all(receipt[key] is True for key in (
                    "AllNativeHeadRowsAccounted", "AllCurrentObjectsCaptured",
                    "CapturedSnapshotsBoundToUnchangedCheckpoint", "AccountSessionAuthorizedAtFinalCapture",
                    "IndexResolverSnapshotBound")) and
                all(receipt[key] is False for key in (
                    "HasNativeSourceAdmission", "SemanticCompleteness", "HistorySemanticsValidated",
                    "PermitsDestinationWrites")),
                "actual_custom_schema_and_current_values")
        identities = [note["typeObjectID"], note["firstDocumentID"], note["secondDocumentID"]]
        identities += [item["objectID"] for item in note["properties"] + note["options"]]
        require(len(set(identities)) == 14 and all(identities), "fourteen_distinct_actual_native_identities")
        require(hashlib.sha256(note["sourceAccountID"].encode()).hexdigest() ==
                receipt["Source"]["accountSHA256"] and
                hashlib.sha256(note["sourceSpaceID"].encode()).hexdigest() ==
                receipt["Inventory"]["SpaceSHA256"], "custom_schema_actual_account_space_binding")
        manifests = list(root.glob("native-source-*/manifest.json"))
        require(len(manifests) == 1, "one_successful_custom_source_bundle")
        manifest_path = manifests[0]
        require(sha(manifest_path) == note["originalSourceManifestSHA256"],
                "custom_source_manifest_identity")
        manifest = json.loads(manifest_path.read_bytes())
        require(manifest["Contract"] == "pinkha-native-whole-source-bundle-v1" and
                manifest["Receipt"] == receipt and len(manifest["Objects"]) == count and
                manifest["SourceRows"]["SHA256"] == note["originalSourceRowsSHA256"] and
                set(identities).issubset({item["ObjectID"] for item in manifest["Objects"]}) and
                not manifest["Files"] and not manifest["FileReferences"],
                "custom_source_complete_bundle_membership")
        members = [manifest["SourceRows"]]
        for item in manifest["Objects"]:
            members.extend([item["Snapshot"], item["NativeJSONView"]])
        require(len({item["Path"] for item in members}) == len(members),
                "custom_source_unique_member_paths")
        for member in members:
            relative = native.relative_member(member["Path"])
            native.checked_file(manifest_path.parent / relative, (member["Bytes"], member["SHA256"]))
        attempts = audit_capture_attempts(root, "native-custom-schema-capture-attempt-", "custom-schema")
        row["status"] = "PASS"
        self.result["nativeCustomSchema"] = {
            "status": "PASS", "method": CUSTOM_METHOD, "captured_objects": count,
            "custom_types": 1, "properties": 7, "options": 4, "typed_documents": 2,
            "distinct_custom_identities": 14, "closed_resolver_unmapped": 0,
            "empty_default_current_values_verified": True, "ordered_identities_verified": True,
            "original_declared_source_members": len(members), "receipt_sha256": sha(note_path),
            "manifest_sha256": sha(manifest_path), "source_rows_sha256": manifest["SourceRows"]["SHA256"],
            "capture_attempts": attempts, "source_semantic_migration_complete": False,
        }

    def audit_peer_capture_attempts(self):
        scopes = [
            ("owner", "owner-initial"), ("member", "member-cold"),
            ("member", "member-prefetched"), ("member", "member-offline-reopen"),
        ]
        self.result["peerCaptureAttempts"] = {
            stage: audit_capture_attempts(self.private / "peers" / role, "capture-" + stage + "-attempt-", stage)
            for role, stage in scopes
        }


    def namespace(self):
        rc, stdout, _ = self.container("native-type-namespace", self.binary,
            ["-test.v", "-test.run=^" + NAMESPACE_METHOD + "$", "-test.count=1", "-test.timeout=210s"],
            seconds=240)
        row = {"method": NAMESPACE_METHOD, "role": "new captured type namespace control", "exit_code": rc}
        self.result["executions"].append(row)
        require(rc == 0, "native_type_namespace_method_exit")
        text = stdout.read_text()
        expected = [NAMESPACE_METHOD] + [NAMESPACE_METHOD + "/" + name for name in NAMESPACE_CASES]
        runs = re.findall(r"(?m)^=== RUN\s+(\S+)\s*$", text)
        passes = re.findall(r"(?m)^\s*--- PASS:\s+(\S+)\s+\(", text)
        require(runs == expected and sorted(passes) == sorted(expected) and
                len(passes) == len(expected) and re.search(r"(?m)^PASS\s*$", text) and
                not re.search(r"(?m)^\s*--- (?:FAIL|SKIP):", text),
                "exact_new_namespace_method_and_eight_cases")
        note_path = self.private / "fixtures" / NAMESPACE_METHOD / "captured-type-namespaces.json"
        note = json.loads(note_path.read_bytes())
        receipt = note["receipt"]
        require(note["boundarySubtests"] == 8 and note["actualNativeTypeURLs"] > 0 and
                note["actualNativeTypeRows"] > 0 and all(note[key] is True for key in (
                    "rawSnapshotsUnchanged", "nativeIDRefusedInTypeKeySlot", "missingTypeRetained",
                    "duplicateAliasesRetained", "capturedCollisionBlocksBundledFallback")) and
                receipt["ClosedResolverUnmapped"] == 0 and all(receipt[key] is True for key in (
                    "AllNativeHeadRowsAccounted", "AllCurrentObjectsCaptured",
                    "CapturedSnapshotsBoundToUnchangedCheckpoint", "AccountSessionAuthorizedAtFinalCapture",
                    "IndexResolverSnapshotBound")) and all(receipt[key] is False for key in (
                    "HasNativeSourceAdmission", "SemanticCompleteness", "HistorySemanticsValidated",
                    "PermitsDestinationWrites")), "actual_native_captured_namespace_closure")
        row.update(status="PASS", named_method_pass=True, subtests=8, stdout_sha256=sha(stdout))
        self.result["capturedTypeNamespace"] = {
            "status": "PASS", "method": NAMESPACE_METHOD, "subtests": 8,
            "native_type_urls": note["actualNativeTypeURLs"],
            "native_type_definitions": note["actualNativeTypeRows"],
            "closed_resolver_unmapped": 0, "raw_snapshots_unchanged": True,
            "receipt_sha256": sha(note_path), "source_receipt": receipt,
        }

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
        rc, stopped, _ = self.command("wait-" + owned["role"] + "-" + owned["phase"],
            ["sudo", "-n", "docker", "wait", owned["name"]], 60)
        require(rc == 0 and stopped.read_text().strip() == "0", "native_peer_actual_stopped_exit")
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
        self.retry_boundaries()
        failures = []
        # These owned fixtures use independent accounts/stores. Retain an actual
        # source-schema failure while still exercising the separately failed
        # peer scope from the same one compiled immutable binary.
        for label, operation in (("custom-schema", self.custom_schema), ("remote-file-peers", self.peers)):
            first = len(self.result["executions"])
            try:
                operation()
            except Exception as exc:
                failures.append({"scope": label, "error_type": type(exc).__name__, "error": str(exc)})
                for row in self.result["executions"][first:]:
                    if row.get("status") != "PASS":
                        row["status"] = "FAIL"
        for name, before in self.snapshots.items():
            path = self.rootfs / name.lstrip("/")
            require(tuple(getattr(path.stat(), key) for key in native.FIELDS) == before,
                    "readonly_compiled_source_changed")
        self.result["compiled_source_unchanged"] = True
        if failures:
            self.result["scopeFailures"] = failures
            raise RuntimeError(failures[0]["error"] if len(failures) == 1 else "owned_native_scopes_failed")
        self.audit_peer_capture_attempts()
        require(len(self.result["executions"]) == 5 and
                all(row["status"] == "PASS" for row in self.result["executions"]),
                "exact_custom_schema_scheduling_and_three_peer_executions")
        self.result["status"] = "NATIVE_CUSTOM_SCHEMA_AND_REMOTE_FILE_PEERS_PASS"

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
    return 0 if runner.result["status"] == "NATIVE_CUSTOM_SCHEMA_AND_REMOTE_FILE_PEERS_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
