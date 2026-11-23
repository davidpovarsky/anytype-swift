"""One new offline basename-plan control; no simulator or product execution."""
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest import mock

import sdk06_basename_enumeration_probe as candidate


class BasenameProbeControls(unittest.TestCase):
    def test_fixed_original26_plan_changes_only_three_unique_exclusions_and_remains_enumeration_only(self):
        plan, originals = candidate._fixed_inputs()
        selection = json.loads(originals["receipt.json"])["selection_contract"]
        variants = candidate.fixed_candidates(selection)
        self.assertEqual(len(variants), 1)
        variant = variants[0]
        self.assertEqual(variant["include"], variant["cli"])
        self.assertEqual(variant["exclude"], variant["cli_skip"])
        self.assertEqual(sum(a != b for a, b in zip(selection["excluded"], variant["exclude"])), 3)
        self.assertEqual(len(variant["exclude"]), 7)
        self.assertEqual({a for a, b in zip(selection["excluded"], variant["exclude"]) if a != b},
                         set(plan["replacements"]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.xctestrun"
            original.write_bytes(originals["original.xctestrun"])
            destination = root / "candidate.xctestrun"
            binding = candidate.copied_configuration(original, destination, variant)
            self.assertEqual(binding["original_sha256"], candidate.XCTESTRUN_SHA)
            self.assertEqual(binding["skip"],
                             [item.removeprefix("AnytypeTests/") for item in variant["exclude"]])
            target = plistlib.loads(destination.read_bytes())["TestConfigurations"][0]["TestTargets"][0]
            source_target = next(value for value in
                                 plistlib.loads(original.read_bytes())["TestConfigurations"][0]["TestTargets"]
                                 if value["BlueprintName"] == "AnytypeTests")
            self.assertEqual({k: v for k, v in target.items()
                              if k not in {"OnlyTestIdentifiers", "SkipTestIdentifiers"}},
                             {k: v for k, v in source_target.items()
                              if k not in {"OnlyTestIdentifiers", "SkipTestIdentifiers"}})
            argv = candidate.enumeration_command(destination, "11111111-1111-4111-8111-111111111111",
                                                  root / "result.json", root / "result.xcresult", variant)
            self.assertEqual(argv.count("-enumerate-tests"), 1)
            self.assertNotIn("build-for-testing", argv)
            self.assertEqual([arg.removeprefix("-skip-testing:") for arg in argv
                              if arg.startswith("-skip-testing:")], variant["exclude"])
            self.assertEqual([arg.removeprefix("-only-testing:") for arg in argv
                              if arg.startswith("-only-testing:")], variant["include"])
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), candidate.XCTESTRUN_SHA)
        # Actual26 remains a failure; this fixture never manufactures a passing
        # current enumeration or a usable admission.
        with self.assertRaisesRegex(ValueError, "exactly the requested23"):
            candidate.qualify_enumeration(
                json.loads(originals["suites-minus-seven-cli.enumeration.json"]), selection)
        changed = copy.deepcopy(plan)
        signature = next(iter(changed["replacements"]))
        changed["replacements"][signature] += "wrong"
        with self.assertRaisesRegex(ValueError, "Exactly three"):
            candidate._reviewed_variant(selection, changed, originals)
        replay = dict(originals)
        receipt = json.loads(replay["receipt.json"])
        receipt["run_attempt"] = "2"
        replay["receipt.json"] = json.dumps(receipt).encode()
        with self.assertRaisesRegex(ValueError, "lineage"):
            candidate._reviewed_variant(selection, plan, replay)
        changed_selection = copy.deepcopy(selection)
        changed_selection["selected"][0] = selection["excluded"][0]
        with self.assertRaisesRegex(ValueError, "frozen contract"):
            candidate._reviewed_variant(changed_selection, plan, originals)
        collision = dict(originals)
        payload = json.loads(collision["suites-minus-seven-cli.enumeration.json"])
        basename = next(iter(plan["replacements"].values()))
        payload["values"][0]["disabledTests"][0]["identifier"] = basename + "Unexpected()"
        collision["suites-minus-seven-cli.enumeration.json"] = json.dumps(payload).encode()
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            candidate._reviewed_variant(selection, plan, collision)
        # The running entrypoint, fixed plan, invoking workflow and every original
        # read at runtime participate in the same before/after integrity map.
        app = Path(candidate.__file__).resolve().parents[2]
        head = candidate.subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"], text=True).strip()
        hashes = candidate.control_sources(app, head)
        self.assertTrue(set(candidate.EXTRA_INTEGRITY_PATHS) <= set(hashes))
        with mock.patch.object(candidate, "sha", side_effect=lambda path:
                               "0" * 64 if str(path).endswith("sdk06-basename-probe-plan.json")
                               else candidate.probe.sha(path)):
            with self.assertRaisesRegex(ValueError, "clean checkout"):
                candidate.control_sources(app, head)


if __name__ == "__main__":
    unittest.main()
