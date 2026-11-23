#!/usr/bin/env python3
"""Static workflow/source audit; no product/controller import or test execution."""
import ast, hashlib, json, pathlib, subprocess
import yaml
ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = pathlib.Path(__file__).resolve().parent
BASE = "cb89f4d1118023fa9c6260ea556c691f8f89f400"
FROZEN = "5a6a05d9152553b1bee661eadc7b539b25b10ae1"
WORKFLOW = ".github/workflows/pinkha-semantic-page-apple-mounted.yml"
CENTRAL = ".github/workflows/torah-inspector-ipados27.yml"
ADMISSION = "Tools/PinkhaSemanticAnchorWire/apple_mounted/admissions/45116855451-1.json"
PLAN = "Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json"
REVIEW = "docs/validation/20261123-semantic-page-mounted-known-pair/source-review.json"
ROUTE = "semantic-page-apple-mounted"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(*args): return subprocess.check_output(["git", "--no-optional-locks", "-C", str(ROOT), *args])
def blob(revision, path): return git("show", revision + ":" + path)
class UniqueLoader(yaml.BaseLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key, value in node.value:
            name = self.construct_object(key, deep=deep)
            assert name not in result, ("duplicate YAML key", name)
            result[name] = self.construct_object(value, deep=deep)
        return result
def parse(raw): return yaml.load(raw, Loader=UniqueLoader)
def product_tree(revision):
    result = {}
    for row in git("ls-tree", "-rz", revision).split(b"\0"):
        if not row: continue
        metadata, name = row.split(b"\t", 1)
        relative = name.decode()
        if relative.startswith(("Tools/", ".github/", "docs/")): continue
        result[relative] = metadata.decode().split()
    return result
assert git("rev-parse", "HEAD").decode().strip() == BASE
old = blob(BASE, WORKFLOW)
current = (ROOT / WORKFLOW).read_bytes()
old_token, new_token = b"45106989988-1.json", b"45116855451-1.json"
assert old.count(old_token) == 1 and new_token not in old
assert current == old.replace(old_token, new_token)
assert current.replace(new_token, old_token) == old
central = blob(BASE, CENTRAL)
assert central == blob(FROZEN, CENTRAL)
if (ROOT / CENTRAL).exists(): assert (ROOT / CENTRAL).read_bytes() == central
mounted, dispatch = parse(current), parse(central)
options = dispatch["on"]["workflow_dispatch"]["inputs"]["route"]["options"]
assert len(options) == len(set(options)) and options.count(ROUTE) == 1
assert dispatch["jobs"][ROUTE] == {
    "if": "${{ inputs.route == 'semantic-page-apple-mounted' }}",
    "uses": "./" + WORKFLOW}
assert sum(item.get("uses") == "./" + WORKFLOW for item in dispatch["jobs"].values()) == 1
assert "default" not in dispatch["on"]["workflow_dispatch"]["inputs"]["route"]
assert options[0] == "full-acceptance"
assert mounted["on"] == {"workflow_dispatch": {}, "workflow_call": {}}
assert mounted["permissions"] == {"contents": "read", "actions": "read"}
job = mounted["jobs"]["original-products-mounted"]
assert job["runs-on"] == "xcode-27" and job["timeout-minutes"] == "120"
assert job["env"]["DEVELOPER_DIR"] == "/Applications/Xcode_27.app/Contents/Developer"
steps = job["steps"]
checkouts = [s for s in steps if s.get("uses") == "actions/checkout@v4"]
assert len(checkouts) == 1
assert checkouts[0]["with"] == {"ref": "${{ github.sha }}",
    "path": "build/page154-mounted-${{ github.run_id }}-${{ github.run_attempt }}/app",
    "fetch-depth": "1", "persist-credentials": "false"}
shells = [s for s in steps if "run" in s]
assert len(shells) == 1 and shells[0]["shell"] == "bash"
body = shells[0]["run"]
assert body.startswith("set -euo pipefail\n")
assert '--admission "$ATTEMPT/app/' + ADMISSION + '"' in body
assert body.count("--admission") == 1 and "45106989988" not in body
assert '--work "$ATTEMPT/work" --evidence "$ATTEMPT/artifact/evidence"' in body
assert 'mkdir -p "$ATTEMPT/artifact"' in body
assert 'mkdir -p "$ATTEMPT/artifact/evidence"' not in body
shell = subprocess.run(["bash", "-n"], input=body.encode(), capture_output=True)
(DOC / "bash.stdout").write_bytes(shell.stdout)
(DOC / "bash.stderr").write_bytes(shell.stderr)
assert shell.returncode == 0, shell.stderr.decode()
upload = [s for s in steps if s.get("uses") == "actions/upload-artifact@v4"]
assert len(upload) == 1 and upload[0]["if"] == "always()"
assert upload[0]["with"] == {
    "name": "Pinkha-Semantic-Page-Mounted-${{ github.run_id }}-${{ github.run_attempt }}",
    "path": "build/page154-mounted-${{ github.run_id }}-${{ github.run_attempt }}/artifact/",
    "retention-days": "14", "if-no-files-found": "error"}
review_raw = (ROOT / REVIEW).read_bytes()
assert review_raw == blob(BASE, REVIEW)
inputs = json.loads(review_raw)["source_sha256"]
assert len(inputs) == 172 and WORKFLOW not in inputs and CENTRAL not in inputs
for relative, expected in inputs.items():
    actual = (ROOT / relative).read_bytes()
    assert sha(actual) == expected and actual == blob(BASE, relative), relative
admission_raw = (ROOT / ADMISSION).read_bytes()
assert admission_raw == blob(BASE, ADMISSION)
assert sha(admission_raw) == "17c37d842009b23d50ab2222383c1f025242aa2e61f1828cf1bc1a346b5ed7e5"
plan_raw = (ROOT / PLAN).read_bytes()
assert plan_raw == blob(BASE, PLAN)
assert sha(plan_raw) == "19806530ea3f492ff221efac5a5430ec46893fb7066bf5294afaa06a390ad42f"
plan = json.loads(plan_raw)
assert len(plan["files"]) == 9
for relative, expected in plan["files"].items():
    assert sha(blob(BASE, relative)) == expected["sha256"]
products = product_tree(BASE)
assert products == product_tree(FROZEN) and len(products) == 6321
controller = (ROOT / "Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py").read_bytes()
assert controller == blob(BASE, "Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py")
node = next(n for n in ast.parse(controller).body if isinstance(n, ast.FunctionDef) and n.name == "product_inputs")
guard = ast.get_source_segment(controller.decode(), node)
assert '("Tools/", ".github/", "docs/")' in guard
for check in ['head == os.environ.get("GITHUB_SHA")',
              'args.admission.relative_to(ROOT).as_posix() in inputs',
              'product_inputs(before) == product_inputs(inputs)']:
    assert check in controller.decode()
retention = (json.dumps(inputs, sort_keys=True, indent=2) + "\n").encode()
(DOC / "retained-qualified-inputs.json").write_bytes(retention)
review = {
 "status": "STATIC_WORKFLOW_SOURCE_AUDIT_PASS", "parent_sha": BASE,
 "frozen_app_origin_sha": FROZEN, "changed_workflow": WORKFLOW,
 "before_sha256": sha(old), "after_sha256": sha(current),
 "exact_inverse": {"before": old_token.decode(), "after": new_token.decode(),
    "occurrences": 1, "whole_file_inverse_equal": True},
 "central": {"path": CENTRAL, "sha256": sha(central), "unchanged_from_frozen_origin": True,
    "route_already_present": True, "route_occurrences": 1, "reusable_call_occurrences": 1,
    "default_and_other_routes_unchanged": True},
 "admission": {"path": ADMISSION, "sha256": sha(admission_raw), "unchanged": True},
 "source_plan": {"path": PLAN, "sha256": sha(plan_raw), "files": 9, "unchanged": True},
 "qualified_inputs": {"count": len(inputs), "ledger_sha256": sha(retention),
    "original_source_review_sha256": sha(review_raw), "all_live_and_git_bytes_unchanged": True},
 "product_inputs": {"count": len(products), "all_git_modes_objects_equal_to_frozen_origin": True,
    "excluded_prefixes": ["Tools/", ".github/", "docs/"]},
 "checkout": "Exact github.sha, committed fixed admission, existing current source equality guards",
 "artifact": {"always_upload": True, "retention_days": 14, "missing_files_error": True},
 "bash_syntax": {"argv": ["bash", "-n"], "stdin_sha256": sha(body.encode()),
    "return_code": shell.returncode, "stdout_sha256": sha(shell.stdout), "stderr_sha256": sha(shell.stderr)},
 "yaml": {"version": yaml.__version__, "duplicate_keys_rejected": True},
 "audit_script_sha256": sha(pathlib.Path(__file__).read_bytes()),
 "control_tests_executed": 0, "old_controls_replayed": 0, "apple_builds": 0,
 "product_tests_executed": 0, "workflow_dispatches": 0,
 "mounted_preparation": "NOT_RUN", "mounted_ui": "NOT_RUN"}
(DOC / "source-review.json").write_text(json.dumps(review, sort_keys=True, indent=2) + "\n")
print(json.dumps({"status": review["status"], "qualified_inputs": len(inputs),
    "product_inputs": len(products), "central_unchanged": True,
    "source_review_sha256": sha((DOC / "source-review.json").read_bytes())}))
