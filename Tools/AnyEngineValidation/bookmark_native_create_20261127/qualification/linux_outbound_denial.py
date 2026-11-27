#!/usr/bin/env python3
"""Install a process-inherited Linux syscall filter before one owned child.

Only the explicitly launched process tree is constrained. No host network or
service configuration is changed. The caller supplies and verifies the command.
"""
import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

LIBRARY = Path("/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5")
LIBRARY_SHA = "3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19"
DENIED = ("connect", "sendto", "sendmsg", "sendmmsg",
          "io_uring_setup", "io_uring_enter", "io_uring_register")

def install():
    assert sys.platform == "linux" and os.uname().machine == "aarch64"
    assert LIBRARY.resolve() == LIBRARY and LIBRARY.is_file() and not LIBRARY.is_symlink()
    before = LIBRARY.stat(); raw = LIBRARY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == LIBRARY_SHA
    lib = ctypes.CDLL(str(LIBRARY), use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                         ctypes.c_int, ctypes.c_uint, ctypes.c_void_p]
    lib.seccomp_rule_add_array.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.restype = ctypes.c_int
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7fff0000)
    assert context
    try:
        for name in DENIED:
            number = lib.seccomp_syscall_resolve_name(name.encode("ascii"))
            assert number >= 0, "unsupported syscall authority"
            assert lib.seccomp_rule_add_array(context, 0x00050000 | errno.EPERM,
                                              number, 0, None) == 0
        assert lib.seccomp_load(context) == 0
    finally:
        lib.seccomp_release(context)
    assert LIBRARY.read_bytes() == raw
    after = LIBRARY.stat()
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
    assert status["NoNewPrivs"].strip() == "1" and status["Seccomp"].strip() == "2"
    return {"librarySHA256": LIBRARY_SHA, "deniedSyscalls": list(DENIED),
            "noNewPrivileges": True, "seccompFilterActive": True}

def probe(port):
    result = install()
    result["tcpDenied"] = False; result["udpDenied"] = False
    try:
        socket.create_connection(("127.0.0.1", port), timeout=2).close()
    except OSError as error:
        result["tcpErrno"] = error.errno
        result["tcpDenied"] = error.errno == errno.EPERM
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as stream:
        try: stream.sendto(b"owned-offline-policy-probe", ("127.0.0.1", port))
        except OSError as error:
            result["udpErrno"] = error.errno
            result["udpDenied"] = error.errno == errno.EPERM
    assert result["tcpDenied"] and result["udpDenied"]
    print(json.dumps(result, sort_keys=True))

def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--probe":
        port = int(sys.argv[2]); assert 0 < port < 65536
        probe(port); return
    assert len(sys.argv) >= 3 and sys.argv[1] == "--exec"
    command = sys.argv[2:]
    assert Path(command[0]).is_absolute()
    install()
    os.execv(command[0], command)

if __name__ == "__main__":
    main()
