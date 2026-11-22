#!/usr/bin/env python3
"""Choose an explicitly supported installed runtime/device pair, without creating it."""
from __future__ import annotations

import re


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _version(text):
    _require(isinstance(text, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,2}", text),
             "Malformed simulator runtime version")
    parts = tuple(map(int, text.split(".")))
    parts += (0,) * (3 - len(parts))
    _require(0 < parts[0] <= 65535 and all(0 <= value <= 255 for value in parts[1:]),
             "Simulator version cannot be represented by the native runtime bounds")
    return parts, (parts[0] << 16) | (parts[1] << 8) | parts[2]


def _unique(items, label):
    _require(isinstance(items, list), "Missing simulator " + label)
    result = {}
    for value in items:
        _require(isinstance(value, dict), "Malformed simulator " + label)
        identifier = value.get("identifier")
        _require(isinstance(identifier, str) and identifier and identifier not in result,
                 "Missing or repeated simulator identifier in " + label)
        result[identifier] = value
    return result


def choose_pair(runtime_inventory, device_inventory, *, product_family="iPad", major=27,
                architecture="arm64"):
    """Require both the runtime support matrix and the installed type's bounds.

    A model-specific iPhone runtime may share the general iOS version number.
    Neither version sorting nor a type's minimum version proves compatibility.
    Missing support matrices are refused instead of inferred from device names.
    """
    _require(product_family in {"iPad", "iPhone"} and type(major) is int and major > 0,
             "Unsupported simulator family or major version")
    _require(architecture in {"arm64", "x86_64"}, "Unsupported simulator architecture")
    _require(isinstance(runtime_inventory, dict) and isinstance(device_inventory, dict),
             "Simulator inventories must be objects")
    runtimes = _unique(runtime_inventory.get("runtimes"), "runtimes")
    device_types = _unique(device_inventory.get("devicetypes"), "device types")
    candidates = []
    for identifier, runtime in runtimes.items():
        if not identifier.startswith("com.apple.CoreSimulator.SimRuntime.iOS-") or runtime.get("isAvailable") is not True:
            continue
        version, encoded = _version(runtime.get("version"))
        if version[0] != major:
            continue
        architectures = runtime.get("supportedArchitectures")
        _require(isinstance(architectures, list) and all(isinstance(value, str) for value in architectures),
                 "Runtime lacks explicit supported architectures")
        if architecture not in architectures:
            continue
        supported = _unique(runtime.get("supportedDeviceTypes"), "runtime-supported device types")
        for device_id, description in supported.items():
            installed = device_types.get(device_id)
            if installed is None or description.get("productFamily") != product_family or installed.get("productFamily") != product_family:
                continue
            minimum, maximum = installed.get("minRuntimeVersion"), installed.get("maxRuntimeVersion")
            _require(type(minimum) is int and type(maximum) is int and 0 <= minimum <= maximum <= 0xFFFFFFFF,
                     "Malformed installed simulator runtime bounds")
            if minimum <= encoded <= maximum:
                _require(isinstance(installed.get("name"), str) and installed["name"], "Missing installed device name")
                candidates.append((version, minimum, installed["name"], identifier, device_id, runtime, installed))
    _require(candidates, "No explicitly compatible installed " + product_family + " / iOS " + str(major) + " pair")
    chosen = max(candidates, key=lambda value: value[:5])
    return {
        "runtime": chosen[5], "device": chosen[6],
        "selection": {
            "runtimeIdentifier": chosen[3], "deviceTypeIdentifier": chosen[4],
            "runtimeVersion": chosen[5]["version"], "runtimeBuild": chosen[5].get("buildversion"),
            "productFamily": product_family, "architecture": architecture,
            "compatibilityEvidence": "runtime.supportedDeviceTypes AND installed type version bounds"
        }
    }
