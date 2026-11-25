#!/usr/bin/env python3
"""Run only the new native inventory tests using the unchanged qualified C4 inputs."""
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
DELTA_SHA = "0d791ace3ccbc1e566fe51b94ca3cf89e6ce9d77a8443cb2bfd68f63b63d8d2b"
HEART_SHA = "d8e609b9faf2ea7307178676ebecfcd6da524159"
METHODS = [
    "TestNativeTreeInventoryBindsDetachedNativeHeads",
    "TestNativeTreeInventoryRefusesMalformedNativeHeads",
    "TestNativeTreeInventoryRefusesUnownedOrCorruptCapture",
]
SUBTESTS = {
    METHODS[0]: ["space", "object", "root", "raw-root", "head", "duplicate-head"],
    METHODS[1]: ["unknown-head", "duplicate-head", "unknown-deletion", "deleted-tree-retained"],
    METHODS[2]: [],
}
helper_path = PORTABLE / "run_native.py"
if hashlib.sha256(helper_path.read_bytes()).hexdigest() != HELPER_SHA:
    raise RuntimeError("qualified_native_helper_changed")
spec = importlib.util.spec_from_file_location("qualified_c4_native_helpers", helper_path)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
require, sha, save = native.require, native.sha, native.save


def apply_inventory_delta(root, snapshots, metadata):
    require(sha(HERE / "source-delta-v1.json") == DELTA_SHA, "inventory_delta_identity")
    delta = json.loads((HERE / "source-delta-v1.json").read_bytes())
    require(delta["schema"] == "native-tree-inventory-source-delta-v1" and
            delta["base_heart_commit"] == native.DERIVED_HEART_SHA and
            delta["derived_heart_commit"] == HEART_SHA and delta["only_additions"] is True,
            "inventory_delta_lineage")
    expected = ["core/pinkha/localstorewitness/native_tree_inventory.go",
                "core/pinkha/localstorewitness/native_tree_inventory_test.go"]
    require([v["path"] for v in delta["files"]] == expected, "inventory_exact_two_additions")
    for row in delta["files"]:
        relative = native.relative_member(row["path"])
        source = HERE / "source" / relative
        native.checked_file(source, (row["bytes"], row["sha256"]))
        raw = source.read_bytes()
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() ==
                row["git_blob_sha1"] and row["mode"] == 0o644, "inventory_git_blob_identity")
        logical = str(native.HEART / relative)
        target = root / logical.lstrip("/")
        require(not target.exists() and not target.is_symlink() and logical not in snapshots,
                "inventory_addition_overwrites_source")
        with target.open("xb") as out:
            out.write(raw)
        target.chmod(row["mode"])
        native.checked_file(target, (row["bytes"], row["sha256"]))
        snapshots[logical] = tuple(getattr(target.stat(), k) for k in native.FIELDS)
    save(metadata / "native-inventory-source-delta-v1.json", delta)
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
    names = re.findall(r'"(TestNativeTreeInventory[^"]+)"', main.read_text())
    require(sorted(names) == sorted(METHODS), "actual_inventory_test_registration")
    return main


