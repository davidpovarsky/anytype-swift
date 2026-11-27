"""Four new pure boundary checks; synthetic files, no process/backend/UI call."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


module = load("accessibility_boundary_candidate", Path(__file__).with_name("native_accessibility_observations.py"))
original = load("existing_styled_observations", ROOT / "interfaces_work/native-styled-control/native_styled_observations.py")
rtl = load("existing_rtl_matrix", ROOT / "interfaces_work/native-rtl/native_rtl_matrix.py")


class Core:
    @staticmethod
    def require(value, message):
        if not value:
            raise ValueError(message)

    @staticmethod
    def sha(value):
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def raw(path, maximum):
        value = Path(path).read_bytes()
        if len(value) > maximum:
            raise ValueError("Synthetic input exceeded the original finite bound")
        return value

    @staticmethod
    def decode(value):
        return json.loads(value)

    @staticmethod
    def digest(path):
        return Core.sha(Path(path).read_bytes())


c = Core()
UDID = "2C15BD20-7EC7-4EF9-9A31-90002BA99712"


def write(path, value):
    path.write_bytes(value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True) + "\n").encode())


def context(stage):
    return dict(schema="native-accessibility-invocation/v1", runID="97B7A74E-EFFF-4EAC-951C-5EE1FD5AF16D",
                appSourceCommit="a" * 40, uiSourceCommit="a" * 40, simulatorUDID=UDID,
                ownedScope="C362A522-2C97-4E9A-AE69-46FFBB602F6A", method=module.PLANS[stage]["method"],
                appLanguage="he", osLanguage="en", contentSize=module.PLANS[stage]["contentSize"],
                appearance="light", deviceFamily="ipad", settingsReadbackSHA256="b" * 64)


def voice_trace(searches=2):
    actions = ["currentSpeech.initial"] + ["moveForward.search." + str(i) for i in range(1, searches + 1)]
    actions += ["currentSpeech.target", "moveForward.afterTarget", "moveBackward.returnToTarget", "currentSpeech.returnedTarget"]
    spoken = ["A preceding element"] * searches + ["Native speech marker"]
    spoken += ["Native speech marker", "A different next element", "Native speech marker", "Native speech marker"]
    trace = [{"action": action, "utterance": speech, "operationSeconds": 0.1, "elapsedSeconds": i + 1}
             for i, (action, speech) in enumerate(zip(actions, spoken))]
    return {"voiceover-returned": {"observedUtterance": "native speech marker", "focusedAccessibilityIdentifierObserved": False},
            "voiceover-trace": dict(initialVoiceOverEnabled=False, enableAttempted=True, enabledObserved=True,
                disabledObserved=True, completedTraversal=True, cleanupFailures=[], trace=trace,
                maximumSearchForwardMoves=24, maximumForwardMoves=25, maximumSpeechOperations=29,
                traversalBudgetSeconds=60, traversalElapsedSeconds=len(trace) + 10,
                speechMatchRule="normalized utterance contains the fixture phrase: native speech marker",
                focusedAccessibilityIdentifierObserved=False)}


def ledger(out, label, argv, raw, started, elapsed=0.1):
    # Pure synthetic original73bb-shaped receipts. No PID is probed or signaled.
    command = dict(argv=argv, pid=90001, pgid=90001, started=started, cleanupErrors=[], termination=[],
                   lifecycleSHA256=original.OWNED_OUTCOMES_SHA)
    process = dict(command, exitCode=0, elapsedSeconds=elapsed, stopped=None, logSHA256=c.sha(raw),
                   status="EXIT_RECORDED_PENDING_GROUP_OBSERVATION")
    write(out / (label + ".command.json"), command)
    write(out / (label + ".process-exit.json"), process)
    result = dict(process, status="PASS", ownedProcessGroup="ABSENT_ESRCH",
                  processExitReceiptSHA256=c.digest(out / (label + ".process-exit.json")))
    write(out / (label + ".result.json"), result)
    write(out / (label + ".log"), raw)


class Boundaries(unittest.TestCase):
    def test_closed_scope_and_original13_environment(self):
        with self.assertRaises(ValueError):
            module.require_runtime_ready(c)
        for stage in module.PLANS:
            fields = context(stage)
            raw = json.dumps(fields, sort_keys=True).encode()
            result = module.environment(c, raw, UDID, stage)
            self.assertEqual(result["PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_SHA256"], c.sha(raw))
            self.assertFalse(module.plan(c, stage)["runtimeReady"])
        for key, value in (("contentSize", module.EXPANDED), ("uiSourceCommit", "c" * 40),
                           ("osLanguage", "he"), ("method", module.AUDIT)):
            fields = context("accessibility-voiceover-large"); fields[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module._context(c, fields, UDID, "accessibility-voiceover-large")
        with self.assertRaises(ValueError):
            module.plan(c, "all-native23")

    def test_speech_order_cleanup_and_literal_bounds(self):
        for count in (0, 24):
            module._voiceover(c, voice_trace(count))
        mutations = [
            lambda x: x["voiceover-trace"].update(disabledObserved=False),
            lambda x: x["voiceover-trace"].update(initialVoiceOverEnabled=True),
            lambda x: x["voiceover-trace"]["trace"][-1].update(action="currentSpeech.target"),
            lambda x: x["voiceover-trace"]["trace"][-3].update(utterance="Native speech marker"),
            lambda x: x["voiceover-trace"]["trace"][-1].update(elapsedSeconds=61),
            lambda x: x["voiceover-trace"]["trace"][-1].update(utterance="x" * 16385),
            lambda x: x["voiceover-returned"].update(focusedAccessibilityIdentifierObserved=True),
        ]
        for index, mutate in enumerate(mutations):
            value = voice_trace(); mutate(value)
            with self.subTest(index=index), self.assertRaises(ValueError):
                module._voiceover(c, value)

    def test_manifest_method_device_types_and_final_custody(self):
        with tempfile.TemporaryDirectory(prefix="ax-manifest-", dir=Path(__file__).parent) as temporary:
            out = Path(temporary); names = []
            for phase in module.PHASES[module.AUDIT]:
                names.extend([(module.PREFIX + phase, ".json"), (module.PREFIX + phase + "-private-ax", ".txt"),
                              (module.PREFIX + phase, ".png")])
            names.extend((module.PREFIX + phase + "-audit", ".json") for phase in ("library", "editor"))
            names.extend((module.FINAL_PREFIX + module.AUDIT + "-" + name, ext)
                         for name, ext in (("context", ".json"), ("ax", ".txt"), ("screen", ".png")))
            items = []
            for index, (human, ext) in enumerate(names):
                name = "synthetic-" + str(index) + ext
                data = b"{}" if ext == ".json" else b"synthetic AX fixture" if ext == ".txt" else (
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (1).to_bytes(4, "big") * 2 + b"\x00" * 9)
                write(out / name, data)
                items.append(dict(suggestedHumanReadableName=human + ext, exportedFileName=name,
                                  deviceId=UDID, isAssociatedWithFailure=False))
            original_manifest = [dict(testIdentifier=module.TARGET + "/NativeLaunchTests/" + module.AUDIT + "()", attachments=items)]
            write(out / "manifest.json", original_manifest)
            self.assertEqual(len(module._attachments(c, original, out, UDID, module.AUDIT)[1]), 14)
            for mutate in (lambda m: m[0].update(testIdentifier="NativeLaunchTests/" + module.VOICEOVER),
                           lambda m: m[0]["attachments"][0].update(deviceId=context("accessibility-audit-large")["runID"]),
                           lambda m: m[0]["attachments"].pop(),
                           lambda m: m[0]["attachments"][0].update(exportedFileName="../wrong.json")):
                changed = copy.deepcopy(original_manifest); mutate(changed); write(out / "manifest.json", changed)
                with self.assertRaises(ValueError):
                    module._attachments(c, original, out, UDID, module.AUDIT)

    def test_original_ledger_binds_selected_size_and_restoration(self):
        helpers, _ = rtl.original_helpers(c, ROOT / "interfaces_work/native-rtl/portable-helper-source")
        with tempfile.TemporaryDirectory(prefix="ax-readbacks-", dir=Path(__file__).parent) as temporary:
            out = Path(temporary); fields = context("accessibility-audit-expanded")
            prefs = plistlib.dumps({"AppleLanguages": ["en"], "AppleLocale": "en_US"})
            for prefix, size, started in (("rtl-before", "large", 100), ("accessibility-before", module.EXPANDED, 120),
                                          ("accessibility-after", module.EXPANDED, 170), ("accessibility-restored", "large", 190)):
                ledger(out, prefix + "-language-readback", ["xcrun", "simctl", "spawn", UDID, "defaults", "export", "NSGlobalDomain", "-"], prefs, started)
                for index, (key, value) in enumerate((("appearance", "light"), ("content_size", size)), 1):
                    ledger(out, prefix + "-" + key.replace("_", "-") + "-readback",
                           ["xcrun", "simctl", "ui", UDID, key], (value + "\n").encode(), started + index)
                value, _ = module._readbacks(c, original, out, fields, helpers, prefix, size)
                write(out / (prefix + "-environment.json"), value)
            fields["settingsReadbackSHA256"] = c.digest(out / "accessibility-before-environment.json")
            argv = ["xcodebuild", "test-without-building", "-xctestrun", str(out / "Selected.xctestrun"),
                    "-destination", "platform=iOS Simulator,id=" + UDID,
                    "-default-test-execution-time-allowance", "900", "-maximum-test-execution-time-allowance", "900",
                    "-only-testing:" + module.TARGET + "/NativeLaunchTests/" + module.AUDIT]
            ledger(out, "execute", argv, b"synthetic result only", 150, 10)
            for label, size, at in (("accessibility-set-content-size", module.EXPANDED, 110),
                                    ("accessibility-restore-content-size", "large", 180)):
                ledger(out, label, ["xcrun", "simctl", "ui", UDID, "content_size", size], b"", at)
            result = module._settings(c, original, out, fields, "accessibility-audit-expanded", helpers)
            self.assertIsNotNone(result["expandedSettingRestoration"])
            changed = dict(fields, settingsReadbackSHA256="0" * 64)
            with self.assertRaises(ValueError):
                module._settings(c, original, out, changed, "accessibility-audit-expanded", helpers)
            ledger(out, "accessibility-restore-content-size", ["xcrun", "simctl", "ui", UDID, "content_size", "large"], b"", 155)
            with self.assertRaises(ValueError):
                module._settings(c, original, out, fields, "accessibility-audit-expanded", helpers)
            write(out / "accessibility-after-content-size-readback.log", b"large\n")
            with self.assertRaises(ValueError):
                module._settings(c, original, out, fields, "accessibility-audit-expanded", helpers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
