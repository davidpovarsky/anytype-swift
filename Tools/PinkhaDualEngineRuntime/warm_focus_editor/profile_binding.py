"""Finite binding of original focus22/34 and first-editor preparation/four UI.

No new Swift source, declaration parser, result validator, warning helper or
fixture projection. The old failed preparation remains separate failed evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from originals import require

LANES = ("focus-lifecycle", "editor")
ACTIVATION_SHA256 = "e674b6e534b46cc6bfde2201a4c7731f9be5b66afcf4e3f962b71c0759b52f0c"
MEMBERSHIP_SHA256 = "5c4711f1b50498d9c2babcb4593795c7b14e5aa7867d6ebbeffdcb6948fc33ee"
SELECTION_SHA256 = "9d4ec5c867a9d03f6d0d41d5c52c7faaafc6116e09c0c135cd3790c76940d170"
READY_FOR_EXECUTION = False
FINAL_SOURCE_SDK_NATIVE_PRODUCT_TUPLE = None


def local_json(name, expected):
    path = Path(__file__).absolute().with_name(name)
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and path.stat().st_size <= 1024 * 1024, "Exact bounded physical original binding required")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, "Reviewed finite binding changed: " + name)
    return json.loads(raw)


def require_runtime_ready():
    """Fail before any source/host path, subprocess, output or account operation."""
    activation = local_json("activation.json", ACTIVATION_SHA256)
    require(activation["schema"] == "pinkha-warm-focus-editor-activation-v1"
            and activation["readyForExecution"] is False and activation["plans"] == []
            and activation["finalSourceSDKNativeProductTuple"] is None
            and activation["originalSelectionSHA256"] == SELECTION_SHA256
            and (activation["declaredFocusMethods"], activation["declaredFocusCases"]) == (22, 34)
            and (activation["requiredAppCompilerSources"], activation["requiredStage1UICompilerSources"]) == (61, 10)
            and activation["separateNativeUIReceiptRequired"] is False
            and activation["original8acAssemblyReuseOnly"] is True
            and READY_FOR_EXECUTION is False and FINAL_SOURCE_SDK_NATIVE_PRODUCT_TUPLE is None,
            "The separately reviewed closed intermediate runtime tuple differs")
    raise ValueError("Priority warm focus/editor is CLOSED: the actual source/SDK/original8ac/current-product tuple and reviewed activation are required")


def source_membership():
    value = local_json("source-membership.json", MEMBERSHIP_SHA256)
    require(value["schema"] == "pinkha-priority-warm-source-membership-v1"
            and len(value["native"]) == len(set(value["native"])) == 61
            and len(value["ui"]) == len(set(value["ui"])) == 10
            and len(value["externalPackageSources"]) == 9
            and value["NativeUIReceiptRequired"] is False,
            "Exact finite App61/Stage1UI10 source membership required")
    return value


class UnselectedRoute:
    """An unreachable original non-editor dependency cannot start another lane."""
    def __getattr__(self, name):
        raise ValueError("This finite consumer does not select the original non-editor helper: " + name)


class BoundSourceQueries:
    """Only the originals' two exact read-only Git shapes, under owned60s custody.

    This object is scoped to the two newly loaded original profile namespaces.
    It does not monkeypatch the process-global subprocess module. Original
    focus/startup validator bodies and returned source contracts remain exact.
    """
    def __init__(self, source, commands, originals):
        self.source, self.commands, self.originals = Path(source), commands, originals
        self.sequence = 0

    def check_output(self, argv, **kwargs):
        require(self.commands.is_open, "Unresolved original ownership blocks source witness queries")
        self.originals.unchanged()
        allowed = (["git", "-C", str(self.source), "ls-files", "-z"],
                   ["git", "-C", str(self.source), "rev-parse", "HEAD"])
        require(list(argv) in allowed and set(kwargs) <= {"timeout"}
                and (not kwargs or kwargs["timeout"] == 60),
                "Only the two original finite source query shapes are admitted")
        self.sequence += 1
        path, _ = self.commands.run(list(argv), "original-source-query-" + str(self.sequence), 60)
        return self.originals.shared.raw(path)


class RuntimeBindings:
    def __init__(self, originals, commands, context):
        self.originals, self.commands, self.context = originals, commands, context
        self.selection = local_json("priority-runtime-selection.closed.json", SELECTION_SHA256)
        self.source_bytes = {}
        self.contract = None
        self.command_gate()
        originals.install_runtime(commands)
        self.host = originals.host
        for key in ("focus", "editor"):
            pin = self.selection[key]["source"]
            self._source(pin)
        self._source(self.selection["editor"]["preparationSource"])
        require(originals.focus.METHOD_COUNT == 22 and originals.focus.CASE_COUNT == 34,
                "Original focus profile scope differs")
        editor = originals.wave15.LANES["editor"]
        methods = [editor["suite"] + "/" + name for name in editor["methods"]]
        methods.append("PinkhaStage1AcceptanceUITests/testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen")
        require(["PinkhaStage1AcceptanceUITests/" + name for name in methods] == self.selection["editor"]["selectors"]
                and "AnytypeTests/" + editor["preparation"] + "()" == self.selection["editor"]["preparationSelector"]
                and editor["fixture"] == self.selection["editor"]["fixture"],
                "Original editor preparation, fixture or first3-plus-switch selection differs")
        budget = originals.carriers.selection_time_budget("PinkhaStage1AcceptanceUITests", methods)
        require(budget["default_seconds"] == budget["maximum_seconds"] == 300
                and budget["total_method_seconds"] == 1200,
                "The original four UI method budgets differ")
        self.proof = {"schema": "pinkha-priority-original-focus-editor-binding-v1",
            "selectionSHA256": SELECTION_SHA256, "sourceCommit": context["sourceIdentity"]["commit"],
            "actualBuildReceipt": context["buildRef"],
            "actualNativeCompilationProof": context["build"]["nativeCompilationProof"],
            "actualStage1CompilationProof": context["build"]["uiCompilationProof"],
            "requiredCompilerSources": {"app": 61, "stage1UI": 10},
            "nativeUICompilerAdmissionRequired": False, "focusMethods": 22, "focusCases": 34,
            "editorPreparationMethods": 1, "editorUIMethods": 4,
            "startupProfileSHA256": "6960a4f74aa6b582e783addf358cc1806728dffd520483336c877e473b63aeb9",
            "startupConsumerSHA256": "1cd58739742768bb8863c49797c1035292796c1cf7ab6de0e928a90be5bf95a6",
            "UIBudget": budget, "visualReview": "PENDING", "historicalFailedPreparationUnchanged": True,
            "oldApp15ReusedAsCurrent": False, "testsExecutedByBinding": 0}

    def command_gate(self):
        require(self.commands.is_open, "Original owned group is unresolved; priority witness admission is closed")
        self.originals.unchanged()

    def _source(self, pin):
        relative = pin["path"]
        path = self.originals.source / relative
        require(path.is_file() and not path.is_symlink() and path.resolve() == path,
                "Exact physical original priority Swift source required")
        raw = path.read_bytes()
        require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"]
                and self.context["selectedSourceProof"]["sourceRows"][relative]["sha256"] == pin["sha256"],
                "Priority source differs from the original or actual compiled source inventory")
        self.source_bytes[relative] = raw

    def focus_contract(self):
        self.command_gate()
        value = self.originals.focus.source_contract(self.originals.source)
        require(value["kind"] == "focus-lifecycle"
                and (value["expected_methods"], value["declared_cases"]) == (22, 34)
                and value["source_sha256"] == self.selection["focus"]["source"]["sha256"]
                and set(value["compiled_identifiers"]) == {row["selector"] for row in self.selection["focus"]["methods"]},
                "Exact original focus declarations or literal cases differ")
        if self.contract is None:
            self.contract = value
        require(value == self.contract, "Original focus source contract changed during runtime")
        self.unchanged()
        return self.contract

    def unchanged(self):
        self.originals.unchanged()
        require(local_json("priority-runtime-selection.closed.json", SELECTION_SHA256) == self.selection,
                "Original selection binding changed")
        for relative, before in self.source_bytes.items():
            path = self.originals.source / relative
            require(path.resolve() == path and not path.is_symlink() and path.read_bytes() == before,
                    "An actual compiled priority source changed: " + relative)

    def startup_admission(self, settings, binding, contract_ref):
        self.command_gate()
        require(binding["sourceSHA"] == self.context["sourceIdentity"]["commit"],
                "Startup source differs from the actual new product")
        # This original hook schema describes the actual current admission.
        # Add explicit provenance: it is not a call to the historical App15 gate
        # and never relabels a retained fixture or failed preparation as current.
        return {"schema": "pinkha-combined-host-acceptance-admission-v1",
            "executionEnvironment": "SentinelX-owned-Mac", "sourceCommit": binding["sourceSHA"],
            **settings, "admissionScope": "CURRENT_FORWARD_WARM_PRODUCT_ORIGINAL_STARTUP_VIEW",
            "actualCommonBuildContract": contract_ref, "actualBuildReceipt": self.context["buildRef"],
            "actualRootBuildAdmission": self.context["rootAdmissionRef"],
            "actualRuntimePlan": self.context["planRef"], "original8acAssemblyReused": True,
            "historicalApp15AdmittedAsCurrent": False, "historicalFixtureReused": False,
            "preparationAcceptedByThisView": False, "visualReview": "PENDING"}
