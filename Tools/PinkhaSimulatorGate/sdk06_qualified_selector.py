"""Admit one actual successful SDK06 selector probe, then bind current execution.

This admits selector grammar only. The original 7293 Products are never current
App evidence. The current consumer must enumerate its own new Debug Products,
then pass the unchanged 23-method/32-case result validator.
"""
from dataclasses import dataclass, field
import ast
import io
import subprocess
import hashlib
import json
from pathlib import Path
import plistlib
import re

import sdk06_enumeration_probe as probe
import shared_editor_existing_build as component

PROTOCOL = "sdk06-qualified-selector-admission-v1"
PROBE_PROTOCOL = "sdk06-original-products-enumeration-only-v1"
MAX_ARTIFACT_BYTES = 256 * 1024**2
require = probe.require
_PLAN_SEAL = object()

BASENAME_VARIANT = "suites-minus-seven-three-parameter-basenames-cli"
BASENAME_ENTRY = "Tools/PinkhaSimulatorGate/sdk06_basename_enumeration_probe.py"
BASENAME_PLAN = "Tools/PinkhaSimulatorGate/sdk06-basename-probe-plan.json"
BASENAME_PROOF_ROOT = "docs/validation/20261123-sdk06-basename-probe/original-45116213338"
BASENAME_EXTRA_INPUTS = (
    BASENAME_ENTRY, BASENAME_PLAN,
    ".github/workflows/pinkha-sdk06-basename-probe.yml",
    ".github/workflows/torah-inspector-ipados27.yml",
    BASENAME_PROOF_ROOT + "/receipt.json",
    BASENAME_PROOF_ROOT + "/suites-minus-seven-cli.enumeration.json",
    BASENAME_PROOF_ROOT + "/enumerate-suites-minus-seven-cli.command.json",
    BASENAME_PROOF_ROOT + "/original.xctestrun",
    BASENAME_PROOF_ROOT + "/suites-minus-seven-cli.xctestrun",
)
BASENAME_CURRENT_INPUTS = (BASENAME_ENTRY, BASENAME_PLAN) + BASENAME_EXTRA_INPUTS[4:]
BASENAME_FIXED_HASHES = {
    "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py":
        "ce2987846cdd42ebab7702e7dff51068bfb15ee48a66011f621695dbd72ebbce",
    BASENAME_ENTRY: "bf48d27955b94abc8bb3a93559ba608f94c818c7beeab1138b2e85b8911706cc",
    BASENAME_PLAN: "9f812368d7b091e88e1346c16a81f8e993eb3f15c9b852379dd62aacc7532f22",
}


def _basename_source_scope(sources):
    require(set(BASENAME_EXTRA_INPUTS) <= set(sources),
            "All nine exact basename integrity inputs are required")
    require(all(sources.get(path) == checksum for path, checksum in BASENAME_FIXED_HASHES.items()),
            "The exact reviewed basename provider/plan/original probe must be pinned")


def _basename_provider(control=None):
    # Check bytes before importing this separate provider. No caller-supplied
    # path, module, plan or import override is accepted.
    root = Path(__file__).resolve().parents[2]
    require(control is None or Path(control).resolve() == root,
            "The basename provider must belong to the current owned controller")
    for relative, checksum in BASENAME_FIXED_HASHES.items():
        path = root / relative
        require(path.is_file() and not path.is_symlink() and probe.sha(path) == checksum,
                "Current fixed basename provider/plan/original probe bytes differ")
    import importlib
    fixed = importlib.import_module("sdk06_basename_enumeration_probe")
    require(Path(fixed.__file__).resolve() == root / BASENAME_ENTRY
            and fixed.VARIANT_NAME == BASENAME_VARIANT
            and fixed.EXTRA_INTEGRITY_PATHS == BASENAME_EXTRA_INPUTS,
            "Unexpected basename provider identity or extra source scope")
    fixed._fixed_inputs()
    return fixed


def _candidate_variants(approved, selection):
    if approved.get("qualified_variant") == BASENAME_VARIANT:
        candidates = _basename_provider().fixed_candidates(selection)
        require(len(candidates) == 1 and candidates[0].get("name") == BASENAME_VARIANT,
                "Exactly the fixed basename request must match the actual probe")
        return candidates
    return probe.variants(selection)



