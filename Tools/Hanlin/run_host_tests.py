#!/usr/bin/env python3
"""Run one reviewed component profile on a fresh, source-bound OS27 test host.

The default SDK06 profile and the optional editor profile have separate receipts.
Neither profile proves native UI, real account writes, or provider networking.
"""
import argparse
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import subprocess
import sys

from host_command import CommandCancelled, cancellation_signals, command
import wave15_core_profile as core_profile


BRANCH = "codex/chatgpt-wave15-integration-20261118"
CONFIGURATION = "Debug-Anytype"
SUITES = {
    "HanlinHostAdapterTests": 32,
    "HanlinHostWriteTests": 12,
    "HanlinHostReadWriteTests": 17,
    "HanlinSDKConsumerTests": 6,
}
SDK_RETURN_METHODS = {
    "nativeReturnReceiptCompletesOnceWithoutRearmingExecution",
    "nativeReturnHandoffCannotBeMintedTwiceOrForAnAliasedTarget",
    "nativeReturnCannotAcknowledgeQueuedOrDifferentMountedTargets",
    "cancelledOrExpiredNativeReturnNeverRunsMountValidation",
    "nativeReturnScopeLossPreservesQueuedReceiptWithoutRetry",
    "reentrantNativeReturnCancellationCannotPublishMountedReceipt",
}
SDK_SELECTION_METHODS = {
    "nativeSelectionCurrentValueIsCheckedWithoutSkippingFirstEmission",
    "nativeSelectionDoneAndReselectCannotRestoreEitherFence",
    "nativeSelectionChangedOrderAndUnicodeAliasCannotRearmAuthority",
    "nativeSelectionTableAndNonselectionModesUseTheEmittedValue",
}
SDK_BUDGET_METHOD = "HanlinSDKConsumerTests/canonicalDispatcherBudgetsReachReadAndReplayOnlyReceipt"
SDK_BUDGET_ARGUMENTS = ("1048576", "8388608")
EDITOR_SUITE = "TorahQuoteInsertionTests"
EDITOR_METHODS = {
    "delayedDropDoesNotRegainAuthorityOnReactivation": None,
    "staleInspectorInsertionIsRejected": "dismiss",
    "deniedDropDoesNotCreateTextOrMetadata": None,
    "dropDeduplicationIsPerGesture": None,
    "dropLifetimeIsIndependentOfInspectorPresentation": None,
    "revocationDuringBlockResponseStopsMetadata": None,
    "lateBlockResponseDoesNotMutateTheNewLifetime": None,
    "lateInspectorResponseDoesNotReplaceNewSelectionStatus": None,
    "metadataWriteRevalidatesAfterSuspendedNativeRead": "cancel",
    "inspectorInsertionPersistsConfirmedCanonicalMetadata": None,
}


class HostTestProfile(str, Enum):
    SDK06 = "sdk06"
    EDITOR = "editor"
    CORE = "wave15-core"
    COMPONENTS = "wave15-components"

    @property
    def suites(self):
        if self is self.COMPONENTS:
            return {name: count for part in (self.SDK06, self.EDITOR, self.CORE)
                    for name, count in part.suites.items()}
        if self is self.SDK06:
            return SUITES
        if self is self.EDITOR:
            return {EDITOR_SUITE: len(EDITOR_METHODS)}
        return core_profile.suite_counts()

    @property
    def result_prefix(self):
        return {self.SDK06: "sdk06", self.EDITOR: "editor-host", self.CORE: "wave15-core",
                self.COMPONENTS: "wave15-components"}[self]

    @property
    def pass_status(self):
        return {self.SDK06: "SDK06_COMPONENT_PASS", self.EDITOR: "EDITOR_COMPONENT_PASS",
                self.CORE: "WAVE15_CORE_COMPONENT_PASS",
                self.COMPONENTS: "WAVE15_ALL_COMPONENTS_PASS"}[self]


class EditorEvidenceReviewPending(ValueError):
    """Raw Apple evidence exists, but its argument representation is unrecognized."""


LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_identity(head, expected_sha, branch, expected_branch, run_id, attempt):
    require(expected_branch == BRANCH and branch == expected_branch, "Wrong SDK integration branch")
    require(re.fullmatch(r"[0-9a-f]{40}", expected_sha or "") and head == expected_sha,
            "Actual source SHA differs from the workflow run")
    require(re.fullmatch(r"[1-9][0-9]*", run_id or "") and re.fullmatch(r"[1-9][0-9]*", attempt or ""),
            "Missing actual run/attempt identity")


def expected_methods(app, profile=HostTestProfile.SDK06):
    """Read tracked sources; editor additionally requires exact reviewed arguments."""
    methods, files = set(), {}
    if profile is HostTestProfile.COMPONENTS:
        for part in (HostTestProfile.SDK06, HostTestProfile.EDITOR, HostTestProfile.CORE):
            part_methods, part_files = expected_methods(app, part)
            if part is HostTestProfile.SDK06:
                require(SDK_BUDGET_METHOD in part_methods, "Reviewed SDK budget method disappeared")
                for path in part_files:
                    validate_sdk_declarations((app / path).read_text(encoding="utf-8"), Path(path).stem)
            require(not methods.intersection(part_methods) and not files.keys() & part_files.keys(),
                    "Component source scopes overlap")
            methods.update(part_methods)
            files.update(part_files)
        return methods, files
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    for suite, minimum in profile.suites.items():
        candidates = [p for p in tracked if p.casefold() == f"AnytypeTests/Pinkha/{suite}.swift".casefold()]
        require(len(candidates) == 1, "Missing or case-colliding tracked SDK suite: " + suite)
        actual = app / candidates[0]
        synced = app / "AnytypeTests/Pinkha" / (suite + ".swift")
        require(synced.is_file() and actual.samefile(synced), "Suite absent from Xcode synchronized root: " + suite)
        text = actual.read_text(encoding="utf-8")
        names = (sorted(core_profile.validate_source(text, core_profile.load_manifest()[suite]))
                 if profile is HostTestProfile.CORE else
                 re.findall(r"@Test(?:\([^\n]*\))?\s+func\s+(\w+)\s*\(", text))
        require(len(set(names)) == len(names) and len(names) >= minimum,
                "Reviewed SDK test declarations disappeared: " + suite)
        if profile is HostTestProfile.SDK06 and suite == "HanlinHostAdapterTests":
            require(SDK_RETURN_METHODS.issubset(names), "Reviewed native return test declarations disappeared")
            require(SDK_SELECTION_METHODS.issubset(names), "Reviewed native selection test declarations disappeared")
        if profile is HostTestProfile.EDITOR:
            declarations = re.findall(r"@Test(?:\(([^\n]*)\))?\s+func\s+(\w+)\s*\(([^)]*)\)", text)
            require(set(names) == set(EDITOR_METHODS), "Reviewed editor method set changed")
            require(len(declarations) == len(EDITOR_METHODS), "Unrecognized editor test declaration")
            for attributes, name, parameters in declarations:
                parameter = EDITOR_METHODS[name]
                if parameter is None:
                    require(not parameters.strip() and "arguments:" not in attributes,
                            "Unexpected editor argument declaration: " + name)
                else:
                    require(parameters.strip() == parameter + ": Bool"
                            and re.search(r"\barguments\s*:\s*\[\s*false\s*,\s*true\s*\]", attributes),
                            "Reviewed editor Bool arguments changed: " + name)
        methods.update(suite + "/" + name for name in names)
        files[candidates[0]] = sha256(actual)
    return methods, files


