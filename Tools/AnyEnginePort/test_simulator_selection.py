#!/usr/bin/env python3
"""Exercise the workflow's actual simulator-selection scripts using synthetic CLI JSON."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import argparse, hashlib, json, os, re, tempfile, textwrap

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/pinkha-any-engine-port.yml"

@contextmanager
def in_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)

def runtime(identifier, version, available=True):
    return {"identifier": identifier, "version": version, "isAvailable": available}

def device(name, identifier):
    return {"name": name, "deviceTypeIdentifier": identifier, "isAvailable": True}

def check_script(code, available, versions, expected):
    calls = []
    with tempfile.TemporaryDirectory(prefix="any-simulator-selector-") as directory:
        work = Path(directory)
        for kind in ("any-native-evidence", "any-patched-evidence"):
            (work / "build" / kind).mkdir(parents=True)
        def command(arguments, **kwargs):
            if arguments == ["xcrun", "simctl", "list", "devices", "available", "--json"]:
                return json.dumps({"devices": available}).encode()
            if arguments == ["xcrun", "simctl", "list", "runtimes", "--json"]:
                return json.dumps({"runtimes": versions}).encode()
            if arguments[:3] == ["xcrun", "simctl", "create"]:
                calls.append(arguments)
                return "SYNTHETIC-OWNED-UDID\n"
            raise AssertionError("Unexpected subprocess: " + repr(arguments))
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "synthetic-run",
                                     "GITHUB_ENV": str(work / "github-env")}), \
             patch("subprocess.check_output", side_effect=command), in_directory(work):
            failure = None
            try:
                exec(compile(code, "<actual-workflow-selector>", "exec"), {"__name__": "__main__"})
            except SystemExit as error:
                failure = str(error)
        if expected is None:
            assert failure and not calls, "Incompatible metadata must not create a simulator"
            return
        assert failure is None, failure
        assert len(calls) == 1 and tuple(calls[0][-2:]) == expected, calls
        outputs = list((work / "build").rglob("simulator.json"))
        assert len(outputs) == 1
        result = json.loads(outputs[0].read_text())
        assert result["ownedUDID"] == "SYNTHETIC-OWNED-UDID"
        assert (result["deviceType"], result["runtime"]) == expected
        assert (work / "github-env").read_text().strip() == "ANY_NATIVE_SIMULATOR_UDID=SYNTHETIC-OWNED-UDID"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, default=WORKFLOW)
    args = parser.parse_args()
    source = args.workflow.read_text(encoding="utf-8")
    bodies = [textwrap.dedent(body) for body in re.findall(
        r"          python3 - <<'PY'\n(.*?)          PY", source, re.DOTALL)
        if '"simctl", "list", "devices"' in body]
    assert len(bodies) == 2, "Both official and patched native workflows need this selection gate"
    ios26 = "com.apple.CoreSimulator.SimRuntime.iOS-26-4"
    ios27phone = "com.apple.CoreSimulator.SimRuntime.iOS-27-0-iPhone19-1"
    ios27pad = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
    ios271 = "com.apple.CoreSimulator.SimRuntime.iOS-27-1"
    phone, pad = "com.apple.CoreSimulator.SimDeviceType.iPhone-19", "com.apple.CoreSimulator.SimDeviceType.iPad-Pro"
    cases = [
        ("hardware_suffix_and_same_version_ipad_preference",
         {ios26:[device("iPad Old", pad)], ios27phone:[device("iPhone 19", phone)],
          ios27pad:[device("iPad Pro", pad)]},
         [runtime(ios26,"26.4"), runtime(ios27phone,"27.0"), runtime(ios27pad,"27.0")], (pad,ios27pad)),
        ("hardware_specific_runtime_uses_metadata_version",
         {ios27phone:[device("iPhone 19",phone)]}, [runtime(ios27phone,"27.0")], (phone,ios27phone)),
        ("newer_compatible_runtime_precedes_older_form_factor",
         {ios27pad:[device("iPad Pro",pad)], ios271:[device("iPhone 19",phone)]},
         [runtime(ios27pad,"27.0"),runtime(ios271,"27.1")], (phone,ios271)),
        ("older_runtime_refused",
         {ios26:[device("iPhone 19",phone)]},[runtime(ios26,"26.4")],None),
        ("unavailable_runtime_refused",
         {ios27phone:[device("iPhone 19",phone)]},[runtime(ios27phone,"27.0",False)],None),
        ("malformed_metadata_refused_without_identifier_guess",
         {ios27phone:[device("iPhone 19",phone)]},[runtime(ios27phone,"unexpected")],None),
    ]
    results = []
    for index, body in enumerate(bodies):
        for name, devices, runtimes, expected in cases:
            check_script(body, devices, runtimes, expected)
            results.append({"script": index, "case": name, "status": "PASS"})
    record = {"status": "PASS", "scope": "actual_workflow_python_with_synthetic_simctl_json",
              "appleSimulatorExecution": False, "count":len(results), "checks":results,
              "workflowSHA256":hashlib.sha256(args.workflow.read_bytes()).hexdigest(),
              "selectorSHA256":[hashlib.sha256(body.encode()).hexdigest() for body in bodies],
              "runnerSHA256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(record,indent=2))
if __name__ == "__main__":
    main()