def source_functions(data, names):
    value = ast.parse(data.decode("utf-8"))
    found = {node.name: ast.dump(node, include_attributes=False) for node in value.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names}
    require(set(found) == set(names), "Exact selector dependency functions missing")
    return found


def original_control_sources(app, approved):
    """Match actual original dependency bytes to Git, plus unchanged selector semantics."""
    sources = approved["probe_control_sources"]
    require(len(sources) <= 120, "Unbounded original probe source closure")
    names = sorted(sources)
    request = "".join(approved["probe_source_sha"] + ":" + name + "\n" for name in names).encode()
    result = subprocess.run(["git", "-C", str(app), "cat-file", "--batch"], input=request,
                            capture_output=True, timeout=45, check=True)
    stream = io.BytesIO(result.stdout); originals = {}
    for name in names:
        header = stream.readline().decode("ascii").strip().split()
        require(len(header) == 3 and header[1] == "blob" and header[2].isdigit(),
                "Original probe source is not an exact Git blob")
        size = int(header[2]); require(0 < size <= 4 * 1024**2, "Unbounded original source blob")
        data = stream.read(size)
        require(len(data) == size and stream.read(1) == b"\n" and digest_bytes(data) == sources[name],
                "Original tested probe dependency differs from its exact source commit")
        originals[name] = data
    require(stream.read() == b"", "Unexpected original source batch output")
    probe_name = "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py"
    require((app / probe_name).read_bytes() == originals[probe_name],
            "Current selector grammar must retain the actual qualified probe controller")
    component_name = "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"
    require(component_name in originals, "Original component dependency is absent")
    names = {"source_contract", "enumerated_identifiers", "scoped_configuration", "validate_results"}
    require(source_functions((app / component_name).read_bytes(), names) ==
            source_functions(originals[component_name], names),
            "Current declaration/enumeration/result validators differ from the qualified originals")
    grammar = {probe_name: probe.sha(app / probe_name), component_name: probe.sha(app / component_name)}
    if approved.get("qualified_variant") == BASENAME_VARIANT:
        _basename_source_scope(sources)
        _basename_provider(app)
        # Both invoking workflow blobs are bound above to the actual probe Git
        # source. They are not executing code in this later current-App route.
        for name in BASENAME_CURRENT_INPUTS:
            require(name in originals and (app / name).read_bytes() == originals[name],
                    "Current fixed basename provider/plan/proof differs from the qualified original")
            grammar[name] = probe.sha(app / name)
    return grammar


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def exact_keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), "Unexpected selector admission fields")


def sha_value(value):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value), "Invalid SHA256")


def positive(value):
    require(isinstance(value, str) and re.fullmatch("[1-9][0-9]*", value), "Invalid run identity")


def read(path, maximum=4 * 1024**2):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= maximum,
            "Missing or unbounded original selector evidence")
    def unique(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "Duplicate selector evidence JSON key")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def admission(value):
    exact_keys(value, {"protocol", "probe_run_id", "probe_run_attempt", "probe_source_sha",
        "artifact_id", "artifact_name", "artifact_sha256", "artifact_bytes",
        "qualified_variant", "probe_control_sources", "files"})
    require(value["protocol"] == PROTOCOL, "Wrong selector admission protocol")
    for name in ("probe_run_id", "probe_run_attempt"): positive(value[name])
    require(isinstance(value["probe_source_sha"], str)
            and re.fullmatch("[0-9a-f]{40}", value["probe_source_sha"]), "Invalid actual probe source")
    require(type(value["artifact_id"]) is int and value["artifact_id"] > 0
            and type(value["artifact_bytes"]) is int
            and 0 < value["artifact_bytes"] <= MAX_ARTIFACT_BYTES, "Unbounded probe artifact")
    sha_value(value["artifact_sha256"])
    require(value["artifact_name"] == "Pinkha-SDK06-Enumeration-" + value["probe_run_id"] + "-" +
            value["probe_run_attempt"], "Probe artifact name differs")
    name = value["qualified_variant"]
    if name != BASENAME_VARIANT:
        require(name in {"suites-minus-seven-cli", "parameter-signature-terminal-parens-cli"},
                "Only an actually qualified reviewed probe variant is supported")
    expected = {"receipt.json", "original.xctestrun", "originals/execution.json",
        "originals/shared-editor-components/compiled-suite-enumeration.json",
        name + ".enumeration.json", name + ".xctestrun",
        "enumerate-" + name + ".command.json", "enumerate-" + name + ".log"}
    exact_keys(value["files"], expected)
    for checksum in value["files"].values(): sha_value(checksum)
    require(value["files"]["original.xctestrun"] == probe.XCTESTRUN_SHA
            and value["files"]["originals/execution.json"] == probe.EXECUTION_SHA,
            "Original exact SDK descriptor/execution identity differs")
    sources = value["probe_control_sources"]
    require(isinstance(sources, dict) and len(sources) >= 5
            and "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py" in sources,
            "Original loaded probe source closure missing")
    if name == BASENAME_VARIANT:
        _basename_source_scope(sources)
    for path, checksum in sources.items():
        if name == BASENAME_VARIANT and path in BASENAME_EXTRA_INPUTS:
            sha_value(checksum)
            continue
        require(isinstance(path, str) and path.startswith("Tools/") and path.endswith(".py")
                and "\\" not in path and all(p not in {"", ".", ".."} for p in path.split("/")),
                "Unsafe probe dependency path")
        sha_value(checksum)
    return value


