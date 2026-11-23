import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_original_ui_timeline as subject


def rendered(scope, status="PASS"):
    return {
        "schema_version": 2, "scope": scope, "status": status,
        "actual_recording_duration_seconds": 161.033333,
        "video_track_time_ranges": [{"start_seconds": 0,
                                    "duration_seconds": 161.88, "end_seconds": 161.88}],
        "frames": [{"scope": scope, "label": label, "status": "PASS"}
                   for label in ("post-action", "near-failure")],
    }


class OriginalUITimelineOutcomeTests(unittest.TestCase):
    def test_nonzero_renderer_preserves_complete_streams_and_first_typed_failure(self):
        first = "FIRST_AVFOUNDATION_DIAGNOSTIC\n"
        stderr = (first + "owned process detail\n" * 600).encode()
        payload = rendered("hanlin", "FAIL")
        payload["frames"][0].update(
            status="FAIL", actual_seconds=118.203333,
            error={"type": "EvidenceError", "reason": "Exact requested frame guard failed"})
        script = (
            "import json,sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(payload) + chr(10))})\n"
            f"sys.stderr.buffer.write({stderr!r})\n"
            "raise SystemExit(1)\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = subject.run_renderer([sys.executable, "-c", script], root, "hanlin")
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["rendered"], payload)
            self.assertEqual(result["process"]["exit_code"], 1)
            self.assertEqual((root / "hanlin.stderr.log").read_bytes(), stderr)
            self.assertTrue((root / "hanlin.stderr.log").read_text().startswith(first))
            self.assertGreater(result["process"]["private_streams"]["stderr"]["bytes"], 4000)
            self.assertEqual(result["process"]["private_streams"]["stderr"]["sha256"],
                             hashlib.sha256(stderr).hexdigest())
            self.assertEqual(json.loads((root / "hanlin.streams.json").read_text()),
                             result["process"])
            self.assertEqual(list(root.glob("*.png")), [])

    def test_invalid_or_timed_out_renderer_still_preserves_owned_process_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = "import sys;sys.stdout.write('not JSON');sys.stderr.write('original failure');sys.exit(3)"
            failed = subject.run_renderer([sys.executable, "-c", script], root / "invalid", "hanlin")
            self.assertEqual(failed["status"], "FAIL")
            self.assertEqual(failed["process"]["exit_code"], 3)
            self.assertEqual(failed["structured_result_error"]["type"], "JSONDecodeError")
            self.assertEqual((root / "invalid/hanlin.stdout.log").read_text(), "not JSON")
            self.assertEqual((root / "invalid/hanlin.stderr.log").read_text(), "original failure")

            # A real child flushes both streams before the unchanged subprocess
            # timeout kills and waits for it. There is no renderer retry.
            script = (
                "import sys,time\n"
                "sys.stdout.write('partial result');sys.stdout.flush()\n"
                "sys.stderr.write('FIRST_ERROR\\n');sys.stderr.flush()\n"
                "time.sleep(30)\n"
            )
            timed = subject.run_renderer([sys.executable, "-c", script], root / "timeout",
                                         "hierarchy-drag", timeout=0.3)
            self.assertEqual(timed["status"], "FAIL")
            self.assertEqual(timed["process"]["error"]["type"], "TimeoutExpired")
            # subprocess reports the actual remaining wait budget, which may
            # be slightly below the configured 0.3 seconds after process setup.
            self.assertGreater(timed["process"]["timeout_seconds"], 0)
            self.assertLessEqual(timed["process"]["timeout_seconds"], 0.3)
            self.assertNotIn("exit_code", timed["process"])
            self.assertEqual((root / "timeout/hierarchy-drag.stdout.log").read_text(), "partial result")
            self.assertEqual((root / "timeout/hierarchy-drag.stderr.log").read_text(), "FIRST_ERROR\n")

    def test_coordinator_keeps_second_asset_and_both_backup_outputs_after_first_asset_failure(self):
        def prepare_original():
            original = Path("build/original-any-ui-export").resolve()
            (original / "selected").mkdir(parents=True)
            (original / "selected/receipt.json").write_text('{"fixture":"pinned-export"}')
            with zipfile.ZipFile(original / "original.zip", "w") as archive:
                archive.writestr("native-ui-continuation.log", "isolated coordinator fixture")
            exported = original / "native-ui-continuation.xcresult-attachments"
            exported.mkdir()
            with (exported / "hierarchy.mp4").open("wb") as stream:
                stream.truncate(subject.CASES["hierarchy-drag"]["bytes"])
            (exported / "tap.plist").write_bytes(b"0" * 1903)
            switches = []
            for index in range(5):
                name = f"switch-{index}.txt"
                (exported / name).write_bytes(b"0" * 2504)
                switches.append({
                    "suggestedHumanReadableName": "Debug description for " + chr(96) + '"0" Switch' + chr(96),
                    "exportedFileName": name,
                })
            manifest = [
                {"testIdentifier": "Module/" + subject.CASES["hanlin"]["method"], "attachments": []},
                {"testIdentifier": "Module/" + subject.CASES["hierarchy-drag"]["method"],
                 "attachments": [{"suggestedHumanReadableName": subject.CASES["hierarchy-drag"]["recording"],
                                  "exportedFileName": "hierarchy.mp4"}]},
                {"testIdentifier": "Module/" + subject.BACKUP_METHOD,
                 "attachments": [{"suggestedHumanReadableName": subject.BACKUP_EVENT,
                                  "exportedFileName": "tap.plist"}, *switches]},
            ]
            (exported / "manifest.json").write_text(json.dumps(manifest))

        def fixture_renderer(command, private_root, scope, *, timeout):
            self.assertEqual(scope, "hierarchy-drag")
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 180)
            return {"status": "PASS", "rendered": rendered(scope), "process": {"fixture": True}}

        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with patch.object(subject.original, "main", prepare_original), \
                     patch.object(subject, "timeline", return_value={"scope": "hierarchy-drag"}), \
                     patch.object(subject, "run_renderer", side_effect=fixture_renderer) as renderer, \
                     patch.object(subject, "sanitize_event", return_value={"numeric_fields": [{"value": 71.5}]}), \
                     patch.object(subject, "sanitize_switches", return_value={"switches": [{"value": 0}]}), \
                     contextlib.redirect_stdout(io.StringIO()):
                    code = subject.main()
                receipt = json.loads(Path("build/original-any-ui-timeline-export/selected/receipt.json").read_text())
                self.assertEqual(code, 1)
                self.assertEqual(receipt["status"], "FAIL")
                self.assertEqual(receipt["outcomes"]["hanlin"]["status"], "FAIL")
                for name in ("hierarchy-drag", "backup-tap", "backup-switches"):
                    self.assertEqual(receipt["outcomes"][name]["status"], "PASS")
                self.assertEqual(renderer.call_count, 1)
                self.assertEqual({item["path"] for item in receipt["selected"]},
                                 {"original-timeline-hierarchy-drag.json",
                                  "backup-tap-numeric-only.json", "backup-switch-values-only.json"})
                self.assertEqual(receipt["product_tests_executed"], 0)
            finally:
                os.chdir(previous)

    def test_overall_success_requires_both_exact_frame_pairs_and_backup_outcomes(self):
        outcomes = {
            scope: {"status": "PASS", "result": {"rendered": rendered(scope)}}
            for scope in subject.CASES
        }
        outcomes.update({name: {"status": "PASS"} for name in ("backup-tap", "backup-switches")})
        self.assertTrue(subject.complete_evidence(outcomes))
        cases = []
        missing_asset = copy.deepcopy(outcomes)
        del missing_asset["hanlin"]
        cases.append(missing_asset)
        missing_frame = copy.deepcopy(outcomes)
        missing_frame["hanlin"]["result"]["rendered"]["frames"].pop()
        cases.append(missing_frame)
        rejected_frame = copy.deepcopy(outcomes)
        rejected_frame["hierarchy-drag"]["result"]["rendered"]["frames"][1]["status"] = "FAIL"
        cases.append(rejected_frame)
        duplicate_label = copy.deepcopy(outcomes)
        duplicate_label["hanlin"]["result"]["rendered"]["frames"][1]["label"] = "post-action"
        cases.append(duplicate_label)
        missing_backup = copy.deepcopy(outcomes)
        del missing_backup["backup-switches"]
        cases.append(missing_backup)
        failed_backup = copy.deepcopy(outcomes)
        failed_backup["backup-tap"]["status"] = "FAIL"
        cases.append(failed_backup)
        for case in cases:
            with self.subTest(index=cases.index(case)):
                self.assertFalse(subject.complete_evidence(case))


if __name__ == "__main__":
    unittest.main()
