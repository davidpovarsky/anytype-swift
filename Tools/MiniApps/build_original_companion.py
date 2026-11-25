"""Run the original verified producer-build prefix; boot/tests are separate owned phases."""
import argparse, base64, threading, ast, datetime, hashlib, importlib.util, json, os, pathlib, plistlib, shlex, shutil, subprocess, sys, time

parser = argparse.ArgumentParser()
parser.add_argument("--recovery-root", type=pathlib.Path, required=True)
args = parser.parse_args()
RECOVERY = args.recovery_root
assert RECOVERY.parent == pathlib.Path("/Users/m1/development/anytype-root-active-20261125")
assert RECOVERY.resolve() == RECOVERY and RECOVERY.is_dir()
ROOT = RECOVERY / "source"
SOURCE = "86a6dde354947be9329fe1e8f4d45a433fe488c4"
DERIVED = RECOVERY / "derived-producer1"
assert not DERIVED.exists(), "A fresh owned DerivedData avoids historical stale artifacts"
EVIDENCE = RECOVERY / "producer1"
PREPARATION = RECOVERY / "preparation"
CONTROLS = pathlib.Path(__file__).resolve().parent
HOST_SHA = "540507770659f00b8424b394c0c3857f52001cd13a0dc2bc3b38f313b385303a"
CONFIG_SHA = "03d96d520f785e34d85b643e31bcb4a424e46e76a81c6b4c245f91eaac3e110f"
RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-2"
ORIGINAL_SHA = "0070ab53ebc486c4df2a722cdd74b036bb5cf002aa72e772813ffaa434dbf23a"

def digest(path):
    with pathlib.Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def save(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2) + "\n")

assert not EVIDENCE.exists()
EVIDENCE.mkdir()
os.environ.update(
    PATH="/Users/m1/builds/_preflight/native-owned-node245-20261125/node-v24.5.0-darwin-arm64/bin:/opt/homebrew/opt/python@3.12/libexec/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer",
    PYTHONDONTWRITEBYTECODE="1", SPLIT_EVIDENCE=str(EVIDENCE),
    SPLIT_DERIVED_DATA=str(DERIVED), SPLIT_NATIVE_TEST_SCOPE="production_runtimes",
    SPLIT_EXECUTION_ORIGIN="local-mac", SPLIT_EXPECTED_SOURCE=SOURCE,
    RUNNER_TEMP=str(EVIDENCE / "runner-temp"), TMPDIR=str(EVIDENCE / "runner-temp") + "/")
(EVIDENCE / "runner-temp").mkdir()
os.environ.pop("SPLIT_REUSE_NATIVE_PROOF", None)
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=20).strip() == SOURCE
common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=ROOT, text=True, timeout=20).strip()
assert (ROOT / common).resolve() == (ROOT / ".git").resolve()
assert not (ROOT / ".git/objects/info/alternates").exists()
preparation = json.loads((PREPARATION / "RESULT.json").read_bytes())
assert preparation["status"] == "EXACT_SOURCE_AND_ORIGINAL_DEPENDENCIES_PREPARED_BUILD_NOT_RUN"
assert preparation["source"] == SOURCE and preparation["existingCheckoutUnchanged"] is True
assert preparation["appBuilds"] == preparation["nativeTests"] == 0
assert len(preparation["steps"]) == 9 and all(step["returncode"] == 0 for step in preparation["steps"])
assert digest(ROOT / "build/runtime-host/RuntimeHostResources.zip") == HOST_SHA
assert digest(ROOT / "Config.xcconfig") == CONFIG_SHA
original_identity = CONTROLS / "source-identity.json"
assert digest(original_identity) == "dca879b7fbbedf2f0243b7f3d90363ec5b6c468d82a49935de9219b1e38602a2"
expected_source = json.loads(original_identity.read_bytes())
assert len(expected_source["tracked_file_sha256"]) == 7693
assert all(digest(ROOT / name) == sha for name, sha in expected_source["tracked_file_sha256"].items())
assert digest(CONTROLS / "source-preparation.diff") == "863bf97e4b83fe9824be5345a7fcb2453f403a50d16ce3fdbc0c1c978b5482ab"
assert subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=ROOT, timeout=20) == (CONTROLS / "source-preparation.diff").read_bytes()
shutil.copy2(PREPARATION / "RESULT.json", EVIDENCE / "host-preparation.json")
free = shutil.disk_usage(ROOT).free
capacity = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "free_bytes": free, "cold_compile_packages_and_export_bytes": 25000000000,
            "concurrent_remaining_bytes": 10000000000, "margin_bytes": 5000000000,
            "basis": "One fresh isolated original MiniApps producer. Allows cold Swift packages/intermediates, native resources, app and immutable ZIP; independent Anytype acceptance allowance. Original preparation is already verified, no second Anytype build, simulator boot or XCTest."}
