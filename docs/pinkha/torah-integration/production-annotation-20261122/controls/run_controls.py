"""Run the new pure annotation recovery controls against actual repository files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

SOURCES = [
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAnnotationNativeIdentity.swift",
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAnnotationCreateRecovery.swift",
    "docs/pinkha/torah-integration/production-annotation-20261122/controls/AnnotationRecoveryControls.swift",
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--swiftc", default=shutil.which("swiftc"))
    args = parser.parse_args()
    if not args.swiftc:
        parser.error("An actual installed Swift compiler is required")
    root, output = args.root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sources = [root / relative for relative in SOURCES]
    records = [
        {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
        for relative, path in zip(SOURCES, sources)
    ]
    binary = output / ("AnnotationRecoveryControls.exe" if os.name == "nt" else "AnnotationRecoveryControls")
    command = [str(args.swiftc), "-swift-version", "6", "-parse-as-library", *map(str, sources), "-o", str(binary)]
    started = time.monotonic()
    compile_result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=90)
    (output / "compile.stdout.log").write_text(compile_result.stdout, encoding="utf-8")
    (output / "compile.stderr.log").write_text(compile_result.stderr, encoding="utf-8")
    report = {
        "schema": 1,
        "scope": "Pure policy over explicit observations, no native engine, Apple module, RPC, database or ACK",
        "inputs": records, "native_tests": 0,
        "compile": {"command": command, "exit_code": compile_result.returncode,
                    "elapsed_seconds": time.monotonic() - started},
    }
    if compile_result.returncode == 0:
        environment = os.environ.copy()
        environment["PATH"] = str(Path(args.swiftc).resolve().parent) + os.pathsep + environment.get("PATH", "")
        started = time.monotonic()
        result = subprocess.run([str(binary)], capture_output=True, text=True, encoding="utf-8",
                                env=environment, timeout=30)
        (output / "run.stdout.log").write_text(result.stdout, encoding="utf-8")
        (output / "run.stderr.log").write_text(result.stderr, encoding="utf-8")
        report["run"] = {"command": [str(binary)], "exit_code": result.returncode,
                         "elapsed_seconds": time.monotonic() - started}
        if result.returncode == 0:
            report["result"] = json.loads(result.stdout)
    for record, path in zip(records, sources):
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise RuntimeError("Source changed during controls: " + record["path"])
    (output / "RESULT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("run", {}).get("exit_code") == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
