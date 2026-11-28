#!/usr/bin/python3
"""Create one private read-only Go module view, then exec one fixed metadata query.

This wrapper owns no process group and launches no child. The caller owns the
existing f9 group, all resource limits, the closed environment/source/toolchain
admission, final audits, and the parent namespace check. A READY receipt proves
only the pre-exec mount boundary, never Go success or source qualification.
"""
import ctypes
import hashlib
import json
import os
import signal
import stat
import sys
import time

ROOT = "/mnt/development/projects/evidence/pinkha-w1-files-queue-component-20261128-metadata1"
SOURCE = "/root/go/pkg/mod"
VIEW = ROOT + "/module-cache-view"
CANDIDATE = ROOT + "/candidate"
SELF = ROOT + "/module_cache_readonly.py"
GO = "/mnt/development/toolchains/go1.27.4/go/bin/go"
RECEIPT = "module-cache-view-receipt.json"
SOURCE_IDENTITY = (2049, 529231, 16877, 0, 0)
ARGV = (GO, "list", "-deps", "-test", "-json",
        "queue.go", "queue_test.go", "queue_retry_generation_test.go")
WRAPPER_SECONDS = 10.0
RECEIPT_CAP = 16 * 1024
MOUNTINFO_CAP = 1024 * 1024
CLONE_NEWNS = 0x00020000
MS_RDONLY, MS_NOSUID, MS_NODEV, MS_NOEXEC = 1, 2, 4, 8
MS_REMOUNT, MS_NOATIME, MS_BIND, MS_REC = 32, 1024, 4096, 16384
MS_PRIVATE = 1 << 18
REQUIRED_OPTIONS = frozenset(("ro", "nosuid", "nodev", "noexec", "noatime"))
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME

started = time.monotonic()
deadline = started + WRAPPER_SECONDS
root_fd = None
fds = []
receipt_created = False
receipt_durable = False
stage = "initial"
record = {
    "schema": "pinkha-queue-metadata-readonly-module-view-v1",
    "root": ROOT, "source": SOURCE, "view": VIEW,
    "cwd": CANDIDATE, "argv": list(ARGV),
    "wrapperDeadlineSeconds": WRAPPER_SECONDS,
    "receiptMaximumBytes": RECEIPT_CAP,
    "goExecutionClaim": False,
    "parentNamespaceUnchangedClaim": False,
    "parentNamespaceVerification": "required independently by caller after group closure",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def guard():
    if time.monotonic() >= deadline:
        raise TimeoutError("read-only module wrapper deadline")


def alarm_handler(_signum, _frame):
    raise TimeoutError("read-only module wrapper alarm")


def identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid)


def directory_details(st):
    return {
        "device": st.st_dev, "inode": st.st_ino, "mode": st.st_mode,
        "uid": st.st_uid, "gid": st.st_gid, "nlink": st.st_nlink,
        "size": st.st_size, "blocks": st.st_blocks,
        "atimeNS": st.st_atime_ns, "mtimeNS": st.st_mtime_ns,
        "ctimeNS": st.st_ctime_ns,
    }


def open_directory(path):
    guard()
    require(path.startswith("/") and path != "/" and
            all(part not in ("", ".", "..") for part in path[1:].split("/")),
            "fixed absolute physical directory")
    fd = os.open("/", DIRECTORY_FLAGS)
    try:
        for part in path[1:].split("/"):
            guard()
            next_fd = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        require(stat.S_ISDIR(os.fstat(fd).st_mode), "directory descriptor")
        return fd
    except BaseException:
        os.close(fd)
        raise


def keep_directory(path, private=False):
    fd = open_directory(path)
    fds.append(fd)
    st = os.fstat(fd)
    if private:
        require(st.st_uid == os.geteuid() and not (stat.S_IMODE(st.st_mode) & 0o077),
                "private current-owner directory: " + path)
    return fd, st