def original_api(run, artifact, approved):
    admission(approved)
    require(run.get("id") == int(approved["probe_run_id"])
            and run.get("run_attempt") == int(approved["probe_run_attempt"])
            and run.get("head_sha") == approved["probe_source_sha"]
            and run.get("event") == "workflow_dispatch" and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            and run.get("repository", {}).get("full_name") == probe.REPOSITORY
            and run.get("path") == ".github/workflows/torah-inspector-ipados27.yml",
            "A successful actual reviewed probe attempt is required")
    require(artifact.get("id") == approved["artifact_id"] and artifact.get("name") == approved["artifact_name"]
            and artifact.get("digest") == "sha256:" + approved["artifact_sha256"]
            and artifact.get("size_in_bytes") == approved["artifact_bytes"]
            and artifact.get("expired") is False
            and artifact.get("workflow_run", {}).get("id") == int(approved["probe_run_id"])
            and artifact.get("workflow_run", {}).get("head_sha") == approved["probe_source_sha"],
            "Qualified probe artifact API identity differs")


def selection_from_source(source):
    require(source.get("source_hashes") == probe.SOURCES
            and source.get("expected_methods") == 23 and source.get("declared_invocations") == 32,
            "Current consumer test declaration source differs from the original probe")
    declarations = source.get("compiled_declarations", {})
    require(isinstance(declarations, dict) and len(declarations) == 30, "Exactly30 declarations required")
    selected = sorted(declarations[name] for name in source.get("methods", []))
    excluded = sorted(declarations[name] for name in source.get("unselected_existing_methods", []))
    require(len(set(selected)) == len(selected) == 23 and len(set(excluded)) == len(excluded) == 7
            and not set(selected).intersection(excluded)
            and sorted(selected + excluded) == sorted(declarations.values())
            and sum(not name.endswith("()") for name in excluded) == 3, "Exact23+7 identities differ")
    return dict(test_plan="AnytypeTests", selected=selected, excluded=excluded,
                declarations=sorted(declarations.values()))


