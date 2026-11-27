"""Finite Renderer5 binding around unchanged original Core/RTL validators.

Historical Core22 modules and source remain untouched. This separate namespace
uses the actual complete 78cc Swift file; no Swift source is projected or copied
into a compiler input. Runtime activation is deliberately closed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from originals import require

PREFIX = "Tools/PinkhaDualEngineRuntime/hosted_core24/"
CORE_PATH = "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/native-renderer-hosted/native_core_hosted_profile.py"
HOST_PATH = "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/native-renderer-hosted/combined_host_acceptance_app15.py"
RTL_PATH = "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/rtl-current-editor-profile/rtl_hosted_profile.py"
PROFILE_SHA256 = "20b680037fc717c84c0b3cf3b410085d036bb0d047f25b97b2d48ca3e7232275"
ACTIVATION_SHA256 = "58b35def6566f07b946a09e0d3734c5a3fba80aef755cc52ea6248bef605b277"
ORIGINALS_SHA256 = "adc29fa18b2bd64dce6bca3cf6ded88ae6203246a12fa7e781229fda41b1f326"
ORIGINAL_MANIFEST_SHA256 = "b0afbd53aef99cc44adc77432c6fba6b7b060faf4808e81ec01799df3d2e627c"
READY_FOR_EXECUTION = False
FUTURE_SOURCE_COMMIT = None
FUTURE_NATIVE_SOURCE_MANIFEST_SHA256 = None
LANES = ("native-properties-hosted", "native-block-creation-hosted", "native-typography-hosted",
         "native-renderer-hosted", "rtl-hosted")
LANE_SCOPE = {"native-properties-hosted": (9, 9), "native-block-creation-hosted": (2, 2),
              "native-typography-hosted": (2, 2), "native-renderer-hosted": (5, 5), "rtl-hosted": (6, 10)}
ORIGINAL_TARGETS = {lane: "AnytypeTests" if lane == "rtl-hosted" else "PinkhaAnyUITests" for lane in LANES}
RENDERER = "AnyNativeTextRendererTests"
RENDERER_PATH = "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift"
ORIGINAL_METHODS = (
    "testEqualNativeTextChangesAttributesWithoutReplacingCharactersOrSelection",
    "testChangedNativeTextReplacesCharactersAndKeepsValidSelection",
    "testMarkedTextKeepsCharactersSelectionAndAttributesUntilCommit",
)
ADDED_METHODS = (
    "testMountedControllerRefreshesCanonicalEquivalentLatinTextInTheSameCell",
    "testMountedControllerRefreshesHebrewCombiningOrderInTheSameCell",
)


def physical_raw(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and path.is_file() and not path.is_symlink(), "Exact physical finite profile source required")
    return path.read_bytes()


def require_runtime_ready():
    """Refuse before any external path, command, output or device admission."""
    raw = physical_raw(Path(__file__).absolute().with_name("activation.json"))
    require(hashlib.sha256(raw).hexdigest() == ACTIVATION_SHA256,
            "The separately reviewed closed Core24 activation changed")
    activation = json.loads(raw)
    require(activation["schema"] == "pinkha-hosted-core24-activation-v1"
            and activation["readyForExecution"] is False and activation["plans"] == []
            and (activation["expectedMethods"], activation["expectedCases"]) == (24, 28)
            and all(activation[key] is None for key in ("appSourceSHA", "appSourceTree",
                "nativeSourceManifestSHA256", "hostedOwnerSHA256", "buildReceiptSHA256",
                "native23CompilerReceiptSHA256"))
            and READY_FOR_EXECUTION is False and FUTURE_SOURCE_COMMIT is None
            and FUTURE_NATIVE_SOURCE_MANIFEST_SHA256 is None,
            "The separately reviewed closed Core24 runtime tuple differs")
    raise ValueError("Core24/28 runtime is CLOSED: final source/native/producer receipts and a separately reviewed activation are required")


class LaneValidators:
    """One exact original validator and immutable compiler contract per Core lane."""
    def __init__(self, bindings, lane, source_commit, native_compilation_proof):
        self.bindings, self.lane = bindings, lane
        bindings.command_gate()
        self.contract = bindings.profile.source_contract(bindings.originals.source, lane,
            source_commit=source_commit, native_compilation_proof=native_compilation_proof,
            rtl_profile_path=bindings.originals.source / RTL_PATH)
        self.original_contract = copy.deepcopy(self.contract)
        self.original_validator = bindings.profile.validators(lane)
        require(type(self.original_validator) is bindings.profile.OriginalValidators
                and self.contract["kind"] == lane
                and (self.contract["expected_methods"], self.contract["declared_cases"]) == LANE_SCOPE[lane]
                and self.contract["original_target"] == "PinkhaAnyUITests"
                and self.contract["selected_target"] == "AnytypeTests"
                and self.contract["hosted_original_source_directly_compiled"] is True,
                "Actual original source/compiler-qualified Core lane required")
        bindings.unchanged()

    def check(self, contract=None):
        self.bindings.command_gate()
        require(self.contract == self.original_contract
                and (contract is None or contract is self.contract),
                "Use the same unchanged compiler-qualified Core contract throughout the lane")

    def recheck(self):
        self.check()
        current = self.bindings.profile.source_contract(self.bindings.originals.source, self.lane,
            source_commit=self.contract["source_commit"],
            native_compilation_proof=self.contract["native_compilation_proof"],
            rtl_profile_path=self.bindings.originals.source / RTL_PATH)
        require(current == self.original_contract, "Original Core source/compiler witness changed")
        self.bindings.unchanged()
        return self.contract

    def invocation_selectors(self, selectors, contract):
        self.check(contract)
        result = self.bindings.profile.invocation_selectors(selectors, contract)
        self.bindings.unchanged()
        return result

    def validate_enumeration(self, payload, contract):
        self.check(contract)
        result = self.original_validator.validate_enumeration(payload, contract)
        self.bindings.unchanged()
        return result

    def validate_results(self, summary, tree, udid):
        self.check()
        result = self.original_validator.validate_results(summary, tree, udid)
        self.bindings.unchanged()
        return result


class RuntimeBindings:
    """Separate exact-data namespace; every reused validator AST stays original."""
    def __init__(self, originals, commands, control):
        self.originals, self.commands = originals, commands
        self.control = Path(control)
        require(self.control.is_absolute() and self.control.resolve() == self.control
                and Path(__file__).absolute() == self.control / PREFIX / "profile_binding.py",
                "Exact admitted control checkout owns the Core24 binding")
        self.instances = {}
        self.profile_path = Path(__file__).absolute().with_name("profile.json")
        self.profile_raw = physical_raw(self.profile_path)
        require(hashlib.sha256(self.profile_raw).hexdigest() == PROFILE_SHA256,
                "The exact fixed Renderer5 source binding changed")
        self.specification = json.loads(self.profile_raw)
        require(self.specification["schema"] == "pinkha-hosted-core24-renderer5-source-v1"
                and self.specification["runtimeReady"] is False
                and self.specification["finalSourceNativeTuple"] is None
                and self.specification["originalMethods"] == list(ORIGINAL_METHODS)
                and self.specification["addedMethods"] == list(ADDED_METHODS)
                and self.specification["expectedMethods"] == 24
                and self.specification["expectedCases"] == 28,
                "Only the exact reviewed complete Core24/28 source scope is supported")
        loader = sys.modules.get(type(originals).__module__)
        require(loader is not None and getattr(loader, "Originals", None) is type(originals)
                and type(originals).__name__ == "Originals"
                and hashlib.sha256(physical_raw(Path(loader.__file__))).hexdigest() == ORIGINALS_SHA256
                and originals.proof["manifestSHA256"] == ORIGINAL_MANIFEST_SHA256,
                "Actual unchanged original Core22 loader and its complete source closure required")
        self.original_suites = copy.deepcopy(originals.native_core.SUITES)
        self.original_profiles = copy.deepcopy(originals.native_core.PROFILES)
        old = self.original_suites[RENDERER]
        require(old["source_path"] == RENDERER_PATH
                and old["source_sha256"] == self.specification["originalSource"]["sha256"]
                and tuple(old["methods"]) == ORIGINAL_METHODS
                and all(value == originals.native_core.single() for value in old["methods"].values())
                and self.original_profiles["native-renderer-hosted"] == {
                    "suite": RENDERER, "methods": 3, "cases": 3},
                "The original unchanged Renderer3 source and method inventory are required")
        suites, profiles = copy.deepcopy(self.original_suites), copy.deepcopy(self.original_profiles)
        suites[RENDERER]["source_sha256"] = self.specification["source"]["sha256"]
        suites[RENDERER]["methods"].update({name: originals.native_core.single() for name in ADDED_METHODS})
        profiles["native-renderer-hosted"] = {"suite": RENDERER, "methods": 5, "cases": 5}
        self.expected_suites, self.expected_profiles = copy.deepcopy(suites), copy.deepcopy(profiles)
        before = len(originals.proof["declarations"])
        self.profile = originals.selected("core24_original_renderer_validators", CORE_PATH,
            ("single", "require", "selected", "fixed_contract", "source_contract",
             "invocation_selectors", "OriginalValidators", "validators"),
            bindings={"TARGET": "AnytypeTests", "SUITES": suites, "PROFILES": profiles,
                      "declared_contract": self.declared_contract})
        self.HOSTED_LANES = originals.native_core.HOSTED_LANES
        self.proof = {"schema": "pinkha-hosted-core24-original-validator-binding-v1",
            "profileSHA256": PROFILE_SHA256,
            "source": copy.deepcopy(self.specification["source"]),
            "originalSource": copy.deepcopy(self.specification["originalSource"]),
            "unchangedOriginalValidatorDeclarations": copy.deepcopy(originals.proof["declarations"][before:]),
            "originalCore22LoaderSHA256": ORIGINALS_SHA256,
            "originalCore22ManifestSHA256": ORIGINAL_MANIFEST_SHA256,
            "historicalCore22BytesUnchanged": True, "swiftSourceProjected": False,
            "sameOriginalValidatorPerCoreLane": True,
            "originalCommandBarrierRequiredBeforeWitness": True,
            "expectedMethods": 24, "expectedCases": 28, "testsExecuted": 0}
        require(len(self.proof["unchangedOriginalValidatorDeclarations"]) == 8
                and all(row["originalASTNodeUnchanged"] is True
                        for row in self.proof["unchangedOriginalValidatorDeclarations"]),
                "Eight exact original validator declarations must remain unchanged")
        self._install_original_host_bindings()
        self.unchanged()

    def declared_contract(self, source, lane):
        if lane != "native-renderer-hosted":
            # Preserve the original parser, complete source pins and all13
            # unaffected native-core method contracts exactly.
            return self.originals.native_core.declared_contract(source, lane)
        raw = physical_raw(Path(source) / RENDERER_PATH)
        original = self.specification["originalSource"]
        expected = self.specification["source"]
        offset = original["bytes"]
        require(len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"]
                and hashlib.sha256(raw[:offset]).hexdigest() == original["sha256"]
                and len(raw[offset:]) == self.specification["append"]["bytes"]
                and hashlib.sha256(raw[offset:]).hexdigest() == self.specification["append"]["sha256"],
                "The complete original Renderer3 prefix and exact mounted2 suffix are required")
        text = raw.decode("utf-8")
        sync = re.findall(r"^    func (test[A-Za-z0-9_]+)\(\) \{", text, flags=re.M)
        asynchronous = re.findall(r"^    func (test[A-Za-z0-9_]+)\(\) async throws \{", text, flags=re.M)
        require(text.count("@MainActor\nfinal class " + RENDERER + ": XCTestCase {") == 1
                and text.count("extension " + RENDERER + " {") == 1 and "@Test" not in text
                and tuple(sync) == ORIGINAL_METHODS and tuple(asynchronous) == ADDED_METHODS
                and len(re.findall(r"\bfunc\s+test[A-Za-z0-9_]+", text)) == 5
                and len(set(sync + asynchronous)) == 5,
                "Exactly the three original and two genuine async UIKit XCTest declarations are required")
        return self.profile.fixed_contract(lane)

    def _install_original_host_bindings(self):
        original = self.originals
        bindings = {"shared": original.shared, "native_core": self,
                    "NATIVE": "AnytypeTests", "UI": "PinkhaStage1AcceptanceUITests",
                    "SUPPORT": Path("Library/Application Support")}
        for name in ("require", "raw", "decode", "write", "write_bytes", "sha", "digest"):
            bindings[name] = getattr(original.shared, name)
        before = len(original.proof["declarations"])
        self.host_functions = original.selected("core24_original_host_functions", HOST_PATH,
            ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "host_validation_module"),
            bindings=bindings)
        bindings.update({name: getattr(self.host_functions, name) for name in
            ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "host_validation_module")})
        self.host = original.selected("core24_original_host_methods", HOST_PATH, ("Consumer",),
            methods=("__init__", "command", "container", "installed", "create", "appearance", "stage", "preserve"),
            bindings=bindings)
        self.proof["unchangedOriginalHostDeclarations"] = copy.deepcopy(original.proof["declarations"][before:])
        require(len(self.proof["unchangedOriginalHostDeclarations"]) == 12
                and all(row["originalASTNodeUnchanged"] is True
                        for row in self.proof["unchangedOriginalHostDeclarations"]),
                "Four exact original host helpers and eight Consumer methods must remain unchanged")

    def unchanged(self):
        self.originals.unchanged()
        require(physical_raw(self.profile_path) == self.profile_raw
                and self.originals.modules.get("core24_original_renderer_validators") is self.profile
                and sys.modules.get("core24_original_renderer_validators") is self.profile
                and self.profile.SUITES == self.expected_suites
                and self.profile.PROFILES == self.expected_profiles
                and self.originals.native_core.SUITES == self.original_suites
                and self.originals.native_core.PROFILES == self.original_profiles,
                "Finite profile or unchanged historical Core22 data changed")

    def command_gate(self):
        require(self.commands.is_open,
                "Original owned group is unresolved; compiler witness admission is closed")
        self.unchanged()

    def source_contract(self, lane, *, source_commit, native_compilation_proof):
        self.command_gate()
        require(lane in self.HOSTED_LANES, "Only the four exact Core lanes use this binding")
        if lane not in self.instances:
            self.instances[lane] = LaneValidators(self, lane, source_commit, native_compilation_proof)
            return self.instances[lane].contract
        current = self.instances[lane]
        require(current.contract["source_commit"] == source_commit
                and current.contract["native_compilation_proof"] == native_compilation_proof,
                "A lane cannot adopt another original source or compiler proof")
        return current.recheck()

    def validators(self, lane):
        self.command_gate()
        require(lane in self.instances, "Original source/compiler qualification must precede lane callbacks")
        current = self.instances[lane]
        current.check()
        return current

    def invocation_selectors(self, selectors, contract):
        self.command_gate()
        require(isinstance(contract, dict) and contract.get("kind") in self.instances,
                "Only an existing exact Core lane contract can select tests")
        return self.instances[contract["kind"]].invocation_selectors(selectors, contract)