def record_wrapper_source():
    guard()
    fd = os.open("module_cache_readonly.py",
                 os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME,
                 dir_fd=root_fd)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                before.st_uid == os.geteuid() and
                not (stat.S_IMODE(before.st_mode) & 0o022) and
                0 < before.st_size <= 64 * 1024, "bounded owned wrapper source")
        parts, count = [], 0
        while count <= before.st_size:
            guard()
            part = os.read(fd, min(65536, before.st_size + 1 - count))
            if not part:
                break
            parts.append(part)
            count += len(part)
        after = os.fstat(fd)
        require(count == before.st_size and directory_details(after) == directory_details(before),
                "wrapper source exact-size stable read")
        return {"path": SELF, "bytes": count,
                "sha256": hashlib.sha256(b"".join(parts)).hexdigest(),
                "metadata": directory_details(after)}
    finally:
        os.close(fd)


def same_path_directory(path, wanted):
    fd = open_directory(path)
    try:
        current = os.fstat(fd)
        require(identity(current) == wanted, "fixed directory identity: " + path)
        return current
    finally:
        os.close(fd)


def namespace():
    guard()
    # This is the current process's procfs namespace handle, not a user path.
    fd = os.open("/proc/%d/ns/mnt" % os.getpid(), os.O_RDONLY | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        return {"device": st.st_dev, "inode": st.st_ino}
    finally:
        os.close(fd)


def unescape_mount_field(value):
    # mountinfo escapes these four bytes. No path lookup or readlink occurs.
    for escaped, plain in (("\\040", " "), ("\\011", "\t"),
                           ("\\012", "\n"), ("\\134", "\\")):
        value = value.replace(escaped, plain)
    return value


def mountinfo():
    guard()
    fd = os.open("/proc/%d/mountinfo" % os.getpid(),
                 os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        chunks, total = [], 0
        while True:
            guard()
            data = os.read(fd, min(65536, MOUNTINFO_CAP + 1 - total))
            if not data:
                break
            chunks.append(data)
            total += len(data)
            require(total <= MOUNTINFO_CAP, "bounded mountinfo")
        text = b"".join(chunks).decode("utf-8", "strict")
    finally:
        os.close(fd)
    result = []
    for line in text.splitlines():
        guard()
        fields = line.split(" ")
        require(fields.count("-") == 1, "mountinfo separator")
        separator = fields.index("-")
        require(separator >= 6 and len(fields) == separator + 4, "mountinfo fields")
        result.append({
            "mountID": int(fields[0]), "parentID": int(fields[1]),
            "majorMinor": fields[2],
            "root": unescape_mount_field(fields[3]),
            "mountPoint": unescape_mount_field(fields[4]),
            "options": sorted(fields[5].split(",")),
            "optionalFields": fields[6:separator],
            "fileSystemType": fields[separator + 1],
            "mountSource": unescape_mount_field(fields[separator + 2]),
            "superOptions": sorted(fields[separator + 3].split(",")),
            "raw": line,
        })
    return result


def below(path, parent):
    return path == parent or path.startswith(parent.rstrip("/") + "/")


def containing_mount(rows, path):
    candidates = [row for row in rows if below(path, row["mountPoint"])]
    require(bool(candidates), "containing physical mount")
    return max(candidates, key=lambda row: len(row["mountPoint"]))


def expected_bind_root(source_mount):
    relative = SOURCE[len(source_mount["mountPoint"].rstrip("/")):].lstrip("/")
    return source_mount["root"].rstrip("/") + "/" + relative


def verify_view(source_fd, source_before, root_before, candidate_before, source_mount, ns):
    guard()
    require(namespace() == ns, "same isolated mount namespace")
    same_path_directory(ROOT, identity(root_before))
    same_path_directory(CANDIDATE, identity(candidate_before))
    same_path_directory(SOURCE, SOURCE_IDENTITY)
    require(identity(os.fstat(source_fd)) == SOURCE_IDENTITY, "same source descriptor")
    view_fd = open_directory(VIEW)
    try:
        view_st = os.fstat(view_fd)
        require(identity(view_st) == SOURCE_IDENTITY, "view is exact source inode")
        readonly = bool(os.fstatvfs(view_fd).f_flag & os.ST_RDONLY)
        require(readonly, "view ST_RDONLY")
    finally:
        os.close(view_fd)
    require(directory_details(os.fstat(source_fd)) == directory_details(source_before),
            "source complete directory metadata unchanged")
    rows = mountinfo()
    selected = [row for row in rows if row["mountPoint"] == VIEW]
    require(len(selected) == 1, "exactly one private view mount")
    view_mount = selected[0]
    require(REQUIRED_OPTIONS.issubset(set(view_mount["options"])) and
            "rw" not in view_mount["options"], "required read-only mount options")
    require(view_mount["majorMinor"] == source_mount["majorMinor"] and
            view_mount["fileSystemType"] == source_mount["fileSystemType"] and
            view_mount["root"] == expected_bind_root(source_mount),
            "exact bind source in mountinfo")
    require(not any(field.startswith(("shared:", "master:", "propagate_from:"))
                    for field in view_mount["optionalFields"]), "private view propagation")
    require(not any(row["mountPoint"] != VIEW and below(row["mountPoint"], VIEW)
                    for row in rows), "no nested view mounts")
    require(not any(row["mountPoint"] != SOURCE and below(row["mountPoint"], SOURCE)
                    for row in rows), "no nested source mounts")
    return view_mount, directory_details(view_st), readonly


def write_receipt(status):
    global receipt_created, receipt_durable
    guard()
    require(root_fd is not None and not receipt_created, "one owned receipt")
    record["status"] = status
    record["stage"] = stage
    record["wrapperElapsedSecondsBeforeReceipt"] = time.monotonic() - started
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    require(len(payload) <= RECEIPT_CAP, "bounded receipt")
    # Mask termination across first exclusive ownership acquisition. The caller
    # still owns whole-group deadlines and preserves any incomplete receipt.
    masked = {signal.SIGTERM, signal.SIGINT, signal.SIGALRM}
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, masked)
    fd = None
    try:
        try:
            fd = os.open(RECEIPT, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=root_fd)
            receipt_created = True
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                before.st_uid == os.geteuid() and stat.S_IMODE(before.st_mode) == 0o600,
                "private single-link receipt")
        view = memoryview(payload)
        while view:
            guard()
            count = os.write(fd, view)
            require(count > 0, "receipt progress")
            view = view[count:]
        guard()
        os.fsync(fd)
        after = os.fstat(fd)
        require(identity(after) == identity(before) and after.st_nlink == 1 and
                after.st_size == len(payload), "complete same receipt descriptor")
        guard()
        os.fsync(root_fd)
        receipt_durable = True
    finally:
        if fd is not None:
            os.close(fd)


