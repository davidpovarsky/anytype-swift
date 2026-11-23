import json
from pathlib import Path
import plistlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_original_ui_timeline as subject


def sample_log(scope):
    case = subject.CASES[scope]
    method = case["method"]
    action = (case["action_prefix"] if scope == "hanlin"
              else case["action_prefix"] + 'source" Button for 1.1 seconds, drag to target')
    return "\n".join([
        f"Test Case '-[Module.NativeLaunchTests {method}]' started.",
        f'    t = 0.00s Start Test at {case["start"]}',
        '    t = 40.00s Tap "any-native-workspace-setup" Button',
        f'    t = {case["action_seconds"]:.2f}s {action}',
        f'    t = {case["failure_seconds"]:.2f}s Capturing element debug description',
        f'NativeLaunchTests.swift:{case["failure_line"]}: error: -[Module.NativeLaunchTests {method}] : failed',
        f"Test Case '-[Module.NativeLaunchTests {method}]' failed ({case['failure_seconds'] + 2:.3f} seconds).",
    ])


class OriginalUITimelineExportTests(unittest.TestCase):
    def test_both_case_frames_are_bound_to_original_post_onboarding_actions(self):
        for scope, case in subject.CASES.items():
            with self.subTest(scope=scope):
                result = subject.timeline(sample_log(scope), scope, case)
                self.assertEqual(len(result["frames"]), 2)
                for frame in result["frames"]:
                    self.assertGreater(frame["seconds"], result["min_seconds"])
                    self.assertLess(frame["seconds"], result["max_seconds"])
                    self.assertGreater(frame["seconds"], result["setup_seconds"] + 60)

    def test_refuses_missing_setup_changed_clock_or_changed_action(self):
        scope = "hanlin"
        case = subject.CASES[scope]
        good = sample_log(scope)
        bad = [
            good.replace('Tap "any-native-workspace-setup" Button', "Unproven setup"),
            good.replace(case["start"], "2026-11-23 00:49:18.784"),
            good.replace("150.89s", "140.89s"),
            good.replace("40.00s", "149.00s"),
        ]
        for log in bad:
            with self.subTest(log_kind=bad.index(log)):
                with self.assertRaises(ValueError):
                    subject.timeline(log, scope, case)

    def test_switch_sanitizer_discards_phrase_labels_and_ancestor_tree(self):
        secret = "fixture-private-recovery-text-never-publish"
        source = (
            f"StaticText, {{0, 0}}, label: '{secret}'\n"
            f"  Switch, 0xabc, {{{{20.0, 297.5}}, {{716.0, 52.0}}}}, label: '{secret}', value: 0\n"
            f"    Switch, 0xdef, {{{{40.0, 309.5}}, {{63.0, 28.0}}}}, value: 0\n"
            f"Path to element: Application, label: '{secret}'\n"
        ).encode()
        result = subject.sanitize_switches(source)
        self.assertEqual([r["value"] for r in result["switches"]], [0, 0])
        self.assertEqual(result["switches"][1]["frame"], [40, 309.5, 63, 28])
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn("0xabc", json.dumps(result))

    def test_tap_sanitizer_keeps_numeric_points_and_omits_arbitrary_text(self):
        secret = "fixture-private-recovery-text-never-publish"
        archive = {"$version": 100000, "$objects": [
            {"point": "{71.5, 323.5}", "offset": 0.012, "label": secret,
             "data": secret.encode(), "reference": plistlib.UID(1)}
        ]}
        result = subject.sanitize_event(plistlib.dumps(archive, fmt=plistlib.FMT_BINARY))
        self.assertEqual(result["point_literals"][0]["point"], "{71.5, 323.5}")
        self.assertNotIn(secret, json.dumps(result))

    def test_unrecognized_backup_data_fails_without_emitting_raw_content(self):
        with self.assertRaises(ValueError):
            subject.sanitize_switches(b"StaticText, label: 'private phrase'")
        with self.assertRaises(plistlib.InvalidFileException):
            subject.sanitize_event(b"private phrase")


if __name__ == "__main__":
    unittest.main()
