"""Seal the reviewed property join; never run a compiler, Git, or a host tool.

Run explicitly after root has copied the actual control receipt and refreshed
README/EVIDENCE_INDEX. Missing, pending, or inconsistent evidence fails before
any output is written. Historical input-manifest pending labels are retained;
only the actual execution receipts establish the bounded validation results.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import zipfile
import zlib


BASE = "f25442b59f021ebb8dd5b2ec2a5be1f5f2c6be5e"
FROZEN_PRODUCER = "fc03fcd713e2c449ad97c5d1e604a9433c2a309b"
CB2_PRODUCER = "cb2df9baa201db0ce404ba37eac853424bae6204"
BRANCH = "codex/otzaria-reviewed-followups-waxqv0pw-20261122"
DOCROOT = "docs/hq-integration/completion-20261122/reviewed-followups-waxqv0pw/original-properties"
PATCH_SHA = "90605b0cb2576c87c3102729ef4784733fc4e24989045acd756b3b9d1f6d5a25"
MODAL_SHA = "377ef209aa567db9f95728f54be101726befea96b2e2cc36b28d0ca3a8bb729d"
ARCHIVE_SHA = "1d21d47b8cd407675265c87a82a2c6a32d1dee537b524eed6f10179ed7194514"
PARSE_SHA = "341f136d75c156e367c566531da4a843c7eaac4d75a123f43b85b4dbf7e20c6d"
PARSE_HOST = (r"C:\Users\DAVID\Code\Codex-Agent-HQ\build"
              r"\property-source-90605b0c-waxqv0pw-20261122\PARSE_RESULT.json")
CONTROL_HOST = (r"C:\Users\DAVID\Code\Codex-Agent-HQ\build"
                r"\property-modal-controls-1d21d47b-waxqv0pw-20261122\CONTROL_RUN_RECEIPT.json")
CHANGED_CONTROL_PATHS = frozenset({
    "Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/OriginalEditorPropertyScope.swift",
    "Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift",
})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def integer(value: object, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, label + " is not the exact expected integer")


def relative(value: str) -> str:
    require(isinstance(value, str) and bool(value), "Empty/non-string relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value and
            all(part not in (".", "..") for part in path.parts) and
            "\\" not in value and ":" not in value, "Unsafe relative path: " + value)
    return value


def rows_by_path(rows: list[dict], count: int, label: str, key: str = "path") -> dict[str, dict]:
    require(isinstance(rows, list) and len(rows) == count, label + " has the wrong membership count")
    result = {}
    for row in rows:
        name = relative(row[key])
        require(name not in result, label + " contains a duplicate: " + name)
        result[name] = row
    return result


def entry(path: str, data: bytes) -> dict:
    return {"path": relative(path), "bytes": len(data), "sha256": sha(data),
            "base64": base64.b64encode(data).decode("ascii")}


class Snapshot:
    """Retain the exact bytes used and reject a concurrent input update."""
    def __init__(self) -> None:
        self.inputs: dict[Path, bytes] = {}

    def read(self, root: Path, name: str) -> bytes:
        path = root / relative(name)
        require(path.is_file(), "Required input is missing; no payload produced: " + str(path))
        require(path.resolve().is_relative_to(root.resolve()), "Input escapes its owned directory")
        data = path.read_bytes()
        if path in self.inputs:
            require(self.inputs[path] == data, "Input changed during assembly: " + str(path))
        self.inputs[path] = data
        return data

    def json(self, root: Path, name: str):
        return json.loads(self.read(root, name))

    def verify_unchanged(self) -> None:
        for path, data in self.inputs.items():
            require(path.read_bytes() == data, "Input changed during assembly: " + str(path))


def main() -> None:
    root = Path(__file__).resolve().parent
    controls = root.parent / "original_editor_property_modal_controls_20261122"
    snap = Snapshot()

    # These two are deliberately read first: no directory or placeholder result
    # is created while the real root-owned control execution is pending.
    binding = snap.json(root, "validation/CONTROL_SOURCE_BINDING.json")
    control_bytes = snap.read(root, "validation/CONTROL_RESULT.json")
    actual = json.loads(control_bytes)
    require(binding["status"] == "PASS_ACTUAL_NEW_PROPERTY_CONTROLS", "Control binding is not a pass")
    require(binding["receipt_sha256"] == sha(control_bytes), "Actual control receipt hash differs")
    require(PureWindowsPath(binding["receipt_host_path"]) == PureWindowsPath(CONTROL_HOST),
            "Control binding names a different host receipt")
    require(binding["archive_sha256"] == ARCHIVE_SHA and binding["source_patch_sha256"] == PATCH_SHA,
            "Control binding names different frozen inputs")
    for key, expected in (("executed", 14), ("passed", 14),
                          ("compiler_processes", 1), ("execution_processes", 1)):
        integer(binding[key], expected, "Control binding " + key)
    require(binding["prior_suites_rerun"] is False, "Old suites were rerun")
    require(isinstance(binding["scope"], str) and bool(binding["scope"].strip()), "Missing actual control scope")

    manifest = snap.json(root, "SOURCE_MANIFEST.json")
    require(manifest["base_commit"] == BASE and manifest["compatible_frozen_producer"] == FROZEN_PRODUCER,
            "Source base/producer differs")
    require(manifest["combined_patch"]["sha256"] == PATCH_SHA, "Different combined source patch")
    require(manifest["Apple_typecheck"] == manifest["Native"] == "NOT_RUN", "Unexpected source acceptance claim")
    files = rows_by_path(manifest["files"], 16, "Joined source")
    source = []
    for name, row in files.items():
        before = snap.read(root, "base/" + name)
        after = snap.read(root, "source/" + name)
        require(sha(before) == row["base_sha256"] and blob(before) == row["base_git_blob"],
                "Source preimage differs: " + name)
        require(sha(after) == row["source_sha256"] and blob(after) == row["source_git_blob"] and
                len(after) == row["source_bytes"], "Source candidate differs: " + name)
        source.append(entry(name, after) | {"before_sha256": sha(before), "base_git_blob": blob(before)})
    patch_name = relative(manifest["combined_patch"]["path"])
    patch = snap.read(root, patch_name)
    require(sha(patch) == PATCH_SHA and len(patch) == 69734 == manifest["combined_patch"]["bytes"],
            "Combined patch bytes differ")

    parse_bytes = snap.read(root, "validation/PARSE_RESULT.json")
    syntax = json.loads(parse_bytes)
    parse_binding = snap.json(root, "validation/PARSE_SOURCE_BINDING.json")
    require(len(parse_bytes) == 12533 and sha(parse_bytes) == PARSE_SHA == parse_binding["receipt_sha256"],
            "Actual syntax receipt differs")
    require(syntax["status"] == "PASS_16_COMPLETE_SWIFT_FILES_SYNTAX" and
            parse_binding["status"] == "PASS_EXACT16_INPUTS_AND_RECEIPT", "Syntax receipt is not the reviewed pass")
    require(syntax["source_base"] == BASE and syntax["patch"] == manifest["combined_patch"] and
            syntax["inputs"] == manifest["files"] and parse_binding["patch"] == manifest["combined_patch"],
            "Syntax inputs are not the exact complete joined files")
    integer(syntax["exit_code"], 0, "Syntax exit")
    integer(syntax["compiler_processes"], 1, "Syntax compiler count")
    integer(parse_binding["receipt_bytes"], 12533, "Syntax receipt size")
    integer(parse_binding["source_files"], 16, "Syntax source count")
    require(syntax["prior_suites_rerun"] is False and
            syntax["Apple_typecheck"] == syntax["Native"] == "NOT_RUN", "Syntax scope has changed")

    inputs = snap.json(controls, "INPUTS.json")
    production = snap.json(controls, "PRODUCTION_INPUTS.json")
    handed = snap.json(controls, "GIT_SOURCE_VERIFICATION.json")
    packet = snap.json(controls, "PACKET_RECEIPT.json")
    expected_ids = inputs["expected_control_ids"]
    require(isinstance(expected_ids, list) and len(expected_ids) == len(set(expected_ids)) == 14 and
            all(isinstance(name, str) and name for name in expected_ids), "Control IDs are not exactly14 unique identities")
    integer(inputs["expected_controls"], 14, "Expected control count")
    require(binding["actual_control_ids"] == expected_ids, "Actual control IDs/order differ")
    require(inputs["combined_patch_sha256"] == PATCH_SHA and inputs["modal_patch_sha256"] == MODAL_SHA,
            "Control input source patches differ")
    require(inputs["prior_suites_rerun"] is False, "Control input scope changed")
    input_files = rows_by_path(inputs["files"], 17, "Compiled control inputs", key="name")
    archive_bytes = snap.read(controls, "property-modal-controls.zip")
    require(sha(archive_bytes) == ARCHIVE_SHA == packet["sha256"] and
            len(archive_bytes) == 46699 == packet["bytes"], "Frozen control ZIP differs")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        expected_members = set(input_files) | {"INPUTS.json", "PRODUCTION_INPUTS.json", "PRODUCTION_REGIONS.json", "README.md"}
        require(len(archive.namelist()) == len(expected_members) == 21 and
                set(archive.namelist()) == expected_members, "Control ZIP membership differs or contains duplicates")
        require(archive.testzip() is None, "Control ZIP CRC failed")
        for name in expected_members:
            require(PurePosixPath(relative(name)).name == name, "Control ZIP member is not a direct leaf")
        for name, row in input_files.items():
            data = archive.read(name)
            require(sha(data) == row["sha256"] and len(data) == row["bytes"], "Control ZIP input differs: " + name)
        for name in ("INPUTS.json", "PRODUCTION_INPUTS.json", "PRODUCTION_REGIONS.json", "README.md"):
            require(archive.read(name) == snap.read(controls, name), "ZIP/local metadata differ: " + name)
    require(sha(snap.read(controls, "PRODUCTION_INPUTS.json")) == inputs["production_inputs_sha256"] and
            sha(snap.read(controls, "PRODUCTION_REGIONS.json")) == inputs["production_regions_sha256"],
            "Canonical/region manifests differ")

    require(actual["status"] == "PASS_NEW_PORTABLE_PROPERTY_MODAL_CONTROLS", "Raw controls did not pass")
    require(actual["archive_sha256"] == ARCHIVE_SHA and actual["combined_patch_sha256"] == PATCH_SHA and
            actual["modal_patch_sha256"] == MODAL_SHA and
            actual["input_manifest_sha256"] == sha(snap.read(controls, "INPUTS.json")), "Raw controls ran different inputs")
    require(actual["passed"] == expected_ids, "Raw receipt does not retain the exact ordered passing IDs")
    for key, expected in (("executed", 14), ("failed", 0), ("skipped", 0), ("compiler_processes", 1),
                          ("execution_processes", 1), ("dependency_builds", 0), ("unchanged_compiled_inputs", 17)):
        integer(actual[key], expected, "Actual control " + key)
    require(actual["prior_suites_rerun"] is False and
            actual["apple_typecheck"] == actual["native_editor"] == "NOT_RUN", "Actual control scope differs")
    for label in ("compile", "run"):
        require(actual[label]["timed_out"] is False, "Actual " + label + " timed out")
        integer(actual[label]["returncode"], 0, "Actual " + label + " exit")

    identities = snap.json(root, "review/CONTROL_PRODUCTION_IDENTITY.json")
    require(identities["status"] == "PASS_ACTUAL_F254_AND_LOCAL_CANONICAL_PRODUCTION_INPUTS" and
            identities["source_base"] == BASE, "Actual F254 canonical input proof is missing")
    require(production["base"] == FROZEN_PRODUCER and handed["neutral_base_to_verify"] == BASE and
            handed["combined_patch_sha256"] == PATCH_SHA, "Canonical mapping references differ")
    canonical = rows_by_path(production["sources"], 13, "Canonical production inputs")
    hand_map = rows_by_path(handed["sources"], 13, "Handed canonical mapping")
    actual_map = rows_by_path(identities["files"], 13, "Actual F254 mapping")
    require(set(canonical) == set(hand_map) == set(actual_map), "Canonical mapping membership differs")
    require(set(canonical) & set(files) == CHANGED_CONTROL_PATHS, "Changed canonical input boundary differs")
    unchanged = []
    for name, row in canonical.items():
        data = snap.read(controls, "production/" + name)
        require(sha(data) == row["sha256"] and blob(data) == row["git_blob"] and len(data) == row["bytes"],
                "Complete canonical source differs: " + name)
        proof, mapping = actual_map[name], hand_map[name]
        require(all(proof[k] == mapping[k] == row[k] for k in ("path", "git_blob", "sha256", "bytes")),
                "Canonical proof differs: " + name)
        base_blob = files[name]["base_git_blob"] if name in CHANGED_CONTROL_PATHS else row["git_blob"]
        require(proof["f254_blob"] == proof["expected_f254_blob"] ==
                mapping["verify_at_neutral_base_git_blob"] == base_blob, "Actual F254 blob differs: " + name)
        if name in CHANGED_CONTROL_PATHS:
            require(proof["included_in_changed_source"] is True and data == snap.read(root, "source/" + name),
                    "Changed canonical source is not the full joined candidate: " + name)
        else:
            require(proof["included_in_changed_source"] is False and
                    mapping["verify_at_neutral_base_sha256"] == row["sha256"], "Unchanged canonical source differs")
            unchanged.append(dict(row) | {"base_git_blob": base_blob})
    require(len(unchanged) == 11, "Expected exactly11 unchanged production inputs")

    workflow = snap.json(root, "review/PUSH_WORKFLOW_AUDIT.json")
    actual_workflows = snap.json(root, "review/ACTUAL_F254_WORKFLOW_BLOBS.json")
    require(workflow["base"] == BASE and workflow["branch"] == BRANCH and
            workflow["status"] == "NO_EXISTING_PUSH_WORKFLOW_MATCHES_THIS_NEUTRAL_BRANCH", "Workflow audit scope differs")
    integer(workflow["matching_count"], 0, "Matching workflows")
    integer(workflow["new_ci_runs_requested"], 0, "Requested CI runs")
    integer(workflow["workflow_count"], 49, "Workflow count")
    wf = rows_by_path(workflow["workflows"], 49, "Audited workflows")
    wf_actual = rows_by_path(actual_workflows, 49, "Actual workflows")
    require({p: x["git_blob"] for p, x in wf.items()} == {p: x["git_blob"] for p, x in wf_actual.items()},
            "Actual49 workflow blobs differ")
    require(all(row["matches_publishing_branch"] is False for row in wf.values()), "A workflow matches the neutral branch")
    review = snap.json(root, "review/ROOT_SOURCE_REVIEW.json")
    require(review["base"] == BASE and review["combined_patch_sha256"] == PATCH_SHA and
            review["status"] == "ROOT_SOURCE_REVIEW_GO_WITH_BOUNDED_ACCEPTANCE_GATES_OPEN" and
            review["Native"] == "NOT_RUN", "Root source review differs")
    cb2 = snap.json(root, "review/CB2_PRODUCER_PREIMAGE_IDENTITY.json")
    require(cb2["producer"] == CB2_PRODUCER and cb2["source_base"] == BASE and
            cb2["status"] == "PASS_ALL_16_PREIMAGES_EXACT_IN_ACTUAL_CB2_PRODUCER", "CB2 preimage proof differs")
    cb2_map = rows_by_path(cb2["files"], 16, "CB2 preimages")
    require(set(cb2_map) == set(files) and all(cb2_map[p]["actual"] == cb2_map[p]["expected"] ==
            files[p]["base_git_blob"] for p in files), "CB2 preimage identities differ")

    index = snap.json(root, "EVIDENCE_INDEX.json")
    require(index["base_commit"] == BASE and index["combined_patch"]["sha256"] == PATCH_SHA,
            "Evidence index refers to different source")
    current_controls = index["validation"]["new_behavioral_controls"]
    require(current_controls and "PENDING" not in json.dumps(current_controls).upper(),
            "Root must refresh EVIDENCE_INDEX after actual controls before sealing")
    evidence: dict[str, dict] = {}
    content_locations: dict[str, str] = {}
    aliases = []

    def include(name: str, data: bytes, *, deduplicate: bool = False) -> None:
        destination = DOCROOT + "/" + relative(name)
        require(name not in ("SOURCE_PUBLICATION.json", ".gitattributes"), "Publisher-owned evidence path")
        if destination in evidence:
            require(evidence[destination]["sha256"] == sha(data), "Conflicting evidence destination: " + name)
            return
        if deduplicate and sha(data) in content_locations:
            aliases.append({"requested_path": destination, "retained_path": content_locations[sha(data)], "sha256": sha(data)})
            return
        evidence[destination] = entry(destination, data)
        content_locations.setdefault(sha(data), destination)

    indexed = rows_by_path(index["entries"], index["indexed_files"], "Evidence index")
    total = 0
    for name, row in indexed.items():
        require(name != "EVIDENCE_INDEX.json", "Evidence index cannot hash itself")
        data = snap.read(root, name)
        require(sha(data) == row["sha256"] and len(data) == row["bytes"], "Indexed evidence changed: " + name)
        include(name, data)
        total += len(data)
    require(total == index["indexed_bytes"] and "README.md" in indexed, "Evidence inventory size/README differs")
    # The existing collision-free evidence hierarchy is preserved exactly. Large
    # encoded staging payloads and expanded ZIP members are never repackaged.
    actual_evidence = {p.relative_to(root).as_posix() for p in (root / "evidence").rglob("*") if p.is_file()}
    require(actual_evidence <= set(indexed), "Current evidence contains files missing from the refreshed index")
    include("EVIDENCE_INDEX.json", snap.read(root, "EVIDENCE_INDEX.json"))
    for name in ("SOURCE_MANIFEST.json", patch_name, "build_join.py", "build_publication.py", "publish_source.py",
                 "validation/PARSE_RESULT.json", "validation/PARSE_SOURCE_BINDING.json", "validation/PARSE_JOB_NOTIFICATION.json",
                 "validation/CONTROL_RESULT.json", "validation/CONTROL_SOURCE_BINDING.json", "validation/run_parse.py"):
        include(name, snap.read(root, name), deduplicate=True)
    for path in sorted((root / "review").rglob("*")):
        if path.is_file():
            name = path.relative_to(root).as_posix()
            include(name, snap.read(root, name), deduplicate=True)
    for path in sorted((root / "validation").iterdir()):
        if (path.is_file() and "PAYLOAD" not in path.name.upper() and
                path.suffix in (".json", ".log", ".py", ".txt", ".zip")):
            name = path.relative_to(root).as_posix()
            include(name, snap.read(root, name), deduplicate=True)
    control_names = ["README.md", "build_controls.py", "INPUTS.json", "PRODUCTION_INPUTS.json", "PRODUCTION_REGIONS.json",
                     "EXTRACTED_INPUTS.json", "GIT_SOURCE_VERIFICATION.json", "PACKET_RECEIPT.json",
                     "property-modal-controls.zip", "run_portable_controls.py", "run_portable_controls_original.py"]
    control_names += [p.relative_to(controls).as_posix() for p in sorted((controls / "review").rglob("*")) if p.is_file()]
    runner_review = snap.json(controls, "review/ROOT_RUNNER_REVIEW.json")
    require(sha(snap.read(controls, "run_portable_controls.py")) == runner_review["executed_runner_sha256"] and
            sha(snap.read(controls, "run_portable_controls_original.py")) == runner_review["original_runner_sha256"] and
            runner_review["production_or_control_zip_changed"] is False, "Reviewed actual runner differs")
    require(sha(snap.read(controls, "build_controls.py")) == packet["build_controls_sha256"], "Control packet builder differs")
    for name in control_names:
        include("new-controls/" + name, snap.read(controls, name), deduplicate=True)

    payload = {
        "parent": BASE, "branch": BRANCH, "docroot": DOCROOT,
        "source": source, "patch": entry(patch_name, patch),
        "unchanged_control_sources": unchanged, "workflow_audit": workflow,
        "control_summary": {key: binding[key] for key in ("executed", "passed", "prior_suites_rerun", "scope")},
        "validation_receipts": [{"host_path": PARSE_HOST, "sha256": PARSE_SHA},
                                {"host_path": binding["receipt_host_path"], "sha256": sha(control_bytes)}],
        "evidence": list(evidence.values()), "evidence_aliases": aliases,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    packed = base64.b64encode(zlib.compress(raw, 9))
    metadata = {"status": "READY_FOR_ROOT_NEUTRAL_PUBLICATION_NOT_PUBLISHED", "parent": BASE, "branch": BRANCH,
                "source_files": 16, "source_patch_sha256": PATCH_SHA, "unchanged_control_sources": 11,
                "controls_executed": 14, "controls_passed": 14, "prior_suites_rerun": False,
                "syntax_files": 16, "Apple_typecheck": "NOT_RUN", "Native": "NOT_RUN",
                "workflow_files": 49, "matching_push_workflows": 0,
                "evidence_files": len(evidence), "evidence_bytes": sum(row["bytes"] for row in evidence.values()),
                "payload_bytes": len(raw), "payload_sha256": sha(raw),
                "packed_bytes": len(packed), "packed_sha256": sha(packed),
                "builder_sha256": sha(snap.read(root, "build_publication.py"))}
    snap.verify_unchanged()
    output = root / "publication"
    outputs = {"PAYLOAD.json": raw, "PAYLOAD.zlib.b64": packed,
               "PAYLOAD_METADATA.json": (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}
    for name, data in outputs.items():
        path = output / name
        require(not path.exists() or path.read_bytes() == data, "Preserve an earlier packet; output already differs: " + str(path))
    output.mkdir(exist_ok=True)
    for name, data in outputs.items():
        path = output / name
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(data)
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    main()
