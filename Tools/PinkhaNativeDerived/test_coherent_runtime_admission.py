"""Adversarial controls for coherent admission; no Apple/native test execution."""
import argparse
import base64
import copy
import io
import json
from pathlib import Path
import plistlib
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import coherent_runtime_admission as admission
import download_heart_runtime as download
import heart_runtime_profile as profiles

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "docs/validation/20261122-coherent-heart-native-pass/original"
BRANCH = "codex/chatgpt-wave15-shared-20261121"
REPOSITORY = "davidpovarsky/anytype-swift"
PRODUCER = "a" * 40
CONSUMER = "b" * 40
UDID = "12345678-1234-1234-1234-123456789ABC"


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def packed_zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return output.getvalue()


def packed_tar(files, extra=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, raw in files.items():
            member = tarfile.TarInfo(name); member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        if extra is not None:
            member, raw = extra
            archive.addfile(member, io.BytesIO(raw) if raw is not None else None)
    return output.getvalue()


def varint(value):
    output = bytearray()
    while value > 127:
        output.append((value & 127) | 128); value >>= 7
    output.append(value)
    return bytes(output)


def bytes_field(number, raw):
    return varint(number * 8 + 2) + varint(len(raw)) + raw


class CoherentAdmissionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch_raw = (ORIGINAL / "runtime-source/native-heart-integration.patch").read_bytes()
        cls.inventory_raw = (ORIGINAL / "runtime-source/native-heart-integration.json").read_bytes()
        cls.inventory = json.loads(cls.inventory_raw)
        cls.original = {name: (ORIGINAL / "actual" / name).read_bytes() for name in admission.RAW_FILES
                        if not name.startswith("object-")}
        cls.profile = profiles.select(profiles.COHERENT)
        profiles.verify_source(cls.profile, cls.patch_raw, cls.inventory_raw)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = self.root / "app"; self.app.mkdir()
        self.calls = []

    def fixture(self, mutate=None, tar_extra=None):
        profile = self.profile
        product_binary = b"synthetic production controller input\x00" + profile.binary_marker.encode()
        fixture_binary = b"synthetic fixture controller input\x00" + admission.FIXTURE_TAG.encode()
        descriptor = {"AvailableLibraries": [dict(LibraryIdentifier="ios-arm64-simulator", LibraryPath="Lib.framework",
                       SupportedArchitectures=["arm64"], SupportedPlatform="ios", SupportedPlatformVariant="simulator")]}
        files = {admission.BINARY: product_binary, "Info.plist": plistlib.dumps(descriptor),
                 "ios-arm64-simulator/Lib.framework/Headers/Service.objc.h": b"ServicePinkhaTorahAuthorizedOperationRead"}
        hashes = {name: profiles.digest_bytes(raw) for name, raw in files.items()}
        slices = [dict(path=admission.BINARY, architecture="arm64", sha256=hashes[admission.BINARY], marker=profile.version)]
        production = dict(fixture_compiled=False, fixture_tag=None, binary_sha256=hashes[admission.BINARY],
                          files_sha256=hashes, binary_slices=slices, artifact_name=profile.archive_name)
        fixture = dict(fixture_compiled=True, fixture_tag=admission.FIXTURE_TAG,
                       binary_sha256=profiles.digest_bytes(fixture_binary),
                       files_sha256={admission.BINARY: profiles.digest_bytes(fixture_binary)})
        native_hashes = {entry["path"]: entry["after_sha256"] for entry in self.inventory["files"]}
        receipt = dict(status="PASS", target="ios", heart_sha=self.inventory["heart_sha"],
            patch_sha256=profile.patch_sha256, inventory_sha256=profile.inventory_sha256,
            marker=profile.receipt_marker, capability_marker="pinkha-native-t5-lookup-v1-" + profile.patch_sha256,
            files=self.inventory["files"], artifacts=[dict(path=name, sha256=sha) for name, sha in hashes.items()],
            binary_slices=slices, runtime_variant=profile.name, expected_app_get_version=profile.version,
            github_run_id="9991", github_run_attempt="1", integration_sha=PRODUCER,
            fixture_included=False, selected_framework="production", fixture_tag=None, fixture_source_sha256={}, bridge_sha256=None,
            target_architecture="arm64", target_environment="simulator", native_source_run=profiles.COHERENT_NATIVE_RUN,
            native_source_sha=admission.NATIVE_SOURCE, native_source_count=139, native_test_invocations=0,
            build_status="APPLE_FRAMEWORK_BUILT_NOT_EXECUTED", app_get_version_status="NOT_RUN_BUILD_ONLY")
        build = dict(status="BUILT_DISTINCT_COHERENT_APPLE_FRAMEWORKS_NOT_EXECUTED", app_sha=PRODUCER,
                     run_id="9991", run_attempt="1", native_run=profiles.COHERENT_NATIVE_RUN, native_source=admission.NATIVE_SOURCE,
                     patch_sha256=profile.patch_sha256, inventory_sha256=profile.inventory_sha256,
                     native_source_count=139, native_source_sha256=native_hashes,
                     runtime_version=profile.version, old_tests_executed=0, production_binary_execution="NOT_RUN",
                     original_fixture_sha256=admission.ORIGINAL_FIXTURE, bridge_sha256="c" * 64,
                     frameworks={"production": production, "fixture": fixture})
        native_files = dict(self.original)
        native_observation = json.loads(native_files["native-observation.json"])
        for kind in ("search", "show"):
            description = native_observation["object_" + kind + "_error_description"].encode()
            native_files["object-" + kind + "-removed.pb"] = bytes_field(1, b"\x08\x02" + bytes_field(2, description))
        coherent = json.loads(native_files["coherent-observation.json"])
        owner_response = admission._fields(native_files["coherent-owner.pb"])
        snapshot = admission._fields(admission._one(owner_response, 3, 2))
        actual = dict(status=admission.APPLE_PASS, app_sha=PRODUCER, run_id="9991", run_attempt="1",
                      nonce=coherent["nonce"], pid=coherent["pid"], production_binary_execution="NOT_RUN",
                      full_app_acceptance="NOT_RUN", network_acl_transport="NOT_RUN", fresh_ios_process_reopen="NOT_RUN",
                      native=dict(status="PASS_ACTUAL_COHERENT_APPLE_FIXTURE", nonce=coherent["nonce"], pid=coherent["pid"],
                        bridge_sha256=build["bridge_sha256"], original_fixture_sha256=admission.ORIGINAL_FIXTURE,
                        runtime_version=profile.version, heart_sha=self.inventory["heart_sha"], production_binary_executed=False,
                        fixture_tag=admission.FIXTURE_TAG, network_acl_transport="NOT_RUN", full_app_acceptance="NOT_RUN",
                        account_id=admission._one(snapshot, 2, 2).decode(), space_id=admission._one(snapshot, 3, 2).decode(),
                        operation_id=coherent["nonce"], files={}, files_sha256={}),
                      shared_swift_codec=dict(owner_decoded=True, reader_decoded=True, exact_variants=True,
                                              removed_rejected=True, removed_error="permissionDenied"))
        device = dict(deviceId=UDID, osVersion="27.0", osBuildNumber="24A1", architecture="arm64")
        summary = dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                       devicesAndConfigurations=[dict(device=device)])
        identifier = "CoherentHeartAuthorityHarnessTests/" + admission.METHOD + "()"
        tree = dict(testNodes=[dict(nodeType="Test Case", nodeIdentifier=identifier, result="Passed")])
        modules = {"Modules/PinkhaKit/Sources/Read.swift": b"unchanged synthetic shared model",
                   "Modules/PinkhaHeartEngine/Sources/Codec.swift": b"unchanged synthetic codec"}
        copied = {name: profiles.digest_bytes(raw) for name, raw in modules.items()}
        source_map = {**copied, "Tools/PinkhaNativeDerived/coherent_apple/run_host.py": "d" * 64}
        host = dict(status=admission.APPLE_PASS, app_sha=PRODUCER, run_id="9991", run_attempt="1",
            native_run=profiles.COHERENT_NATIVE_RUN, production_binary_execution="NOT_RUN", full_app_acceptance="NOT_RUN",
            network_acl_transport="NOT_RUN", fresh_ios_process_reopen="NOT_RUN", old_native_methods_executed=0,
            old_swift_methods_executed=0, app_capability="OFF", copied_module_sha256=copied,
            source_snapshot_sha256=profiles.json_digest(source_map),
            production_binary_sha256=production["binary_sha256"], fixture_binary_sha256=fixture["binary_sha256"],
            bridge_sha256=build["bridge_sha256"], shared_swift_codec=actual["shared_swift_codec"],
            configuration=dict(appSHA=PRODUCER, runID="9991", runAttempt="1", nonce=actual["nonce"],
                               bridgeSHA=build["bridge_sha256"], originalFixtureSHA=admission.ORIGINAL_FIXTURE,
                               runtimeVersion=profile.version),
            commands=[dict(name="ios-coherent-tests", status="PASS_EXIT_0",
                           argv=["xcodebuild", "test", "-only-testing:CoherentHeartAuthorityHarnessTests/" + admission.METHOD])],
            actual_execution=dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                                  method=admission.METHOD, udid=UDID, device=device, actual_cases={identifier: "Passed"}))
        run = dict(id=9991, status="completed", conclusion="success", run_attempt=1,
                   head_sha=PRODUCER, head_branch=BRANCH, repository=dict(full_name=REPOSITORY),
                   path=".github/workflows/torah-inspector-ipados27.yml", event="workflow_dispatch",
                   display_title="Pinkha coherent-heart-apple · " + PRODUCER)
        value = dict(receipt=receipt, build=build, host=host, actual=actual, native_files=native_files,
                     files=files, run=run, summary=summary, tree=tree, source_map=source_map, modules=modules,
                     patch_raw=self.patch_raw, inventory_raw=self.inventory_raw)
        if mutate:
            mutate(value)
        for name, raw in value["modules"].items():
            path = self.app / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        # Recompute outer transport hashes after mutations: failures therefore
        # exercise semantic admission, rather than merely a stale ZIP checksum.
        for name, raw in value["native_files"].items():
            actual["native"]["files"][name] = base64.b64encode(raw).decode()
            actual["native"]["files_sha256"][name] = profiles.digest_bytes(raw)
        receipt_raw = encoded(receipt)
        runtime_tar = packed_tar({**{"Lib.xcframework/" + name: raw for name, raw in value["files"].items()},
                                  "PinkhaNativeHeartBuild.json": receipt_raw}, extra=tar_extra)
        production["artifact_sha256"] = profiles.digest_bytes(runtime_tar)
        build_raw = encoded(build)
        actual_raw = encoded(actual)
        host.update(build_receipt_sha256=profiles.digest_bytes(build_raw), actual_attachment_sha256=profiles.digest_bytes(actual_raw))
        artifact = dict(status="APPLE_RUNTIME_ARTIFACT_BUILT_NOT_EXECUTED", path=profile.archive_name,
            sha256=profiles.digest_bytes(runtime_tar), receipt_sha256=profiles.digest_bytes(receipt_raw),
            runtime_variant=profile.name, fixture_included=False, integration_sha=PRODUCER,
            github_run_id="9991", github_run_attempt="1", patch_sha256=profile.patch_sha256,
            inventory_sha256=profile.inventory_sha256, heart_sha=self.inventory["heart_sha"])
        proof_files = {
            "proof/production/custom-heart-build.json": receipt_raw,
            "proof/production/runtime-artifact.json": encoded(artifact),
            "proof/native-source/native-heart-integration.patch": value["patch_raw"],
            "proof/native-source/native-heart-integration.json": value["inventory_raw"],
            "proof/native-source-after.json": encoded(native_hashes), "proof/build.json": build_raw,
            "proof/host/receipt.json": encoded(host), "proof/host/actual.json": actual_raw,
            "proof/host/control-source-before.json": encoded(source_map), "proof/host/control-source-after.json": encoded(source_map),
            "proof/host/xcresult-summary.log": encoded(summary), "proof/host/xcresult-tests.log": encoded(tree),
            "proof/host/coherent-heart.xcresult/Info.plist": plistlib.dumps({"synthetic_control": True}),
            **{"proof/host/native/" + name: raw for name, raw in value["native_files"].items()},
        }
        runtime_zip = packed_zip({profile.archive_name: runtime_tar})
        proof_zip = packed_zip(proof_files)
        names = [profile.artifact_name, "Pinkha-Coherent-Heart-Apple-9991-1"]
        items = [dict(id=1001+i, name=name, expired=False, size_in_bytes=len(raw), digest="sha256:" + profiles.digest_bytes(raw),
                      workflow_run=dict(id=9991, head_sha=PRODUCER, head_branch=BRANCH))
                 for i, (name, raw) in enumerate(zip(names, [runtime_zip, proof_zip]))]
        value.update(args=argparse.Namespace(runtime_profile=profile.name, source_run_id="9991", expected_app_branch=BRANCH,
                     repository=REPOSITORY, app_source=self.app, work=self.root/"work", evidence=self.root/"evidence"),
                     runtime_zip=runtime_zip, proof_zip=proof_zip, items=items, actual_raw=actual_raw)
        return value

    def run_fixture(self, value, *, corrupt_zip=False, summary_replay=None, tree_replay=None, attachment_replay=None, changed_head=False):
        def command(argv, output=None, timeout=300):
            self.calls.append(list(argv))
            if argv[:2] == ["gh", "api"]:
                endpoint = argv[2]
                if endpoint.endswith("/runs/9991"):
                    raw = encoded(value["run"])
                elif endpoint.endswith("/artifacts?per_page=100"):
                    raw = encoded(dict(total_count=len(value["items"]), artifacts=value["items"]))
                elif endpoint.endswith("/artifacts/1001/zip"):
                    raw = value["runtime_zip"] + (b"corrupt" if corrupt_zip else b"")
                elif endpoint.endswith("/artifacts/1002/zip"):
                    raw = value["proof_zip"]
                else:
                    self.fail("Unexpected network command " + repr(argv))
            elif argv[:4] == ["xcrun", "xcresulttool", "get", "test-results"]:
                raw = encoded((value["summary"] if summary_replay is None else summary_replay) if argv[4]=="summary"
                              else (value["tree"] if tree_replay is None else tree_replay))
            elif argv[:4] == ["xcrun", "xcresulttool", "export", "attachments"]:
                path = Path(argv[argv.index("--output-path")+1]); path.mkdir()
                (path/"actual.json").write_bytes(value["actual_raw"] if attachment_replay is None else attachment_replay)
                raw = b"synthetic control export\n"
            else:
                self.fail("Admission attempted an unexpected command: " + repr(argv))
            with output.open("xb") as stream:
                stream.write(raw)
        git_calls = []
        def source_git(_, *args):
            git_calls.append(args)
            if args[0] == "branch":
                return BRANCH
            if args[0] == "status":
                return ""
            if args[0] == "ls-files":
                return "\0".join(sorted(value["modules"]))+"\0"
            return "e" * 40 if changed_head and len(git_calls)>2 else CONSUMER
        def slices(framework, marker):
            binary = framework / admission.BINARY
            profiles.require(marker.encode() in binary.read_bytes(), "Synthetic control marker missing")
            return [dict(path=admission.BINARY, architecture="arm64", sha256=admission.digest(binary), marker=marker)]
        with patch.object(download, "command", side_effect=command), patch.object(admission, "git", side_effect=source_git), \
             patch.object(admission, "verify_framework_slices", side_effect=slices):
            return download.execute(value["args"])

    def assert_not_installed(self):
        self.assertFalse((self.app/"Dependencies/Middleware/Lib.xcframework").exists())

    def test_exact_production_and_replayed_original_proof_are_admitted(self):
        value = self.fixture()
        result = self.run_fixture(value)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["installed_fixture"])
        self.assertEqual(result["production_binary_execution"], "NOT_RUN")
        self.assertEqual(result["coherent_fixture_ios_acceptance"], admission.APPLE_PASS)
        self.assertEqual(result["producer"]["source_sha"], PRODUCER)
        self.assertEqual(result["app_source_sha"], CONSUMER)
        self.assertEqual(result["heart_artifact_id"], 1001)
        self.assertEqual(result["heart_proof_artifact_id"], 1002)
        binding = profiles.installed_binding(self.app, result, CONSUMER, profiles.COHERENT, "9991")
        self.assertEqual(profiles.verify_binding(binding), self.profile.version)
        self.assertEqual(len(self.calls), 7)
        self.assertFalse(any(argv[0] in ("xcodebuild", "go", "swift") for argv in self.calls))

    def test_another_or_unsuccessful_producer_cannot_be_admitted(self):
        for key, invalid in [("conclusion","failure"),("status","in_progress"),("run_attempt",0),
                             ("head_branch","develop"),("head_sha","f"*40),("event","push"),
                             ("path",".github/workflows/another.yml"),("display_title","Pinkha coherent-heart-native · "+PRODUCER)]:
            with self.subTest(key=key):
                self.setUp(); value=self.fixture(lambda f: f["run"].update({key:invalid}))
                with self.assertRaises(RuntimeError): self.run_fixture(value)
                self.assert_not_installed()

    def test_expired_wrong_branch_repeated_or_corrupt_artifacts_fail(self):
        for mutate in [lambda v:v["items"][0].update(expired=True),
                       lambda v:v["items"][0]["workflow_run"].update(head_branch="develop"),
                       lambda v:v["items"].append(copy.deepcopy(v["items"][0])),
                       lambda v:v["items"][0].update(digest="sha256:"+"0"*64),
                       lambda v:v["items"][0].update(size_in_bytes=v["items"][0]["size_in_bytes"]+1)]:
            self.setUp(); value=self.fixture(); mutate(value)
            with self.assertRaises(RuntimeError): self.run_fixture(value)
            self.assert_not_installed()
        self.setUp(); value=self.fixture()
        with self.assertRaises(RuntimeError): self.run_fixture(value,corrupt_zip=True)
        self.assert_not_installed()

    def test_test_only_or_relabelled_receipt_is_rejected(self):
        for key, invalid in [("fixture_included",True),("selected_framework","fixture"),("fixture_tag",admission.FIXTURE_TAG),
                             ("bridge_sha256","c"*64),("fixture_source_sha256",{"bridge.go":"c"*64}),
                             ("target_architecture","x86_64"),("target_environment","device"),
                             ("native_source_count",138),("native_source_run","44961619024"),
                             ("native_source_sha","e"*40),("native_test_invocations",1),
                             ("runtime_variant","r15-attachment-v1"),("app_get_version_status","PASS")]:
            with self.subTest(key=key):
                self.setUp(); value=self.fixture(lambda f:f["receipt"].update({key:invalid}))
                with self.assertRaises(RuntimeError): self.run_fixture(value)
                self.assert_not_installed()

    def test_changed_frozen_source_bytes_fail_despite_fresh_artifact_hashes(self):
        for key in ("patch_raw","inventory_raw"):
            self.setUp(); value=self.fixture(lambda f:f.update({key:f[key]+b"\n"}))
            with self.assertRaises(RuntimeError): self.run_fixture(value)
            self.assert_not_installed()

    def test_fixture_binary_or_bridge_cannot_hide_in_production_inventory(self):
        def injected(f):
            name="ios-arm64-simulator/Lib.framework/Headers/Service.objc.h"
            f["files"][name] += b"\nServicePinkhaCoherentAppleAuthorityFixture"
            digest=profiles.digest_bytes(f["files"][name])
            for row in f["receipt"]["artifacts"]:
                if row["path"]==name: row["sha256"]=digest
            f["build"]["frameworks"]["production"]["files_sha256"][name]=digest
        value=self.fixture(injected)
        with self.assertRaises(RuntimeError): self.run_fixture(value)
        self.assert_not_installed()
        self.setUp()
        value=self.fixture(lambda f:f["build"]["frameworks"]["fixture"].update(binary_sha256=f["build"]["frameworks"]["production"]["binary_sha256"]))
        with self.assertRaises(RuntimeError): self.run_fixture(value)
        self.assert_not_installed()

    def test_wrong_platform_plist_cannot_pass_binary_hash_only(self):
        def mutate(f):
            plist=plistlib.loads(f["files"]["Info.plist"]);plist["AvailableLibraries"][0]["SupportedPlatformVariant"]="maccatalyst"
            f["files"]["Info.plist"]=plistlib.dumps(plist); digest=profiles.digest_bytes(f["files"]["Info.plist"])
            for row in f["receipt"]["artifacts"]:
                if row["path"]=="Info.plist": row["sha256"]=digest
            f["build"]["frameworks"]["production"]["files_sha256"]["Info.plist"]=digest
        value=self.fixture(mutate)
        with self.assertRaises(RuntimeError): self.run_fixture(value)
        self.assert_not_installed()

    def test_xcresult_replay_prevents_forged_success_json_and_detached_attachment(self):
        value=self.fixture(); failed=copy.deepcopy(value["summary"]);failed.update(passedTests=0,failedTests=1)
        with self.assertRaises(RuntimeError): self.run_fixture(value,summary_replay=failed)
        self.assert_not_installed()
        self.setUp();value=self.fixture()
        with self.assertRaises(RuntimeError): self.run_fixture(value,attachment_replay=b'{"status":"unrelated"}')
        self.assert_not_installed()

    def test_extra_skipped_wrong_or_duplicate_xctest_is_rejected(self):
        mutations=[lambda f:f["summary"].update(skippedTests=1),
                   lambda f:f["tree"]["testNodes"][0].update(nodeIdentifier="Other/testOther()"),
                   lambda f:f["tree"]["testNodes"].append(copy.deepcopy(f["tree"]["testNodes"][0])),
                   lambda f:f["host"]["actual_execution"].update(udid="0"*36)]
        for mutate in mutations:
            self.setUp();value=self.fixture(mutate)
            with self.assertRaises(RuntimeError): self.run_fixture(value)
            self.assert_not_installed()

    def test_native_observation_and_actual_wire_must_agree(self):
        def leaked_t2(f): f["native_files"]["coherent-removed.pb"] += bytes_field(3,b"exposed snapshot")
        def leaked_t5(f): f["native_files"]["object-show-removed.pb"] += bytes_field(2,b"exposed ObjectView")
        def wrong_account(f): f["actual"]["native"]["account_id"]="different account"
        def stale_cache(f):
            observation=json.loads(f["native_files"]["native-observation.json"]);observation["populated_native_cache"]=False
            f["native_files"]["native-observation.json"]=encoded(observation)
        for mutate in (leaked_t2,leaked_t5,wrong_account,stale_cache):
            self.setUp();value=self.fixture(mutate)
            with self.assertRaises(RuntimeError): self.run_fixture(value)
            self.assert_not_installed()

    def test_source_change_between_download_and_copy_fails(self):
        value=self.fixture()
        with self.assertRaises(RuntimeError): self.run_fixture(value,changed_head=True)
        self.assert_not_installed()

    def test_consumer_module_bytes_must_equal_the_original_executed_modules(self):
        value=self.fixture()
        path=self.app/"Modules/PinkhaHeartEngine/Sources/Codec.swift"
        path.write_bytes(b"changed codec cannot inherit the producer's Swift acceptance")
        with self.assertRaisesRegex(RuntimeError,"Consumer shared modules differ"):
            self.run_fixture(value)
        self.assert_not_installed()

    def test_existing_middleware_is_preserved_before_any_download(self):
        value=self.fixture(); existing=self.app/"Dependencies/Middleware/Lib.xcframework"
        existing.mkdir(parents=True);(existing/"owner-data").write_bytes(b"preserve")
        with self.assertRaises(RuntimeError): self.run_fixture(value)
        self.assertEqual((existing/"owner-data").read_bytes(),b"preserve")
        self.assertEqual(self.calls,[])

    def test_archive_traversal_symlinks_duplicates_and_file_parent_conflicts_fail(self):
        cases=[]
        for name in ("../escape","/absolute","C:/escape","Lib.xcframework/../escape","Lib.xcframework\\escape"):
            member=tarfile.TarInfo(name);member.size=1;cases.append((member,b"x"))
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE):
            member=tarfile.TarInfo("Lib.xcframework/evil");member.type=kind;member.linkname="outside";cases.append((member,None))
        duplicate=tarfile.TarInfo("PinkhaNativeHeartBuild.json");duplicate.size=1;cases.append((duplicate,b"x"))
        for extra in cases:
            self.setUp();value=self.fixture(tar_extra=extra)
            with self.assertRaises(RuntimeError): self.run_fixture(value)
            self.assert_not_installed();self.assertFalse((self.root/"escape").exists())
        for names in [[("a",b"x"),("a/b",b"x")],[("a",b"x"),("a",b"x")]]:
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,"w") as archive:
                for name,raw in names: archive.writestr(name,raw)
            archive_path=self.root/"malicious.zip";archive_path.write_bytes(buffer.getvalue())
            with self.assertRaises(RuntimeError): admission.safe_zip(archive_path,self.root/"extract")
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,"w") as archive:
            info=zipfile.ZipInfo("link");info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
            archive.writestr(info,b"outside")
        archive_path=self.root/"link.zip";archive_path.write_bytes(buffer.getvalue())
        with self.assertRaises(RuntimeError): admission.safe_zip(archive_path,self.root/"extract")

    def test_duplicate_json_keys_and_overlong_wire_encodings_fail(self):
        with self.assertRaises(RuntimeError): admission.json_value(b'{"status":"PASS","status":"FAIL"}',"control")
        with self.assertRaises(RuntimeError): admission._fields(b"\x88\x00\x02")
        with self.assertRaises(RuntimeError): admission._fields(b"\x0a\xff\x7fshort")


if __name__ == "__main__":
    unittest.main()
