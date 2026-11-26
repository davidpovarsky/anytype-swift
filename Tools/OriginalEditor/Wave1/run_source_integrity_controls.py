#!/usr/bin/env python3
"""Integrity controls against real Git source; never product/runtime acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/OriginalEditor"))
from wave1_source import BASE, FILES, RELATIVE, observe, validate_document

def run(*args, cwd=None):
    return subprocess.check_output(list(args), cwd=cwd, stderr=subprocess.STDOUT, text=True).strip()

def rejects(name, operation, results):
    try:
        operation()
    except (ValueError, subprocess.CalledProcessError):
        results.append({"control": name, "status": "PASS_REJECTED"})
    else:
        raise AssertionError("Unsafe source was admitted: " + name)

def main():
    binding = json.loads((ROOT / "Tools/OriginalEditor/framework_profile.json").read_text())[
        "wave1_product_source_adoption"]
    document = json.loads((ROOT / RELATIVE).read_bytes())
    baseline = observe(ROOT, binding)
    results = [{"control": "exact_real_committed_product", "status": "PASS"}]
    for key, value in (
        ("schema", "unreviewed/9"),
        ("base_source", "0" * 40),
        ("reviewed_source", "0" * 40),
        ("scope", "RUNTIME_ACCEPTED"),
        ("native_acceptance_reused_by_this_document", True),
    ):
        changed = copy.deepcopy(document)
        changed[key] = value
        rejects("document_" + key, lambda changed=changed: validate_document(changed, binding), results)
    for role in ("base_product_trees", "reviewed_product_trees"):
        changed = copy.deepcopy(document)
        changed[role].pop("Modules")
        rejects("omitted_" + role, lambda changed=changed: validate_document(changed, binding), results)
    changed = copy.deepcopy(document)
    changed["files"] = changed["files"][:-1]
    rejects("omitted_changed_file", lambda: validate_document(changed, binding), results)
    changed = dict(binding, sha256="0" * 64)
    rejects("wrong_adoption_digest", lambda: observe(ROOT, changed), results)
    with tempfile.TemporaryDirectory(prefix="anytype-wave1-source-controls-") as temp:
        fixture = Path(temp) / "source"
        run("git", "-c", "gc.auto=0", "clone", "--shared", "--no-checkout", str(ROOT), str(fixture))
        run("git", "sparse-checkout", "init", "--cone", cwd=fixture)
        run("git", "sparse-checkout", "set", "OriginalEditorFramework", "Tools/OriginalEditor", cwd=fixture)
        run("git", "checkout", cwd=fixture)
        observe(fixture, binding)
        source = fixture / FILES[0]
        original = source.read_bytes()
        source.write_bytes(original + b"\n// unreviewed working change\n")
        rejects("uncommitted_product_bytes", lambda: observe(fixture, binding), results)
        source.write_bytes(original)
        unexpected = fixture / "OriginalEditorFramework/Unreviewed.swift"
        unexpected.write_text("struct Unreviewed {}\n")
        rejects("additional_product_source", lambda: observe(fixture, binding), results)
        unexpected.unlink()
        receipt = fixture / RELATIVE
        raw = receipt.read_bytes()
        receipt.write_bytes(raw + b" ")
        changed = dict(binding, sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
        rejects("rewritten_receipt_and_digest", lambda: observe(fixture, changed), results)
        receipt.write_bytes(raw)
        source.write_bytes(original + b"\n// unreviewed committed change\n")
        run("git", "add", "--", FILES[0], cwd=fixture)
        run("git", "-c", "user.name=Source Integrity Test", "-c", "user.email=source-control@example.invalid",
            "-c", "gc.auto=0", "commit", "-m", "Negative source-integrity fixture", cwd=fixture)
        rejects("different_committed_product_tree", lambda: observe(fixture, binding), results)
    print(json.dumps({"schema": "anytype.wave1-source-integrity-controls/1",
                      "status": "PASS", "source_sha": run("git", "-C", str(ROOT), "rev-parse", "HEAD"),
                      "reviewed_product": baseline["reviewed_source"], "base_source": BASE,
                      "controls": results, "native_runtime_executed": False}, indent=2))

if __name__ == "__main__":
    main()
