#!/usr/bin/env python3
"""Prepare the reviewed musl closure, then run T2 registry adapter tests only."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

GENPROTO_PATH = "google.golang.org/genproto"
GENPROTO_VERSION = "v0.0.0-20241021214115-324edc3d5d38"
GENPROTO_SUM = "h1:Q3nlH8iSQSRUwOskjbcSMcF2jiYMNiQYZ0c2KEJLKKU="
GENPROTO_MOD_SUM = "h1:xBI+tzfqGGN2JBeSebfKXFSdBpWVQ7sLW40PTupVRm4="
TANTIVY_SHA = "88b34e006707bfec2d29e8b26405f67cbb975d06fd4ea164da856d0084aaabbc"
IMAGE = "golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heart-source", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args()
    control = Path(__file__).resolve().parents[2]
    heart, work, evidence = args.heart_source.resolve(), args.work.resolve(), args.evidence.resolve()
    work.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "NOT_RUN_PREFLIGHT", "image_expected": IMAGE,
               "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
               "app_sha_expected": args.expected_app_sha, "commands": []}
    def run(command, name, env):
        receipt["commands"].append({"name": name, "argv": list(map(str, command))})
        with (evidence / (name + ".log")).open("x", encoding="utf-8") as log:
            result = subprocess.run(command, cwd=heart, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        if result.returncode:
            raise RuntimeError(name + " failed; retained log contains the exact error")
    try:
        helper_path = control / "Tools/PinkhaNativeDerived/build_custom_heart.py"
        spec = importlib.util.spec_from_file_location("t2_pinned_native_helper", helper_path)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        native = helper.fetch_tantivy(heart, "linux-amd64-musl")
        if native["archive_sha256"] != TANTIVY_SHA:
            raise ValueError("Tantivy differs from pinned d984 dependency")
        receipt["tantivy"] = native
        gowork = work / "go.work"
        gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + GENPROTO_PATH + " => "
                          + GENPROTO_PATH + " " + GENPROTO_VERSION + "\n", encoding="utf-8")
        env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1", GOMAXPROCS="2",
                   GOMEMLIMIT="2048MiB", GOFLAGS="-mod=readonly", CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
        receipt["gowork"] = gowork.read_text()
        run(["go", "mod", "download"], "pinned-module-download", env)
        env["GOPROXY"] = "off"
        run(["go", "list", "-m", "-json", GENPROTO_PATH], "genproto-selection", env)
        selected = json.loads((evidence / "genproto-selection.log").read_text())
        effective = selected.get("Replace", selected)
        if (selected.get("Path") != GENPROTO_PATH or effective.get("Path") != GENPROTO_PATH
                or effective.get("Version") != GENPROTO_VERSION or effective.get("Sum") != GENPROTO_SUM
                or effective.get("GoModSum") != GENPROTO_MOD_SUM):
            raise ValueError("resolved genproto differs from reviewed version/checksums")
        receipt["genproto"] = effective
        receipt["status"] = "PASS_DEPENDENCY_PREFLIGHT"
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("run_native_operations.py")),
                                 "--heart-source", str(heart), "--evidence", str(evidence),
                                 "--expected-app-sha", args.expected_app_sha, "--suite", "registration"],
                                cwd=control, env=env, timeout=2400)
        receipt["runner_returncode"] = result.returncode
        return result.returncode
    except Exception as exc:
        receipt["status"] = "NOT_RUN_PREFLIGHT_FAILED" if "runner_returncode" not in receipt else "FAIL"
        receipt["error"] = type(exc).__name__ + ": " + str(exc)
        print(receipt["error"], file=sys.stderr)
        return 1
    finally:
        (evidence / "dependency-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
