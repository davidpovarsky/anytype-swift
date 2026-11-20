"""Portable controls of the source/result/producer gates; not Apple test execution."""
import copy
import hashlib
import io
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
import zipfile

import original_editor_profile as profile
import prepare_original_editor_heart as heart
import run_host_tests as host

APP = Path(__file__).resolve().parents[2]


class OriginalEditorProfileTests(unittest.TestCase):
    def setUp(self):
        self.methods = {suite + "/" + name for suite, item in profile.manifest()["suites"].items()
                        for name in item["methods"]}
        self.tree = {"testNodes": [
            {"nodeType": "Test Case", "nodeIdentifier": name + "()", "result": "Passed",
             "children": [{"nodeType": "Test Case Run", "result": "Passed"}]}
            for name in sorted(self.methods)]}
        self.summary = {"totalTestCount": 37, "passedTests": 37, "failedTests": 0, "skippedTests": 0,
                        "devicesAndConfigurations": [{"device": {"deviceId": "owned-ipad",
                            "osVersion": "27.2", "osBuildNumber": "24C-test-control",
                            "architecture": "arm64", "modelName": "iPad Pro"}}]}

    def validate(self, summary=None, tree=None):
        return host.validate_results(summary or self.summary, tree or self.tree, self.methods,
                                     "owned-ipad", host.HostTestProfile.ORIGINAL_EDITOR)

    def test_real_original_git_trees_and_thirty_seven_registered_declarations(self):
        methods, files = profile.expected_methods(APP)
        self.assertEqual(methods, self.methods)
        self.assertEqual(len(files), 6)
        self.assertEqual(sum(profile.suite_counts().values()), 37)
        self.assertEqual(host.expected_methods(APP, host.HostTestProfile.ORIGINAL_EDITOR),
                         (methods, files))

    def test_exact_original_profile_accepts_only_its_source_branch_run_identity(self):
        profile.require_identity("a" * 40, "a" * 40, profile.BRANCH, profile.BRANCH, "123", "1")
        variants = [
            ("b" * 40, "a" * 40, profile.BRANCH, profile.BRANCH, "123", "1"),
            ("a" * 40, "a" * 40, host.BRANCH, profile.BRANCH, "123", "1"),
            ("a" * 40, "a" * 40, profile.BRANCH, host.BRANCH, "123", "1"),
            ("a" * 40, "a" * 40, profile.BRANCH, profile.BRANCH, "0", "1"),
            ("a" * 40, "a" * 40, profile.BRANCH, profile.BRANCH, "123", ""),
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                profile.require_identity(*value)
        with self.assertRaises(ValueError):
            host.require_identity("a" * 40, "a" * 40, profile.BRANCH, profile.BRANCH, "123", "1")

    def test_real_declarations_reject_missing_duplicate_renamed_and_parameterized_methods(self):
        for suite, item in profile.manifest()["suites"].items():
            text = (APP / item["path"]).read_text(encoding="utf-8")
            first = item["methods"][0]
            variants = [
                text.replace("@Test", "", 1),
                text.replace("func " + first + "(", "func wrongName(", 1),
                text.replace("func " + first + "()", "func " + first + "(value: Bool)", 1),
                text.replace("@Test", "@Test(arguments: [false, true])", 1),
                text + "\n@Test func " + first + "() {}\n",
            ]
            for index, variant in enumerate(variants):
                with self.subTest(suite=suite, variant=index), self.assertRaises(ValueError):
                    profile.validate_declarations(variant, suite, item["methods"])

    def test_exact_source_named_result_fixture_is_accepted(self):
        result = self.validate()
        self.assertEqual(result["actual_method_count"], 37)
        self.assertEqual(result["declared_case_count"], 37)
        self.assertEqual(result["counts"]["passedTests"], 37)

    def test_summary_count_failure_skip_and_boolean_cannot_claim_acceptance(self):
        variants = [("totalTestCount", 0), ("totalTestCount", 12), ("passedTests", 10),
                    ("failedTests", 1), ("skippedTests", 1), ("totalTestCount", True)]
        for key, value in variants:
            summary = copy.deepcopy(self.summary)
            summary[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.validate(summary=summary)

    def test_missing_repeated_and_outside_methods_do_not_hide_in_passing_total(self):
        missing = copy.deepcopy(self.tree)
        missing["testNodes"].pop()
        repeated = copy.deepcopy(self.tree)
        repeated["testNodes"][-1] = copy.deepcopy(repeated["testNodes"][0])
        outside = copy.deepcopy(self.tree)
        outside["testNodes"][-1]["nodeIdentifier"] = "UnreviewedSuite/method()"
        for tree in [missing, repeated, outside]:
            with self.subTest(tree=tree), self.assertRaises(ValueError):
                self.validate(tree=tree)

    def test_failed_skipped_or_unknown_execution_descendants_are_rejected(self):
        for child in [
            {"nodeType": "Test Case Run", "result": "Failed"},
            {"nodeType": "Test Case Run", "result": "Skipped"},
            {"nodeType": "Test Case Run"},
            {"nodeType": "Arguments", "result": "Passed", "name": "true"},
            {"nodeType": "Unknown", "result": "Passed"},
        ]:
            tree = copy.deepcopy(self.tree)
            tree["testNodes"][0]["children"] = [child]
            with self.subTest(child=child), self.assertRaises(ValueError):
                self.validate(tree=tree)

    def test_actual_destination_and_os_are_still_mandatory(self):
        for key, value in [("deviceId", "another"), ("osVersion", "26.3"),
                           ("architecture", "x86_64"), ("modelName", "iPhone")]:
            summary = copy.deepcopy(self.summary)
            summary["devicesAndConfigurations"][0]["device"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(summary=summary)

    def test_existing_component_selection_does_not_implicitly_expand(self):
        expected = {name for part in [host.HostTestProfile.SDK06, host.HostTestProfile.EDITOR,
                                    host.HostTestProfile.CORE] for name in part.suites}
        self.assertEqual(set(host.HostTestProfile.COMPONENTS.suites), expected)
        self.assertFalse(set(profile.suite_counts()) & expected)
        self.assertEqual(host.HostTestProfile.ORIGINAL_EDITOR.result_prefix, "original-editor")
        self.assertEqual(host.HostTestProfile.ORIGINAL_EDITOR.pass_status, "ORIGINAL_EDITOR_COMPONENT_PASS")


class OriginalHeartProducerTests(unittest.TestCase):
    def setUp(self):
        self.pin = profile.manifest()["heart"]
        self.run = {"id": self.pin["run_id"], "head_sha": self.pin["head_sha"],
                    "head_branch": self.pin["head_branch"], "run_attempt": 1,
                    "status": "completed", "conclusion": "success",
                    "repository": {"full_name": heart.REPOSITORY},
                    "event": "workflow_dispatch", "path": ".github/workflows/torah-inspector-ipados27.yml",
                    "display_title": "Pinkha heart-runtime \u00b7 " + self.pin["head_sha"]}
        self.artifact = {"id": self.pin["artifact_id"], "name": self.pin["name"], "expired": False,
                         "size_in_bytes": self.pin["zip_bytes"], "digest": "sha256:" + self.pin["zip_sha256"],
                         "workflow_run": {"id": self.pin["run_id"], "head_sha": self.pin["head_sha"],
                                          "head_branch": self.pin["head_branch"]}}

    def test_exact_recorded_metadata_contract(self):
        heart.verify_metadata(self.run, self.artifact, self.pin)

    def test_wrong_producer_source_outcome_attempt_repository_or_route_is_rejected(self):
        variants = [("id", 1), ("head_sha", "a" * 40), ("head_branch", "develop"), ("run_attempt", 2),
                    ("status", "in_progress"), ("conclusion", "failure"),
                    ("repository", {"full_name": "other/repository"}), ("event", "push"),
                    ("path", ".github/workflows/other.yml"), ("display_title", "another scope")]
        for key, value in variants:
            run = copy.deepcopy(self.run)
            run[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                heart.verify_metadata(run, self.artifact, self.pin)

    def test_wrong_expired_digest_size_or_unbound_artifact_is_rejected(self):
        variants = [("id", 1), ("name", "other-runtime"), ("expired", True), ("expired", None),
                    ("size_in_bytes", 1), ("digest", "sha256:" + "0" * 64),
                    ("workflow_run", {"id": 1, "head_sha": self.pin["head_sha"],
                                      "head_branch": self.pin["head_branch"]})]
        for key, value in variants:
            artifact = copy.deepcopy(self.artifact)
            artifact[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                heart.verify_metadata(self.run, artifact, self.pin)

    def make_zip(self, root, names=None, symlink=False):
        path = root / "fixture.zip"
        expected_name = self.pin["name"] + ".tar.gz"
        with zipfile.ZipFile(path, "w") as archive:
            for name in names or [expected_name]:
                item = zipfile.ZipInfo(name)
                if symlink:
                    item.create_system = 3
                    item.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(item, b"UNIT CONTROL ONLY; NOT A HEART FRAMEWORK")
        pin = dict(self.pin, zip_bytes=path.stat().st_size,
                   zip_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        output = root / "output"
        output.mkdir()
        return path, pin, output

    def test_verified_zip_preserves_exact_single_inner_archive_bytes_and_crc(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, pin, output = self.make_zip(Path(temp))
            receipt = heart.unpack_exact_archive(archive, output, pin)
            self.assertTrue(receipt["zip_crc_verified"])
            self.assertEqual(Path(receipt["archive"]).read_bytes(),
                             b"UNIT CONTROL ONLY; NOT A HEART FRAMEWORK")

    def test_wrong_zip_size_or_digest_is_rejected_before_unpacking(self):
        for field, value in [("zip_bytes", 1), ("zip_sha256", "0" * 64)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                archive, pin, output = self.make_zip(Path(temp))
                pin[field] = value
                with self.assertRaises(ValueError):
                    heart.unpack_exact_archive(archive, output, pin)
                self.assertEqual(list(output.iterdir()), [])

    def test_unexpected_extra_traversal_or_symlink_archive_members_are_rejected(self):
        name = self.pin["name"] + ".tar.gz"
        for names, symlink in [([name, "extra"], False), (["../" + name], False), ([name], True)]:
            with self.subTest(names=names, symlink=symlink), tempfile.TemporaryDirectory() as temp:
                archive, pin, output = self.make_zip(Path(temp), names, symlink)
                with self.assertRaises(ValueError):
                    heart.unpack_exact_archive(archive, output, pin)
                self.assertEqual(list(output.iterdir()), [])

    def test_existing_archive_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, pin, output = self.make_zip(Path(temp))
            target = output / (self.pin["name"] + ".tar.gz")
            target.write_bytes(b"existing evidence")
            with self.assertRaises(ValueError):
                heart.unpack_exact_archive(archive, output, pin)
            self.assertEqual(target.read_bytes(), b"existing evidence")


if __name__ == "__main__":
    unittest.main()
