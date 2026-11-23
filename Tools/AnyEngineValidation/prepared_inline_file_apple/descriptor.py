"""Bind one generated XCTest descriptor to this exact owned inline-file run."""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import plistlib
import re

import contract

ENVIRONMENT = {
    "sourceSHA": "PINKHA_PREPARED_INLINE_APPLE_SOURCE_SHA",
    "runID": "PINKHA_PREPARED_INLINE_APPLE_RUN_ID",
    "runAttempt": "PINKHA_PREPARED_INLINE_APPLE_RUN_ATTEMPT",
    "nonce": "PINKHA_PREPARED_INLINE_APPLE_NONCE",
}


def validate_binding(value):
    contract.require(isinstance(value, dict) and set(value) == set(ENVIRONMENT),
                     "Exactly the owned source/run/attempt/nonce binding is required")
    patterns = {"sourceSHA": r"[0-9a-f]{40}", "runID": r"[1-9][0-9]*",
                "runAttempt": r"[1-9][0-9]*", "nonce": r"[0-9a-f]{32}"}
    contract.require(all(isinstance(value[k], str) and re.fullmatch(patterns[k], value[k]) for k in patterns),
                     "Malformed owned acceptance identity")
    return {ENVIRONMENT[k]: value[k] for k in ENVIRONMENT}


def targets(document):
    contract.require(isinstance(document, dict), "Generated XCTest descriptor must be a dictionary")
    if "TestConfigurations" in document:
        configs = document["TestConfigurations"]
        contract.require(isinstance(configs, list) and len(configs) == 1
                         and isinstance(configs[0], dict) and configs[0].get("IsEnabled", True) is not False,
                         "One enabled generated test configuration is required")
        result = configs[0].get("TestTargets")
        contract.require(isinstance(result, list) and len(result) == 1 and isinstance(result[0], dict),
                         "One exact generated runtime test target is required")
        return result
    result = []
    for key, value in document.items():
        if key.startswith("__"):
            continue
        if isinstance(value, dict) and "TestBundlePath" in value:
            contract.require(key == contract.TARGET, "Unexpected legacy generated test target")
            result.append(value)
    contract.require(len(result) == 1, "One legacy generated runtime test target is required")
    return result


def bind_document(document, binding):
    environment = validate_binding(binding)
    changed = copy.deepcopy(document)
    original_targets, changed_targets = targets(document), targets(changed)
    original, target = original_targets[0], changed_targets[0]
    contract.require(target.get("BlueprintName", contract.TARGET) == contract.TARGET
                     and isinstance(target.get("TestBundlePath"), str) and target["TestBundlePath"].endswith(".xctest")
                     and isinstance(target.get("TestHostPath"), str) and bool(target["TestHostPath"]),
                     "Generated target is not the actual runtime XCTest bundle")
    skip = target.get("SkipTestIdentifiers", [])
    contract.require(isinstance(skip, list) and all(isinstance(v, str) for v in skip),
                     "Malformed original test exclusion")
    method, group = contract.METHOD, contract.METHOD.split("/")[0]
    contract.require(not any(v in (method, group, contract.TARGET, contract.SELECTOR)
                             or method.startswith(v.rstrip("/") + "/") for v in skip),
                     "Original generated descriptor excludes the selected method")
    current = target.setdefault("EnvironmentVariables", {})
    contract.require(isinstance(current, dict) and all(isinstance(k, str) and isinstance(v, str)
                     for k, v in current.items()), "Malformed generated target environment")
    contract.require(not any(k.startswith("PINKHA_PREPARED_INLINE_APPLE_") for k in current),
                     "Generated descriptor already contains another acceptance binding")
    current.update(environment)
    target["OnlyTestIdentifiers"] = [method]
    # Xcode injection and every other generated target field are preserved.
    before_rest = {k:v for k,v in original.items() if k not in ("EnvironmentVariables", "OnlyTestIdentifiers")}
    after_rest = {k:v for k,v in target.items() if k not in ("EnvironmentVariables", "OnlyTestIdentifiers")}
    contract.require(before_rest == after_rest, "Generated XCTest injection or paths changed")
    return changed


def bind_generated(products, evidence, binding):
    products = products.resolve()
    candidates = sorted(products.glob("*.xctestrun"))
    contract.require(len(candidates) == 1, "Exactly one fresh original generated XCTest descriptor required")
    original = candidates[0]
    contract.require(original.is_file() and not original.is_symlink() and original.stat().st_size <= 8 * 1024**2,
                     "Invalid or oversized original XCTest descriptor")
    before = original.read_bytes()
    document = plistlib.loads(before)
    bound = bind_document(document, binding)
    # Keep __TESTROOT__ relative to the original product directory.
    path = original.with_name("prepared-inline-bound-" + binding["nonce"] + ".xctestrun")
    contract.require(not path.exists(), "A prior bound XCTest descriptor must not be replaced")
    encoded = plistlib.dumps(bound, fmt=plistlib.FMT_XML, sort_keys=True)
    with path.open("xb") as stream:
        stream.write(encoded)
    contract.require(original.read_bytes() == before, "Original generated descriptor changed")
    audit = dict(source_descriptor=str(original), source_descriptor_sha256=hashlib.sha256(before).hexdigest(),
                 bound_descriptor=str(path), bound_descriptor_sha256=contract.digest(path),
                 selected_target=contract.TARGET, selected_method=contract.METHOD,
                 environment_variables=validate_binding(binding), original_descriptor_unchanged=True,
                 same_product_directory=True, original_injection_preserved=True)
    contract.save(evidence / "owned-xctestrun-binding.json", audit)
    return path, audit


def product_inventory(products):
    products = products.resolve()
    contract.require(products.is_dir(), "Actual compiled products are missing")
    result = {}
    for path in sorted(products.rglob("*")):
        if path.suffix == ".xctestrun":
            continue
        key = path.relative_to(products).as_posix()
        if path.is_symlink():
            result[key] = dict(kind="symlink", target=os.readlink(path))
        elif path.is_file():
            result[key] = dict(kind="file", sha256=contract.digest(path), size=path.stat().st_size,
                               mode=path.stat().st_mode & 0o777)
    contract.require(result, "Compiled product inventory is empty")
    return result
