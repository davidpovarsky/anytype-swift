"""Seven new Heart acknowledgement cases, reusing the SDK06 Debug build.

The explicit lane alias opts into these new cases once. The original
hanlin-native lane keeps its selection, so later UI-only work need not repeat
already qualified component evidence.
"""
import hashlib
import re
import subprocess

LANE = "hanlin-native-text-ack"
BASE_LANE = "hanlin-native"
SUITE = "PinkhaNativeTextAcknowledgementTests"
METHOD_NAMES = (
    "unchangedNativeSnapshotDoesNotWrite",
    "optimisticFailureRequiresNativeRetry",
    "canonicallyEquivalentUTF8RequiresNativeWrite",
    "identicalInFlightCallbackWaitsForTheNativeResult",
    "laterTextIsSerializedAfterFailedNativeWrite",
    "queuedReversalPreservesTheFinalAcceptedText",
    "failedPayloadDoesNotRewriteANewRemoteValue",
)
METHODS = [SUITE + "/" + name for name in METHOD_NAMES]

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def resolve_lane(requested):
    return (BASE_LANE, True) if requested == LANE else (requested, False)

def validate_source(text):
    declarations = re.findall(r"@Test(?:\(([^\n]*)\))?\s+func\s+(\w+)\s*\(([^)]*)\)", text)
    require(len(declarations) == len(METHOD_NAMES)
            and {name for _, name, _ in declarations} == set(METHOD_NAMES),
            "The seven native-ack component declarations changed")
    require(all(not parameters.strip() and "arguments:" not in attributes
                for attributes, _, parameters in declarations),
            "Native-ack cases must be the seven reviewed nonparameterized methods")
    return METHODS.copy()

def source_contract(app):
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    expected = "AnytypeTests/Pinkha/" + SUITE + ".swift"
    candidates = [name for name in tracked if name.casefold() == expected.casefold()]
    require(len(candidates) == 1, "Missing or case-colliding native-ack test source")
    actual, synced = app / candidates[0], app / expected
    require(synced.is_file() and actual.samefile(synced),
            "Native-ack test source is absent from the Xcode synchronized root")
    data = actual.read_bytes()
    methods = validate_source(data.decode("utf-8"))
    return {"path": candidates[0], "sha256": hashlib.sha256(data).hexdigest(),
            "methods": methods, "expected_methods": len(methods),
            "scope": "CONTROLLED_NATIVE_SERVICE_COMPONENTS"}

def qualify_result(result):
    require(result.get("status") == "PASS"
            and all(type(result.get(key)) is int for key in ("passed", "failed", "skipped"))
            and result["passed"] == len(METHODS)
            and result.get("failed") == 0 and result.get("skipped") == 0
            and result.get("selected") == METHODS,
            "Actual native-ack result differs from the exact seven-method selection")
    actual = result.get("actual_methods", {})
    require(isinstance(actual, dict) and len(actual) == len(METHODS)
            and {name.removesuffix("()") for name in actual} == set(METHODS)
            and set(actual.values()) == {"Passed"},
            "Missing, extra or nonpassing native-ack method result")
    return {"status": "TEXT_NATIVE_ACK_COMPONENT_PASS", "actual_methods": actual,
            "passed": len(METHODS), "failed": 0, "skipped": 0,
            "real_native_persistence_accepted": False,
            "limitations": ["Controlled native service responses; real engine and UI acceptance are separate."]}
