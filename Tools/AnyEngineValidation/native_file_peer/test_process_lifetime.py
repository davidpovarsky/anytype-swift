#!/usr/bin/env python3
import ast, pathlib, re, shlex, subprocess, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent
SCOPE = {"re":re, "shlex":shlex}
def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)
SCOPE["require"] = require
tree = ast.parse((ROOT/"run_native.py").read_text())
functions = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in
             ("peer_start_barrier","require_fresh_reopen")]
exec(compile(ast.Module(body=functions,type_ignores=[]),str(ROOT/"run_native.py"),"exec"),SCOPE)

class PeerLifetime(unittest.TestCase):
    def test_immediate_exit_waits_until_original_process_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=pathlib.Path(tmp)/"start marker.command.json"
            process=subprocess.Popen(["sh","-c",SCOPE["peer_start_barrier"](marker)+"printf native-completed"],stdout=subprocess.PIPE)
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    process.communicate(timeout=0.15)
                self.assertIsNone(process.poll())
                marker.write_text('{"phase":"start-reopen"}')
                stdout,_=process.communicate(timeout=2)
                self.assertEqual(process.returncode,0)
                self.assertEqual(stdout,b"native-completed")
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()

    def fixtures(self):
        return ({"containerID":"a"*64,"startedAt":"2026-11-24T22:39:12.999757491Z"},
                {"containerID":"b"*64,"finishedAt":"2026-11-24T22:39:09.000000000Z"},
                {"containerID":"c"*64,"finishedAt":"2026-11-24T22:39:10.000000000Z"})

    def test_reused_kernel_numbers_do_not_replace_original_lifetime_evidence(self):
        reopen,owner,member=self.fixtures()
        for row in (reopen,owner,member):
            row.update(hostPID=42,namespace="net:[4026532270]")
        SCOPE["require_fresh_reopen"](reopen,owner,member)

    def test_same_container_or_missing_stop_cannot_prove_new_process(self):
        for fault in ("same","missing","live","malformed"):
            with self.subTest(fault=fault):
                reopen,owner,member=self.fixtures()
                if fault=="same": reopen["containerID"]=owner["containerID"]
                if fault=="missing": owner.pop("finishedAt")
                if fault=="live": owner["finishedAt"]="2026-11-24T22:39:13.000000000Z"
                if fault=="malformed": reopen["containerID"]="unknown"
                with self.assertRaises(RuntimeError):
                    SCOPE["require_fresh_reopen"](reopen,owner,member)

if __name__=="__main__":
    unittest.main()
