#!/usr/bin/env python3
"""Run the complete original notification suite on the exact additive SDK9565."""
import argparse, hashlib, json, os, pathlib, re, signal, subprocess, time, traceback

SOURCE = "9565a9e4775901a4cee6f0402d7fd2978fab6612"
MARKER = "b5b2ce165c1217140fcddd9289f6f496acb2e7fbd41ccd82fb3bc0a368002150"
EVENT = "867613ea9cf2785e6eff3caad96c620a8c50d16fd22d266eeda899b7ab784f69"
TEST = "7ee626a9f4e53cfa5c74d9f123d367eb43f5d6de21dfb152047ab75e4cb0e066"
FLOOR = 2 * 1024 ** 3

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def require(value, reason):
    if not value: raise RuntimeError(reason)

def free(path):
    v = os.statvfs(path)
    return v.f_bavail * v.f_frsize

def verify(source):
    marker = source / ".pinkha-source.json"
    require(sha(marker) == MARKER, "exact_materialized_marker")
    value = json.loads(marker.read_bytes())
    require(value["revision"] == SOURCE and len(value["files"]) == 959, "exact_complete_canonical_source")
    for name, expected in value["files"].items():
        p = source / name
        require(p.is_file() and not p.is_symlink() and sha(p) == expected, "source_changed:" + name)
    require(sha(source / "Packages/HanlinPlatform/Sources/HanlinScriptExtensions/HanlinNotificationEvent.swift") == EVENT, "exact_original_dff_product")
    test = source / "Packages/HanlinPlatform/Tests/HanlinScriptExtensionsTests/HanlinNotificationInvocationTests.swift"
    require(sha(test) == TEST, "exact_complete_original_test_file")
    names = re.findall(r"@Test(?:\([^\n]*\))?\s+func\s+(\w+)", test.read_text())
    require(len(names) == len(set(names)) == 11, "exact_original_eleven_methods")
    return names

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=pathlib.Path)
    p.add_argument("--output", required=True, type=pathlib.Path)
    args = p.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    result = {"status": "FAIL", "sourceCommit": SOURCE, "controllerSHA256": sha(pathlib.Path(__file__)),
              "appBuilds": 0, "nativeGoBuilds": 0, "simulatorBoots": 0,
              "fullAppAcceptance": False, "osNotificationDeliveryAccepted": False,
              "started": time.time(), "errors": []}
    child = None
    start = time.monotonic()
    try:
        expected = verify(source)
        result["sourceMethods"] = expected
        result["sourceBeforeVerified"] = True
        result["freeBytesBefore"] = free(out)
        result["estimatedColdBuildGrowthBytes"] = 10 * 1024 ** 3
        require(result["freeBytesBefore"] > result["estimatedColdBuildGrowthBytes"] + FLOOR, "measured_phase_capacity")
        result["jobs"] = os.cpu_count() or 1
        result["jobsBasis"] = "actual host logical CPUs; no additional utilization cap"
        argv = ["/usr/bin/xcrun", "swift", "test", "--package-path",
                str(source / "Packages/HanlinPlatform"), "--scratch-path", str(out / "build"),
                "--force-resolved-versions", "--skip-update", "--jobs", str(result["jobs"]),
                "--filter", "HanlinNotificationInvocationTests", "--xunit-output", str(out / "original-tests.xml")]
        result["argv"] = argv
        write(out / "command.json", result)
        log = out / "original-test.log"
        with log.open("wb") as output:
            child = subprocess.Popen(argv, stdout=output, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True,
                                     env=dict(os.environ, SWIFTPM_MODULECACHE_OVERRIDE=str(out / "module-cache")))
            result["pid"] = child.pid; result["pgid"] = os.getpgid(child.pid)
            write(out / "started.json", result)
            minimum = free(out)
            while child.poll() is None:
                minimum = min(minimum, free(out))
                if minimum < FLOOR or time.monotonic() - start > 1800:
                    result["stopReason"] = "capacity_floor" if minimum < FLOOR else "original_command_timeout"
                    os.killpg(child.pid, signal.SIGTERM)
                    try: child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        if child.poll() is None: os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=10)
                    break
                time.sleep(2)
        result["exitCode"] = child.returncode
        result["minimumFreeBytes"] = minimum
        result["logSHA256"] = sha(log)
        result["sourceAfterVerified"] = verify(source) == expected
        census = subprocess.run(["/bin/ps", "-A", "-o", "pid=,pgid="],
                                capture_output=True, text=True, timeout=10)
        (out / "original-final-pid-pgid.txt").write_text(census.stdout)
        result["groupCensusExit"] = census.returncode
        rows = [line.split() for line in census.stdout.splitlines() if line.strip()]
        require(census.returncode == 0 and rows and
                all(len(row) == 2 and all(x.isdigit() for x in row) for row in rows),
                "numeric_owned_group_observation_unresolved")
        result["ownedGroupRemaining"] = any(int(row[1]) == child.pid for row in rows)
        require(not result["ownedGroupRemaining"], "owned_group_not_quiescent")
        text = log.read_text(errors="replace")
        passed = re.findall(r"✔ Test ([^\n]+?) passed after", text)
        summaries = re.findall(r"Test run with (\d+) tests?(?: in \d+ suites?)? passed", text)
        result["originalPassedLines"] = passed
        result["originalSwiftTestingCounts"] = [int(x) for x in summaries]
        require(child.returncode == 0 and not result.get("stopReason"), "original_command_failed")
        require(result["originalSwiftTestingCounts"] == [12], "exact_original_twelve_case_instances")
        require(all(any(re.match(re.escape(name) + r"\(", line) for line in passed)
                    for name in expected), "all_original_methods_must_actually_pass")
        result.update(status="PASS_ORIGINAL_NOTIFICATION_SUITE_NOT_APP_ACCEPTANCE",
                      actualMethodCount=11, actualCaseCount=12, failed=0, skipped=0)
    except BaseException as error:
        result["errors"].append({"type": type(error).__name__, "message": str(error)})
        (out / "failure.txt").write_text(traceback.format_exc())
    finally:
        result["elapsedSeconds"] = time.monotonic() - start
        result["finished"] = time.time()
        if child is not None and child.poll() is None:
            result["status"] = "FAIL"; result["unresolvedLiveChildPID"] = child.pid
        write(out / "result.json", result)
        print(json.dumps(result), flush=True)
    return 0 if result["status"].startswith("PASS_") else 1

if __name__ == "__main__":
    raise SystemExit(main())
