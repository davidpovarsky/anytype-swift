"""Exact Heart related-read error mapping in the necessary SDK06 Debug build.

This is adapter classification evidence, not signed native ACL acceptance.
Original raw xcresult argument nodes must qualify both Bool invocations.
"""
import wave15_core_profile as core

SUITE = "TorahRelatedReadAuthorityMappingTests"
SOURCE_PATH = "AnyTypeTests/Pinkha/TorahRelatedReadAuthorityMappingTests.swift"
EXPECTED_METHOD_COUNT = 2
DECLARED_CASE_COUNT = 3

METHODS = {
    "nativeDenialRequiresExactTypedCodeAndDescription": {
        "parameters": [{"name": "objectShow", "type": "Bool"}],
        "argument_collections": [[False, True]], "case_count": 2,
    },
    "providerAndTransportDescriptionsCannotForgeNativeAuthority": {
        "parameters": [], "argument_collections": [], "case_count": 1,
    },
}


def validate_source(text):
    declarations = core.inspect_declarations(text)
    core.require(declarations == METHODS,
                 "Heart related-read authority declarations or literal argument cases changed")
    core.require(len(METHODS) == EXPECTED_METHOD_COUNT
                 and sum(value["case_count"] for value in METHODS.values()) == DECLARED_CASE_COUNT,
                 "Heart related-read authority selection is inconsistent")
    return set(METHODS)


def validate_arguments(tree, expected):
    return core.validate_arguments(tree, expected, {SUITE: {"methods": METHODS}})
