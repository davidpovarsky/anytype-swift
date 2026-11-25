"""Validate the exact committed and prepared source of a local MiniApps producer.

This independently reconstructs only a committed, explicitly reviewed generated
delta. All temporary Git objects/index data stay in an owned temporary directory;
the producer source, object store and worktree are read-only inputs.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import subprocess
import tempfile


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def valid_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def contained_file(root, name):
    require(isinstance(name, str) and name and Path(name).name == name
            and name not in {".", ".."} and "\n" not in name and "\r" not in name,
            "Producer evidence name escapes its original directory")
    path = Path(root) / name
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Missing or aliased original producer source evidence")
    return path


def git_object(root, *arguments, env=None):
    result = subprocess.run(["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false",
                             "-C", str(root), *arguments], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    require(result.returncode == 0, "Cannot read/reconstruct exact producer Git objects: "
            + result.stderr.decode("utf8", errors="replace")[-2000:])
    return result.stdout


def prepared_source_tree(identity, sdk_root, source_sha, source_tree, review_spec,
                         export_directory, consumer_root, object_env):
    """Admit only a separately committed review of the exact generated delta."""
    status = identity.get("git_status_porcelain", "")
    require(isinstance(status, str), "Invalid producer preparation status")
    fields = ("preparation_diff_name", "preparation_diff_sha256", "prepared_tree")
    if review_spec is None:
        require(status == "", "Dirty producer preparation requires a committed review")
        if any(key in identity for key in fields):
            require(all(key in identity for key in fields) and export_directory is not None,
                    "Incomplete producer preparation identity")
            patch = contained_file(export_directory, identity["preparation_diff_name"])
            require(patch.read_bytes() == b"" and digest(patch) == identity["preparation_diff_sha256"]
                    and identity["prepared_tree"] == source_tree,
                    "Prepared producer source requires a committed review")
        return source_tree
    require(isinstance(review_spec, dict) and set(review_spec) == {"path", "sha256"},
            "Producer preparation requires its exact committed review")
    name, expected = review_spec["path"], review_spec["sha256"]
    require(isinstance(name, str) and name.startswith("Tools/MiniApps/") and name.endswith(".json")
            and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
            and "\n" not in name and "\r" not in name and valid_digest(expected),
            "Invalid producer preparation review path or digest")
    consumer_root = Path(consumer_root).resolve(strict=True)
    review_path = consumer_root / name
    require(review_path.is_file() and not review_path.is_symlink()
            and review_path.resolve(strict=True).is_relative_to(consumer_root)
            and digest(review_path) == expected, "Producer preparation review bytes differ")
    committed = git_object(consumer_root, "show", "HEAD:" + name)
    require(committed == review_path.read_bytes(),
            "Producer preparation review is not the exact committed file")
    review = json.loads(committed)
    require(review.get("schema") == "miniapps.producer-preparation-review/1"
            and review.get("producer_sha") == source_sha
            and review.get("source_tree") == source_tree
            and review.get("prepared_tree") == identity.get("prepared_tree"),
            "Producer preparation review is bound to different source trees")
    require(review.get("git_status_porcelain") == status and status,
            "Producer preparation status differs from its review")
    require(export_directory is not None, "Producer preparation export is absent")
    specification = review.get("patch")
    require(isinstance(specification, dict) and set(specification) == {"name", "bytes", "sha256"}
            and specification.get("name") == identity.get("preparation_diff_name")
            and valid_digest(specification.get("sha256"))
            and specification["sha256"] == identity.get("preparation_diff_sha256"),
            "Producer preparation patch identity differs")
    patch = contained_file(export_directory, specification["name"])
    require(type(specification["bytes"]) is int and specification["bytes"] > 0
            and patch.stat().st_size == specification["bytes"]
            and digest(patch) == specification["sha256"], "Producer preparation patch bytes differ")
    changes = review.get("changes")
    require(isinstance(changes, list) and changes, "Producer preparation has no reviewed changes")
    names = []
    for change in changes:
        require(isinstance(change, dict), "Invalid producer preparation change")
        path = change.get("path")
        require(isinstance(path, str) and path and not PurePosixPath(path).is_absolute()
                and ".." not in PurePosixPath(path).parts and "\n" not in path and "\r" not in path
                and "\t" not in path and change.get("status") == "M"
                and isinstance(change.get("reason"), str) and change["reason"].strip(),
                "Producer preparation only admits reviewed regular-file modifications")
        names.append(path)
    require(len(names) == len(set(names)), "Duplicate producer preparation change")
    require(status == "".join(" M " + path + "\n" for path in sorted(names)),
            "Producer preparation contains an unreviewed index or working-tree change")
    git_object(sdk_root, "read-tree", source_sha, env=object_env)
    git_object(sdk_root, "apply", "--cached", "--binary", "--whitespace=nowarn",
               str(patch), env=object_env)
    prepared = git_object(sdk_root, "write-tree", env=object_env).decode().strip()
    require(prepared == review["prepared_tree"],
            "Reconstructed producer preparation tree differs from the reviewed tree")
    raw = git_object(sdk_root, "diff-tree", "--no-commit-id", "--name-status", "-r", "-z",
                     "--no-renames", source_tree, prepared, env=object_env).decode().split("\0")
    require(raw[-1] == "" and len(raw) % 2 == 1, "Invalid prepared source tree delta")
    actual = list(zip(raw[0:-1:2], raw[1:-1:2]))
    require(actual == [("M", name) for name in sorted(names)],
            "Prepared source tree contains unreviewed changes")
    for change in changes:
        for phase, tree in (("before", source_tree), ("after", prepared)):
            entry = git_object(sdk_root, "ls-tree", "-z", tree, "--", change["path"], env=object_env)
            require(entry.endswith(b"\0") and entry.count(b"\0") == 1,
                    "Prepared source file is absent")
            attributes, path = entry[:-1].split(b"\t", 1)
            mode, kind, blob = attributes.decode().split()
            require(path.decode() == change["path"] and kind == "blob" and mode in ("100644", "100755"),
                    "Producer preparation cannot replace a regular file with another kind")
            content = git_object(sdk_root, "cat-file", "blob", blob, env=object_env)
            proof = {"mode": mode, "blob": blob, "bytes": len(content),
                     "sha256": hashlib.sha256(content).hexdigest()}
            require(change.get(phase) == proof, "Producer preparation " + phase + " object differs: " + change["path"])
        require(change["before"]["mode"] == change["after"]["mode"],
                "Producer preparation may not change file permissions")
    return prepared
def validate_source_identity(identity, sdk_root, source_sha, *, review_spec=None,
                             export_directory=None, consumer_root=None):
    require(isinstance(identity, dict) and identity.get("commit") == source_sha
            and isinstance(source_sha, str) and re.fullmatch(r"[0-9a-f]{40}", source_sha),
            "Local producer source identity differs from the consumer SDK")
    sdk_root = Path(sdk_root)
    require(sdk_root.is_absolute() and sdk_root.resolve(strict=True) == sdk_root
            and git_object(sdk_root, "rev-parse", "--show-toplevel").decode().strip() == str(sdk_root),
            "Producer repository must be its actual canonical source root")
    tree = git_object(sdk_root, "rev-parse", source_sha + "^{tree}").decode().strip()
    require(identity.get("tree") == tree, "Producer source tree differs from its immutable commit")
    objects_name = git_object(sdk_root, "rev-parse", "--git-path", "objects").decode().strip()
    objects = (sdk_root / objects_name).resolve()
    require(objects.is_dir(), "Producer Git object store is missing")
    with tempfile.TemporaryDirectory(prefix="miniapps-prepared-source-") as folder:
        private = Path(folder)
        (private / "objects").mkdir()
        environment = dict(os.environ, GIT_INDEX_FILE=str(private / "index"),
                           GIT_OBJECT_DIRECTORY=str(private / "objects"),
                           GIT_ALTERNATE_OBJECT_DIRECTORIES=str(objects),
                           GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")
        admitted = prepared_source_tree(identity, sdk_root, source_sha, tree, review_spec,
            export_directory, consumer_root, environment)
        files = identity.get("tracked_file_sha256")
        require(isinstance(files, dict) and files, "Producer has no original source-file identity")
        require(all(isinstance(path, str) and path and "\n" not in path and "\r" not in path
                    and not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts
                    and valid_digest(expected) for path, expected in files.items()),
                "Invalid producer source-file inventory")
        names = sorted(files)
        requested = "".join(admitted + ":" + name + "\n" for name in names).encode()
        result = subprocess.run(["git", "-c", "gc.auto=0", "-C", str(sdk_root), "cat-file", "--batch"],
                                env=environment, input=requested, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=120)
        require(result.returncode == 0, "Cannot read exact original producer source objects")
        cursor = 0
        for name in names:
            end = result.stdout.find(b"\n", cursor)
            require(end >= cursor, "Incomplete original producer source objects")
            header = result.stdout[cursor:end].split()
            require(len(header) == 3 and header[1] == b"blob", "Producer source file is missing: " + name)
            size = int(header[2])
            start = end + 1
            content = result.stdout[start:start + size]
            require(len(content) == size and result.stdout[start + size:start + size + 1] == b"\n",
                    "Incomplete producer source file: " + name)
            require(hashlib.sha256(content).hexdigest() == files[name], "Producer source bytes differ: " + name)
            cursor = start + size + 1
        require(cursor == len(result.stdout), "Unexpected extra producer source objects")
    return {"status": "PASS_EXACT_PREPARED_PRODUCER_SOURCE", "source_sha": source_sha,
            "source_tree": tree, "prepared_tree": admitted, "verified_source_files": len(names),
            "producer_object_store_modified": False}


