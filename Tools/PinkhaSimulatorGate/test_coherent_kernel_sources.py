"""Two new controls for the actual coherent readiness/source-check failure boundaries."""
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock

import coherent_controller_sources as source
import coherent_release_cleanup as cleanup
import run_owned_single_lane as groups
import run_t5_apple_pair as pair
import wave15_batch as batch


class CoherentKernelAndSourceControls(unittest.TestCase):
    def test_coherent_owned_readiness_and_nested_cleanup_use_exact_kernel_absence(self):
        with tempfile.TemporaryDirectory(prefix="coherent-kernel-control-") as tmp:
            app = Path(tmp).resolve()
            root = app / "evidence/lanes/editor/owned-readiness"
            root.mkdir(parents=True)
            log = root / "new-coherent-command.log"
            adapter = cleanup.readiness_commands(pair)
            result, actual_log = adapter.run_logged([sys.executable, "-B", "-c", "print('COHERENT_NEW_SCOPE')"],
                                        app, root, "new-coherent-command", timeout=15)
            self.assertEqual(actual_log, log)
            command = json.loads(log.with_suffix(".command.json").read_text())
            original = root / command["original_owned_command"]
            before = original.read_bytes()
            observed = command["owned_group_quiescence"]
            self.assertEqual((result["status"], observed["status"], observed["absence_source"]),
                             ("SUCCESS", "PASS", "KERNEL_ESRCH"))
            self.assertEqual((observed["budget_seconds"], observed["observations"]), (10, 0))
            self.assertEqual(observed["kernel_group_observation"]["errno"], errno.ESRCH)
            pid = json.loads(before)["worker_pid"]
            self.assertEqual(pid, command["controller_process_id"])
            report = {"groups_checked": 0}
            cleanup.audit_nested_receipts([root], app, app / "private", report)
            self.assertEqual(report["groups_checked"], 1)
            self.assertEqual(report["original_owned_commands"][0]["absence_source"], "KERNEL_ESRCH")
            self.assertEqual(original.read_bytes(), before)
            retained = Path(os.environ["PINKHA_COHERENT_CONTROL_ORIGINALS"]).resolve()
            self.assertTrue(retained.is_dir())
            for path in (log, log.with_suffix(".command.json"), original):
                with (retained / path.name).open("xb") as output:
                    output.write(path.read_bytes())
            for bad in ({"worker_pid": os.getpgrp(), "owned_group_cleanup": "TERM_THEN_KILL"},
                        {"worker_pid": pid, "owned_group_cleanup": "NOT_COMPLETED"}):
                path = root / "invalid.json";path.write_text(json.dumps(bad))
                with mock.patch.object(groups.os, "killpg") as signal:
                    with self.assertRaises(RuntimeError):
                        groups.verify_owned_group_stopped(path, cleanup_profile=batch.COHERENT_HEART_PROFILE)
                    signal.assert_not_called()
            print("COHERENT_KERNEL_ORIGINAL " + json.dumps({
                "ownedPID": pid, "originalSHA256": hashlib.sha256(before).hexdigest(),
                "readinessKernelAbsence": True, "nestedGroups": 1, "oldProductTests": 0}, sort_keys=True))

    def test_single_git_batch_preserves_exact_loaded_closure_and_rejects_corruption(self):
        with tempfile.TemporaryDirectory(prefix="coherent-source-control-") as tmp:
            root = Path(tmp).resolve()
            names = ["Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py",
                     "Tools/PinkhaSimulatorGate/coherent_controller_sources.py",
                     "Tools/PinkhaSimulatorGate/first.py",
                     "Tools/PinkhaSimulatorGate/second.py",
                     "Tools/Hanlin/helper.py"]
            modules = {}
            for n,name in enumerate(names):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(("# exact original source " + str(n) + "\n").encode())
                module=ModuleType("_coherent_source_control_"+str(n));module.__file__=str(path)
                modules[module.__name__]=module
            def git(*args):
                return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.STDOUT)
            git("init","--quiet")
            git("add",".")
            git("-c","user.name=Control Fixture","-c","user.email=control@example.invalid","commit","-qm","Exact fixture")
            head=git("rev-parse","HEAD").decode().strip()
            expected={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(names)}
            actual_check=subprocess.check_output
            with mock.patch.dict(sys.modules,modules), mock.patch.object(source.subprocess,"check_output",
                                                                         wraps=actual_check) as commands:
                self.assertEqual(source.control_sources(root,head),expected)
                self.assertEqual(len(commands.call_args_list),2)
                self.assertEqual(commands.call_args_list[1].args[0][-2:],["cat-file","--batch"])
                self.assertEqual(commands.call_args_list[1].kwargs["timeout"],30)
            ordered=sorted(names)
            raw=actual_check(
                ["git","-C",str(root),"cat-file","--batch"],
                input="".join(head+":"+name+"\n" for name in ordered).encode(),timeout=30)
            self.assertEqual(source.decode_batch(raw,ordered),
                             {name:(root/name).read_bytes() for name in ordered})
            for label,changed in [("truncated",raw[:-2]),("extra",raw+b"x"),
                                  ("wrong_type",raw.replace(b" blob ",b" tree ",1)),
                                  ("changed_blob",raw.replace(b"exact original",b"EXACT original",1)),
                                  ("missing",b"missing missing\n")]:
                with self.subTest(protocol=label), self.assertRaises(ValueError):
                    source.decode_batch(changed,ordered)
            path=root/names[-1];path.write_bytes(b"# changed after original commit\n")
            with mock.patch.dict(sys.modules,modules), self.assertRaisesRegex(ValueError,"dirty"):
                source.control_sources(root,head)
            git("checkout","--",names[-1])
            with mock.patch.dict(sys.modules,modules), self.assertRaises(ValueError):
                source.control_sources(root,"0"*40)
            path.unlink()
            with mock.patch.dict(sys.modules,modules), self.assertRaisesRegex(ValueError,"dirty"):
                source.control_sources(root,head)


if __name__ == "__main__":
    unittest.main()
