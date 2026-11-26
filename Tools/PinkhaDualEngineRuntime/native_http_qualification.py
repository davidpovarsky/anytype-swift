"""Admit the retained actual two-peer permission-boundary qualification.

This requalifies original evidence; it never executes a test, starts an account,
or changes the minimum legacy compatibility floor.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import stat

FILES = {'RESULT.json': {'bytes': 3110, 'sha256': 'b8694dbd2ac3facce43771bdb7f206461d1b95924a5ccb1248114185a394ce1d'}, 'controller.py': {'bytes': 13429, 'sha256': 'aa08818d437ce6cd4b8bdee6c94f730e0dc11c55593b8818e074823c8c354f6e'}, 'current-BUILD.json': {'bytes': 1181, 'sha256': '3241e434144c399e52c1bd199f4b75a142d2ae62e8de82206721f65f993e94b1'}, 'legacy-BUILD.json': {'bytes': 1179, 'sha256': 'b792cee4e9e6e19ee75e75e25f5d248f898d81896d7bd3b84e8a7cb89c5338c7'}, 'native-exit-original.json': {'bytes': 177, 'sha256': '90d2b30a36ceabb540cbcb7475c31b713e99a197864e9920dc1eba981ecc0ad7'}, 'original.log': {'bytes': 135774, 'sha256': '36aee08b83cdefc5a097f40defd23ba85664f966df37c485f8d752f19723892e'}, 'owned-group-observations.json': {'bytes': 108, 'sha256': '891f8edfa299a8bd8b9b8700ded68e13510fd5a98eca41da5e0dbaf599deeb6a'}, 'qualification.json': {'bytes': 2952, 'sha256': 'd50faf7ce50c6c418b8cc55dd7e46d86aa1a9d5783819b0b943e74c3ddb09da0'}, 'source-after.json': {'bytes': 310030, 'sha256': '2fa7285670f6cfcac0b87a0b0b6d49a900ac68f703f59c5a54e9fa0c7419c2f0'}, 'source-before.json': {'bytes': 310030, 'sha256': '2fa7285670f6cfcac0b87a0b0b6d49a900ac68f703f59c5a54e9fa0c7419c2f0'}}
METHODS = {
    "TestPinkhaMixedOldOwnerNewMember_RemoteRoleEnforcement",
    "TestPinkhaMixedNewOwnerOldMember_RemoteRoleEnforcement",
}
CURRENT = {"any": "8fbd1e819fb132ac0e0a848d2ddf5c5714189b81",
           "sdk": "c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"}
LEGACY = {"any": "9a190eb8236f18da75e5d85c3d1db31cd558d098",
          "sdk": "e195f6c07a053c6588e39ffe72ee4fc44cf3d953"}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def qualify_contents(values, manifest):
    require(set(values) == set(FILES), "closed_original_native_http_files_required")
    for name, row in FILES.items():
        require(len(values[name]) == row["bytes"]
                and hashlib.sha256(values[name]).hexdigest() == row["sha256"],
                "original_native_http_bytes_changed:" + name)
    result = json.loads(values["RESULT.json"])
    qualification = json.loads(values["qualification.json"])
    original_exit = json.loads(values["native-exit-original.json"])
    observations = json.loads(values["owned-group-observations.json"])
    require({name: manifest["sourcePins"][name] for name in CURRENT} == CURRENT,
            "qualified_current_native_sources_differ")
    require(result["status"] == "PASS_TWO_REAL_FIXED_NATIVE_MIXED_VERSION_AUTHORITY_SCENARIOS"
            and result["exitCode"] == 0 and result["passed"] == 2
            and result["failed"] == result["skipped"] == result["forcedNativeStops"] == 0
            and result["completedAuthorityScenarios"] == 2 and result["unparsedLogLines"] == 0
            and set(result["expectedMethods"]) == METHODS
            and set(result["tests"]) == METHODS
            and all(row["status"] == "pass" for row in result["tests"].values()),
            "two_original_real_native_methods_required")
    require(qualification["status"] == "SOURCE_QUALIFIED_NOT_EXECUTED"
            and result["qualificationSHA256"] == FILES["qualification.json"]["sha256"]
            and result["controllerSHA256"] == FILES["controller.py"]["sha256"]
            and qualification["actualMinimumLegacyCommit"] == LEGACY["any"]
            and qualification["authorityInverseRestoresEveryOriginalByte"] is True
            and qualification["wrapperInverseRestoresEveryOriginalByte"] is True
            and qualification["originalUnpatchedLegacyReclassified"] is False
            and qualification["originalNativeDeadlinesChanged"] == 0
            and qualification["originalPayloadLeakChecksChanged"] == 0
            and qualification["originalSignedReadAssertionsChanged"] == 0,
            "original_native_assertions_or_legacy_floor_changed")
    require(result["new"] == qualification["current"] and result["old"] == qualification["legacy"]
            and qualification["current"]["commits"] == CURRENT
            and qualification["legacy"]["commits"] == LEGACY,
            "actual_native_binary_source_bindings_differ")
    for label, expected in (("current", CURRENT), ("legacy", LEGACY)):
        row = qualification[label]
        build = json.loads(values[label + "-BUILD.json"])
        require(row["buildReceiptSHA256"] == FILES[label + "-BUILD.json"]["sha256"]
                and build["status"] == "PASS_BUILD_ONLY" and build["exitCode"] == 0
                and build["sourceUnchanged"] is True and build["ownedGroupAbsent"] is True
                and build["commits"] == expected
                and build["binary"] == {key: row[key] for key in ("path", "bytes", "sha256")},
                "original_native_build_binding_changed:" + label)
    require(result["sourceBeforeVerified"] is True and result["sourceAfterVerified"] is True
            and result["originalBinariesPreserved"] is True
            and values["source-before.json"] == values["source-after.json"]
            and qualification["sourceInventorySHA256"] == FILES["source-before.json"]["sha256"],
            "original_native_source_integrity_not_qualified")
    require(original_exit["exitCode"] == 0
            and original_exit["pid"] == original_exit["pgid"] == result["pid"] == result["pgid"]
            and result["ownedGroupAbsent"] is True
            and result["processObservationsSHA256"] == FILES["owned-group-observations.json"]["sha256"]
            and observations == [dict(observations[0], pgid=result["pgid"], signal=0, state="ABSENT_ESRCH")]
            and original_exit["logSHA256"] == result["logSHA256"] == FILES["original.log"]["sha256"],
            "actual_native_exit_or_positive_group_absence_changed")
    events = [json.loads(line) for line in values["original.log"].decode("utf-8").splitlines()]
    require(all(isinstance(event, dict) and event.get("Action") not in ("fail", "skip") for event in events),
            "original_native_failure_or_skip_present")
    passed = [event["Test"] for event in events if event.get("Action") == "pass" and "Test" in event]
    ran = [event["Test"] for event in events if event.get("Action") == "run" and "Test" in event]
    packages = [event for event in events if event.get("Action") == "pass" and "Test" not in event]
    require(len(passed) == len(ran) == 2 and set(passed) == set(ran) == METHODS
            and len(packages) == 1 and packages == result["packageResults"],
            "original_go_json_method_census_changed")
    return {"status": "PASS_RETAINED_ORIGINAL_TWO_NATIVE_PERMISSION_METHODS",
            "resultSHA256": FILES["RESULT.json"]["sha256"],
            "sourceQualificationSHA256": FILES["qualification.json"]["sha256"],
            "originalLogSHA256": FILES["original.log"]["sha256"],
            "currentSources": CURRENT, "minimumLegacySources": LEGACY,
            "originalMethodsPassed": 2, "testsExecutedNow": 0, "appBuilds": 0,
            "originalFiles": FILES}


def qualify(root, manifest):
    root = Path(root)
    require(root.resolve() == root and root.is_dir()
            and {p.name for p in root.iterdir()} == set(FILES),
            "closed_unaliased_original_native_http_directory_required")
    values = {}
    for name, row in FILES.items():
        path = root / name
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_size == row["bytes"],
                "bounded_original_native_http_file_required:" + name)
        data = path.read_bytes()
        after = path.lstat()
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                "original_native_http_file_changed_during_read:" + name)
        values[name] = data
    proof = qualify_contents(values, manifest)
    qualification = json.loads(values["qualification.json"])
    binaries = {}
    for label in ("current", "legacy"):
        row = qualification[label]
        path = Path(row["path"])
        require(path.resolve() == path and path.is_file() and not path.is_symlink()
                and path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
                "retained_original_native_binary_changed:" + label)
        binaries[label] = {key: row[key] for key in ("path", "bytes", "sha256")}
    proof["retainedBinariesVerified"] = binaries
    return proof
