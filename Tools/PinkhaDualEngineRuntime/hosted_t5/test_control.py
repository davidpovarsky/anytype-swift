"""Authored control cases, NOT_RUN. No native fixtures or test-result substitutes."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import profile
import publication
import run


class SourceControl(unittest.TestCase):
    def test_original_stage_failure_survives_receipt_io_failure(self):
        def fail_write(*_):
            raise OSError("disk unavailable")
        shared = SimpleNamespace(write=fail_write, error=lambda error: {"type": type(error).__name__, "error": str(error)})
        writer = run.FirstFailure(shared)
        actual = {"status": "FAIL", "firstFailure": {"type": "OriginalTestFailure", "error": "original test exited 65"}}
        self.assertFalse(writer.retain(Path("unused"), actual, "terminal"))
        self.assertEqual(writer.first["type"], "OriginalTestFailure")
        self.assertEqual(writer.first["error"], "original test exited 65")
        self.assertEqual(len(writer.receipt_failures), 1)

    def test_closed_source_profile_cannot_admit_a_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / profile.PREFIX
            target.mkdir(parents=True)
            target.joinpath("activation.json").write_bytes(Path(profile.__file__).with_name("activation.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "T5 is CLOSED"):
                profile.activation(root)

    def test_unresolved_original_group_forbids_preserve_shutdown_and_next_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            shared = SimpleNamespace(write=lambda path, value: path.write_text(str(value)),
                error=lambda error: {"type": type(error).__name__, "error": str(error)}, product_integrity=lambda _: {})
            commands = SimpleNamespace(is_open=False, blocked={"status": "CLOSED_UNRESOLVED_ORIGINAL_OWNED_GROUP"},
                                       first_exception={"type": "TimeoutError", "error": "original owned process unresolved"})
            calls = []
            consumer = SimpleNamespace(root=root, shared_module=shared, commands=commands, devices=[], invoked_devices=set(),
                built={}, binding={"sourceSHA": "a" * 40}, t5_containers={}, t5_shutdown={})
            def create(*args, **kwargs):
                consumer.devices.append("00000000-0000-0000-0000-000000000001")
                raise TimeoutError("original owned process unresolved")
            def forbidden(*args, **kwargs):
                calls.append("forbidden")
                raise AssertionError("new process/device operation after unresolved custody")
            consumer.create = create
            consumer.command = consumer.preserve = consumer.container = forbidden
            writer = run.FirstFailure(shared)
            result, scope = run.execute_lane(consumer, "t5-native-ui", "native_ui", {},
                SimpleNamespace(verify_created_device=forbidden), {}, {}, writer)
            self.assertEqual(calls, [])
            self.assertIsNone(scope)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(writer.first["type"], "TimeoutError")
            self.assertEqual(result["ownedSimulator"]["status"], "UNRESOLVED_NO_FURTHER_DEVICE_OPERATION")

    def test_terminal_io_failure_does_not_replace_prior_native_error(self):
        shared = SimpleNamespace(write=lambda *_: (_ for _ in ()).throw(OSError("receipt failure")),
            error=lambda error: {"type": type(error).__name__, "error": str(error)})
        writer = run.FirstFailure(shared)
        writer.failure(RuntimeError("native readback failed"), "original-native-readback")
        first = dict(writer.first)
        result = {"status": "FAIL", "firstFailure": first}
        self.assertFalse(writer.retain(Path("unused"), result, "final"))
        self.assertEqual(writer.first, first)
        self.assertEqual(result["firstFailure"], first)

    def test_first_terminal_io_failure_replaces_only_an_explicit_null_cause(self):
        shared = SimpleNamespace(write=lambda *_: (_ for _ in ()).throw(OSError("first terminal failure")),
            error=lambda error: {"type": type(error).__name__, "error": str(error)})
        writer = run.FirstFailure(shared)
        result = {"status": "PASS_PENDING_RECEIPT", "firstFailure": None}
        self.assertFalse(writer.retain(Path("unused"), result, "final"))
        self.assertEqual(result["firstFailure"], writer.first)
        self.assertEqual(result["firstFailure"]["type"], "OSError")
        self.assertEqual(result["status"], "FAIL")

    def test_ui_publication_uses_only_original_selected_attachment_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            lane = root / "evidence/lanes/t5-native-ui"
            attachments = lane / "core-ui/private-attachments"
            attachments.mkdir(parents=True)
            (lane / "unselected-private.json").write_text('{"private":true}')
            (attachments / "selected.png").write_bytes(b"selected-original")
            (attachments / "unselected.png").write_bytes(b"unselected-private")
            (attachments / "manifest.json").write_text('[{"testIdentifier":"Original/selected","attachments":[{"exportedFileName":"selected.png"}]},{"testIdentifier":"Other/unselected","attachments":[{"exportedFileName":"unselected.png"}]}]')
            evidence = SimpleNamespace(METHODS={"original": "Original/selected"}, require=profile.require,
                attachment_path=lambda base, name: base / name)
            t5 = {"evidence": evidence, "helpers": {"t5_native_ui_r08": SimpleNamespace(METHOD="Original/r08", APPEARANCES=("light", "dark"))}}
            allowed = publication.original_allowed_files(root, t5)
            self.assertIn(attachments / "selected.png", allowed)
            self.assertNotIn(attachments / "unselected.png", allowed)
            self.assertNotIn(lane / "unselected-private.json", allowed)


if __name__ == "__main__":
    unittest.main()
