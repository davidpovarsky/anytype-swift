"""One fixed SDK06 tag selection over the admitted original451394 native build.

This adapter never builds products. The original descriptor, its separately
normalized host copy, and both selection copies keep distinct identities.
"""
from __future__ import annotations

import base64
import copy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import plistlib
import uuid

import shared_editor_existing_build as component
import sdk06_enumeration_probe as probe
import sdk06_tagged_selector as retained_tagged

PROTOCOL = "sdk06-original-native-tag-selection-v1"
TAG = "pinkhaSDK06Pending23"
ORIGINAL_DESCRIPTOR_SHA256 = "4a2868235a870acf7567dfed7e00bd95079189cc9cc757c07cc28498265bedc2"
_SEAL = object()


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def selection_arguments():
    # Keep tag selection independent from the broad discovery suite filters.
    return ["-only-testing-tags", TAG]


def tag_only_value(value):
    require(isinstance(value, dict)
            and value.get("__xctestrun_metadata__", {}).get("FormatVersion") == 2,
            "Only the admitted v2 native descriptor is supported")
    result = copy.deepcopy(value)
    configurations = result.get("TestConfigurations")
    require(isinstance(configurations, list) and len(configurations) == 1
            and isinstance(configurations[0], dict)
            and configurations[0].get("IsEnabled", True) is True,
            "One enabled original native configuration is required")
    targets = configurations[0].get("TestTargets")
    require(isinstance(targets, list) and all(isinstance(item, dict) for item in targets),
            "Original native test targets are missing")
    selected = [target for target in targets if target.get("BlueprintName") == "AnytypeTests"]
    require(len(selected) == 1 and selected[0].get("IsEnabled", True) is True,
            "One enabled original AnytypeTests target is required")
    # The admitted original has no selection metadata. Never erase or override
    # pre-existing restrictions in an unexpected descriptor.
    forbidden = {
        "OnlyTestIdentifiers", "SkipTestIdentifiers", "TestIdentifiers",
        "OnlyTestTags", "SkipTestTags", "OnlyTestingTags", "SkipTestingTags",
        "TagsToRun", "TagsToSkip",
    }
    def inspect(node):
        if isinstance(node, dict):
            require(not forbidden.intersection(node), "Unexpected original selection metadata")
            for child in node.values():
                inspect(child)
        elif isinstance(node, list):
            for child in node:
                inspect(child)
    inspect(value)
    configurations[0]["TestTargets"] = selected
    return result


def selected_configuration(original, destination, origin, shared):
    origin.verify_descriptor_binding()
    require(original == origin.native_configuration
            and destination.parent.resolve() == original.parent.resolve()
            and destination != original and not destination.exists()
            and not destination.is_symlink(),
            "A fresh sibling of the admitted host descriptor is required")
    raw = original.read_bytes()
    require(digest(raw) == origin.descriptor_binding["host_sha256"]
            and origin.descriptor_binding["original_sha256"] == ORIGINAL_DESCRIPTOR_SHA256,
            "The original-to-host descriptor binding differs")
    value = plistlib.loads(raw)
    selected = tag_only_value(value)
    with destination.open("xb") as output:
        plistlib.dump(selected, output, sort_keys=False)
    require(original.read_bytes() == raw, "The admitted host descriptor changed")
    return {
        "path": str(destination),
        "sha256": shared.digest(destination),
        "original_sha256": digest(raw),
        "input_kind": "ORIGINAL_NATIVE_HOST_NORMALIZED_DESCRIPTOR",
        "frozen_original_sha256": ORIGINAL_DESCRIPTOR_SHA256,
        "format_version": 2,
        "target": "AnytypeTests",
        "selection_fields_injected": [],
        "only_change_from_host_value": "RETAIN_ORIGINAL_ANYTYPE_TESTS_TARGET",
        "other_targets_removed_from_copy": [
            item.get("BlueprintName") for item in value["TestConfigurations"][0]["TestTargets"]
            if item.get("BlueprintName") != "AnytypeTests"
        ],
    }