def syscall_ok(result, name):
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, name + ": " + os.strerror(code))


def main():
    global root_fd, stage
    require(len(sys.argv) == 2 and sys.argv[1] == ROOT, "one exact ROOT argument")
    require(os.path.abspath(__file__) == SELF, "fixed wrapper path")
    require(os.getcwd() == CANDIDATE, "fixed candidate cwd")
    require(os.environ.get("GOMODCACHE") == VIEW, "fixed read-only GOMODCACHE")
    root_fd, root_before = keep_directory(ROOT, private=True)
    record["wrapperSource"] = record_wrapper_source()
    candidate_fd, candidate_before = keep_directory(CANDIDATE, private=True)
    require(identity(os.stat(".", follow_symlinks=False)) == identity(candidate_before),
            "cwd descriptor identity")
    view_fd, view_before = keep_directory(VIEW, private=True)
    require(view_before.st_dev == root_before.st_dev, "view precreated on owned ROOT filesystem")
    with os.scandir(view_fd) as entries:
        require(next(entries, None) is None, "empty precreated view directory")
    source_fd, source_before = keep_directory(SOURCE)
    require(identity(source_before) == SOURCE_IDENTITY, "exact admitted module source identity")
    source_mounts = mountinfo()
    require(not any(row["mountPoint"] == VIEW for row in source_mounts), "view not mounted initially")
    require(not any(row["mountPoint"] != SOURCE and below(row["mountPoint"], SOURCE)
                    for row in source_mounts), "source contains no nested mount")
    source_mount = containing_mount(source_mounts, SOURCE)
    record["sourceExpectedIdentity"] = list(SOURCE_IDENTITY)
    record["sourceBefore"] = directory_details(source_before)
    record["rootBefore"] = directory_details(root_before)
    record["candidateBefore"] = directory_details(candidate_before)
    record["viewBefore"] = directory_details(view_before)
    record["sourceContainingMountBefore"] = source_mount
    original_namespace = namespace()
    record["originalNamespace"] = original_namespace
    libc = ctypes.CDLL(None, use_errno=True)
    libc.unshare.argtypes = [ctypes.c_int]
    libc.unshare.restype = ctypes.c_int
    libc.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                           ctypes.c_ulong, ctypes.c_void_p]
    libc.mount.restype = ctypes.c_int
    stage = "unshare"
    guard()
    syscall_ok(libc.unshare(CLONE_NEWNS), "unshare(CLONE_NEWNS)")
    child_namespace = namespace()
    require(child_namespace != original_namespace, "new mount namespace before any mount")
    record["isolatedNamespace"] = child_namespace
    stage = "private-propagation"
    guard()
    syscall_ok(libc.mount(None, b"/", None, MS_REC | MS_PRIVATE, None),
               "mount(MS_REC|MS_PRIVATE)")
    same_path_directory(SOURCE, SOURCE_IDENTITY)
    same_path_directory(ROOT, identity(root_before))
    same_path_directory(CANDIDATE, identity(candidate_before))
    same_path_directory(VIEW, identity(view_before))
    stage = "bind"
    guard()
    syscall_ok(libc.mount(SOURCE.encode("ascii"), VIEW.encode("ascii"), None,
                         MS_BIND, None), "private fixed module bind")
    stage = "readonly-remount"
    guard()
    readonly_flags = MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC | MS_NOATIME
    syscall_ok(libc.mount(None, VIEW.encode("ascii"), None, readonly_flags, None),
               "private bind read-only remount")
    stage = "verified-preexec"
    selected, view_after, readonly = verify_view(
        source_fd, source_before, root_before, candidate_before, source_mount, child_namespace)
    record.update({
        "verifiedMount": selected, "viewAfter": view_after,
        "sourceAfter": directory_details(os.fstat(source_fd)),
        "viewSTReadonly": readonly,
        "sourceViewIdentityEqual": True, "sourceMetadataUnchanged": True,
        "namespaceChangedBeforeMount": True,
        "propagationMadePrivateRecursively": True,
        "requiredMountOptions": sorted(REQUIRED_OPTIONS),
        "bindFlags": MS_BIND, "readonlyRemountFlags": readonly_flags,
        "nestedSourceOrViewMounts": False,
        "noChildBeforeExec": True,
        "noCleanupOrDeletion": True,
    })
    guard()
    write_receipt("READY_READONLY_MODULE_VIEW_NOT_GO_EXECUTION")
    # Check the same mounted source after durable receipt creation. A later
    # failure leaves the READY receipt but a nonzero wrapper result; the caller
    # must require both receipt validity and normal Go command closure.
    verified_again, _, _ = verify_view(
        source_fd, source_before, root_before, candidate_before, source_mount, child_namespace)
    require(verified_again == selected, "same exact mount after durable receipt")
    require(receipt_durable, "durable pre-exec receipt")
    guard()
    for fd in reversed(fds):
        os.close(fd)
    fds.clear()
    root_fd = None
    # The wrapper's ten-second alarm must not become Go's lifetime policy.
    # The existing f9 owner retains the command/group timeout after exec.
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    os.execve(GO, list(ARGV), dict(os.environ))


signal.signal(signal.SIGALRM, alarm_handler)
guard()
signal.setitimer(signal.ITIMER_REAL, deadline - time.monotonic())
try:
    main()
except BaseException as exc:
    failure = {
        "status": "READONLY_MODULE_WRAPPER_FAILED",
        "stage": stage, "errorType": type(exc).__name__,
        "error": str(exc)[:1024], "receiptCreated": receipt_created,
        "receiptDurable": receipt_durable,
        "elapsedSeconds": time.monotonic() - started,
        "goExecutionClaim": False,
    }
    if root_fd is not None and not receipt_created and time.monotonic() < deadline:
        try:
            record["failure"] = failure
            write_receipt("FAIL_READONLY_MODULE_VIEW_NOT_GO_EXECUTED")
        except BaseException as receipt_error:
            failure["receiptError"] = (type(receipt_error).__name__ + ": " + str(receipt_error))[:512]
    signal.setitimer(signal.ITIMER_REAL, 0)
    for fd in reversed(fds):
        try:
            os.close(fd)
        except OSError:
            pass
    # No path is removed, restored, remounted globally, or silently retried.
    sys.stderr.write(json.dumps(failure, sort_keys=True) + "\n")
    sys.stderr.flush()
    sys.exit(1)
