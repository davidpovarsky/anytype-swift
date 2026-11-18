"""Pure build-control checks. No Apple framework or runtime is executed here."""
import copy
from pathlib import Path
import unittest

import build_t5_r15_runtime as runtime
import r15_runtime_go as launcher


def metadata():
    return {"AvailableLibraries": [
        {"LibraryIdentifier": "ios-arm64", "LibraryPath": "Lib.framework",
         "SupportedArchitectures": ["arm64"], "SupportedPlatform": "ios"},
        {"LibraryIdentifier": "ios-arm64_x86_64-simulator", "LibraryPath": "Lib.framework",
         "SupportedArchitectures": ["arm64", "x86_64"], "SupportedPlatform": "ios",
         "SupportedPlatformVariant": "simulator"},
    ]}


def slices():
    return [dict(path=path, architecture=arch, marker=runtime.VERSION, sha256="a" * 64)
            for path, arch in sorted(runtime.EXPECTED_SLICES)]


def module_inputs():
    heart = Path("/owned/heart").resolve()
    native = dict(Path=launcher.NATIVE_MODULE, Replace=dict(Dir=str(heart), Path=str(heart)))
    selected = dict(Path=launcher.GENPROTO, Version="obsolete-root-version",
                    Replace=dict(Path=launcher.GENPROTO, Version=launcher.VERSION))
    downloaded = dict(Path=launcher.GENPROTO, Version=launcher.VERSION,
                      Sum=launcher.MODULE_SUM, GoModSum=launcher.MOD_SUM)
    return heart, native, selected, downloaded


class R15RuntimeControls(unittest.TestCase):
    def test_exact_device_and_both_simulator_architectures_are_accepted(self):
        proof = runtime.validate_framework(metadata(), slices())
        self.assertEqual(proof["verified_architecture_count"], 3)
        self.assertEqual(proof["simulator_architectures"], ["arm64", "x86_64"])

    def test_missing_duplicate_and_foreign_slices_are_rejected(self):
        for change in ["missing", "duplicate", "foreign"]:
            with self.subTest(change=change):
                values = slices()
                if change == "missing":
                    values.pop()
                elif change == "duplicate":
                    values[1] = copy.deepcopy(values[0])
                else:
                    values[0]["architecture"] = "armv7"
                with self.assertRaises(RuntimeError):
                    runtime.validate_framework(metadata(), values)

    def test_legacy_marker_or_invalid_binary_hash_cannot_enable_r15(self):
        for field, value in [("marker", runtime.MARKER), ("marker", runtime.VERSION + "-unexpected"),
                             ("sha256", ""), ("sha256", "g" * 64)]:
            with self.subTest(field=field, value=value[:16]):
                values = slices()
                values[0][field] = value
                with self.assertRaises(RuntimeError):
                    runtime.validate_framework(metadata(), values)

    def test_metadata_cannot_relabel_a_missing_or_different_platform(self):
        for field, value in [("SupportedPlatform", "macos"), ("SupportedPlatformVariant", ""),
                             ("SupportedArchitectures", ["arm64"]), ("LibraryPath", "../Lib.framework")]:
            with self.subTest(field=field):
                info = metadata()
                info["AvailableLibraries"][1][field] = value
                with self.assertRaises(RuntimeError):
                    runtime.validate_framework(info, slices())

    def test_native_and_generated_modules_have_explicit_different_workspace_scopes(self):
        heart, generated, work = Path("/owned/heart"), Path("/owned/tmp"), Path("/owned/work/go.work")
        self.assertEqual(launcher.select_scope(heart / "clientlibrary", heart, generated, work),
                         ("heart-source", str(work.resolve())))
        self.assertEqual(launcher.select_scope(generated / "gomobile-work/ios/src-arm64", heart, generated, work),
                         ("generated-gobind", "off"))
        with self.assertRaises(RuntimeError):
            launcher.select_scope(Path("/unowned/location"), heart, generated, work)

    def test_generated_module_must_retain_native_source_and_effective_genproto(self):
        heart, native, selected, downloaded = module_inputs()
        actual = launcher.validate_modules(native, selected, downloaded, heart)
        self.assertEqual(actual["genproto_download"]["Sum"], launcher.MODULE_SUM)

    def test_generated_module_checksum_or_revision_drift_is_rejected(self):
        for field, value in [("Path", "example.invalid/fork"), ("Version", "unexpected"),
                             ("Sum", "h1:wrong"), ("GoModSum", "h1:wrong")]:
            with self.subTest(field=field):
                heart, native, selected, downloaded = module_inputs()
                downloaded[field] = value
                with self.assertRaises(RuntimeError):
                    launcher.validate_modules(native, selected, downloaded, heart)

    def test_downloading_the_right_version_cannot_hide_the_wrong_selected_version(self):
        heart, native, selected, downloaded = module_inputs()
        selected["Replace"]["Version"] = "wrong-selected-version"
        with self.assertRaises(RuntimeError):
            launcher.validate_modules(native, selected, downloaded, heart)

    def test_native_module_cannot_be_replaced_by_another_checkout(self):
        heart, native, selected, downloaded = module_inputs()
        native["Replace"]["Dir"] = str(Path("/different/heart").resolve())
        with self.assertRaises(RuntimeError):
            launcher.validate_modules(native, selected, downloaded, heart)


if __name__ == "__main__":
    unittest.main(verbosity=2)