save("capacity.json", capacity)
assert free >= 40000000000, capacity
for argv, name in [(["/usr/bin/memory_pressure", "-Q"], "memory.txt"),
                   (["/usr/sbin/sysctl", "vm.swapusage"], "swap.txt")]:
    result = subprocess.run(argv, capture_output=True, timeout=20)
    (EVIDENCE / name).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0

helper = CONTROLS / "owned_commands.py"
assert digest(helper) == "e26589b62e3c69db67e534b3ecf42eb6342983e9c581474d9228f1bcc0e62f34"
sys.path.insert(0, str(helper.parent))
from owned_commands import run_logged

# Restore exact canonical Host bytes through the original workflow copy.
canonical_input = ROOT / "build/runtime-host/RuntimeHostResources.zip"
packaged_input = ROOT / "AI_HLY/RuntimeHostResources.zip"
assert digest(canonical_input) == HOST_SHA == "540507770659f00b8424b394c0c3857f52001cd13a0dc2bc3b38f313b385303a"
assert digest(packaged_input) == digest(canonical_input)
workflow = ROOT / ".github/workflows/validate-app-split.yml"
assert "cp build/runtime-host/RuntimeHostResources.zip AI_HLY/RuntimeHostResources.zip" in workflow.read_text()
stage_command = ["/bin/cp", "build/runtime-host/RuntimeHostResources.zip", "AI_HLY/RuntimeHostResources.zip"]
stage_result = run_logged(stage_command, ROOT, EVIDENCE / "canonical-workflow-host-copy.log", 60)
assert stage_result.returncode == 0 and digest(packaged_input) == digest(canonical_input)
runtime_resource_stage = {
    "status": "ORIGINAL_WORKFLOW_RESOURCE_COPY_VERIFIED_AFTER_EXACT_RECOVERY",
    "source": SOURCE, "workflow_sha256": digest(workflow),
    "actual_command": stage_command, "command_receipt_sha256": digest(EVIDENCE / "canonical-workflow-host-copy.command.json"),
    "prepared_and_current_source_sha256": digest(canonical_input),
    "source_recovery_receipt": str(PREPARATION / "RESULT.json"),
    "source_recovery_receipt_sha256": digest(PREPARATION / "RESULT.json"),
    "original_source_identity_sha256": digest(original_identity),
    "lost_historical_raw_log_not_recreated": True,
    "new_build_required": True, "runtime_body_change": False}
save("canonical-runtime-resource-stage.json", runtime_resource_stage)

sys.path.insert(0, str(ROOT / "Scripts/ProductSplit"))
import run_native_acceptance as original

