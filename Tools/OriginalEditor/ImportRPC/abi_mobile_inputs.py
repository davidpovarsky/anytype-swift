#!/usr/bin/env python3
"""Observe the original gomobile iOS builds without changing their source or targets.

Only -x/-work are added to the original gomobile command. Its original traced
environment and retained wrapper roots drive post-build go-list observations.
No generator, native test, or second mobile compilation is performed here.
"""
import json
from pathlib import Path
import re

MOBILE_VERSION = "v0.0.0-20250218173827-cd096645fcd3"
MOBILE_SOURCE_BLOBS = {
    "cmd/gomobile/env.go": "320597994e7c7cfef14fc295a074700fee0ca02b",
    "cmd/gomobile/build.go": "a8f0ad2ccd1bf8aef846c32c228ad5328a393d67",
    "cmd/gomobile/bind.go": "4e1c453f418589afc1576045140946fb878a3868",
    "cmd/gomobile/bind_iosapp.go": "ca3815e3a61a405a59969c09df5ce7ae2e9f01e3",
    "cmd/gomobile/init.go": "48642e22b3afaf45c2542144f34e6d4ab891b6de",
}
TARGETS = (("ios", "arm64", "iphoneos"), ("iossimulator", "arm64", "iphonesimulator"),
           ("iossimulator", "amd64", "iphonesimulator"))
TAGS = "nogrpcserver gomobile nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"
FIELDS = ("GoFiles", "CgoFiles", "CFiles", "CXXFiles", "MFiles", "HFiles", "FFiles",
          "SFiles", "SysoFiles", "EmbedFiles")
ENV_KEYS = ("PWD", "GOMODCACHE", "GOOS", "GOARCH", "GOFLAGS", "CC", "CXX",
            "CGO_CFLAGS", "CGO_CXXFLAGS", "CGO_LDFLAGS", "CGO_ENABLED", "DARWIN_SDK", "GOPATH")


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def json_objects(text):
    decoder, position, rows = json.JSONDecoder(), 0, []
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break
        value, position = decoder.raw_decode(text, position)
        require(isinstance(value, dict), "Go declaration contains a non-object")
        rows.append(value)
    require(rows, "Empty actual Go declaration")
    return rows


def module_identity(module):
    result = {key: module.get(key, "") for key in ("Path", "Version")}
    if module.get("Replace"):
        result["Replace"] = {key: module["Replace"].get(key, "") for key in ("Path", "Version")}
    return result


def admit_mobile_module(module, cache, row):
    require(module["Path"] == "golang.org/x/mobile" and module["Version"] == MOBILE_VERSION
            and not module.get("Replace"), "Original gomobile module identity differs")
    directory = Path(module["Dir"]).resolve()
    require(directory.is_relative_to(Path(cache).resolve()), "Original gomobile module escapes owned cache")
    rows = []
    for name, blob in MOBILE_SOURCE_BLOBS.items():
        observed = row(directory / name, name)
        require(observed["git_blob"] == blob, "Original gomobile trace/source contract differs")
        rows.append(observed)
    return {"module": module_identity(module), "directory": str(directory), "files": rows}


