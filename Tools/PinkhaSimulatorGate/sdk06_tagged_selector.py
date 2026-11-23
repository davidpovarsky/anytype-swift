"""Fixed pending-test tag admission; historical controls never admit execution.

The actual current build must enumerate all 30 unchanged declarations and then
exactly the tagged 23 before any method can execute. This module never restores
old Products and never changes the original 23-method/32-case result validator.
"""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import uuid

import sdk06_enumeration_probe as probe
import sdk06_qualified_selector as original
import shared_editor_existing_build as component

PROTOCOL = "sdk06-current-build-pending23-tag-v1"
TAG = "pinkhaSDK06Pending23"
MANIFEST = "Tools/PinkhaSimulatorGate/sdk06-tagged-source.json"
MANIFEST_SHA256 = "aa485ea3c302f2112430f7fd2da91866a24452d9b2d263601d551ec065fc2650"
CONTROL_PATHS = (
    "Tools/PinkhaSimulatorGate/sdk06_tagged_selector.py",
    "Tools/PinkhaSimulatorGate/sdk06_tagged_continuation.py",
    ".github/workflows/pinkha-sdk06-tagged-continuation.yml",
)
_SEAL = object()
require = probe.require
digest = original.digest_bytes


def read_regular(root, relative, maximum=4 * 1024**2):
    name = PurePosixPath(relative)
    require(not name.is_absolute() and "\\" not in relative
            and all(part not in {"", ".", ".."} for part in name.parts), "Unsafe fixed input path")
    root = Path(root)
    path = root
    for part in name.parts:
        path = path / part
        require(not path.is_symlink(), "Fixed input cannot pass through a symbolic link")
    details = path.stat()
    require(stat.S_ISREG(details.st_mode) and 0 < details.st_size <= maximum,
            "Missing, irregular or unbounded fixed input: " + relative)
    return path.read_bytes(), "100755" if details.st_mode & 0o111 else "100644"


def manifest(root):
    data, _ = read_regular(root, MANIFEST)
    require(digest(data) == MANIFEST_SHA256, "Unreviewed tagged source manifest")
    value = json.loads(data)
    require(value["schema"] == "sdk06-pending23-tag-source-v1" and value["tag"] == TAG
            and len(value["source_inverses"]) == 5, "Unknown tag source contract")
    return value


def recover_source(relative, data, contract):
    """Only five pinned current files, with exact-once literal whole-file inverses."""
    row = contract["source_inverses"][relative]
    require(digest(data) == row["after_sha256"], "Current tag metadata/hook bytes differ: " + relative)
    recovered = data
    for edit in reversed(row["hunks"]):
        before, after = edit["before"].encode(), edit["after"].encode()
        require(before != after and recovered.count(after) == 1,
                "Exact tag inverse is absent or ambiguous: " + relative)
        recovered = recovered.replace(after, before, 1)
    require(digest(recovered) == row["before_sha256"], "Tag inverse does not restore the entire original file")
    return recovered


def project_membership(data, contract):
    member = contract["project_membership"]
    require(digest(data) == member["sha256"], "Reviewed AnytypeTests project changed")
    text = data.decode()
    def block(identifier):
        matches = list(re.finditer(r"\b" + identifier + r" /\*[^\n]*?\*/ = \{", text))
        require(len(matches) == 1, "Missing or ambiguous synchronized project object")
        start = matches[0].end() - 1
        depth = 0
        for index in range(start, len(text)):
            depth += (text[index] == "{") - (text[index] == "}")
            if depth == 0:
                return text[start:index + 1]
        raise ValueError("Unclosed synchronized project object")
    target, group, exceptions = (block(member[key]) for key in
                                  ("target_id", "root_group_id", "exceptions_id"))
    require("isa = PBXNativeTarget;" in target
            and re.search(r"fileSystemSynchronizedGroups = \([^)]*" + member["root_group_id"], target)
            and "isa = PBXFileSystemSynchronizedRootGroup;" in group
            and "path = AnytypeTests;" in group and member["exceptions_id"] in group
            and member["target_id"] in exceptions,
            "Tag file is not in the actual AnytypeTests synchronized target")
    omitted = re.search(r"membershipExceptions = \((.*?)\);", exceptions, re.S)
    require(omitted is not None and "Pinkha" not in omitted.group(1),
            "The pending tag is excluded from the synchronized test target")
    return dict(target="AnytypeTests", target_id=member["target_id"],
                root_group_id=member["root_group_id"], relative_path=member["relative_path"],
                project_sha256=member["sha256"], explicit_project_edit_required=False)