def qualified_record(receipt, approved, selection):
    require(receipt.get("protocol") == PROBE_PROTOCOL and receipt.get("status") == probe.PROBE_PASS
            and receipt.get("control_source_sha") == approved["probe_source_sha"]
            and receipt.get("run_id") == approved["probe_run_id"]
            and receipt.get("run_attempt") == approved["probe_run_attempt"]
            and receipt.get("control_source_hashes") == approved["probe_control_sources"],
            "Qualified original probe source/run/attempt differs")
    require(receipt.get("original_source_sha") == probe.ORIGINAL_SOURCE
            and receipt.get("original_run_id") == probe.ORIGINAL_RUN
            and receipt.get("original_run_attempt") == probe.ORIGINAL_ATTEMPT
            and receipt.get("original_artifact_id") == probe.ARTIFACT_ID
            and receipt.get("original_artifact_sha256") == probe.OUTER_SHA
            and receipt.get("original_products_sha256") == probe.PRODUCTS_SHA,
            "Probe does not bind the exact original7293 SDK Products")
    require(all(type(receipt.get(k)) is int and receipt[k] == 0 for k in
                ("app_builds", "actual_product_tests_executed"))
            and all(receipt.get(k) is False for k in ("sdk06_accepted", "release_accepted", "full_matrix_accepted")),
            "Selector evidence cannot be relabelled as product acceptance")
    require(receipt.get("control_sources_unchanged") is True and receipt.get("original_products_unchanged") is True
            and receipt.get("finished_at") and not receipt.get("cancelled")
            and not receipt.get("final_integrity_failure"), "Final probe integrity was not qualified")
    cleanup = receipt.get("owned_simulator_cleanup", {})
    require(set(cleanup) == {"shutdown", "delete"}
            and all(row.get("status") == "PASS" and type(row.get("return_code")) is int
                    and row["return_code"] == 0 for row in cleanup.values()), "Probe owned cleanup did not pass")
    require(receipt.get("restored_products") == {
        "entries": 5007, "status": "ORIGINAL_BYTES_RESTORED_ENUMERATION_ONLY"},
        "Original exact Products restoration is missing")
    require(receipt.get("selection_contract") == selection, "Original23+7 selection contract differs")
    variants = _candidate_variants(approved, selection)
    records = receipt.get("probes")
    require(isinstance(records, list) and 1 <= len(records) <= len(variants)
            and [row.get("name") for row in records] == [row["name"] for row in variants[:len(records)]],
            "Actual bounded probe order differs")
    name = approved["qualified_variant"]
    require(receipt.get("qualified_variant") == name and records[-1].get("name") == name
            and records[-1].get("status") == probe.PROBE_PASS
            and sum(row.get("status") == probe.PROBE_PASS for row in records) == 1,
            "Exactly one actual final qualified variant is required")
    record = records[-1]
    require(record.get("command_return_code") == 0
            and type(record.get("actual_product_tests_executed")) is int
            and record["actual_product_tests_executed"] == 0
            and record.get("enumeration_sha256") == approved["files"][name + ".enumeration.json"],
            "Original successful enumeration output is unbound")
    return record, variants[len(records)-1]


def validate_original_copy(original, copied, record, variant):
    before = original.read_bytes()
    require(digest_bytes(before) == probe.XCTESTRUN_SHA
            and probe.sha(copied) == record["binding"].get("copied_sha256")
            and record["binding"].get("original_sha256") == probe.XCTESTRUN_SHA,
            "Original/candidate descriptor hashes differ")
    old = plistlib.loads(before); new = plistlib.loads(copied.read_bytes())
    require(old.get("__xctestrun_metadata__", {}).get("FormatVersion") == 2
            and len(old.get("TestConfigurations", [])) == 1, "Unexpected original descriptor format")
    configurations = old["TestConfigurations"]
    targets = configurations[0].get("TestTargets", [])
    selected = [target for target in targets if target.get("BlueprintName") == "AnytypeTests"]
    require(len(selected) == 1, "Exact original AnytypeTests target missing")
    target = selected[0]
    target["OnlyTestIdentifiers"] = [name.removeprefix("AnytypeTests/") for name in variant["include"]]
    if variant["exclude"]:
        target["SkipTestIdentifiers"] = list(dict.fromkeys(target.get("SkipTestIdentifiers", []) +
            [name.removeprefix("AnytypeTests/") for name in variant["exclude"]]))
    injection = record["binding"].get("runtime_injection", {})
    require(injection.get("original_token") == probe.ORIGINAL_MAIN_THREAD_CHECKER
            and isinstance(injection.get("replacement_token"), str)
            and injection["replacement_token"].endswith("/usr/lib/libMainThreadChecker.dylib")
            and injection.get("change_scope") == "ONE_EXACT_TOKEN_IN_COPIED_TESTING_ENVIRONMENT_ONLY",
            "Original qualified runtime relocation differs")
    chain = target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"].split(":")
    require(chain.count(probe.ORIGINAL_MAIN_THREAD_CHECKER) == 1, "Original exact injection token missing")
    target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = ":".join(
        injection["replacement_token"] if token == probe.ORIGINAL_MAIN_THREAD_CHECKER else token for token in chain)
    configurations[0]["TestTargets"] = selected
    require(new == old and record["binding"].get("only") == target["OnlyTestIdentifiers"]
            and record["binding"].get("skip") == target.get("SkipTestIdentifiers", []),
            "Qualified descriptor changed an unadmitted field")