def parse_bind_trace(stdout, stderr, temporary, environment, sdk_context, ldflags):
    temporary = Path(temporary).resolve()
    work_lines = [line[5:] for line in stdout.splitlines() if line.startswith("WORK=")]
    require(len(work_lines) == 1, "Original gomobile retained-work identity is missing/repeated")
    work = Path(work_lines[0])
    require(work.is_absolute() and work == work.resolve() and work.parent == temporary
            and work.name.startswith("gomobile-work-") and not work.is_symlink(),
            "Original gomobile work escapes the owned temporary root")
    replacements = {"$WORK": str(work), "$GOMOBILE": str(Path(environment["GOPATH"]) / "pkg/gomobile"),
                    "$GOPATH": environment["GOPATH"]}
    lines = [line for line in stderr.splitlines() if " go build " in line and " -buildmode=c-archive " in line]
    require(len(lines) == 3, "Original gomobile must execute exactly its three iOS archive builds")
    observed = {}
    expected_prefix = ("-tags " + ",".join(TAGS.split()) + " -x -ldflags " + ldflags
                       + " -work -buildmode=c-archive -o ")
    for original_line in lines:
        expanded = original_line
        for name, value in replacements.items():
            expanded = expanded.replace(name, value)
        prefix, arguments = expanded.split(" go build ", 1)
        matches = list(re.finditer(r"(?:^| )([A-Z][A-Z0-9_]*)=", prefix))
        require(tuple(match.group(1) for match in matches) == ENV_KEYS,
                "Original gomobile archive environment key/order differs")
        values = {match.group(1): prefix[match.end():matches[n+1].start() if n+1 < len(matches) else len(prefix)].strip()
                  for n, match in enumerate(matches)}
        require(all(values.values()) and not any("$" in value for value in values.values()),
                "Unresolved original gomobile environment value")
        source = Path(values["PWD"])
        require(source.is_absolute() and source == source.resolve() and source.parent.parent == work,
                "Original gomobile wrapper source escapes retained work")
        platform, arch = source.parent.name, source.name.removeprefix("src-")
        key = (platform, arch)
        require(key not in observed and source.name == "src-" + arch
                and key in {(p, a) for p, a, _ in TARGETS}, "Unexpected/repeated original iOS target")
        sdk = next(s for p, a, s in TARGETS if (p, a) == key)
        context = sdk_context[sdk]
        clang_arch = "x86_64" if arch == "amd64" else arch
        minimum = "-miphoneos-version-min=13.0" if platform == "ios" else "-mios-simulator-version-min=13.0"
        flags = "-isysroot " + context["sdk_root"] + " " + minimum + " -fembed-bitcode -arch " + clang_arch
        require(values["GOOS"] == "ios" and values["GOARCH"] == arch and values["GOFLAGS"] == "-tags=ios"
                and values["CGO_ENABLED"] == "1" and values["DARWIN_SDK"] == sdk
                and values["CC"] == context["clang"] and values["CXX"] == context["clang"] + "++"
                and all(values[k] == flags for k in ("CGO_CFLAGS", "CGO_CXXFLAGS", "CGO_LDFLAGS"))
                and values["GOMODCACHE"] == environment["GOMODCACHE"]
                and values["GOPATH"] == str(work / platform) + ":" + environment["GOPATH"],
                "Original traced iOS toolchain/architecture flags differ")
        require(arguments.startswith(expected_prefix) and arguments.endswith(" ./gobind"),
                "Original mobile archive invocation changed")
        archive = Path(arguments[len(expected_prefix):-len(" ./gobind")])
        require(archive.is_absolute() and archive == archive.resolve()
                and archive.is_relative_to(work) and archive.suffix == ".a",
                "Original archive output escapes owned work")
        observed[key] = {"platform": platform, "architecture": arch, "sdk": sdk,
                        "source": str(source), "archive": str(archive), "environment": values,
                        "original_trace_line": original_line}
    require(set(observed) == {(p, a) for p, a, _ in TARGETS}, "Original iOS target set is incomplete")
    return work, [observed[(p, a)] for p, a, _ in TARGETS]


def declared_files(packages, roots, heart, source, original_modules, row):
    roots = tuple(Path(root).resolve() for root in roots)
    heart, source = Path(heart).resolve(), Path(source).resolve()
    rows, summaries = {}, []
    for package in packages:
        require(not package.get("Error") and not package.get("DepsErrors"),
                "Actual iOS package declaration contains errors")
        directory = Path(package.get("Dir", "/")).resolve()
        require(any(directory.is_relative_to(root) for root in roots),
                "Actual iOS package directory escapes original owned/toolchain inputs")
        module = package.get("Module")
        if module:
            if module.get("Main"):
                require(module["Path"] == "gobind" and Path(module["Dir"]).resolve() == source,
                        "Unexpected actual mobile wrapper main module")
            elif module["Path"] == "github.com/anyproto/anytype-heart":
                replacement = module.get("Replace", {})
                require(Path(replacement.get("Dir", "/")).resolve() == heart
                        and replacement.get("Path") == str(heart) and not replacement.get("Version"),
                        "Actual mobile wrapper does not use the exact qualified Heart checkout")
            else:
                require(module["Path"] in original_modules
                        and module_identity(module) == module_identity(original_modules[module["Path"]]),
                        "Actual mobile dependency differs from original Heart module selection")
        else:
            require(package.get("Standard"), "Unidentified non-standard mobile package")
        names = {name for field in FIELDS for name in package.get(field, [])}
        extra = []
        if module:
            actual_module = module.get("Replace", module)
            if actual_module.get("GoMod"):
                extra.append(Path(actual_module["GoMod"]))
        for path in [directory / name for name in sorted(names)] + extra:
            require(path.is_file() and not path.is_symlink()
                    and any(path.resolve().is_relative_to(root) for root in roots),
                    "Actual iOS compiler/module source escapes its admitted roots")
            path = path.resolve()
            observed = row(path, str(path))
            require(str(path) not in rows or rows[str(path)] == observed, "Actual mobile input changed during declaration")
            rows[str(path)] = observed
        summaries.append({"import_path": package.get("ImportPath"), "directory": str(directory),
                          "standard": bool(package.get("Standard")), "module": module})
    for name in ("core/annotation_import.go", "core/annotation_schema.go",
                 "clientlibrary/service/service.pb.go", "pb/commands.pb.go"):
        require(str(heart / name) in rows, "Actual iOS declaration omits the original Import RPC source")
    require(str(source / "go.mod") in rows, "Actual generated wrapper module was not declared")
    for name in ("go.mod", "go.sum"):
        path = source / name
        require(path.is_file(), "Original mobile wrapper module/checksum input is absent")
        rows[str(path)] = row(path, str(path))
    return sorted(rows.values(), key=lambda item: item["path"]), summaries


