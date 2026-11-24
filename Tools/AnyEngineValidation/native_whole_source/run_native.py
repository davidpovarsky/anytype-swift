#!/usr/bin/env python3
"""Run only new closed whole-source controls using unchanged qualified C4 carriers."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
PORTABLE = HERE.parent / "loaded_account_witness" / "portable"
HELPER_SHA = "cf3b927951ddfdfcfe9e51d724cce1753b03d92c147224dba23c5cda8b868fdc"
DELTA_SHA = '52321d2880aac17f5cba613c023aaa2c87b49edd78cfab0bb554ba1e97d30d5e'
HEART_SHA = '4b62d683e4a3bc2d19bf942f9b20ccbd675b3488'
METHODS = ['TestLoadedAccountWholeSourceBindsLocalPayloadAndMetadata', 'TestLoadedAccountWholeSourceRefusesChangedCheckpointAndAuthority', 'TestLoadedAccountCapturedResolverAccountsForMissingSchemas']
SUBTESTS = {'TestLoadedAccountWholeSourceBindsLocalPayloadAndMetadata': ['missing-local-leaf-refused'], 'TestLoadedAccountWholeSourceRefusesChangedCheckpointAndAuthority': ['invalid-session', 'object-bound', 'unsafe-output-directory'], 'TestLoadedAccountCapturedResolverAccountsForMissingSchemas': ['detached-row-and-no-live-fallback', 'missing-target-type-is-explicit', 'colliding-keys-refuse-ambiguous-format', 'mismatched-native-row-refused']}
helper_path = PORTABLE / "run_native.py"
if hashlib.sha256(helper_path.read_bytes()).hexdigest() != HELPER_SHA:
    raise RuntimeError("qualified_native_helper_changed")
spec = importlib.util.spec_from_file_location("qualified_c4_native_helpers", helper_path)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
require, sha, save = native.require, native.sha, native.save


def apply_whole_source_delta(root, snapshots, metadata):
    require(sha(HERE / "source-delta-v1.json") == DELTA_SHA, "whole_source_delta_identity")
    delta = json.loads((HERE / "source-delta-v1.json").read_bytes())
    require(delta["schema"] == "native-whole-source-delta-v1" and
            delta["base_heart_commit"] == native.DERIVED_HEART_SHA and
            delta["derived_heart_commit"] == HEART_SHA and
            delta["existing_changes"] == 1 and delta["additions"] == 15,
            "whole_source_delta_lineage")
    expected = ['core/application/loaded_object_witness.go', 'core/application/loaded_object_witness_test.go', 'core/application/loaded_space_bundle.go', 'core/application/loaded_space_witness.go', 'core/application/loaded_space_witness_test.go', 'core/block/export/native_file_references.go', 'core/block/export/native_object_witness.go', 'core/block/export/native_raw_object.go', 'core/files/filestorage/native_snapshot.go', 'core/files/native_capture.go', 'core/pinkha/localstorewitness/native_inventory_collections.go', 'core/pinkha/localstorewitness/native_tree_inventory.go', 'core/pinkha/localstorewitness/native_tree_inventory_test.go', 'pkg/lib/anyblockjson/storeresolver/captured.go', 'pkg/lib/anyblockjson/storeresolver/read_index.go', 'pkg/lib/anyblockjson/storeresolver/storeresolver.go']
    require([v["path"] for v in delta["files"]] == expected, "whole_source_exact_file_scope")
    for row in delta["files"]:
        relative = native.relative_member(row["path"])
        source = HERE / "source" / relative
        native.checked_file(source, (row["bytes"], row["sha256"]))
        raw = source.read_bytes()
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() ==
                row["git_blob_sha1"] and row["mode"] == 0o644, "whole_source_git_blob_identity")
        logical = str(native.HEART / relative)
        target = root / logical.lstrip("/")
        if row["operation"] == "A":
            require(not target.exists() and not target.is_symlink() and logical not in snapshots,
                    "whole_source_addition_overwrites_source")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as out:
                out.write(raw)
        else:
            require(row["operation"] == "M" and row["path"] ==
                    "pkg/lib/anyblockjson/storeresolver/storeresolver.go" and
                    logical in snapshots and target.is_file() and not target.is_symlink(),
                    "whole_source_only_approved_existing_field")
            require(tuple(getattr(target.stat(), key) for key in native.FIELDS) == snapshots[logical],
                    "whole_source_original_field_changed")
            native.checked_file(target, (row["before_bytes"], row["before_sha256"]))
            before = target.read_bytes()
            require(hashlib.sha1(b"blob " + str(len(before)).encode() + b"\0" + before).hexdigest() ==
                    row["before_git_blob_sha1"] and
                    row["replace_before"] == "index      spaceindex.Store" and
                    row["replace_after"] == "index      readIndex",
                    "whole_source_old_constructor_blob")
            require(before.count(row["replace_before"].encode()) == 1 and
                    before.replace(row["replace_before"].encode(), row["replace_after"].encode()) == raw,
                    "whole_source_approved_field_only")
            target.write_bytes(raw)
        target.chmod(row["mode"])
        native.checked_file(target, (row["bytes"], row["sha256"]))
        snapshots[logical] = tuple(getattr(target.stat(), k) for k in native.FIELDS)
    save(metadata / "native-whole-source-delta-v1.json", delta)
    return delta


def actual_generated_main(work_root, stderr):
    matches = re.findall(rb"(?m)^WORK=([^\r\n]+)$", stderr.read_bytes())
    require(len(matches) == 1, "single_actual_go_work_required")
    work = Path(matches[0].decode("utf-8", "strict"))
    require(work.parent == work_root and re.fullmatch(r"go-build\d+", work.name) and
            work.is_dir() and not work.is_symlink(), "actual_go_work_scope")
    candidates = list(work.glob("*/_testmain.go"))
    require(len(candidates) == 1 and candidates[0].is_file() and
            not candidates[0].is_symlink(), "actual_generated_main_unique")
    main = candidates[0]
    names = re.findall(r'"(TestLoadedAccount(?:WholeSource|CapturedResolver)[^"]+)"' , main.read_text())
    require(sorted(names) == sorted(METHODS), "actual_whole_source_test_registration")
    return main


def audit_method(stdout, method, fixtures):
    text = stdout.read_text()
    expected = {method} | {method + "/" + child for child in SUBTESTS[method]}
    runs = re.findall(r"(?m)^=== RUN\s+(\S+)\s*$", text)
    passed = re.findall(r"(?m)^\s*--- PASS:\s+(\S+)\s+\(", text)
    require(set(runs) == expected and len(runs) == len(expected) and
            set(passed) == expected and len(passed) == len(expected) and
            re.search(r"(?m)^PASS\s*$", text) and
            not re.search(r"(?m)^\s*--- (?:SKIP|FAIL):", text),
            "exact_whole_source_method_and_subtests")
    result = {"named_method_pass": True, "subtests_pass": len(expected)-1,
              "stdout_sha256": sha(stdout)}
    if method == METHODS[0]:
        note_path = fixtures / method / "whole-source-local-payload.json"
        note = json.loads(note_path.read_bytes())
        receipt = note["receipt"]
        payload = b"native-source-plain-0123456789\x00\xff" * 600
        require(note["payloadSHA256"] == hashlib.sha256(payload).hexdigest() and
                note["payloadBytes"] == len(payload) and
                receipt["Version"] == "loaded-account-native-space-source-v1" and
                all(receipt[k] is True for k in (
                    "AccountSessionAuthorizedAtFinalCapture", "AllNativeHeadRowsAccounted",
                    "CapturedSnapshotsBoundToUnchangedCheckpoint", "IndexResolverSnapshotBound",
                    "OriginalNativeHistoryRowsRetained")) and
                all(receipt[k] is False for k in ("HistorySemanticsValidated",
                    "SemanticCompleteness", "HasNativeSourceAdmission", "PermitsDestinationWrites")) and
                receipt["CapturedFiles"] == 1 and receipt["PlaintextBytes"] == len(payload) and
                receipt["MetadataBytes"] > 0,
                "whole_source_actual_payload_receipt")
        candidates = [q for q in (fixtures / method).glob("native-source-*/manifest.json")
                      if sha(q) == note["manifestSHA256"]]
        require(len(candidates)==1 and candidates[0].stat().st_size==note["manifestBytes"],
                "whole_source_private_original_manifest")
        manifest_path = candidates[0]
        manifest = json.loads(manifest_path.read_bytes())
        require(manifest["Contract"]=="pinkha-native-whole-source-bundle-v1" and
                manifest["Receipt"]==receipt and len(manifest["Files"])==1,
                "whole_source_bundle_contract")
        members=[manifest["SourceRows"]]+[o["Snapshot"] for o in manifest["Objects"]]
        for file in manifest["Files"]:
            for variant in file["Variants"]:
                members.extend((variant["Payload"],variant["Metadata"]))
        require(len(members)==note["membersVerified"],"whole_source_original_member_count")
        for member in members:
            path=manifest_path.parent/native.relative_member(member["Path"])
            native.checked_file(path,(member["Bytes"],member["SHA256"]))
        missing_path=fixtures/method/"whole-source-missing-leaf.json"
        missing=json.loads(missing_path.read_bytes())
        require(missing["explicitFileGap"] is True and
                missing["receipt"]["CapturedFiles"]==0 and
                missing["receipt"]["CurrentFilePayloadCompleteness"] is False,
                "whole_source_real_missing_leaf_refusal")
        result.update(native_receipt=receipt,private_manifest_sha256=sha(manifest_path),
                      private_members_verified=len(members),payload_sha256=note["payloadSHA256"],
                      missing_leaf_refused=True,receipt_sha256=sha(note_path))
    elif method == METHODS[1]:
        note_path=fixtures/method/"whole-source-checkpoint-refusal.json"
        note=json.loads(note_path.read_bytes())
        require(set(note)=={"actualNativeEdit","refusedChangedCheckpoint","invalidSessionRefused",
                           "objectBoundRefused","symlinkOutputRefused"} and
                all(value is True for value in note.values()),"whole_source_native_mutation_refused")
        result.update(refusals=note,receipt_sha256=sha(note_path))
    else:
        require(text.count("WHOLE_SOURCE_CAPTURED_RESOLVER_OBSERVATION")==1,
                "whole_source_closed_resolver_receipt")
    return result


class WholeSourceRunner(native.Runner):
    def __init__(self):
        os.umask(0o077)
        self.base = Path(os.environ["RUNNER_TEMP"]) / "pinkha-native-whole-source"
        self.base.mkdir(mode=0o700)
        self.public, self.private = self.base / "public", self.base / "private"
        self.inputs, self.rootfs = self.base / "inputs", self.base / "rootfs"
        for path in (self.public, self.private, self.inputs, self.rootfs):
            path.mkdir(mode=0o700)
        for name in ("commands", "fixtures", "work", "products", "go-build",
                     "source-metadata", "image-data-empty"):
            (self.private / name).mkdir(mode=0o700)
        self.commands, self.names = [], []
        self.result = {
            "schema": "native-whole-source-portable-v1", "status": "RUNNING",
            "controller_sha": os.environ.get("GITHUB_SHA"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "heart_sha": HEART_SHA, "base_heart_sha": native.HEART_SHA,
            "context_heart_sha": native.DERIVED_HEART_SHA, "any_sync_sha": native.SYNC_SHA,
            "qualified_helper_sha256": HELPER_SHA, "selected_methods": METHODS,
            "methods": [], "builds": 0, "semanticCompleteness": False,
            "filePayloadCompleteness": False, "hasNativeSourceAdmission": False,
            "permitsDestinationWrites": False, "accountSessionAuthorized": False,
            "historySemanticsValidated": False,
        }

    def execute(self):
        require(os.getuid() == 1001 and platform.machine() == "aarch64",
                "qualified_runner_identity")
        require(os.environ.get("GITHUB_ACTIONS") == "true", "genuine_github_actions_required")
        self.result["resources_before"] = self.guard(start=True)
        self.result["profile"] = {
            "fresh_disk_cache": True, "copied_warm_cache": False, "build_seconds": 1800,
            "test_seconds": 240, "container_memory_bytes": 4 * native.GIB,
            "container_cpus": 1, "package": "./core/application",
        }
        controller = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        require(controller == os.environ["GITHUB_SHA"] == os.environ["EXPECTED_SOURCE_SHA"],
                "controller_commit")
        compiler = self.download("PINKHA_NATIVE_COMPILER_URL", "compiler.zip", native.COMPILER)
        source = self.download("PINKHA_NATIVE_SOURCE_URL", "source.tar.gz", native.SOURCE)
        self.result["input_sha256"] = {"compiler": native.COMPILER[1], "source": native.SOURCE[1]}
        with zipfile.ZipFile(compiler) as archive:
            members = archive.infolist()
            require(len(members) == 215 and all(not v.is_dir() for v in members),
                    "compiler_member_census")
            for member in members:
                native.relative_member(member.filename)
            candidates = [v for v in members if Path(v.filename).name == "compiler-image.tar"]
            require(len(candidates) == 1 and candidates[0].file_size == native.IMAGE_TAR[0],
                    "compiler_image_member")
            image = self.inputs / "compiler-image.tar"
            with archive.open(candidates[0]) as src, image.open("xb") as dst:
                shutil.copyfileobj(src, dst, native.MIB)
        native.checked_file(image, native.IMAGE_TAR)
        self.snapshots, self.result["source"] = native.extract_source(
            source, self.rootfs, self.private / "source-metadata")
        self.result["source"]["context_derivation"] = native.apply_source_delta(
            self.rootfs, self.snapshots, PORTABLE, self.private / "source-metadata")
        self.result["source"]["whole_source_derivation"] = apply_whole_source_delta(
            self.rootfs, self.snapshots, self.private / "source-metadata")
        self.command("load-image", ["sudo", "-n", "docker", "load", "--input", str(image)], 180)
        _, out, _ = self.command("image-inspect",
                                 ["sudo", "-n", "docker", "image", "inspect", native.IMAGE], 30)
        imageinfo = json.loads(out.read_bytes())[0]
        require(imageinfo["Id"] == native.IMAGE and imageinfo["Architecture"] == "arm64" and
                imageinfo["Os"] == "linux", "qualified_image_identity")
        self.result["compiler_image"] = native.IMAGE
        binary = self.private / "products/native-whole-source.test"
        self.result["builds"] += 1
        rc, _, stderr = self.container("build", native.GOROOT / "bin/go",
            ["test", "-c", "-work", "-x", "-p=1", "-mod=readonly",
             "-modfile=" + str(native.ORIGINAL / "candidate.mod"),
             "-tags", native.TAGS + " pinkha_localstore_witness",
             "-o", str(binary), "./core/application"],
            build=True, seconds=1800)
        require(rc == 0, "native_whole_source_compile_failed")
        require(binary.is_file() and 0 < binary.stat().st_size <= 256 * native.MIB,
                "native_binary_shape")
        with binary.open("rb") as file:
            header = file.read(20)
        require(header[:6] == b"\x7fELF\x02\x01" and
                int.from_bytes(header[18:20], "little") == 183, "native_binary_arm64_elf")
        main = actual_generated_main(self.private / "work", stderr)
        shutil.copyfile(main, self.private / "generated-test-main.go")
        self.result["generated_main"] = {
            "path": str(main), "sha256": sha(main), "bytes": main.stat().st_size,
            "origin": "actual -work build directory", "new_registration": METHODS,
        }
        self.result["binary"] = {"bytes": binary.stat().st_size, "sha256": sha(binary)}
        rc, out, _ = self.container("binary-buildinfo", native.GOROOT / "bin/go",
                                    ["version", "-m", str(binary)], seconds=30)
        require(rc == 0 and out.read_text().splitlines()[0] ==
                str(binary) + ": go1.26.5", "actual_binary_toolchain")
        rc, out, _ = self.container("binary-method-list", binary,
                                    ["-test.list=^(" + "|".join(METHODS) + ")$"], seconds=30)
        require(rc == 0 and out.read_text().splitlines() == METHODS,
                "actual_binary_whole_source_methods")
        self.result["actual_named_methods_sha256"] = sha(out)
        for index, method in enumerate(METHODS, 1):
            row = {"method": method, "status": "FAIL"}
            self.result["methods"].append(row)
            rc, stdout, _ = self.container("whole-source-method-" + str(index), Path("/usr/bin/env"),
                ["PINKHA_NATIVE_OWNED_SNAPSHOT_PRIVATE_ROOT=" + str(self.private / "fixtures"),
                 str(binary), "-test.v", "-test.run=^" + method + "$",
                 "-test.count=1", "-test.timeout=210s"])
            row["exit_code"] = rc
            try:
                require(rc == 0, "native_whole_source_method_exit")
                row["audit"] = audit_method(stdout, method, self.private / "fixtures")
                row["status"] = "PASS"
            except Exception as exc:
                row["error"] = str(exc)
        for name, before in self.snapshots.items():
            path = self.rootfs / name.lstrip("/")
            require(tuple(getattr(path.stat(), key) for key in native.FIELDS) == before,
                    "readonly_source_changed")
        self.result["compiled_source_unchanged"] = True
        require(len(self.result["methods"]) == 3 and
                all(v["status"] == "PASS" for v in self.result["methods"]),
                "native_whole_source_three_method_acceptance")
        self.result["status"] = "THREE_NATIVE_WHOLE_SOURCE_METHODS_PASS"


def main():
    runner = WholeSourceRunner()
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
    return 0 if runner.result["status"] == "THREE_NATIVE_WHOLE_SOURCE_METHODS_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
