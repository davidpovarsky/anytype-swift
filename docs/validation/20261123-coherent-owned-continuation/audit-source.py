#!/usr/bin/env python3
"""Read-only exact source/retention inventory; never import or execute project code."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3] if "__file__" in globals() and Path(__file__).name != "<stdin>" else Path("/mnt/development/projects/worktrees/anytype-wave15-coherent-owned-continuation-20261123")
SOURCE = "3a6f932925a7cadd37490b91eed59c27f58da446"
RETAINED = "75bd6d7af18dfd511e85582ce7f994d2801b7703"
BASE = "a69d0967c1dad4b9476b04af2b681474983e0b96"
DIRECTORY = "docs/validation/20261123-coherent-owned-continuation"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=30)


def content(commit, path):
    return git("show", commit + ":" + path)


def blob(commit, path):
    raw = git("ls-tree", "-z", commit, "--", path).rstrip(b"\0")
    meta, actual = raw.split(b"\t", 1)
    mode, kind, identity = meta.decode().split()
    assert actual.decode() == path and kind == "blob"
    return dict(mode=mode, blob=identity)


def record(path):
    p = ROOT / path
    assert p.is_file() and not p.is_symlink() and p.resolve() == p
    raw = p.read_bytes()
    assert raw == content(SOURCE, path)
    return dict(sha256=sha(raw), bytes=len(raw), **blob(SOURCE, path))


def functions(raw):
    result = {}
    def walk(node, prefix=""):
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[prefix + child.name] = ast.dump(child, include_attributes=False)
            if isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + ".")
    walk(ast.parse(raw))
    return result


def main():
    tracked = git("ls-tree", "-r", "--name-only", SOURCE, "--", "Tools").decode().splitlines()
    registry = {}
    for name in tracked:
        if name.endswith(".py"):
            registry.setdefault(Path(name).stem, []).append(name)
    own = "Tools/PinkhaSimulatorGate/"
    origin = ast.parse((ROOT / own / "coherent_original_products.py").read_bytes())
    required = next(ast.literal_eval(n.value) for n in origin.body
                    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name)
                        and t.id == "CLEANUP_MODULE_NAMES" for t in n.targets))
    pending = [own + "test_coherent_owned_continuation.py", *[own + name + ".py" for name in required]]
    seen, edges, external = set(), [], set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        raw = (ROOT / path).read_bytes()
        for node in ast.walk(ast.parse(raw, filename=path)):
            modules = ([n.name.split(".")[0] for n in node.names] if isinstance(node, ast.Import)
                       else [node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
            for module in modules:
                candidates = registry.get(module, [])
                assert len(candidates) <= 1, (path, module, candidates)
                if candidates:
                    target = candidates[0]
                    edges.append(dict(source=path, line=node.lineno, module=module, target=target))
                    pending.append(target)
                else:
                    external.add(module)
    assert len(seen) == 60
    assert external <= set(sys.stdlib_module_names), sorted(external - set(sys.stdlib_module_names))
    inputs = {name: record(name) for name in sorted(seen)}
    same, changed, added = [], [], []
    retained_paths = set(git("ls-tree", "-r", "--name-only", RETAINED, "--", "Tools").decode().splitlines())
    for name, row in inputs.items():
        if name not in retained_paths:
            added.append(name); row["scope"] = "NEW_CONTROLLER_SCOPE"
        elif content(RETAINED, name) == (ROOT / name).read_bytes():
            same.append(name); row["scope"] = "EXACT_RETAINED_CURRENT_DEPENDENCY"
        else:
            changed.append(name); row["scope"] = "NEW_DECLARED_CALLER_HOOKS"
    assert len(same) == 53 and len(changed) == 4 and len(added) == 3
    expected_changes = {
        own + "coherent_original_products.py": {"ContinuationOrigin.__init__", "ContinuationOrigin.verify_control",
            "ContinuationOrigin.validate_intent", "ContinuationOrigin.nested_cleanup_anchor"},
        own + "wave15_batch.py": {"worker", "run_nested_worker_command", "validate_worker_conclusion"},
        own + "run_wave15_acceptance.py": {"execute"},
        own + "coherent_heart_release.py": {"nested_cleanup"},
    }
    inverses, patch = {}, []
    for name in sorted(changed):
        old, new = content(RETAINED, name), (ROOT / name).read_bytes()
        old_functions, new_functions = functions(old), functions(new)
        changed_functions = {key for key in old_functions.keys() & new_functions.keys()
                             if old_functions[key] != new_functions[key]}
        assert changed_functions == expected_changes[name]
        assert not (old_functions.keys() - new_functions.keys())
        a, b = old.splitlines(keepends=True), new.splitlines(keepends=True)
        operations = list(difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes())
        reverse = list(b)
        hunks = []
        for tag, i1, i2, j1, j2 in reversed(operations):
            if tag == "equal":
                continue
            before, after = b"".join(a[i1:i2]), b"".join(b[j1:j2])
            hunks.append(dict(operation=tag, retained_lines=[i1, i2], candidate_lines=[j1, j2],
                              retained_sha256=sha(before), candidate_sha256=sha(after),
                              retained_bytes=len(before), candidate_bytes=len(after)))
            reverse[j1:j2] = a[i1:i2]
        assert b"".join(reverse) == old
        inverses[name] = dict(retained_sha256=sha(old), candidate_sha256=sha(new),
            exact_whole_file_inverse=True, inverse_hunks=list(reversed(hunks)),
            changed_functions=sorted(changed_functions),
            added_functions=sorted(new_functions.keys() - old_functions.keys()),
            unchanged_function_count=sum(old_functions[k] == new_functions[k]
                for k in old_functions.keys() & new_functions.keys()))
        patch.extend(difflib.unified_diff(old.decode().splitlines(keepends=True),
            new.decode().splitlines(keepends=True), fromfile="retained/" + name, tofile="candidate/" + name))
    assert (ROOT / own / "run_owned_single_lane.py").read_bytes() == content(RETAINED, own + "run_owned_single_lane.py")
    original_kernel = functions(content(BASE, own + "run_owned_single_lane.py"))
    current_kernel = functions((ROOT / own / "run_owned_single_lane.py").read_bytes())
    kernel_names = [name for name in original_kernel if "kernel" in name]
    assert kernel_names and all(original_kernel[n] == current_kernel[n] for n in kernel_names)
    auxiliary = ["Tools/Hanlin/source.json", "Tools/Hanlin/wave15-core-tests.json",
                 "Tools/PinkhaNativeDerived/package_evidence.py"]
    for name in auxiliary:
        inputs[name] = dict(record(name), scope="EXPLICIT_DATA_OR_PACKAGING_SOURCE")
    package = (ROOT / auxiliary[-1]).read_bytes()
    current_package = content(RETAINED, auxiliary[-1])
    line = b"            ('sdk06-ui', 'sdk06-early-products', 'BuildProducts.tar.gz'),\n"
    assert current_package.count(line) == 1 and current_package.replace(line, b"") == package
    assert b"path.suffix in {'.log', '.json', '.png', '.txt'}" in package
    methods = [n.name for n in ast.walk(ast.parse((ROOT / own / "test_coherent_owned_continuation.py").read_bytes()))
               if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert len(methods) == 4
    originals = {}
    directory = Path("/mnt/development/projects/diagnostics/coherent-kernel-actual-result-20261123")
    for name in ["diagnosis.json", "continuation-design.md"]:
        candidates = [p for p in [directory / "diagnosis" / name, directory / name] if p.is_file()]
        assert len(candidates) == 1, (name, candidates)
        p = candidates[0]
        originals[str(p)] = dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
    result = dict(protocol="pinkha-coherent-owned-source-retention-v1", source_commit=SOURCE,
        retained_dependency_commit=RETAINED, original_base=BASE,
        preparation_status="SOURCE_ONLY_CONTROLS_NOT_RUN", product_executions=0, control_executions=0,
        python_sources=len(seen), data_or_packaging_inputs=len(auxiliary), inputs=inputs,
        required_canonical_modules={name: own + name + ".py" for name in required},
        static_edges=sorted(edges, key=lambda v:(v["source"],v["line"],v["module"])),
        external_modules=sorted(external), exact_retained_python_files=same,
        new_python_files=added, changed_existing_python_files=changed,
        exact_inverses=inverses, retained_kernel_functions=kernel_names,
        tests=["CoherentOwnedContinuationTests." + name for name in methods],
        original_failure_sources=originals,
        packaging=dict(candidate_sha256=sha(package), current_retained_sha256=sha(current_package),
            only_unrelated_qualified_delta=line.decode().strip(),
            new_raw_original_paths=["lanes/" + lane + "/construction/" + name
                for lane in ("editor","quote-drop","properties-set")
                for name in ("create.log","post-preparation-container.log")],
            existing_log_json_policy_covers_actual_new_outputs=True,
            policy_modified=False, missing_historical_raw_lookup_files_reconstructed=False))
    print(json.dumps({"review": result, "patch": "".join(patch)}, sort_keys=True))


if __name__ == "__main__":
    main()
