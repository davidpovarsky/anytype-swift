"""Pure original F/T5 selection, language and lifecycle rejection controls. No Apple acceptance."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import types

def require(value, message):
    if not value:
        raise ValueError(message)

def extract(source, names, namespace):
    module = ast.parse(source)
    selected = [n for n in module.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in selected} == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<exact-qualified-original-functions>", "exec"), namespace)
    return namespace

def main():
    directory = Path(__file__).parent
    repo = directory.parents[3]
    commit = "0c5ffc51cdeb480194fdd4d5e396a602d04d5d78"
    source = lambda name: subprocess.check_output(["git", "-C", str(repo), "show", commit + ":" + name], timeout=30).decode()
    common = {"require": require}
    extract(source("Tools/PinkhaSimulatorGate/validate_release.py"), ["method_results"], common)
    extract(source("Tools/PinkhaSimulatorGate/t5_native_ui_evidence.py"), ["validate_selection"], common)
    extract(source("Tools/PinkhaSimulatorGate/run_wave15_acceptance.py"), ["nonempty", "fixture_environment"], common)
    control = (directory / "combined_host_acceptance_current.py").read_text()
    shared = types.SimpleNamespace(OS_VERSION="27.0", OS_BUILD="24A434", error=lambda e: {"type": type(e).__name__, "message": str(e)})
    namespace = {"require": require, "shared": shared, "NATIVE": "AnytypeTests"}
    extract(control, ["exact_enumeration", "result_selection", "invocation_selectors"], namespace)
    methods = ["PinkhaStage1AcceptanceUITests/" + n for n in (
        "testAppWideDirectionPersistenceAndInteractiveBack", "testMultiBlockEnterCreationAndTypingLifecycle",
        "testDocumentSourcesEntryOpensExistingSearch", "testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen")]
    selectors = ["PinkhaStage1AcceptanceUITests/" + n for n in methods]
    enumeration = {"errors": [], "values": [{"enabledTests": [{"identifier": n} for n in methods], "disabledTests": []}]}
    cases = {}
    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, AssertionError):
            cases[name] = "PASS_REQUIRED_REFUSAL"
        else:
            raise AssertionError("False acceptance: " + name)
    namespace["exact_enumeration"](enumeration, selectors)
    cases["completeOriginalEnumeration"] = "PASS_PURE_CONTROL"
    for name, change in (
        ("missingCompiledMethod", lambda j: j["values"][0]["enabledTests"].pop()),
        ("extraCompiledMethod", lambda j: j["values"][0]["enabledTests"].append({"identifier": "Other/test"})),
        ("duplicateCompiledMethod", lambda j: j["values"][0]["enabledTests"].append(j["values"][0]["enabledTests"][0])),
        ("disabledSelectedMethod", lambda j: j["values"][0]["disabledTests"].append(j["values"][0]["enabledTests"][0])),
        ("enumerationErrors", lambda j: j["errors"].append("actual compilation refused")),
        ("multipleConfigurations", lambda j: j["values"].append(copy.deepcopy(j["values"][0]))),
    ):
        value = copy.deepcopy(enumeration); change(value)
        reject(name, lambda value=value: namespace["exact_enumeration"](value, selectors))
    qualified = copy.deepcopy(enumeration)
    qualified["values"][0]["enabledTests"] = [{"identifier": n} for n in selectors]
    namespace["exact_enumeration"](qualified, selectors)
    cases["fullTargetClassMethodEnumeration"] = "PASS_PURE_CONTROL"
    for name, change in (
        ("foreignEnumerationTarget", lambda j: j["values"][0]["enabledTests"][0].update(identifier="OtherTarget/" + methods[0])),
        ("canonicalDuplicateAlias", lambda j: j["values"][0]["enabledTests"].append({"identifier": selectors[0]})),
        ("disabledCanonicalAlias", lambda j: j["values"][0]["disabledTests"].append({"identifier": selectors[0]})),
    ):
        value = copy.deepcopy(enumeration); change(value)
        reject(name, lambda value=value: namespace["exact_enumeration"](value, selectors))
    # The original parameterized method must remain selected and validated;
    # only Xcode invocation filtering uses the already source-validated suite.
    host = "AnytypeTests/TorahRelatedDocumentActionTests/"
    host_selectors = [host + str(i) + "()" for i in range(10)] + [host + "lateUnlinkFailureIsIgnoredAfterDocumentLifetimeEnds(isNote:)"]
    contract = {"expected_methods":11, "declared_cases":12, "compiled_identifiers":sorted(host_selectors)}
    assert namespace["invocation_selectors"](host_selectors, contract) == [host.rstrip("/")]
    assert namespace["invocation_selectors"](selectors) == selectors
    cases["originalCompleteHostSuiteFilter"] = "PASS_PURE_CONTROL"
    for name, change in (
        ("hostContractMissingMethod", lambda c:c["compiled_identifiers"].pop()),
        ("hostContractReducedCaseCount", lambda c:c.update(declared_cases=11)),
        ("hostContractReducedMethodCount", lambda c:c.update(expected_methods=10)),
    ):
        c=copy.deepcopy(contract);change(c)
        reject(name,lambda c=c:namespace["invocation_selectors"](host_selectors,c))
    missing_parameter = {"errors":[],"values":[{"testPlan":"AnytypeTests",
        "enabledTests":[{"identifier":n} for n in host_selectors[:-1]],
        "disabledTests":[{"identifier":host_selectors[-1]}]}]}
    reject("parameterizedHostMethodStillRequired",lambda:namespace["exact_enumeration"](missing_parameter,host_selectors))
    tree = [{"nodeType": "Test Case", "nodeIdentifier": n + "()", "result": "Passed"} for n in methods]
    device = {"deviceId": "pure-control-device", "architecture": "arm64", "osVersion": "27.0",
              "osBuildNumber": "24A434", "platform": "iOS Simulator"}
    summary = {"totalTestCount": 4, "passedTests": 4, "failedTests": 0, "skippedTests": 0,
               "devicesAndConfigurations": [{"device": device}]}
    helpers = {"run_ui27": types.SimpleNamespace(method_results=common["method_results"]),
               "t5_native_ui_evidence": types.SimpleNamespace(validate_selection=common["validate_selection"])}
    call_result = lambda s,t: namespace["result_selection"](s,t,selectors,"pure-control-device",helpers)
    call_result(summary, tree); cases["completeOriginalResult"] = "PASS_PURE_CONTROL"
    for name, mutate in (
        ("missingActualMethod", lambda s,t: t.pop()),
        ("duplicateActualMethod", lambda s,t: t.append(copy.deepcopy(t[0]))),
        ("skippedMethod", lambda s,t: s.update(skippedTests=1, passedTests=3)),
        ("failedMethod", lambda s,t: t[0].update(result="Failed")),
        ("extraActualMethod", lambda s,t: t.append({"nodeType":"Test Case","nodeIdentifier":"Other/test()","result":"Passed"})),
        ("zeroActualCounts", lambda s,t: s.update(totalTestCount=0, passedTests=0)),
        ("wrongDevice", lambda s,t: s["devicesAndConfigurations"][0]["device"].update(deviceId="another")),
        ("wrongRuntimeBuild", lambda s,t: s["devicesAndConfigurations"][0]["device"].update(osBuildNumber="other")),
    ):
        s,t = copy.deepcopy(summary),copy.deepcopy(tree);mutate(s,t)
        reject(name, lambda s=s,t=t:call_result(s,t))
    fixture = {"spaceId":"space", "pinkhaObjectId":"pinkha", "noteObjectId":"note", "pageObjectId":"page"}
    common["fixture_environment"]("editor", fixture, "he", "en")
    cases["observedOppositeLanguage"] = "PASS_PURE_CONTROL"
    reject("sameDeviceLanguage", lambda:common["fixture_environment"]("editor", fixture, "he", "he"))
    reject("unobservedDeviceLanguage", lambda:common["fixture_environment"]("editor", fixture, "he", None))
    # Execute the actual consumer's failure cleanup with local inert doubles;
    # no process, simulator or application operation is made by this control.
    namespace.update(Path=Path, time=time, UI="PinkhaStage1AcceptanceUITests",
                     write=lambda p,v:p.write_text(json.dumps(v)))
    extract(control, ["Consumer"], namespace)
    with tempfile.TemporaryDirectory(prefix="pinkha-f-lifecycle-control-") as temporary:
        consumer = namespace["Consumer"].__new__(namespace["Consumer"])
        consumer.root = Path(temporary)
        consumer.binding = {"sourceSHA":commit}
        consumer.devices = ["prior-owned-device"]
        consumer.built = {}
        consumer.invoked_devices = set()
        preserved,commands = [],[]
        def create_then_fail(lane, directory, editor=False):
            consumer.devices.append("new-owned-device")
            raise ValueError("owned boot failed before create returns")
        consumer.create = create_then_fail
        consumer.preserve = lambda device,*args:preserved.append(device) or {"pureControl":True}
        consumer.command = lambda argv,*args,**kw:commands.append(argv) or (None,{})
        outcome = consumer.execute_lane("editor")
        assert outcome["status"] == "FAIL" and preserved == ["new-owned-device"]
        assert commands == [["xcrun","simctl","shutdown","new-owned-device"]]
        cases["ownedCreateFailureRetained"] = "PASS_PURE_CONTROL_NO_SIMULATOR"
        invoked = namespace["Consumer"].__new__(namespace["Consumer"])
        invoked.invoked_devices = {"invoked-device"}
        def missing_container(device,kind,label,required):
            assert required is True
            raise ValueError("missing actual invoked account must fail")
        invoked.container = missing_container
        directory = Path(temporary)/"missing-account";directory.mkdir()
        reject("invokedMissingAccountRefused", lambda:invoked.preserve("invoked-device",directory,"editor"))
    extract(control, ["observe_owned_groups"], namespace)
    calls = []
    command_double = types.SimpleNamespace(groups=[111, 222], absent_groups={111},
        present=lambda group: calls.append(group) or False)
    observed = namespace["observe_owned_groups"](command_double)
    assert observed["status"] == "PASS" and calls == [222] and command_double.absent_groups == {111, 222}
    cases["knownAbsentGroupNeverReprobed"] = "PASS_PURE_CONTROL_NO_PROCESSES"
    def denied(group):
        raise PermissionError("controlled observation denial")
    command_double = types.SimpleNamespace(groups=[333], absent_groups=set(), present=denied)
    observed = namespace["observe_owned_groups"](command_double)
    assert observed["status"] == "FAIL" and observed["errors"][0]["type"] == "PermissionError"
    cases["permissionErrorRetainsTerminalFailure"] = "PASS_REQUIRED_REFUSAL"
    command_double = types.SimpleNamespace(groups=[444], absent_groups=set(), present=lambda group:True)
    assert namespace["observe_owned_groups"](command_double)["status"] == "FAIL"
    cases["unresolvedOwnedGroupRefusesAcceptance"] = "PASS_REQUIRED_REFUSAL"
    result = {"status":"PASS_CURRENT_HOST_NEGATIVE_CONTROLS_NOT_APPLE_ACCEPTANCE", "cases":cases,
              "actualAppleTests":0,"simulatorsCreated":0,"engineCalls":0,
              "controllerSHA256":hashlib.sha256(control.encode()).hexdigest(),
              "originalFirstEditorMethods":methods}
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__ == "__main__":
    main()
