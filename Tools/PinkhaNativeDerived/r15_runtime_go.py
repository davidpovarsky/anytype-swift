#!/usr/bin/env python3
"""Build-local Go launcher for pinned gomobile's generated modules.

The native workspace applies the reviewed genproto replacement only to the
native checkout. The pinned gomobile copies that replacement into temporary
gobind modules; those modules must build with GOWORK=off and prove the exact
selected dependency and checksum before compilation.
"""
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
            or downloaded.get("Path") != GENPROTO or downloaded.get("Version") != VERSION
            or downloaded.get("Sum") != MODULE_SUM or downloaded.get("GoModSum") != MOD_SUM):
        raise RuntimeError("Generated gobind module changed the reviewed genproto identity or checksum")
    return dict(native=native, genproto_selection=selected, genproto_download=downloaded)


def audit_modules(real_go, env, cwd, heart):
    if env.get("GOWORK") != "off" or env.get("GOPROXY") != "off":
        raise RuntimeError("Generated module proof requires explicit workspace isolation and offline module cache")
    mod = cwd / "go.mod"
    if not mod.is_file() or "module gobind" not in mod.read_text(encoding="utf8"):
        raise RuntimeError("The pinned gomobile-generated gobind module is missing")

    def query(arguments):
        result = subprocess.run([str(real_go), *arguments], cwd=cwd, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if result.returncode:
            raise RuntimeError("Offline generated-module identity query failed: " + " ".join(arguments) + ": " + result.stderr.strip())
        return json.loads(result.stdout)

    native = query(["list", "-m", "-json", NATIVE_MODULE])
    selected = query(["list", "-m", "-json", GENPROTO])
    # The selection is checked independently: this exact download cannot conceal
    # a different selected version. GOPROXY=off forbids fetching a new module.
    downloaded = query(["mod", "download", "-json", GENPROTO + "@" + VERSION])
    verified = validate_modules(native, selected, downloaded, heart)
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
                "PINKHA_T5_MOBILE_TMP", "PINKHA_T5_GO_AUDIT"]
    if any(not os.environ.get(name) for name in required):
        raise RuntimeError("Build-local launcher contract is missing")
    real_go, heart, workspace, generated, audit = [Path(os.environ[name]) for name in required]
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
        if scope == "generated-gobind" and arguments and arguments[0] in ["build", "install", "run", "test"]:
            receipt["before_build_modules"] = audit_modules(real_go, env, cwd, heart)
        result = subprocess.run([str(real_go), *arguments], cwd=cwd, env=env)
        receipt["return_code"] = result.returncode
        if result.returncode == 0 and scope == "generated-gobind" and arguments[:2] == ["mod", "tidy"]:
            receipt["after_tidy_modules"] = audit_modules(real_go, env, cwd, heart)
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
