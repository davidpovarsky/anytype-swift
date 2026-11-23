"""One new original-data control; no Docker, package, Go, or native work."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[4]
SUBJECT_PATH = ROOT / "Tools/AnyEngineValidation/loaded_account_witness/portable/compiler_producer.py"
ORIGINALS = ROOT / "docs/validation/20261123-loaded-account-portable/compiler-original-45262244082/originals"
DATA_INPUTS = {'result.json': '3c3f2cdecf58d3b95092f4371fc43877637e88dfd0e92474ca9799e150f5b275', 'commands/002-before-blob-00.stdout': '0fd72d2024a5b3a1bdccb5cb9392a5ae8b646f685b0c56493c7f44feb62370e3', 'commands/019-acquire-inspect-before.stdout': '189b5927c03c373b6a19111ae090ebac806f850ec1cd01198a3264febde16d1d', 'commands/021-acquire-cleanup-before.stdout': '6e74af6a6be3b4696096dc9704f08266d3f351ac242ab62137cd0d64f5efece2'}
OLD = '        require(host["Binds"] == owned["binds"], "container_bindings")\n'
NEW = ('        require(isinstance(host["Binds"], list)\n'
       '                and all(isinstance(value, str) for value in host["Binds"])\n'
       '                and sorted(host["Binds"]) == sorted(owned["binds"]), "container_bindings")\n')
spec = importlib.util.spec_from_file_location("compiler_bind_order_subject", SUBJECT_PATH)
subject = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = subject
spec.loader.exec_module(subject)

def original(name):
    path = ORIGINALS / name
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != DATA_INPUTS[name]:
        raise AssertionError("original_data_hash:" + name)
    return body

class CompilerBindOrderOriginalControl(unittest.TestCase):
    observations = []

    def test_original_docker_bind_order_accepts_only_exact_owned_multiset(self):
        result = json.loads(original("result.json"), object_pairs_hook=subject.unique)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["primary_error"], {"type": "Refusal", "message": "container_bindings"})
        self.assertEqual(result["final_errors"], [
            {"phase": "owned_cleanup", "type": "Refusal", "message": "compiler_container_cleanup_failed"}])
        self.assertEqual(result["context"]["run_id"], "45262244082")
        self.assertEqual(result["context"]["run_attempt"], "1")
        self.assertEqual(result["context"]["source_sha"], "56b4caafae1c0898b483717abed495f2e3b9281b")
        before = original("commands/002-before-blob-00.stdout")
        self.assertEqual(hashlib.sha256(before).hexdigest(),
                         "0fd72d2024a5b3a1bdccb5cb9392a5ae8b646f685b0c56493c7f44feb62370e3")
        current = SUBJECT_PATH.read_bytes()
        self.assertEqual(current.count(NEW.encode()), 1)
        self.assertEqual(current.replace(NEW.encode(), OLD.encode(), 1), before)
        self.assertEqual(pathlib.Path(subject.__file__).resolve(), SUBJECT_PATH.resolve())
        owned = result["containers"]["acquire"]
        commands = {row["name"]: row for row in result["commands"]}
        argv = commands["acquire-create"]["argv"]
        declared = [argv[i + 1] for i, value in enumerate(argv) if value == "--volume"]
        self.assertEqual(declared, owned["binds"])
        self.assertEqual(len(declared), 2)
        self.assertEqual(len(set(declared)), 2)
        p = object.__new__(subject.Producer)
        p.containers = copy.deepcopy(result["containers"])
        p.base_id = "sha256:31b7df755869f3d5b0a8a87e0f29ea85cac62a522f008681d304e311160d181f"
        ctx = result["context"]
        p.labels = {"org.anytapy.scope": "loaded-account-compiler",
                    "org.anytapy.run": ctx["run_id"], "org.anytapy.attempt": ctx["run_attempt"],
                    "org.anytapy.source": ctx["source_sha"]}
        rows = []
        with mock.patch.object(subject.subprocess, "Popen", side_effect=AssertionError("process_forbidden")), \
             mock.patch.object(subject.os, "system", side_effect=AssertionError("process_forbidden")):
            for name in ("019-acquire-inspect-before", "021-acquire-cleanup-before"):
                parsed = json.loads(original("commands/" + name + ".stdout"), object_pairs_hook=subject.unique)
                self.assertEqual(len(parsed), 1)
                info = parsed[0]
                self.assertEqual(info["HostConfig"]["Binds"], list(reversed(declared)))
                self.assertEqual(info["State"]["Running"], False)
                self.assertEqual(info["State"]["Pid"], 0)
                self.assertEqual(info["State"]["Status"], "created")
                self.assertIs(p.check_container("acquire", info), info)
                rows.append({"case": name, "origin": "original Docker inspection",
                             "outcome": "ACCEPTED_COMPLETE_OWNED_BIND_MULTISET"})
            original_info = parsed[0]
            in_order = copy.deepcopy(original_info)
            in_order["HostConfig"]["Binds"] = list(declared)
            self.assertIs(p.check_container("acquire", in_order), in_order)
            rows.append({"case": "declared-order", "origin": "synthetic order only", "outcome": "ACCEPTED"})
            script, out = declared
            cases = [
                ("missing-all", []),
                ("missing-script", [out]),
                ("missing-output", [script]),
                ("extra", declared + ["/etc:/unowned:ro"]),
                ("extra-duplicate", declared + [script]),
                ("replacement-duplicate", [script, script]),
                ("changed-source", [script.replace("portable:/scripts", "portable-other:/scripts"), out]),
                ("changed-destination", [script.replace(":/scripts:", ":/other:"), out]),
                ("changed-read-mode", [script.rsplit(":", 1)[0] + ":rw", out]),
                ("changed-write-mode", [script, out.rsplit(":", 1)[0] + ":ro"]),
                ("extra-propagation", [script + ",rshared", out]),
                ("empty-string", ["", out]),
                ("non-string", [7, out]),
                ("null", None),
                ("string", script),
                ("tuple", tuple(declared)),
                ("object", {"binds": declared}),
            ]
            for name, binds in cases:
                with self.subTest(case=name):
                    value = copy.deepcopy(original_info)
                    value["HostConfig"]["Binds"] = binds
                    with self.assertRaises(subject.Refusal) as caught:
                        p.check_container("acquire", value)
                    self.assertEqual(str(caught.exception), "container_bindings")
                    rows.append({"case": name, "origin": "synthetic negative mutation",
                                 "outcome": "REFUSED_CONTAINER_BINDINGS"})
        self.assertEqual(p.containers, result["containers"])
        type(self).observations = rows
