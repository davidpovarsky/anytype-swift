"""Four exact future hosted suites; no product admission or runtime approval.

The package originals must be compiled directly by the admitted AnytypeTests
target. The old Properties search/selection 15-test profile is independent.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

TARGET = "AnytypeTests"
CLOSED_PROFILE = "native-core-closed-profile.json"


def single():
    return {"parameters": [], "argument_collections": [], "case_count": 1}


SUITES = {
    "AnyNativePropertyPresentationTests": {
        "source_path": "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift",
        "source_sha256": "7df1a45aa85cd71bc7ec8353b98150609bc2d2fb07a2aa1ebf08f7fb40fdab61",
        "framework": "Swift Testing",
        "methods": {name: single() for name in (
            "delayedReviewCannotRestoreOldTypeOrEraseAcknowledgedUndo",
            "delayedReadFailureCannotReplaceAcknowledgedWriteFeedbackOrUndo",
            "delayedRefreshCannotRevealAnAcknowledgedHiddenProperty",
            "refreshDuringWriteDoesNotDispatchOrReportMissingWorkspace",
            "supersededReadFailureCannotClearNewerReadSpinnerOrFeedback",
            "oldReadCannotPublishOrClearLoadingAfterOwnerReactivation",
            "oldWriteCompletionCannotClearNewOwnerSavingStateOrPublishFailure",
            "currentReadFailureDiscardsDisplayedValuesAndUndoUntilReviewed",
            "deactivationDiscardsDisplayedValuesAndUndoBeforeNewOwnerRead",
        )},
    },
    "AnyNativeTextBlockCreationTests": {
        "source_path": "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextBlockCreationTests.swift",
        "source_sha256": "e36af9a049013d2e19453849170ee2deac65d189d1c9603cf75c3f47b71a037e",
        "framework": "Swift Testing",
        "methods": {name: single() for name in (
            "existingParagraphAndInspectorQuoteKeepTheirOriginalStyleCarrier",
            "distinctChoicesRoundTripThroughNativeIntentAndExistingDisplayPolicies",
        )},
    },
    "AnyNativeTextTypographyTests": {
        "source_path": "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextTypographyTests.swift",
        "source_sha256": "fde5f3bd8da14f0f3e6502d60cacdf3304ea78aba9c41b35ca73317995cdff07",
        "framework": "XCTest",
        "methods": {name: single() for name in (
            "testNativeHeadingLevelsAndCodeUseOriginalAnytypeFacesAtBothSizes",
            "testFontRefreshRetainsHeadingEmphasisInlineCodeRTLSelectionAndMarkedBuffer",
        )},
    },
    "AnyNativeTextRendererTests": {
        "source_path": "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift",
        "source_sha256": "695c89e5c8d5ad8e41f8ec525486836e42338bcc063d13f0945080c169fd7eaa",
        "framework": "XCTest",
        "methods": {name: single() for name in (
            "testEqualNativeTextChangesAttributesWithoutReplacingCharactersOrSelection",
            "testChangedNativeTextReplacesCharactersAndKeepsValidSelection",
            "testMarkedTextKeepsCharactersSelectionAndAttributesUntilCommit",
        )},
    },
}
PROFILES = {
    "native-properties-hosted": {"suite": "AnyNativePropertyPresentationTests", "methods": 9, "cases": 9},
    "native-block-creation-hosted": {"suite": "AnyNativeTextBlockCreationTests", "methods": 2, "cases": 2},
    "native-typography-hosted": {"suite": "AnyNativeTextTypographyTests", "methods": 2, "cases": 2},
    "native-renderer-hosted": {"suite": "AnyNativeTextRendererTests", "methods": 3, "cases": 3},
}
HOSTED_LANES = frozenset(PROFILES)
PLANS = frozenset(lane + "-only" for lane in HOSTED_LANES)


def require(value, message):
    if not value:
        raise ValueError(message)


def require_runtime_ready(admission, parent):
    """A mutable ready flag cannot authorize this still-unqualified tranche."""
    require(admission.get("plan") in PLANS, "Only the four fixed future native-core plans are supported")
    require(Path(parent).is_dir(), "The exact future control closure must exist")
    raise ValueError("Future native-core runtime is closed: a reviewed matching source freeze, successful shared producer and exact admission are still required")


def selected(kind):
    require(kind in PROFILES, "Only the four fixed native-core suites are supported")
    profile = PROFILES[kind]
    return profile, profile["suite"], SUITES[profile["suite"]]


def fixed_contract(kind):
    profile, suite, specification = selected(kind)
    methods = sorted(suite + "/" + name for name in specification["methods"])
    require(len(methods) == profile["methods"] == profile["cases"],
                 "Exact unparameterized native-core method inventory changed")
    return {
        "kind": kind,
        "framework": specification["framework"],
        "methods": methods,
        "compiled_identifiers": [TARGET + "/" + method + "()" for method in methods],
        "source_hashes": {specification["source_path"]: specification["source_sha256"]},
        "expected_methods": profile["methods"],
        "declared_cases": profile["cases"],
        "original_target": "PinkhaAnyUITests",
        "selected_target": TARGET,
        "tests_executed": 0,
    }


def declared_contract(app, kind):
    import wave15_core_profile as core
    profile, suite, specification = selected(kind)
    data = (Path(app) / specification["source_path"]).read_bytes()
    require(hashlib.sha256(data).hexdigest() == specification["source_sha256"],
                 "Exact original native-core test source changed: " + suite)
    text = data.decode("utf-8")
    if specification["framework"] == "Swift Testing":
        require(core.inspect_declarations(text) == specification["methods"],
                     "Original native-core Swift Testing declaration inventory changed")
    else:
        # Only these two exact whole-source-pinned UIKit XCTest classes are
        # supported. Typography keeps its original throwing signature; the
        # existing Renderer3 methods are parameterless and non-throwing.
        exact_xctest = {
            "AnyNativeTextTypographyTests": (2, " throws"),
            "AnyNativeTextRendererTests": (3, ""),
        }
        require(suite in exact_xctest
                     and text.count("@MainActor\nfinal class " + suite + ": XCTestCase {") == 1
                     and "@Test" not in text,
                     "Exact UIKit XCTest class declaration changed")
        count, signature_suffix = exact_xctest[suite]
        methods = re.findall(r"^    func (test[A-Za-z0-9_]+)\(\)" + signature_suffix + r" \{", text, flags=re.M)
        require(len(methods) == len(set(methods)) == count
                     and set(methods) == set(specification["methods"])
                     and len(re.findall(r"\bfunc\s+test[A-Za-z0-9_]+", text)) == count,
                     "Exact fixed UIKit XCTest declarations changed")
    return fixed_contract(kind)


def source_contract(app, kind, *, source_commit, native_compilation_proof, rtl_profile_path):
    import native_compiler_witness as witness
    contract = declared_contract(app, kind)
    actual = witness.verify_native_compiler_sources(
        app, source_commit=source_commit, native_compilation_proof=native_compilation_proof,
        expected_sources=contract["source_hashes"], rtl_profile_path=rtl_profile_path)
    require(actual["tests_executed"] == 0 and actual["source_hashes"] == contract["source_hashes"],
                 "Original compiler witness changed the selected native-core scope")
    return dict(contract, source_commit=source_commit, native_compilation_proof=native_compilation_proof,
                actual_native_compiler_witnesses=actual["actual_native_compiler_witnesses"],
                witness_validator_sha256=actual["witness_validator_sha256"],
                hosted_original_source_directly_compiled=True)


def invocation_selectors(selectors, contract):
    kind = contract.get("kind")
    expected = fixed_contract(kind)
    require(all(contract.get(key) == value for key, value in expected.items())
                 and sorted(selectors) == expected["compiled_identifiers"]
                 and len(selectors) == len(set(selectors)) == expected["expected_methods"]
                 and contract.get("actual_native_compiler_witnesses")
                 and contract.get("native_compilation_proof")
                 and contract.get("hosted_original_source_directly_compiled") is True,
                 "Complete exact source/compiler-qualified native-core contract required")
    # Retain the existing suite-selection workaround and exact enumeration gate.
    # It also avoids changing native XCTest method spelling on the command line.
    return [TARGET + "/" + PROFILES[kind]["suite"]]


class OriginalValidators:
    def __init__(self, kind):
        self.kind = kind
        _, suite, specification = selected(kind)
        self.suites = {suite: specification}

    def validate_enumeration(self, payload, contract):
        import shared_editor_existing_build as existing
        require(contract["kind"] == self.kind, "Native-core enumeration profile differs")
        invocation_selectors(contract["compiled_identifiers"], contract)
        plan, enabled, disabled = existing.enumerated_identifiers(payload)
        require(plan == TARGET and enabled == set(contract["compiled_identifiers"])
                     and not enabled.intersection(disabled),
                     "Every exact native-core compiled method must be present with no extra method")
        return {"test_plan": plan, "identifiers": sorted(enabled), "tests_executed": 0}

    def validate_results(self, summary, tree, udid):
        import run_host_tests as host
        import wave15_core_profile as core
        expected = {suite + "/" + method for suite, value in self.suites.items() for method in value["methods"]}
        actual = host.validate_results(summary, tree, expected, udid)
        # Both frameworks have exact parameterless Test Case nodes here. Reuse
        # the original node/argument validator with this fixed source inventory;
        # in-method loops never become separately credited XCTest cases.
        cases = core.validate_arguments(tree, expected, self.suites)
        scope = PROFILES[self.kind]
        require(actual["counts"]["totalTestCount"] == scope["methods"]
                     and cases["actual_method_count"] == scope["methods"]
                     and cases["declared_case_count"] == scope["cases"],
                     "Actual native-core method/case execution is incomplete")
        return dict(actual, **cases)


def validators(kind):
    return OriginalValidators(kind)


def run_hosted(consumer, lane, directory, udid):
    """Use the admitted producer's exact proof, never an independently supplied pin."""
    require_runtime_ready(consumer.admission, Path(__file__).resolve().parent)
    require(lane in HOSTED_LANES
                 and consumer.source_admission.get("commit") == consumer.binding["sourceSHA"],
                 "Actual complete common source admission is required")
    require(consumer.admission.get("deviceFamily") == "ipad",
                 "Unchanged original hosted validators require the OS27 iPad scope")
    shared = consumer.shared_module
    producer = shared.decode(shared.pinned(consumer.admission["producerReceipt"]))
    pin = producer.get("nativeCompilationProof")
    require(isinstance(pin, dict), "Actual admitted producer lacks its native compiler proof")
    import rtl_hosted_profile as rtl
    def current_contract():
        return source_contract(consumer.source, lane, source_commit=consumer.binding["sourceSHA"],
                               native_compilation_proof=pin, rtl_profile_path=Path(rtl.__file__).resolve())
    before = current_contract()
    methods = [value.removeprefix(TARGET + "/") for value in before["compiled_identifiers"]]
    actual, _ = consumer.stage(directory, "native", udid, methods, {}, allowance=300, host_contract=before)
    require(current_contract() == before, "Native-core source/compiler proof changed during execution")
    return {
        "native": actual, "sourceContract": before,
        "actualNativeACLAccepted": False, "actualNativePersistenceAccepted": False,
        "applicationUIAccepted": False, "physicalDeviceAccepted": False,
    }
