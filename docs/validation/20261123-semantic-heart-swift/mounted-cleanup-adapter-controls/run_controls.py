from pathlib import Path
import datetime, hashlib, json, platform, subprocess, sys, time, unittest

ROOT = Path("/mnt/development/projects/worktrees/anytype-wave15-semantic-swift-20261123")
SHARED = Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
CONSUMER = Path("/mnt/development/projects/worktrees/anytype-wave15-semantic-apple-consumer-20261123")
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "Tools/PinkhaSemanticAnchorWire/apple_mounted"),
    str(CONSUMER / "Tools/PinkhaSemanticAnchorWire/apple_consumer"),
    str(SHARED / "Tools/PinkhaSimulatorGate"), str(SHARED / "Tools/Hanlin"),
    str(SHARED / "Tools/PinkhaNativeDerived")]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value): (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def head(root): return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
assert head(ROOT) == "bc29685e6fdd842023b9045908d9c5622827dfc8"
helper = SHARED / "Tools/AnyEngineValidation/prepared_inline_file_apple/cleanup.py"
assert sha(helper) == "14fa818cdf6c2cf8b7b1f78c075bad8e98240bf1f40d2d50acf6fb3c5fd74cc6"
import test_mounted_cleanup
methods = ['test_qualified_policy_body_is_identical_and_import_names_remain_scoped', 'test_tuple_path_adapter_retains_original_timeout_and_prior_product_failure', 'test_incomplete_command_records_or_quiescence_never_turn_cleanup_into_pass', 'test_recovered_creation_owner_is_bound_to_exact_original_command_and_log']

loaded = {}
for name, module in list(sys.modules.items()):
    raw = getattr(module, "__file__", None)
    if raw:
        path = Path(raw).resolve()
        if path.is_file() and path.is_relative_to(Path("/mnt/development/projects/worktrees")):
            loaded[name] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)
for relative in ["Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py",
                 "Tools/PinkhaSemanticAnchorWire/apple_mounted/README.md",
                 "Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json"]:
    path = ROOT / relative
    loaded[relative] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)
loaded["qualified_original_inline_cleanup"] = dict(path=str(helper), sha256=sha(helper), bytes=helper.stat().st_size)
save("source-before.json", loaded)
save("command.json", dict(argv=[sys.executable, "-B", str(Path(__file__).resolve())],
    python=sys.version, platform=platform.platform(), source_sha=head(ROOT),
    external_helper_source_sha=head(SHARED), consumer_helper_source_sha=head(CONSUMER),
    module_search_paths=sys.path[:5], exact_methods=methods, retained_mounted_methods_not_run=14, retained_policy_methods_not_run=9,
    product_tests=0, app_builds=0, native_builds=0, xcodebuild_commands=0))
events = []
class Result(unittest.TextTestResult):
    def startTest(self, test):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(), action="start", test=test.id()))
        super().startTest(test)
    def addSuccess(self, test):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(), action="pass", test=test.id()))
        super().addSuccess(test)
    def addFailure(self, test, err):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(), action="fail", test=test.id()))
        super().addFailure(test, err)
    def addError(self, test, err):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(), action="error", test=test.id()))
        super().addError(test, err)

suite = unittest.defaultTestLoader.loadTestsFromNames(
    ["test_mounted_cleanup.MountedCleanupAdapterControls." + name for name in methods])
assert suite.countTestCases() == 4
started = time.monotonic()
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(suite)
save("events.json", events)
after = {name: dict(row, sha256=sha(Path(row["path"])), bytes=Path(row["path"]).stat().st_size)
    for name, row in loaded.items()}
save("source-after.json", after)
unchanged = after == loaded and head(ROOT) == "bc29685e6fdd842023b9045908d9c5622827dfc8"
save("result.json", dict(status="PASS_CONTROLLER_CONTROLS" if result.wasSuccessful() and unchanged else "FAIL",
    started=4, passed=sum(row["action"] == "pass" for row in events), failures=len(result.failures),
    errors=len(result.errors), skipped=len(result.skipped), elapsed_seconds=time.monotonic()-started,
    source_unchanged=unchanged, source_sha=head(ROOT), methods=methods, affected_original_methods=0,
    new_methods=4, retained_mounted_methods_not_run=14, retained_policy_methods_not_run=9, current_adapter_catalog=4,
    native_test_executions=0, app_builds=0, apple_method_executions=0, mounted_acceptance="NOT_RUN",
    finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
sys.exit(0 if result.wasSuccessful() and unchanged else 1)
