"""Pure build-control checks. No Apple framework or runtime is executed here."""
import copy
from pathlib import Path
import unittest
import tempfile

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
                    Replace=dict(Path=launcher.GENPROTO, Version=launcher.VERSION,
                                 Sum=launcher.MODULE_SUM, GoModSum=launcher.MOD_SUM))
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

    def test_correct_download_cannot_hide_selected_checksum_drift_or_absence(self):
        for field in ["Sum", "GoModSum"]:
            for value in ["h1:wrong", None]:
                with self.subTest(field=field, value=value):
                    heart, native, selected, downloaded = module_inputs()
                    if value is None:
                        selected["Replace"].pop(field)
                    else:
                        selected["Replace"][field] = value
                    with self.assertRaises(RuntimeError):
                        launcher.validate_modules(native, selected, downloaded, heart)

    def test_native_module_cannot_be_replaced_by_another_checkout(self):
        heart, native, selected, downloaded = module_inputs()
        native["Replace"]["Dir"] = str(Path("/different/heart").resolve())
        with self.assertRaises(RuntimeError):
            launcher.validate_modules(native, selected, downloaded, heart)


    def mobile_fixture(self, root):
        work, cache, gobind = root / "work", root / "module-cache", root / "deps/gobind"
        work.mkdir()
        cache.mkdir()
        gobind.parent.mkdir()
        gobind.write_bytes(b"fixture pinned gobind binary")
        env = dict(GOPROXY="off", GOFLAGS="-mod=readonly", GOWORK="reviewed.work",
                   GOPATH="original-shared-path", PATH="unchanged-path")
        return work, cache, gobind, runtime.digest(gobind), env

    def test_apple_workspace_preserves_original_module_cache_and_pinned_gobind(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
            original = dict(env)
            selected, receipt = runtime.prepare_apple_bind(work, cache, gobind, str(gobind), expected, env)
            self.assertEqual(env, original)
            self.assertEqual(selected["GOMODCACHE"], str(cache))
            self.assertEqual(selected["GOPROXY"], "off")
            self.assertEqual(selected["GOFLAGS"], "-mod=readonly")
            self.assertEqual(selected["GOWORK"], "reviewed.work")
            self.assertTrue((Path(selected["GOPATH"]) / "pkg/gomobile").is_dir())
            self.assertEqual(receipt["gobind_sha256"], expected)
            self.assertEqual(receipt["gomobile_init"], "NOT_INVOKED_UNPINNED_LATEST_INSTALL")
            self.assertEqual(receipt["mobile_version"], runtime.MOBILE_VERSION)

    def test_foreign_path_tool_or_changed_pinned_binary_is_rejected_before_workspace_creation(self):
        for change in ["foreign-path", "changed-binary", "missing-path"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
                selected = str(gobind)
                if change == "foreign-path":
                    selected = str(gobind.parent / "different-gobind")
                elif change == "changed-binary":
                    gobind.write_bytes(b"unexpected replacement binary")
                else:
                    selected = None
                with self.assertRaises(RuntimeError):
                    runtime.prepare_apple_bind(work, cache, gobind, selected, expected, env)
                self.assertFalse((work / "gomobile-gopath").exists())

    def test_apple_preparation_cannot_enable_network_or_replace_missing_module_cache(self):
        for change in ["network", "mutable-modules", "missing-cache", "relative-cache"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
                if change == "network":
                    env["GOPROXY"] = "https://proxy.golang.org"
                elif change == "mutable-modules":
                    env["GOFLAGS"] = "-mod=mod"
                elif change == "missing-cache":
                    cache = cache / "absent"
                else:
                    cache = Path("relative-cache")
                with self.assertRaises(RuntimeError):
                    runtime.prepare_apple_bind(work, cache, gobind, str(gobind), expected, env)
                self.assertFalse((work / "gomobile-gopath").exists())

    def test_existing_mobile_workspace_is_not_reused_or_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
            previous = work / "gomobile-gopath"
            previous.mkdir()
            marker = previous / "preserve-existing"
            marker.write_text("must remain")
            with self.assertRaises(FileExistsError):
                runtime.prepare_apple_bind(work, cache, gobind, str(gobind), expected, env)
            self.assertEqual(marker.read_text(), "must remain")


if __name__ == "__main__":
    unittest.main(verbosity=2)