def validate_original_command(receipt, record, command, log, variant):
    name = "enumerate-" + variant["name"]
    records = [row for row in receipt.get("commands", []) if row.get("name") == name]
    require(len(records) == 1, "Original enumeration command observation missing or duplicated")
    observed = records[0]
    require(observed.get("argv") == command.get("argv")
            and observed.get("worker_pid") == command.get("worker_pid")
            and observed.get("return_code") == command.get("return_code") == 0
            and command.get("owned_group_cleanup") == "TERM_THEN_KILL"
            and not command.get("cleanup_error_type")
            and observed.get("output_sha256") == probe.sha(log),
            "Original command/owned process/output linkage differs")
    quiescence = observed.get("owned_group_quiescence", {})
    require(quiescence.get("status") == "PASS" and quiescence.get("live_members") == 0
            and quiescence.get("pgid") == command.get("worker_pid")
            and not observed.get("quiescence_failure"), "Original enumeration process cleanup is unqualified")
    argv = command["argv"]
    require(isinstance(argv, list) and argv.count("-xctestrun") == 1
            and argv.count("-test-enumeration-output-path") == 1 and argv.count("-resultBundlePath") == 1,
            "Unknown original enumeration argv")
    descriptor = Path(argv[argv.index("-xctestrun")+1])
    output = Path(argv[argv.index("-test-enumeration-output-path")+1])
    result = Path(argv[argv.index("-resultBundlePath")+1])
    owner = receipt.get("owned_simulator", {})
    require(descriptor.name == "SDK06-" + owner.get("nonce", "") + "-" + variant["name"] + ".xctestrun"
            and output.name == variant["name"] + ".enumeration.json"
            and result.name == variant["name"] + ".xcresult"
            and argv == probe.enumeration_command(descriptor, owner.get("udid"), output, result, variant),
            "Original argv differs from the actual qualified variant")


