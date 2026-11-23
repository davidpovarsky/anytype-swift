"""Preserve successful native build bytes before any admission or test selection.

This archive is evidence only. It does not authorize build reuse or imply that
cached entries, signatures, runtime identity, or any product test have passed.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import tarfile


STATUS = "OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


class HashingReader:
    def __init__(self, source):
        self.source = source
        self.hasher = hashlib.sha256()

    def read(self, size):
        data = self.source.read(size)
        self.hasher.update(data)
        return data


def capture(derived, evidence, *, source_sha, run_id, run_attempt, build_flags, scope="sdk06"):
    derived, evidence = Path(derived).resolve(), Path(evidence).resolve()
    products = derived / "Build/Products"
    require(products.is_dir() and not products.is_symlink(), "Original build products are missing")
    require(not evidence.is_relative_to(products), "Product evidence cannot be inside the product tree")
    require(re.fullmatch(r"[0-9a-f]{40}", source_sha or "")
            and str(run_id).isascii() and str(run_id).isdigit() and int(run_id) > 0
            and str(run_attempt).isascii() and str(run_attempt).isdigit() and int(run_attempt) > 0,
            "Actual build source and run identity are required")
    require(scope in {"sdk06", "coherent-native", "coherent-ui"}, "Unknown early product evidence scope")
    target = evidence / (scope + "-early-products")
    require(not target.exists() and not target.is_symlink(), "Refuse stale early product evidence")
    target.mkdir(parents=True)
    receipt = dict(status="CAPTURING", capture_phase="AFTER_BUILD_BEFORE_ADMISSION",
                   source_sha=source_sha, run_id=str(run_id), run_attempt=str(run_attempt),
                   build_flags=list(build_flags), captured_at=datetime.now(timezone.utc).isoformat(),
                   build_reuse_enabled=False, every_entry_build_origin_verified=False,
                   native_acceptance_reused=False, ui_acceptance_reused=False,
                   symlink_targets_require_separate_dependency_review=True, products={})
    partial = target / "BuildProducts.tar.gz.partial"
    archive = target / "BuildProducts.tar.gz"
    try:
        paths = [products, *sorted(products.rglob("*"))]
        require(any(path.is_file() and not path.is_symlink() and path.parent == products
                    and path.suffix == ".xctestrun" and not path.name.startswith("UI27-")
                    for path in paths), "Original Xcode test configuration is missing")
        source_inputs = derived / "Build/PinkhaSourceInputs.json"
        if source_inputs.exists() or source_inputs.is_symlink():
            paths.append(source_inputs)
        # tar keeps executable modes and links; it never follows a product link.
        # Stale cache entries remain observable, never silently qualified as a build.
        with tarfile.open(partial, mode="x:gz", compresslevel=1, dereference=False) as packed:
            for path in paths:
                name = path.relative_to(derived).as_posix()
                before = path.lstat()
                require(stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode)
                        or stat.S_ISLNK(before.st_mode), "Special build product cannot be archived: " + name)
                member = packed.gettarinfo(str(path), arcname=name)
                row = dict(mode=stat.S_IMODE(before.st_mode))
                if member.isfile():
                    with path.open("rb") as source:
                        reader = HashingReader(source)
                        packed.addfile(member, reader)
                    after = path.lstat()
                    require((before.st_size, before.st_mtime_ns, before.st_ino, before.st_dev)
                            == (after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev),
                            "Build product changed during capture: " + name)
                    row.update(kind="file", bytes=member.size, sha256=reader.hasher.hexdigest())
                else:
                    packed.addfile(member)
                    if member.issym():
                        require(path.readlink().as_posix() == member.linkname,
                                "Build product link changed during capture: " + name)
                        row.update(kind="symlink", target=member.linkname)
                    elif member.islnk():
                        require(member.linkname in receipt["products"], "Missing prior hard-link archive target")
                        row.update(kind="hardlink", target=member.linkname)
                    else:
                        require(member.isdir(), "Unsupported build product archive entry: " + name)
                        row.update(kind="directory")
                receipt["products"][name] = row
        partial.rename(archive)
        receipt.update(status=STATUS, archive_path=archive.relative_to(evidence).as_posix(),
                       archive_sha256=digest(archive), archive_bytes=archive.stat().st_size,
                       source_inputs_present="Build/PinkhaSourceInputs.json" in receipt["products"])
    except BaseException as error:
        receipt.update(status="CAPTURE_FAILED_NO_BUILD_REUSE_ALLOWED",
                       error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (target / "manifest.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    manifest = target / "manifest.json"
    return {key: receipt[key] for key in ("status", "capture_phase", "archive_path", "archive_sha256",
                                         "archive_bytes", "build_reuse_enabled")} | {
        "manifest_path": manifest.relative_to(evidence).as_posix(),
        "manifest_sha256": digest(manifest), "entries": len(receipt["products"])}
