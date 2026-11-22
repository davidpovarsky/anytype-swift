#!/usr/bin/env python3
"""Audit the original build evidence; never promote its failed host execution."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parent
ZIP_SHA = "ff35f54d028057cccc3125d63e681a257e371d37cacd3e7a5ea0aadf1b69b358"
RUN = "45035194823"
SHA = "78b8b6168f0a750d2b742d94b78c95aa4abf579a"
NATIVE_SHA = "b2fc3804426067dd1ec8318d6ea92a4bcb8e9545"
EXPECTED = {
    "production": {
        "artifact_id": 14759749573,
        "zip_sha256": "9129d5b08a52f48422c2494b195ec6f32128948a0a578f3af0785102d35c925e",
        "tar_sha256": "ac94393135cf044d1dd035d7c00fed8c6d0ba0c265d9b0e7b9b676d1f6abe3dc",
        "binary_sha256": "1b317dd0d4a22222f0e2eac7769be65b301ffbf4e45c91be4ab4377b87dfa1d1",
    },
    "fixture": {
        "artifact_id": 14760192199,
        "zip_sha256": "5bd3b2dde6287dd648b69b4d6149293f60f454223e8be3a33ec1174d4f77e926",
        "tar_sha256": "031e3e1893fb20dda22f197e52182112b1f28384302a27006b3faf2534d6c6ab",
        "binary_sha256": "84213a9393e7ae17633dce1c60f53afcf7a373f83069e60d9667d53f603642f9",
    },
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    original = ROOT / "proof-original.zip"
    raw = original.read_bytes()
    assert len(raw) == 3_791_782 and sha(raw) == ZIP_SHA
    with zipfile.ZipFile(original) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) == 106
        assert all(not PurePosixPath(n).is_absolute() and ".." not in PurePosixPath(n).parts
                   and "\\" not in n for n in names)
        assert not any("xcresult" in n for n in names)
        original_files = {n: sha(archive.read(n)) for n in sorted(names)}
        read = lambda n: json.loads(archive.read(n))
        build = read("proof/build.json")
        host = read("proof/host/receipt.json")
        retained = read("controls/retained-original.json")
        before = read("proof/native-source-before.json")
        after = read("proof/native-source-after.json")
        assert before == after and len(before) == 139
        assert build["run_id"] == host["run_id"] == RUN
        assert build["app_sha"] == host["app_sha"] == SHA
        assert build["native_run"] == host["native_run"] == "45026227924"
        assert build["native_source"] == NATIVE_SHA and build["native_source_count"] == 139
        assert build["status"] == "BUILT_DISTINCT_COHERENT_APPLE_FRAMEWORKS_NOT_EXECUTED"
        assert build["phase"] == "COMPLETE"
        assert build["fixture_ios_execution"] == build["production_binary_execution"] == "NOT_RUN"
        assert build["old_tests_executed"] == 0
        assert host["status"] == "FAIL" and host["error_type"] == "ValueError"
        assert host["error"] == "Native command failed: create-owned-simulator.log"
        assert host["full_app_acceptance"] == host["production_binary_execution"] == "NOT_RUN"
        assert host["build_receipt_sha256"] == sha(archive.read("proof/build.json"))
        source_snapshot = read("proof/host/control-source-before.json")
        assert len(source_snapshot) == 447
        assert host["source_snapshot_sha256"] == sha(json.dumps(source_snapshot, sort_keys=True, separators=(",", ":")).encode())
        commands = [(c["name"], c["status"]) for c in host["commands"]]
        assert commands == [
            ("schemes", "PASS_EXIT_0"), ("resolve-packages", "PASS_EXIT_0"),
            ("runtimes", "PASS_EXIT_0"), ("device-types", "PASS_EXIT_0"),
            ("create-owned-simulator", "FAIL"),
        ]
        failure = archive.read("proof/host/create-owned-simulator.log").decode()
        assert "Incompatible device" in failure and "403" in failure
        assert retained["status"] == "RETAINED_UNCHANGED_CONTROL_EXECUTION"
        assert retained["methods_executed_again"] == 0
        assert retained["python_methods_passed"] == 5 and retained["embedded_go_methods_passed"] == 3
        assert retained["fail"] == retained["skip"] == 0
        for variant, expected in EXPECTED.items():
            framework = build["frameworks"][variant]
            packaged = read(f"proof/{variant}/custom-heart-build.json")
            descriptor = read(f"proof/{variant}/runtime-artifact.json")
            assert framework["artifact_sha256"] == descriptor["sha256"] == expected["tar_sha256"]
            assert framework["binary_sha256"] == host[f"{variant}_binary_sha256"] == expected["binary_sha256"]
            assert descriptor["github_run_id"] == packaged["github_run_id"] == RUN
            assert descriptor["integration_sha"] == packaged["integration_sha"] == SHA
            assert descriptor["fixture_included"] == packaged["fixture_included"] == (variant == "fixture")
            assert descriptor["receipt_sha256"] == sha(archive.read(f"proof/{variant}/custom-heart-build.json"))
        assert EXPECTED["fixture"]["binary_sha256"] != EXPECTED["production"]["binary_sha256"]

    receipt = {
        "status": "ORIGINAL_BUILD_PROOF_AUDIT_PASS_HOST_EXECUTION_FAILED",
        "run_id": RUN, "run_url": f"https://github.com/davidpovarsky/anytype-swift/actions/runs/{RUN}",
        "source_sha": SHA, "proof_artifact_id": 14759749585,
        "proof_zip_sha256": ZIP_SHA, "proof_zip_bytes": len(raw), "original_file_count": len(original_files),
        "original_file_sha256": original_files,
        "native_source_count_unchanged": 139, "native_source_run": "45026227924", "native_source_sha": NATIVE_SHA,
        "framework_receipt_bindings": EXPECTED,
        "framework_archives_downloaded_in_this_replay": False,
        "framework_binary_bytes_independently_verified_in_this_replay": False,
        "retained_old_controls_executed_again": 0,
        "actual_xctest_methods": 0, "host_execution_status": "FAIL_BEFORE_SIMULATOR_CREATION",
        "production_execution": "NOT_RUN", "fixture_execution": "NOT_RUN",
        "full_T2": "OPEN", "full_T5": "OPEN", "SDK06": "OPEN",
        "full_app_acceptance": "OPEN", "physical_iPad": "NOT_RUN",
    }
    (ROOT / "ORIGINAL_BUILD_AUDIT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in [
        "status", "run_id", "proof_zip_sha256", "original_file_count",
        "native_source_count_unchanged", "actual_xctest_methods", "host_execution_status",
    ]}, sort_keys=True))


if __name__ == "__main__":
    main()