def source_admission(app):
    """Source metadata only, explicitly no binary or selector admission."""
    app = Path(app).resolve(strict=True)
    contract = manifest(app)
    historical = contract["historical_view"]
    current, restored = {}, {}
    for relative, row in historical["files"].items():
        data, mode = read_regular(app, relative)
        require(mode == row["git_mode"], "Fixed source executable mode changed")
        restored[relative] = (recover_source(relative, data, contract)
                              if relative in contract["source_inverses"] else data)
        require(digest(restored[relative]) == row["sha256"], "Unadmitted source/proof dependency: " + relative)
        current[relative] = dict(sha256=digest(data), git_mode=mode)
    require(set(contract["source_inverses"]) <= set(restored), "Inverse source is outside the original fixed view")
    source = contract["tag_source"]
    tag_bytes, tag_mode = read_regular(app, source["path"])
    require(digest(tag_bytes) == source["sha256"] and tag_mode == source["git_mode"],
            "The exact new Tag declaration changed")
    current[source["path"]] = dict(sha256=digest(tag_bytes), git_mode=tag_mode)
    project = contract["project_membership"]
    project_bytes, project_mode = read_regular(app, project["path"])
    membership = project_membership(project_bytes, contract)
    current[project["path"]] = dict(sha256=digest(project_bytes), git_mode=project_mode)
    for relative in (MANIFEST, *CONTROL_PATHS):
        data, mode = read_regular(app, relative)
        current[relative] = dict(sha256=digest(data), git_mode=mode)
    specs, tagged = {}, set()
    for relative, row in contract["source_inverses"].items():
        if not relative.endswith(".swift"):
            continue
        original_specs = component.host.core_profile.inspect_declarations(restored[relative].decode())
        current_specs = component.host.core_profile.inspect_declarations((app / relative).read_text())
        require(current_specs == original_specs, "Test parameter names, types, arrays or case counts changed")
        suite = Path(relative).stem
        for name, specification in current_specs.items():
            signature = "(" + "".join(parameter["name"] + ":" for parameter in specification["parameters"]) + ")"
            specs["AnytypeTests/" + suite + "/" + name + signature] = specification
        for edit in row["hunks"]:
            require(edit["kind"] == "test_tag_metadata_only" and edit["after"].count(".tags(." + TAG + ")") == 1
                    and TAG not in edit["before"], "Only exact pending @Test metadata is allowed")
            tagged.add("AnytypeTests/" + edit["method"])
    selection = contract["selection"]
    require(sorted(specs) == selection["declarations"]
            and tagged == {name.split("(", 1)[0] for name in selection["selected"]}
            and len(tagged) == 23 and len(selection["excluded"]) == 7
            and sum(specs[name]["case_count"] for name in selection["selected"]) == 32,
            "Pending tag coverage or exact original method/argument inventory changed")
    return dict(protocol=PROTOCOL, status="SOURCE_METADATA_ADMITTED_SELECTOR_NOT_RUN",
        manifest_sha256=MANIFEST_SHA256, source_root=str(app),
        actual_current_inputs=dict(sorted(current.items())),
        inverse_current_hashes={name: row["after_sha256"] for name, row in contract["source_inverses"].items()},
        recovered_original_hashes={name: row["before_sha256"] for name, row in contract["source_inverses"].items()},
        exact_method_argument_declarations=specs, target_membership=membership,
        selection=selection, selector_qualified=False, product_tests_executed_now=0,
        original_7293_products_relabelled=False)


