import os, stat, hashlib, json, time, signal, resource
START = time.monotonic()
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
def stop(signum, frame):
    raise TimeoutError("exact public receipt read deadline")
signal.signal(signal.SIGALRM, stop)
signal.alarm(10)
ROOT = "/mnt/development/projects/evidence/pinkha-w1-files-queue-component-20261128-metadata1"
FILES = [
    ("result.json", 17668, "bd6b7e3c91f89476c45261712f763315a50b090589a7b3e8afc6c9bdd5b31de0"),
    ("terminal-candidate.json", 1078, "866075381a8327ad681d69342bbfb3dcf1ca423babce2506fcd8d941fb9b4558"),
    ("module-cache-view-receipt.json", 5107, "5f442faa5cfd9a716fca199b717b4db7c2968a7ea691820ac36721ac86fa3f0d"),
]
def identity(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink,
            s.st_size, s.st_blocks, s.st_atime_ns, s.st_mtime_ns, s.st_ctime_ns]
def guard():
    if time.monotonic() - START > 10:
        raise TimeoutError("exact public receipt read deadline")
fds = []
result = {"scope": "three exact public metadata receipts only", "files": [],
          "noPayloadOrAccountRead": True, "noProjectWrite": True, "noCompilerOrNative": True}
try:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC
    fd = os.open("/", flags)
    fds.append(fd)
    for component in ROOT.lstrip("/").split("/"):
        guard()
        fd = os.open(component, flags, dir_fd=fd)
        fds.append(fd)
    root_before = identity(os.fstat(fd))
    for name, size, wanted in FILES:
        guard()
        pre = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if not stat.S_ISREG(pre.st_mode) or pre.st_nlink != 1 or pre.st_size != size:
            raise RuntimeError("fixed regular single-link receipt identity: " + name)
        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC, dir_fd=fd)
        try:
            if identity(os.fstat(handle)) != identity(pre):
                raise RuntimeError("opened receipt identity: " + name)
            chunks = []
            remaining = size + 1
            while remaining:
                guard()
                part = os.read(handle, min(65536, remaining))
                if not part:
                    break
                chunks.append(part)
                remaining -= len(part)
            raw = b"".join(chunks)
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != wanted:
                raise RuntimeError("exact receipt whole bytes: " + name)
            if identity(os.fstat(handle)) != identity(pre):
                raise RuntimeError("opened receipt metadata changed: " + name)
        finally:
            os.close(handle)
        if identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != identity(pre):
            raise RuntimeError("named receipt metadata changed: " + name)
        result["files"].append({"name": name, "path": ROOT + "/" + name, "bytes": size,
                                "sha256": wanted, "stableIdentity": identity(pre),
                                "rawUTF8": raw.decode("utf-8")})
    if identity(os.fstat(fd)) != root_before:
        raise RuntimeError("receipt directory metadata changed")
    result["directoryIdentityUnchanged"] = True
    result["status"] = "PASS_EXACT_NOATIME_NOFOLLOW_PUBLIC_RECEIPT_READ"
finally:
    for handle in reversed(fds):
        os.close(handle)
    signal.alarm(0)
print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
