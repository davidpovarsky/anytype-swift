"""Verify authentic committed generated SDK sources without granting ABI acceptance."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

COMPLETE = "4fd99f19b0ec361ba84ac4b2822cae10c6818f99"
PREIMAGE = "7ea121d46a48e00cbcb02e91621c75947c57f6a4"
ORIGINAL = "997e285617d57b31c4205976f01019819fa29a03"
POSTIMAGE = "81115fe82b4ffbedd49ca69a573d85acafa67650"
LOCAL_ANNOTATION_BASE = "bc36e8ecd803c0c4f9c856ed9a5384e074432952"
LOCAL_ANNOTATION_SOURCE = "cbe25cb467f989a1d40ed564d833616346a7d9b6"
LOCAL_ANNOTATION_FILES = (
    "Modules/Services/Sources/Services/Auth/AuthMiddleService+OriginalLocalAnnotation.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationJournal.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationMaterialization.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationNativeBody.swift",
    "OriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift",
)
SCOPES = (
    "Modules/ProtobufMessages/Sources/Protocol",
    "Modules/ProtobufMessages/Sources/Generated/CommandsInvocation",
    "Modules/ProtobufMessages/Sources/Generated/service+invocation.swift",
    "Modules/ProtobufMessages/Sources/Loc/Generated/Error+Localization.swift",
    "Modules/Services/Sources/Generated/BundledPropertyKey.swift",
    "Modules/Services/Sources/Generated/BundledPropertiesValueProvider.swift",
    "Modules/Services/Sources/Generated/BundledPropertyKey+SystemKeys.swift",
    "Modules/Services/Sources/Generated/BundledPropertyKey+internalKeys.swift",
    "Modules/Services/Sources/Generated/ObjectTypeUniqueKey+Bundled.swift",
    "Dependencies/Middleware/protobuf",
    "Dependencies/Middleware/genmodels",
    "Dependencies/Middleware/json",
)
DOCUMENTS = {
    "source_adoption": "Tools/OriginalEditor/GeneratedImport/SOURCE_ADOPTION.json",
    "generated_index": "Tools/OriginalEditor/GeneratedImport/GENERATED_OUTPUT_INDEX.json",
    "generation_handoff": "Tools/OriginalEditor/GeneratedImport/ACTUAL_GENERATED_UNION_HANDOFF.json",
}
PRODUCTS = ("Anytype/Sources", "Anytype/Resources", "Modules",
            "OriginalEditorFramework", "Dependencies/Middleware")


def require(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60)


def safe_path(root, name):
    path = PurePosixPath(name)
    require(bool(name) and str(path) == name and not path.is_absolute()
            and ".." not in path.parts and "\0" not in name and "\\" not in name,
            "Generated source path is not canonical")
    result = Path(root).joinpath(*path.parts)
    require(result.resolve().is_relative_to(Path(root).resolve()),
            "Generated source escapes its checkout")
    for item in [result, *result.parents]:
        require(not item.is_symlink(), "Generated source contains a symlink")
        if item == Path(root):
            break
    return result


def row(path, name):
    require(path.is_file() and not path.is_symlink(), "Generated source is not a regular file")
    raw = path.read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def git_entries(root, revision):
    rows = {}
    for entry in git(root, "ls-tree", "-r", "-z", revision, "--", *SCOPES).split(b"\0"):
        if not entry:
            continue
        meta, name = entry.split(b"\t", 1)
        mode, kind, identity = meta.decode().split()
        name = name.decode()
        require(mode == "100644" and kind == "blob" and name not in rows,
                "Generated Git inventory has an unexpected object or mode")
        rows[name] = identity
    return rows


def working_entries(root):
    rows = {}
    for scope in SCOPES:
        source = safe_path(root, scope)
        require(source.exists(), "A committed generated scope is absent")
        paths = [source] if source.is_file() else source.rglob("*")
        for path in paths:
            require(not path.is_symlink(), "Generated scope contains an aliased member")
            if path.is_dir():
                continue
            name = path.relative_to(root).as_posix()
            require(name not in rows, "Generated source scope overlaps another scope")
            rows[name] = row(path, name)
    return [rows[name] for name in sorted(rows)]


def validate_documents(adoption, index, handoff):
    require(adoption["schema"] == "otzaria.complete-sdk-authentic-generated-source/1"
            and adoption["sdk_preimage_commit"] == PREIMAGE
            and adoption["original_generated_preimage_commit"] == ORIGINAL
            and adoption["complete_original_product_source"] == COMPLETE
            and adoption["scopes"] == list(SCOPES),
            "Original complete/generated source lineage differs")
    require(set(index) == {"native", "swift", "middleware"}
            and [len(index[family]) for family in ("native", "swift", "middleware")] == [11, 696, 37],
            "Authentic generated family inventory differs")
    before, after = adoption["before"], adoption["after"]
    expected = sorted(index["swift"] + index["middleware"], key=lambda item: item["path"])
    require(before == sorted(before, key=lambda item: item["path"])
            and len(before) == len({item["path"] for item in before}) == 695
            and after == expected
            and len(after) == len({item["path"] for item in after}) == 733,
            "Complete generated preimage/postimage inventory differs")
    require(all(any(item["path"] == scope or item["path"].startswith(scope + "/")
                    for scope in SCOPES) for item in before + after),
            "Generated output is outside the original SDK scopes")
    before_by = {item["path"]: item for item in before}
    require(set(before_by) <= {item["path"] for item in after},
            "Original generated source was removed")
    changes = [{"path": item["path"], "before": before_by.get(item["path"]), "after": item}
               for item in after if before_by.get(item["path"]) != item]
    require(changes == adoption["actual_changed_paths"] and len(changes) == 41
            and sum(item["before"] is None for item in changes) == 38,
            "Exact generated source delta differs")
    require(adoption["generation_run"] == handoff["run_id"] == 45261979047
            and adoption["generation_source"] == handoff["head_sha"]
                == "af96f761efe2cb4d92f5296fec85a152fd3aef17"
            and handoff["generated_native_tree"] == "995327648a4e4523c37208251ba54b47bccb2ab4"
            and handoff["all_744_final_output_rows_equal_generated_index"] is True
            and handoff["native_afterimages"] == index["native"]
            and adoption["generator_invocations_in_this_adoption"] == 0
            and adoption["native_family_installed"] is False
            and adoption["lib_installed"] is False
            and adoption["complete_sdk_native_acceptance"] is False
            and adoption["host_native_acceptance"] is False,
            "Source adoption incorrectly changes producer provenance or acceptance")
    return before, after, changes


def verify_generated_source(root, profile):
    root = Path(root).resolve()
    binding = profile["generated_import_source"]
    require(binding["schema"] == "otzaria.committed-generated-sdk-binding/1"
            and binding["postimage_source"] == POSTIMAGE
            and binding["complete_source_base"] == COMPLETE,
            "Unreviewed generated source binding")
    documents = {}
    for role, relative in DOCUMENTS.items():
        expected = binding["documents"][role]
        require(expected["path"] == relative, "Generated provenance document path differs")
        path = safe_path(root, relative)
        actual = row(path, relative)
        require(actual["sha256"] == expected["sha256"]
                and actual["git_blob"] == git(root, "rev-parse", "HEAD:" + relative).decode().strip(),
                "Generated provenance document bytes differ")
        documents[role] = json.loads(path.read_bytes())
    before, after, changes = validate_documents(
        documents["source_adoption"], documents["generated_index"], documents["generation_handoff"])
    previous = {item["path"]: item["git_blob"] for item in before}
    require(git_entries(root, ORIGINAL) == previous and git_entries(root, PREIMAGE) == previous,
            "Original generated Git preimages differ")
    require(git_entries(root, "HEAD") == {item["path"]: item["git_blob"] for item in after},
            "Committed generated postimages differ")
    require(working_entries(root) == after, "Working generated postimages differ")
    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", POSTIMAGE, "HEAD"],
                   check=True, timeout=60)
    delta = git(root, "diff", "--name-only", PREIMAGE, POSTIMAGE, "--", *SCOPES).decode().splitlines()
    require(delta == [item["path"] for item in changes], "Committed generated delta is incomplete")
    # Keep the authentic generator adoption and its historical product trees
    # unchanged. The separately reviewed production lifecycle adds exactly six
    # original Swift files; no generated source or native ABI input is rewritten.
    generated_trees = {path: git(root, "rev-parse", POSTIMAGE + ":" + path).decode().strip()
                       for path in PRODUCTS}
    require(generated_trees == binding["composed_product_trees"]
            and generated_trees == {path: git(root, "rev-parse", LOCAL_ANNOTATION_BASE + ":" + path).decode().strip()
                                    for path in PRODUCTS}, "Original generated SDK product tree differs")
    reviewed_delta = git(root, "diff", "--name-status", LOCAL_ANNOTATION_BASE,
                         LOCAL_ANNOTATION_SOURCE, "--", *PRODUCTS).decode().splitlines()
    require(reviewed_delta == ["A\t" + path for path in LOCAL_ANNOTATION_FILES],
            "Reviewed local lifecycle is not the exact six additive Swift files")
    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", LOCAL_ANNOTATION_SOURCE, "HEAD"],
                   check=True, timeout=60)
    trees = {path: git(root, "rev-parse", "HEAD:" + path).decode().strip() for path in PRODUCTS}
    historical_trees = {path: git(root, "rev-parse", LOCAL_ANNOTATION_SOURCE + ":" + path).decode().strip()
                        for path in PRODUCTS}
    from additive_facade_source import observe as observe_additive_facade
    additive_facade = observe_additive_facade(root, profile, historical_trees)
    admitted_trees = additive_facade["reviewed_product_trees"] if additive_facade else historical_trees
    require(trees == admitted_trees, "Reviewed local annotation product tree differs")
    original = {path: git(root, "rev-parse", COMPLETE + ":" + path).decode().strip()
                for path in profile["original_trees"]}
    require(profile["original_trees"] == {path: trees[path] for path in profile["original_trees"]}
            and all(trees[path] == git(root, "rev-parse", COMPLETE + ":" + path).decode().strip()
                    for path in ("Anytype/Sources", "Anytype/Resources"))
            and trees["Dependencies/Middleware"] == generated_trees["Dependencies/Middleware"],
            "Local lifecycle changed original UI, resources or native middleware")
    subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", *PRODUCTS],
                   check=True, timeout=60)
    return {"schema": "otzaria.committed-generated-sdk-source-observation/1",
            "postimage_source": POSTIMAGE, "preimage_source": PREIMAGE,
            "reviewed_complete_source": COMPLETE,
            "reviewed_local_annotation_source": LOCAL_ANNOTATION_SOURCE,
            "local_annotation_source_delta": reviewed_delta,
            "generated_index_sha256": binding["documents"]["generated_index"]["sha256"],
            "source_adoption_sha256": binding["documents"]["source_adoption"]["sha256"],
            "composed_product_trees": trees, "original_complete_trees": original,
            "working_generated_files": len(after), "committed_generated_blobs": len(after),
            "changed_source_paths": len(changes), "generation_run": 45261979047,
            "generation_aggregate_result": "FAIL; original missing-SDK Swift failure preserved",
            "native_or_swift_qualification_granted": False,
            "lib_abi_qualification": "NOT_ASSESSED_BY_SOURCE_OBSERVATION",
            **({"annotation_exchange": additive_facade} if additive_facade else {})}
