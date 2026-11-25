"""Keep this completed coherent run outside the next checkout's cleanup."""
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone


def require(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    require(platform.system() == "Darwin", "Retention requires the qualified Mac runner")
    app = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    run_id, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    require(re.fullmatch(r"[1-9][0-9]*", run_id) and re.fullmatch(r"[1-9][0-9]*", attempt),
            "Invalid original run identity")
    require(os.environ.get("UI27_ACCEPTANCE_LANE") == "coherent-heart-release",
            "Only the completed coherent run is admitted")
    evidence = app / "build/ui27-evidence"
    require(evidence.is_dir() and not evidence.is_symlink(), "Original run evidence is missing")
    preflight = json.loads((evidence / "preflight/preflight.json").read_text())
    require(preflight.get("run_id") == run_id and preflight.get("source_sha") == os.environ["GITHUB_SHA"],
            "Retention source/run identity differs")
    # The same original cleanup audit gates both compilation caching and retention.
    subprocess.run([sys.executable, "-B", str(app / "Tools/PinkhaSimulatorGate/coherent_heart_release.py"),
                    "--check-cache-ready", str(evidence)], cwd=app, check=True)
    names = ("ui27-derived", "ui27-derived-ui", "ui27-evidence",
             "ui27-heart-" + run_id + "-" + attempt)
    sources = [app / "build" / name for name in names]
    sources = [source for source in sources if source.exists() or source.is_symlink()]
    require(all(source.is_dir() and not source.is_symlink()
                and source.resolve().parent == app / "build" for source in sources),
            "Retention path is not an original run-owned directory")
    live = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True, check=True).stdout
    require(not any(str(source) in line for source in sources for line in live.splitlines()),
            "An active process still references this run's build path")
    root = Path("/Users/m1/builds/_retained-anytype")
    require(root.is_dir() and root.resolve() == root, "Unexpected retention root")
    target = root / (run_id + "-" + attempt)
    require(not target.exists() and not target.is_symlink(), "Refuse to overwrite retained run")
    (target / "build").mkdir(parents=True)
    journal = dict(run_id=run_id, run_attempt=attempt, source_sha=os.environ["GITHUB_SHA"],
                   status="RETAINING", moved=[], acceptance_claim=False,
                   started_at=datetime.now(timezone.utc).isoformat())

    def save():
        (target / "retention.json").write_text(json.dumps(journal, indent=2, sort_keys=True) + "\n")

    save()
    try:
        for source in sources:
            destination = target / "build" / source.name
            source.rename(destination)
            journal["moved"].append(dict(original=str(source), retained=str(destination)))
            save()
        journal["status"] = "ORIGINAL_COMPLETED_PRODUCTS_RETAINED"
    except BaseException as error:
        journal.update(status="PARTIAL_RETENTION", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        journal["finished_at"] = datetime.now(timezone.utc).isoformat()
        save()
    print(json.dumps(journal, sort_keys=True))


if __name__ == "__main__":
    main()