path = ROOT / "Scripts/ProductSplit/run_native_acceptance.py"
assert digest(path) == ORIGINAL_SHA
source_text = path.read_text()
start = source_text.index("def main():\n")
stop = source_text.index("        state['status'] = 'INFRA_ERROR'\n        devices = ", start)
prefix = source_text[start:stop]
(EVIDENCE / "original-build-prefix.py.fragment").write_text(prefix)
boot_block = """        command(['sysctl', 'hw.memsize', 'hw.ncpu'], 'before-boot-host-resources.txt')
        command(['vm_stat'], 'before-boot-memory.txt')
        command(['ps', '-axo', 'pid,ppid,%cpu,%mem,state,etime,comm'], 'before-boot-processes.txt')
        command(['xcrun', 'simctl', 'boot', simulator], 'boot.log')
        command(['xcrun', 'simctl', 'bootstatus', simulator, '-b'], 'bootstatus.log', timeout=300)
"""
assert prefix.count(boot_block) == 1
prefix = prefix.replace(boot_block, """        state['simulator_boot'] = 'DEFERRED_TO_SEPARATELY_ADMITTED_TEST_PHASE'
""")
original_runtime = """        runtime = next(r for r in runtimes if r.get('isAvailable') and not r.get('isInternal')
                       and r['identifier'].endswith('iOS-'+sdk.replace('.', '-')))
"""
assert prefix.count(original_runtime) == 1
effective_runtime = """        runtime = next(r for r in runtimes if r.get('isAvailable') and not r.get('isInternal')
                       and r['identifier'] == 'com.apple.CoreSimulator.SimRuntime.iOS-27-2')
        assert runtime['version'] == '27.2' and runtime['buildversion'] == '24B8117'
        assert tuple(map(int, runtime['version'].split('.'))) >= tuple(map(int, sdk.split('.')))
"""
prefix = prefix.replace(original_runtime, effective_runtime)
prefix = prefix.replace("        state['status'] = 'PACKAGING_FAILED'", "        state['canonical_runtime_host_resource'] = json.loads((EVIDENCE/'canonical-runtime-resource-stage.json').read_text())\n        state['status'] = 'PACKAGING_FAILED'")
suffix = """        if state.get('consumer_build_export') != 'EXECUTED_PASS_BUILD_ONLY_NATIVE_ACCEPTANCE_RUNNING':
            raise RuntimeError('The actual build-only consumer export did not pass')
        state.update(status='BUILD_ONLY_VERIFIED_NATIVE_TESTS_NOT_RUN', ui='NOT_RUN',
                     fresh_native_method_count=0, reused_native_method_count=0)
        return state
    except Exception as error:
        state['error'] = str(error)
        raise
    finally:
        (EVIDENCE/'acceptance.json').write_text(json.dumps(state, indent=2)+'\\n')
"""
program = prefix + suffix
ast.parse(program)
(EVIDENCE / "effective-build-prefix.py").write_text(program)
save("original-build-prefix-admission.json", {
    "source": SOURCE, "original_runner_sha256": ORIGINAL_SHA, "original_runner_file_unmodified": True,
    "original_prefix_sha256": hashlib.sha256(source_text[start:stop].encode()).hexdigest(),
    "effective_prefix_sha256": hashlib.sha256(program.encode()).hexdigest(),
    "changes": ["defer only five pre-boot resource/process/boot commands; no synthetic success records",
                "select independently installed 27.2/24B8117 with SDK compatibility and original device-type checks",
                "stop after all original source/typecheck/build/signature/architecture/resource/immutable early-export gates"],
    "actual_build_argv_unchanged": True, "native_test_credit": 0,
    "historical_binary_recovered": False,
    "prior_preparation_failure_preserved": True
})
original_command = original.command

def validate_worklets(build_text):
    lines = [line.strip() for line in build_text.splitlines()
             if "WorkletsVersion.cpp" in line and " -c " in line and "/clang " in line]
    assert len(lines) <= 1
    if lines:
        tokens = shlex.split(lines[0])
        flags = []
        response = []
        for token in tokens:
            if token.startswith("@"):
                p = pathlib.Path(token[1:])
                raw = p.read_bytes()
                parsed = shlex.split(raw.decode())
                flags += parsed
                response.append({"path": str(p), "sha256": hashlib.sha256(raw).hexdigest()})
        assert "-DWORKLETS_VERSION=0.13.0" in flags
        assert not any("WORKLETS_VERSION" in flag and flag != "-DWORKLETS_VERSION=0.13.0" for flag in flags)
        obj = pathlib.Path(tokens[tokens.index("-o") + 1])
        save("worklets-object-admission.json", {"status": "CURRENT_ORIGINAL_OBJECT_COMPILED_WITH_RESOLVED_VERSION",
             "source": SOURCE, "command": lines[0], "object": str(obj),
             "object_sha256": digest(obj), "responses": response})
    else:
        raise RuntimeError("Recovered source requires actual new WorkletsVersion.cpp code generation; no historical object admission used")

def checked(argv, name, timeout=60, env=None):
    if name == "build.log":
        assert env is None and timeout == 2400 and "build-for-testing" in argv
        begun = time.monotonic()
        result = run_logged(argv, ROOT, EVIDENCE / name, timeout)
        output = (EVIDENCE / name).read_text(errors="replace")
        with (EVIDENCE / "commands.jsonl").open("a") as stream:
            stream.write(json.dumps({"argv": argv, "exit": result.returncode,
                "seconds": time.monotonic()-begun, "log": name, "sha256": digest(EVIDENCE/name)})+"\n")
        assert result.returncode == 0, ("actual original build-for-testing failed", result.returncode)
        app = DERIVED / "Build/Products/Debug-iphonesimulator/HanlinMiniApps.app"
        original_command([sys.executable, "Scripts/Runtime/validate_ios_system_resources.py",
                          "--app", str(app), "--json-output", str(EVIDENCE/"built-ios-system-resources.json")],
                         "built-ios-system-resources.log", timeout=60)
        assert digest(app / "RuntimeHostResources.zip") == HOST_SHA
        assert digest(app / "RuntimeHostResources.zip") == digest(ROOT / "AI_HLY/RuntimeHostResources.zip")
        save("actual-bundled-current-host.json", {
            "status": "ACTUAL_APP_ARCHIVE_EQUALS_CANONICAL_PREPARED_HOST",
            "source": SOURCE, "app_archive_sha256": digest(app / "RuntimeHostResources.zip"),
            "canonical_stage_sha256": digest(EVIDENCE / "canonical-runtime-resource-stage.json")})
        validate_worklets(output)
        return output
    return original_command(argv, name, timeout=timeout, env=env)

