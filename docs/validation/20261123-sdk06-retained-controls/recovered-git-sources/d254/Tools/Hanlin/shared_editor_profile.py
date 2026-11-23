"""The reviewed UIKit boundary affected by shared local-edit ownership."""
import wave15_core_profile as core

SUITE = "TextBlockFocusLifecycleTests"

def plain():
    return dict(parameters=[], argument_collections=[], case_count=1)

METHODS = {
    "sameInputOwnerSurvivesForkAndExplicitReplacementEndsComposition": plain(),
    "reusedCellDoesNotPreserveDifferentPendingOwner": dict(
        parameters=[dict(name="composing", type="Bool")],
        argument_collections=[[False, True]], case_count=2),
    "pendingLocalTextSurvivesNativeReconfiguration": plain(),
    "completedLocalTextAcceptsRemoteReplacement": plain(),
    "initialFocusWaitsForAttachment": plain(),
    "explicitHandoffDoesNotReplayInitialCaret": plain(),
    "requestIdentityParticipatesInCellConfigurationEquality": plain(),
    "staleFocusDoesNotSurviveRowLifetime": dict(
        parameters=[dict(name="change", type="String")],
        argument_collections=[["rebind", "detach", "editorContext"]], case_count=3),
    "reusedCellUsesCurrentLockBeforeFocus": dict(
        parameters=[dict(name="newLocked", type="Bool")],
        argument_collections=[[False, True]], case_count=2),
    "insertedCellUsesCurrentEditingBeforeFocus": dict(
        parameters=[dict(name="editing", type="Bool")],
        argument_collections=[[False, True]], case_count=2),
}

def validate_source(text):
    declarations = core.inspect_declarations(text)
    core.require(all(declarations.get(name) == expected for name, expected in METHODS.items()),
                 "Shared-editor named declarations or literal argument cases changed")
    return set(METHODS)

def validate_arguments(tree, expected):
    return core.validate_arguments(tree, expected, {SUITE: {"methods": METHODS}})
