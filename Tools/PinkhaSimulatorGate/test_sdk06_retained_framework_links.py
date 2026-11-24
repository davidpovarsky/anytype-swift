"""One original-data regression and derived-file admission control; no compiler."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shlex
import tempfile
import unittest

import sdk06_component_projection as projection

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/validation/20261124-sdk06-retained-framework-links/control-data/original-link-fixture.json"
FIXTURE_SHA = "13a2995c961df0c8cd42184c2c3d489f8a6a5ac63966eea385d503dcdaf3a4c3"


class SDK06RetainedFrameworkLinkControl(unittest.TestCase):
    def test_original_link_inputs_optin_and_exact_retained_byte_admission(self):
        fixture_raw = FIXTURE.read_bytes()
        self.assertEqual(hashlib.sha256(fixture_raw).hexdigest(), FIXTURE_SHA)
        fixture = json.loads(fixture_raw)
        fixed = projection.contract(ROOT)
        binding = fixed["retained_framework_links"]
        rows = projection.retained_framework_rows(fixed)
        self.assertEqual(binding, fixture["retained_framework_links"])
        self.assertFalse(fixture["actual_binary_export_observation"])
        self.assertEqual((len(fixed["selection"]["selected"]), len(fixed["selection"]["excluded"]),
                          fixed["required_argument_cases"]), (23, 7, 32))

        with self.subTest(scope="actual_original_successful_and_failed_link_commands"):
            original = fixture["original_test_link"]
            failed = fixture["current_test_link"]
            self.assertEqual(hashlib.sha256(original["command"].encode()).hexdigest(), original["sha256"])
            self.assertEqual(hashlib.sha256(failed["command"].encode()).hexdigest(), failed["sha256"])
            original_tokens = shlex.split(original["command"])
            failed_tokens = shlex.split(failed["command"])
            positions = []
            for row in rows:
                original_matches = [i for i, token in enumerate(original_tokens)
                                    if token.endswith("/" + row["link_relative"])]
                self.assertEqual(len(original_matches), 1)
                positions += original_matches
                self.assertFalse(any(token.endswith("/" + row["link_relative"]) for token in failed_tokens))
                recipes = [recipe for recipe in fixture["original_framework_recipes"]
                           if recipe["module"] == row["product"]]
                self.assertEqual(len(recipes), 1)
                recipe = recipes[0]
                self.assertEqual(hashlib.sha256(recipe["command"].encode()).hexdigest(),
                                 recipe["command_sha256"])
                recipe_tokens = shlex.split(recipe["command"])
                self.assertIn("-emit-library", recipe_tokens)
                index = recipe_tokens.index("-install_name")
                self.assertEqual(recipe_tokens[index - 1:index + 3],
                                 ["-Xclang-linker", "-install_name", "-Xclang-linker", row["install_name"]])
            self.assertEqual(positions, sorted(positions))
            self.assertEqual(rows[3]["link_identity"]["sha256"],
                             "777d4238100340dd1eac91c0201739fc1329d15089815ac03235a60fedd0db43")
            self.assertEqual(rows[3]["runtime_identity"]["sha256"],
                             "2ff1d982dfc3247a6f9e48ab01ac85c5bd1d87cded07cd4aa2b67d6e41169a23")
            self.assertNotEqual(rows[3]["link_identity"], rows[3]["runtime_identity"])

        with self.subTest(scope="optin_adds_only_four_exact_link_inputs"):
            original_products = Path("/retained-original/Build/Products/Debug-Anytype-iphonesimulator")
            staged_app = Path("/fresh-staged-host/Anytype.app")
            names = [row["basename"] for row in fixed["source_files"].values()]
            baseline, base_ids = projection.project_value(names, staged_app, original_products, fixed)
            explicit_default, default_ids = projection.project_value(
                names, staged_app, original_products, fixed, with_retained_frameworks=False)
            corrected, corrected_ids = projection.project_value(
                names, staged_app, original_products, fixed, with_retained_frameworks=True)
            self.assertEqual((baseline, base_ids), (explicit_default, default_ids))
            self.assertEqual(base_ids, corrected_ids)
            old_settings = baseline["objects"][base_ids["target-config"]]["buildSettings"]
            new_settings = corrected["objects"][corrected_ids["target-config"]]["buildSettings"]
            self.assertEqual(old_settings["OTHER_LDFLAGS"], [str(staged_app / "Anytype.debug.dylib")])
            self.assertEqual(new_settings["OTHER_LDFLAGS"], old_settings["OTHER_LDFLAGS"] +
                             [str(original_products / row["link_relative"]) for row in rows])
            self.assertEqual(new_settings["BUNDLE_LOADER"], str(staged_app / "Anytype"))
            self.assertEqual(new_settings["TEST_HOST"], "")
            self.assertEqual(new_settings["LD_RUNPATH_SEARCH_PATHS"],
                             ["@executable_path/Frameworks", "@loader_path/Frameworks"])
            new_settings["OTHER_LDFLAGS"] = copy.deepcopy(old_settings["OTHER_LDFLAGS"])
            self.assertEqual(corrected, baseline)
            self.assertEqual(corrected["objects"][corrected_ids["target"]]["dependencies"], [])
            self.assertEqual(corrected["objects"][corrected_ids["target"]]["packageProductDependencies"], [])
            with self.assertRaisesRegex(ValueError, "opt-in must be boolean"):
                projection.project_value(names, staged_app, original_products, fixed, with_retained_frameworks=1)

        mutations = (
            ("wrong_original_source", lambda value: value["retained_framework_links"].__setitem__("source_sha", "0" * 40)),
            ("wrong_archive", lambda value: value["retained_framework_links"].__setitem__("native_archive_sha256", "0" * 64)),
            ("wrong_link_command", lambda value: value["retained_framework_links"].__setitem__("original_test_link_command_sha256", "0" * 64)),
            ("missing_framework", lambda value: value["retained_framework_links"]["frameworks"].pop()),
            ("duplicate_framework", lambda value: value["retained_framework_links"]["frameworks"].__setitem__(1, copy.deepcopy(rows[0]))),
            ("non_mapping_framework", lambda value: value["retained_framework_links"]["frameworks"].__setitem__(0, None)),
            ("escaping_link_path", lambda value: value["retained_framework_links"]["frameworks"][0].__setitem__("link_relative", "../Anytype")),
            ("changed_runtime_path", lambda value: value["retained_framework_links"]["frameworks"][0].__setitem__("runtime_relative", "Frameworks/Other.framework/Other")),
            ("changed_install_name", lambda value: value["retained_framework_links"]["frameworks"][0].__setitem__("install_name", "@rpath/Other")),
            ("changed_mode", lambda value: value["retained_framework_links"]["frameworks"][0]["link_identity"].__setitem__("mode", 0o644)),
            ("zero_length", lambda value: value["retained_framework_links"]["frameworks"][0]["link_identity"].__setitem__("bytes", 0)),
            ("malformed_hash", lambda value: value["retained_framework_links"]["frameworks"][0]["link_identity"].__setitem__("sha256", "invalid")),
        )
        for label, mutate in mutations:
            with self.subTest(scope="fixed_metadata_refusal", mutation=label):
                changed = copy.deepcopy(fixed)
                mutate(changed)
                with self.assertRaises(ValueError):
                    projection.retained_framework_rows(changed)

        # These are small derived guard fixtures, never claimed to be the original
        # framework payloads, their exported symbols, or an actual runtime load.
        with tempfile.TemporaryDirectory(prefix="sdk06-framework-guards-") as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            original_products = directory / "original-products"
            staged_app = directory / "staged" / "Anytype.app"
            original_products.mkdir()
            staged_app.mkdir(parents=True)
            derived = copy.deepcopy(fixed)
            originals = {}
            for index, row in enumerate(derived["retained_framework_links"]["frameworks"]):
                for role, root in (("link", original_products), ("runtime", staged_app)):
                    suffix = "runtime-variant" if index == 3 and role == "runtime" else "same-original-role"
                    raw = ("derived-small-guard-fixture:" + row["product"] + ":" + suffix + "\n").encode()
                    path = root / row[role + "_relative"]
                    path.parent.mkdir(parents=True)
                    path.write_bytes(raw)
                    path.chmod(0o755)
                    row[role + "_identity"] = {"bytes": len(raw), "mode": 0o755,
                                               "sha256": hashlib.sha256(raw).hexdigest()}
                    originals[path] = raw
            with self.subTest(scope="derived_exact_files_and_distinct_runtime_identity"):
                observed = projection.verify_retained_framework_links(original_products, staged_app, derived)
                self.assertEqual([row["link_runtime_byte_equal"] for row in observed["frameworks"]],
                                 [True, True, True, False])
                self.assertFalse(observed["symbol_exports_inspected"])
                self.assertFalse(observed["runtime_load_succeeded"])
                self.assertEqual(observed["app_native_or_package_builds"], 0)
                self.assertEqual([row["product"] for row in observed["frameworks"]],
                                 list(projection.RETAINED_FRAMEWORK_PRODUCTS))
            for role, root in (("link", original_products), ("runtime", staged_app)):
                path = root / derived["retained_framework_links"]["frameworks"][0][role + "_relative"]
                raw = originals[path]
                for damage in ("hash", "length", "mode", "missing"):
                    with self.subTest(scope="derived_file_refusal", role=role, damage=damage):
                        if damage == "hash":
                            path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                        elif damage == "length":
                            path.write_bytes(raw[:-1])
                        elif damage == "mode":
                            path.chmod(0o644)
                        else:
                            path.unlink()
                        try:
                            with self.assertRaises((ValueError, FileNotFoundError)):
                                projection.verify_retained_framework_links(original_products, staged_app, derived)
                        finally:
                            path.write_bytes(raw)
                            path.chmod(0o755)
            self.assertEqual({path: path.read_bytes() for path in originals}, originals)


if __name__ == "__main__":
    unittest.main()
