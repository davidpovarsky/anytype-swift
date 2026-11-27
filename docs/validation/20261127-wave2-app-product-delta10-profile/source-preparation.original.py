"""Local source-only preparation; creates no runtime adapter or test process."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(relative, expected):
    value = (WORK / relative).read_bytes()
    assert sha(value) == expected
    return value


def inverse(original, candidate):
    # Finite byte offsets, including Unicode. No character-offset ambiguity.
    old, new = original.splitlines(keepends=True), candidate.splitlines(keepends=True)
    edits = []
    for tag, a, b, c, d in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        replacement, expected = b"".join(old[a:b]), b"".join(new[c:d])
        edits.append({"candidateOffset": len(b"".join(new[:c])),
                      "candidateBytes": len(expected), "candidateSHA256": sha(expected),
                      "restoreUTF8": replacement.decode(), "restoreSHA256": sha(replacement)})
    restored = candidate
    for edit in reversed(edits):
        start, length = edit["candidateOffset"], edit["candidateBytes"]
        assert sha(restored[start:start + length]) == edit["candidateSHA256"]
        restored = restored[:start] + edit["restoreUTF8"].encode() + restored[start + length:]
    assert restored == original
    return {"candidateSHA256": sha(candidate), "candidateBytes": len(candidate),
            "restoredSHA256": sha(original), "restoredBytes": len(original), "edits": edits}


proposal = json.loads((WORK / "wave2-product-admission-delta/profile-feasibility/closed-profile-proposal.json").read_text())
specs = proposal["sources"]
raw = {
    "g05": read("torah-acceptance-prep/g05-cache-review/candidate/AnyTypeTests/Pinkha/PropertyCreationSearchTests.swift", specs["g05"]["sha256"]),
    "g07": read("wave2-quote-audit/patch/AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift", specs["g07"]["sha256"]),
    "bin": read("interfaces_work/bin-read-failure/candidate/Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift", specs["bin"]["sha256"]),
}
old = {
    "g05": read("torah-acceptance-prep/g05-current-review/source/AnyTypeTests/Pinkha/PropertyCreationSearchTests.swift", specs["g05"]["originalPreG05SHA256"]),
    "g07": read("wave2-quote-audit/source/AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift", specs["g07"]["retainedPrefixSHA256"]),
    "bin": read("interfaces_work/bin-read-failure/source/Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift", specs["bin"]["retainedSearchSHA256"]),
}
readonly = read("torah-acceptance-prep/g05-current-review/candidate/AnyTypeTests/Pinkha/PropertyCreationSearchTests.swift", specs["g05"]["retainedReadonlyPrefixSHA256"])
inverses = {
    "g05": [inverse(readonly, raw["g05"]), inverse(old["g05"], readonly)],
    "g07": [inverse(old["g07"], raw["g07"])],
    "bin": [inverse(old["bin"], raw["bin"])],
}
annotation = b"    @MainActor\n"
append = raw["g07"][68698:]
assert sha(append) == specs["g07"]["appendSHA256"] and append.count(annotation) == 2
offsets, cursor = [], 0
while True:
    offset = append.find(annotation, cursor)
    if offset < 0:
        break
    offsets.append(68698 + offset)
    cursor = offset + len(annotation)
projection = raw["g07"]
for offset in reversed(offsets):
    assert projection[offset:offset + len(annotation)] == annotation
    projection = projection[:offset] + projection[offset + len(annotation):]
inverse_document = {"schema": "pinkha-app-product-delta10-source-inverse-v1",
                    "runtimeReady": False, "swiftSourceModifiedOrCompiled": False,
                    "sources": inverses,
                    "g07DeclarationProjection": {"sourceSHA256": sha(raw["g07"]),
                        "prefixBytes": 68698, "prefixSHA256": sha(old["g07"]),
                        "appendBytes": len(append), "appendSHA256": sha(append),
                        "annotationUTF8": annotation.decode(), "byteOffsets": offsets,
                        "projectionSHA256": sha(projection)}}
out = ROOT / "profile"
out.mkdir(exist_ok=True)
inverse_raw = (json.dumps(inverse_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
(out / "source-inverse.json").write_bytes(inverse_raw)

parser_path = WORK / "wave2-editor-rtl/profile-inputs/wave15_core_profile.py"
assert sha(parser_path.read_bytes()) == "f544619607be0d25e74cff541ac66418b76df11abcd9c15c0ca774d6cbd5d96a"
loader = importlib.util.spec_from_file_location("delta10_preparation_original_parser", parser_path)
parser = importlib.util.module_from_spec(loader)
loader.loader.exec_module(parser)
sources = {}
for key, spec in specs.items():
    parsed = projection if key == "g07" else raw[key]
    methods = parser.inspect_declarations(parsed.decode())
    assert len(methods) == spec["fullFileTestDeclarations"]
    sources[key] = {"path": spec["path"], "bytes": len(raw[key]), "sha256": sha(raw[key]),
                    "publication": spec["publication"], "originalTarget": spec["originalTarget"],
                    "selectedTarget": "AnytypeTests", "completeDeclarations": methods,
                    "restoredOriginalSHA256": sha(old[key]), "restoredOriginalBytes": len(old[key])}
lanes = {}
for lane in proposal["lanes"]:
    selected = {}
    for method in lane["methods"]:
        definition = {"parameters": method["parameters"], "argument_collections": method["argumentCollections"], "case_count": method["cases"]}
        assert sources[lane["source"]]["completeDeclarations"][method["name"]] == definition
        selected[method["name"]] = definition
    lanes[lane["lane"]] = {"suite": lane["suite"], "source": lane["source"], "methods": selected,
                            "expectedMethods": lane["methodCount"], "declaredCases": lane["caseCount"],
                            "invocationScope": "exact-methods" if lane["source"] == "g07" else "new-suite"}
manifest = {"schema": "pinkha-app-product-delta10-closed-profile-v1", "runtimeReady": False,
            "methods": 10, "declaredCases": 18, "sources": sources, "lanes": lanes,
            "sourceInverse": {"file": "source-inverse.json", "sha256": sha(inverse_raw), "bytes": len(inverse_raw)},
            "affectedOldG05": proposal["affectedOldG05Separate"],
            "existingCore22": {"commit": "a49003fd3a71712efa2cecb7f9bf991cca228fba",
                "loaderSHA256": "aabcf1eec2643f331ed3ab3ae095e156c03de29c4a75ea32405819495af2c9cc",
                "sourceManifestSHA256": "81d178d6d829dc2eff201b8b8dcd190db2da79dc68a6cc06f36ca0d8a90d2778"},
            "actualCombinedSource": None, "successfulProducer": None, "sourceCompilerProof": None,
            "actualCompiledEnumeration": None, "runtimeAdmission": None,
            "runtimeAdapter": "Wave3 owns the separately reviewed fixed additional output namespace and actual integration; no adapter is implemented here."}
manifest_raw = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
(out / "profile.json").write_bytes(manifest_raw)
print(json.dumps({"profileSHA256": sha(manifest_raw), "profileBytes": len(manifest_raw),
                  "inverseSHA256": sha(inverse_raw), "inverseBytes": len(inverse_raw),
                  "g07ProjectionSHA256": sha(projection), "annotationByteOffsets": offsets,
                  "fullDeclarations": {k: len(v["completeDeclarations"]) for k, v in sources.items()},
                  "methods": 10, "cases": 18, "nativeOrCompilerOrRuntimeCalls": 0}, sort_keys=True))
