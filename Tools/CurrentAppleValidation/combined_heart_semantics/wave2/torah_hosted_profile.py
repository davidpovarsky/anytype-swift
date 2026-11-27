"""Exact selected regressions on an already admitted native host.

Related originates in PinkhaAnyUITests. It may receive AnytypeTests hosted
credit only when the shared producer proves direct compilation of the exact
original source in that target; package declarations alone never authorize it.
"""
import hashlib
from pathlib import Path

import run_host_tests as host
import wave15_core_profile as core
import shared_editor_existing_build as existing
import native_compiler_witness as witness

TARGET = "AnytypeTests"


def single():
    return {"parameters": [], "argument_collections": [], "case_count": 1}


SUITES = {
    "PropertyCreationSearchTests": {
        "source_path": "AnyTypeTests/Pinkha/PropertyCreationSearchTests.swift",
        "source_sha256": "69d7afd02929d0a0f8a220acff3ada1ac156e7cbed70294861cb8481ae06e236",
        "methods": {name: single() for name in (
            "latestQueryOwnsRowsAndErrors", "cancelledRequestDoesNotPublish", "preCancelledRequestDoesNotLoad",
            "nativeFailurePreservesOrdinaryChoices", "existingSearchFailureIsVisible", "retryKeepsQueryAndSpace",
            "catalogCancellationStopsAtTheSearchBoundary", "preCancelledCatalogDoesNotSearch",
            "providerCancellationPropagatesThroughLoaderAndPicker")},
    },
    "PropertyCreationSelectionTests": {
        "source_path": "AnyTypeTests/Pinkha/PropertyCreationSelectionTests.swift",
        "source_sha256": "833ce32686d7daf2907eb796aca8a79aa3a099ec1d5361d53a2d5949c5193baf",
        "methods": {name: single() for name in (
            "failureAndRetry", "pendingSelectionOwnsTheWrite", "cancellationDoesNotPublishFailure",
            "cancelledLateErrorDoesNotPublishFailure", "cancelledLateSuccessRetainsOutcomeWithoutPublishing",
            "preCancelledSelectionDoesNotWrite")},
    },
    "AnyNativeTorahRelatedIdentityTests": {
        "source_path": "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTorahRelatedIdentityTests.swift",
        "source_sha256": "af7e3270f8b29d56ade52603e648d2ef36bb6a07dfea8bc07b9d7c2d448d8095",
        "methods": {
            "matchingMetadataPreservesExactDocumentAndSource": single(),
            "mismatchedMetadataCannotBeDisplayed": {
                "parameters": [{"name": "foreignSpace", "type": "Bool"}],
                "argument_collections": [[False, True]], "case_count": 2},
            "mismatchedMetadataCannotAuthorizeUnlink": {
                "parameters": [{"name": "foreignSpace", "type": "Bool"}],
                "argument_collections": [[False, True]], "case_count": 2},
            "staleSourceRowCannotUnlinkTheCurrentSelection": single(),
            "currentReadOnlyMetadataCannotAuthorizeUnlink": single(),
        },
    },
    "TorahSearchResolutionPublicationTests": {
        "source_path": "AnyTypeTests/Pinkha/TorahSearchResolutionPublicationTests.swift",
        "source_sha256": "bf736097ed333279f80d0b2474211e301a191bd3613abd43808458428dc9fb12",
        "methods": {
            "referenceResolutionErrorBelongsToTheCurrentQuery": {
                "parameters": [{"name": "replaceQuery", "type": "Bool"}],
                "argument_collections": [[False, True]], "case_count": 2},
        },
    },
    "AnyLibrarySearchPublicationTests": {
        "source_path": "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift",
        "source_sha256": "e46dc67553d9e050c7955958cff56aac559c4d51eaa3b75e379029dd83f8d839",
        "methods": {name: single() for name in (
            "failedReplacementSearchCannotDisplayThePreviousQueryResults",
            "cancelledOlderReadCannotRepopulateAFailedReplacement")},
    },
}
PROFILES = {
    "properties-hosted": {"suites": ("PropertyCreationSearchTests", "PropertyCreationSelectionTests"),
                          "methods": 15, "cases": 15, "original_target": TARGET},
    "related-hosted": {"suites": ("AnyNativeTorahRelatedIdentityTests",),
                       "methods": 5, "cases": 7, "original_target": "PinkhaAnyUITests"},
    "inspector-hosted": {"suites": ("TorahSearchResolutionPublicationTests",),
                         "methods": 1, "cases": 2, "original_target": TARGET},
    "library-hosted": {"suites": ("AnyLibrarySearchPublicationTests",),
                       "methods": 2, "cases": 2, "original_target": "PinkhaAnyUITests"},
}
HOSTED_LANES = frozenset((*PROFILES, "rtl-hosted"))


def selected_suites(kind):
    core.require(kind in PROFILES, "Only the fixed reviewed regression profiles are supported")
    return {name: SUITES[name] for name in PROFILES[kind]["suites"]}


