#!/usr/bin/env python3
"""Materialize one exact8f2 common intake; no product or test execution.

The historical common controller is retained without changing any byte. A
closed profile is useful for review while the original build runs. A ready
profile only configures the later runtime guard; the original proof APIs must
still read and qualify all actual evidence before returning cloned Products.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import stat
import types

HISTORICAL_SHA = "4ec8617c59da3183a68a53ea9f840e57738469f36f9a0bc5b5a00e806d73cd9c"
FRAGMENT_SHA = "f097cdb1a12087475cda0728d34d7a7dcb2ef0d62ad67810fd9724d11d096bfa"
SOURCE = "8f2c11713fb8a40ae13444104723666ffef68afe"
TREE = "7bcaa6e1b6eadf42eaaaebcb75aab84686aa1f9a"
SDK_REVISION = "38528941720d9b4f2da8dce7afbc788c2e554a0c"
INPUTS = {
    "wave3_warm_retry": ("wave3_warm_retry.py", "c4b67858674156894a29b326c2766d043ce0308c065029bd5c1a6ae1aa254fff"),
    "stage_wave3_warm_retry": ("stage_wave3_warm_retry.py", "e6f71083caea861183dcfb14bb72942a652672864bb463f13adcceab1129b022"),
    "preserve_failed_shared_build": ("preserve_failed_shared_build.py", "d0d696f29cfabcafa08a9dc0e7b50fb240ffab119fda19843420060e4647780c"),
    "receipt_admission": ("receipt_admission.py", "9ce1288feb8f3c534bb7eb784909624fc66168473e93eedff2f2945583d6a18d"),
    "wave3_shared_build": ("wave3_shared_build.py", "47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd"),
    "stage_wave3_source": ("stage_wave3_source.py", "374c863440dd7920d607191f2626ff06621d2bf8ae54a2fad05722874617058d"),
    "base_producer": ("build_wave2_app16_compiler_qualified.py", "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c"),
    "base_delta": ("build_wave2_app16_compiler_qualified_delta.json", "5e18f0a7cdb25cc30d010eb0c19819fe778cb338366763f06f76fef649189970"),
    "original_producer": ("build_main_permission.py", "617b163951a9692909bef38a4991ded8c53e8c21ad9278a9564222fce1a57a68"),
}
MARKER = '\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path, expected):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and stat.S_ISREG(path.lstat().st_mode),
            "Canonical original regular input required")
    value = path.read_bytes()
    require(len(value) <= 4 * 1024**2 and sha(value) == expected, "Pinned original input changed: " + str(path))
    return value


def decode(raw):
    def unique(rows):
        value = {}
        for key, item in rows:
            require(key not in value, "Duplicate frozen profile key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite frozen profile")))


def definitions(value):
    text = value.decode()
    return [(node.name, ast.get_source_segment(text, node)) for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))]


def compose(original, fragment, embedded, profile):
    require(sha(original) == HISTORICAL_SHA and sha(fragment) == FRAGMENT_SHA,
            "Historical4ec controller or reviewed additive fragment changed")
    require(set(embedded) == set(INPUTS) and all(sha(embedded[key].encode()) == value[1] for key, value in INPUTS.items()),
            "Exact original Wave3 gate, adapter and three-level inverse inputs required")
    require(isinstance(profile, dict) and profile.get("schema") == "pinkha-wave2-exact8f2-runtime-freeze-v1"
            and type(profile.get("readyForRuntimeAdmission")) is bool
            and profile.get("sourceCommit") == SOURCE and profile.get("sourceTree") == TREE
            and profile.get("canonicalSDKRevision") == SDK_REVISION,
            "One literal exact8f2/385 profile required; no source override is supported")
    text = fragment.decode()
    for token, value in (("__WAVE3_FROZEN_PROFILE__", profile), ("__WAVE3_EMBEDDED_INPUTS__", embedded)):
        require(text.count(token) == 1, "Exact additive materialization token required")
        text = text.replace(token, repr(value))
    original_text = original.decode()
    require(original_text.count(MARKER) == 1, "Original common main boundary changed")
    addition = "\n\n# BEGIN EXACT8F2 ADDITIVE INTAKE\n" + text + "\n# END EXACT8F2 ADDITIVE INTAKE\n"
    position = original_text.index(MARKER)
    candidate = (original_text[:position] + addition + original_text[position:]).encode()
    require((candidate.decode()[:position] + candidate.decode()[position + len(addition):]).encode() == original,
            "Every original common controller byte must restore")
    old_defs, new_defs = definitions(original), definitions(candidate)
    require(new_defs[:len(old_defs)] == old_defs, "An original function/class declaration changed")
    module = types.ModuleType("wave3_prepared_guard_control_only")
    module.__file__ = str(Path(__file__).with_name("UNEXECUTED_COMBINED_CONTROLLER.py"))
    exec(compile(candidate, module.__file__, "exec"), module.__dict__)
    if profile["readyForRuntimeAdmission"]:
        module.w3_freeze()
        guarded = "CONFIGURED_REQUIRES_ALL_ACTUAL_EVIDENCE_AT_RUNTIME"
    else:
        try:
            module.admit_and_clone_products({}, None, None, None)
        except ValueError as error:
            require(str(error).startswith("Wave3 runtime intake is closed:"), "Closed profile reached an unexpected boundary")
        else:
            raise ValueError("Closed profile unexpectedly reached product admission")
        guarded = "CLOSED_BEFORE_ANY_PRODUCT_READ_OR_COMMAND"
    return candidate, {
        "schema": "pinkha-wave2-exact8f2-common-intake-materialization-v1",
        "status": "PREPARED_EXACT8F2_SHARED_INTAKE_NOT_PRODUCT_ADMISSION",
        "sourceCommit": SOURCE, "sourceTree": TREE, "canonicalSDKRevision": SDK_REVISION,
        "historicalCommonSHA256": HISTORICAL_SHA, "fragmentSHA256": FRAGMENT_SHA,
        "inputSHA256": {key: value[1] for key, value in INPUTS.items()},
        "candidateSHA256": sha(candidate), "inverseRestoresEveryOriginalByte": True,
        "originalDefinitionsUnchanged": len(old_defs), "insertionCharacterOffset": position,
        "insertionCharacterLength": len(addition), "runtimeGuard": guarded,
        "selfContainedCommonModule": True, "additionalRuntimeSiblingPythonFiles": [],
        "actualProductAdmitted": False, "productsCloned": 0, "applicationBuilds": 0,
        "nativeBuilds": 0, "appleTestsExecuted": 0, "simulatorCommands": 0,
    }


def prepare(historical, inputs_root, frozen_profile, frozen_sha256, output):
    package = Path(__file__).resolve().parent
    original = read(historical, HISTORICAL_SHA)
    fragment = read(package / "wave3_intake.py", FRAGMENT_SHA)
    embedded = {key: read(Path(inputs_root) / name, expected).decode() for key, (name, expected) in INPUTS.items()}
    profile_raw = read(frozen_profile, frozen_sha256)
    candidate, proof = compose(original, fragment, embedded, decode(profile_raw))
    output = Path(output)
    require(output.is_absolute() and output.parent.resolve() == output.parent and output.parent.is_dir()
            and not output.exists() and not output.is_symlink(), "Fresh owned preparation output required")
    output.mkdir(mode=0o700)
    for name, value in (("combined_heart_semantics_current.py", candidate),
                        ("combined_heart_semantics_a089_preserved.py", original),
                        ("frozen-profile.json", profile_raw)):
        path = output / name
        with path.open("xb") as stream:
            stream.write(value)
        path.chmod(0o600)
    proof.update(frozenProfileSHA256=sha(profile_raw), materializerSHA256=sha(Path(__file__).read_bytes()))
    path = output / "materialization.json"
    with path.open("x") as stream:
        stream.write(json.dumps(proof, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-common", type=Path, required=True)
    parser.add_argument("--original-inputs", type=Path, required=True)
    parser.add_argument("--frozen-profile", type=Path, required=True)
    parser.add_argument("--frozen-profile-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    proof = prepare(args.historical_common, args.original_inputs, args.frozen_profile,
                    args.frozen_profile_sha256, args.output)
    print(json.dumps({key: proof[key] for key in ("status", "candidateSHA256", "runtimeGuard", "actualProductAdmitted")}))


if __name__ == "__main__":
    main()