def test_cases(tree):
    found = {}

    def visit(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                name = value.get("nodeIdentifier")
                require(isinstance(name, str) and name and name not in found,
                        "Unnamed or duplicate xcresult test case")
                found[name] = value.get("result")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(tree)
    return found


def validate_results(summary, tree, expected, udid, profile=HostTestProfile.SDK06):
    counts = {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(all(type(value) is int for value in counts.values()), "Missing integer xcresult counts")
    require(counts["totalTestCount"] >= len(expected) > 0, "Zero or incomplete SDK test selection")
    require(counts["passedTests"] == counts["totalTestCount"] and counts["failedTests"] == counts["skippedTests"] == 0,
            "Failed or skipped SDK tests")
    configurations = summary.get("devicesAndConfigurations", [])
    require(len(configurations) == 1, "Expected one actual test destination")
    device = configurations[0].get("device", {})
    require(device.get("deviceId") == udid and device.get("osVersion", "").split(".")[0] == "27"
            and device.get("osBuildNumber") and device.get("architecture") == "arm64"
            and "iPad" in device.get("modelName", ""), "Raw xcresult device differs from disposable OS27 iPad")
    cases = test_cases(tree)
    require(cases and all(result == "Passed" for result in cases.values()), "Missing or nonpassing actual test cases")
    observed = set()
    for identifier in cases:
        matches = [method for method in expected if re.search(r"(?:^|/)" + re.escape(method) + r"(?:\(|/|$)", identifier)]
        require(len(matches) == 1, ("Unexpected xcresult test outside the four SDK suites: "
                                  if profile is HostTestProfile.SDK06 else "Unexpected xcresult editor test: ") + identifier)
        observed.add(matches[0])
    require(observed == expected, "Missing SDK test methods: " + ", ".join(sorted(expected - observed)))
    result = dict(counts=counts, methods=sorted(observed), actual_cases=cases, device=device)
    if profile is HostTestProfile.EDITOR:
        result.update(validate_editor_arguments(tree, expected))
        # Some xcresult versions summarize parameterized methods, while the
        # tree contains the distinct argument cases. Preserve the raw count;
        # never infer execution of an argument from this aggregate alone.
        require(counts["totalTestCount"] in {len(EDITOR_METHODS), result["declared_case_count"]},
                "Editor summary does not describe the exact methods or argument cases")
    if profile is HostTestProfile.CORE:
        result.update(core_profile.validate_arguments(tree, expected))
        require(counts["totalTestCount"] in {41, 57},
                "Core summary differs from its exact method or literal-case scope")
    if profile is HostTestProfile.COMPONENTS:
        result["components"] = validate_component_arguments(tree, expected)
        result["actual_method_count"] = len(expected)
        result["declared_case_count"] = sum(part["declared_case_count"] for part in result["components"].values())
        require(counts["totalTestCount"] in {len(expected), result["declared_case_count"]},
                "Combined summary differs from exact source-bound method or argument execution count")
    return result


def validate_component_arguments(tree, expected):
    """Keep original case nodes and apply each existing argument contract.

    The combined raw summary is retained once. No per-component xcresult summary
    or passed-test aggregate is invented from that total.
    """
    nodes = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(tree)
    components, assigned = {}, set()
    for part in (HostTestProfile.SDK06, HostTestProfile.EDITOR, HostTestProfile.CORE):
        names = {name for name in expected if name.split("/", 1)[0] in part.suites}
        require(names and not assigned.intersection(names), "Missing or overlapping component selection")
        selected = [node for node in nodes if any(re.search(
            r"(?:^|/)" + re.escape(name) + r"(?:\(|/|$)", node["nodeIdentifier"]) for name in names)]
        require(len(selected) == len(names), "Component method has missing or duplicate actual terminals")
        detail = dict(methods=sorted(names), actual_method_count=len(selected),
                      actual_cases={node["nodeIdentifier"]: node["result"] for node in selected})
        if part is HostTestProfile.SDK06:
            detail.update(validate_sdk_arguments(selected, names))
        elif part is HostTestProfile.EDITOR:
            detail.update(validate_editor_arguments(selected, names))
        elif part is HostTestProfile.CORE:
            detail.update(core_profile.validate_arguments(selected, names))
        components[part.value] = detail
        assigned.update(names)
    require(assigned == expected and len(nodes) == len(expected),
            "Combined execution includes unassigned or repeated methods")
    return components


def validate_sdk_declarations(text, suite):
    """The combined count uses the one reviewed SDK literal argument matrix."""
    declarations = re.findall(r"@Test(?:\(([^\n]*)\))?\s+func\s+(\w+)\s*\(([^)]*)\)", text)
    require(len(declarations) == text.count("@Test"), "Unrecognized combined SDK test declaration")
    for attributes, name, parameters in declarations:
        if suite + "/" + name == SDK_BUDGET_METHOD:
            require(parameters.strip() == "budget: Int" and re.fullmatch(
                r"\s*arguments:\s*\[\s*1_048_576\s*,\s*8\s*\*\s*1_048_576\s*\]\s*", attributes),
                "Reviewed SDK literal budget declarations changed")
        else:
            require(not parameters.strip() and "arguments:" not in attributes,
                    "Unreviewed SDK argument declaration in combined profile")


def validate_sdk_arguments(nodes, expected):
    """Bind SDK argument counts to the exact values seen in original Apple evidence."""
    require(SDK_BUDGET_METHOD in expected, "Missing SDK budget selection")
    actual, seen = {}, set()
    for node in nodes:
        identifier = node["nodeIdentifier"]
        names = [name for name in expected if identifier in {
            name + ("(budget:)" if name == SDK_BUDGET_METHOD else "()"),
            "AnytypeTests/" + name + ("(budget:)" if name == SDK_BUDGET_METHOD else "()")}]
        require(len(names) == 1 and names[0] not in seen, "Unknown or repeated SDK method signature")
        name = names[0]
        seen.add(name)
        descendants = []
        def descend(child):
            require(isinstance(child, dict) and child.get("nodeType") in
                    {"Arguments", "Repetition", "Test Case Run"} and child.get("result") == "Passed",
                    "Unknown, failed or skipped SDK execution descendant")
            descendants.append(child)
            children = child.get("children", [])
            require(isinstance(children, list), "Malformed SDK execution children")
            for value in children:
                descend(value)
        children = node.get("children", [])
        require(isinstance(children, list), "Malformed SDK method children")
        for child in children:
            descend(child)
        arguments = [child for child in descendants if child["nodeType"] == "Arguments"]
        if name == SDK_BUDGET_METHOD:
            require(len(arguments) == 2 and {child.get("name") for child in arguments} == set(SDK_BUDGET_ARGUMENTS),
                    "SDK budget arguments differ from the two exact source-bound executions")
            actual[name] = [dict(node_identifier=identifier, argument_display=child["name"], result="Passed")
                            for child in arguments]
        else:
            require(not arguments, "Nonparameterized SDK method gained argument execution")
            actual[name] = [dict(node_identifier=identifier, result="Passed")]
    require(seen == expected, "Missing actual SDK method")
    return dict(declared_case_count=sum(len(values) for values in actual.values()), sdk_cases=actual,
                argument_evidence="EXACT_1_MIB_AND_8_MIB_SOURCE_BOUND_VALUES_AND_ACTUAL_TERMINALS")


def validate_editor_arguments(tree, expected):
    """Recognize actual Test Case -> Arguments nodes, never count a method twice.

    Xcode's Arguments children have display values, not unique nodeIdentifier
    fields. Unknown representations remain review-pending with raw data retained.
    """
    require(expected == {EDITOR_SUITE + "/" + name for name in EDITOR_METHODS},
            "Editor result contract differs from the reviewed method set")
    nodes = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(tree)
    if len(nodes) != len(EDITOR_METHODS):
        raise EditorEvidenceReviewPending("Unrecognized editor method/argument tree; expected ten method nodes")
    actual = {}
    for node in nodes:
        identifier = node["nodeIdentifier"]
        names = [name for name, parameter in EDITOR_METHODS.items()
                 if identifier in {EDITOR_SUITE + "/" + name + "(" + (parameter + ":" if parameter else "") + ")",
                                   "AnytypeTests/" + EDITOR_SUITE + "/" + name + "(" + (parameter + ":" if parameter else "") + ")"}]
        require(len(names) == 1 and names[0] not in actual, "Unexpected or duplicate full editor method identity")
        name = names[0]
        descendants = []

        def descend(value):
            require(isinstance(value, dict), "Malformed editor result descendant")
            descendants.append(value)
            children = value.get("children", [])
            require(isinstance(children, list), "Malformed editor result children")
            for child in children:
                descend(child)

        for child in node.get("children", []):
            descend(child)
        for child in descendants:
            if "result" in child:
                require(child["result"] == "Passed", "Failed or skipped editor descendant result")
            if child.get("nodeType") not in {"Arguments", "Repetition", "Test Case Run"}:
                raise EditorEvidenceReviewPending("Unrecognized editor execution child: " + str(child.get("nodeType")))
            require(child.get("result") == "Passed", "Failed, skipped, or missing editor argument/run result")
        arguments = [child for child in descendants if child.get("nodeType") == "Arguments"]
        if EDITOR_METHODS[name] is None:
            require(not arguments, "Unexpected arguments for a nonparameterized editor method")
            actual[name] = [dict(node_identifier=identifier, result=node["result"])]
        else:
            if not arguments or any(child.get("name") not in {"false", "true"} for child in arguments):
                raise EditorEvidenceReviewPending("Unrecognized Bool argument representation: " + identifier)
            require(len(arguments) == 2 and {child["name"] for child in arguments} == {"false", "true"},
                    "Missing or duplicate editor Bool case: " + identifier)
            actual[name] = [dict(node_identifier=identifier, argument=child["name"], result=child["result"])
                            for child in sorted(arguments, key=lambda item: item["name"])]
    count = sum(len(cases) for cases in actual.values())
    require(count == 12, "Expected exactly twelve distinct editor argument cases")
    return dict(actual_method_count=len(actual), declared_case_count=count, editor_cases=actual)


def verify_packages(app, derived, evidence, pin, git):
    lock = json.loads((app / LOCK).read_text())
    pins = {item["identity"].lower(): item["state"].get("revision") for item in lock["pins"]}
    require(pins.get("swift-ai-sdk") == pin["swiftAISDKRevision"], "Resolved Swift AI SDK differs from canonical pin")
    kit = pins.get("torahinspectorkit", "")
    require(re.fullmatch(r"[0-9a-f]{40}", kit or ""), "Missing resolved Kit revision")
    require(f'revision: "{kit}"' in (app / "Modules/PinkhaKit/Package.swift").read_text()
            and f"revision = {kit};" in (app / "Anytype.xcodeproj/project.pbxproj").read_text(),
            "Actual Kit lock and both production pins differ")
    actual = {}
    for identity in ("torahinspectorkit", "swift-ai-sdk"):
        checkouts = [p for p in (derived / "SourcePackages/checkouts").iterdir() if p.name.lower() == identity]
        require(len(checkouts) == 1, "Missing actual dependency checkout: " + identity)
        actual[identity] = git(checkouts[0], "rev-parse", "HEAD")
        require(actual[identity] == pins[identity], "Actual dependency checkout differs: " + identity)
    write(evidence / "actual-package-pins.json", lock)
    return actual


def xctest_products(configuration):
    """Resolve the actual Xcode TestHostPath/TestBundlePath, then their executables.

    Placeholder semantics follow Apple's TN2339, Listing 20. No binary name or
    embedded PlugIns layout is inferred from a target's display name.
    """
    products = configuration.parent.resolve()
    entries = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("BlueprintName") == "AnytypeTests" and "TestBundlePath" in value:
                entries.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(plistlib.loads(configuration.read_bytes()))
    require(len(entries) == 1, "Expected one actual AnytypeTests product declaration")

    def resolve(raw, host=None):
        require(isinstance(raw, str) and raw, "Missing actual Xcode product path")
        allowed = {"__TESTROOT__"} | ({"__TESTHOST__"} if host is not None else set())
        require(set(re.findall(r"__[A-Za-z][A-Za-z0-9_]*?__", raw)).issubset(allowed),
                "Unsupported Xcode product placeholder")
        value = raw.replace("__TESTROOT__", str(products))
        if host is not None:
            value = value.replace("__TESTHOST__", str(host))
        path = Path(value).resolve()
        require(path.is_dir() and path.is_relative_to(products), "Xcode product missing or outside fresh products")
        return path

    host = resolve(entries[0].get("TestHostPath"))
    bundle = resolve(entries[0].get("TestBundlePath"), host)
    require(host.suffix == ".app" and bundle.name == "AnytypeTests.xctest", "Unexpected actual test host/bundle")

    def executable(owner):
        info = plistlib.loads((owner / "Info.plist").read_bytes())
        name = info.get("CFBundleExecutable")
        require(isinstance(name, str) and name not in {"", ".", ".."} and Path(name).name == name
                and "\\" not in name, "Unsafe or missing CFBundleExecutable")
        path = (owner / name).resolve()
        require(path.is_relative_to(owner) and path.is_file(), "Declared product executable is missing")
        return path

    return host, executable(host), bundle, executable(bundle)


def execute(args, receipt):
    app, evidence, derived = args.app.resolve(), args.evidence.resolve(), args.derived.resolve()
    profile = HostTestProfile(args.profile)
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple silicon Mac required")
    sys.path.insert(0, str(app / "Tools/PinkhaNativeDerived"))
    from build_custom_heart import digest, git
    from build_native_ipa import prepare_source_cache, run_xctest, test_configuration
    from validate_wave1 import verify_runtime_copies
    from prepare_sdk import verify

    def identity():
        head = git(app, "rev-parse", "HEAD")
        require_identity(head, os.environ.get("GITHUB_SHA"), git(app, "branch", "--show-current"),
                         args.expected_app_branch, os.environ.get("GITHUB_RUN_ID"), os.environ.get("GITHUB_RUN_ATTEMPT"))
        return head

    head = identity()
    require(not git(app, "diff", "--name-only", "HEAD"), "Tracked source differs before SDK build")
    require(not derived.exists(), "Refuse stale SDK DerivedData; use a fresh run/attempt directory")
    preflight = json.loads((evidence / "preflight/preflight.json").read_text())
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN" and preflight.get("source_sha") == head
            and preflight.get("run_id") == os.environ["GITHUB_RUN_ID"]
            and preflight.get("run_attempt") == os.environ["GITHUB_RUN_ATTEMPT"], "Actual preflight identity differs")
    ipad = preflight["selected"]["ipad"]
    udid = ipad["udid"]
    expected, sources = expected_methods(app, profile)
    pin = json.loads((app / "Tools/Hanlin/source.json").read_text())
    snapshot = verify(app / "Dependencies/Hanlin")
    write(evidence / "hanlin-snapshot.json", snapshot)
    installation = json.loads((evidence / "heart/heart-installation.json").read_text())
    require(installation.get("status") == "PASS" and installation.get("app_source_sha") == head
            and installation.get("source_run_id") == args.heart_source_run_id, "Installed Heart provenance differs")
    heart = json.loads((app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json").read_text())
    require(heart.get("status") == "PASS" and heart.get("target") == "ios"
            and heart.get("marker") == installation["marker"], "Verified iOS Heart is missing")
    for item in heart["artifacts"]:
        require(digest(app / "Dependencies/Middleware/Lib.xcframework" / item["path"]) == item["sha256"],
                "Installed Heart bytes changed after verification")
    receipt.update(source_sha=head, preflight=preflight, configuration=CONFIGURATION,
                   profile=profile.value, selection=["AnytypeTests/" + name for name in profile.suites],
                   expected_methods=sorted(expected),
                   test_source_hashes=sources, hanlin_revision=pin["revision"], heart=installation,
                   hanlin_snapshot_sha256=sha256(evidence / "hanlin-snapshot.json"), phase="SIMULATOR_BOOT")
    if profile in {HostTestProfile.CORE, HostTestProfile.COMPONENTS}:
        receipt["core_manifest_sha256"] = sha256(core_profile.MANIFEST_PATH)
    write(evidence / "execution.json", receipt)
    flags = ["OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED", "ENABLE_TESTABILITY=YES",
             "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
             "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
    selection = ["-only-testing:" + name for name in receipt["selection"]]
    prepare_source_cache(app, derived)
    build = ["xcodebuild", "build-for-testing", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
             "-configuration", CONFIGURATION, "-destination", "platform=iOS Simulator,id=" + udid,
             "-derivedDataPath", str(derived), "-parallel-testing-enabled", "NO", *selection, *flags]
    receipt["build_command"] = build
    write(evidence / "execution.json", receipt)
    command(["xcrun", "simctl", "boot", udid], app, evidence)
    command(["xcrun", "simctl", "bootstatus", udid, "-b"], app, evidence)
    receipt["phase"] = "BUILD"
    write(evidence / "execution.json", receipt)
    command(build, app, evidence)
    receipt["build_succeeded"] = True
    configuration = test_configuration(derived / "Build/Products", "AnytypeTests")
    built, app_executable, test_bundle, test_executable = xctest_products(configuration)
    receipt["actual_product_paths"] = dict(app=str(built), test_bundle=str(test_bundle),
                                          app_executable=str(app_executable), test_executable=str(test_executable))
    receipt["app_executable_sha256"] = digest(app_executable)
    receipt["test_executable_sha256"] = digest(test_executable)
    command(["codesign", "--verify", "--strict", str(built)], app, evidence)
    verify_runtime_copies(built, installation["marker"].encode(), evidence)
    receipt["dependency_checkouts"] = verify_packages(app, derived, evidence, pin, git)
    verify(app / "Dependencies/Hanlin")
    receipt["xctestrun_sha256"] = digest(configuration)
    result = evidence / {HostTestProfile.SDK06: "SDK06.xcresult",
                         HostTestProfile.EDITOR: "EditorHost.xcresult",
                         HostTestProfile.CORE: "Wave15Core.xcresult",
                         HostTestProfile.COMPONENTS: "Wave15Components.xcresult"}[profile]
    require(not result.exists(), "Refuse an existing SDK xcresult")
    receipt["phase"] = "EXECUTION"
    test = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
            *selection, "-resultBundlePath", str(result)]
    receipt["test_command"] = test
    write(evidence / "execution.json", receipt)
    prefix = profile.result_prefix
    run_xctest(test, app, evidence, result, prefix, command_runner=command)
    receipt["test_command_exit_code"] = 0
    receipt.update(phase="RESULT_REVIEW", raw_summary_sha256=sha256(evidence / (prefix + "-summary.json")),
                   raw_tests_sha256=sha256(evidence / (prefix + "-tests.json")))
    write(evidence / "execution.json", receipt)
    summary = json.loads((evidence / (prefix + "-summary.json")).read_text())
    tree = json.loads((evidence / (prefix + "-tests.json")).read_text())
    identity()
    require(set(git(app, "diff", "--name-only", "HEAD").splitlines()).issubset({LOCK}),
            "Tracked source changed during SDK build/test")
    verify(app / "Dependencies/Hanlin")
    receipt["post_execution_source_verified"] = True
    write(evidence / "execution.json", receipt)
    receipt["actual"] = validate_results(summary, tree, expected, udid, profile)
    limitation = ("Native write dispatch, mounted document/account/scene lifetime UI, provider networking and full UI acceptance remain NOT_RUN"
                  if profile is HostTestProfile.SDK06 else
                  "Editor component tests use controlled store and insertion fixtures; native drag/drop UI, real middleware writes, and all SDK06 acceptance remain NOT_RUN by this profile")
    if profile is HostTestProfile.CORE:
        limitation = ("Existing UIKit direction, gesture, marker and native Properties component tests; "
                      "real multi-block UI, Add Property UI, native account writes and physical devices remain NOT_RUN by this profile")
    if profile is HostTestProfile.COMPONENTS:
        limitation = ("SDK06, editor and UIKit/Properties component contracts on one fresh source-bound build; "
                      "native consent/write/drag/drop UI, live provider networking, two clients and physical "
                      "device guarantees remain NOT_RUN by this profile")
    receipt.update(status=profile.pass_status, phase="COMPLETE", release_accepted=False, limitations=[limitation])


def cleanup(evidence, receipt):
    path = evidence / "preflight/preflight.json"
    if platform.system() != "Darwin" or not path.exists():
        return
    preflight = json.loads(path.read_text())
    run = os.environ.get("GITHUB_RUN_ID")
    if preflight.get("run_id") != run or preflight.get("run_attempt") != os.environ.get("GITHUB_RUN_ATTEMPT"):
        return
    inventory = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"]))
    devices = {d["udid"]: d for values in inventory["devices"].values() for d in values}
    removed = []
    for kind, item in preflight.get("selected", {}).items():
        udid = item.get("udid")
        name = "Pinkha-UI27-" + str(run) + "-" + kind
        if item.get("name") == name and devices.get(udid, {}).get("name") == name:
            subprocess.run(["xcrun", "simctl", "shutdown", udid], capture_output=True)
            subprocess.run(["xcrun", "simctl", "delete", udid], check=True, capture_output=True)
            removed.append(udid)
    receipt["removed_disposable_simulators"] = removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--derived", required=True, type=Path)
    parser.add_argument("--expected-app-branch", required=True, choices=[BRANCH])
    parser.add_argument("--heart-source-run-id", required=True)
    parser.add_argument("--profile", choices=[profile.value for profile in HostTestProfile], default=HostTestProfile.SDK06.value)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    require(re.fullmatch(r"[1-9][0-9]*", args.heart_source_run_id), "Explicit Heart source run is required")
    receipt = dict(status="RUNNING", phase="PREFLIGHT", profile=args.profile, build_succeeded=False, test_command_exit_code=None,
                   source_sha=os.environ.get("GITHUB_SHA"), run_id=os.environ.get("GITHUB_RUN_ID"),
                   run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), started_at=datetime.now(timezone.utc).isoformat())
    with cancellation_signals():
        try:
            write(args.evidence / "execution.json", receipt)
            execute(args, receipt)
            require(receipt.get("profile") == args.profile and receipt["status"] == HostTestProfile(args.profile).pass_status,
                    "Completed receipt does not match its explicit component profile")
        except KeyboardInterrupt as error:
            receipt.update(status="CANCELLED", error_type=type(error).__name__, error=str(error))
            if isinstance(error, CommandCancelled):
                receipt["cancellation_signal"] = error.signum
        except core_profile.CoreEvidenceReviewPending as error:
            receipt.update(status="CORE_EVIDENCE_REVIEW_PENDING", error_type=type(error).__name__, error=str(error))
        except EditorEvidenceReviewPending as error:
            receipt.update(status="EDITOR_EVIDENCE_REVIEW_PENDING", error_type=type(error).__name__, error=str(error))
        except BaseException as error:
            receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        finally:
            # The command has already stopped/reaped its own process group.
            # Do not start more simctl/XCTest processes during runner cancellation.
            if receipt["status"] == "CANCELLED":
                receipt["simulator_cleanup"] = "DEFERRED_TO_EPHEMERAL_RUNNER_AFTER_CANCELLATION"
            else:
                try:
                    cleanup(args.evidence, receipt)
                except KeyboardInterrupt as error:
                    receipt.update(status="CANCELLED", error_type=type(error).__name__, error=str(error),
                                   simulator_cleanup="INTERRUPTED_DURING_DISPOSABLE_SIMULATOR_CLEANUP")
                    if isinstance(error, CommandCancelled):
                        receipt["cancellation_signal"] = error.signum
                except Exception as error:
                    receipt["cleanup_error"] = str(error)
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            write(args.evidence / "execution.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == HostTestProfile(args.profile).pass_status else 1


if __name__ == "__main__":
    raise SystemExit(main())