def capture(commands, bind_command, heart, work, evidence, environment, sdk_context,
            original_modules, goroot, ldflags, row, write):
    bind_stdout = (evidence / bind_command["stdout"]).read_text()
    bind_stderr = (evidence / bind_command["stderr"]).read_text()
    retained, builds = parse_bind_trace(bind_stdout, bind_stderr, work / "tmp", environment, sdk_context, ldflags)
    originals = {module["Path"]: module for module in original_modules}
    require(len(originals) == len(original_modules)
            and originals["github.com/anyproto/anytype-heart"].get("Main"),
            "Original Heart module selection is missing/repeated")
    original_sums = set((heart / "go.sum").read_text().splitlines())
    union, groups = {}, []
    for build in builds:
        source = Path(build["source"])
        require(source.is_dir() and Path(build["archive"]).is_file(),
                "Successful original gomobile wrapper/archive was not retained")
        before = {name: row(source / name, name) for name in ("go.mod", "go.sum")}
        require(set((source / "go.sum").read_text().splitlines()).issubset(original_sums),
                "Original wrapper introduced an unpinned dependency checksum")
        saved = environment.copy()
        try:
            environment.update({key: value for key, value in build["environment"].items() if key != "PWD"})
            # Original pinned runCmd adds this after emitting its trace.
            environment["TMPDIR"] = str(retained)
            label = "ios-inputs-" + build["platform"] + "-" + build["architecture"]
            output = commands.require(label, ["go", "list", "-mod=readonly", "-deps", "-json",
                "-tags", ",".join(TAGS.split()), "./gobind"], source, 1500)
            command = commands.items[-1]
        finally:
            environment.clear()
            environment.update(saved)
        rows, packages = declared_files(json_objects(output.read_text()),
            (heart, retained, environment["GOMODCACHE"], goroot), heart, source, originals, row)
        require({name: row(source / name, name) for name in ("go.mod", "go.sum")} == before,
                "Read-only iOS declaration changed original wrapper module/checksum inputs")
        for item in rows:
            require(item["path"] not in union or union[item["path"]] == item,
                    "Cross-architecture source changed during observation")
            union[item["path"]] = item
        wrapper_rows = [row(path, path.relative_to(source).as_posix()) for path in sorted(source.rglob("*"))
                        if path.is_file() and not path.is_symlink()]
        destination = evidence / "mobile-wrapper-source" / build["platform"] / build["architecture"]
        for item in wrapper_rows:
            path = destination / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((source / item["path"]).read_bytes())
        groups.append({**build, "declaration_command": command, "files": rows, "packages": packages,
                       "wrapper_module_inputs": before, "retained_wrapper_source": wrapper_rows,
                       "archive_identity": row(Path(build["archive"]), build["archive"])})
    result = {"schema": "otzaria.original-import-mobile-compiler-inputs/1", "status": "PASS",
        "original_gomobile_command": bind_command, "retained_original_work": str(retained),
        "groups": groups, "files": sorted(union.values(), key=lambda item: item["path"]),
        "scope": "Actual original iOS archive environments and wrapper module declarations after successful single gomobile bind; no build/test replay."}
    write(evidence / "DECLARED_MOBILE_COMPILER_INPUTS.json", result)
    return result


def recheck(inputs, row):
    for item in inputs["files"]:
        require(row(Path(item["path"]), item["path"]) == item,
                "Actual mobile compiler/module input changed after its declaration")
    for group in inputs["groups"]:
        require(row(Path(group["archive"]), group["archive"]) == group["archive_identity"],
                "Actual original mobile archive changed after binding")
    return {"status": "PASS", "actual_ios_target_groups": len(inputs["groups"]),
            "declared_source_module_files_checked": len(inputs["files"])}
