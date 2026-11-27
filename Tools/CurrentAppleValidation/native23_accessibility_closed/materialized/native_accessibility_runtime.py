"""Finite AX-setting choreography inside the existing Native23 command owner.

No subprocess, simulator discovery, product admission or second process manager
is provided here. The exact reviewed c249 registry owns every supplied command.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import re
import uuid

TARGET = "PinkhaAnyNativeUITests"
ENVIRONMENT = ("PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_JSON", "PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_SHA256")
STAGES = ("accessibility-audit-large", "accessibility-audit-expanded", "accessibility-voiceover-large")


class AccessibilitySession:
    def __init__(self, c, observations, matrix, runtime, helpers, configuration,
                 cell_path, cell_sha, commands, out, udid, source, stage):
        c.require(stage in STAGES and re.fullmatch(r"[0-9a-f]{40}", source) is not None,
                  "One exact admitted-source accessibility plan required")
        c.require(isinstance(commands, runtime.OwnedCommands) and commands.out == out and commands.closed,
                  "The existing sole Native23 owned command registry is required")
        c.require(set(helpers) == set(matrix.HELPERS), "Exactly the original three RTL helper functions required")
        self.c, self.observations, self.matrix, self.runtime = c, observations, matrix, runtime
        self.helpers, self.configuration = helpers, copy.deepcopy(configuration)
        self.cell_path, self.cell_sha = cell_path, cell_sha
        self.commands, self.run, self.out, self.udid = commands, commands.run, out, udid
        self.source, self.stage, self.specification = source, stage, observations.plan(c, stage)
        self.context = self.forwarded_environment = None
        self.may_have_changed = self.did_execute = self.finished = False

    def revalidate_cell(self):
        self.c.require(self.matrix.cell(self.c, self.cell_path, self.cell_sha) == self.configuration,
                       "The exact pinned accessibility base cell changed")

    def require_closed(self):
        self.c.require(self.commands.closed, "Unresolved owned command custody forbids accessibility device operations")

    def readback(self, phase):
        c = self.c
        c.require(phase in ("before", "after", "restored"), "Finite accessibility readback phase required")
        c.require(phase != "restored" or self.specification["contentSize"] == self.observations.EXPANDED,
                  "Only the expanded audit has a restoration phase")
        self.require_closed()
        prefix = "accessibility-" + phase
        self.run(["xcrun", "simctl", "spawn", self.udid, "defaults", "export", "NSGlobalDomain", "-"],
                 self.out, prefix + "-language-readback", timeout=120)
        for key in ("appearance", "content_size"):
            self.require_closed()
            self.run(["xcrun", "simctl", "ui", self.udid, key], self.out,
                     prefix + "-" + key.replace("_", "-") + "-readback", timeout=30)
        value = self.observations.readback_record(c, self.out, self.configuration, self.udid,
            self.stage, phase, settings_helpers=self.helpers)
        path = self.out / (prefix + "-environment.json")
        self.runtime.exclusive(c, path, self.runtime.encoded(value))
        return {"environment": self.runtime.pin(c, path, 16384), "value": value}

    def prepare(self):
        c = self.c
        self.revalidate_cell()
        self.require_closed()
        c.require(self.context is None, "One fresh accessibility invocation required")
        baseline = self.matrix.prepare(c, self.helpers, self.configuration, self.run, self.out, self.udid)
        before_path = self.out / "rtl-before-environment.json"
        if self.specification["contentSize"] == self.observations.EXPANDED:
            # Set before the first possible write. A setter that later fails its
            # ledger/readback still requires restoration on positively closed custody.
            self.may_have_changed = True
            self.require_closed()
            self.run(["xcrun", "simctl", "ui", self.udid, "content_size", self.observations.EXPANDED],
                     self.out, "accessibility-set-content-size", timeout=30)
            selected = self.readback("before")
            before_path = self.out / "accessibility-before-environment.json"
        else:
            observed = self.observations.readback_record(c, self.out, self.configuration, self.udid,
                self.stage, "before", settings_helpers=self.helpers)
            c.require(c.decode(c.raw(before_path, 16384)) == observed == baseline,
                      "The original retained large baseline differs from actual command readbacks")
            selected = {"environment": self.runtime.pin(c, before_path, 16384), "value": observed}
        language = "en" if self.configuration["appLanguage"] == "he" else "he"
        context = {"schema": "native-accessibility-invocation/v1", "runID": str(uuid.uuid4()).upper(),
            "appSourceCommit": self.source, "uiSourceCommit": self.source, "simulatorUDID": self.udid,
            "ownedScope": str(uuid.uuid4()).upper(), "method": self.specification["method"],
            "appLanguage": self.configuration["appLanguage"], "osLanguage": language,
            "contentSize": self.specification["contentSize"], "appearance": self.configuration["appearance"],
            "deviceFamily": self.configuration["deviceFamily"], "settingsReadbackSHA256": c.digest(before_path)}
        raw = self.runtime.encoded(context)
        self.observations.environment(c, raw, self.udid, self.stage)  # Exact original13-field validation.
        self.runtime.exclusive(c, self.out / "accessibility-invocation.json", raw)
        self.context = context
        return {"configuration": self.configuration, "configurationSHA256": self.cell_sha,
                "plan": self.specification, "originalBaseline": baseline, "selectedBefore": selected,
                "invocation": self.runtime.pin(c, self.out / "accessibility-invocation.json", 16384),
                "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}

    def bind(self, original):
        c = self.c
        selector = "NativeLaunchTests/" + self.specification["method"]
        c.require(self.context is not None and self.forwarded_environment is None
                  and set(original) == {TARGET, "__xctestrun_metadata__"},
                  "One original single-target accessibility descriptor required")
        target = original[TARGET]
        c.require(target["OnlyTestIdentifiers"] == [selector]
                  and target["EnvironmentVariables"].get("PINKHA_NATIVE_UI_UNIFIED_HOST") == "1"
                  and target["EnvironmentVariables"].get("PINKHA_SIMULATOR_UI_DISPOSABLE") == "1",
                  "Original disposable same-source NativeUI descriptor required")
        for key in ENVIRONMENT:
            c.require(key not in os.environ and "TEST_RUNNER_" + key not in os.environ
                      and all(key not in target.get(group, {}) and "TEST_RUNNER_" + key not in target.get(group, {})
                              for group in ("EnvironmentVariables", "TestingEnvironmentVariables", "UITargetAppEnvironmentVariables")),
                      "Ambient or prebound accessibility context overrides are forbidden")
        raw = c.raw(self.out / "accessibility-invocation.json", 16384)
        c.require(c.decode(raw) == self.context, "Retained accessibility invocation changed")
        additions = self.observations.environment(c, raw, self.udid, self.stage)
        c.require(set(additions) == set(ENVIRONMENT), "Only the two original context variables may be forwarded")
        value = copy.deepcopy(original)
        value[TARGET]["EnvironmentVariables"].update(additions)
        inverse = copy.deepcopy(value)
        for key in additions:
            del inverse[TARGET]["EnvironmentVariables"][key]
        c.require(inverse == original, "The original bound descriptor must restore exactly")
        self.forwarded_environment = {"TEST_RUNNER_" + key: item for key, item in additions.items()}
        return value, {"environmentKeys": list(ENVIRONMENT), "invocationSHA256": c.sha(raw),
                       "selector": TARGET + "/" + selector, "methodBudgetSeconds": self.specification["allowance"],
                       "inverseRestoresOriginalBoundDescriptor": True}

    def environment(self):
        self.c.require(self.forwarded_environment is not None, "The actual original descriptor must bind the context first")
        return dict(self.forwarded_environment)

    def execute(self, argv, timeout, environment):
        c = self.c
        self.revalidate_cell()
        self.require_closed()
        c.require(not self.did_execute and self.context is not None
                  and environment == self.environment() and timeout == self.specification["allowance"] + 300,
                  "Exactly one original accessibility execution with the unchanged command budget required")
        selector = "-only-testing:" + self.specification["selector"]
        c.require([value for value in argv if value.startswith("-only-testing:")] == [selector],
                  "Only the exact source-bound accessibility method may execute")
        for flag, expected in (("-xctestrun", str(self.out / "Selected.xctestrun")),
                               ("-destination", "platform=iOS Simulator,id=" + self.udid),
                               ("-default-test-execution-time-allowance", "900"),
                               ("-maximum-test-execution-time-allowance", "900")):
            c.require(argv.count(flag) == 1 and argv.index(flag) + 1 < len(argv)
                      and argv[argv.index(flag) + 1] == expected, "Original accessibility command differs: " + flag)
        c.require(c.decode(c.raw(self.out / "accessibility-invocation.json", 16384)) == self.context,
                  "Original accessibility context changed before execution")
        self.did_execute = True
        return self.run(argv, self.out, "execute", timeout=timeout, environment=environment, allow_failure=True)

    def finish(self, app):
        """Retain actual readbacks and restore after every attempted expanded setter."""
        c = self.c
        c.require(not self.finished, "Accessibility finalization may run only once")
        self.finished = True
        first, errors = None, []
        result = {"schema": "native-accessibility-finalization/v1", "stage": self.stage,
                  "expandedWriteAttempted": self.may_have_changed, "originalExecutionAttempted": self.did_execute,
                  "after": None, "restoration": None, "installedCodeAfter": None,
                  "errors": errors, "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}

        def attempt(phase, action):
            nonlocal first
            try:
                return action()
            except BaseException as error:
                if first is None:
                    first = error
                errors.append({"phase": phase, "type": type(error).__name__, "reason": str(error)})
                return None

        attempt("original-cell-revalidation", self.revalidate_cell)
        if self.did_execute:
            result["after"] = attempt("selected-after-readback", lambda: self.readback("after"))
        if self.may_have_changed:
            if not self.commands.closed:
                result["restoration"] = {"withheldReason": "UNRESOLVED_OWNED_COMMAND_CUSTODY"}
                attempt("restoration-owned-custody", self.require_closed)
            else:
                def restore():
                    self.require_closed()
                    self.run(["xcrun", "simctl", "ui", self.udid, "content_size", "large"],
                             self.out, "accessibility-restore-content-size", timeout=30)
                    return self.readback("restored")
                result["restoration"] = attempt("restore-original-large-and-readback", restore)
        if self.did_execute and app is not None:
            def installed():
                self.require_closed()
                return self.matrix.installed(c, self.helpers, self.run, self.out, self.udid, app, "after")
            result["installedCodeAfter"] = attempt("original-installed-app-after", installed)
        result["ownedCommandsClosed"] = self.commands.closed
        if not self.commands.closed:
            attempt("final-owned-command-custody", self.require_closed)
        result["status"] = "PASS_SETTINGS_FINALIZATION_NOT_UI_ACCEPTANCE" if first is None else "FAIL"
        try:
            self.runtime.exclusive(c, self.out / "accessibility-finalization.json", self.runtime.encoded(result))
        except BaseException as error:
            if first is None:
                first = error
            else:
                first.add_note("Secondary accessibility-finalization retention failure: " + repr(error))
        if first is not None:
            raise first
        return result
