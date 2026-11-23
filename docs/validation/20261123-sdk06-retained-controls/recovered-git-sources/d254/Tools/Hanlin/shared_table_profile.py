"""Exact actual-handler table scope for the existing SDK06 application build.

This declares source methods and raw literal argument cases; it does not infer
argument execution from an aggregate xcresult count.
"""
import wave15_core_profile as core

SUITE = "SimpleTableTextPersistenceTests"
SOURCE_PATH = "AnyTypeTests/Pinkha/SimpleTableTextPersistenceTests.swift"
EXPECTED_METHOD_COUNT = 11
DECLARED_CASE_COUNT = 14

def plain():
    return dict(parameters=[], argument_collections=[], case_count=1)

def boolean(name):
    return dict(parameters=[dict(name=name, type="Bool")],
                argument_collections=[[False, True]], case_count=2)

METHODS = {
    "acceptedSnapshotSurvivesViewReuse": plain(),
    "laterDraftKeepsTheLatestAcceptedSnapshot": plain(),
    "nativeRejectionKeepsTheTableDirty": plain(),
    "defocusCommitsTheDeferredSearchBuffer": plain(),
    "rowRebindCannotWriteIntoTheNewOwner": plain(),
    "structuralKeyWaitsForAcceptedText": plain(),
    "replacementClaimsPendingOwnershipBeforePublication": boolean("asyncEntry"),
    "markdownStyleWaitsForEarlierNativeWrite": plain(),
    "markdownCommandsKeepCapturedTextBeforeLaterTyping": boolean("addBlock"),
    "markdownAddBlockDoesNotContinueAfterOwnerRebind": boolean("returnToOriginalID"),
    "queuedMarkdownCommandIsRetiredWhenRowChanges": plain(),
}

def validate_source(text):
    declarations = core.inspect_declarations(text)
    core.require(declarations == METHODS,
                 "Table named declarations or exact literal argument cases changed")
    core.require(len(METHODS) == EXPECTED_METHOD_COUNT
                 and sum(x["case_count"] for x in METHODS.values()) == DECLARED_CASE_COUNT,
                 "Table source method or argument scope is inconsistent")
    return set(METHODS)

def validate_arguments(tree, expected):
    return core.validate_arguments(tree, expected, {SUITE: {"methods": METHODS}})