def validate_build_membership(app):
    """Run on the real Apple checkout before build; no Linux case aliases in source."""
    app = Path(app)
    contract = manifest(app)
    member = contract["project_membership"]
    actual = app / contract["tag_source"]["path"]
    synchronized = app / member["synchronized_root"] / member["relative_path"]
    require(synchronized.is_file() and actual.samefile(synchronized),
            "Tag source is not physically available to the Xcode synchronized target")
    command = ["git", "-C", str(app), "grep", "-l", "-F", TAG, "--",
               "AnyTypeTests/**/*.swift", "AnytypeTests/**/*.swift",
               "Anytype/**/*.swift", "Modules/**/*.swift", "PinkhaStage1Acceptance/**/*.swift"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    expected = {name for name in contract["source_inverses"] if name.endswith(".swift")} | {contract["tag_source"]["path"]}
    require(result.returncode == 0 and set(result.stdout.splitlines()) == expected,
            "Pending tag must occur only in its exact four tracked test source files")


def historical_retained_view(app, view):
    """Copy a fixed historical view for the unchanged original proof verifier.

    No source view path is returned as an App source. The wrapper records actual
    current hashes separately; every nested verifier field belongs to the
    explicitly labelled historical source view, including its source_inputs.
    """
    app, view = Path(app).resolve(strict=True), Path(view)
    require(not view.is_symlink() and view.resolve() != app
            and not app.is_relative_to(view.resolve()), "Historical view cannot replace the App checkout")
    admitted = source_admission(app)
    contract = manifest(app)
    expected = contract["historical_view"]["files"]
    if not view.exists():
        view.mkdir(parents=True)
        for relative, row in expected.items():
            data, _ = read_regular(app, relative)
            if relative in contract["source_inverses"]:
                data = recover_source(relative, data, contract)
            require(digest(data) == row["sha256"], "Historical view input changed during creation")
            destination = view / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(data)
            destination.chmod(0o755 if row["git_mode"] == "100755" else 0o644)
    expected_directories = {str(parent) for name in expected for parent in PurePosixPath(name).parents if str(parent) != "."}
    files, directories = set(), set()
    for path in view.rglob("*"):
        require(not path.is_symlink(), "Historical view cannot contain links")
        relative = path.relative_to(view).as_posix()
        if path.is_dir(): directories.add(relative)
        else: files.add(relative)
    require(files == set(expected) and directories == expected_directories,
            "Historical view has missing or extra members")
    for relative, row in expected.items():
        data, mode = read_regular(view, relative)
        require(digest(data) == row["sha256"] and mode == row["git_mode"],
                "Historical view bytes/mode differ")
    from sdk06_retained_controls import verify_retained_controls
    import sdk06_retained_controls as retained
    verifier = contract["historical_view"]["verifier_path"]
    require(Path(retained.__file__).resolve() == app / verifier,
            "The unchanged actual retained verifier is required")
    result = verify_retained_controls(view)
    require(source_admission(app) == admitted, "Current source changed during historical verification")
    return dict(status="PASS_HISTORICAL_CONTROLS_ONLY_CURRENT_SELECTOR_NOT_RUN",
        source_scope="HISTORICAL_RETAINED_VIEW", historical_view_root=str(view.resolve()),
        historical_original_receipt=result, actual_current_inputs=admitted["actual_current_inputs"],
        inverse_current_hashes=admitted["inverse_current_hashes"],
        recovered_original_hashes=admitted["recovered_original_hashes"],
        historical_view_is_app_build_source=False, current_selector_qualified=False,
        old_controller_methods_executed_now=0, product_tests_executed_now=0)


def selection_arguments():
    return ["-only-testing:AnytypeTests/" + suite for suite in component.SUITES] + ["-only-testing-tags", TAG]


def source_selection(source, contract):
    expected_hashes = {name: row["after_sha256"] for name, row in contract["source_inverses"].items()
                       if name.endswith(".swift")}
    require(source.get("source_hashes") == expected_hashes
            and source.get("expected_methods") == 23 and source.get("declared_invocations") == 32,
            "Current tagged component source differs from the fixed admission")
    declarations = source.get("compiled_declarations", {})
    actual = dict(test_plan="AnytypeTests",
        selected=sorted(declarations[name] for name in source["methods"]),
        excluded=sorted(declarations[name] for name in source["unselected_existing_methods"]),
        declarations=sorted(declarations.values()))
    require(actual == contract["selection"], "Current source signature or excluded declaration changed")
    return actual


def qualify_enumeration(payload, selection):
    plan, enabled, disabled = component.enumerated_identifiers(payload)
    require(plan == "AnytypeTests" and enabled == set(selection["selected"])
            and set(selection["excluded"]) <= disabled and not enabled.intersection(disabled),
            "Current tag did not select exact23 and explicitly exclude all7; no product tests permitted")
    return dict(status="EXACT_CURRENT_TAG_SELECTION_VERIFIED", selected=sorted(enabled),
                excluded=selection["excluded"], expected_methods=23, required_argument_cases=32,
                product_tests_executed=0)


@dataclass(frozen=True)
class TaggedSelectionPlan:
    control: Path
    binding_json: str
    source_json: str
    _seal: object = field(repr=False)
    _pending_execution: dict = field(default_factory=dict, repr=False, compare=False)

    def verify(self):
        require(self._seal is _SEAL, "Tag plan did not pass exact current source admission")
        require(source_admission(self.control) == json.loads(self.source_json), "Current tag plan sources changed")
        return manifest(self.control)

    def enumerate_current(self, app, base, evidence, shared, source):
        contract = self.verify()
        require(Path(app).resolve() == self.control and not self._pending_execution,
                "Tag enumeration requires this current App source and a fresh plan")
        selection = source_selection(source, contract)
        require(base[:2] == ["xcodebuild", "test-without-building"]
                and base.count("-xctestrun") == base.count("-destination") == 1
                and not any(item.startswith(("-only-testing", "-skip-testing")) for item in base),
                "Unexpected current test command prefix")
        destination = base[base.index("-destination") + 1]
        require(destination.startswith("platform=iOS Simulator,id=")
                and probe.owned.valid_udid(destination.split("=", 2)[-1]),
                "Actual owned simulator UUID required")
        original_configuration = Path(base[base.index("-xctestrun") + 1])
        token = uuid.uuid4().hex
        bindings, observations = {}, {}
        command_receipt = dict(protocol=PROTOCOL, **json.loads(self.binding_json),
                               source_manifest_sha256=MANIFEST_SHA256, product_tests_executed=0)
        runner = probe.Commands(app, evidence, command_receipt)
        for label in ("discovery", "selected"):
            configuration = original_configuration.with_name("UI27-tagged-sdk06-" + token + "-" + label + ".xctestrun")
            binding = component.scoped_configuration(original_configuration, configuration,
                ["AnytypeTests/" + suite for suite in component.SUITES], shared)
            command_base = list(base)
            command_base[command_base.index("-xctestrun") + 1] = str(configuration)
            arguments = (selection_arguments() if label == "selected" else
                         ["-only-testing:AnytypeTests/" + suite for suite in component.SUITES])
            output, result = evidence / ("tagged-" + label + ".enumeration.json"), evidence / ("tagged-" + label + ".xcresult")
            command = [*command_base, *arguments, "-enumerate-tests", "-test-enumeration-style", "flat",
                "-test-enumeration-format", "json", "-test-enumeration-output-path", str(output),
                "-resultBundlePath", str(result)]
            _, outcome = runner.run(command, "tagged-" + label, timeout=600)
            require(outcome["return_code"] == 0
                    and probe.sha(original_configuration) == binding["original_sha256"]
                    and probe.sha(configuration) == binding["sha256"], "Current enumeration or descriptor integrity failed")
            payload = original.read(output)
            if label == "discovery":
                plan, enabled, disabled = component.enumerated_identifiers(payload)
                require(plan == "AnytypeTests" and enabled == set(selection["declarations"])
                        and not enabled.intersection(disabled), "Current build does not expose the exact30 declarations")
            else:
                qualify_enumeration(payload, selection)
            bindings[label] = binding
            observations[label] = dict(command=command, output_path=str(output), sha256=probe.sha(output))
        self.verify()
        receipt = dict(status="EXACT_COMPILED_SELECTION_VERIFIED", selector_plan_protocol=PROTOCOL,
            source_manifest_sha256=MANIFEST_SHA256, binding=json.loads(self.binding_json),
            selection_nonce=token, test_plan="AnytypeTests", selected_identifiers=selection["selected"],
            selected_method_count=23, unselected_identifiers=selection["excluded"], enumerated_source_method_count=30,
            selected_configuration=bindings["selected"], discovery_configuration=bindings["discovery"],
            original_configuration_path=str(original_configuration), destination=destination,
            tag_cli_arguments=selection_arguments(), current_enumeration=observations, tests_executed=0)
        self._pending_execution["receipt_sha256"] = digest(json.dumps(receipt, sort_keys=True).encode())
        return receipt

    def execution_arguments(self, enumeration, selected_base):
        self.verify()
        require(self._pending_execution.get("receipt_sha256") ==
                digest(json.dumps(enumeration, sort_keys=True).encode()),
                "Execution requires this plan's exact current enumeration, once")
        require(enumeration["binding"] == json.loads(self.binding_json)
                and enumeration["tag_cli_arguments"] == selection_arguments()
                and selected_base[:2] == ["xcodebuild", "test-without-building"]
                and selected_base.count("-xctestrun") == selected_base.count("-destination") == 1
                and not any(item.startswith(("-only-testing", "-skip-testing")) for item in selected_base)
                and selected_base[selected_base.index("-destination") + 1] == enumeration["destination"]
                and selected_base[selected_base.index("-xctestrun") + 1] == enumeration["selected_configuration"]["path"],
                "Current source/run/destination/descriptor or exact tag argv differs")
        for name in ("discovery", "selected"):
            observation = enumeration["current_enumeration"][name]
            require(probe.sha(Path(observation["output_path"])) == observation["sha256"],
                    "Current original enumeration changed")
            binding = enumeration[name + "_configuration"]
            require(probe.sha(Path(binding["path"])) == binding["sha256"]
                    and probe.sha(Path(enumeration["original_configuration_path"])) == binding["original_sha256"],
                    "Current original or selected descriptor changed")
        self._pending_execution.clear()
        self._pending_execution["consumed"] = True
        return selection_arguments()


def load_plan(app, binding):
    app = Path(app).resolve(strict=True)
    require(app == Path(__file__).resolve().parents[2], "Current tag plan belongs only to this actual controller checkout")
    require(set(binding) == {"source_sha", "run_id", "run_attempt"}
            and re.fullmatch("[0-9a-f]{40}", binding["source_sha"])
            and all(re.fullmatch("[1-9][0-9]*", binding[name]) for name in ("run_id", "run_attempt")),
            "Exact current source/run/attempt identity required")
    admitted = source_admission(app)
    return TaggedSelectionPlan(app, json.dumps(binding, sort_keys=True),
                               json.dumps(admitted, sort_keys=True), _SEAL)
