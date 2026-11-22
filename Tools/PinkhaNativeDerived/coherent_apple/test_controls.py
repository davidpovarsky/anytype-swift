"""Narrow admission, raw-wire and assertion-translation controls for the new lane."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import contract
import fixture
import run_host


class CoherentAppleControls(unittest.TestCase):
    def test_original_assertions_are_exactly_bound_before_fixture_derivation(self):
        original = {
            "coherent_authority_account_test.go": "3a1fcd0f370224e59137897467e59bb4d41e44ce580e3c0bacce48170019d71b",
            "native_signed_revocation_base_test.go": "389184e3ba40e1371143505c48eedd6420872f35f57d66784ee5262c62bed25d",
        }
        values, hashes, identity = fixture.source_files(contract.ROOT, original)
        self.assertEqual(len(values), 3)
        self.assertEqual(len(identity), 64)
        for name, raw in values.items():
            self.assertTrue(raw.startswith(fixture.PREFIX.encode()))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), hashes[name])
        for name in original:
            raw = (contract.ROOT / fixture.ORIGINAL_DIRECTORY / name).read_bytes()
            derived = fixture.transformed(name, raw).decode()
            self.assertEqual(raw.decode().count("require."), derived.count("coherentAppleRequire."))
            self.assertNotIn("testing.T", derived)
            with self.assertRaises(ValueError):
                fixture.transformed(name, raw.replace(b"require.NoError", b"require.UnreviewedAssertion", 1))
        with self.assertRaises(ValueError):
            fixture.source_files(contract.ROOT, dict(original, **{"coherent_authority_account_test.go": "0" * 64}))

    def test_raw_t5_denial_requires_exact_error_and_no_payload(self):
        def wire(description=b"PINKHA_CURRENT_SPACE_READ_DENIED_V1"):
            error = b"\x08\x02\x12" + bytes([len(description)]) + description
            return b"\x0a" + bytes([len(error)]) + error
        for kind in ("search", "show"):
            result = run_host.qualify_t5_wire(wire(), kind, "PINKHA_CURRENT_SPACE_READ_DENIED_V1")
            self.assertTrue(result["payload_absent"])
            bad = [b"", wire() + b"\x12\x00", wire()+wire(), wire().replace(b"\x08\x02", b"\x08\x00"),
                   wire(b"generic error"), wire()[:-1], b"\x8a\x00" + wire()[1:], wire() + b"\x18\x01"]
            if kind == "show": bad.append(wire() + b"\x18\x00")
            for value in bad:
                with self.subTest(kind=kind, value=value):
                    with self.assertRaises(ValueError):
                        run_host.qualify_t5_wire(value, kind, "PINKHA_CURRENT_SPACE_READ_DENIED_V1")
        run_host.qualify_t5_wire(wire() + b"\x18\x00", "search", "PINKHA_CURRENT_SPACE_READ_DENIED_V1")

    def test_build_identity_never_conflates_production_and_fixture(self):
        value = dict(status="BUILT_DISTINCT_COHERENT_APPLE_FRAMEWORKS_NOT_EXECUTED", app_sha="a" * 40,
            run_id="123", native_run=contract.NATIVE_RUN, native_source=contract.NATIVE_SOURCE,
            patch_sha256=contract.PATCH, inventory_sha256=contract.INVENTORY, native_source_count=139,
            old_tests_executed=0, bridge_sha256="b" * 64, frameworks={
                "production": dict(fixture_compiled=False, fixture_tag=None, binary_sha256="1" * 64),
                "fixture": dict(fixture_compiled=True, fixture_tag=contract.FIXTURE_TAG, binary_sha256="2" * 64)})
        contract.validate_build_receipt(value, "a" * 40, "123")
        for field, wrong in [("native_source_count", 85), ("patch_sha256", "0"*64),
                             ("old_tests_executed", 25), ("status", "PASS")]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    contract.validate_build_receipt(dict(value, **{field: wrong}), "a" * 40, "123")
        for field, wrong in [("fixture_compiled", True), ("fixture_tag", contract.FIXTURE_TAG), ("binary_sha256", "2"*64)]:
            changed = deepcopy(value); changed["frameworks"]["production"][field] = wrong
            with self.assertRaises(ValueError):
                contract.validate_build_receipt(changed, "a" * 40, "123")

    def test_native_producer_must_be_exact_successful_route(self):
        value = dict(id=int(contract.NATIVE_RUN), run_attempt=1, head_sha=contract.NATIVE_SOURCE,
            status="completed", conclusion="success", event="workflow_dispatch",
            head_branch="codex/chatgpt-wave15-shared-20261121", path=".github/workflows/torah-inspector-ipados27.yml",
            display_title="Pinkha coherent-heart-native · " + contract.NATIVE_SOURCE)
        contract.validate_native_run(value)
        for key, wrong in [("run_attempt", 2), ("conclusion", "failure"), ("status", "in_progress"),
                           ("head_sha", "0" * 40), ("head_branch", "develop"), ("display_title", "arbitrary green job")]:
            with self.assertRaises(ValueError):
                contract.validate_native_run(dict(value, **{key: wrong}))

    def test_go_assertion_adapter_rejects_failures_and_runs_cleanup(self):
        go = shutil.which("go")
        self.assertIsNotNone(go, "The narrow assertion adapter controls require the pinned real Go compiler")
        version = subprocess.check_output([go, "version"], text=True).strip()
        self.assertTrue(version.startswith("go version go1.26.5 "), version)
        source = (contract.HERE / "fixture_bridge.go").read_text()
        begin, end = "type coherentAppleAbort struct{}", "// PinkhaCoherentAppleAuthorityFixture is a one-shot"
        self.assertEqual(source.count(begin), 1)
        self.assertEqual(source.count(end), 1)
        fragment = source[source.index(begin):source.index(end)]
        with tempfile.TemporaryDirectory(prefix="coherent-assertion-controls-") as directory:
            root = Path(directory)
            (root / "go.mod").write_text("module coherentassertioncontrols\n\ngo 1.26.5\n")
            (root / "adapter.go").write_text('package service\nimport("fmt";"path/filepath";"reflect";"runtime")\n' + fragment)
            (root / "adapter_test.go").write_text(GO_CONTROLS)
            completed = subprocess.run([go, "test", "-count=1", "-timeout=30s", "-v", "./..."], cwd=root,
                env=dict(os.environ, GOTOOLCHAIN="local", GOWORK="off", GOFLAGS="", GOPROXY="off"),
                text=True, capture_output=True, timeout=90)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(completed.stdout.count("--- PASS: Test"), 3)
            print(completed.stdout)


GO_CONTROLS = r'''package service
import("testing";"strings";"reflect")
func expectAbort(t *testing.T, run func(*coherentAppleT)) {
    t.Helper(); probe:=&coherentAppleT{}
    defer func(){if _,ok:=recover().(coherentAppleAbort);!ok||!probe.failed{t.Fatal("assertion did not fail closed")}}()
    run(probe); t.Fatal("assertion returned after failure")
}
func TestAssertionAdapterPositiveAndNegativeSemantics(t *testing.T) {
    a:=coherentAppleRequire; p:=&coherentAppleT{}; pointer:=new(int)
    a.True(p,true);a.False(p,false);a.NoError(p,nil);a.Equal(p,[]byte{1},[]byte{1});a.NotEqual(p,1,2)
    a.Nil(p,(*int)(nil));a.NotNil(p,pointer);a.Empty(p,[]int{});a.NotEmpty(p,[]int{1})
    a.Len(p,"abc",3);a.Same(p,pointer,pointer);a.LessOrEqual(p,2,2);a.Contains(p,[]int32{4,9},int32(9))
    bad:=[]func(*coherentAppleT){func(p *coherentAppleT){a.True(p,false)},func(p *coherentAppleT){a.False(p,true)},
      func(p *coherentAppleT){a.Equal(p,1,2)},func(p *coherentAppleT){a.NotEqual(p,1,1)},func(p *coherentAppleT){a.Nil(p,pointer)},func(p *coherentAppleT){a.NotNil(p,(*int)(nil))},
      func(p *coherentAppleT){a.Empty(p,"x")},func(p *coherentAppleT){a.NotEmpty(p,"")},func(p *coherentAppleT){a.Len(p,"x",2)},
      func(p *coherentAppleT){a.Same(p,pointer,new(int))},func(p *coherentAppleT){a.LessOrEqual(p,3,2)},
      func(p *coherentAppleT){a.Contains(p,[]int32{4,9},int32(0))}}
    for _,run:=range bad{expectAbort(t,run)}
}
func TestCleanupRunsOnceInReverseOrder(t *testing.T) {
    p:=&coherentAppleT{}; order:=[]int{}
    p.Cleanup(func(){order=append(order,1)});p.Cleanup(func(){order=append(order,2)})
    p.finish();p.finish();if !reflect.DeepEqual(order,[]int{2,1}){t.Fatal(order)}
    p.Cleanup(func(){panic("private diagnostic")});p.finish();if !p.failed{t.Fatal("cleanup failure was lost")}
}
func TestFailureDiagnosticsExcludeAssertionValues(t *testing.T) {
    p:=&coherentAppleT{}
    func(){defer func(){_ = recover()}();p.Fatalf("private secret %s","secret-seed") }()
    if !p.failed||strings.Contains(p.location,"secret-seed")||p.location==""{t.Fatal("invalid sanitized failure")}
}
'''


if __name__ == "__main__":
    unittest.main()
