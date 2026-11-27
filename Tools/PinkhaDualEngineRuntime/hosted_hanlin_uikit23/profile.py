"""Hanlin UIKit23/23; source expectations grant no execution authority.

The actual Core22 Originals object supplies the byte-pinned original parser,
compiler witness, enumeration and result functions. This module never creates
a process, descriptor, simulator, native account, or producer admission.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sys

PROFILE_SHA256 = "672be064e3f5a1b090643b9a151af3923981ea363a380b97201364714ec03c78"
ORIGINALS_SHA256 = "adc29fa18b2bd64dce6bca3cf6ded88ae6203246a12fa7e781229fda41b1f326"
ORIGINAL_MANIFEST_SHA256 = "b0afbd53aef99cc44adc77432c6fba6b7b060faf4808e81ec01799df3d2e627c"
TARGET = "AnytypeTests"
LANES = ('hanlin-viewport21-hosted', 'hanlin-observation2-hosted')
HOSTED_LANES = frozenset(LANES)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require_runtime_ready(*args, **kwargs):
    # No flag, JSON value, environment variable or supplied receipt can open
    # this source-only checkpoint. Wave3 owns a reviewed integration successor.
    raise ValueError("Hanlin UIKit23/23 runtime CLOSED: profile-only source, no admitted execution adapter")


def _physical_file(root, relative, maximum=2 * 1024**2):
    root = Path(root)
    require(root.is_absolute() and root.resolve() == root and root.is_dir(),
            "Exact physical source/control root required")
    path = root / relative
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and path.is_relative_to(root) and path.stat().st_size <= maximum,
            "Exact bounded physical input required: " + relative)
    return path.read_bytes()


def _profile():
    root = Path(__file__).resolve().parent
    raw = _physical_file(root, "profile.json")
    require(sha(raw) == PROFILE_SHA256, "Exact finite component profile changed")
    value = json.loads(raw)
    require(value["schema"] == 'pinkha-hosted-hanlin-uikit23-closed-profile-v1' and value["runtimeReady"] is False
            and set(value["lanes"]) == set(LANES)
            and (value["methods"], value["declaredCases"]) == (23, 23)
            and value["finalSDKAndNativeTuple"] is None,
            "Finite closed original component scope differs")
    pin = value["sourceInverse"]
    require(pin["file"] == "source-inverse.json", "Fixed inverse filename required")
    inverse_raw = _physical_file(root, pin["file"])
    require(len(inverse_raw) == pin["bytes"] and sha(inverse_raw) == pin["sha256"],
            "Original finite source inverses changed")
    inverse = json.loads(inverse_raw)
    require(inverse["schema"] == 'pinkha-hosted-hanlin-uikit23-source-inverse-v1' and inverse["runtimeReady"] is False
            and inverse["swiftTestBodiesModified"] is False and inverse["swiftSourcesCompiled"] is False
            and set(inverse["sources"]) == set(('observation', 'viewport')), "Finite inverse scope differs")
    return value, inverse


def _originals(originals):
    cls = type(originals)
    module = sys.modules.get(cls.__module__)
    require(module is not None and cls.__name__ == "Originals"
            and getattr(module, "Originals", None) is cls, "Actual original Core22 loader object required")
    path = Path(module.__file__)
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink()
            and sha(path.read_bytes()) == ORIGINALS_SHA256,
            "Original Core22 loader source changed")
    require(originals.proof.get("manifestSHA256") == ORIGINAL_MANIFEST_SHA256,
            "Original 15-file Core22 closure differs")
    for name, member in (("wave15_core_profile", "core_declarations"),
                         ("shared_editor_existing_build", "enumeration"),
                         ("run_host_tests", "host_results"),
                         ("native_compiler_witness", "witness")):
        require(originals.modules.get(name) is getattr(originals, member)
                and sys.modules.get(name) is getattr(originals, member),
                "Foreign or replaced original validator module: " + name)
    originals.unchanged()


def _reverse_source(raw, steps, source):
    current, proofs = raw, []
    for step in steps:
        require(len(current) == step["candidateBytes"] and sha(current) == step["candidateSHA256"],
                "Exact candidate input to source inverse required")
        end = len(current)
        for edit in reversed(step["edits"]):
            start, length = edit["candidateOffset"], edit["candidateBytes"]
            require(type(start) is int and type(length) is int and 0 <= start <= start + length <= end,
                    "Overlapping or invalid finite inverse span")
            replacement = edit["restoreUTF8"].encode("utf-8")
            require(sha(current[start:start + length]) == edit["candidateSHA256"]
                    and sha(replacement) == edit["restoreSHA256"], "Finite inverse preimage differs")
            current = current[:start] + replacement + current[start + length:]
            end = start
        require(len(current) == step["restoredBytes"] and sha(current) == step["restoredSHA256"],
                "Finite inverse did not restore the published original input")
        proofs.append({key: step[key] for key in
                       ("candidateSHA256", "candidateBytes", "restoredSHA256", "restoredBytes")})
    require(len(current) == source["restoredOriginalBytes"]
            and sha(current) == source["restoredOriginalSHA256"], "Original source custody differs")
    return proofs


def _declaration_view(raw, source_key, inverse):
    require(source_key in inverse["sources"], "Only an exact fixed original source is supported")
    return raw, {"projectionApplied": False, "compiledSwiftSourceModified": False}


def fixed_contract(lane):
    """Fixed source expectations only; these are not observed compiled IDs."""
    require(lane in HOSTED_LANES, "Only the two fixed Hanlin UIKit23/23 lanes are supported")
    profile, _ = _profile()
    selected = profile["lanes"][lane]
    source = profile["sources"][selected["source"]]
    suite, methods = selected["suite"], selected["methods"]
    identifiers = sorted(TARGET + "/" + suite + "/" + name + "("
                         + "".join(item["name"] + ":" for item in definition["parameters"]) + ")"
                         for name, definition in methods.items())
    return {"kind": lane, "scope": "hosted-hanlin-uikit23", "phase": "FIXED_SOURCE_EXPECTATIONS_ONLY",
            "suite": suite, "methods": sorted(suite + "/" + name for name in methods),
            "expected_compiled_identifiers": identifiers,
            "expected_methods": selected["expectedMethods"], "declared_cases": selected["declaredCases"],
            "source_hashes": {source["path"]: source["sha256"]},
            "original_target": source["originalTarget"], "selected_target": TARGET,
            "profile_sha256": PROFILE_SHA256, "source_commit": None, "native_compilation_proof": None,
            "actual_native_compiler_witnesses": None, "actual_compiled_enumeration": None,
            "product_admission_performed": False, "runtime_admission_performed": False,
            "tests_executed": 0}


def declared_contract(originals, lane):
    """Inspect exact published source; never claim compilation or enumeration."""
    require(lane in LANES, "Only the two fixed Hanlin UIKit23/23 lanes are supported")
    _originals(originals)
    profile, inverse = _profile()
    selected = profile["lanes"][lane]
    key = selected["source"]
    source = profile["sources"][key]
    raw = _physical_file(originals.source, source["path"])
    require(len(raw) == source["bytes"] and sha(raw) == source["sha256"],
            "Full published test input changed: " + source["path"])
    restored = _reverse_source(raw, inverse["sources"][key], source)
    for relative, expected in profile["supportSources"].items():
        actual = _physical_file(originals.source, relative)
        require(len(actual) == expected["bytes"] and sha(actual) == expected["sha256"]
                and hashlib.sha1(b"blob " + str(len(actual)).encode() + b"\0" + actual).hexdigest() == expected["gitBlob"],
                "Exact supporting SDK implementation or explicit test-product linkage changed: " + relative)
    view, projection = _declaration_view(raw, key, inverse)
    complete = originals.core_declarations.inspect_declarations(view.decode("utf-8"))
    require(complete == source["completeDeclarations"], "Complete immutable declaration inventory differs")
    methods = selected["methods"]
    require({name: complete[name] for name in methods} == methods
            and len(methods) == selected["expectedMethods"]
            and sum(value["case_count"] for value in methods.values()) == selected["declaredCases"],
            "Selected method/literal-case inventory differs")
    originals.unchanged()
    return dict(fixed_contract(lane), phase="SOURCE_DECLARATIONS_ONLY",
                complete_declarations=len(complete), source_inverse=restored,
                declaration_projection=projection)


def selection_plan(originals, lane):
    """Only exact original method IDs; no suite or wildcard fallback."""
    contract = declared_contract(originals, lane)
    profile, _ = _profile()
    selected = profile["lanes"][lane]
    selectors = list(selected["invocationSelectors"])
    require(selected["invocationScope"] == "exact-methods"
            and sorted(selectors) == contract["expected_compiled_identifiers"]
            and len(selectors) == len(set(selectors)) == contract["expected_methods"]
            and [value.replace(TARGET + "/", contract["original_target"] + "/", 1)
                 for value in selectors] == selected["originalSelectors"],
            "Only the exact original method map with an explicit host-target prefix is supported")
    return {"contract": contract, "proposed_invocation_selectors": selectors,
            "source_declarations_only": True, "execution_authorized": False}


def source_contract(originals, lane, *, source_commit, native_compilation_proof):
    """Read-only proof from a future already-admitted producer, not admission.

    Wave3 must pass its actual common-admitted source commit and producer's
    nativeCompilationProof. No source hash or source root is caller-configurable.
    """
    require(isinstance(source_commit, str) and re.fullmatch(r"[0-9a-f]{40}", source_commit)
            and isinstance(native_compilation_proof, dict)
            and isinstance(native_compilation_proof.get("path"), str)
            and re.fullmatch(r"[0-9a-f]{64}", native_compilation_proof.get("sha256", "")),
            "Actual admitted source/native compiler proof required; declaration evidence is insufficient")
    contract = declared_contract(originals, lane)
    rtl = originals.source / "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/rtl-current-editor-profile/rtl_hosted_profile.py"
    proof = originals.witness.verify_native_compiler_sources(
        originals.source, source_commit=source_commit, native_compilation_proof=native_compilation_proof,
        expected_sources=contract["source_hashes"], rtl_profile_path=rtl)
    require(proof["source_hashes"] == contract["source_hashes"] and proof["tests_executed"] == 0
            and proof["actual_native_compiler_witnesses"], "Exact actual native compiler witnesses required")
    return dict(contract, phase="SOURCE_AND_COMPILER_WITNESS_QUALIFIED", source_commit=source_commit,
                native_compilation_proof=copy.deepcopy(native_compilation_proof),
                actual_native_compiler_witnesses=proof["actual_native_compiler_witnesses"],
                witness_validator_sha256=proof["witness_validator_sha256"])


def _result_evidence(originals, lane, summary, tree, udid):
    """Pure existing evidence validators; caller still owes compiler/enumeration custody."""
    _originals(originals)
    profile, _ = _profile()
    selected = profile["lanes"][lane]
    suites = {selected["suite"]: {"methods": selected["methods"]}}
    expected = {selected["suite"] + "/" + name for name in selected["methods"]}
    observed = originals.host_results.validate_results(summary, tree, expected, udid)
    cases = originals.core_declarations.validate_arguments(tree, expected, suites)
    require(observed["counts"]["totalTestCount"] in {selected["expectedMethods"], selected["declaredCases"]}
            and cases["actual_method_count"] == selected["expectedMethods"]
            and cases["declared_case_count"] == selected["declaredCases"],
            "Exact original component method/argument execution is incomplete")
    return dict(observed, **cases)


class CompilerQualifiedProfile:
    """One fixed lane's validators; carries no runtime permission or process API.

    Keep this same instance for selection, actual enumeration and result checks.
    A new instance cannot inherit an earlier lane's enumeration observation.
    """
    def __init__(self, originals, lane, *, source_commit, native_compilation_proof):
        self.originals, self.lane = originals, lane
        self.contract = source_contract(originals, lane, source_commit=source_commit,
                                        native_compilation_proof=native_compilation_proof)
        self.enumeration = None

    def _unchanged(self):
        before = self.contract
        require(source_contract(self.originals, self.lane, source_commit=before["source_commit"],
                                native_compilation_proof=before["native_compilation_proof"]) == before,
                "Original source/compiler witness changed during this profile")

    def invocation_selectors(self, selectors):
        self._unchanged()
        require(sorted(selectors) == self.contract["expected_compiled_identifiers"]
                and len(selectors) == len(set(selectors)) == self.contract["expected_methods"],
                "Only the complete exact new method selection is supported")
        return selection_plan(self.originals, self.lane)["proposed_invocation_selectors"]

    def validate_enumeration(self, payload):
        require(self.enumeration is None, "One actual enumeration observation per lane instance required")
        self._unchanged()
        plan, enabled, disabled = self.originals.enumeration.enumerated_identifiers(payload)
        require(plan == TARGET and enabled == set(self.contract["expected_compiled_identifiers"])
                and not enabled.intersection(disabled),
                "Actual compiled new-method selection differs; never widen to the legacy suite")
        self.enumeration = copy.deepcopy(payload)
        return {"test_plan": plan, "actual_compiled_identifiers": sorted(enabled),
                "source_compiler_witness_qualified": True, "tests_executed": 0,
                "runtime_admission_performed": False}

    def validate_results(self, summary, tree, udid):
        require(self.enumeration is not None, "Actual same-instance compiled enumeration must precede results")
        self._unchanged()
        result = _result_evidence(self.originals, self.lane, summary, tree, udid)
        self._unchanged()
        return dict(result, profile_scope="hosted-hanlin-uikit23", original_target=self.contract["original_target"],
                    selected_target=TARGET, sourceContract=copy.deepcopy(self.contract),
                    applicationUIAccepted=False, nativePersistenceAccepted=False, nativeACLAccepted=False,
                    physicalDeviceAccepted=False, runtime_admission_performed=False)


def validators(originals, lane, *, source_commit, native_compilation_proof):
    """Exact equivalent of a native_core validator factory; keep one per lane."""
    return CompilerQualifiedProfile(originals, lane, source_commit=source_commit,
                                    native_compilation_proof=native_compilation_proof)


def invocation_selectors(selectors, qualified_profile):
    """Route through the same fixed compiler-qualified validator instance."""
    require(type(qualified_profile) is CompilerQualifiedProfile, "Actual fixed Hanlin UIKit23/23 validator instance required")
    return qualified_profile.invocation_selectors(selectors)


if __name__ == "__main__":
    require_runtime_ready()
