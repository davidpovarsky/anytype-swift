"""Portable SYNTHETIC controls; no Apple, UI, Native, or product execution."""
from pathlib import Path
import base64
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "interfaces_work/native-styled-control/native_styled_observations.py"
spec = importlib.util.spec_from_file_location("styled_observations_control", SOURCE)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class C:
    @staticmethod
    def require(value, reason):
        if not value:
            raise RuntimeError(reason)

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def decode(raw):
        return json.loads(raw)

    @staticmethod
    def raw(path, maximum):
        raw = Path(path).read_bytes()
        C.require(len(raw) <= maximum, "synthetic bounded read")
        return raw


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o600)
    return {"path": str(path), "bytes": len(raw), "sha256": C.sha(raw)}


class Fixture:
    """Deliberately fabricated portable inputs, never a runtime receipt."""
    def __init__(self, out, stage):
        self.out, self.stage = out, stage
        self.directory = out / "private-original-styled-attachments"
        self.directory.mkdir(parents=True)
        self.udid = "00000000-0000-4000-8000-000000000001"
        self.settings = {"ownedUDID": self.udid, "language": {"app_language": "he", "device_language": "en"},
                         "presentation": {"appearance": "light", "content_size": "large"},
                         "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}
        settings = write(out / "rtl-before-environment.json", encoded(self.settings))
        self.context = {"schema": "native-accessibility-invocation/v1", "runID": "00000000-0000-4000-8000-000000000002",
                        "ownedScope": "00000000-0000-4000-8000-000000000003", "simulatorUDID": self.udid,
                        "appSourceCommit": "a" * 40, "uiSourceCommit": "a" * 40, "method": M.PLANS[stage]["method"],
                        "appLanguage": "he", "osLanguage": "en", "contentSize": "large", "appearance": "light",
                        "deviceFamily": "ipad", "settingsReadbackSHA256": settings["sha256"]}
        self.invocation = write(out / "styled-invocation.json", encoded(self.context))
        self.native, self.meta, self.paths, self.items = {}, {}, {}, []
        if stage == "styled-blocks":
            for choice in M.CHOICES:
                self.add("choice-" + choice + "-empty-rtl", choice, [(choice, "", choice)])
                self.add("choice-" + choice + "-saved", choice, [(choice, "אב7", choice)])
            self.add("before-menu-empty-rtl", "paragraph", [("heading-3", "", "inserted"), ("paragraph", "אב7", "paragraph")])
            self.add("before-menu-saved", "paragraph", [("heading-3", "ת8", "inserted"), ("paragraph", "אב7", "paragraph")])
            for choice in M.CHOICES:
                blocks = [(choice, "אב7", choice)]
                if choice == "paragraph":
                    blocks.insert(0, ("heading-3", "ת8", "inserted"))
                self.add("cold-" + choice, choice, blocks, pid=2002)
        else:
            self.add("live-heading-1-empty-rtl", "live", [("heading-1", "", "h")])
            self.add("live-code-empty-rtl", "live", [("heading-1", "אב", "h"), ("code", "", "c")])
            self.add("live-paragraph-empty-rtl", "live", [("heading-1", "אב", "h"), ("code", "A7", "c"), ("paragraph", "", "p")])
            for phase in M.LIVE_PHASES[3:]:
                self.add(phase, "live", [("heading-1", "אב", "h"), ("code", "A7", "c"), ("paragraph", "", "p")],
                         expanded=phase == "live-accessibility")
        for phase, native in self.native.items():
            self.paths[(phase, "native")] = self.directory / (phase + "-native.json")
            ref = write(self.paths[(phase, "native")], encoded(native))
            self.meta[phase]["nativeObservationSHA256"] = ref["sha256"]
        if stage == "styled-live-type":
            self.live_control()
        for phase in M.PLANS[stage]["phases"]:
            for kind, ext in (("native", ".json"), ("context", ".json"), ("ax", ".txt"), ("screen", ".png")):
                path = self.directory / (phase + "-" + kind + ext)
                self.paths[(phase, kind)] = path
                if kind == "context":
                    write(path, encoded(self.meta[phase]))
                elif kind == "ax":
                    write(path, b"SYNTHETIC CONTROL ONLY; NOT AN APP ACCESSIBILITY TREE\n")
                elif kind == "screen":
                    write(path, self.png())
                self.item(M.PREFIX + phase + "-" + kind + "_SYNTHETIC" + ext, path)
        final = {"schema": "native-accessibility-private-final/v1", "invocation": self.context,
                 "caseReachedEnd": True, "appStateBeforeTermination": "SYNTHETIC runningForeground",
                 "runnerSimulatorUDID": self.udid, "captureRequiresCompletedOnboarding": False,
                 "contentsPrivate": True, "captureBeforeTermination": True}
        for kind, ext in (("context", ".json"), ("ax", ".txt"), ("screen", ".png")):
            path = self.directory / ("final-" + kind + ext)
            self.paths[("final", kind)] = path
            raw = encoded(final) if kind == "context" else self.png() if kind == "screen" else b"SYNTHETIC FINAL AX\n"
            write(path, raw)
            self.item(M.FINAL_PREFIX + self.context["method"] + "-" + kind + ext, path)
        self.save_manifest()

    @staticmethod
    def png():
        return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=")

    def item(self, human, path):
        self.items.append({"suggestedHumanReadableName": human, "exportedFileName": path.name,
                           "deviceId": self.udid, "isAssociatedWithFailure": False})

    def save_manifest(self):
        write(self.directory / "manifest.json", encoded([{"testIdentifier": M.TARGET + "/NativeLaunchTests/" +
                                                           self.context["method"] + "()", "attachments": self.items}]))

    def add(self, phase, object_id, rows, pid=2001, expanded=False):
        blocks, visible = [], []
        for index, (choice, body, block_id) in enumerate(rows):
            level = int(choice[-1]) if choice.startswith("heading-") else None
            style = {"pinkhaWritingDirection": "rightToLeft", "pinkhaTextAlignment": "natural",
                     "retainedUnknownNativeStyleField": "SYNTHETIC"}
            if level:
                style["level"] = level
            if choice in ("bulleted-list", "numbered-list"):
                style["ordered"] = choice == "numbered-list"
            if choice == "numbered-list":
                style["number"] = 1
            if choice == "checklist":
                style["checked"] = False
            size = {"heading-1": 28, "heading-2": 22, "code": 15}.get(choice, 17)
            font = {"name": "IBMPlexMono" if choice == "code" else "Inter_Bold" if level else "Inter",
                    "family": "SYNTHETIC FAMILY", "pointSize": size + 8 if expanded else size,
                    "bold": level is not None, "italic": False}
            paragraph = {"baseWritingDirection": 1, "alignment": 2}
            length = len(body.encode("utf-16-le")) // 2
            report = {"schema": "native-mounted-text-presentation/v1", "nativeType": "heading" if level else
                      "list_item" if choice in ("numbered-list", "bulleted-list") else "check_list_item" if choice == "checklist" else choice,
                      "nativeStylePresent": True, "nativeStyleJSON": json.dumps(style, sort_keys=True),
                      "contentSizeCategory": "SYNTHETIC_EXPANDED_CATEGORY" if expanded else "SYNTHETIC_LARGE_CATEGORY",
                      "fontReadOrigin": "mounted-UITextView-attributedText-and-typingAttributes",
                      "nativeReadOrigin": "AnyDocumentPresentation.read.snapshot.blocks", "assignedUIFontOnly": True,
                      "fontRuns": [{"location": 0, "length": length, "font": font, "paragraph": paragraph}] if body else [],
                      "typingFont": font, "typingParagraph": paragraph}
            blocks.append({"blockSHA256": C.sha(block_id.encode()), "textSHA256": C.sha(body.encode()),
                           "sourceSHA256": C.sha(body.encode()), "utf16Length": length, "nativeMarks": [], "renderedMarks": [],
                           "selectionLocation": 0, "selectionLength": 0, "isFirstResponder": False, "textPresentation": report})
            visible.append({"identifier": "any-native-block-" + block_id, "value": body,
                            "frame": "{{12, " + str(40 + index * 70) + "}, {300, 60}}"})
        self.native[phase] = {"schema": "any-semantic-anchor-native-rendered/v1", "mode": "read-only", "state": "MATCHED",
                              "pid": pid, "nativeReadOrigin": "AnyDocumentPresentation.read", "engineCalls": 0, "mutations": 0,
                              "selectionChanges": 0, "spaceSHA256": C.sha(b"synthetic-space"), "objectSHA256": C.sha(object_id.encode()),
                              "nativeVersionSHA256": C.sha(b"synthetic-version"), "generation": "00000000-0000-4000-8000-000000000099",
                              "semanticSources": [], "sourceReadOrigin": "TorahEditorSession.associationRecords",
                              "nativeMarkCount": 0, "renderedMarkCount": 0, "blocks": blocks}
        self.meta[phase] = {"schema": "native-styled-ui-observation/v1", "phase": phase, "invocation": self.context,
                            "nativeObservationSHA256": "", "appPIDFromOriginalObserver": pid, "runnerProcessID": 1234,
                            "appLaunchArguments": ["--native-ui-tests", "--native-ui-test-scope", self.context["ownedScope"],
                                                   "-AppleLanguages", "(he,en)", "-AppleLocale", "he_IL"],
                            "visualReview": "PENDING", "fontClaim": "Assigned UIFont, not per-glyph fallback face", "visibleBlocks": visible}
        if phase.startswith("cold-"):
            self.meta[phase].update(hierarchyRowIdentifier="any-native-hierarchy-row-" + object_id, objectIDFromOriginalHierarchy=object_id)

    def command(self, label, argv, start, duration=1, log=b"", execute=False):
        log_ref = write(self.out / (label + ".log"), log)
        cmd = {"argv": argv, "pid": 4321, "pgid": 4321, "started": start, "freeBytesBefore": 10**10,
               "cleanupErrors": [], "termination": [],
               "lifecycleSHA256": "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"}
        command = write(self.out / (label + ".command.json"), encoded(cmd))
        process = dict(cmd, exitCode=0, elapsedSeconds=duration - 0.01, minimumFreeBytes=10**10,
                       stopped=None, logSHA256=log_ref["sha256"], status="EXIT_RECORDED_PENDING_GROUP_OBSERVATION")
        exit_ref = write(self.out / (label + ".process-exit.json"), encoded(process))
        result = dict(process, elapsedSeconds=duration, ownedProcessGroup="ABSENT_ESRCH", status="PASS",
                      processExitReceiptSHA256=exit_ref["sha256"])
        pins = {"command": command, "result": write(self.out / (label + ".result.json"), encoded(result)), "processExit": exit_ref}
        if not execute:
            pins["log"] = log_ref
        return pins

    def live_control(self):
        bundle = "io.synthetic.tests.runner"
        runner = {"bundleIdentifier": bundle, "builtApplication": str(self.out / "products/Runner.app"), "builtExecutable": "Runner",
                  "builtCodeCarriersSHA256": "c" * 64, "installedCodeCarriersSHA256": "c" * 64,
                  "installedApplication": "/Users/SYNTHETIC/Library/Developer/CoreSimulator/Devices/" + self.udid + "/data/App/Runner.app",
                  "dataContainer": "/Users/SYNTHETIC/Library/Developer/CoreSimulator/Devices/" + self.udid + "/data/Container",
                  "installedLookupCommand": "styled-runner-app-00", "processIDFromRequest": 1234}
        self.command("styled-runner-app-00", ["xcrun", "simctl", "get_app_container", self.udid, bundle, "app"],
                     1001, log=(runner["installedApplication"] + "\n").encode())
        self.command("styled-runner-data", ["xcrun", "simctl", "get_app_container", self.udid, bundle, "data"],
                     1003, log=(runner["dataContainer"] + "\n").encode())
        execute = self.command("execute", ["SYNTHETIC-NOT-EXECUTED", "test-without-building"], 1000, duration=100, execute=True)
        rows = []
        for index, (phase, size, before, after) in enumerate((
            ("expanded", "accessibility-extra-extra-extra-large", "live-large-before", "live-accessibility"),
            ("restored", "large", "live-accessibility", "live-large-restored"),
        )):
            native_raw = self.paths[(before, "native")].read_bytes()
            request = {"schema": "native-typography-live-request/v1", "phase": phase,
                       "requestNonce": str(uuid.UUID(int=100 + index)).upper(), "invocation": self.context,
                       "requestedContentSize": size, "runnerProcessID": 1234, "runnerBundleID": bundle,
                       "appPIDFromOriginalObserver": 2001, "nativeObservationJSON": native_raw.decode(),
                       "nativeObservationSHA256": C.sha(native_raw)}
            request_ref = write(self.out / "private-styled-rendezvous" / (phase + "-request.json"), encoded(request))
            readback = size + "\n"
            response = {"schema": "native-typography-live-response/v1", "phase": phase, "requestNonce": request["requestNonce"],
                        "requestSHA256": request_ref["sha256"], "simulatorUDID": self.udid, "contentSize": size,
                        "readback": readback, "readbackSHA256": C.sha(readback.encode()), "status": "APPLIED_AND_READ_BACK"}
            response_ref = write(self.out / "private-styled-rendezvous" / (phase + "-response.json"), encoded(response))
            self.meta[after]["controllerReadback"] = {"requestSHA256": request_ref["sha256"], "responseSHA256": response_ref["sha256"], "response": response}
            rows.append({"phase": phase, "contentSize": size, "request": request_ref, "response": response_ref,
                         "requestNonce": request["requestNonce"], "runnerProcessID": 1234, "appPIDFromOriginalObserver": 2001,
                         "nativeObservationSHA256": C.sha(native_raw), "readback": readback,
                         "readbackSHA256": C.sha(readback.encode()), "responsePublished": True,
                         "set": self.command("styled-" + phase + "-set", ["xcrun", "simctl", "ui", self.udid, "content_size", size], 1010 + index * 40),
                         "read": self.command("styled-" + phase + "-read", ["xcrun", "simctl", "ui", self.udid, "content_size"],
                                              1012 + index * 40, log=readback.encode())})
        self.meta["live-large-restored"].update(baselineObservationSHA256=C.sha(self.paths[("live-large-before", "native")].read_bytes()),
                                                baselineAppPID=2001, restoredAppPID=2001)
        final = {"attempted": True, "target": "large", "actual": "large", "readback": "large\n", "readbackSHA256": C.sha(b"large\n"),
                 "set": self.command("styled-final-restore-set", ["xcrun", "simctl", "ui", self.udid, "content_size", "large"], 1101),
                 "read": self.command("styled-final-restore-read", ["xcrun", "simctl", "ui", self.udid, "content_size"], 1103, log=b"large\n")}
        self.control = {"schema": "native-styled-live-control/v1", "stage": "styled-live-type",
                        "status": "PASS_REQUESTS_AND_RESTORED_NOT_UI_ACCEPTANCE", "invocationSHA256": self.invocation["sha256"],
                        "ownedUDID": self.udid, "sourceCommit": self.context["appSourceCommit"], "initialContentSize": "large",
                        "runner": runner, "execute": execute, "requests": rows, "finalRestore": final, "errors": [],
                        "actualXCTestAcceptance": False, "visualReview": "PENDING", "nativeCalls": 0,
                        "mutationScope": "owned simulator content_size only"}
        self.save_control()

    def save_control(self):
        write(self.out / "styled-live-control.json", encoded(self.control))

    def mutate_native(self, phase, change):
        change(self.native[phase])
        ref = write(self.paths[(phase, "native")], encoded(self.native[phase]))
        self.meta[phase]["nativeObservationSHA256"] = ref["sha256"]
        write(self.paths[(phase, "context")], encoded(self.meta[phase]))

    def collect(self):
        return M.attachments(C, self.directory, self.udid, self.context, self.stage)


class Controls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="SYNTHETIC-styled-collector-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def fixture(self, stage):
        return Fixture(self.root / (stage + "-" + str(uuid.uuid4())), stage)

    def test_finite_observations_remain_non_acceptance(self):
        for stage, count in (("styled-blocks", 29), ("styled-live-type", 6)):
            with self.subTest(stage=stage):
                result = self.fixture(stage).collect()
                self.assertEqual(len(result["phases"]), count)
                self.assertFalse(result["standaloneProductOrXCTestAcceptance"])
                self.assertEqual(result["visualReview"], "PENDING")

    def test_exact_actual_source_inverse_and_changed_proof(self):
        current = (ROOT / "interfaces_work/native-styled-ui/patch/NativeLaunchTests.swift").read_bytes()
        proof = (ROOT / "interfaces_work/native-styled-ui/source-proof.json").read_bytes()
        self.assertEqual(C.sha(M.qualify_source(C, current, proof)), M.PREFIX19_SHA)
        with self.assertRaisesRegex(RuntimeError, "published Styled23"):
            M.qualify_source(C, current, proof + b" ")

    def test_named_native_and_context_json_are_not_interchangeable(self):
        fixture = self.fixture("styled-blocks")
        fixture.items[1]["suggestedHumanReadableName"] = fixture.items[0]["suggestedHumanReadableName"]
        fixture.save_manifest()
        with self.assertRaisesRegex(RuntimeError, "Duplicate"):
            fixture.collect()

    def test_wrong_device_and_absent_final_cannot_qualify(self):
        fixture = self.fixture("styled-blocks")
        fixture.items[0]["deviceId"] = str(uuid.uuid4())
        fixture.save_manifest()
        with self.assertRaisesRegex(RuntimeError, "another phase/method/device"):
            fixture.collect()
        fixture.items[0]["deviceId"] = fixture.udid
        fixture.items.pop()
        fixture.save_manifest()
        with self.assertRaisesRegex(RuntimeError, "final trio"):
            fixture.collect()

    def test_full_native_style_retention_includes_unknown_fields(self):
        fixture = self.fixture("styled-blocks")
        def change(native):
            report = native["blocks"][0]["textPresentation"]
            style = json.loads(report["nativeStyleJSON"])
            style["retainedUnknownNativeStyleField"] = "CHANGED"
            report["nativeStyleJSON"] = json.dumps(style, sort_keys=True)
        fixture.mutate_native("cold-code", change)
        with self.assertRaisesRegex(RuntimeError, "Every original native style byte"):
            fixture.collect()

    def test_partial_font_growth_and_empty_typing_font_are_rejected(self):
        for empty in (False, True):
            with self.subTest(empty=empty):
                fixture = self.fixture("styled-live-type")
                def change(native):
                    if empty:
                        native["blocks"][2]["textPresentation"]["typingFont"]["pointSize"] = 17
                    else:
                        report = native["blocks"][0]["textPresentation"]
                        first = copy.deepcopy(report["fontRuns"][0])
                        first["length"] = 1
                        second = copy.deepcopy(first)
                        second["location"], second["font"]["pointSize"] = 1, 28
                        report["fontRuns"] = [first, second]
                fixture.mutate_native("live-accessibility", change)
                with self.assertRaisesRegex(RuntimeError, "Each actual font run/empty typing font"):
                    fixture.collect()

    def test_cold_process_and_live_native_generation_must_match_their_contract(self):
        fixture = self.fixture("styled-blocks")
        for phase in ("cold-" + x for x in M.CHOICES):
            fixture.meta[phase]["appPIDFromOriginalObserver"] = 2001
            fixture.mutate_native(phase, lambda native: native.update(pid=2001))
        with self.assertRaisesRegex(RuntimeError, "distinct-PID cold reopen"):
            fixture.collect()
        fixture = self.fixture("styled-live-type")
        fixture.mutate_native("live-accessibility", lambda native: native.update(generation=str(uuid.uuid4()).upper()))
        with self.assertRaisesRegex(RuntimeError, "native read/blocks/selection"):
            fixture.collect()

    def test_rehashed_wrong_device_setter_cannot_be_a_coordination_success(self):
        fixture = self.fixture("styled-live-type")
        fixture.control["requests"][0]["set"] = fixture.command("styled-expanded-set",
            ["xcrun", "simctl", "ui", str(uuid.uuid4()), "content_size", "accessibility-extra-extra-extra-large"], 1010)
        fixture.save_control()
        with self.assertRaisesRegex(RuntimeError, "command argv/owned process"):
            fixture.collect()

    def test_missing_actual_final_restore_is_not_hidden_by_pass_status(self):
        fixture = self.fixture("styled-live-type")
        fixture.control["finalRestore"]["attempted"] = False
        fixture.save_control()
        with self.assertRaisesRegex(RuntimeError, "Actual final restoration"):
            fixture.collect()

    def test_arbitrary_matching_lifecycle_hash_in_owned_ledger_is_rejected(self):
        fixture = self.fixture("styled-live-type")
        self.assertFalse(fixture.collect()["standaloneProductOrXCTestAcceptance"])
        label = "styled-expanded-set"
        pins = fixture.control["requests"][0]["set"]
        for key, suffix in (("command", ".command.json"), ("processExit", ".process-exit.json"), ("result", ".result.json")):
            path = fixture.out / (label + suffix)
            value = json.loads(path.read_bytes())
            value["lifecycleSHA256"] = "b" * 64
            if key == "result":
                value["processExitReceiptSHA256"] = pins["processExit"]["sha256"]
            pins[key] = write(path, encoded(value))
        fixture.save_control()
        with self.assertRaisesRegex(RuntimeError, "initial lifecycle record"):
            fixture.collect()


if __name__ == "__main__":
    unittest.main(verbosity=2)