@dataclass(frozen=True)
class QualifiedSelectorPlan:
    admission_path: Path
    control: Path
    current_grammar_json: str
    _seal: object = field(repr=False)
    admission_sha256: str
    evidence: Path
    approved_json: str
    selection_json: str
    variant_json: str

    def verify(self):
        require(self._seal is _PLAN_SEAL, "Selector plan did not pass original evidence admission")
        for name, checksum in json.loads(self.current_grammar_json).items():
            require(probe.sha(self.control / name) == checksum, "Current selector dependency changed")
        require(probe.sha(self.admission_path) == self.admission_sha256, "Committed selector admission changed")
        approved = json.loads(self.approved_json)
        require(read(self.admission_path) == approved, "Selector admission content changed")
        for name, checksum in approved["files"].items():
            path = self.evidence / name
            require(path.is_file() and not path.is_symlink() and probe.sha(path) == checksum,
                    "Original qualified selector evidence changed")
        return json.loads(self.selection_json), json.loads(self.variant_json)

    def arguments(self):
        _, variant = self.verify()
        return (["-only-testing:" + name for name in variant["cli"]] +
                ["-skip-testing:" + name for name in variant.get("cli_skip", [])])

    def enumerate_current(self, app, base, evidence, shared, source):
        selection, variant = self.verify()
        require(selection_from_source(source) == selection, "Current consumer declarations changed")
        original = Path(base[base.index("-xctestrun")+1])
        require(base.count("-destination") == 1, "Current owned destination is missing")
        destination = base[base.index("-destination")+1]
        require(destination.startswith("platform=iOS Simulator,id="), "Unknown current simulator destination")
        udid = destination.removeprefix("platform=iOS Simulator,id=")
        require(probe.owned.valid_udid(udid), "Current owned simulator UUID is invalid")
        token = __import__("uuid").uuid4().hex
        configurations = {}
        observations = {}
        runner_receipt = {"selector_admission_sha256": self.admission_sha256, "actual_product_tests_executed": 0}
        runner = probe.Commands(app, evidence, runner_receipt)
        for label, current_variant in (
            ("discovery", dict(include=["AnytypeTests/" + s for s in component.SUITES],
                exclude=[], cli=["AnytypeTests/" + s for s in component.SUITES], cli_skip=[])),
            ("selected", variant),
        ):
            configuration = original.with_name("UI27-qualified-sdk06-" + token + "-" + label + ".xctestrun")
            binding = probe.copied_configuration(original, configuration, current_variant)
            output = evidence / ("qualified-" + label + ".enumeration.json")
            result = evidence / ("qualified-" + label + ".xcresult")
            command = probe.enumeration_command(configuration, udid,
                output, result, current_variant)
            _, outcome = runner.run(command, "qualified-" + label, timeout=600)
            require(outcome["return_code"] == 0
                    and probe.sha(original) == binding["original_sha256"]
                    and probe.sha(configuration) == binding["copied_sha256"], "Current enumeration changed descriptor bytes")
            payload = read(output)
            if label == "discovery":
                plan, enabled, disabled = component.enumerated_identifiers(payload)
                require(plan == selection["test_plan"] and enabled == set(selection["declarations"])
                        and not enabled.intersection(disabled), "Current binary differs from exact30 declarations")
            else:
                observations["qualification"] = probe.qualify_enumeration(payload, selection)
            configurations[label] = dict(path=str(configuration), sha256=binding["copied_sha256"],
                original_sha256=binding["original_sha256"], binding=binding)
            observations[label] = dict(command=command, sha256=probe.sha(output), configuration=configurations[label])
        self.verify()
        return dict(status="EXACT_COMPILED_SELECTION_VERIFIED", test_plan=selection["test_plan"],
            selector_admission_sha256=self.admission_sha256, selector_plan_protocol=PROTOCOL,
            selected_identifiers=selection["selected"], selected_method_count=23,
            unselected_identifiers=selection["excluded"], enumerated_source_method_count=30,
            selected_configuration=configurations["selected"], discovery_configuration=configurations["discovery"],
            qualified_cli_arguments=self.arguments(), current_enumeration=observations, tests_executed=0)

    def execution_arguments(self, enumeration):
        args = self.arguments()
        require(enumeration.get("status") == "EXACT_COMPILED_SELECTION_VERIFIED"
                and enumeration.get("selector_admission_sha256") == self.admission_sha256
                and enumeration.get("qualified_cli_arguments") == args,
                "Execution must use the exact admitted current enumeration argv")
        return args


def load_plan(admission_path, evidence, run, artifact, current_source, *, control):
    admission_path, evidence = Path(admission_path), Path(evidence)
    approved = admission(read(admission_path))
    original_api(run, artifact, approved)
    current_grammar = original_control_sources(control, approved)
    for name, checksum in approved["files"].items():
        path = evidence / name
        require(path.is_file() and not path.is_symlink() and probe.sha(path) == checksum,
                "Pinned original probe file differs: " + name)
    selection = probe.selection_contract(read(evidence / "originals/execution.json"),
        read(evidence / "originals/shared-editor-components/compiled-suite-enumeration.json"))
    require(selection_from_source(current_source) == selection, "Current consumer source does not match original selector declarations")
    receipt = read(evidence / "receipt.json")
    record, variant = qualified_record(receipt, approved, selection)
    actual = probe.qualify_enumeration(read(evidence / (variant["name"] + ".enumeration.json")), selection)
    require(actual == record.get("qualification"), "Stored qualification differs from actual original enumeration")
    validate_original_copy(evidence / "original.xctestrun", evidence / (variant["name"] + ".xctestrun"), record, variant)
    validate_original_command(receipt, record, read(evidence / ("enumerate-" + variant["name"] + ".command.json")),
                              evidence / ("enumerate-" + variant["name"] + ".log"), variant)
    return QualifiedSelectorPlan(admission_path, Path(control), json.dumps(current_grammar, sort_keys=True), _PLAN_SEAL,
        probe.sha(admission_path), evidence,
        json.dumps(approved, sort_keys=True), json.dumps(selection, sort_keys=True), json.dumps(variant, sort_keys=True))
