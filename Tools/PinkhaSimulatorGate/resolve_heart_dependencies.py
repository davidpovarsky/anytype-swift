"""Resolve the two observed missing Heart dependency pins without compiling."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
EXPECTED_ADDITIONS = {"swift-markdown", "swift-cmark"}

def execute(app, evidence):
    if platform.system() != "Darwin":
        raise RuntimeError("Xcode dependency resolution requires an Apple host")
    evidence.mkdir(parents=True, exist_ok=True)
    def git(*args):
        return subprocess.check_output(["git", "-C", str(app), *args], text=True).strip()
    source = git("rev-parse", "HEAD")
    if source != os.environ["GITHUB_SHA"] or git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Exact clean published source required")
    before = (app / LOCK).read_bytes()
    (evidence / "original-Package.resolved").write_bytes(before)
    command = ["xcodebuild", "-resolvePackageDependencies", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
               "-clonedSourcePackagesDirPath", str(evidence / "SourcePackages")]
    result = {"status": "RUNNING", "source_sha": source, "run_id": os.environ["GITHUB_RUN_ID"],
              "command": command, "app_builds": 0, "test_executions": 0,
              "started_at": datetime.now(timezone.utc).isoformat()}
    try:
        with (evidence / "resolve.log").open("w", encoding="utf8") as log:
            done = subprocess.run(command, cwd=app, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        result["return_code"] = done.returncode
        after = (app / LOCK).read_bytes()
        (evidence / "generated-Package.resolved").write_bytes(after)
        old = {p["identity"]: p for p in json.loads(before)["pins"]}
        new = {p["identity"]: p for p in json.loads(after)["pins"]}
        additions = sorted(set(new) - set(old))
        removals = sorted(set(old) - set(new))
        state_changes = [name for name in old.keys() & new.keys() if old[name]["state"] != new[name]["state"]]
        result.update(added_pins=[new[name] for name in additions], removed_pins=removals,
                      existing_state_changes=state_changes, original_sha256=hashlib.sha256(before).hexdigest(),
                      generated_sha256=hashlib.sha256(after).hexdigest(),
                      tracked_status=git("status", "--porcelain", "--untracked-files=no"))
        if (done.returncode != 0 or removals or state_changes or not EXPECTED_ADDITIONS.issubset(new)
                or set(additions) not in (EXPECTED_ADDITIONS, set())):
            raise RuntimeError("Resolution differs from the observed two-pin addition; review exact artifact")
        if result["tracked_status"] != ("M " + LOCK if before != after else ""):
            raise RuntimeError("Resolution changed unexpected tracked source")
        result["status"] = "GENERATED_TWO_MISSING_PINS_FOR_REVIEW" if additions else "PUBLISHED_LOCK_UNCHANGED"
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if (app / LOCK).is_file():
            (evidence / "generated-Package.resolved").write_bytes((app / LOCK).read_bytes())
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        (evidence / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf8")
        print(json.dumps({key: result[key] for key in ["status", "source_sha", "app_builds", "test_executions"]}))

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--app",type=Path,required=True)
    p.add_argument("--evidence",type=Path,required=True)
    a=p.parse_args()
    execute(a.app.resolve(),a.evidence.resolve())
