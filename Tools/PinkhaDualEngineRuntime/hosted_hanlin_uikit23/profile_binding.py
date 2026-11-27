"""Bind the fixed original component profile to unchanged original host declarations.

This is a finite API bridge, not a declaration profile or process manager.
Every lane retains one real W2 CompilerQualifiedProfile for selector,
enumeration and result calls. Its inherited Git witness is called only while
the original runtime command barrier remains open.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from originals import HOST_PATH, require

DEPENDENCY_SHA256 = "698f82318f971f2e0f3de707fcd721388707197a746309f4a555e2f09004f58d"
ACTIVATION_SHA256 = "2a6d9b503a49c156a1dc6dc6d110c2008386eee18a9c4021af18c7c24655fa23"
W2_PREFIX = "Tools/PinkhaDualEngineRuntime/hosted_hanlin_uikit23/"
W2_MODULE_NAME = "hosted_hanlin_uikit23_original_profile"
LANES = ('hanlin-viewport21-hosted', 'hanlin-observation2-hosted')
LANE_SCOPE = {'hanlin-viewport21-hosted': (21, 21), 'hanlin-observation2-hosted': (2, 2)}
ORIGINAL_TARGETS = {'hanlin-viewport21-hosted': 'AI_HLYTests', 'hanlin-observation2-hosted': 'AI_HLYTests'}
READY_FOR_EXECUTION = False
FUTURE_SOURCE_COMMIT = None
FUTURE_NATIVE_SOURCE_MANIFEST_SHA256 = None


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def physical_raw(path, maximum=2 * 1024 ** 2):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and path.resolve() == path and path.stat().st_size <= maximum,
            "Exact bounded physical profile input required")
    return path.read_bytes()


def require_runtime_ready():
    """Refuse before any external path, command, output or device admission."""
    raw = physical_raw(Path(__file__).absolute().with_name("activation.json"))
    require(hashlib.sha256(raw).hexdigest() == ACTIVATION_SHA256,
            "The separately reviewed closed activation changed")
    activation = json.loads(raw)
    require(activation["schema"] == "pinkha-hosted-hanlin-uikit23-activation-v1"
            and activation["readyForExecution"] is False and activation["plans"] == []
            and (activation["expectedMethods"], activation["expectedCases"]) == (23, 23)
            and all(activation[key] is None for key in ("appSourceSHA", "appSourceTree",
                "nativeSourceManifestSHA256", "hostedOwnerSHA256", "buildReceiptSHA256",
                "native23CompilerReceiptSHA256"))
            and READY_FOR_EXECUTION is False and FUTURE_SOURCE_COMMIT is None
            and FUTURE_NATIVE_SOURCE_MANIFEST_SHA256 is None,
            "The separately reviewed closed runtime tuple differs")
    raise ValueError("Hanlin UIKit23/23 runtime is CLOSED: final source/native/producer receipts and a separately reviewed activation are required")


class LaneValidators:
    """Signature adapter around exactly one fixed original lane instance."""
    def __init__(self, bindings, lane, source_commit, native_compilation_proof):
        self.bindings, self.lane = bindings, lane
        bindings.command_gate()
        self.qualified = bindings.profile.validators(bindings.originals, lane,
            source_commit=source_commit, native_compilation_proof=native_compilation_proof)
        require(type(self.qualified) is bindings.profile.CompilerQualifiedProfile,
                "The actual fixed original component lane instance is required")
        self.contract = self.qualified.contract
        self.original_contract = copy.deepcopy(self.contract)
        require(self.contract["kind"] == lane
                and (self.contract["expected_methods"], self.contract["declared_cases"]) == LANE_SCOPE[lane]
                and self.contract["original_target"] == ORIGINAL_TARGETS[lane]
                and self.contract["selected_target"] == "AnytypeTests"
                and self.contract["phase"] == "SOURCE_AND_COMPILER_WITNESS_QUALIFIED",
                "Actual compiler-qualified finite source scope differs")
        bindings.unchanged()

    def check(self, contract=None):
        self.bindings.command_gate()
        require(self.qualified.contract is self.contract and self.contract == self.original_contract
                and (contract is None or contract is self.contract),
                "Use the same untouched compiler-qualified contract throughout this lane")

    def recheck(self):
        self.check()
        current = self.bindings.profile.source_contract(self.bindings.originals, self.lane,
            source_commit=self.contract["source_commit"],
            native_compilation_proof=self.contract["native_compilation_proof"])
        require(current == self.original_contract, "Original component source/compiler witness changed")
        self.bindings.unchanged()
        return self.contract

    def invocation_selectors(self, selectors, contract):
        self.check(contract)
        result = self.bindings.profile.invocation_selectors(selectors, self.qualified)
        self.bindings.unchanged()
        return result

    def validate_enumeration(self, payload, contract):
        self.check(contract)
        result = self.qualified.validate_enumeration(payload)
        self.bindings.unchanged()
        return result

    def validate_results(self, summary, tree, udid):
        self.check()
        result = self.qualified.validate_results(summary, tree, udid)
        self.bindings.unchanged()
        return result


class RuntimeBindings:
    """Separate finite host namespace; existing Core22 modules stay unchanged."""
    def __init__(self, originals, commands, control):
        self.originals, self.commands = originals, commands
        self.control = Path(control)
        require(self.control.is_absolute() and self.control.resolve() == self.control
                and Path(__file__).absolute() == self.control / W2_PREFIX / "profile_binding.py",
                "Exact admitted control checkout owns this finite profile")
        self.instances = {}
        dependency_path = Path(__file__).absolute().with_name("profile-dependency.json")
        raw = physical_raw(dependency_path)
        require(hashlib.sha256(raw).hexdigest() == DEPENDENCY_SHA256,
                "The exact fixed original component dependency binding changed")
        self.dependency = json.loads(raw)
        require(self.dependency["schema"] == 'pinkha-hosted-hanlin-uikit23-profile-binding-v1'
                and self.dependency["repository"] == "davidpovarsky/anytype-swift"
                and self.dependency["runtimeReady"] is False
                and self.dependency["newTestImplementation"] is False
                and self.dependency["newFiniteProfileImplementation"] is True
                and self.dependency["finalSourceSDKNativeTuple"] is None
                and (self.dependency["reviewedMethodCount"], self.dependency["reviewedCaseCount"]) == (23, 23)
                and set(self.dependency["files"]) == {W2_PREFIX + name for name in
                    ("profile.py", "profile.json", "source-inverse.json")},
                "Only the exact three-file original component profile is supported")
        loader = sys.modules.get(type(originals).__module__)
        require(loader is not None and getattr(loader, "Originals", None) is type(originals)
                and type(originals).__name__ == "Originals"
                and hashlib.sha256(physical_raw(Path(loader.__file__))).hexdigest()
                    == self.dependency["originalCore22LoaderSHA256"]
                and originals.proof["manifestSHA256"] == self.dependency["originalCore22ManifestSHA256"],
                "The actual unchanged original Core22 loader object is required")
        self.profile_bytes = {}
        for relative, pin in self.dependency["files"].items():
            value = physical_raw(self.control / relative)
            require(identity(value) == pin, "Fixed component profile input changed: " + relative)
            self.profile_bytes[relative] = value
        require(W2_MODULE_NAME not in sys.modules and W2_MODULE_NAME not in originals.modules,
                "A foreign module already owns the fixed W2 profile name")
        path = self.control / W2_PREFIX / "profile.py"
        specification = importlib.util.spec_from_file_location(W2_MODULE_NAME, path)
        require(specification is not None and specification.loader is not None,
                "Original component profile module cannot be loaded")
        self.profile = importlib.util.module_from_spec(specification)
        sys.modules[W2_MODULE_NAME] = self.profile
        # The unchanged original loader closes every module in its owned
        # registry. Register this added module without replacing any original.
        originals.modules[W2_MODULE_NAME] = self.profile
        specification.loader.exec_module(self.profile)
        require(self.profile.LANES == LANES and self.profile.HOSTED_LANES == frozenset(LANES),
                "Only the two exact fixed lanes may bind original host functions")
        self.HOSTED_LANES = self.profile.HOSTED_LANES
        self.proof = {"schema": "pinkha-hosted-hanlin-uikit23-original-host-api-binding-v1",
            "originalSourceOrigins": copy.deepcopy(self.dependency["sourceOrigins"]),
            "profileFiles": copy.deepcopy(self.dependency["files"]),
            "originalCore22LoaderSHA256": self.dependency["originalCore22LoaderSHA256"],
            "originalCore22ManifestSHA256": originals.proof["manifestSHA256"],
            "newFiniteSelectorProfile": True, "newSwiftTests": False, "sameOriginalInstancePerLane": True,
            "originalCommandBarrierRequiredBeforeWitness": True,
            "runtimeAdmissionPerformed": False, "testsExecuted": 0}
        self._install_original_host_bindings()
        self.unchanged()

    def _install_original_host_bindings(self):
        original = self.originals
        bindings = {"shared": original.shared, "native_core": self,
                    "NATIVE": "AnytypeTests", "UI": "PinkhaStage1AcceptanceUITests",
                    "SUPPORT": Path("Library/Application Support")}
        for name in ("require", "raw", "decode", "write", "write_bytes", "sha", "digest"):
            bindings[name] = getattr(original.shared, name)
        before = len(original.proof["declarations"])
        self.host_functions = original.selected("hosted_hanlin_uikit23_original_host_functions", HOST_PATH,
            ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "host_validation_module"),
            bindings=bindings)
        bindings.update({name: getattr(self.host_functions, name) for name in
            ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "host_validation_module")})
        self.host = original.selected("hosted_hanlin_uikit23_original_host_methods", HOST_PATH, ("Consumer",),
            methods=("__init__", "command", "container", "installed", "create", "appearance", "stage", "preserve"),
            bindings=bindings)
        self.proof["unchangedOriginalDeclarations"] = copy.deepcopy(original.proof["declarations"][before:])
        require(len(self.proof["unchangedOriginalDeclarations"]) == 12
                and all(row["originalASTNodeUnchanged"] is True
                        for row in self.proof["unchangedOriginalDeclarations"]),
                "Four original helpers and eight original Consumer methods must remain exact")

    def unchanged(self):
        self.originals.unchanged()
        require(sys.modules.get(W2_MODULE_NAME) is self.profile
                and self.originals.modules.get(W2_MODULE_NAME) is self.profile,
                "The exact fixed profile module was replaced")
        for relative, before in self.profile_bytes.items():
            require(physical_raw(self.control / relative) == before,
                    "Fixed component profile bytes changed during the runtime")

    def command_gate(self):
        # W2 delegates to the original compiler witness's three bounded Git
        # queries. Never enter that path after unresolved original ownership.
        require(self.commands.is_open,
                "Original owned group is unresolved; W2 compiler witness admission is closed")
        self.unchanged()

    def source_contract(self, lane, *, source_commit, native_compilation_proof):
        self.command_gate()
        require(lane in self.HOSTED_LANES, "Only the two fixed component lanes are supported")
        if lane not in self.instances:
            self.instances[lane] = LaneValidators(self, lane, source_commit, native_compilation_proof)
            return self.instances[lane].contract
        current = self.instances[lane]
        require(current.contract["source_commit"] == source_commit
                and current.contract["native_compilation_proof"] == native_compilation_proof,
                "An existing lane cannot adopt another source or compiler proof")
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
                "Only an existing exact lane contract can select tests")
        return self.instances[contract["kind"]].invocation_selectors(selectors, contract)
