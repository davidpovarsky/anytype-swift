"""One root-owned Foundation compile/run of the frozen property-modal packet."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from zipfile import ZipFile


ARCHIVE_SHA256 = "1d21d47b8cd407675265c87a82a2c6a32d1dee537b524eed6f10179ed7194514"
DEFAULT_COMPILER = r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--compiler", default=DEFAULT_COMPILER, type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve(strict=True)
    compiler = args.compiler.resolve(strict=True)
    output = args.output_dir.resolve()
    archive_bytes = archive.read_bytes()
    assert sha(archive_bytes) == ARCHIVE_SHA256, "frozen archive SHA256 mismatch"
    # An existing directory is never reused or removed. This prevents an
    # accidental duplicate compile/run from overwriting an earlier receipt.
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "inputs"
    inputs.mkdir()
    receipt = {"status": "ADMISSION", "archive_sha256": ARCHIVE_SHA256,
               "compiler": str(compiler), "prior_suites_rerun": False,
               "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "compiler_processes": 0, "execution_processes": 0, "dependency_builds": 0,
               "apple_typecheck": "NOT_RUN", "native_editor": "NOT_RUN"}
    try:
        with ZipFile(archive) as zipped:
            assert zipped.testzip() is None, "CRC failure"
            manifest_bytes = zipped.read("INPUTS.json")
            manifest = json.loads(manifest_bytes)
            expected = {row["name"] for row in manifest["files"]} | {
                "INPUTS.json", "PRODUCTION_REGIONS.json", "PRODUCTION_INPUTS.json", "README.md"
            }
            assert len(zipped.namelist()) == len(expected) and set(zipped.namelist()) == expected
            for name in sorted(expected):
                assert Path(name).name == name and name not in (".", "..")
                (inputs / name).write_bytes(zipped.read(name))
        for row in manifest["files"]:
            data = (inputs / row["name"]).read_bytes()
            assert row["name"].endswith(".swift") and sha(data) == row["sha256"]
            assert len(data) == row["bytes"]
        assert sha((inputs / "PRODUCTION_REGIONS.json").read_bytes()) == manifest["production_regions_sha256"]
        assert sha((inputs / "PRODUCTION_INPUTS.json").read_bytes()) == manifest["production_inputs_sha256"]
        receipt.update(status="INPUTS_VERIFIED", input_manifest_sha256=sha(manifest_bytes),
                       modal_patch_sha256=manifest["modal_patch_sha256"],
                       combined_patch_sha256=manifest["combined_patch_sha256"])
        executable = output / "property-modal-controls.exe"
        command = [str(compiler), "-swift-version", "5", "-strict-concurrency=complete",
                   "-parse-as-library", "-j", "1", "-whole-module-optimization", "-Onone"]
        command += [str(inputs / row["name"]) for row in manifest["files"]]
        command += ["-o", str(executable)]
        runtime = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
        assert runtime.is_dir(), "expected existing Swift runtime is unavailable"
        env = dict(os.environ)
        env["PATH"] = str(compiler.parent) + os.pathsep + str(runtime) + os.pathsep + env.get("PATH", "")
        receipt["runtime_directory"] = str(runtime)

        def invoke(name: str, argv: list[str], timeout: int) -> dict:
            log = output / (name + ".log")
            started = time.monotonic()
            timed_out = False
            code = None
            with log.open("wb") as stream:
                try:
                    result = subprocess.run(argv, cwd=output, env=env, stdout=stream,
                                            stderr=subprocess.STDOUT, timeout=timeout, check=False)
                    code = result.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
            result = {"argv": argv, "cwd": str(output), "timeout_seconds": timeout,
                      "timed_out": timed_out, "returncode": code,
                      "elapsed_seconds": round(time.monotonic() - started, 3),
                      "stdout_sha256": sha(log.read_bytes()), "stdout_path": log.name}
            record(output / (name + ".command.json"), result)
            assert not timed_out and code == 0, name + " did not succeed; retained original log"
            return result

        receipt["status"] = "COMPILING"
        receipt["compiler_processes"] += 1
        record(output / "CONTROL_RUN_RECEIPT.json", receipt)
        receipt["compile"] = invoke("compile", command, 180)
        receipt["executable_sha256"] = sha(executable.read_bytes())
        receipt["status"] = "RUNNING"
        receipt["execution_processes"] += 1
        record(output / "CONTROL_RUN_RECEIPT.json", receipt)
        receipt["run"] = invoke("run", [str(executable)], 45)
        report = json.loads((output / "run.log").read_text(encoding="utf-8"))
        assert report["status"] == "PASS_NEW_PORTABLE_PROPERTY_MODAL_CONTROLS"
        assert report["passed"] == report["expected"] == manifest["expected_control_ids"]
        assert report["executed"] == manifest["expected_controls"]
        assert report["failed"] == report["skipped"] == 0
        assert report["modal_patch_sha256"] == manifest["modal_patch_sha256"]
        assert report["combined_patch_sha256"] == manifest["combined_patch_sha256"]
        assert report["native_editor"] == report["canonical_network_read"] == "NOT_RUN"
        assert report["prior_suites_rerun"] is False
        for row in manifest["files"]:
            data = (inputs / row["name"]).read_bytes()
            assert sha(data) == row["sha256"] and len(data) == row["bytes"]
        receipt.update(status="PASS_NEW_PORTABLE_PROPERTY_MODAL_CONTROLS",
                       passed=report["passed"], executed=report["executed"], failed=0, skipped=0,
                       finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       unchanged_compiled_inputs=17,
                       run_json_sha256=sha((output / "run.log").read_bytes()))
        record(output / "CONTROL_RUN_RECEIPT.json", receipt)
        print(json.dumps({"status": receipt["status"], "executed": report["executed"],
                          "receipt": str(output / "CONTROL_RUN_RECEIPT.json")}))
    except BaseException as error:
        receipt.update(status="FAILED_NO_ACCEPTANCE_CREDIT", failure_type=type(error).__name__, failure=str(error),
                       finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        record(output / "CONTROL_RUN_RECEIPT.json", receipt)
        raise


if __name__ == "__main__":
    main()
