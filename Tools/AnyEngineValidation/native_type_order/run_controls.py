import datetime, hashlib, json, os, pathlib, re, shutil, signal, subprocess, time
ROOT = pathlib.Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
CACHE = pathlib.Path("/tmp/pinkha-c-swift-cache-20261125")
OUT = pathlib.Path("/mnt/development/projects/evidence/migration-final-20261125/native-type-order/controls-attempt1")
EXPECTED = "5fb71c1849c86bf14b54325d5ffdc439bf8b1c29"
SELECTORS = "NativeImportedTypeOrderTests|NativeDefinitionPlanTests/testTypeManualOrder|NativeDefinitionPlanTests/testOriginalCustomCaptureMapsCurrentChoicesAndValuesWithoutPromotingSourceAcceptance"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def sources():
    files = subprocess.check_output(["git", "-c", "safe.directory="+str(ROOT), "-C", str(ROOT),
        "ls-files", "--", "Modules/PinkhaAnyEngine", "Modules/PinkhaAnyIntegration",
        "Modules/PinkhaAnyHost", "Modules/PinkhaKit"], text=True).splitlines()
    return {name: sha(ROOT / name) for name in files
            if name.endswith(".swift") or name.endswith("Package.resolved")}
def dependencies():
    value = json.loads((CACHE / "workspace-state.json").read_text())
    return value.get("object", value).get("dependencies", [])
head = subprocess.check_output(["git", "-c", "safe.directory="+str(ROOT), "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
assert head == EXPECTED
assert CACHE.is_symlink() and CACHE.resolve() == pathlib.Path("/mnt/development/projects/evidence/migration-final-20261125/compiled-resolver/swift-cache")
assert not OUT.exists()
OUT.mkdir(mode=0o700, parents=True)
before, deps = sources(), dependencies()
save("source-before.json", before); save("dependencies-before.json", deps)
project_free, temporary_free = shutil.disk_usage(ROOT).free, shutil.disk_usage("/tmp").free
estimate, floor = 128 * 1024**2, 256 * 1024**2
assert min(project_free, temporary_free) > estimate + floor
temp = OUT / "temporary"; temp.mkdir(mode=0o700)
env = os.environ.copy()
env.update(TMPDIR=str(temp),
    PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE="/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156")
command = ["/usr/local/bin/swift", "test", "--package-path", str(ROOT / "Modules/PinkhaAnyHost"),
           "--scratch-path", str(CACHE), "--jobs", "2", "--filter", SELECTORS]
save("command.json", {"command": command, "sourceCommit": head, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "expectedMethods": 7, "newNativeCalls": 0, "warmIncrementalEstimateBytes": estimate,
                     "emergencyFreeBytes": floor, "initialProjectFreeBytes": project_free, "initialTemporaryFreeBytes": temporary_free})
started = time.monotonic(); process = None; absent = False; absence = None; stopped = False
minimum = min(project_free, temporary_free)
errors = []
def present():
    global absent, absence
    if process is None or absent: return False
    try: os.killpg(process.pid, 0)
    except ProcessLookupError:
        absent = True; absence = datetime.datetime.now(datetime.timezone.utc).isoformat(); return False
    return True
def stop_owned():
    if not present(): return
    os.killpg(process.pid, signal.SIGTERM)
    until = time.monotonic() + 15
    while time.monotonic() < until:
        if not present(): return
        time.sleep(0.1)
    if present(): os.killpg(process.pid, signal.SIGKILL)
try:
    with (OUT / "original.log").open("xb") as stream:
        process = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        save("owned-process.json", {"pid":process.pid, "pgid":process.pid, "at":datetime.datetime.now(datetime.timezone.utc).isoformat()})
        while process.poll() is None:
            minimum = min(minimum, shutil.disk_usage(ROOT).free, shutil.disk_usage("/tmp").free)
            if minimum < floor or time.monotonic()-started > 500:
                stopped = True; stop_owned(); break
            time.sleep(0.5)
        process.wait(timeout=20)
        # Establish terminal group absence before longer log/source hashing.
        if present():
            stop_owned()
except BaseException as exc:
    errors.append({"type": type(exc).__name__, "message": str(exc)})
finally:
    try:
        stop_owned()
        if process is not None: process.wait(timeout=20)
    except BaseException as exc: errors.append({"phase":"owned-cleanup", "type":type(exc).__name__, "message":str(exc)})
    after = sources(); after_deps = dependencies()
    save("source-after.json", after); save("dependencies-after.json", after_deps)
    log = (OUT / "original.log").read_text(errors="replace") if (OUT / "original.log").exists() else ""
    cases = re.findall(r"Test Case '([^']+)' (passed|failed|skipped)", log)
    counts = {outcome:sum(row[1] == outcome for row in cases) for outcome in ("passed","failed","skipped")}
    result = {"status":"PASS_AFFECTED_COMPONENT_CONTROLS_ONLY" if
        process is not None and process.returncode == 0 and not stopped and not errors and absent and
        before == after and deps == after_deps and counts == {"passed":7,"failed":0,"skipped":0}
        else "FAIL", "returncode":process.returncode if process else None, "counts":counts,
        "methods":cases, "sourceCommit":head, "sourceUnchanged":before == after,
        "dependenciesUnchanged":deps == after_deps, "controllerStopped":stopped, "errors":errors,
        "seconds":round(time.monotonic()-started,3), "minimumFreeBytes":minimum,
        "ownedGroupPositivelyAbsent":absent, "absenceObservedAt":absence,
        "logSHA256":sha(OUT/"original.log") if (OUT/"original.log").exists() else None,
        "newNativeCalls":0, "destinationWrites":0, "wholeMigrationAccepted":False}
    save("result.json", result)
    print(json.dumps(result))
    print("\n".join(log.splitlines()[-26:]))
raise SystemExit(0 if result["status"] == "PASS_AFFECTED_COMPONENT_CONTROLS_ONLY" else 1)
