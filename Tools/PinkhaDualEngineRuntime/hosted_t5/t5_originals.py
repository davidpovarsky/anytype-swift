"""Install only exact original T5 declarations; no old standalone entry point."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import uuid

from profile import MANIFEST_SHA256, PROFILE, require

BASE = "Tools/PinkhaSimulatorGate/"
BUILD = "Tools/CurrentAppleValidation/combined_heart_semantics/build15/"
HOST = BUILD + "combined_host_acceptance_app15.py"


def constants(originals, module, path, names):
    """Retain the finite original assignment nodes, including their dependencies."""
    text = originals.sources[path].decode()
    tree = ast.parse(text)
    nodes = []
    for name in names:
        found = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
        require(len(found) == 1, "One exact original constant required: " + name)
        nodes.append(found[0])
        raw = "".join(text.splitlines(keepends=True)[found[0].lineno - 1:found[0].end_lineno]).encode()
        originals.proof["declarations"].append({"path": path, "declaration": name,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "originalASTNodeUnchanged": True})
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), module.__file__, "exec"), module.__dict__)


def install(originals, control, receipt_writer):
    manifest_path = Path(__file__).with_name("original_sources.json")
    raw_manifest = manifest_path.read_bytes()
    require(hashlib.sha256(raw_manifest).hexdigest() == MANIFEST_SHA256, "T5 original source manifest changed")
    manifest = json.loads(raw_manifest)
    require(manifest["schema"] == "pinkha-hosted-t5-original-source-closure-v1", "Unknown T5 original source closure")
    for relative, pin in manifest["files"].items():
        path = originals.source / relative
        require(path.is_file() and not path.is_symlink() and path.resolve() == path, "Original T5 source missing or aliased")
        raw = path.read_bytes()
        require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"]
                and hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == pin["gitBlob"],
                "Original T5 source changed: " + relative)
        if relative in originals.sources:
            require(originals.sources[relative] == raw, "Original shared/T5 source disagreement")
        originals.sources[relative] = raw
        originals.proof["files"][relative] = pin
    evidence = originals.full("t5_native_ui_evidence", BASE + "t5_native_ui_evidence.py")
    mutations = originals.full("t5_native_ui_mutations", BASE + "t5_native_ui_mutations.py")
    r08 = originals.full("t5_native_ui_r08", BASE + "t5_native_ui_r08.py")
    native_ui = originals.selected("hosted_t5_native_ui_identity", BASE + "run_t5_native_ui.py", ("native_ui_identity",),
        bindings={"evidence": evidence, "native_mutations": mutations})
    constants(originals, native_ui, BASE + "run_t5_native_ui.py", ("UI_FIXTURE", "UI_SECRETS", "NATIVE_ROOT"))
    pair = originals.selected("hosted_t5_original_pair_validators", BASE + "run_t5_apple_pair.py",
        ("require", "sha_bytes", "is_digest", "target_key", "validate_freshness_graph", "contains_secret"))
    constants(originals, pair, BASE + "run_t5_apple_pair.py", ("ROOT_RELATIVE_PATH",))
    freshness = originals.selected("t5_remaining_freshness", BASE + "t5_remaining_freshness.py",
        ("source_contract", "native_paths"), bindings={"pair": pair})
    constants(originals, freshness, BASE + "t5_remaining_freshness.py",
        ("PROTOCOL", "NATIVE_PASS", "SUITE", "METHOD", "SWIFT", "ORIGINAL_BYTES", "ORIGINAL_SHA", "PRIVATE", "COUNTS", "STAGES"))
    gateway = originals.selected("combined_t5_freshness_gateway", BUILD + "combined_t5_freshness_gateway.py",
        ("validate_receipt", "validate_combined_receipt"), bindings={"pair": pair,
            **{name: getattr(freshness, name) for name in ("PROTOCOL", "NATIVE_PASS", "STAGES", "COUNTS")},
            "RUNTIME_PROFILE": PROFILE})
    selection = originals.selected("hosted_t5_original_selection", BASE + "validate_release.py", ("method_results",),
        bindings={"require": originals.shared.require})
    ui = originals.selected("hosted_t5_original_ui_budget", BASE + "run_ui27.py", ("code_carriers", "selection_time_budget"),
        bindings={"digest": originals.shared.digest, "method_results": selection.method_results})
    constants(originals, ui, BASE + "run_ui27.py", ("DEFAULT_METHOD_SECONDS", "PROPERTIES_METHOD_SECONDS", "LONG_PROPERTIES_METHODS"))
    shared = originals.shared
    bindings = {"shared": shared, "uuid": uuid, "NATIVE": "AnytypeTests", "UI": "PinkhaStage1AcceptanceUITests",
                "SUPPORT": Path("Library/Application Support"), "PROFILE": PROFILE}
    for name in ("require", "raw", "decode", "write_bytes", "sha", "digest"):
        bindings[name] = getattr(shared, name)
    bindings["write"] = receipt_writer.write
    functions = originals.selected("hosted_t5_original_functions", HOST,
        ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "result_selection", "host_validation_module",
         "native_ui_prior_processes", "observe_owned_groups"), bindings=bindings)
    for name in ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "result_selection", "host_validation_module", "native_ui_prior_processes"):
        bindings[name] = getattr(functions, name)
    host = originals.selected("hosted_t5_original_consumer", HOST, ("Consumer",),
        methods=("__init__", "command", "container", "installed", "create", "appearance", "read_private", "stage", "preserve", "native_ui", "freshness"),
        bindings=bindings)
    helpers = {"run_ui27": ui, "t5_native_ui_evidence": evidence, "t5_native_ui_mutations": mutations,
               "t5_native_ui_r08": r08, "run_t5_native_ui": native_ui, "t5_remaining_freshness": freshness}
    return {"host": host, "functions": functions, "helpers": helpers, "gateway": gateway, "pair": pair,
            "evidence": evidence, "manifestSHA256": MANIFEST_SHA256}


def bind_runtime(originals, t5, runtime, bundle_id, version):
    require(bundle_id == "io.anytype.app", "Original T5 UI explicitly requires the shared Debug App bundle")
    originals.configure_runtime(runtime=runtime, bundle_id=bundle_id)
    require(not hasattr(originals.shared, "VERSION") and not hasattr(t5["gateway"], "VERSION"), "T5 native identity already bound")
    originals.shared.VERSION = version
    t5["gateway"].VERSION = version
    originals.runtime_binding["VERSION"] = version
    originals.proof["sameHostRuntimeBinding"]["VERSION"] = version