def audit_method(stdout, method):
    text = stdout.read_text()
    expected = {method} | {method + "/" + child for child in SUBTESTS[method]}
    runs = re.findall(r"(?m)^=== RUN\s+(\S+)\s*$", text)
    passed = re.findall(r"(?m)^\s*--- PASS:\s+(\S+)\s+\(", text)
    require(set(runs) == expected and len(runs) == len(expected) and
            set(passed) == expected and len(passed) == len(expected) and
            re.search(r"(?m)^PASS\s*$", text) and
            not re.search(r"(?m)^\s*--- (?:SKIP|FAIL):", text),
            "exact_inventory_method_and_subtests")
    result = {"named_method_pass": True, "subtests_pass": len(expected) - 1,
              "stdout_sha256": sha(stdout)}
    receipts = re.findall(r"NATIVE_TREE_INVENTORY (\{[^\r\n]+\})", text)
    require(len(receipts) == (1 if method == METHODS[0] else 0), "inventory_receipt_count")
    if receipts:
        receipt = json.loads(receipts[0])
        require(receipt["Version"] == "native-tree-identity-inventory-v1" and
                receipt["AllHeadRowsAccounted"] is True and receipt["Trees"] >= 2 and
                receipt["OtherCollections"] >= 2 and receipt["OtherCollectionRows"] >= 1 and
                all(receipt[key] is False for key in (
                    "AccountSessionAuthorized", "HistorySemanticsValidated",
                    "SemanticCompleteness", "FilePayloadCompleteness",
                    "HasNativeSourceAdmission", "PermitsDestinationWrites")),
                "bounded_native_inventory_receipt")
        require(all(re.fullmatch(r"[0-9a-f]{64}", receipt[key]) for key in (
            "SourceWitnessSHA256", "InventorySHA256", "SpaceSHA256", "ACLHeadSHA256")),
            "inventory_safe_receipt_digests")
        result["native_receipt"] = receipt
    return result


class InventoryRunner(native.Runner):
    def __init__(self):
        os.umask(0o077)
        self.base = Path(os.environ["RUNNER_TEMP"]) / "pinkha-native-tree-inventory"
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
            "schema": "native-tree-inventory-portable-v1", "status": "RUNNING",
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
            "container_cpus": 1, "package": "./core/pinkha/localstorewitness",
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
        self.result["source"]["inventory_derivation"] = apply_inventory_delta(
            self.rootfs, self.snapshots, self.private / "source-metadata")
        self.command("load-image", ["sudo", "-n", "docker", "load", "--input", str(image)], 180)
        _, out, _ = self.command("image-inspect",
                                 ["sudo", "-n", "docker", "image", "inspect", native.IMAGE], 30)
        imageinfo = json.loads(out.read_bytes())[0]
        require(imageinfo["Id"] == native.IMAGE and imageinfo["Architecture"] == "arm64" and
                imageinfo["Os"] == "linux", "qualified_image_identity")
        self.result["compiler_image"] = native.IMAGE
        binary = self.private / "products/native-tree-inventory.test"
        self.result["builds"] += 1
        rc, _, stderr = self.container("build", native.GOROOT / "bin/go",
            ["test", "-c", "-work", "-x", "-p=1", "-mod=readonly",
             "-modfile=" + str(native.ORIGINAL / "candidate.mod"),
             "-tags", native.TAGS + " pinkha_localstore_witness",
             "-o", str(binary), "./core/pinkha/localstorewitness"],
            build=True, seconds=1800)
        require(rc == 0, "native_inventory_compile_failed")
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
                                    ["-test.list=^TestNativeTreeInventory"], seconds=30)
        require(rc == 0 and out.read_text().splitlines() == METHODS,
                "actual_binary_inventory_methods")
        self.result["actual_named_methods_sha256"] = sha(out)
        for index, method in enumerate(METHODS, 1):
            row = {"method": method, "status": "FAIL"}
            self.result["methods"].append(row)
            rc, stdout, _ = self.container("inventory-method-" + str(index), Path("/usr/bin/env"),
                ["PINKHA_NATIVE_OWNED_SNAPSHOT_PRIVATE_ROOT=" + str(self.private / "fixtures"),
                 str(binary), "-test.v", "-test.run=^" + method + "$",
                 "-test.count=1", "-test.timeout=210s"])
            row["exit_code"] = rc
            try:
                require(rc == 0, "native_inventory_method_exit")
                row["audit"] = audit_method(stdout, method)
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
                "native_inventory_three_method_acceptance")
        self.result["status"] = "THREE_NATIVE_INVENTORY_METHODS_PASS"


def main():
    runner = InventoryRunner()
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
    return 0 if runner.result["status"] == "THREE_NATIVE_INVENTORY_METHODS_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
