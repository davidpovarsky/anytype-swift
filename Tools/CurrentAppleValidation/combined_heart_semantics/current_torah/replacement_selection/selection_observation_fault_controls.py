"""Pure collector fault controls: no native, UIKit, simulator or acceptance execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types
import replacement_selection_observation as observed

sha = lambda value: hashlib.sha256(value).hexdigest()
binding = {"sourceSHA": "0c5ffc51cdeb480194fdd4d5e396a602d04d5d78",
           "runID": "123456", "runAttempt": "1", "nonce": "0" * 32}
state = {"inputIdentity": "ObjectIdentifier(disposable-control)", "firstResponder": True,
         "windowPresent": True, "editable": True, "selectedLength": 6}
trace = dict(binding, protocol="pinkha-heart-semantic-source-entry-observation-v1",
             processID=123, capacityReached=False, originalMountedObserverEnabled=False,
             extraEngineCalls=0, selectionChanges=0, menuDismissals=0, automaticRetries=0,
             events=[{"stage": "source-menu-handler", "uptime": 90, "state": {}},
                     {"stage": "source-menu-input", "uptime": 105, "state": state},
                     {"stage": "input-edit-menu-will-present", "uptime": 106, "state": state}])
witness = dict(binding, protocol="heart-semantic-source-real-replacement-selection-v1",
               selectionStartedUptime=100, beforeTypingUptime=110, expectedUTF16Length=6,
               expectedTextSHA256=sha(b"Anchor"), realCommandA=True, programmaticSelectionChanges=0)
def require(value, message):
    if not value:
        raise ValueError(message)
class Policy:
    def attachment(self, directory, prefix, selector, device, maximum):
        values = {
            "heart-semantic-source-replacement-selection": json.dumps(witness).encode(),
            "heart-semantic-source-replacement-selection-ax":
                b"Application, synthetic, pid: 123\n TextView, frame, value: Anchor, Keyboard Focused\n",
            "heart-semantic-source-replacement-selection-visual": b"synthetic visual control only"
        }
        return values[prefix], {"pureControl": True}
def run():
    cases = {}
    def evaluate(value):
        c = types.SimpleNamespace(require=require, sha=sha, decode=json.loads,
             STAGES={"linked-ui": "original/linked"}, app_file=lambda *a, **kw: json.dumps(value).encode())
        return observed.qualify_selection(c, Policy(), None, Path("/unused"), Path("/unused"),
                                          "synthetic-device", binding, binding)
    result = evaluate(copy.deepcopy(trace))
    assert result["locationZeroEvidence"] == "INFERRED_FROM_NATIVE_FULL_LENGTH_AND_EXACT_FOCUSED_AX_VALUE"
    cases["completeSyntheticWitness"] = "PASS_PURE_CONTROL_NOT_NATIVE_ACCEPTANCE"
    for name, changed in (
        ("differentInputIdentity", dict(state, inputIdentity="ObjectIdentifier(other)")),
        ("missingInputIdentity", {k:v for k,v in state.items() if k != "inputIdentity"}),
        ("collapsedRange", dict(state, selectedLength=0)),
    ):
        value = copy.deepcopy(trace)
        value["events"].append({"stage": "input-edit-menu-will-dismiss", "uptime": 107, "state": changed})
        try:
            evaluate(value)
        except ValueError:
            cases[name] = "PASS_REQUIRED_REFUSAL"
        else:
            raise AssertionError("false PASS for " + name)
    value = copy.deepcopy(trace)
    value["events"].append({"stage": "input-resign-before", "uptime": 107, "state": state})
    try:
        evaluate(value)
    except ValueError:
        cases["resignationBeforeTyping"] = "PASS_REQUIRED_REFUSAL"
    else:
        raise AssertionError("false PASS for resignation")
    return {"scope": "PURE_COLLECTOR_CONTROLS_ONLY", "cases": cases, "nativeCalls": 0,
            "simulatorCalls": 0, "actualUIOrNativeAcceptance": False,
            "observerSHA256": sha(Path(observed.__file__).read_bytes())}
if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
