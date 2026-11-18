#!/usr/bin/env python3
"""Build-local Go launcher for pinned gomobile's generated modules.

The native workspace applies the reviewed genproto replacement only to the
native checkout. The pinned gomobile copies that replacement into temporary
gobind modules; those modules must build with GOWORK=off and prove the exact
selected dependency and checksum before compilation.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

NATIVE_MODULE = "github.com/anyproto/anytype-heart"
GENPROTO = "google.golang.org/genproto"
VERSION = "v0.0.0-20241021214115-324edc3d5d38"
MODULE_SUM = "h1:Q3nlH8iSQSRUwOskjbcSMcF2jiYMNiQYZ0c2KEJLKKU="
MOD_SUM = "h1:xBI+tzfqGGN2JBeSebfKXFSdBpWVQ7sLW40PTupVRm4="


def select_scope(cwd, heart, generated, workspace):
    cwd, heart, generated = cwd.resolve(), heart.resolve(), generated.resolve()
    if cwd.is_relative_to(heart):
        return "heart-source", str(workspace.resolve())
    if cwd.is_relative_to(generated):
        return "generated-gobind", "off"
    raise RuntimeError("Go child working directory is outside the owned native and generated module scopes")


def validate_modules(native, selected, downloaded, heart):
    resolved = native.get("Replace", native)
    if (native.get("Path") != NATIVE_MODULE
            or not resolved.get("Dir") or Path(resolved["Dir"]).resolve() != heart.resolve()):
        raise RuntimeError("Generated gobind module does not use the exact owned Heart checkout")
    effective = selected.get("Replace", selected)
    if (selected.get("Path") != GENPROTO or effective.get("Path") != GENPROTO
            or effective.get("Version") != VERSION
            or effective.get("Sum") != MODULE_SUM or effective.get("GoModSum") != MOD_SUM
            or downloaded.get("Path") != GENPROTO or downloaded.get("Version") != VERSION
            or downloaded.get("Sum") != MODULE_SUM or downloaded.get("GoModSum") != MOD_SUM):
        raise RuntimeError("Generated gobind module changed the reviewed genproto identity or checksum")
    return dict(native=native, genproto_selection=selected, genproto_download=downloaded)



def module_records(text):
    decoder, position, records = json.JSONDecoder(), 0, []
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break
        item, position = decoder.raw_decode(text, position)
        if not isinstance(item, dict) or item.get("Error"):
            raise RuntimeError("Invalid module JSON stream")
        records.append(item)
    if not records:
        raise RuntimeError("Empty module JSON stream")
    return records


def checksum(value):
    try:
        if not isinstance(value, str) or not value.startswith("h1:"):
            return False
        return len(base64.b64decode(value[3:], validate=True)) == 32
    except ValueError:
        return False


def downloaded_modules(text):
    modules = {}
    for item in module_records(text):
        path, version = item.get("Path"), item.get("Version")
        if (not isinstance(path, str) or not path or not isinstance(version, str) or not version
                or item.get("Replace") or not all(checksum(item.get(key)) for key in ["Sum", "GoModSum"])):
            raise RuntimeError("Incomplete downloaded dependency identity/checksums")
        key = path + "@" + version
        value = {key: item[key] for key in ["Path", "Version", "Sum", "GoModSum"]}
        if key in modules and modules[key] != value:
            raise RuntimeError("Conflicting downloaded dependency receipts")
        modules[key] = value
    return modules


def selected_graph(records, heart):
    graph, seen, main_count = {}, set(), 0
    for item in records:
        path = item.get("Path")
        if not isinstance(path, str) or not path or path in seen:
            raise RuntimeError("Invalid or duplicate selected module path")
        seen.add(path)
        if item.get("Main"):
            if path != "gobind" or item.get("Version") or item.get("Replace"):
                raise RuntimeError("Unexpected generated main module")
            main_count += 1
            continue
        effective = item.get("Replace", item)
        if path == NATIVE_MODULE:
            if (not effective.get("Dir") or effective.get("Version")
                    or Path(effective["Dir"]).resolve() != heart.resolve()):
                raise RuntimeError("Generated graph changed the exact local Heart source")
            continue
        if (not item.get("Version") or not effective.get("Path") or not effective.get("Version")
                or not all(checksum(effective.get(key)) for key in ["Sum", "GoModSum"])):
            raise RuntimeError("Selected remote module lacks its version or both actual checksums: " + path)
        graph[path] = dict(version=item["Version"], replaced="Replace" in item,
                           effective_path=effective["Path"], effective_version=effective["Version"],
                           sum=effective["Sum"], go_mod_sum=effective["GoModSum"])
    if main_count != 1 or not graph:
        raise RuntimeError("One actual gobind main module and a nonempty dependency graph required")
    return graph


def validate_downloaded_graph(graph, downloads):
    for path, selected in graph.items():
        key = selected["effective_path"] + "@" + selected["effective_version"]
        expected = dict(Path=selected["effective_path"], Version=selected["effective_version"],
                        Sum=selected["sum"], GoModSum=selected["go_mod_sum"])
        if downloads.get(key) != expected:
            raise RuntimeError("Selected graph and downloaded dependency differ: " + path)


def validate_seeded_graph(actual, expected):
    if not actual or not expected or any(expected.get(path) != value for path, value in actual.items()):
        raise RuntimeError("Generated tidy/build selected an unseeded or changed module/version/replacement/checksum")
    return dict(selected_modules=len(actual), seeded_modules=len(expected),
                pruned_seed_modules=sorted(set(expected) - set(actual)),
                policy="ALLOW_UNUSED_MODULE_PRUNING_ONLY")


def canonical_manifest(document):
    if (not isinstance(document, dict) or document.get("Module") != {"Path": "gobind"}
            or document.get("Go") != "1.26.5"):
        raise RuntimeError("Pinned gomobile-generated module/go directive differs")
    result = dict(document)
    for key in ["Require", "Replace"]:
        if not isinstance(result.get(key), list):
            raise RuntimeError("Generated require and replace declarations are required")
        result[key] = sorted(result[key], key=lambda item: json.dumps(item, sort_keys=True))
    return result


def load_seed_contract(path, expected_sha, heart, generated):
    if (not path.is_absolute() or path.is_symlink()
            or not path.resolve().is_relative_to(generated.resolve().parent)
            or not path.is_file() or len(expected_sha) != 64
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha):
        raise RuntimeError("Owned generated-graph contract path or hash differs")
    contract = json.loads(path.read_text(encoding="utf8"))
    if (contract.get("schema") != "pinkha-generated-module-graph-v1"
            or contract.get("native_directory") != str(heart.resolve())
            or not isinstance(contract.get("selected_dependencies"), dict)
            or not contract["selected_dependencies"]):
        raise RuntimeError("Generated-graph contract identity is missing")
    canonical_manifest(contract["before_tidy_manifest"])
    return contract


def audit_initial_manifest(real_go, env, cwd, contract):
    if env.get("GOWORK") != "off" or env.get("GOPROXY") != "off":
        raise RuntimeError("Original generated manifest must be checked offline and outside the native workspace")
    result = subprocess.run([str(real_go), "mod", "edit", "-json"], cwd=cwd, env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if result.returncode:
        raise RuntimeError("Cannot read original generated module manifest: " + result.stderr.strip())
    actual = canonical_manifest(json.loads(result.stdout))
    if actual != contract["before_tidy_manifest"]:
        raise RuntimeError("Actual pre-tidy gomobile module differs from the hydrated seed declarations")
    raw = (cwd / "go.mod").read_bytes()
    return dict(status="EXACT_GENERATED_INPUT", go_mod_text=raw.decode("utf8"),
                go_mod_sha256=hashlib.sha256(raw).hexdigest(),
                input_native_graph_sha256=contract["input_native_graph_sha256"])


def audit_modules(real_go, env, cwd, heart, contract):
    if env.get("GOWORK") != "off" or env.get("GOPROXY") != "off":
        raise RuntimeError("Generated module proof requires explicit workspace isolation and offline module cache")
    mod = cwd / "go.mod"
    if not mod.is_file() or "module gobind" not in mod.read_text(encoding="utf8"):
        raise RuntimeError("The pinned gomobile-generated gobind module is missing")

    def query(arguments, stream=False):
        result = subprocess.run([str(real_go), *arguments], cwd=cwd, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if result.returncode:
            raise RuntimeError("Offline generated-module identity query failed: " + " ".join(arguments) + ": " + result.stderr.strip())
        return module_records(result.stdout) if stream else json.loads(result.stdout)

    native = query(["list", "-m", "-json", NATIVE_MODULE])
    # Hydrate only the reviewed cached module before listing the selected graph,
    # so go list includes both checksums. GOPROXY=off forbids any new download.
    downloaded = query(["mod", "download", "-json", GENPROTO + "@" + VERSION])
    selected = query(["list", "-m", "-json", GENPROTO])
    # Both the selected graph and cached archive must prove the exact hashes.
    # A correct cached download cannot conceal a different selected dependency.
    verified = validate_modules(native, selected, downloaded, heart)
    # An offline full download adds only checksums to this disposable generated
    # module. The seed must already contain every selected archive.
    download_records = query(["mod", "download", "-json", "all"], stream=True)
    downloads = downloaded_modules("\n".join(json.dumps(item) for item in download_records))
    graph = selected_graph(query(["list", "-m", "-json", "all"], stream=True), heart)
    validate_downloaded_graph(graph, downloads)
    verified["seed_graph_comparison"] = validate_seeded_graph(graph, contract["selected_dependencies"])
    verified["selected_dependency_graph"] = graph
    verified["go_mod_sha256"] = hashlib.sha256(mod.read_bytes()).hexdigest()
    verified["go_mod_text"] = mod.read_text(encoding="utf8")
    sums = cwd / "go.sum"
    if not sums.is_file():
        raise RuntimeError("Generated module has no checksum file")
    verified["go_sum_sha256"] = hashlib.sha256(sums.read_bytes()).hexdigest()
    return verified


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    required = ["PINKHA_T5_REAL_GO", "PINKHA_T5_HEART", "PINKHA_T5_GOWORK",
                "PINKHA_T5_MOBILE_TMP", "PINKHA_T5_GO_AUDIT",
                "PINKHA_T5_GENERATED_CONTRACT", "PINKHA_T5_GENERATED_CONTRACT_SHA256"]
    if any(not os.environ.get(name) for name in required):
        raise RuntimeError("Build-local launcher contract is missing")
    real_go, heart, workspace, generated, audit = [Path(os.environ[name]) for name in required[:5]]
    if not real_go.is_absolute() or real_go.resolve() == Path(__file__).resolve():
        raise RuntimeError("An absolute original Go executable is required")
    cwd = Path.cwd().resolve()
    receipt = dict(argv=arguments, cwd=str(cwd), original_go=str(real_go),
                   original_gowork=os.environ.get("GOWORK"),
                   goos=os.environ.get("GOOS"), goarch=os.environ.get("GOARCH"),
                   darwin_sdk=os.environ.get("DARWIN_SDK"))
    path = audit / (str(uuid4()) + ".json")
    try:
        scope, gowork = select_scope(cwd, heart, generated, workspace)
        env = dict(os.environ, GOWORK=gowork)
        receipt.update(scope=scope, selected_gowork=gowork, goproxy=env.get("GOPROXY"))
        contract = None
        if scope == "generated-gobind":
            contract = load_seed_contract(
                Path(os.environ["PINKHA_T5_GENERATED_CONTRACT"]),
                os.environ["PINKHA_T5_GENERATED_CONTRACT_SHA256"], heart, generated)
            receipt["generated_contract_sha256"] = os.environ["PINKHA_T5_GENERATED_CONTRACT_SHA256"]
            if arguments[:2] == ["mod", "tidy"]:
                receipt["before_tidy_seed"] = audit_initial_manifest(real_go, env, cwd, contract)
        if scope == "generated-gobind" and arguments and arguments[0] in ["build", "install", "run", "test"]:
            receipt["before_build_modules"] = audit_modules(real_go, env, cwd, heart, contract)
        result = subprocess.run([str(real_go), *arguments], cwd=cwd, env=env)
        receipt["return_code"] = result.returncode
        if result.returncode == 0 and scope == "generated-gobind" and arguments[:2] == ["mod", "tidy"]:
            receipt["after_tidy_modules"] = audit_modules(real_go, env, cwd, heart, contract)
        return result.returncode
    except Exception as error:
        receipt.update(return_code=91, error_type=type(error).__name__, error=str(error))
        print(str(error), file=sys.stderr)
        return 91
    finally:
        with path.open("x", encoding="utf8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
