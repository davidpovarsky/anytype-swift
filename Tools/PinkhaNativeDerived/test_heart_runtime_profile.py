"""Synthetic admission controls only; these do not execute native or Apple tests."""
import argparse
import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import attachment_runtime as attachment
import build_t5_r15_runtime as builder
import download_heart_runtime as download
import heart_runtime_profile as profiles
import install_verified_heart as installer

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "codex/chatgpt-wave15-shared-20261121"
REPOSITORY = "davidpovarsky/anytype-swift"
PRODUCER_SHA = "a" * 40
CONSUMER_SHA = "f" * 40


def packed_zip(name, raw):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, raw)
    return buffer.getvalue()


def fixture_log():
    basic = "github.com/anyproto/anytype-heart/core/block/editor/basic"
    details = "github.com/anyproto/anytype-heart/core/block/detailservice"
    top = "TestTorahOrdinaryDetailsDoNotAttachProjectedProperties"
    names = [(basic, top), (details, "TestTorahExplicitAttachmentsSurviveOrdinaryDetailsEdits")]
    names += [(basic, top + "/" + api + "/" + state) for api in ("SetDetails", "UpdateDetails")
              for state in ("unattached", "explicit-source-already-attached")]
    events = [dict(Package=package, Test=name, Action=action)
              for package, name in names for action in ("run", "pass")]
    events += [dict(Package=package, Action="pass") for package in (basic, details)]
    return "".join(json.dumps(event) + "\n" for event in events).encode()


class RuntimeConsumerControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corrected = attachment.prepare(ROOT, ROOT, profiles.CORRECTED)
        approval = attachment.APPROVAL_ROOT + "/revision-14"
        cls.legacy = (
            attachment.frozen_blob(ROOT, approval + "/native-heart-integration.patch"),
            attachment.frozen_blob(ROOT, approval + "/native-heart-integration.json"),
        )

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.app = self.root / "app"
        self.app.mkdir()
        self.commands = []

    def run_metadata(self):
        return dict(id=9991, status="completed", conclusion="success", run_attempt=1,
                    head_sha=PRODUCER_SHA, head_branch=BRANCH, repository=dict(full_name=REPOSITORY),
                    event="workflow_dispatch", path=".github/workflows/torah-inspector-ipados27.yml",
                    display_title="Pinkha t5-r15-attachment-runtime · " + PRODUCER_SHA)

    def make_fixture(self, profile_name=profiles.CORRECTED, mutate_receipt=None, failed_log=False):
        profile = profiles.select(profile_name)
        patch_raw, inventory_raw = ((self.corrected.patch, self.corrected.inventory)
                                    if profile_name == profiles.CORRECTED else self.legacy)
        inventory = json.loads(inventory_raw)
        log_raw = fixture_log()
        log = self.root / "synthetic-native-controller-input.log"
        log.write_bytes(log_raw)
        fixtures = builder.qualify_corrected_fixtures(log)
        if failed_log:
            log_raw = log_raw.replace(b'"Action": "pass"', b'"Action": "fail"', 1)
            fixtures["log_sha256"] = profiles.digest_bytes(log_raw)
        files = {path: b"synthetic-controller-binary\x00" + profile.binary_marker.encode()
                 for path, _ in builder.EXPECTED_SLICES}
        slices = [dict(path=path, architecture=architecture,
                       sha256=profiles.digest_bytes(files[path]), marker=profile.binary_marker)
                  for path, architecture in sorted(builder.EXPECTED_SLICES)]
        receipt = dict(status="PASS", target="ios", heart_sha=attachment.HEART_SHA,
                       patch_sha256=profile.patch_sha256, marker=profile.receipt_marker,
                       files=inventory["files"], binary_slices=slices,
                       artifacts=[dict(path=name, sha256=profiles.digest_bytes(raw)) for name, raw in sorted(files.items())])
        if profile_name == profiles.CORRECTED:
            receipt.update(github_run_id="9991", github_run_attempt="1", integration_sha=PRODUCER_SHA,
                           source_sha=attachment.SOURCE_SHA, runtime_variant=profile.name,
                           inventory_sha256=profile.inventory_sha256, expected_app_get_version=profile.version,
                           capability_marker="pinkha-native-t5-lookup-v1-" + profile.patch_sha256,
                           build_status="APPLE_FRAMEWORK_BUILT_NOT_EXECUTED",
                           app_get_version_status="NOT_RUN_BUILD_ONLY",
                           native_tests="PASS_FOCUSED_ATTACHMENT_FIXTURES", native_test_invocations=2,
                           correction_provenance=inventory["correction_provenance"],
                           native_attachment_fixtures=fixtures)
        if mutate_receipt:
            mutate_receipt(receipt)
        receipt_raw = (json.dumps(receipt, indent=2) + "\n").encode()
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as archive:
            for name, raw in {**{"Lib.xcframework/" + name: raw for name, raw in files.items()},
                              "PinkhaNativeHeartBuild.json": receipt_raw}.items():
                item = tarfile.TarInfo(name); item.size = len(raw)
                archive.addfile(item, io.BytesIO(raw))
        runtime_tar = tar_buffer.getvalue()
        runtime_zip = packed_zip(profile.archive_name, runtime_tar)
        artifact_receipt = dict(status="APPLE_RUNTIME_ARTIFACT_BUILT_NOT_EXECUTED",
                                sha256=profiles.digest_bytes(runtime_tar),
                                receipt_sha256=profiles.digest_bytes(receipt_raw), github_run_id="9991",
                                github_run_attempt="1", integration_sha=PRODUCER_SHA,
                                runtime_variant=profile.name, expected_app_get_version=profile.version)
        proof_buffer = io.BytesIO()
        with zipfile.ZipFile(proof_buffer, "w") as archive:
            members = {
                "runtime/custom-heart-build.json": receipt_raw,
                "runtime/runtime-artifact.json": json.dumps(artifact_receipt).encode(),
                "runtime/corrected-native-source/native-heart-integration.patch.txt": patch_raw,
                "runtime/corrected-native-source/native-heart-integration.json": inventory_raw,
                "runtime/corrected-attachment-fixtures.log": log_raw,
                "runtime/corrected-attachment-fixtures.json": json.dumps(fixtures).encode(),
            }
            for name, raw in members.items():
                archive.writestr(name, raw)
        proof_zip = packed_zip("Pinkha-Native-Derived-Evidence.zip", proof_buffer.getvalue())
        artifacts = []
        for identifier, name, raw in [
            (1001, profile.artifact_name, runtime_zip),
            (1002, "Pinkha-T5-Attachment-Runtime-" + profile.name + "-9991-1", proof_zip),
        ]:
            artifacts.append(dict(id=identifier, name=name, expired=False, size_in_bytes=len(raw),
                                  digest="sha256:" + profiles.digest_bytes(raw),
                                  workflow_run=dict(id=9991, head_sha=PRODUCER_SHA)))
        args = argparse.Namespace(runtime_profile=profile_name, source_run_id="9991",
                                  expected_app_branch=BRANCH, repository=REPOSITORY,
                                  app_source=self.app, work=self.root / "download", evidence=self.root / "evidence")
        approval = self.app / attachment.APPROVAL_ROOT / "revision-14"
        approval.mkdir(parents=True)
        (approval / "native-heart-integration.patch").write_bytes(self.legacy[0])
        (approval / "native-heart-integration.json").write_bytes(self.legacy[1])
        return dict(args=args, profile=profile, run=self.run_metadata(), artifacts=artifacts,
                    runtime_tar=runtime_tar, runtime_zip=runtime_zip, proof_zip=proof_zip,
                    receipt=receipt, inventory=inventory)

    def execute(self, fixture, *, corrupt_download=False):
        def command(argv, output=None, timeout=300):
            self.commands.append(list(argv))
            if argv[1:3] == ["run", "download"]:
                (fixture["args"].work / fixture["profile"].archive_name).write_bytes(fixture["runtime_tar"])
                return
            endpoint = argv[2]
            if endpoint.endswith("/actions/runs/9991"):
                raw = json.dumps(fixture["run"]).encode()
            elif endpoint.endswith("/artifacts?per_page=100"):
                raw = json.dumps(dict(total_count=len(fixture["artifacts"]), artifacts=fixture["artifacts"])).encode()
            elif endpoint.endswith("/artifacts/1001/zip"):
                raw = fixture["runtime_zip"] + (b"corrupted" if corrupt_download else b"")
            elif endpoint.endswith("/artifacts/1002/zip"):
                raw = fixture["proof_zip"]
            else:
                self.fail("Unexpected download command: " + repr(argv))
            output.write_bytes(raw)

        def slices(framework, marker):
            result = []
            for name, architecture in sorted(builder.EXPECTED_SLICES):
                raw = (framework / name).read_bytes()
                profiles.require(marker.encode() in raw, "Synthetic binary does not contain the requested full marker")
                result.append(dict(path=name, architecture=architecture,
                                   sha256=profiles.digest_bytes(raw), marker=marker))
            return result

        with patch.object(download, "command", side_effect=command), \
             patch.object(installer, "git", side_effect=lambda _, *args: BRANCH if args[0] == "branch" else CONSUMER_SHA), \
             patch.object(installer, "verify_framework_slices", side_effect=slices):
            return download.execute(fixture["args"])

    def test_corrected_archive_original_proof_and_installed_binding_retain_exact_producer(self):
        fixture = self.make_fixture()
        result = self.execute(fixture)
        binding = profiles.installed_binding(self.app, result, CONSUMER_SHA, profiles.CORRECTED, "9991")
        self.assertEqual(profiles.verify_binding(binding), fixture["profile"].version)
        self.assertEqual(binding["heart_source_sha"], PRODUCER_SHA)
        self.assertEqual(binding["heart_source_attempt"], "1")
        self.assertEqual(binding["heart_artifact_id"], 1001)
        self.assertEqual(binding["heart_proof_artifact_id"], 1002)
        self.assertEqual(len(self.commands), 4)
        self.assertFalse(any(command[1:3] == ["run", "download"] for command in self.commands))
        self.assertEqual((fixture["args"].evidence / "original-corrected-attachment-fixtures.log").read_bytes(), fixture_log())

    def test_default_original_r14_keeps_its_artifact_source_and_marker(self):
        fixture = self.make_fixture("r14")
        result = self.execute(fixture)
        binding = profiles.installed_binding(self.app, result, CONSUMER_SHA, "r14", "9991")
        self.assertEqual(binding, dict(runtime_profile="r14", native_marker=profiles.select().binary_marker))
        self.assertEqual(len(self.commands), 1)
        self.assertEqual(self.commands[0][1:3], ["run", "download"])
        self.assertIn("Pinkha-Universal-Verified-Heart-r14", self.commands[0])

    def test_original_or_partial_version_cannot_be_relabelled_corrected(self):
        for field, value in [
            ("runtime_variant", "r15"), ("expected_app_get_version", profiles.select().version),
            ("expected_app_get_version", profiles.select(profiles.CORRECTED).receipt_marker),
            ("github_run_id", "9992"), ("github_run_attempt", "2"),
            ("integration_sha", "b" * 40), ("source_sha", "c" * 40),
            ("inventory_sha256", "d" * 64), ("native_test_invocations", 0),
            ("native_tests", "NOT_RUN_BUILD_ONLY"),
        ]:
            with self.subTest(field=field, value=value):
                self.setUp()
                fixture = self.make_fixture(mutate_receipt=lambda r: r.update({field: value}))
                with self.assertRaises(RuntimeError):
                    self.execute(fixture)
                self.assertFalse((self.app / "Dependencies/Middleware/Lib.xcframework").exists())

    def test_wrong_source_run_attempt_branch_repository_route_and_nonpass_are_rejected(self):
        cases = [
            ("id", 9992), ("status", "in_progress"), ("conclusion", "failure"),
            ("run_attempt", 0), ("head_branch", "another-branch"),
            ("repository", dict(full_name="another/repo")), ("event", "pull_request"),
            ("path", ".github/workflows/another.yml"), ("display_title", "Pinkha t5-r15-runtime · " + PRODUCER_SHA),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                run = self.run_metadata(); run[field] = value
                with self.assertRaises(RuntimeError):
                    profiles.validate_producer(run, "9991", REPOSITORY, BRANCH)

    def test_foreign_expired_duplicate_or_missing_artifact_cannot_trigger_a_fallback(self):
        for mode in ("head", "run", "expired", "duplicate", "missing"):
            with self.subTest(mode=mode):
                self.setUp()
                fixture = self.make_fixture()
                entry = fixture["artifacts"][0]
                if mode == "head": entry["workflow_run"]["head_sha"] = "b" * 40
                elif mode == "run": entry["workflow_run"]["id"] = 9992
                elif mode == "expired": entry["expired"] = True
                elif mode == "duplicate": fixture["artifacts"].append(copy.deepcopy(entry))
                else: fixture["artifacts"].pop(0)
                with self.assertRaises(RuntimeError):
                    self.execute(fixture)
                self.assertFalse(any(command[1:3] == ["run", "download"] for command in self.commands))

    def test_modified_original_zip_fails_before_unpack_or_install(self):
        fixture = self.make_fixture()
        with self.assertRaisesRegex(RuntimeError, "digest/size"):
            self.execute(fixture, corrupt_download=True)
        self.assertFalse((self.app / "Dependencies/Middleware/Lib.xcframework").exists())

    def test_self_consistent_build_metadata_cannot_hide_a_failed_original_native_fixture(self):
        fixture = self.make_fixture(failed_log=True)
        with self.assertRaisesRegex(RuntimeError, "did not pass"):
            self.execute(fixture)
        self.assertFalse((self.app / "Dependencies/Middleware/Lib.xcframework").exists())

    def test_installed_receipt_change_or_wrong_consumer_source_cannot_become_runtime_proof(self):
        fixture = self.make_fixture()
        result = self.execute(fixture)
        with self.assertRaises(RuntimeError):
            profiles.installed_binding(self.app, result, "c" * 40, profiles.CORRECTED, "9991")
        with self.assertRaises(RuntimeError):
            profiles.installed_binding(self.app, result, CONSUMER_SHA, profiles.CORRECTED, "9992")
        receipt = self.app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json"
        receipt.write_bytes(receipt.read_bytes() + b"\n")
        with self.assertRaises(RuntimeError):
            profiles.installed_binding(self.app, result, CONSUMER_SHA, profiles.CORRECTED, "9991")

    def test_existing_native_installation_is_preserved_instead_of_overwritten(self):
        fixture = self.make_fixture()
        target = self.app / "Dependencies/Middleware/Lib.xcframework/original"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing native installation")
        with self.assertRaisesRegex(RuntimeError, "overwrite"):
            self.execute(fixture)
        self.assertEqual(target.read_bytes(), b"existing native installation")

    def test_unrecognized_profile_or_missing_mapped_producer_fields_fails_closed(self):
        with self.assertRaises(RuntimeError):
            profiles.select("r15")
        fixture = self.make_fixture()
        result = self.execute(fixture)
        binding = profiles.installed_binding(self.app, result, CONSUMER_SHA, profiles.CORRECTED, "9991")
        for key in profiles.BINDING_KEYS:
            changed = dict(binding); changed.pop(key)
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                profiles.verify_binding(changed)

    def test_transport_payload_cannot_extract_foreign_paths_or_extra_members(self):
        for name in ("../unexpected.tar.gz", "foreign.tar.gz"):
            raw = packed_zip(name, b"synthetic payload")
            path = self.root / "foreign.zip"; path.write_bytes(raw)
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                download.extract_payload(path, "expected.tar.gz", self.root)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("expected.tar.gz", b"a")
            archive.writestr("unexpected", b"b")
        path.write_bytes(buffer.getvalue())
        with self.assertRaises(RuntimeError):
            download.extract_payload(path, "expected.tar.gz", self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
