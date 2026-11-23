"""Opt-in UI-only build for the previously failed Page154 startup transition.

Native/App Products, fixture preparation, ordinary publication and downstream UI
assertions retain their original origins. This adapter never builds the App.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import warning_profile as profile


class WarningContinuation:
    def __init__(self, args, binding, head, plan, proof, consumer, receipt):
        self.args, self.binding, self.head, self.plan = args, binding, head, plan
        self.proof, self.consumer, self.receipt = proof, consumer, receipt
        self.source = args.work / "ui-warning-source"
        self.derived = args.work / "ui-warning-derived"
        self.evidence = args.evidence / "ui-runner"
        self.generated = None
        self.generated_inputs = None
        self.preservation = None
        self.original = None
        self.approved = None
        self.ui_binding = dict(binding, sourceSHA=head)
        self.detail = dict(
            status="NOT_RUN", purpose="FAILED_PAGE_UI_STARTUP_WARNING_CONTINUATION",
            app_source_sha=profile.APP_COMMIT, ui_source_sha=head,
            ui_input_plan_sha256=profile.PLAN_SHA256, ui_source_sha256=profile.UI_SHA256,
            selector=profile.SELECTOR, preparation_selector=profile.PREPARATION,
            build_flags=list(consumer.BUILD_FLAGS), app_builds=0, native_builds=0,
            ui_builds_started=0, ui_builds_succeeded=0,
            original_simulator_state_reused=False, new_preparation_acceptance_credit=0,
            retained_preparation_acceptance=plan["retained_preparation"],
            actual_ui_acceptance="NOT_RUN")
        receipt["startup_warning_continuation"] = self.detail

    def save(self):
        self.proof.save(self.args.evidence / "execution.json", self.receipt)
        if self.evidence.exists():
            self.proof.save(self.evidence / "warning-build.json", self.detail)

    def build(self, runner, udid):
        p, c = self.proof, self.consumer
        p.require(not self.evidence.exists() and not self.derived.exists(),
                  "Fresh warning UI evidence/derived roots required")
        self.evidence.mkdir()
        try:
            copied = profile.copy_sources(self.source, self.args.controller, self.args.app, self.plan)
            generator = c.shared.ui_only_project
            p.require(Path(generator.__code__.co_filename).resolve()
                      == self.args.controller / self.plan["generator_path"],
                      "Actual qualified generator import origin differs")
            self.generated = generator(self.source)
            self.generated_inputs = profile.generated_project(self.source, self.generated, self.plan)
            source_receipt = dict(
                protocol="pinkha-page154-warning-ui-build-inputs-v1",
                app_source_sha=profile.APP_COMMIT, ui_source_sha=self.head,
                input_plan_sha256=profile.PLAN_SHA256,
                source_inputs=copied, generated_and_copied_inputs=self.generated_inputs,
                generator_path=self.plan["generator_path"],
                generator_sha256=self.plan["generator_sha256"],
                selector=profile.SELECTOR, app_targets=0, ui_targets=1,
                package_references=0, build_implicit_dependencies=False)
            p.save(self.evidence / "build-source-inputs.json", source_receipt)
            self.detail.update(generated_project=str(self.generated),
                               build_source_inputs_sha256=p.digest(self.evidence / "build-source-inputs.json"),
                               generated_and_copied_inputs=self.generated_inputs,
                               ui_builds_started=1)
            self.receipt["ui_builds"] = 1
            self.save()
            runner.run(profile.build_command(self.generated, self.derived, udid, c.BUILD_FLAGS),
                       "build-warning-ui-runner", 1200)
            self.detail["ui_builds_succeeded"] = 1
            p.require(profile.generated_project(self.source, self.generated, self.plan)
                      == self.generated_inputs, "Warning UI inputs changed during build")
            source_path = self.derived / "Build/PinkhaSourceInputs.json"
            p.require(source_path.parent.is_dir() and not source_path.exists()
                      and not source_path.is_symlink(), "Fresh UI build source receipt required")
            p.save(source_path, source_receipt)
            preservation = c.early_build_products.capture(
                self.derived, self.evidence, source_sha=self.head,
                run_id=self.binding["runID"], run_attempt=self.binding["runAttempt"],
                build_flags=c.BUILD_FLAGS, scope="semantic-page154")
            self.preservation = {**preservation,
                "archive_path": "ui-runner/" + preservation["archive_path"],
                "manifest_path": "ui-runner/" + preservation["manifest_path"]}
            self.detail["early_products"] = self.preservation
            self.save()
            self.original = c.shared.test_configuration(self.derived / "Build/Products", profile.TARGET)
            self.detail["descriptor"] = c.ui_build.descriptor_summary(
                self.original, self.derived / "Build/Products")
            self.approved = profile.same_job_descriptor(profile.regular(self.original))
            p.descriptor_admission(self.approved, p.UI)
            shutil.copyfile(self.original, self.evidence / "original.xctestrun")
            self.detail["original_xctestrun"] = dict(
                path="ui-runner/original.xctestrun",
                products_path=self.original.relative_to(self.derived).as_posix(),
                sha256=p.digest(self.original))
            self.detail["same_job_descriptor_admission"] = self.approved
            self.detail["product_integrity_before"] = c.ui_build.verify_preserved_products(
                self.derived, self.args.evidence, self.preservation, self.ui_binding, c.BUILD_FLAGS)
            self.detail["status"] = "NEW_UI_ONLY_PRODUCTS_PRESERVED_AND_ADMITTED"
            self.save()
            return self.original, self.approved
        except BaseException as error:
            self.detail.update(status="FAIL", error_type=type(error).__name__, error=str(error))
            self.save()
            raise

    def setup(self, verified, fixture):
        self.detail["fresh_fixture_setup"] = profile.setup_accounting(
            verified, fixture, self.binding, self.plan)
        self.save()

    def observations(self, directory, udid):
        p = self.proof
        manifest = p.read(directory / "manifest.json")
        p.require(isinstance(manifest, list), "Actual warning UI attachment manifest missing")
        expected = {
            "semantic-anchor-native-startup-capture": "capture",
            "semantic-anchor-native-startup-reopen": "reopen",
            "semantic-anchor-native-startup-warning-ax": "ax",
            "semantic-anchor-native-startup-warning": "screen"}
        found = {}
        for row in manifest:
            for item in row.get("attachments", []):
                name = str(item.get("suggestedHumanReadableName", ""))
                matches = [key for key in expected if name.startswith(key + "_")]
                if not matches:
                    continue
                p.require(len(matches) == 1, "Ambiguous warning attachment name")
                key = matches[0]
                test = str(row.get("testIdentifier", "")).removeprefix(
                    profile.TARGET + "/").removesuffix("()")
                p.require(test == "/".join(profile.SELECTOR.split("/")[1:])
                          and key not in found and str(item.get("deviceId", "")).lower() == udid.lower()
                          and item.get("isAssociatedWithFailure") is False,
                          "Wrong or duplicate warning UI attachment")
                path = directory / p.native.relative(item.get("exportedFileName"))
                p.require(path.parent == directory, "Unexpected warning attachment hierarchy")
                kind = expected[key]
                if kind in {"capture", "reopen"}:
                    value = p.read(path, 65536)
                    profile.startup_observation(value, self.binding, kind)
                elif kind == "ax":
                    raw = profile.regular(path, 2 * 1024**2).decode("utf8", errors="strict")
                    p.require(all(text in raw for text in (
                        "Warning", "You launch app with a unstable middleware.",
                        "Continue with current vault", "Logout from current vault")),
                        "Actual pre-Continue native warning AX missing")
                else:
                    raw = profile.regular(path, 20 * 1024**2)
                    p.require(len(raw) > 0, "Actual warning screenshot missing")
                found[key] = dict(path=str(path), sha256=p.digest(path), kind=kind, test=test)
        p.require(set(found) == set(expected), "Both startup traces and original native warning evidence required")
        self.detail["startup_observations"] = found
        self.detail["actual_ui_acceptance"] = "PASS_UNCHANGED_DOWNSTREAM_JOURNEY_WITH_REAL_WARNING_CONTINUE"
        self.save()
        return found

    def finish(self, copied_descriptors):
        p, c = self.proof, self.consumer
        if self.generated_inputs is not None:
            p.require(profile.generated_project(self.source, self.generated, self.plan)
                      == self.generated_inputs, "Copied/generated UI inputs changed")
            self.detail["build_inputs_unchanged"] = True
        if self.preservation is not None:
            additions = {path.relative_to(self.derived).as_posix(): digest
                         for path, digest in copied_descriptors if path.is_relative_to(self.derived)}
            self.detail["product_integrity_after"] = c.ui_build.verify_preserved_products(
                self.derived, self.args.evidence, self.preservation, self.ui_binding,
                c.BUILD_FLAGS, descriptor_additions=additions)
        self.save()
