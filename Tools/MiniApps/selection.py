"""Select exact compiled MiniApps methods without weakening result verification.

Swift Testing methods require their argument list in Xcode 27 selectors.
Semantic method identities remain those in the original five-method profile.
"""
from pathlib import Path
import plistlib
import sys

from acceptance_profile import PREPARE, VERIFY, ADAPTER, UI_RETURN, UI_REPLAY

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/AnyEnginePort"))
from native_ui_transition_contract import enumerated_identifiers

TARGET_METHODS = {
    "AnytypeTests": (PREPARE, VERIFY, ADAPTER),
    "PinkhaStage1AcceptanceUITests": (UI_RETURN, UI_REPLAY),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def selector(target, method):
    require(target in TARGET_METHODS and method in TARGET_METHODS[target],
            "Unknown MiniApps target/method pair")
    return method + ("()" if target == "AnytypeTests" else "")


def configure_tests(original, destination, environment, target, method):
    """Copy and scope the real descriptor; keep original products and skip filters."""
    selected = selector(target, method)
    raw = Path(original).read_bytes()
    data = plistlib.loads(raw)
    version = data.get("__xctestrun_metadata__", {}).get("FormatVersion")
    if version == 2:
        configurations = data.get("TestConfigurations", [])
        require(len(configurations) == 1 and configurations[0].get("IsEnabled", True),
                "Expected one enabled native test configuration")
        targets = configurations[0].get("TestTargets", [])
        matches = [entry for entry in targets if entry.get("BlueprintName") == target]
        require(len(matches) == 1, "Missing or duplicate MiniApps test target")
        entry = matches[0]
        configurations[0]["TestTargets"] = [entry]
    elif version == 1:
        matches = [entry for key, entry in data.items()
                   if key != "__xctestrun_metadata__" and isinstance(entry, dict)
                   and (entry.get("BlueprintName") == target or key == target)]
        require(len(matches) == 1, "Missing or duplicate MiniApps UI target")
        entry = matches[0]
        data = {"__xctestrun_metadata__": data["__xctestrun_metadata__"], target: entry}
    else:
        raise ValueError("Unsupported original xctestrun format")
    require("TestBundlePath" in entry and entry.get("IsEnabled", True),
            "MiniApps test target is missing or disabled")
    entry.setdefault("EnvironmentVariables", {}).update(environment)
    entry["OnlyTestIdentifiers"] = [selected]

    def relocate(value):
        if isinstance(value, dict):
            return {key: relocate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [relocate(item) for item in value]
        if isinstance(value, str):
            return value.replace("__TESTROOT__", str(Path(original).parent))
        return value

    Path(destination).write_bytes(plistlib.dumps(relocate(data)))
    return Path(destination)


def validate_enumeration(payload, target, method):
    selector(target, method)
    plan, enabled, disabled = enumerated_identifiers(payload)
    expected = {target + "/" + method + "()"}
    require(enabled == expected, "Compiled MiniApps selection is not the exact required method")
    if target == "AnytypeTests":
        require(plan == "AnytypeTests", "Original native test plan changed")
    return {"semanticMethod": method, "target": target, "selector": selector(target, method),
            "enabledOriginalIdentifiers": sorted(enabled), "disabledCount": len(disabled),
            "observedTestPlan": plan, "testsExecuted": 0}
