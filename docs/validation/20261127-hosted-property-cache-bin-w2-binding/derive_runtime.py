"""Finite source-only binding delta; never imports or executes runtime controls."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parent
PREFIX = Path("Tools/PinkhaDualEngineRuntime/hosted_property_cache_bin")
BEFORE = ROOT.parent / "candidate1-preserved/after" / PREFIX
AFTER = ROOT / "after" / PREFIX
operations = {}


def replace(name, before, after):
    path = AFTER / name
    raw = path.read_bytes()
    old, new = before.encode(), after.encode()
    assert raw.count(old) == 1, (name, before, raw.count(old))
    path.write_bytes(raw.replace(old, new, 1))
    operations.setdefault(name, []).append({"before": before, "after": after})


replace("run.py", "import cache_bin_profile\n", "import profile_binding\n")
replace("run.py", '''LANES = ("property-read-only-hosted", "property-revision-hosted",
         "property-source-drop-hosted", "library-bin-hosted")
LANE_SCOPE = {"property-read-only-hosted": (3, 7), "property-revision-hosted": (3, 6),
              "property-source-drop-hosted": (2, 2), "library-bin-hosted": (2, 3)}''',
'''LANES = profile_binding.LANES
LANE_SCOPE = profile_binding.LANE_SCOPE''')
replace("run.py", '''def source_contract_for_lane(consumer, lane, originals, producer_pin):
    """Bind only the finite G05/G07/Bin methods to the original compiler proof."""
    require(lane in LANES, "Only the four fixed G05/G07/Bin lanes are permitted")
    rtl_witness = originals.source / "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/rtl-current-editor-profile/rtl_hosted_profile.py"
    return originals.delta_profile.source_contract(consumer.source, lane,
        source_commit=consumer.binding["sourceSHA"], native_compilation_proof=producer_pin, rtl_profile_path=rtl_witness)''',
'''def source_contract_for_lane(consumer, lane, originals, producer_pin):
    """Delegate to one real W2 lane instance under the original command barrier."""
    require(lane in LANES and consumer.profile_bindings.originals is originals,
            "Only the four fixed lanes and actual original Core22 loader are permitted")
    return consumer.profile_bindings.source_contract(lane,
        source_commit=consumer.binding["sourceSHA"], native_compilation_proof=producer_pin)''')
replace("run.py", '"originalTarget": "AnytypeTests", "executedTarget": "AnytypeTests",',
                    '"originalTarget": None, "executedTarget": "AnytypeTests",')
replace("run.py", '        result["sourceContract"] = before\n',
'''        require(before["original_target"] == profile_binding.ORIGINAL_TARGETS[lane]
                and before["selected_target"] == "AnytypeTests", "Original source target identity differs")
        result["originalTarget"] = before["original_target"]
        result["sourceContract"] = before
''')
replace("run.py", 'methods = [name.removeprefix("AnytypeTests/") for name in before["compiled_identifiers"]]',
                    'methods = [name.removeprefix("AnytypeTests/") for name in before["expected_compiled_identifiers"]]')
replace("run.py", '''def run(args, originals):
    cache_bin_profile.require_runtime_ready()''',
'''def run(args, originals):
    profile_binding.require_runtime_ready()''')
replace("run.py", '    built, contract, consumer, clone_progress = {}, None, None, {}\n',
                    '    built, contract, consumer, clone_progress = {}, None, None, {}\n    profile_bindings = None\n')
replace("run.py", '            result.update(receiptContract=contract_ref, commonBuildAdmission=proof)\n',
'''            result.update(receiptContract=contract_ref, commonBuildAdmission=proof)
            profile_bindings = profile_binding.RuntimeBindings(originals, commands)
            result["publishedW2ProfileBinding"] = profile_bindings.proof
''')
replace("run.py", '            consumer = originals.host.Consumer(output, settings, commands, built, app, originals.helpers, binding)\n',
'''            consumer = profile_bindings.host.Consumer(output, settings, commands, built, app, originals.helpers, binding)
            consumer.profile_bindings = profile_bindings
''')
replace("run.py", '''                originals.unchanged()
                result["native23CompilerFinal"] = native23_reader.recheck()''',
'''                originals.unchanged()
                if profile_bindings is not None:
                    profile_bindings.unchanged()  # File-only after any owned-command closure.
                result["native23CompilerFinal"] = native23_reader.recheck()''')
replace("run.py", '''    args = parser.parse_args()
    cache_bin_profile.require_runtime_ready()''',
'''    args = parser.parse_args()
    profile_binding.require_runtime_ready()''')
replace("admission.py", '"cache_bin_profile.py", "profile.json", "activation.json", "native23_receipts.py")}',
                          '"profile_binding.py", "profile-dependency.json", "activation.json", "native23_receipts.py")}')

# The original loader is used byte-for-byte. These three finite inverses show
# exactly how the earlier, unpromoted candidate differs from the restored file.
operations["originals.py"] = [
    {"before": "\nimport cache_bin_profile\n", "after": ""},
    {"before": "        self.delta_profile = cache_bin_profile\n", "after": ""},
    {"before": 'bindings = {"shared": self.shared, "native_core": self.delta_profile,',
     "after": 'bindings = {"shared": self.shared, "native_core": self.native_core,'},
]
report = {"schema": "pinkha-app10-w2-runtime-literal-inverses-v1", "files": {}}
for name, changes in operations.items():
    before = (BEFORE / name).read_bytes()
    after = (AFTER / name).read_bytes()
    current = before
    for change in changes:
        old, new = change["before"].encode(), change["after"].encode()
        assert current.count(old) == 1
        current = current.replace(old, new, 1)
    assert current == after
    restored = after
    for change in reversed(changes):
        old, new = change["before"].encode(), change["after"].encode()
        if not new:
            # A complete whole-file replay above proves these exact removals.
            # Reverse the two removed lines at their unique surrounding anchors.
            if old == b"        self.delta_profile = cache_bin_profile\n":
                anchor = b'        self.native_core = self.full("native_core_hosted_profile", CORE_PATH)\n'
                assert restored.count(anchor) == 1
                restored = restored.replace(anchor, anchor + old, 1)
            elif old == b"\nimport cache_bin_profile\n":
                anchor = b"from types import ModuleType, SimpleNamespace\n"
                assert restored.count(anchor) == 1
                restored = restored.replace(anchor, anchor + old, 1)
            else:
                raise AssertionError("No implicit empty-string inverse is permitted")
        else:
            assert restored.count(new) == 1
            restored = restored.replace(new, old, 1)
    assert restored == before
    ast.parse(after)
    report["files"][name] = {"beforeBytes": len(before), "beforeSHA256": hashlib.sha256(before).hexdigest(),
        "afterBytes": len(after), "afterSHA256": hashlib.sha256(after).hexdigest(),
        "literalOperations": changes, "fullOriginalRestored": True}
(ROOT / "runtime-literal-inverses.json").open("x").write(json.dumps(report, sort_keys=True, indent=2) + "\n")
print(json.dumps({name: {key: row[key] for key in ("afterBytes", "afterSHA256", "fullOriginalRestored")}
                  for name, row in report["files"].items()}, sort_keys=True))
