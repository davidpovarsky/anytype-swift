"""Pure build-control checks. No Apple framework or runtime is executed here."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
import subprocess
from unittest import mock
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


    def dependency_fixture(self, root):
        source, work = root / "cached-mobile", root / "owned-work"
        source.mkdir()
        work.mkdir()
        primary = Path(__file__).resolve().parents[2] / (
            "docs/validation/20261118-t5-r15-runtime/44235484816/dependency-source")
        for name in runtime.MOBILE_SEED_HASHES:
            (source / name).write_bytes((primary / ("mobile." + name)).read_bytes())
        selected = dict(Path="golang.org/x/mobile", Version=runtime.MOBILE_VERSION,
                        Sum=runtime.MOBILE_MODULE_SUM, GoModSum=runtime.MOBILE_MOD_SUM, Dir=str(source))
        return source, work, selected

    def test_mobile_seed_uses_exact_primary_files_without_mutating_the_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, work, selected = self.dependency_fixture(Path(temporary).resolve())
            before = {name: (source / name).read_bytes() for name in runtime.MOBILE_SEED_HASHES}
            seed, receipt = runtime.prepare_mobile_dependency_seed(work, selected)
            self.assertEqual({name: (seed / name).read_bytes() for name in before}, before)
            self.assertEqual({name: (source / name).read_bytes() for name in before}, before)
            self.assertEqual(receipt["seed_sha256"], runtime.MOBILE_SEED_HASHES)
            self.assertEqual(seed.parent, work)

    def test_mobile_selection_or_cached_declaration_drift_is_rejected_before_copy(self):
        for change in ["module", "version", "sum", "mod-sum", "replace", "go.mod", "go.sum"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                source, work, selected = self.dependency_fixture(Path(temporary).resolve())
                if change in ["go.mod", "go.sum"]:
                    (source / change).write_bytes(b"changed declaration bytes")
                elif change == "replace":
                    selected["Replace"] = {"Path": "foreign/mobile"}
                else:
                    field = {"module": "Path", "version": "Version", "sum": "Sum", "mod-sum": "GoModSum"}[change]
                    selected[field] = "unexpected"
                with self.assertRaises(RuntimeError):
                    runtime.prepare_mobile_dependency_seed(work, selected)
                self.assertFalse((work / "mobile-dependency-seed").exists())

    def test_existing_dependency_seed_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, work, selected = self.dependency_fixture(Path(temporary).resolve())
            target = work / "mobile-dependency-seed"
            target.mkdir()
            marker = target / "preserve"
            marker.write_text("existing owned state")
            with self.assertRaises(FileExistsError):
                runtime.prepare_mobile_dependency_seed(work, selected)
            self.assertEqual(marker.read_text(), "existing owned state")

    def test_pinned_shiny_and_metal_download_receipts_bind_both_checksums(self):
        values = [dict(Path=path, **fields) for path, fields in runtime.MOBILE_GRAPH_REQUIRED.items()]
        receipt = runtime.validate_mobile_dependency_download("\n".join(json.dumps(value) for value in values))
        self.assertEqual(receipt["modules"], runtime.MOBILE_GRAPH_REQUIRED)
        self.assertEqual(receipt["downloaded_module_count"], 2)

    def test_missing_old_or_ambiguous_metal_cache_receipt_cannot_pass(self):
        for change in ["missing", "version", "sum", "mod-sum", "error", "duplicate"]:
            with self.subTest(change=change):
                values = [dict(Path=path, **fields) for path, fields in runtime.MOBILE_GRAPH_REQUIRED.items()]
                if change == "missing":
                    values.pop()
                elif change == "duplicate":
                    values.append(copy.deepcopy(values[-1]))
                elif change == "error":
                    values[-1]["Error"] = "not downloaded"
                else:
                    field = {"version": "Version", "sum": "Sum", "mod-sum": "GoModSum"}[change]
                    values[-1][field] = "old-native-only-receipt"
                with self.assertRaises(RuntimeError):
                    runtime.validate_mobile_dependency_download("\n".join(json.dumps(value) for value in values))



    def generated_fixture(self, root):
        work, heart, mobile = root / "owned-work", root / "owned-heart", root / "pinned-mobile"
        for directory in [work, heart, mobile]:
            directory.mkdir()
        (heart / "preserve-native").write_bytes(b"unchanged native input")
        proof = Path(__file__).resolve().parents[2] / "docs/validation/20261118-t5-r15-runtime/44240654969"
        for path in runtime.MOBILE_BIND_SOURCES:
            target = mobile / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((proof / "dependency-source" / ("gomobile-" + Path(path).name)).read_bytes())
        module = dict(Path="golang.org/x/mobile", Version=runtime.MOBILE_VERSION,
                      Sum=runtime.MOBILE_MODULE_SUM, GoModSum=runtime.MOBILE_MOD_SUM, Dir=str(mobile))
        source = proof / "unpacked/Pinkha-Native-Derived-Evidence/runtime/resolved-native-modules.log"
        records = launcher.module_records(source.read_text(encoding="utf8"))
        # This is a controller fixture. Only the machine-local root path changes;
        # all captured remote module/version/replacement data remains original.
        records[0]["Dir"] = str(heart)
        return work, heart, module, records

    def graph_fixture(self):
        heart, native, genproto, _ = module_inputs()
        fields = runtime.GENERATED_GRAPH_REQUIRED["git.sr.ht/~sbinet/gg"]
        gg = dict(Path=fields["effective_path"], Version=fields["effective_version"],
                  Sum=fields["sum"], GoModSum=fields["go_mod_sum"])
        rows = [dict(Path="gobind", Main=True), native, gg, genproto]
        graph = launcher.selected_graph(rows, heart)
        downloads = {
            value["effective_path"] + "@" + value["effective_version"]: dict(
                Path=value["effective_path"], Version=value["effective_version"],
                Sum=value["sum"], GoModSum=value["go_mod_sum"])
            for value in graph.values()
        }
        return heart, rows, graph, downloads

    def manifest_fixture(self, heart):
        return dict(Module={"Path": "gobind"}, Go="1.26.5",
                    Require=[dict(Path="example.org/dependency", Version="v1.2.3")],
                    Replace=[dict(Old={"Path": launcher.NATIVE_MODULE}, New={"Path": str(heart)})])

    def test_generated_seed_keeps_original_native_floors_and_exact_gomobile_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
            before = copy.deepcopy(rows)
            seed, receipt = runtime.generated_dependency_seed(
                work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
            self.assertEqual(rows, before)
            self.assertEqual(receipt["source_module_count"], 882)
            text = (seed / "go.mod").read_text()
            self.assertIn("git.sr.ht/~sbinet/gg v0.3.1", text)
            self.assertNotIn("git.sr.ht/~sbinet/gg v0.6.0", text)
            self.assertIn("gonum.org/v1/gonum v0.17.0", text)
            self.assertIn("replace (", text)
            genproto = next(item for item in rows if item["Path"] == launcher.GENPROTO)
            self.assertIn(launcher.GENPROTO + " " + genproto["Version"] + " => "
                          + launcher.GENPROTO + " " + launcher.VERSION, text)
            self.assertEqual((heart / "preserve-native").read_bytes(), b"unchanged native input")

    def test_invalid_native_graph_or_changed_generator_is_rejected_before_seed_creation(self):
        for change in ["duplicate", "foreign-native", "foreign-local", "newline-path", "mobile", "genproto", "source"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
                if change == "duplicate":
                    rows.append(copy.deepcopy(rows[-1]))
                elif change == "foreign-native":
                    rows[0]["Dir"] = str(heart.parent / "other")
                elif change == "foreign-local":
                    rows[1]["Replace"] = dict(Path="../foreign", Dir="/foreign")
                elif change == "newline-path":
                    rows[1]["Path"] += "\nreplace injected"
                elif change == "mobile":
                    next(item for item in rows if item["Path"] == "golang.org/x/mobile")["Version"] = "v1.2.3"
                elif change == "genproto":
                    next(item for item in rows if item["Path"] == launcher.GENPROTO)["Replace"]["Sum"] = "h1:wrong"
                else:
                    (Path(mobile["Dir"]) / "cmd/gomobile/bind.go").write_bytes(b"changed pinned generator")
                with self.assertRaises(RuntimeError):
                    runtime.generated_dependency_seed(
                        work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
                self.assertFalse((work / "generated-dependency-seed").exists())

    def test_selected_graph_and_authoritative_expanded_dependency_hashes_are_bound(self):
        _, _, graph, downloads = self.graph_fixture()
        receipt = runtime.validate_generated_seed_graph(graph, downloads)
        self.assertEqual(receipt["selected_module_count"], 2)
        self.assertEqual(receipt["downloaded_module_count"], 2)

    def test_changed_or_missing_selected_and_downloaded_hashes_are_rejected(self):
        for field in ["sum", "go_mod_sum", "effective_version", "effective_path"]:
            with self.subTest(field=field):
                _, _, graph, downloads = self.graph_fixture()
                graph["git.sr.ht/~sbinet/gg"][field] = "changed"
                with self.assertRaises(RuntimeError):
                    runtime.validate_generated_seed_graph(graph, downloads)
        for field in ["Sum", "GoModSum"]:
            with self.subTest(download_field=field):
                _, _, graph, downloads = self.graph_fixture()
                downloads["git.sr.ht/~sbinet/gg@v0.6.0"].pop(field)
                with self.assertRaises(RuntimeError):
                    launcher.validate_downloaded_graph(graph, downloads)

    def test_post_tidy_graph_allows_pruning_but_no_selection_drift(self):
        _, _, expected, _ = self.graph_fixture()
        only_genproto = {launcher.GENPROTO: expected[launcher.GENPROTO]}
        result = launcher.validate_seeded_graph(only_genproto, expected)
        self.assertEqual(result["pruned_seed_modules"], ["git.sr.ht/~sbinet/gg"])
        for field in ["version", "replaced", "effective_path", "effective_version", "sum", "go_mod_sum", "new-module"]:
            with self.subTest(field=field):
                actual = copy.deepcopy(only_genproto)
                if field == "new-module":
                    actual["unexpected.org/new"] = copy.deepcopy(actual[launcher.GENPROTO])
                elif field == "replaced":
                    actual[launcher.GENPROTO][field] = False
                else:
                    actual[launcher.GENPROTO][field] = "changed"
                with self.assertRaises(RuntimeError):
                    launcher.validate_seeded_graph(actual, expected)

    def test_selected_graph_cannot_hide_duplicate_or_foreign_local_modules(self):
        for change in ["duplicate", "foreign-native", "missing-main", "other-main", "sum", "mod-sum"]:
            with self.subTest(change=change):
                heart, rows, _, _ = self.graph_fixture()
                if change == "duplicate":
                    rows.append(copy.deepcopy(rows[-1]))
                elif change == "foreign-native":
                    rows[1]["Replace"]["Dir"] = str(heart.parent / "different-heart")
                elif change == "missing-main":
                    rows.pop(0)
                elif change == "other-main":
                    rows[0]["Path"] = "other-main"
                else:
                    rows[2].pop("Sum" if change == "sum" else "GoModSum")
                with self.assertRaises(RuntimeError):
                    launcher.selected_graph(rows, heart)

    def test_failed_conflicting_or_unverified_download_streams_are_rejected(self):
        _, _, _, downloads = self.graph_fixture()
        original = list(downloads.values())
        for change in ["error", "conflict", "missing-sum", "bad-mod-sum"]:
            with self.subTest(change=change):
                rows = copy.deepcopy(original)
                if change == "error":
                    rows[0]["Error"] = "not downloaded"
                elif change == "conflict":
                    rows.append(dict(rows[0], Sum=launcher.MODULE_SUM))
                elif change == "missing-sum":
                    rows[0].pop("Sum")
                else:
                    rows[0]["GoModSum"] = "h1:not-a-real-hash"
                with self.assertRaises(RuntimeError):
                    launcher.downloaded_modules("\n".join(json.dumps(item) for item in rows))

    def test_actual_pre_tidy_manifest_is_checked_before_the_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manifest = self.manifest_fixture(root / "heart")
            contract = dict(before_tidy_manifest=launcher.canonical_manifest(manifest),
                            input_native_graph_sha256="a" * 64)
            (root / "go.mod").write_text("module gobind\n\ngo 1.26.5\n", encoding="utf8")
            env = dict(GOWORK="off", GOPROXY="off")
            for change in ["unchanged", "require", "replace", "go"]:
                with self.subTest(change=change):
                    actual = copy.deepcopy(manifest)
                    if change == "require":
                        actual["Require"][0]["Version"] = "v9.9.9"
                    elif change == "replace":
                        actual["Replace"][0]["New"]["Path"] = "/different/heart"
                    elif change == "go":
                        actual["Go"] = "1.25.6"
                    response = subprocess.CompletedProcess([], 0, stdout=json.dumps(actual), stderr="")
                    with mock.patch.object(launcher.subprocess, "run", return_value=response):
                        if change == "unchanged":
                            result = launcher.audit_initial_manifest(root / "go", env, root, contract)
                            self.assertEqual(result["status"], "EXACT_GENERATED_INPUT")
                        else:
                            with self.assertRaises(RuntimeError):
                                launcher.audit_initial_manifest(root / "go", env, root, contract)

    def test_seed_contract_is_owned_hashed_and_tied_to_native_identity(self):
        for change in ["unchanged", "outside", "hash", "native", "schema"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                work, heart = root / "work", root / "heart"
                work.mkdir()
                generated = work / "gomobile-tmp"
                generated.mkdir()
                _, _, graph, _ = self.graph_fixture()
                data = dict(schema="pinkha-generated-module-graph-v1", native_directory=str(heart),
                            selected_dependencies=graph,
                            before_tidy_manifest=self.manifest_fixture(heart))
                if change == "native":
                    data["native_directory"] = str(root / "foreign")
                elif change == "schema":
                    data["schema"] = "unrelated"
                path = (root if change == "outside" else work) / "contract.json"
                path.write_text(json.dumps(data), encoding="utf8")
                expected = hashlib.sha256(path.read_bytes()).hexdigest()
                if change == "hash":
                    expected = "0" * 64
                if change == "unchanged":
                    self.assertEqual(launcher.load_seed_contract(path, expected, heart, generated), data)
                else:
                    with self.assertRaises(RuntimeError):
                        launcher.load_seed_contract(path, expected, heart, generated)


    def test_generated_hydration_copy_preserves_exact_original_bind_input(self):
        with tempfile.TemporaryDirectory() as directory:
            work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
            seed, receipt = runtime.generated_dependency_seed(work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
            original = (seed / "go.mod").read_bytes()
            hydrated = runtime.prepare_generated_hydration(work, seed, receipt["initial_go_mod_sha256"])
            self.assertNotEqual(seed, hydrated)
            self.assertEqual((hydrated / "go.mod").read_bytes(), original)
            # Emulate the observed Go metadata operation, not a native build.
            (hydrated / "go.mod").write_text("mutated disposable hydration declaration")
            self.assertEqual((seed / "go.mod").read_bytes(), original)
            self.assertEqual(runtime.digest(seed / "go.mod"), receipt["initial_go_mod_sha256"])
            self.assertEqual((heart / "preserve-native").read_bytes(), b"unchanged native input")

    def test_generated_hydration_requires_original_bytes_and_fresh_owned_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
            seed, receipt = runtime.generated_dependency_seed(work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
            for location, expected in [(work.parent, receipt["initial_go_mod_sha256"]), (work, "0" * 64)]:
                with self.subTest(location=location, expected=expected), self.assertRaises(RuntimeError):
                    runtime.prepare_generated_hydration(location, seed, expected)
            runtime.prepare_generated_hydration(work, seed, receipt["initial_go_mod_sha256"])
            with self.assertRaises(FileExistsError):
                runtime.prepare_generated_hydration(work, seed, receipt["initial_go_mod_sha256"])

    def hydration_manifests(self):
        original = dict(Module={"Path": "gobind"}, Go="1.26.5", Exclude=None, Retract=None,
                        Replace=[dict(Old={"Path": "original.example/dependency", "Version": "v1.0.0"},
                                      New={"Path": "reviewed.example/fork", "Version": "v1.0.1"})],
                        Require=[dict(Path="example.test/a", Version="v1.0.0"),
                                 dict(Path="example.test/b", Version="v1.0.0")])
        hydrated = copy.deepcopy(original)
        hydrated["Require"][1]["Version"] = "v1.1.0"
        hydrated["Require"].append(dict(Path="example.test/c", Version="v1.2.0", Indirect=True))
        # These versions model already independently checksum-verified selection.
        graph = {path: dict(version=version) for path, version in
                 [("example.test/a", "v1.0.0"), ("example.test/b", "v1.1.0"), ("example.test/c", "v1.2.0")]}
        return original, hydrated, graph

    def test_generated_hydration_records_only_selected_mvs_and_indirect_additions(self):
        original, hydrated, graph = self.hydration_manifests()
        before, after = copy.deepcopy(original), copy.deepcopy(hydrated)
        receipt = runtime.validate_generated_hydration_manifest(original, hydrated, graph)
        self.assertEqual(original, before)
        self.assertEqual(hydrated, after)
        self.assertEqual(receipt["selected_version_updates"], [dict(path="example.test/b", original="v1.0.0", hydrated="v1.1.0")])
        self.assertEqual(receipt["selected_indirect_additions"], [dict(path="example.test/c", hydrated="v1.2.0")])
        self.assertEqual((receipt["original_requirements"], receipt["hydrated_requirements"]), (2, 3))
        self.assertTrue(receipt["original_non_require_declarations_preserved"])

    def test_generated_hydration_rejects_other_declaration_or_selection_changes(self):
        changes = {
            "module": lambda value: value.update(Module={"Path": "other"}),
            "toolchain": lambda value: value.update(Toolchain="go1.27.0"),
            "go": lambda value: value.update(Go="1.27.0"),
            "replace": lambda value: value["Replace"][0]["New"].update(Version="v2.0.0"),
            "exclude": lambda value: value.update(Exclude=[dict(Path="example.test/a", Version="v1.0.0")]),
            "removed-original": lambda value: value["Require"].pop(0),
            "version-drift": lambda value: value["Require"][1].update(Version="v1.0.9"),
            "directness": lambda value: value["Require"][0].update(Indirect=True),
            "new-direct": lambda value: value["Require"][2].update(Indirect=False),
            "unselected-module": lambda value: value["Require"].append(dict(Path="unknown.test/module", Version="v1.0.0", Indirect=True)),
            "duplicate": lambda value: value["Require"].append(copy.deepcopy(value["Require"][0])),
            "unknown-require-field": lambda value: value["Require"][0].update(Changed=True),
            "invalid-indirect": lambda value: value["Require"][2].update(Indirect=1),
        }
        for name, change in changes.items():
            with self.subTest(case=name):
                original, hydrated, graph = self.hydration_manifests()
                change(hydrated)
                with self.assertRaises(RuntimeError):
                    runtime.validate_generated_hydration_manifest(original, hydrated, graph)


if __name__ == "__main__":
    unittest.main(verbosity=2)
