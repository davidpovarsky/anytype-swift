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
assert head(ROOT) == "308c5ab3934168a6cbecbcc1f8aee9221eb8748c"
helper = SHARED / "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py"
assert sha(helper) == "9169a1cdbd1e5c49b5f7a4b49e125e902a20e00627f2a8b0ae0dc866ec685468"
import sdk06_enumeration_probe
import test_mounted_contract
methods = [
"test_copied_selector_and_binding_preserve_original_host_and_testing_environment",
"test_descriptor_hash_and_explicit_injection_absence_are_admitted_before_copy",
"test_native_plan_identity_and_observed_unnamed_ui_plan_cannot_weaken_exact_selection",
"test_pinned_injection_relocates_only_one_token_and_reverses_all_other_fields",
"test_v1_ui_exact_single_blueprint_preserves_format_and_rejects_named_or_ambiguous_shapes",
]
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
save("source-before.json", loaded)
save("command.json", dict(argv=[sys.executable, "-B", str(Path(__file__).resolve())],
    python=sys.version, platform=platform.platform(), source_sha=head(ROOT),
    external_helper_source_sha=head(SHARED), consumer_helper_source_sha=head(CONSUMER),
    module_search_paths=sys.path[:5], exact_methods=methods, retained_old_methods_not_run=9,
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
    ["test_mounted_contract.MountedControllerControls." + name for name in methods])
assert suite.countTestCases() == 5
started = time.monotonic()
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(suite)
save("events.json", events)
after = {name: dict(row, sha256=sha(Path(row["path"])), bytes=Path(row["path"]).stat().st_size)
    for name, row in loaded.items()}
save("source-after.json", after)
unchanged = after == loaded and head(ROOT) == "308c5ab3934168a6cbecbcc1f8aee9221eb8748c"
save("result.json", dict(status="PASS_CONTROLLER_CONTROLS" if result.wasSuccessful() and unchanged else "FAIL",
    started=5, passed=sum(row["action"] == "pass" for row in events), failures=len(result.failures),
    errors=len(result.errors), skipped=len(result.skipped), elapsed_seconds=time.monotonic()-started,
    source_unchanged=unchanged, source_sha=head(ROOT), methods=methods, affected_original_methods=1,
    new_methods=4, retained_original_methods_not_run=9, current_distinct_catalog=14,
    native_test_executions=0, app_builds=0, apple_method_executions=0, mounted_acceptance="NOT_RUN",
    finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
sys.exit(0 if result.wasSuccessful() and unchanged else 1)
