"""Explicit Page154 simulator policy bound to a previously executed iPad pair.

The original lane failed its separate runtime-observation gate. Its native and
UI methods nevertheless ran successfully on this exact runtime/device pair.
The old UUID is provenance only; the consumer still creates a fresh simulator.
"""
from __future__ import annotations

import simulator_selection

POLICY = "page154-observed-ipad27-m5-16gb-v1"
RUNTIME_ID = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
RUNTIME_VERSION = "27.0"
RUNTIME_BUILD = "24A434"
DEVICE_ID = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB"
DEVICE_NAME = "iPad Pro 13-inch (M5) (16GB)"
MODEL_ID = "iPad17,4"
ARCHITECTURE = "arm64"
ORIGIN = {
    "runID": "45096079315",
    "runAttempt": "1",
    "sourceSHA": "d254a4a1ccd9288f585ff9374088cbaf965b36b4",
    "originalLaneConclusion": "FAIL",
    "artifactID": "14784114263",
    "artifactSHA256": "02b180cd51bf905161c7254c9daa41430de46803290df9cfc3e6eb20ba636f5d",
    "preflightPath": "preflight/preflight.json",
    "preflightSHA256": "277d97e146ad951da127bb4ee339c32079ce5ecf434047118bd98df38d39a349",
    "executionPath": "execution.json",
    "executionSHA256": "439507093898b297b5b007c69fc885ddf7baf95fcc67fa7aa5e9101a4ffd9426",
    "originalSimulatorUDID": "6BA9F042-CEB5-49CF-9301-D8395698D8A5",
    "nativeMethodsPassed": 1,
    "uiMethodsPassed": 1,
    "scope": "Observed pair compatibility; current Page154 execution remains separately required.",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def choose_pair(runtime_inventory, device_inventory):
    """Admit this one installed pair, with no alternate selection or fallback."""
    require(isinstance(runtime_inventory, dict) and isinstance(device_inventory, dict),
            "Page154 simulator inventories must be objects")
    # Validate the complete original inventories before restricting the policy.
    # Duplicated identities must never be hidden by filtering.
    runtimes = simulator_selection._unique(runtime_inventory.get("runtimes"), "runtimes")
    devices = simulator_selection._unique(device_inventory.get("devicetypes"), "device types")
    require(RUNTIME_ID in runtimes and DEVICE_ID in devices,
            "The explicitly observed Page154 simulator pair is not installed")
    runtime, device = runtimes[RUNTIME_ID], devices[DEVICE_ID]
    require(runtime.get("version") == RUNTIME_VERSION
            and runtime.get("buildversion") == RUNTIME_BUILD
            and runtime.get("platform") == "iOS"
            and runtime.get("isInternal") is False,
            "The explicitly observed Page154 runtime version/build/platform changed")
    require(device.get("name") == DEVICE_NAME and device.get("modelIdentifier") == MODEL_ID
            and device.get("productFamily") == "iPad",
            "The explicitly observed Page154 device identity changed")
    for label in ("minRuntimeVersion", "maxRuntimeVersion"):
        value = device.get(label)
        require(type(value) is int
                and simulator_selection._version(device.get(label + "String"))[1] == value,
                "Installed Page154 device numeric/text runtime bounds disagree")
    pair = simulator_selection.choose_pair(
        {"runtimes": [runtime]}, {"devicetypes": [device]},
        product_family="iPad", major=27, architecture=ARCHITECTURE)
    require(pair["selection"]["runtimeIdentifier"] == RUNTIME_ID
            and pair["selection"]["deviceTypeIdentifier"] == DEVICE_ID,
            "Page154 simulator policy selected an unreviewed alternate")
    pair["selection"]["selectionPolicy"] = POLICY
    pair["selection"]["observedPairProvenance"] = dict(ORIGIN)
    return pair
