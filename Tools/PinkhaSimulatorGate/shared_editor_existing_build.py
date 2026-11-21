"""Run the unchanged ten-method retained UIKit profile in the SDK06 build.

The profile's original declaration and parameter-case validators remain the
authority. This wrapper consumes only the current job's already verified app
and test products; it does not create or restore another application build.
"""
import json
from pathlib import Path
import sys

HANLIN_TOOLS = Path(__file__).resolve().parents[1] / "Hanlin"
if str(HANLIN_TOOLS) not in sys.path:
    sys.path.insert(0, str(HANLIN_TOOLS))
import run_host_tests as host

LANE = "hanlin-native-shared-editor"
PROFILE = host.HostTestProfile.SHARED_EDITOR
SUITE = "TextBlockFocusLifecycleTests"

def source_contract(app):
    expected, hashes = host.expected_methods(app, PROFILE)
    host.require(len(expected) == 10, "The existing ten-method shared-editor selection changed")
    return {"methods": sorted(expected), "source_hashes": hashes,
            "expected_methods": 10, "declared_invocations": 15,
            "profile": PROFILE.value}

def execute(app, configuration, udid, expected_app, evidence, shared):
    host.require(not evidence.exists() or not any(evidence.iterdir()),
                 "Refuse stale shared-editor component evidence")
    evidence.mkdir(parents=True, exist_ok=True)
    source = source_contract(app)
    built, app_executable, test_bundle, test_executable = host.xctest_products(configuration)
    host.require(built.resolve() == expected_app.resolve(),
                 "Shared-editor components must use the SDK06 app build")
    hashes = {"app_executable": shared.digest(app_executable),
              "test_executable": shared.digest(test_executable),
              "xctestrun": shared.digest(configuration)}
    bundle = evidence / "SharedEditor.xcresult"
    command = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
               "-destination", "platform=iOS Simulator,id=" + udid,
               "-parallel-testing-enabled", "NO",
               "-only-testing:AnytypeTests/" + SUITE,
               "-resultBundlePath", str(bundle)]
    receipt = {"status": "FAIL", "phase": "EXECUTION", "profile": PROFILE.value,
               "build_mode": "SAME_JOB_EXISTING_SDK06_BUILD", "additional_app_builds": 0,
               "source": source, "built_products": hashes, "command": command}
    shared.write(evidence / "execution.json", receipt)
    try:
        shared.run_xctest(command, app, evidence, bundle, PROFILE.result_prefix,
                          command_runner=host.command)
        summary_path = evidence / (PROFILE.result_prefix + "-summary.json")
        tree_path = evidence / (PROFILE.result_prefix + "-tests.json")
        actual = host.validate_results(json.loads(summary_path.read_text()),
                                       json.loads(tree_path.read_text()),
                                       set(source["methods"]), udid, PROFILE)
        host.require(source_contract(app) == source, "Shared-editor source changed during execution")
        host.require(shared.digest(app_executable) == hashes["app_executable"]
                     and shared.digest(test_executable) == hashes["test_executable"]
                     and shared.digest(configuration) == hashes["xctestrun"],
                     "Shared-editor built products changed during execution")
        receipt.update(status=PROFILE.pass_status, phase="COMPLETE", actual=actual,
                       raw_summary_sha256=shared.digest(summary_path),
                       raw_tests_sha256=shared.digest(tree_path),
                       real_native_persistence_accepted=False)
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        shared.write(evidence / "execution.json", receipt)
    return receipt
