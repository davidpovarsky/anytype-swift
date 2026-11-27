"""Finite source-bound T5 successor. No caller flag can open this profile."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

PREFIX = "Tools/PinkhaDualEngineRuntime/hosted_t5/"
MANIFEST_SHA256 = "1807a0aab8d76b53691a9e97a58339c251263a8f42377ef6d5f7166ed855df77"
# Replaced only by the source-packaging step, not by runtime input.
ACTIVATION_SHA256 = "9b0704f98a73e5586636050c8701c554ea6abf1b14689fda3d192a272fefa4b2"
PROFILE = "dual-engine-runtime-v1"
CAPABILITY = "Modules/PinkhaKit/Sources/PinkhaKit/Torah/T5NativeRelatedLookupCapability.swift"
T5_UI = "PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift"
PREPARATION = "AnyTypeTests/Pinkha/TorahT5UIAcceptancePreparationTests.swift"
FRESHNESS = "AnyTypeTests/Pinkha/TorahT5RuntimePairTests.swift"
PLANS = (
    ("t5-native-ui-only", "t5-native-ui", "native_ui"),
    ("t5-remaining-freshness-only", "t5-remaining-freshness", "freshness"),
)
METHODS = (
    "AnytypeTests/TorahT5UIAcceptancePreparationTests/prepareFreshNativeUIFixture()",
    "PinkhaStage1AcceptanceUITests/PinkhaT5NativeAcceptanceUITests/testCurrentSpaceRowsAndExactBlockNavigation",
    "PinkhaStage1AcceptanceUITests/PinkhaT5NativeAcceptanceUITests/testAddNoteEditOpenUnlinkAndRetainAfterRelaunch",
    "PinkhaStage1AcceptanceUITests/PinkhaT5NativeAcceptanceUITests/testHebrewRelatedRowsLongTitlesAndReadOnlyNavigation",
    "AnytypeTests/TorahT5RemainingFreshnessTests/nativeQuoteMoveAndBlockDeletion()",
)
DEPENDENCIES = {
    "admission": ("Tools/PinkhaDualEngineRuntime/hosted_core13/admission.py", "11dc47753d6011de6fba8955239a6b63f5fde919b8a7d8edbb2dec75ccfaeb76"),
    "originals": ("Tools/PinkhaDualEngineRuntime/hosted_core13/originals.py", "adc29fa18b2bd64dce6bca3cf6ded88ae6203246a12fa7e781229fda41b1f326"),
    "hosted_t5_core_lifetime": ("Tools/PinkhaDualEngineRuntime/hosted_core13/run.py", "cf16f08fefcc0d639e1f924a230c2fefb8bcc7af4f311e9e03191165908a29c8"),
    # This exact shared file-only reader is a pending root-reviewed dependency;
    # it never configures or executes the separate Native23 runner.
    "hosted_t5_native23_receipts": ("Tools/PinkhaDualEngineRuntime/hosted_property_cache_bin/native23_receipts.py", "94b947f1210b3affc3be5a7f54e09420aeef6c81400c8f5be504d3ca7e4cb89e"),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(data):
    def object_pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, "Duplicate JSON key")
            value[key] = item
        return value
    def nonfinite(_):
        raise ValueError("Nonfinite JSON value")
    return json.loads(data, object_pairs_hook=object_pairs, parse_constant=nonfinite)


def activation(root):
    path = Path(root) / PREFIX / "activation.json"
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and digest(path) == ACTIVATION_SHA256, "Exact source-bound T5 activation required")
    value = strict_json(path.read_bytes())
    require(value["schema"] == "pinkha-hosted-t5-closed-activation-v1", "Unknown T5 activation")
    require(value["readyForRuntime"] is True and value["finalProducerTuple"] is not None,
            "T5 is CLOSED: final native/product/runtime identity has not been selected")
    require(value["plans"] == [row[0] for row in PLANS]
            and value["startupSeconds"] == 120 and value["methodCount"] == 5
            and value["executionCount"] == 6 and value["compiledSourceCounts"] == [61, 10, 2],
            "Only the two original fresh plans and exact source counts may run")
    final = value["finalProducerTuple"]
    require(set(final) == {"appSourceSHA", "appSourceTree", "nativeRuntimeVersion", "nativeSourceManifestSHA256",
            "nativeBinarySHA256", "assemblyReceiptSHA256", "sdkRevision", "sdkReceiptSHA256", "packageResolvedSHA256",
            "capabilitySourceSHA256", "nodeIdentity"}, "Unknown or incomplete final producer tuple")
    for key in ("appSourceSHA", "appSourceTree", "sdkRevision"):
        require(re.fullmatch(r"[a-f0-9]{40}", final[key]), "Exact immutable source identity required")
    for key in ("nativeSourceManifestSHA256", "nativeBinarySHA256", "assemblyReceiptSHA256", "sdkReceiptSHA256",
                "packageResolvedSHA256", "capabilitySourceSHA256"):
        require(re.fullmatch(r"[a-f0-9]{64}", final[key]), "Exact original final digest required")
    require(final["nativeRuntimeVersion"] == "pinkha-dual-runtime-v1-" + final["nativeSourceManifestSHA256"],
            "Final runtime must be derived from the exact admitted original native manifest")
    node = final["nodeIdentity"]
    require(set(node) == {"executable", "executableSHA256", "nodeVersion", "opensslVersion", "platform", "machine", "macOS", "images"}
            and Path(node["executable"]).is_absolute() and re.fullmatch(r"[a-f0-9]{64}", node["executableSHA256"])
            and re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", node["nodeVersion"])
            and isinstance(node["opensslVersion"], str) and node["opensslVersion"]
            and node["platform"] == "darwin" and node["machine"] == "arm64"
            and re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,2}", node["macOS"])
            and isinstance(node["images"], list) and 0 < len(node["images"]) <= 128, "Actual pinned Node runtime required")
    require(node["images"] == sorted(node["images"], key=lambda row: row["path"])
            and len({row["path"] for row in node["images"]}) == len(node["images"])
            and all(set(row) == {"path", "resolvedPath", "bytes", "sha256"} and Path(row["path"]).is_absolute()
                    and row["path"] == row["resolvedPath"] and type(row["bytes"]) is int and row["bytes"] > 0
                    and re.fullmatch(r"[a-f0-9]{64}", row["sha256"]) for row in node["images"])
            and any(row["path"] == node["executable"] and row["sha256"] == node["executableSHA256"] for row in node["images"]),
            "Full actual non-system Node/libnode/libcrypto image closure required")
    return value


def qualify_final(value, plan, context, originals):
    """Runtime admission never substitutes metadata for actual compiled input."""
    final = value["finalProducerTuple"]
    require((plan["appSourceSHA"], plan["appSourceTree"], plan["hanlinRevision"])
            == (final["appSourceSHA"], final["appSourceTree"], final["sdkRevision"]), "Final source/SDK tuple differs")
    inputs = context["build"]["inputs"]
    for actual, expected in (("nativeSourceManifestSHA256", "nativeSourceManifestSHA256"),
                             ("nativeSHA256", "nativeBinarySHA256"), ("sdkReceiptSHA256", "sdkReceiptSHA256"),
                             ("lockSHA256", "packageResolvedSHA256")):
        require(inputs[actual] == final[expected], "Actual compiler input differs from final T5 tuple")
    assembly_path = context["nativeRoot"] / "receipt.json"
    require(digest(assembly_path) == final["assemblyReceiptSHA256"], "Final original native assembly changed")
    assembly = originals.gate.json_ref({"path": str(assembly_path), "sha256": digest(assembly_path)})
    require(assembly["sourceManifestSHA256"] == final["nativeSourceManifestSHA256"]
            and assembly["runtimeIdentity"]["sourceManifestSHA256"] == final["nativeSourceManifestSHA256"]
            and assembly["fullAnyRuntimeVersion"] == final["nativeRuntimeVersion"], "Actual native identity differs")
    capability = context["source"] / CAPABILITY
    require(digest(capability) == final["capabilitySourceSHA256"], "Compiled capability source changed")
    matches = re.findall(r'public static let unifiedRuntimeVersion\s*=\s*"([^"\n]+)"', capability.read_text())
    require(matches == [final["nativeRuntimeVersion"]], "Product capability must be promoted before compilation")
    before = originals.gate.json_ref({"path": str(context["root"] / "build16/source-before.json"),
                                     "sha256": digest(context["root"] / "build16/source-before.json")})
    require(before["files"][CAPABILITY]["sha256"] == final["capabilitySourceSHA256"],
            "Actual producer source manifest does not bind the final product capability")
    for path in (T5_UI, PREPARATION, FRESHNESS):
        pin = originals.proof["files"][path]
        require(before["files"][path]["sha256"] == pin["sha256"], "Actual original T5 source was not bound by the producer")
    require(T5_UI in plan["compilerInputs"]["ui"] and PREPARATION in plan["compilerInputs"]["native"]
            and FRESHNESS in plan["compilerInputs"]["native"], "Original T5 Swift sources must be selected for compilation")
    return {"status": "PASS_EXACT_FINAL_T5_PRODUCT_INPUTS_NOT_RUNTIME", "tuple": final,
            "freshFixtureRequired": True, "oldPreparedFixtureReused": False}
