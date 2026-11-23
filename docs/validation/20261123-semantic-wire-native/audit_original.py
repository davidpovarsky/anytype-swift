#!/usr/bin/env python3
"""Audit original source-bound wire executions without rerunning Go tests."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINALS = HERE / "originals"
TOOL = ROOT / "Tools/PinkhaSemanticAnchorWire"
STAGES = (
    ("pinkha-semantic-wire-controls-h21u4r3w", "wire-controls.jsonl", "8cd8d2b0f7875cec57321d89f186977eb1b8e7e643c1038848d0a98d262a079c", "8e7e910bb298cbd9382057e8e4ee227fdb07b4fc5f51d6c844095c59ddf3b167"),
    ("pinkha-semantic-wire-unicode-49d4cdvz", "unicode-controls.jsonl", "d91c3ef78c213a1cb7d5be00511f3d933bd9452e9fff0ee544b2a3e2a4c882c4", "a706e9ed64ba586997a90dc22c97ab5c8a1af6e03c36a175af8713501fd0b1fc"),
    ("pinkha-semantic-wire-unicode-repair-116iipgg", "unicode-controls.jsonl", "9558625e0a558f5527d0d5dfa9c1097aa44168f3b925bdf091497485194175e0", "9290bf998b8fd784f6ab3aed8cb9b45bd9945ce1d1d1bb697a7bd1a7ad033e0d"),
)
UNICODE = "TestSemanticAnchorWireRejectsUnpairedEscapesWithoutChangingValidUnicode"
REPAIRED = ("high-text", "low-text", "high-high-text", "high-bmp-text", "low-high-text", "truncated-pair", "literal-replacement", "escaped-replacement")
UNCHANGED = ("high-identity", "low-param", "valid-pair", "valid-uppercase-pair", "valid-bmp", "literal-backslash-param")
METHODS = (
    "TestSemanticAnchorWireKeepsExactUTF16AndEveryOrderedNativeMark",
    "TestSemanticAnchorWireRejectsAmbiguousUnknownNullAndUnboundedInput",
    "TestSemanticAnchorWireReplyRequiresWitnessAndKeepsNativeResponseEvents",
)
INVALID = ("duplicate-top", "duplicate-snapshot", "duplicate-mark", "case-alias", "unknown-authority",
    "missing-field", "null-version", "null-string", "null-offset", "null-snapshot", "null-text", "null-marks",
    "fractional-offset", "overflow-offset", "utf16-surrogate-offset", "future-version", "too-many-marks",
    "oversized-wire", "invalid-utf8", "trailing-object")
REPLY = ("wrong-marker", "invalid-digest", "unchanged-digest", "missing-events", "oversized-events")

def need(value, message):
    if not value:
        raise ValueError(message)

def sha(value):
    return hashlib.sha256(value).hexdigest()

def digest(path):
    return sha(path.read_bytes())

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def go_log(path, expected, failures, exit_code):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    need(all(r.get("Package") == "command-line-arguments" for r in rows), "Unexpected package")
    runs = [r["Test"] for r in rows if r["Action"] == "run" and "Test" in r]
    ends = [r for r in rows if r["Action"] in ("pass", "fail", "skip") and "Test" in r]
    need(len(runs) == len(set(runs)) == len(expected) and set(runs) == expected, "Wrong named runs")
    need(len(ends) == len(expected) and {r["Test"] for r in ends} == expected, "Missing/duplicate terminal")
    need(not any(r["Action"] == "skip" for r in ends), "Skipped method")
    need({r["Test"] for r in ends if r["Action"] == "fail"} == failures, "Wrong failure set")
    packages = [r for r in rows if r["Action"] in ("pass", "fail", "skip") and "Test" not in r]
    need(len(packages) == 1 and packages[0]["Action"] == ("pass" if exit_code == 0 else "fail"), "Package result mismatch")
    leaves = sorted(n for n in expected if not any(x.startswith(n + "/") for x in expected))
    return {"named_top_level_methods": sorted(n for n in expected if "/" not in n),
        "leaf_terminals": [{"name": n, "status": "FAIL" if n in failures else "PASS"} for n in leaves],
        "leaf_count": len(leaves), "package_status": packages[0]["Action"].upper(),
        "package_elapsed": packages[0].get("Elapsed"), "log_sha256": digest(path)}

def audit():
    manifest = load(HERE / "ORIGINALS_MANIFEST.json")
    observed = {str(p.relative_to(ORIGINALS)): (p.stat().st_size, digest(p)) for p in ORIGINALS.rglob("*") if p.is_file()}
    expected_files = {r["folder"] + "/" + r["relative"]: (r["bytes"], r["sha256"]) for r in manifest["files"]}
    need(len(expected_files) == 27 and observed == expected_files, "Original transfer mismatch")
    stage_logs = []
    expected = set(METHODS) | {METHODS[1] + "/" + n for n in INVALID} | {METHODS[2] + "/" + n for n in REPLY}
    selections = (expected, {UNICODE} | {UNICODE + "/" + n for n in REPAIRED + UNCHANGED},
        {UNICODE} | {UNICODE + "/" + n for n in REPAIRED})
    failures = (set(), {UNICODE, UNICODE + "/literal-replacement", UNICODE + "/escaped-replacement"}, set())
    for index, (directory, log, receipt_sha, log_sha) in enumerate(STAGES):
        folder = ORIGINALS / directory
        receipt = load(folder / "result.json")
        need(digest(folder / "result.json") == receipt_sha and digest(folder / log) == log_sha == receipt["log_sha256"], "Original receipt/log changed")
        need(receipt["source_stable"] is True and receipt["source_before_sha256"] == receipt["source_after_sha256"], "Unstable original source")
        before = receipt["source_before_sha256"]
        need(all(digest(folder / name) == value for name, value in before.items()), "Original source receipt mismatch")
        need(receipt.get("toolchain", receipt.get("go_version")) == "go version go1.25.6 windows/amd64", "Toolchain changed")
        need(receipt["exit_code"] == (1 if index == 1 else 0), "Original exit changed")
        cmd = receipt["command"]
        need(cmd[:5] == [r"C:\Program Files\Go\bin\go.exe", "test", "-json", "-count=1", "-p=2"], "Unexpected original command")
        need(cmd[6:] == ["contract.go", "wire.go", "wire_test.go"] + ([] if index == 0 else ["wire_unicode_test.go"]), "Unexpected compiled file list")
        need(not receipt.get("native_page_executed", False) and not receipt.get("native_service_executed", False)
            and not receipt.get("native_page_methods_executed", 0) and not receipt.get("apple_execution", False), "Scope unexpectedly native")
        result = go_log(folder / log, selections[index], failures[index], receipt["exit_code"])
        result.update(stage=directory, compiled_inputs=cmd[6:], original_command=cmd, source_sha256=before)
        stage_logs.append(result)
    first, failed, repaired = [ORIGINALS / s[0] for s in STAGES]
    native_rel = "pkg/lib/pinkha/semanticanchor/"
    old_wire = (first / "wire.go").read_text()
    new_wire = (repaired / (native_rel + "wire.go")).read_text()
    need(new_wire == (failed / (native_rel + "wire.go")).read_text(), "Production wire changed in fixture repair")
    start = new_wire.index("// encoding/json substitutes U+FFFD")
    end = new_wire.index("func captureWireObject", start)
    retained_body = (new_wire[:start] + new_wire[end:]).replace(" || !captureWireStrings(raw)", "")
    need(retained_body == old_wire, "Unexpected codec production change outside Unicode preflight")
    need((first / "wire_test.go").read_bytes() == (repaired / (native_rel + "wire_test.go")).read_bytes(), "Old wire controls changed")
    bad_test = (failed / (native_rel + "wire_unicode_test.go")).read_text()
    new_test = (repaired / (native_rel + "wire_unicode_test.go")).read_text()
    old_target = '[]byte(\x60text"\x60), []byte(\x60text'
    text_value = "\u05d0\u05d1\u05d2 \U0001f600 text"
    new_target = '[]byte(\x60"text":"' + text_value + '"\x60), []byte(\x60"text":"' + text_value
    need(bad_test.count(old_target) == 3 and bad_test.replace(old_target, new_target) == new_test, "Unexpected Unicode test repair")
    native_manifest_path = ROOT / "Tools/PinkhaSemanticAnchor/native-source.json"
    native_manifest = load(native_manifest_path)
    need(len(native_manifest["files"]) == 9, "Frozen component inventory changed")
    native = ROOT / "Tools/PinkhaSemanticAnchor/native"
    for name, value in native_manifest["files"].items():
        need(digest(native / name) == value, "Current component file changed: " + name)
        original = subprocess.check_output(["git", "-C", str(ROOT), "show", "e7fd39b763d3d0244996c207552096f169de85ed:Tools/PinkhaSemanticAnchor/native/" + name])
        need(sha(original) == value, "Current component not exact e7 source")
    need(digest(native / (native_rel + "contract.go")) == digest(repaired / "contract.go"), "Current contract differs from compiled contract")
    codec_manifest = load(TOOL / "native-source.json")
    need(len(codec_manifest["files"]) == 3, "Codec inventory changed")
    for name, value in codec_manifest["files"].items():
        need(digest(TOOL / "native" / name) == value == digest(repaired / name), "Integrated codec differs from original")
    need(codec_manifest["required_component_manifest_sha256"] == digest(native_manifest_path), "Wrong fixed component dependency")
    return {"status": "PASS_ORIGINAL_WIRE_SOURCE_AND_NAMED_EXECUTION_AUDIT",
        "original_transferred_file_count": 27, "original_bytes_preserved": True,
        "source_base": "e7fd39b763d3d0244996c207552096f169de85ed",
        "toolchain": "go version go1.25.6 windows/amd64",
        "original_executions": stage_logs,
        "unicode_fixture_repair": {"production_source_unchanged": True, "affected_cases_reexecuted": list(REPAIRED),
            "unaffected_passes_retained": list(UNCHANGED),
            "reason": "The first text-quote token matched the JSON field name. Targeting the complete field/value pair repairs six invalid-escape cases and two valid-U+FFFD cases.",
            "current_product_source_unicode_leaf_passes": 14,
            "old_26_leaves_scope": "Original pre-Unicode-preflight source only; unchanged body verified, not rerun against current codec"},
        "fixed_component_files_preserved": 9, "fixed_lease_sha256": native_manifest["files"]["core/block/editor/torahopsobject/semantic_anchor_lease.go"],
        "dependencies": {"compiled_inputs": "contract.go and codec/test files; standard-library-only Go imports",
            "current_contract_sha256": digest(native / (native_rel + "contract.go")),
            "component_manifest_sha256": digest(native_manifest_path)},
        "source_sha256": codec_manifest["files"],
        "product_tests_executed_by_audit": 0,
        "native_service_compile": "NOT_RUN", "native_page_apply": "NOT_RUN",
        "process_reopen": "NOT_RUN", "http": "NOT_RUN", "apple": "NOT_RUN",
        "mounted_acceptance": "NOT_RUN", "app_capability": "OFF"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write deterministic AUDIT.json after verification")
    args = parser.parse_args()
    value = audit()
    if args.write:
        (HERE / "AUDIT.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: value[k] for k in ("status", "original_transferred_file_count", "fixed_component_files_preserved", "product_tests_executed_by_audit", "app_capability")}, sort_keys=True))
