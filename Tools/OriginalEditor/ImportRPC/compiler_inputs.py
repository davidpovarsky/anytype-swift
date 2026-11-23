#!/usr/bin/env python3
"""Bind real owned Go sources and Go's distinct generated test-main inputs."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

FIELDS = ("GoFiles", "CgoFiles", "CFiles", "CXXFiles", "MFiles", "HFiles",
          "FFiles", "SFiles", "SysoFiles", "EmbedFiles", "TestGoFiles",
          "XTestGoFiles", "TestEmbedFiles", "XTestEmbedFiles")
MODULE = "github.com/anyproto/anytype-heart"

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def row(path, name):
    data = Path(path).read_bytes()
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def canonical_absolute(value):
    path = PurePosixPath(value)
    require(value and path.is_absolute() and str(path) == value
            and ".." not in path.parts and "\0" not in value and "\\" not in value,
            "Noncanonical absolute compiler input path")
    return Path(value)

def checked_file(root, path):
    root, path = Path(root), Path(path)
    require(path.is_relative_to(root) and path != root, "Compiler input escapes its declared root")
    for current in [path, *path.parents]:
        require(not current.is_symlink(), "Symlink compiler input refused")
        if current == root:
            break
    require(path.resolve() == path and path.is_file(), "Compiler input is not a regular declared file")
    require(stat.S_ISREG(path.stat().st_mode), "Compiler input is not regular")
    return path

def parse_declaration(path):
    text = Path(path).read_text()
    decoder, offset, packages = json.JSONDecoder(), 0, []
    while offset < len(text):
        while offset < len(text) and text[offset].isspace():
            offset += 1
        if offset == len(text):
            break
        package, offset = decoder.raw_decode(text, offset)
        require(isinstance(package, dict) and not package.get("Error") and not package.get("DepsErrors"),
                "Actual Go package declaration contains errors")
        packages.append(package)
    require(packages, "Actual Go package declaration is empty")
    return packages

def collect(path, heart, cache, evidence, expected_packages):
    heart = canonical_absolute(str(heart))
    cache = canonical_absolute(str(cache))
    require(heart.resolve() == heart and cache.resolve() == cache
            and not heart.is_relative_to(cache) and not cache.is_relative_to(heart),
            "Owned Heart/cache roots overlap or resolve elsewhere")
    packages = parse_declaration(path)
    targets = {MODULE + "/" + item.removeprefix("./"): item.removeprefix("./")
               for item in expected_packages}
    bases = {}
    for package in packages:
        if package.get("ImportPath") in targets:
            require(package["ImportPath"] not in bases, "Duplicate declared base test package")
            bases[package["ImportPath"]] = package
    require(set(bases) == set(targets), "Original test package declaration is incomplete")
    entries, generated, metadata, active = {}, {}, [], {}
    try:
        for package in packages:
            directory = canonical_absolute(package.get("Dir", "/"))
            module = package.get("Module")
            metadata.append({"import_path": package.get("ImportPath"), "directory": str(directory),
                             "standard": package.get("Standard", False), "module": module,
                             "name": package.get("Name"), "for_test": package.get("ForTest")})
            if module and module.get("Main"):
                require(directory.is_relative_to(heart), "Main-module package escapes the owned Heart")
            if not directory.is_relative_to(heart):
                continue
            for part in [directory, *directory.parents]:
                require(not part.is_symlink(), "Symlink owned package directory refused")
                if part == heart:
                    break
            require(directory.resolve() == directory, "Owned package directory resolves elsewhere")
            for field in FIELDS:
                for name in package.get(field, []):
                    active = {"import_path": package.get("ImportPath"), "directory": str(directory),
                              "field": field, "declared_name": name}
                    item = PurePosixPath(name)
                    require(name and str(item) == name and ".." not in item.parts
                            and "\0" not in name and "\\" not in name,
                            "Noncanonical declared compiler filename")
                    source = directory / name
                    if source.is_relative_to(heart):
                        source = checked_file(heart, source)
                        relative = source.relative_to(heart).as_posix()
                        entries[relative] = row(source, relative)
                        continue
                    # Go list -test emits a synthetic main package whose Dir is
                    # the original package but whose single GoFile is in GOCACHE.
                    # It is retained as a generated compiler input, never treated
                    # as source or silently excluded from stability verification.
                    import_path = package.get("ImportPath", "")
                    base_name = import_path.removesuffix(".test")
                    require(import_path == base_name + ".test" and base_name in targets
                            and package.get("Name") == "main" and not package.get("ForTest")
                            and field == "GoFiles" and package.get("GoFiles") == [name]
                            and not any(package.get(other) for other in FIELDS if other != "GoFiles"),
                            "Source escape is not an original selected synthetic test main")
                    base = bases[base_name]
                    require(directory == canonical_absolute(base["Dir"])
                            and module == base.get("Module") and module
                            and module.get("Path") == MODULE and module.get("Main") is True
                            and module.get("Dir") == str(heart)
                            and package.get("Root") == str(heart)
                            and {"os", "reflect", "testing", "testing/internal/testdeps"}.issubset(package.get("Imports", [])),
                            "Synthetic test-main module/package identity differs")
                    source = canonical_absolute(name)
                    require(source.is_relative_to(cache), "Synthetic test main escapes this run's owned GOCACHE")
                    relative = source.relative_to(cache).as_posix()
                    require(re.fullmatch(r"[0-9a-f]{2}/[0-9a-f]{64}-d", relative)
                            and relative[:2] == source.name[:2], "Unexpected generated Go cache filename")
                    checked_file(cache, source)
                    require(import_path not in generated, "Duplicate synthetic test-main package")
                    retained = "compiler-generated-test-mains/" + targets[base_name] + ".testmain.go"
                    observed = row(source, relative)
                    require(observed["bytes"] > 0, "Generated test main is empty")
                    destination = evidence / retained
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(source.read_bytes())
                    retained_row = row(destination, retained)
                    require(all(retained_row[k] == observed[k] for k in ("bytes", "sha256", "git_blob")),
                            "Retained generated test-main bytes differ")
                    generated[import_path] = {"import_path": import_path, "field": field,
                        "cache_input": observed, "retained_input": retained_row}
        require(set(generated) == {name + ".test" for name in targets},
                "Selected synthetic test-main closure is incomplete")
        require("core/annotation_import.go" in entries and "clientlibrary/service/service.pb.go" in entries,
                "Actual native declaration omits original endpoint/mobile export")
    except BaseException as error:
        write(evidence / "COMPILER_INPUT_REJECTION.json",
              {"actual": active, "error_type": type(error).__name__, "error": str(error)})
        raise
    receipt = {"owned_source_inputs": sorted(entries.values(), key=lambda item: item["path"]),
               "generated_test_main_inputs": sorted(generated.values(), key=lambda item: item["import_path"]),
               "packages": metadata, "cache_root": str(cache),
               "scope": "Actual go list -deps -test declaration. Real Heart files and distinct original Go-generated test mains are all retained/bound; no compilation credit."}
    write(evidence / "DECLARED_NATIVE_COMPILER_INPUTS.json", receipt)
    return receipt

def verify_unchanged(receipt, heart, cache):
    for entry in receipt["owned_source_inputs"]:
        source = checked_file(heart, Path(heart) / entry["path"])
        require(row(source, entry["path"]) == entry, "Declared native source changed after compilation")
    for entry in receipt["generated_test_main_inputs"]:
        expected = entry["cache_input"]
        source = checked_file(cache, Path(cache) / expected["path"])
        require(row(source, expected["path"]) == expected, "Declared generated test main changed after compilation")
    return {"status": "PASS", "owned_source_files": len(receipt["owned_source_inputs"]),
            "generated_test_mains": len(receipt["generated_test_main_inputs"])}

def remove_owned_work(work, expected_marker):
    work = canonical_absolute(str(work))
    require(work.resolve() == work and not work.is_symlink() and work.is_dir(),
            "Owned cleanup root changed")
    marker = checked_file(work, work / ".original-rpc-owned-work.json")
    require(marker.read_bytes() == expected_marker, "Owned cleanup marker differs")
    changed = []
    # Go's own module cache deliberately uses read-only directories. Only these
    # newly owned work directories are made owner-traversable/removable; external
    # symlinks are never followed. Source stability is checked before this step.
    for directory, names, _files in os.walk(work, topdown=True, followlinks=False):
        current = Path(directory)
        require(current.resolve().is_relative_to(work) and not current.is_symlink(),
                "Owned cleanup traversed an external directory")
        info = current.stat()
        desired = stat.S_IMODE(info.st_mode) | stat.S_IRWXU
        if desired != stat.S_IMODE(info.st_mode):
            current.chmod(desired)
            changed.append(current.relative_to(work).as_posix())
        names[:] = [name for name in names if not (current / name).is_symlink()]
    shutil.rmtree(work)
    require(not work.exists(), "Owned work remains after cleanup")
    return {"removed": True, "owner_writable_directories": len(changed),
            "scope": "Only this newly created work root; no symlink target followed."}
