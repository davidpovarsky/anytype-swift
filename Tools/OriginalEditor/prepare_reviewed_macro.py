"""Approve one reviewed compiler macro while retaining Xcode validation.

The record shape is a firsthand CI observation, not a stable public API.
Only the genuine Xcode build can establish whether Xcode accepted it.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import tempfile

REVISION = "597c2bb34af0c51331eb3b5e705f942d8ee20daa"
PACKAGE_URL = "https://github.com/ordo-one/equatable"
APPROVAL = {"packageIdentity": "equatable", "targetName": "EquatableMacros", "fingerprint": REVISION}
LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def verify_pin(lock):
    pins = [pin for pin in lock["pins"] if pin["identity"] == "equatable"]
    require(len(pins) == 1, "Missing or duplicate reviewed macro package pin")
    require(pins[0] == {
        "identity": "equatable", "kind": "remoteSourceControl", "location": PACKAGE_URL,
        "state": {"revision": REVISION, "version": "1.4.1"},
    }, "Unreviewed macro package URL, version, or revision")
    return pins[0]


def read_review(root):
    manifest = json.loads((root / "Tools/OriginalEditor/reviewed_equatable_macro.json").read_bytes())
    require(manifest["schema"] == 1 and manifest["repository"] == PACKAGE_URL
            and manifest["identity"] == APPROVAL["packageIdentity"]
            and manifest["revision"] == REVISION and manifest["version"] == "1.4.1"
            and manifest["target_name"] == APPROVAL["targetName"], "Unreviewed macro identity")
    rows = manifest["reviewed_files"]
    require(len(rows) == 18 and len({row["path"] for row in rows}) == 18,
            "Incomplete reviewed macro source closure")
    require(sum(row["path"].startswith("Sources/EquatableMacros/")
                and row["path"].endswith(".swift") for row in rows) == 17
            and sum(row["path"] == "Package.swift" for row in rows) == 1,
            "Unexpected reviewed macro inputs")
    source = root / "docs/pinkha/torah-integration/evidence/original-editor-equatable-macro-20261122/reviewed-source"
    for row in rows:
        path = PurePosixPath(row["path"])
        require(not path.is_absolute() and ".." not in path.parts, "Foreign reviewed source path")
        raw = (source / row["path"]).read_bytes()
        require(len(raw) == row["bytes"] and git_blob(raw) == row["git_blob"]
                and digest(raw) == row["sha256"], "Reviewed source bytes changed: " + row["path"])
    return manifest


def verify_archive(raw, manifest):
    require(0 < len(raw) <= 4_194_304, "Unbounded macro source archive")
    expected = {row["path"]: row for row in manifest["reviewed_files"]}
    files, roots, seen = {}, set(), set()
    expanded = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts and path.parts,
                    "Foreign macro archive path")
            roots.add(path.parts[0])
            require(len(roots) == 1, "Multiple macro archive roots")
            require(member.isdir() or member.isfile(), "Linked or special macro archive member")
            if member.isdir():
                continue
            require(len(path.parts) > 1, "Macro archive file outside package root")
            relative = str(PurePosixPath(*path.parts[1:]))
            require(relative not in seen, "Duplicate macro archive member")
            seen.add(relative)
            expanded += member.size
            require(expanded <= 8_388_608, "Unbounded expanded macro archive")
            if relative in expected or relative.startswith("Sources/EquatableMacros/"):
                require(relative in expected, "Additional unreviewed macro source")
                body = archive.extractfile(member).read()
                row = expected[relative]
                require(len(body) == row["bytes"] and git_blob(body) == row["git_blob"]
                        and digest(body) == row["sha256"], "Macro source differs: " + relative)
                files[relative] = row
    require(set(files) == set(expected), "Missing reviewed macro source")
    return files


def merge_approval(previous):
    entries = [] if previous is None else json.loads(previous)
    require(isinstance(entries, list), "Macro trust store is not an array")
    require(all(isinstance(item, dict) and all(isinstance(item.get(key), str)
                for key in APPROVAL) for item in entries), "Unrecognized macro trust entry")
    if any(all(item.get(key) == value for key, value in APPROVAL.items()) for item in entries):
        return previous, False
    if previous is None:
        after = (json.dumps([APPROVAL], indent=2, sort_keys=True) + "\n").encode()
    else:
        # Insert before the array's final delimiter: every existing byte,
        # including spacing and extra fields, survives in its original order.
        previous.decode("utf-8-sig")
        require(b"\x00" not in previous, "Unrecognized macro trust encoding")
        closing = previous.rfind(b"]")
        require(closing >= 0, "Missing macro trust array delimiter")
        addition = (b"," if entries else b"") + b"\n" + json.dumps(APPROVAL, sort_keys=True).encode() + b"\n"
        after = previous[:closing] + addition + previous[closing:]
        require(after[:closing] + after[closing + len(addition):] == previous,
                "Existing macro trust bytes changed")
    require(json.loads(after)[:-1] == entries, "Existing macro approvals changed")
    return after, True


def checked_target(home):
    home = Path(home).absolute()
    target = home / "Library/org.swift.swiftpm/security/macros.json"
    for path in (home, home / "Library", home / "Library/org.swift.swiftpm",
                 target.parent, target):
        require(not path.is_symlink(), "Aliased macro trust path")
    require(target.resolve().is_relative_to(home.resolve()), "Foreign macro trust path")
    require(not target.exists() or target.is_file(), "Macro trust store is not a file")
    return target


def current_bytes(path):
    return path.read_bytes() if path.exists() else None


def replace_owned(path, expected, desired):
    require(not path.is_symlink() and current_bytes(path) == expected,
            "Macro trust changed concurrently; refusing overwrite")
    if desired is None:
        path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".otzaria-macro-", dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(desired)
            stream.flush()
            os.fsync(stream.fileno())
        require(not path.is_symlink() and current_bytes(path) == expected,
                "Macro trust changed before atomic replace")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def prepare(root, evidence, home):
    require(platform.system() == "Darwin" and platform.machine() == "arm64",
            "Actual macro approval requires the owned Apple runner")
    from framework_profile import BRANCH, REPOSITORY, git
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY
            and os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH
            and os.environ.get("GITHUB_SHA") == git(root, "rev-parse", "HEAD"),
            "Foreign macro approval execution context")
    require(subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
            == "Xcode 27.0\nBuild version 27A266a", "Unreviewed Xcode macro trust format")
    pin = verify_pin(json.loads((root / LOCK).read_bytes()))
    manifest = read_review(root)
    evidence.mkdir(parents=True, exist_ok=False)
    archive_path = evidence / "reviewed-upstream-source.tar.gz"
    with archive_path.open("wb") as output, (evidence / "source-download.stderr.log").open("wb") as error:
        result = subprocess.run(["gh", "api", "/repos/ordo-one/equatable/tarball/" + REVISION],
                                stdout=output, stderr=error, timeout=90)
    require(result.returncode == 0, "Cannot retrieve the immutable reviewed macro source")
    archive = archive_path.read_bytes()
    verified = verify_archive(archive, manifest)
    target = checked_target(home)
    before = current_bytes(target)
    after, added = merge_approval(before)
    if before is not None:
        (evidence / "macros.before.json").write_bytes(before)
    (evidence / "macros.after.json").write_bytes(after)
    state = {
        "schema": 1, "run_id": os.environ["GITHUB_RUN_ID"], "head_sha": os.environ["GITHUB_SHA"],
        "target": str(target), "before_existed": before is not None, "added_by_this_run": added,
        "before_sha256": None if before is None else digest(before), "after_sha256": digest(after),
        "approval": APPROVAL,
    }
    # Preserve ownership before the trust-store mutation, including interruption.
    write_json(evidence / "owned-trust-state.json", state)
    if added:
        replace_owned(target, before, after)
    require(current_bytes(checked_target(home)) == after, "Actual macro trust afterimage differs")
    write_json(evidence / "macro-approval.json", {
        **state, "status": "EXACT_REVIEWED_MACRO_APPROVAL_PREPARED_XCODE_ACCEPTANCE_PENDING",
        "pin": pin, "reviewed_file_count": len(verified), "macro_swift_sources": 17,
        "source_archive_sha256": digest(archive), "source_archive_bytes": len(archive),
        "all_existing_approvals_preserved": True, "blanket_skip_flags_or_defaults_changed": False,
        "framework_builds": 0, "native_tests_executed": 0,
    })


def restore(evidence, home):
    state_path = evidence / "owned-trust-state.json"
    if not state_path.exists():
        return {"status": "NO_OWNED_MACRO_APPROVAL_TO_RESTORE"}
    state = json.loads(state_path.read_bytes())
    target = checked_target(home)
    require(state["schema"] == 1 and state["run_id"] == os.environ["GITHUB_RUN_ID"]
            and state["head_sha"] == os.environ["GITHUB_SHA"] and state["target"] == str(target)
            and state["approval"] == APPROVAL, "Foreign macro trust ownership record")
    if not state["added_by_this_run"]:
        result = {"status": "PREEXISTING_APPROVAL_NOT_CHANGED_BY_THIS_JOB", "wrote_trust_store": False}
    else:
        before = (evidence / "macros.before.json").read_bytes() if state["before_existed"] else None
        after = (evidence / "macros.after.json").read_bytes()
        require((None if before is None else digest(before)) == state["before_sha256"]
                and digest(after) == state["after_sha256"], "Macro restoration evidence changed")
        current = current_bytes(target)
        if current == before:
            result = {"status": "OWNED_APPROVAL_ALREADY_RESTORED", "wrote_trust_store": False}
        else:
            replace_owned(target, after, before)
            require(current_bytes(target) == before, "Macro restore afterimage differs")
            result = {"status": "EXACT_ORIGINAL_MACRO_TRUST_RESTORED", "wrote_trust_store": True}
    write_json(evidence / "macro-restoration.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    root, evidence = args.root.resolve(), args.evidence.resolve()
    require(evidence.is_relative_to(root / "build"), "Macro evidence outside owned build directory")
    if args.restore:
        print(json.dumps(restore(evidence, Path.home()), sort_keys=True))
    else:
        prepare(root, evidence, Path.home())
        print(json.dumps(json.loads((evidence / "macro-approval.json").read_bytes()), sort_keys=True))


if __name__ == "__main__":
    main()
