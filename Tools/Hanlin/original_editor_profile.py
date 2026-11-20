"""Exact original-editor component profile; no UI or live-account acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

BRANCH = "codex/otzaria-original-editor-owned43-apple-reviewed-20261120"
MANIFEST_PATH = Path(__file__).with_name("original_editor_profile.json")


def require(value, message):
    if not value:
        raise ValueError(message)


def manifest():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    require(data["profile"] == "original-editor" and data["required_methods"] == 43,
            "Unreviewed original editor profile")
    names = [suite + "/" + method for suite, item in data["suites"].items()
             for method in item["methods"]]
    require(len(names) == len(set(names)) == 43, "Original editor method inventory differs")
    return data


def suite_counts():
    return {name: len(item["methods"]) for name, item in manifest()["suites"].items()}


def require_identity(head, expected_sha, branch, expected_branch, run_id, attempt):
    require(expected_branch == BRANCH and branch == BRANCH,
            "Wrong original editor consumer branch")
    require(re.fullmatch(r"[0-9a-f]{40}", expected_sha or "") and head == expected_sha,
            "Original editor source differs from actual workflow checkout")
    require(re.fullmatch(r"[1-9][0-9]*", run_id or "") and
            re.fullmatch(r"[1-9][0-9]*", attempt or ""),
            "Missing actual original editor run/attempt")


def git(app, *args):
    return subprocess.check_output(["git", "-C", str(app), *args]).decode("utf-8").strip()


def validate_declarations(text, suite, expected):
    require(re.search(r"\bstruct\s+" + re.escape(suite) + r"\s*\{", text),
            "Original editor suite is missing")
    declarations = re.findall(r"@Test(?:\(([^)]*)\))?\s+func\s+(\w+)\s*\(([^)]*)\)", text)
    require(len(declarations) == text.count("@Test") == len(expected),
            "Original editor declaration count changed")
    require({name for _, name, _ in declarations} == set(expected) and
            len({name for _, name, _ in declarations}) == len(declarations),
            "Original editor declaration names changed")
    require(all(not attributes.strip() and not arguments.strip()
                for attributes, _, arguments in declarations),
            "Unreviewed original editor parameterization")
    return {suite + "/" + name for _, name, _ in declarations}


def expected_methods(app):
    data = manifest()
    for path, expected in data["application_trees"].items():
        require(git(app, "rev-parse", "HEAD:" + path) == expected,
                "Original editor application source tree changed: " + path)
    tracked = git(app, "ls-files", "-z").split("\0")
    methods, files = set(), {}
    for suite, item in data["suites"].items():
        path = item["path"]
        candidates = [p for p in tracked if p.casefold() == path.casefold()]
        require(candidates == [path], "Missing or case-colliding original editor source: " + path)
        actual = app / path
        require(actual.is_file() and not actual.is_symlink(), "Missing original synchronized suite")
        raw = actual.read_bytes()
        # Git stores LF; Windows controls may materialize CRLF. This is only
        # line-ending normalization, not rewriting production/test source.
        canonical = raw.replace(b"\r\n", b"\n")
        require(hashlib.sha256(canonical).hexdigest() == item["sha256"],
                "Original editor test bytes differ from reviewed source: " + path)
        require(hashlib.sha256(subprocess.check_output(
            ["git", "-C", str(app), "show", "HEAD:" + path])).hexdigest() == item["sha256"],
            "Original editor Git test blob differs: " + path)
        methods.update(validate_declarations(canonical.decode("utf-8"), suite, item["methods"]))
        files[path] = hashlib.sha256(raw).hexdigest()
    require(len(methods) == 43, "Expected exactly forty-three reviewed original editor methods")
    return methods, files


def validate_execution(tree, expected):
    nodes = []
    def visit(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(tree)
    require(len(nodes) == len(expected) == 43, "Missing or extra original editor execution")
    seen = set()
    for node in nodes:
        identifier = node.get("nodeIdentifier")
        matches = [name for name in expected if identifier in {name + "()", "AnytypeTests/" + name + "()"}]
        require(len(matches) == 1 and matches[0] not in seen and node.get("result") == "Passed",
                "Unrecognized, repeated, missing or nonpassing original editor method")
        seen.add(matches[0])
        def descend(value):
            require(isinstance(value, dict) and value.get("nodeType") in {"Repetition", "Test Case Run"}
                    and value.get("result") == "Passed",
                    "Unreviewed or nonpassing original editor execution descendant")
            children = value.get("children", [])
            require(isinstance(children, list), "Malformed original editor execution children")
            for child in children:
                descend(child)
        children = node.get("children", [])
        require(isinstance(children, list), "Malformed original editor method children")
        for child in children:
            descend(child)
    require(seen == expected, "Missing original editor method")
    return {"actual_method_count": 43, "declared_case_count": 43,
            "scope": "Original document, text/event ownership, lifetime and block/table-service components; original UI editing not exercised"}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--expected-app-branch", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    app = args.app.resolve()
    require_identity(git(app, "rev-parse", "HEAD"), os.environ.get("GITHUB_SHA"),
                     git(app, "branch", "--show-current"), args.expected_app_branch,
                     os.environ.get("GITHUB_RUN_ID"), os.environ.get("GITHUB_RUN_ATTEMPT"))
    require(not git(app, "diff", "--name-only", "HEAD"), "Tracked source changed before original editor gate")
    methods, sources = expected_methods(app)
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "SOURCE_SELECTION_PASS_APPLE_NOT_RUN", "source_sha": os.environ["GITHUB_SHA"],
               "methods": sorted(methods), "test_source_sha256": sources, "profile_manifest_sha256":
               hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(), "ui_executed": 0}
    (args.evidence / "original-editor-selection.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
