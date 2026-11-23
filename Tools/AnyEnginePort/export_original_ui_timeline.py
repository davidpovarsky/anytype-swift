#!/usr/bin/env python3
"""Extract only post-onboarding stills and numeric backup-control evidence."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import math
import plistlib
import re
import subprocess
import time
import zipfile

import export_original_ui_failures as original

FIRST_EXPORT = {
    "run_id": 45096076370, "source": "59d87891d7235429187599bd02d7ed8178ea8c22",
    "artifact_id": 14783341999,
    "archive_sha256": "144fc822cd08b09b76b01ab0f3aee7b142a13e9e4ede021dda13e685ec9d08eb",
}
CASES = {
    "hanlin": {
        "method": "testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen",
        "recording": "Screen Recording 2026-11-23 at 12.52.18 AM.mp4",
        "bytes": 13292178, "start": "2026-11-23 00:52:18.784",
        "action_prefix": 'Tap "pinkha.hanlin.connect" Button',
        "action_seconds": 150.89, "failure_seconds": 182.38, "failure_line": 1014,
    },
    "hierarchy-drag": {
        "method": "testHierarchyDragIntoFolderPersistsAfterColdReopen",
        "recording": "Screen Recording 2026-11-23 at 12.55.40 AM.mp4",
        "bytes": 13647217, "start": "2026-11-23 00:55:40.068",
        "action_prefix": 'Press "any-native-hierarchy-row-',
        "action_seconds": 112.08, "failure_seconds": 160.96, "failure_line": 466,
    },
}
BACKUP_METHOD = "testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType"
BACKUP_EVENT = "Synthesized Event 2026-11-23 at 12.58.46 AM"
EVENT = re.compile(r"^\s*t\s*=\s*(\d+(?:\.\d+)?)s\s+(.*)$")
FRAME = re.compile(r"\{\{(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\},\s*\{(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\}\}")
SAFE_KEY = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$.]{0,79}$")
POINT = re.compile(r"^[\s{}(),.0-9eE+\-]{3,160}$")


def require(value, reason):
    original.require(value, reason)


def timeline(log, scope, case):
    """Bind media offsets to the exact original XCTest action and failure."""
    lines = log.splitlines()
    method = case["method"]
    starts = [i for i, s in enumerate(lines) if s.startswith("Test Case ")
              and method in s and s.endswith("started.")]
    require(len(starts) == 1, "Expected one exact original method start")
    begin = starts[0]
    ends = [i for i, s in enumerate(lines[begin + 1:], begin + 1)
            if s.startswith("Test Case ") and method in s and " failed (" in s]
    require(len(ends) == 1, "Expected one terminal failed original method")
    end = ends[0]
    segment = lines[begin:end + 1]
    start_lines = [s for s in segment if "Start Test at " in s]
    require(len(start_lines) == 1, "Missing unique original start timestamp")
    start_text = start_lines[0].split("Start Test at ", 1)[1]
    require(start_text == case["start"], "Original start timestamp differs")
    start = datetime.strptime(start_text, "%Y-%m-%d %H:%M:%S.%f")
    recording_start = datetime.strptime(case["recording"],
                                       "Screen Recording %Y-%m-%d at %I.%M.%S %p.mp4")
    delta = (start - recording_start).total_seconds()
    require(0 <= delta < 1.1, "Recording clock is not aligned with test start")
    events = []
    failure = None
    last_time = None
    for i, line in enumerate(segment, begin + 1):
        match = EVENT.match(line)
        if match:
            last_time = float(match[1])
            events.append((last_time, match[2], i))
        if f"NativeLaunchTests.swift:{case['failure_line']}: error:" in line and method in line:
            require(failure is None and last_time is not None, "Ambiguous original failure")
            failure = (last_time, i)
    setup = [e for e in events if e[1].startswith('Tap "any-native-workspace-setup" Button')]
    action = [e for e in events if e[1].startswith(case["action_prefix"])
              and (scope != "hierarchy-drag" or "drag to " in e[1])]
    require(len(setup) == 1 and len(action) == 1 and failure is not None,
            "Missing exact post-onboarding action boundary")
    require(abs(action[0][0] - case["action_seconds"]) < 0.001
            and abs(failure[0] - case["failure_seconds"]) < 0.001,
            "Original action/failure timings differ")
    require(setup[0][0] + 15 < action[0][0] and action[0][0] > 100
            and action[0][0] + 8 < failure[0], "No safe post-onboarding frame window")
    duration_match = re.search(r" failed \((\d+(?:\.\d+)?) seconds\)\.", lines[end])
    require(duration_match is not None, "Missing original test duration")
    duration = float(duration_match[1])
    require(failure[0] <= duration <= failure[0] + 5, "Unexpected teardown interval")
    frames = [
        {"label": "post-action", "seconds": round(action[0][0] + 5 + delta, 3)},
        {"label": "near-failure", "seconds": round(failure[0] - 2 + delta, 3)},
    ]
    return {
        "scope": scope, "method": method, "test_start": start_text,
        "recording_name": case["recording"], "recording_clock_precision_seconds": 1,
        "test_start_after_recording_named_start_seconds": delta,
        "setup_seconds": setup[0][0], "action_seconds": action[0][0],
        "failure_seconds": failure[0], "test_duration_seconds": duration,
        "source_log_lines": {"method_start": begin + 1, "setup": setup[0][2],
                             "action": action[0][2], "failure": failure[1], "terminal": end + 1},
        "min_seconds": round(action[0][0] + 2 + delta, 3),
        "max_seconds": round(failure[0] + delta, 3),
        "expected_duration_seconds": round(duration + delta, 3),
        "frames": frames,
        "alignment": "Original recording name (whole-second precision) plus original XCTest log; frame window is more than 100 seconds after test start.",
    }


def sanitize_switches(data):
    """Retain only switch rectangles/value; never labels, ancestors, or text."""
    text = data.decode("utf-8")
    require(len(data) <= 20000, "Unexpected switch debug attachment size")
    rows = []
    for line in text.splitlines():
        if not re.search(r"(?:^|\s|\u2192)Switch,", line):
            continue
        frame = FRAME.search(line)
        if not frame:
            continue
        value = re.search(r"\bvalue:\s*['\"]?([01])(?:['\"]?(?:,|\s|$))", line)
        if not value:
            continue
        numbers = [float(x) for x in frame.groups()]
        require(all(math.isfinite(v) for v in numbers), "Nonfinite switch geometry")
        rows.append({"frame": numbers, "value": int(value[1]),
                     "disabled": bool(re.search(r"\bDisabled\b", line))})
    require(1 <= len(rows) <= 10, "No bounded switch-only geometry/value evidence")
    return {"switches": rows, "labels_and_ancestor_text_omitted": True}


def sanitize_event(data):
    """Extract numeric leaves and point literals from a synthesized-event plist."""
    require(len(data) <= 20000, "Unexpected tap event attachment size")
    obj = plistlib.loads(data)
    numbers, points = [], []
    visited = 0

    def visit(value, path, depth):
        nonlocal visited
        visited += 1
        require(depth <= 20 and visited <= 10000, "Event archive traversal bound exceeded")
        if isinstance(value, dict):
            for index, (key, child) in enumerate(value.items()):
                safe_key = key if isinstance(key, str) and SAFE_KEY.fullmatch(key) else f"field{index}"
                visit(child, path + [safe_key], depth + 1)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + [index], depth + 1)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            require(math.isfinite(value), "Nonfinite synthesized event number")
            numbers.append({"path": path, "value": value})
        elif isinstance(value, str) and "{" in value and POINT.fullmatch(value):
            points.append({"path": path, "point": value})

    visit(obj, [], 0)
    require(numbers or points, "Synthesized event contains no decodable geometry")
    return {"numeric_fields": numbers, "point_literals": points,
            "arbitrary_strings_and_binary_payloads_omitted": True,
            "scope": "Numeric event evidence only; not an assertion that the tap was delivered."}


def find_case(manifest, method):
    matches = [c for c in manifest
               if c.get("testIdentifier", "").removesuffix("()").endswith("/" + method)]
    require(len(matches) == 1, "Missing unique original attachment case")
    return matches[0]


def attachment_path(root, attachment):
    relative = original.safe(attachment["exportedFileName"])
    path = root.joinpath(*relative.parts)
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),
            "Unsafe original attachment path")
    return path


def error_summary(error):
    return {"type": type(error).__name__, "reason": str(error)[:500]}


def recorded_stage(outcomes, name, operation):
    """A failed owned item must not suppress independent admitted evidence."""
    try:
        value = operation()
        outcomes[name] = {"status": value.get("status", "PASS"), "result": value}
    except Exception as error:
        outcomes[name] = {"status": "FAIL", "error": error_summary(error)}
    return outcomes[name]


def run_renderer(command, private_root, scope, *, timeout=180):
    require(scope in CASES, "Unexpected renderer scope")
    private_root.mkdir(parents=True, exist_ok=True)
    stdout = private_root / (scope + ".stdout.log")
    stderr = private_root / (scope + ".stderr.log")
    record = {"argv": command, "timeout_seconds": timeout}
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            require(timeout > 0, "Original renderer deadline exhausted before this asset")
            process = subprocess.run(command, stdout=out, stderr=err, timeout=timeout)
            record["exit_code"] = process.returncode
        except Exception as error:
            record["error"] = error_summary(error)
            if isinstance(error, subprocess.TimeoutExpired):
                record["timeout_seconds"] = error.timeout
    record["private_streams"] = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": original.digest(path)}
        for name, path in (("stdout", stdout), ("stderr", stderr))
    }
    result = {"status": "FAIL", "process": record}
    try:
        require(stdout.stat().st_size <= 2 * 1024**2, "Renderer structured result exceeds bound")
        rendered = json.loads(stdout.read_text())
        require(isinstance(rendered, dict) and rendered.get("schema_version") == 2
                and rendered.get("scope") == scope
                and rendered.get("status") in ("PASS", "FAIL"), "Invalid typed renderer result")
        result["rendered"] = rendered
        if record.get("exit_code") == 0 and rendered["status"] == "PASS":
            result["status"] = "PASS"
    except Exception as error:
        result["structured_result_error"] = error_summary(error)
    # Complete process bytes remain separate from selected visual evidence.
    (private_root / (scope + ".streams.json")).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n")
    return result


def complete_evidence(outcomes):
    required = {*CASES, "backup-tap", "backup-switches"}
    if set(outcomes) != required or any(outcomes[k].get("status") != "PASS" for k in required):
        return False
    for scope in CASES:
        rendered = outcomes[scope].get("result", {}).get("rendered", {})
        frames = rendered.get("frames", [])
        if (rendered.get("scope") != scope or rendered.get("status") != "PASS"
                or len(frames) != 2
                or {x.get("label") for x in frames} != {"post-action", "near-failure"}
                or any(x.get("scope") != scope or x.get("status") != "PASS" for x in frames)):
            return False
    return True


def main():
    root = Path("build/original-any-ui-timeline-export").resolve()
    output = root / "selected"
    output.mkdir(parents=True, exist_ok=False)
    receipt = {
        "status": "NOT_RUN", "source_run_id": original.RUN, "source_commit": original.SOURCE,
        "archive_sha256": original.ARCHIVE_SHA, "prior_export": FIRST_EXPORT,
        "product_tests_executed": 0, "no_product_execution": True, "selected": [],
        "outcomes": {}, "commands": [], "renderer_total_budget_seconds": 180,
        "scope": "Original post-onboarding stills and sanitized numeric backup evidence; every required item must pass.",
    }

    def publish_metadata(name, value):
        path = output / name
        require(path.suffix == ".json" and path.parent == output, "Unsafe metadata output")
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        return path

    try:
        original.main()
        original_root = Path("build/original-any-ui-export").resolve()
        receipt["attachment_export_receipt_sha256"] = original.digest(original_root / "selected/receipt.json")
        receipt["unchanged_first_exporter_sha256"] = original.digest(Path(original.__file__))
        with zipfile.ZipFile(original_root / "original.zip") as zipped:
            log_bytes = zipped.read("native-ui-continuation.log")
        require(len(log_bytes) <= 1024**2, "Unexpected original UI log size")
        receipt["source_log_sha256"] = hashlib.sha256(log_bytes).hexdigest()
        log = log_bytes.decode("utf-8")
        exported = original_root / "native-ui-continuation.xcresult-attachments"
        manifest = json.loads((exported / "manifest.json").read_text(encoding="utf-8-sig"))
        render_deadline = None

        def render_case(scope, config):
            nonlocal render_deadline
            case = find_case(manifest, config["method"])
            matches = [a for a in case["attachments"]
                       if a.get("suggestedHumanReadableName") == config["recording"]]
            require(len(matches) == 1, "Missing unique pinned original recording")
            video = attachment_path(exported, matches[0])
            require(video.suffix.lower() == ".mp4" and video.stat().st_size == config["bytes"],
                    "Original recording type/size differs")
            plan = timeline(log, scope, config)
            plan["recording_sha256"] = original.digest(video)
            plan["recording_bytes"] = video.stat().st_size
            publish_metadata("original-timeline-" + scope + ".json", plan)
            private_plan = {**plan, "video_path": str(video)}
            render_plan = root / ("private-render-plan-" + scope + ".json")
            render_plan.write_text(json.dumps({"cases": [private_plan]}))
            command = ["xcrun", "swift", "Tools/AnyEnginePort/extract_original_ui_stills.swift",
                       str(render_plan), str(output / "frames")]
            if render_deadline is None:
                render_deadline = time.monotonic() + 180
            result = run_renderer(command, root / "private-process", scope,
                                  timeout=max(0, render_deadline - time.monotonic()))
            receipt["commands"].append(result["process"])
            return result

        for scope, config in CASES.items():
            recorded_stage(receipt["outcomes"], scope, lambda s=scope, c=config: render_case(s, c))

        def backup_tap():
            backup = find_case(manifest, BACKUP_METHOD)
            taps = [a for a in backup["attachments"]
                    if a.get("suggestedHumanReadableName") == BACKUP_EVENT]
            require(len(taps) == 1, "Missing exact original backup tap")
            tap = attachment_path(exported, taps[0])
            require(tap.stat().st_size == 1903, "Original backup tap size differs")
            value = sanitize_event(tap.read_bytes())
            value.update(source_name=BACKUP_EVENT, source_sha256=original.digest(tap))
            publish_metadata("backup-tap-numeric-only.json", value)
            return {"status": "PASS", "source_sha256": original.digest(tap)}

        def backup_switches():
            backup = find_case(manifest, BACKUP_METHOD)
            descriptions = [a for a in backup["attachments"]
                            if a.get("suggestedHumanReadableName", "").startswith(
                                'Debug description for ' + chr(96) + '"0" Switch' + chr(96))]
            require(len(descriptions) == 5, "Unexpected original backup debug count")
            records = []
            for item in descriptions:
                observation = {"status": "FAIL"}
                try:
                    source = attachment_path(exported, item)
                    require(source.stat().st_size == 2504, "Original switch debug size differs")
                    value = sanitize_switches(source.read_bytes())
                    value["source_sha256"] = original.digest(source)
                    observation.update(status="PASS", sanitized=value)
                except Exception as error:
                    observation["error"] = error_summary(error)
                records.append(observation)
            publish_metadata("backup-switch-values-only.json", {
                "cases": records, "method": BACKUP_METHOD,
                "recovery_text_and_full_trees_not_published": True})
            return {"status": "PASS" if all(x["status"] == "PASS" for x in records) else "FAIL",
                    "attachment_count": len(records)}

        recorded_stage(receipt["outcomes"], "backup-tap", backup_tap)
        recorded_stage(receipt["outcomes"], "backup-switches", backup_switches)
        receipt.update(
            status="EXPORTED_ORIGINAL_TIMELINE_EVIDENCE_NOT_ACCEPTANCE"
                if complete_evidence(receipt["outcomes"]) else "FAIL",
            original_archive_verified=True, no_recordings_published=True,
            no_backup_screen_or_full_tree_published=True)
    except BaseException as error:
        receipt.update(status="FAIL", error=error_summary(error))
    finally:
        # Inventory safe independent results even when another required item failed.
        for path in sorted(output.rglob("*")):
            if not path.is_file():
                continue
            require(path.suffix in (".json", ".png"), "Refusing to publish recording or unfiltered attachment")
            require(path.stat().st_size <= 8 * 1024**2, "Selected output exceeded bound")
            receipt["selected"].append({"path": path.relative_to(output).as_posix(),
                                        "bytes": path.stat().st_size, "sha256": original.digest(path)})
        publish_metadata("receipt.json", receipt)
        print(json.dumps({k: receipt[k] for k in ("status", "scope", "product_tests_executed")}))
    return 0 if receipt["status"] == "EXPORTED_ORIGINAL_TIMELINE_EVIDENCE_NOT_ACCEPTANCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
