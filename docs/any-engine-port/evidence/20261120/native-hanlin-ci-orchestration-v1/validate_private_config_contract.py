#!/usr/bin/env python3
"""Check exact schema types against one preserved real stopped-fixture config."""
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    wrapper = ROOT / "Tools/AnyEnginePort/hanlin_fixture_ci.py"
    record = {"schemaVersion": 1, "status": "FAIL",
              "scope": "ci_wrapper_schema_controls_no_new_provider_run",
              "actualAppleExecution": False, "privateMaterialPrinted": False,
              "runnerSHA256": sha(Path(__file__)), "wrapperSHA256": sha(wrapper),
              "priorActualLifecycleWrapperSHA256": "a815c137ea19ab5c07f9cbeea4fa1e00a2de3edfeedec6b976eb99d54d1843ad",
              "checks": [], "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def check(name, condition):
        record["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise RuntimeError("fixed_schema_control_failed")
    try:
        spec = importlib.util.spec_from_file_location("owned_hanlin_ci_schema_control", wrapper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        locator = ROOT / "build/any-engine-port/hanlin-provider-fixture-validation-v2/private-config-location.txt"
        actual = Path(locator.read_text(encoding="utf-8").strip()).resolve()
        actual_before = sha(actual)
        original = json.loads(actual.read_text(encoding="utf-8"))
        private_fixture = actual.parent
        ca = private_fixture / "root-ca.pem"
        ca_before = sha(ca)
        record["publicRootCertificateFileSHA256"] = ca_before
        check("real_stopped_v2_config_accepts_exact_integer_one",
              module.validate_private_config(actual, private_fixture) == original["testRunnerEnvironment"])
        mutations = [("boolean_true", True), ("boolean_false", False),
                     ("floating_one", 1.0), ("string_one", "1"),
                     ("integer_zero", 0), ("integer_two", 2), ("null", None), ("missing", None)]
        with tempfile.TemporaryDirectory(prefix="pinkha-hanlin-schema-controls-") as folder:
            control_root = Path(folder).resolve()
            candidate = control_root / "private-config-control.json"
            for name, value in mutations:
                changed = copy.deepcopy(original)
                if name == "missing":
                    del changed["schemaVersion"]
                else:
                    changed["schemaVersion"] = value
                candidate.write_text(json.dumps(changed), encoding="utf-8")
                denied = False
                try:
                    module.validate_private_config(candidate, private_fixture)
                except module.BoundaryError as error:
                    denied = str(error) == "fixture_config_schema_mismatch"
                check("private_config_rejects_" + name, denied)
            run_id = "90000000001"
            source = "a" * 40
            owned = control_root / ("pinkha-hanlin-ci-" + run_id + "-schema-control")
            owned.mkdir()
            config = owned / "fixture/private-config.json"
            marker_file = owned / "owner.json"
            marker = {"schemaVersion": 1, "githubRunID": run_id,
                      "sourceCommit": source, "ownedDirectory": str(owned)}
            marker_file.write_text(json.dumps(marker), encoding="utf-8")
            with patch.dict(os.environ, {module.OWNED_DIR_ENV: str(owned), module.CONFIG_ENV: str(config)}):
                check("owned_marker_accepts_exact_integer_one",
                      module.read_owned_config(run_id, source, control_root) == (owned, config, marker))
                for name, value in mutations:
                    changed = dict(marker)
                    if name == "missing":
                        del changed["schemaVersion"]
                    else:
                        changed["schemaVersion"] = value
                    marker_file.write_text(json.dumps(changed), encoding="utf-8")
                    denied = False
                    try:
                        module.read_owned_config(run_id, source, control_root)
                    except module.BoundaryError as error:
                        denied = str(error) == "fixture_owner_marker_mismatch"
                    check("owned_marker_rejects_" + name, denied)
        record["actualPrivateInputUnchanged"] = sha(actual) == actual_before and sha(ca) == ca_before
        record["sourceStable"] = sha(wrapper) == record["wrapperSHA256"]
        if not record["actualPrivateInputUnchanged"] or not record["sourceStable"]:
            raise RuntimeError("validation_input_changed")
        record["status"] = "PASS"
    except Exception:
        record["failure"] = "fixed_schema_control_or_private_input_boundary_failed"
    record["finishedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record["passed"] = sum(check["passed"] for check in record["checks"])
    record["total"] = len(record["checks"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record))
    return 0 if record["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
