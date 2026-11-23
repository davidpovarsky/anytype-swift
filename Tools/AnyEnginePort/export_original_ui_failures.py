#!/usr/bin/env python3
"""Export selected original Any UI failure attachments without building or testing."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import stat
import subprocess
import zipfile

RUN = 45087682296
ARTIFACT = 14782745448
SOURCE = "7293e4fd0bcabdcdb643d5768b777b8e87ff1b73"
ARCHIVE_SHA = "6625e363c7cd9e4c256dfc116073687228db7a0564ae6f2aed8213eca089616b"
REPOSITORY = "davidpovarsky/anytype-swift"
BUNDLES = ("native-ui-continuation.xcresult", "archive-roundtrip.xcresult")
METHODS = {
    "testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen": "hanlin",
    "testHierarchyDragIntoFolderPersistsAfterColdReopen": "hierarchy-drag",
    "testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType": "backup-control",
    "testSourceDragIntoNativeEditorPreservesTargetAndColdReopens": "source-drag",
    "testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies": "files",
}

def require(value, reason):
    if not value:
        raise ValueError(reason)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path], timeout=60))

def safe(value):
    p = PurePosixPath(value)
    require(value and not p.is_absolute() and ".." not in p.parts and "\\" not in value, "Unsafe original archive path")
    return p

def main():
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "Wrong evidence repository")
    require(os.environ.get("SOURCE_RUN_ID") == str(RUN), "This exporter is pinned to one original failed run")
    root = Path("build/original-any-ui-export").resolve()
    root.mkdir(parents=True, exist_ok=False)
    output = root / "selected"
    output.mkdir()
    receipt = dict(status="NOT_RUN", source_run_id=RUN, source_commit=SOURCE,
                   artifact_id=ARTIFACT, archive_sha256=ARCHIVE_SHA,
                   scope="Original result extraction only; no build, simulator, or product test execution",
                   product_tests_executed=0, selected=[], cases=[], commands=[])
    def save():
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    try:
        run = api("repos/" + REPOSITORY + "/actions/runs/" + str(RUN))
        require(run["id"] == RUN and run["head_sha"] == SOURCE and run["status"] == "completed"
                and run["conclusion"] == "failure" and run["run_attempt"] == 1
                and run["repository"]["full_name"] == REPOSITORY, "Original run identity changed")
        artifact = api("repos/" + REPOSITORY + "/actions/artifacts/" + str(ARTIFACT))
        require(artifact["id"] == ARTIFACT and artifact["digest"] == "sha256:" + ARCHIVE_SHA
                and artifact["size_in_bytes"] == 215789455 and artifact["expired"] is False,
                "Original artifact identity changed")
        for name, value in (("original-run.json", run), ("original-artifact.json", artifact)):
            (output / name).write_text(json.dumps(value, indent=2) + "\n")
        archive = root / "original.zip"
        with archive.open("wb") as stream:
            subprocess.run(["gh", "api", "repos/" + REPOSITORY + "/actions/artifacts/" + str(ARTIFACT) + "/zip"],
                           stdout=stream, check=True, timeout=240)
        require(digest(archive) == ARCHIVE_SHA, "Original archive bytes changed")
        source = root / "source"
        source.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            require(len(zipped.infolist()) <= 20000, "Unexpected original archive entry count")
            total = 0
            for member in zipped.infolist():
                relative = safe(member.filename.rstrip("/"))
                if relative.parts[0] not in BUNDLES:
                    continue
                require(not stat.S_ISLNK(member.external_attr >> 16), "Symlink in original result bundle")
                total += member.file_size
                require(member.file_size <= 512 * 1024**2 and total <= 2 * 1024**3, "Original results exceeded export bound")
                path = source.joinpath(*relative.parts)
                if member.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with zipped.open(member) as incoming, path.open("xb") as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
        selected_bytes = 0
        for bundle in BUNDLES:
            original = source / bundle
            require((original / "Info.plist").is_file(), "Exact original result bundle is missing")
            exported = root / (bundle + "-attachments")
            command = ["xcrun", "xcresulttool", "export", "attachments", "--path", str(original),
                       "--output-path", str(exported)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            receipt["commands"].append(dict(argv=command, exit_code=result.returncode,
                                            stdout=result.stdout[-2000:], stderr=result.stderr[-2000:]))
            require(result.returncode == 0, "Original xcresult attachment export failed")
            manifest = json.loads((exported / "manifest.json").read_text(encoding="utf-8-sig"))
            require(isinstance(manifest, list), "Unexpected original attachment manifest")
            for case in manifest:
                identifier = case.get("testIdentifier", "").removesuffix("()")
                selected_method = next((m for m in METHODS if identifier.endswith("/" + m)), None)
                if selected_method is None:
                    continue
                scope = METHODS[selected_method]
                case_record = dict(bundle=bundle, test_identifier=identifier, scope=scope, attachments=[])
                for attachment in case.get("attachments", []):
                    name = attachment.get("suggestedHumanReadableName", "")
                    filename = attachment.get("exportedFileName", "")
                    require(isinstance(name, str) and len(name) <= 2048, "Invalid original attachment name")
                    relative = safe(filename)
                    path = exported.joinpath(*relative.parts)
                    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(exported.resolve()),
                            "Original exported attachment escaped its directory")
                    extension = path.suffix.lower()
                    named = ((scope == "backup-control" and name.startswith("native-backup-acknowledgement-control-frames"))
                             or (scope == "source-drag" and name.startswith(("native-source-drag-live-geometry",
                                                                          "native-source-drag-before-gesture")))
                             or (scope == "files" and name.startswith("ARCHIVE_ROUNDTRIP_canonical-source-")
                                 and "_export_directory_NOT_READY_private_" in name))
                    failure = (scope in ("hanlin", "hierarchy-drag", "source-drag")
                               and attachment.get("isAssociatedWithFailure") is True)
                    # Never publish recordings or the backup screen/tree that may contain its phrase.
                    allowed_type = extension in (".png", ".jpg", ".jpeg", ".txt", ".json", ".log")
                    keep = (named or failure) and allowed_type
                    metadata = dict(name=name, exported_file=filename, bytes=path.stat().st_size,
                                    failure_associated=attachment.get("isAssociatedWithFailure"),
                                    selected=keep)
                    case_record["attachments"].append(metadata)
                    if not keep:
                        continue
                    require(path.stat().st_size <= 20 * 1024**2, "Selected attachment exceeded its bound")
                    selected_bytes += path.stat().st_size
                    require(selected_bytes <= 120 * 1024**2, "Selected attachment set exceeded its bound")
                    destination = output / "attachments" / scope / path.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        require(digest(destination) == digest(path), "Conflicting original attachment filename")
                    else:
                        shutil.copyfile(path, destination)
                    receipt["selected"].append(dict(scope=scope, test_identifier=identifier, name=name,
                                                     path=destination.relative_to(output).as_posix(),
                                                     sha256=digest(destination), bytes=destination.stat().st_size))
                receipt["cases"].append(case_record)
        require({row["scope"] for row in receipt["cases"]} == set(METHODS.values()), "Original failed cases were missing from attachment export")
        receipt.update(status="EXPORTED_ORIGINAL_FAILURE_ATTACHMENTS_NOT_ACCEPTANCE", selected_bytes=selected_bytes,
                       original_archive_verified=True, no_product_execution=True,
                       no_backup_phrase_screen_or_tree_selected=True)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        save()
        print(json.dumps({k:receipt[k] for k in ("status", "scope", "product_tests_executed")}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
