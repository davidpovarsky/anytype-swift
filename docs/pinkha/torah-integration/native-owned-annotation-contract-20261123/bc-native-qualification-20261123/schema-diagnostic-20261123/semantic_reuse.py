"""Compare the actual declared semantic test inputs with an authenticated prior run."""
import hashlib
import json
import posixpath
from pathlib import Path, PurePosixPath

PACKAGE = "github.com/anyproto/anytype-heart/core/block/object/objectcreator"
INPUT_FIELDS = (
    "GoFiles", "CgoFiles", "CFiles", "CXXFiles", "MFiles", "HFiles", "FFiles",
    "SFiles", "SwigFiles", "SwigCXXFiles", "SysoFiles", "EmbedFiles",
    "TestGoFiles", "XTestGoFiles", "TestEmbedFiles", "XTestEmbedFiles",
)
BUILD_FIELDS = ("CgoCFLAGS", "CgoCPPFLAGS", "CgoCXXFLAGS", "CgoFFLAGS",
                "CgoLDFLAGS", "CgoPkgConfig")


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def stream(path):
    require(path.stat().st_size <= 64 * 1024 * 1024, "Go declaration exceeds evidence bound")
    raw, decoder, position = path.read_text(), json.JSONDecoder(), 0
    result = []
    while position < len(raw):
        while position < len(raw) and raw[position].isspace():
            position += 1
        if position == len(raw):
            break
        value, position = decoder.raw_decode(raw, position)
        result.append(value)
    return result


def module_identity(module):
    if module is None:
        return None
    result = {key: module.get(key) for key in
              ("Path", "Version", "Main", "GoVersion", "Sum", "GoModSum")}
    if module.get("Replace") is not None:
        result["Replace"] = module_identity(module["Replace"])
    return result


def semantic_dependency_fingerprint(listing, declared, heart):
    packages = stream(Path(listing))
    by_name = {row["ImportPath"]: row for row in packages}
    require(len(by_name) == len(packages), "Duplicate declared package identity")
    root_name = PACKAGE + ".test"
    require(root_name in by_name, "Actual semantic test executable is not declared")
    names = set(by_name[root_name].get("Deps", [])) | {root_name}
    require(names.issubset(by_name), "Semantic dependency declaration is incomplete")
    selected = [by_name[name] for name in sorted(names)]
    by_path = {row["path"]: row for row in declared["files"]}
    require(len(by_path) == len(declared["files"]), "Duplicate declared file identity")
    heart = PurePosixPath(str(heart))
    require("runtime" in by_name and by_name["runtime"].get("Standard"), "Actual Go runtime package is missing")
    goroot = PurePosixPath(by_name["runtime"]["Dir"]).parent.parent
    require(PurePosixPath(by_name["runtime"]["Dir"]) == goroot / "src/runtime", "Actual Go runtime root differs")
    files, normalized = {}, []

    for package in selected:
        require(not package.get("Error") and not package.get("DepsErrors"),
                "Semantic dependency resolution reported an error")
        directory = PurePosixPath(package["Dir"])
        input_rows = {}
        for field in INPUT_FIELDS:
            identifiers = []
            for relative in package.get(field, []):
                path = PurePosixPath(posixpath.normpath(str(directory / relative)))
                require(str(path) in by_path, "Semantic input absent from actual hashed closure: " + str(path))
                row = by_path[str(path)]
                if path.is_relative_to(heart):
                    identifier = "heart/" + str(path.relative_to(heart))
                elif (package["ImportPath"] == root_name and field == "GoFiles"
                      and PurePosixPath(relative).is_absolute()):
                    require(path.name == row["sha256"] + "-d"
                            and path.parent.parent.name == "go-build",
                            "Unexpected generated semantic test main identity")
                    identifier = "generated-test-main/objectcreator"
                elif package.get("Module") and package["Module"].get("Dir"):
                    module = package["Module"]
                    root = PurePosixPath(module["Dir"])
                    require(path.is_relative_to(root), "Module source escapes its actual package module")
                    identifier = "module/" + module["Path"] + "@" + module.get("Version", "") + "/" + str(path.relative_to(root))
                else:
                    require(package.get("Standard"), "Unclassified declared semantic input")
                    # Vendored standard packages may report their external module
                    # as Root. The actual declared runtime Dir identifies GOROOT.
                    root = goroot
                    require(path.is_relative_to(root), "Standard input escapes actual Go root")
                    identifier = "goroot/" + str(path.relative_to(root))
                value = {"path": identifier, "bytes": row["bytes"], "sha256": row["sha256"]}
                require(identifier not in files or files[identifier] == value,
                        "Aliased semantic source identity")
                files[identifier] = value
                identifiers.append(identifier)
            if identifiers:
                input_rows[field] = sorted(identifiers)
        normalized.append({
            "import_path": package["ImportPath"], "name": package.get("Name"),
            "for_test": package.get("ForTest"), "standard": bool(package.get("Standard")),
            "module": module_identity(package.get("Module")),
            "imports": sorted(package.get("Imports", [])),
            "deps": sorted(package.get("Deps", [])),
            "import_map": package.get("ImportMap", {}),
            "build_flags": {key: package.get(key, []) for key in BUILD_FIELDS},
            "inputs": input_rows,
        })
    require("heart/core/block/object/objectcreator/owned_annotation_bundled_persistence_test.go" in files,
            "Actual accepted semantic test source is absent")
    require("heart/core/block/import/owned_annotation_comparison.go" not in files and
            "heart/core/application/owned_annotation_import_native_test.go" not in files,
            "Diagnostic delta intersects the prior semantic dependency closure")
    value = {"schema": 1, "root": root_name, "packages": normalized,
             "files": [files[name] for name in sorted(files)]}
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "packages": len(normalized), "files": len(files),
        "canonical_bytes": len(raw),
        "scope": "Exact original Go-declared package/test/embed/native inputs, module identities and build flags. Generated cgo outputs and complete Apple SDK headers remain outside the prior declared scope.",
    }