# Mirror append-only original logs to the off-host coordinator while they are written.
# This is evidence transport only; original compiler/commands/export remain unchanged.
mirror_stop = threading.Event()
mirror_errors = []
def mirror_raw_logs():
    positions = {}
    try:
        while not mirror_stop.is_set():
            for name in ("build.log", "commands.jsonl"):
                path = EVIDENCE / name
                if not path.is_file():
                    continue
                offset = positions.get(name, 0)
                assert path.stat().st_size >= offset, ("original log truncated", name)
                with path.open("rb") as source:
                    source.seek(offset)
                    while block := source.read(131072):
                        print("HANLIN_NATIVE_MIRROR\t" + json.dumps({"name": name, "offset": offset,
                              "bytes": len(block), "data": base64.b64encode(block).decode()}), flush=True)
                        offset += len(block)
                positions[name] = offset
            mirror_stop.wait(0.5)
    except BaseException as error:
        mirror_errors.append(repr(error))
mirror_thread = threading.Thread(target=mirror_raw_logs, daemon=True)
mirror_thread.start()

original.command = checked
exec(compile(program, str(EVIDENCE / "effective-build-prefix.py"), "exec"), original.__dict__)
try:
    record = original.main()
finally:
    time.sleep(0.6)
    mirror_stop.set()
    mirror_thread.join(timeout=5)
    assert not mirror_thread.is_alive() and not mirror_errors, mirror_errors
device = record["simulator"]
actual = json.loads(original_command(["xcrun", "simctl", "list", "devices", "-j"],
                                    "actual-build-destination-state.json", timeout=30))["devices"]
row = next(d for d in actual[RUNTIME] if d["udid"] == device)
assert row["state"] == "Shutdown", row
source_identity = json.loads((EVIDENCE/"source-identity.json").read_bytes())
assert all(digest(ROOT / name) == sha for name, sha in source_identity["tracked_file_sha256"].items())
assert subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=ROOT, timeout=20) == (EVIDENCE/"source-preparation.diff").read_bytes()
assert source_identity["tracked_file_sha256"] == expected_source["tracked_file_sha256"]
assert source_identity["prepared_tree"] == expected_source["prepared_tree"]
save("BUILD_ONLY_RESULT.json", {"status": "ACTUAL_ORIGINAL_BUILD_AND_IMMUTABLE_EXPORT_PASS_NATIVE_TESTS_NOT_RUN",
    "source": SOURCE, "actual_build_destination": row, "runtime": record["runtime"],
    "native_test_credit": 0, "consumer_build": str(EVIDENCE / "consumer-build"),
    "source_identity_sha256": digest(EVIDENCE/"source-identity.json"),
    "actual_compiler_sdk": subprocess.check_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], text=True, timeout=20).strip(),
    "actual_xcode": subprocess.check_output(["xcodebuild", "-version"], text=True, timeout=20).strip(),
    "prepared_tree": source_identity["prepared_tree"],
    "prepared_diff_sha256": digest(EVIDENCE/"source-preparation.diff"),
    "free_bytes_after": shutil.disk_usage(ROOT).free,
    "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
print((EVIDENCE/"BUILD_ONLY_RESULT.json").read_text(), flush=True)


# Final transport occurs after the last original command, including the destination observation.
# The coordinator requires exact final byte lengths and SHA256 for both live raw logs.
for name in ("commands.jsonl", "source-identity.json", "source-preparation.diff",
             "build.command.json", "BUILD_ONLY_RESULT.json", "host-preparation.json",
             "canonical-runtime-resource-stage.json", "worklets-object-admission.json",
             "consumer-build/producer-manifest.json", "consumer-build/producer-build-receipt.json"):
    path = EVIDENCE / name
    assert path.is_file(), name
    raw = path.read_bytes()
    print("HANLIN_NATIVE_FINAL_FILE\t" + json.dumps({"name": name, "bytes": len(raw),
          "sha256": hashlib.sha256(raw).hexdigest(), "data": base64.b64encode(raw).decode()}), flush=True)
print("HANLIN_NATIVE_FINAL_LOG_HASHES\t" + json.dumps({
    name: {"bytes": (EVIDENCE/name).stat().st_size, "sha256": digest(EVIDENCE/name)}
    for name in ("build.log", "commands.jsonl")}), flush=True)