def declared_contract(app, kind):
    """Exact reviewed declarations; no permission to select or execute a suite."""
    app, suites = Path(app), selected_suites(kind)
    identifiers, methods = [], []
    for suite, specification in suites.items():
        text = (app / specification["source_path"]).read_bytes().decode("utf-8")
        core.require(hashlib.sha256(text.encode("utf-8")).hexdigest() == specification["source_sha256"],
                     "Reviewed hosted regression source changed: " + suite)
        core.require(core.inspect_declarations(text) == specification["methods"],
                     "Exact hosted methods/literal arguments changed: " + suite)
        for name, definition in specification["methods"].items():
            methods.append(suite + "/" + name)
            identifiers.append(TARGET + "/" + suite + "/" + name + "("
                               + "".join(parameter["name"] + ":" for parameter in definition["parameters"]) + ")")
    expected = PROFILES[kind]
    cases = sum(method["case_count"] for specification in suites.values() for method in specification["methods"].values())
    core.require(len(methods) == expected["methods"] and cases == expected["cases"], "Hosted profile scope differs")
    return dict(kind=kind, methods=sorted(methods), compiled_identifiers=sorted(identifiers),
                source_hashes={value["source_path"]: value["source_sha256"] for value in suites.values()},
                expected_methods=expected["methods"], declared_cases=cases, original_target=expected["original_target"],
                selected_target=TARGET, tests_executed=0)


def source_contract(app, kind, *, source_commit, native_compilation_proof, rtl_profile_path):
    contract = declared_contract(app, kind)
    actual = witness.verify_native_compiler_sources(
        app, source_commit=source_commit, native_compilation_proof=native_compilation_proof,
        expected_sources=contract["source_hashes"], rtl_profile_path=rtl_profile_path)
    core.require(actual["tests_executed"] == 0 and actual["source_hashes"] == contract["source_hashes"],
                 "Selected native source witness changed scope")
    return dict(contract, source_commit=source_commit, native_compilation_proof=native_compilation_proof,
                actual_native_compiler_witnesses=actual["actual_native_compiler_witnesses"],
                witness_validator_sha256=actual["witness_validator_sha256"],
                hosted_original_source_directly_compiled=True)


def invocation_selectors(selectors, contract):
    kind = contract.get("kind")
    suites = selected_suites(kind)
    expected = sorted(TARGET + "/" + suite + "/" + name + "("
                      + "".join(parameter["name"] + ":" for parameter in definition["parameters"]) + ")"
                      for suite, specification in suites.items() for name, definition in specification["methods"].items())
    core.require(contract.get("expected_methods") == PROFILES[kind]["methods"]
                 and contract.get("declared_cases") == PROFILES[kind]["cases"]
                 and contract.get("compiled_identifiers") == expected and sorted(selectors) == expected
                 and len(selectors) == len(set(selectors)) == PROFILES[kind]["methods"]
                 and contract.get("source_hashes") == {value["source_path"]: value["source_sha256"] for value in suites.values()}
                 and contract.get("selected_target") == TARGET
                 and contract.get("actual_native_compiler_witnesses") and contract.get("native_compilation_proof")
                 and contract.get("hosted_original_source_directly_compiled") is True,
                 "Complete source/compiler-qualified hosted suites required")
    # Preserve the original Xcode27 parameterized Swift Testing workaround.
    return [TARGET + "/" + suite for suite in sorted(suites)]


class OriginalValidators:
    def __init__(self, kind):
        self.kind = kind
        self.suites = selected_suites(kind)

    def validate_enumeration(self, payload, contract):
        core.require(contract["kind"] == self.kind, "Hosted enumeration profile differs")
        invocation_selectors(contract["compiled_identifiers"], contract)
        plan, enabled, disabled = existing.enumerated_identifiers(payload)
        core.require(plan == TARGET and enabled == set(contract["compiled_identifiers"])
                     and not enabled.intersection(disabled), "Exact compiled hosted selection is incomplete")
        return dict(test_plan=plan, identifiers=sorted(enabled), tests_executed=0)

    def validate_results(self, summary, tree, udid):
        expected = {suite + "/" + name for suite, specification in self.suites.items() for name in specification["methods"]}
        actual = host.validate_results(summary, tree, expected, udid)
        cases = core.validate_arguments(tree, expected, self.suites)
        specification = PROFILES[self.kind]
        core.require(actual["counts"]["totalTestCount"] in {specification["methods"], specification["cases"]}
                     and cases["actual_method_count"] == specification["methods"]
                     and cases["declared_case_count"] == specification["cases"], "Actual hosted method/argument execution is incomplete")
        return dict(actual, **cases)


def validators(kind):
    return OriginalValidators(kind)


def run_hosted(consumer, lane, directory, udid):
    """Only the common-admitted producer may supply the native proof pin."""
    core.require(lane in HOSTED_LANES and consumer.source_admission.get("commit") == consumer.binding["sourceSHA"],
                 "Actual common source admission is required before hosted selection")
    core.require(consumer.admission.get("deviceFamily") == "ipad",
                 "The unchanged original hosted-result validator requires its OS27 iPad scope")
    shared = consumer.shared_module
    producer = shared.decode(shared.pinned(consumer.admission["producerReceipt"]))
    pin = producer.get("nativeCompilationProof")
    core.require(isinstance(pin, dict), "Actual admitted producer has no native compilation proof")
    import rtl_hosted_profile as rtl
    rtl_path = Path(rtl.__file__).resolve()

    def current_contract():
        if lane == "rtl-hosted":
            return rtl.source_contract(consumer.source, source_commit=consumer.binding["sourceSHA"], native_compilation_proof=pin)
        return source_contract(consumer.source, lane, source_commit=consumer.binding["sourceSHA"],
                               native_compilation_proof=pin, rtl_profile_path=rtl_path)

    before = current_contract()
    methods = [identifier.removeprefix(TARGET + "/") for identifier in before["compiled_identifiers"]]
    actual, _ = consumer.stage(directory, "native", udid, methods, {}, allowance=300, host_contract=before)
    core.require(current_contract() == before, "Selected source/compiler proof changed during hosted execution")
    return {"native": actual, "sourceContract": before,
            "actualNativeACLAccepted": False, "actualNativePersistenceAccepted": False,
            "applicationUIAccepted": False, "physicalDeviceAccepted": False}