@dataclass(frozen=True)
class OriginalNativeTaggedSelectionPlan:
    origin: object
    _seal: object = field(repr=False)
    _pending_execution: dict = field(default_factory=dict, repr=False, compare=False)

    def verify(self):
        from sdk06_original_native import SDK06OriginalNativeContext
        require(self._seal is _SEAL and type(self.origin) is SDK06OriginalNativeContext,
                "A sealed fixed original-native origin is required")
        self.origin.verify_current()
        return self.origin.tag_contract

    def enumerate_current(self, app, base, evidence, shared, source):
        contract = self.verify()
        require(Path(app).resolve() == self.origin.app and not self._pending_execution,
                "Original-native enumeration requires its exact App and a fresh plan")
        selection = retained_tagged.source_selection(source, contract)
        require(base[:2] == ["xcodebuild", "test-without-building"]
                and base.count("-xctestrun") == base.count("-destination") == 1
                and not any(item.startswith(("-only-testing", "-skip-testing")) for item in base),
                "Unexpected original-native test command prefix")
        destination = base[base.index("-destination") + 1]
        require(destination == "platform=iOS Simulator,id=" + self.origin.device["udid"],
                "Original-native selection must use the current attempt's owned UUID")
        original = Path(base[base.index("-xctestrun") + 1])
        require(original == self.origin.native_configuration, "Unadmitted native descriptor")
        token = uuid.uuid4().hex
        bindings, observations = {}, {}
        command_receipt = {
            "protocol": PROTOCOL, **self.origin.execution_binding,
            "original_native_origin": self.origin.origin_reference(),
            "product_tests_executed": 0,
        }
        runner = probe.Commands(app, evidence, command_receipt)
        for label in ("discovery", "selected"):
            configuration = original.with_name("UI27-original-sdk06-" + token + "-" + label + ".xctestrun")
            if label == "discovery":
                binding = component.scoped_configuration(original, configuration,
                    ["AnytypeTests/" + suite for suite in component.SUITES], shared)
                arguments = ["-only-testing:AnytypeTests/" + suite for suite in component.SUITES]
            else:
                binding = selected_configuration(original, configuration, self.origin, shared)
                arguments = selection_arguments()
            self.origin.register_generated_descriptor(configuration,
                "discovery" if label == "discovery" else "tagged-selection")
            command_base = list(base)
            command_base[command_base.index("-xctestrun") + 1] = str(configuration)
            output = evidence / ("tagged-" + label + ".enumeration.json")
            result = evidence / ("tagged-" + label + ".xcresult")
            command = [*command_base, *arguments, "-enumerate-tests", "-test-enumeration-style", "flat",
                       "-test-enumeration-format", "json", "-test-enumeration-output-path", str(output),
                       "-resultBundlePath", str(result)]
            _, outcome = runner.run(command, "tagged-" + label, timeout=600)
            require(outcome["return_code"] == 0
                    and probe.sha(original) == binding["original_sha256"]
                    and probe.sha(configuration) == binding["sha256"],
                    "Actual enumeration or descriptor integrity failed")
            payload = json.loads(output.read_bytes())
            # Preserve both original observations before a qualification refusal.
            bindings[label] = binding
            binding["descriptor_bytes_base64"] = base64.b64encode(configuration.read_bytes()).decode("ascii")
            observations[label] = {"command": command, "output_path": str(output),
                                   "sha256": probe.sha(output)}
            shared.write(evidence / "original-tag-enumeration-observations.json",
                {"protocol": PROTOCOL, "bindings": bindings, "observations": observations,
                 "qualified": False, "tests_executed": 0})
            if label == "discovery":
                plan, enabled, disabled = component.enumerated_identifiers(payload)
                require(plan == "AnytypeTests" and enabled == set(selection["declarations"])
                        and not enabled.intersection(disabled),
                        "The restored native build does not expose the exact30 declarations")
            else:
                retained_tagged.qualify_enumeration(payload, selection)
        self.verify()
        receipt = {
            "status": "EXACT_COMPILED_SELECTION_VERIFIED",
            "selector_plan_protocol": PROTOCOL,
            "binding": self.origin.execution_binding,
            "original_native_origin": self.origin.origin_reference(),
            "original_descriptor_binding": self.origin.descriptor_binding,
            "selection_nonce": token,
            "test_plan": "AnytypeTests",
            "selected_identifiers": selection["selected"],
            "selected_method_count": 23,
            "unselected_identifiers": selection["excluded"],
            "enumerated_source_method_count": 30,
            "selected_configuration": bindings["selected"],
            "discovery_configuration": bindings["discovery"],
            "original_configuration_path": str(original),
            "destination": destination,
            "tag_cli_arguments": selection_arguments(),
            "current_enumeration": observations,
            "tests_executed": 0,
        }
        self._pending_execution["receipt_sha256"] = digest(json.dumps(receipt, sort_keys=True).encode())
        return receipt

    def execution_arguments(self, enumeration, selected_base):
        self.verify()
        require(self._pending_execution.get("receipt_sha256") ==
                digest(json.dumps(enumeration, sort_keys=True).encode()),
                "Execution requires this exact current enumeration, once")
        require(enumeration["binding"] == self.origin.execution_binding
                and enumeration["original_native_origin"] == self.origin.origin_reference()
                and enumeration["tag_cli_arguments"] == selection_arguments()
                and selected_base[:2] == ["xcodebuild", "test-without-building"]
                and selected_base.count("-xctestrun") == selected_base.count("-destination") == 1
                and not any(item.startswith(("-only-testing", "-skip-testing")) for item in selected_base)
                and selected_base[selected_base.index("-destination") + 1] == enumeration["destination"]
                and selected_base[selected_base.index("-xctestrun") + 1] ==
                    enumeration["selected_configuration"]["path"],
                "Current origin, source, run, destination, descriptor or tag arguments differ")
        for label in ("discovery", "selected"):
            observation = enumeration["current_enumeration"][label]
            binding = enumeration[label + "_configuration"]
            require(probe.sha(Path(observation["output_path"])) == observation["sha256"]
                    and probe.sha(Path(binding["path"])) == binding["sha256"]
                    and probe.sha(Path(enumeration["original_configuration_path"])) == binding["original_sha256"],
                    "An original enumeration or descriptor changed")
        self._pending_execution.clear()
        self._pending_execution["consumed"] = True
        return selection_arguments()


def load_plan(origin):
    from sdk06_original_native import SDK06OriginalNativeContext
    require(type(origin) is SDK06OriginalNativeContext, "An exact original-native context is required")
    origin.verify_current()
    return OriginalNativeTaggedSelectionPlan(origin, _SEAL)
