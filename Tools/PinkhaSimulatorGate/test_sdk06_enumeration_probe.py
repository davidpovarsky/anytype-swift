"""New original-Products enumeration admission controls; no product tests."""
import copy
import hashlib
import io
import json
from pathlib import Path
import plistlib
import tarfile
import tempfile
import unittest

import sdk06_enumeration_probe as probe

DOCS = Path(__file__).resolve().parents[2] / "docs/validation/20261123-sdk06-original-enumeration"
ORIGINAL = json.loads((DOCS / "original-selection.json").read_bytes())


def selection():
    return probe.selection_contract(ORIGINAL["execution"], ORIGINAL["discovery"])


def payload(enabled, disabled, plan="Anytype"):
    return {"errors": [], "values": [{"testPlan": plan,
            "enabledTests": [{"identifier": name} for name in enabled],
            "disabledTests": [{"identifier": name} for name in disabled]}]}


def product_archive(root, *, mutation=None):
    data = b"original executable\x00bytes"
    entries = {
        "Build/Products": {"kind": "directory", "mode": 0o755},
        "Build/Products/AnytypeTests.xctest": {"kind": "file", "mode": 0o755,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
    }
    manifest = {"products": copy.deepcopy(entries)}
    members = []
    for name, entry in entries.items():
        member = tarfile.TarInfo(name)
        member.mode = entry["mode"]
        member.type = tarfile.DIRTYPE if entry["kind"] == "directory" else tarfile.REGTYPE
        member.size = 0 if member.isdir() else len(data)
        members.append((member, None if member.isdir() else data))
    if mutation:
        mutation(members, manifest)
    archive = root / "Products.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        for member, body in members:
            output.addfile(member, None if body is None else io.BytesIO(body))
    return archive, manifest


def original_configuration(root):
    path = root / "original.xctestrun"
    value = {
        "__xctestrun_metadata__": {"FormatVersion": 2},
        "TestConfigurations": [{"Name": "Original configuration", "IsEnabled": True,
            "TestTargets": [
                {"BlueprintName": "AnytypeTests", "IsEnabled": True,
                 "TestHostPath": "__TESTROOT__/Anytype.app",
                 "TestBundlePath": "__TESTHOST__/PlugIns/AnytypeTests.xctest",
                 "EnvironmentVariables": {"APP_SETTING": "original"},
                 "TestingEnvironmentVariables": {"DYLD_INSERT_LIBRARIES": "original-injection"},
                 "CommandLineArguments": ["original-argument"],
                 "OnlyTestIdentifiers": [],
                 "SkipTestIdentifiers": ["AnotherSuite/previouslyDisabled()"]},
                {"BlueprintName": "UnrelatedTests", "IsEnabled": True},
            ]}],
    }
    path.write_bytes(plistlib.dumps(value, sort_keys=False))
    return path, value


class EnumerationProbeControls(unittest.TestCase):
    def test_original_actual30_discovery_binds_exact23_and_seven_exclusions(self):
        value = selection()
        self.assertEqual(len(value["selected"]), 23)
        self.assertEqual(len(value["excluded"]), 7)
        self.assertEqual(len(value["declarations"]), 30)
        self.assertEqual(sum(not item.endswith("()") for item in value["excluded"]), 3)
        self.assertEqual(sum(not item.endswith("()") for item in value["selected"]), 8)
        result = probe.qualify_enumeration(payload(value["selected"], value["excluded"], value["test_plan"]), value)
        self.assertEqual(result["status"], probe.PROBE_PASS)
        self.assertEqual(result["actual_product_tests_executed"], 0)

    def test_actual15_and_extra_zero_wrong_plan_or_missing_exclusion_never_qualify(self):
        value = selection()
        exact, excluded, plan = value["selected"], value["excluded"], value["test_plan"]
        nonparameterized = [item for item in exact if item.endswith("()")]
        self.assertEqual(len(nonparameterized), 15)
        cases = [
            payload(nonparameterized, excluded + [item for item in exact if item not in nonparameterized], plan),
            payload(exact + excluded, [], plan),
            payload([], exact + excluded, plan),
            payload(exact, excluded, plan + "-different"),
            payload(exact, excluded[:-1], plan),
            payload(exact, excluded + [exact[0]], plan),
        ]
        for observation in cases:
            with self.subTest(observation=observation), self.assertRaises(ValueError):
                probe.qualify_enumeration(observation, value)

    def test_replayed_run_artifact_source_and_changed_source_inventory_rejected(self):
        artifact = {"id": probe.ARTIFACT_ID, "name": probe.ARTIFACT_NAME,
                    "digest": "sha256:" + probe.OUTER_SHA, "size_in_bytes": probe.OUTER_BYTES,
                    "expired": False, "workflow_run": {"id": int(probe.ORIGINAL_RUN),
                    "head_sha": probe.ORIGINAL_SOURCE,
                    "head_branch": "codex/chatgpt-wave15-acceptance-continuation-20261122"}}
        run = {"id": int(probe.ORIGINAL_RUN), "run_attempt": 1, "head_sha": probe.ORIGINAL_SOURCE,
               "event": "workflow_dispatch", "status": "completed", "conclusion": "failure",
               "repository": {"full_name": probe.REPOSITORY},
               "path": ".github/workflows/torah-inspector-ipados27.yml"}
        probe._api_artifact(artifact)
        probe._api_run(run)
        for key, wrong in [("id", probe.ARTIFACT_ID + 1), ("digest", "sha256:" + "0" * 64),
                           ("size_in_bytes", probe.OUTER_BYTES - 1), ("expired", True)]:
            modified = copy.deepcopy(artifact)
            modified[key] = wrong
            with self.subTest(kind="artifact", key=key), self.assertRaises(ValueError):
                probe._api_artifact(modified)
        for key, wrong in [("head_sha", "0" * 40), ("run_attempt", 2), ("run_attempt", True),
                           ("id", int(probe.ORIGINAL_RUN) + 1), ("conclusion", "success")]:
            modified = copy.deepcopy(run)
            modified[key] = wrong
            with self.subTest(kind="run", key=key), self.assertRaises(ValueError):
                probe._api_run(modified)
        execution = copy.deepcopy(ORIGINAL["execution"])
        execution["shared_editor_components"]["source"]["source_hashes"][next(iter(probe.SOURCES))] = "0" * 64
        with self.assertRaises(ValueError):
            probe.selection_contract(execution, ORIGINAL["discovery"])

    def test_restore_verifies_actual_regular_bytes_and_later_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, manifest = product_archive(root)
            destination = root / "restored"
            result = probe.extract_products(archive, destination, manifest)
            self.assertEqual(result["entries"], 2)
            probe.product_manifest_unchanged(destination, manifest)
            (destination / "Build/Products/AnytypeTests.xctest").write_bytes(b"changed executable")
            with self.assertRaises(ValueError):
                probe.product_manifest_unchanged(destination, manifest)

    def test_archive_changed_bytes_mode_missing_extra_or_duplicate_refused(self):
        def bytes_changed(members, manifest):
            member, data = members[1]
            members[1] = member, b"x" + data[1:]
        def mode_changed(members, manifest):
            members[1][0].mode = 0o644
        def missing(members, manifest):
            members.pop()
        def duplicate(members, manifest):
            members.append(copy.deepcopy(members[0]))
        def extra(members, manifest):
            entry = tarfile.TarInfo("Build/Products/Unreviewed")
            entry.mode = 0o644
            entry.size = 1
            members.append((entry, b"x"))
        for mutation in (bytes_changed, mode_changed, missing, duplicate, extra):
            with self.subTest(mutation=mutation.__name__), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive, manifest = product_archive(root, mutation=mutation)
                with self.assertRaises(ValueError):
                    probe.extract_products(archive, root / "restored", manifest)

    def test_product_links_and_escaping_paths_are_never_restored(self):
        def symlink(members, manifest):
            members[1][0].type = tarfile.SYMTYPE
            members[1][0].linkname = "/tmp/not-owned"
            members[1][0].size = 0
            members[1] = members[1][0], None
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, manifest = product_archive(root, mutation=symlink)
            with self.assertRaises(ValueError):
                probe.extract_products(archive, root / "restored", manifest)
        for value in ("../outside", "Build/Products/../../outside", "/Build/Products",
                      "Build\\Products\\outside", "Build/Products//outside", "Other/Products", None):
            with self.subTest(path=value), self.assertRaises(ValueError):
                probe._safe_product(value)

    def test_copied_descriptor_preserves_injection_host_bundle_and_original_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, initial = original_configuration(root)
            before = original.read_bytes()
            for variant in probe.variants(selection()):
                destination = root / (variant["name"] + ".xctestrun")
                binding = probe.copied_configuration(original, destination, variant)
                value = plistlib.loads(destination.read_bytes())
                target = value["TestConfigurations"][0]["TestTargets"][0]
                self.assertEqual(len(value["TestConfigurations"][0]["TestTargets"]), 1)
                for key in ("EnvironmentVariables", "TestingEnvironmentVariables", "CommandLineArguments",
                            "TestHostPath", "TestBundlePath"):
                    self.assertEqual(target[key], initial["TestConfigurations"][0]["TestTargets"][0][key])
                self.assertIn("AnotherSuite/previouslyDisabled()", target["SkipTestIdentifiers"])
                self.assertEqual(binding["copied_sha256"], probe.sha(destination))
                self.assertEqual(original.read_bytes(), before)
            with self.assertRaises(ValueError):
                probe.copied_configuration(original, original, probe.variants(selection())[0])
            outside = root / "different" / "configuration.xctestrun"
            with self.assertRaises(ValueError):
                probe.copied_configuration(original, outside, probe.variants(selection())[0])

    def test_every_bounded_xcode_variant_is_enumeration_only_with_no_build(self):
        value = selection()
        attempts = probe.variants(value)
        self.assertEqual(len(attempts), 4)
        parameterized = [item for item in value["selected"] if not item.endswith("()")]
        self.assertTrue(all(item in attempts[0]["include"] for item in parameterized))
        self.assertTrue(all(item in attempts[1]["cli"] for item in parameterized))
        self.assertTrue(all(item + "()" in attempts[3]["include"] for item in parameterized))
        self.assertEqual(attempts[2]["exclude"], value["excluded"])
        for attempt in attempts:
            command = probe.enumeration_command(Path("copied.xctestrun"),
                        "00000000-1111-4222-8333-444444444444", Path("enumeration.json"), Path("probe.xcresult"), attempt)
            self.assertEqual(command[:2], ["xcodebuild", "test-without-building"])
            self.assertEqual(command.count("-enumerate-tests"), 1)
            self.assertIn("-test-enumeration-output-path", command)
            self.assertNotIn("test", command)
            self.assertNotIn("build", command)
            self.assertNotIn("build-for-testing", command)
            self.assertNotIn("-scheme", command)
            self.assertEqual(command.count("-only-testing"), len(attempt["cli"]))


if __name__ == "__main__":
    unittest.main()
