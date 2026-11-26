#!/usr/bin/env python3
"""Restore eight missing public Go metadata entries using Go's original authentication."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time

BASE = Path("/Users/m1/development/anytype-d-active-20261125/native-immutable")
INPUT = BASE / "inputs-11619a9928d6-8393d79/control"
PRIOR = BASE / "pinkha-dual-native-v1-11619a9928d6-simulator"
ROOT = BASE / "module-metadata-recovery1"
CACHE = Path("/Users/m1/caches/anytapy-go-mod")
GO = Path("/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go")
REVIEW_SHA = "2860bd4ec7d8326a901569345969f3702a6528d65b057b98383de7525b0b091e"
PRIOR_SHA = "19b9d12008b0549e5e9763fd18d0e1e5155b3241d5b492ca650f9ce47a91fe6c"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def write(path, value):
    with path.open("x") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())

def main():
    require(BASE.resolve() == BASE and not ROOT.exists(), "fresh_owned_metadata_root_required")
    require(digest(PRIOR / "evidence/receipt.json") == PRIOR_SHA, "original_failure_changed")
    prior = json.loads((PRIOR / "evidence/receipt.json").read_text())
    require(prior["status"] == "FAIL" and prior["failure"]["message"] == "actual_cached_module_metadata_changed"
            and len(prior["commands"]) == 4 and all(row["exitCode"] == 0 for row in prior["commands"]),
            "exact_zero_compile_preparation_stop_required")
    review_path = INPUT / "module-metadata-hydration.json"
    require(digest(review_path) == REVIEW_SHA, "original_eight_metadata_identities_changed")
    review = json.loads(review_path.read_text())
    require(len(review["modules"]) == 8, "exact_eight_modules_required")
    ROOT.mkdir(mode=0o700)
    result = {"protocol": "pinkha-native-immutable-eight-module-metadata-recovery-v1", "result": "FAIL",
              "controllerSHA256": digest(Path(__file__)), "originalProducerFailureSHA256": PRIOR_SHA,
              "reviewSHA256": REVIEW_SHA, "modules": [], "nativeBuilds": 0, "testsExecuted": 0}
    env = dict(os.environ, GOWORK="off", GOTOOLCHAIN="local", GOFLAGS="-mod=readonly",
               GOROOT=str(GO.parent.parent), GOPATH=str(ROOT / "go-state"), GOMODCACHE=str(CACHE),
               GOCACHE="/Users/m1/caches/anytapy-go1.27.4-build",
               GOPROXY="https://proxy.golang.org,direct", GOSUMDB="sum.golang.org",
               GOPRIVATE="", GONOSUMDB="", GONOPROXY="")
    try:
        result["freeBytesBefore"] = shutil.disk_usage(BASE).free
        require(result["freeBytesBefore"] > 3 * 1024**3, "metadata_download_phase_space_unavailable")
        for index, row in enumerate(review["modules"], 1):
            path = CACHE / "cache/download" / row["path"] / "@v" / (row["version"] + ".mod")
            require(path.resolve() == path and not path.is_symlink(), "metadata_cache_path_changed")
            entry = {"path": row["path"], "version": row["version"], "cachePath": str(path),
                     "expectedGoModSHA256": row["goModSHA256"], "expectedGoModSum": row["goModSum"],
                     "existedBefore": path.is_file()}
            result["modules"].append(entry)
            if path.is_file():
                require(digest(path) == row["goModSHA256"], "conflicting_cache_bytes_must_not_be_overwritten")
            log = ROOT / (f"{index:02d}.stdout.json")
            err = ROOT / (f"{index:02d}.stderr.log")
            argv = [str(GO), "mod", "download", "-json", row["path"] + "@" + row["version"]]
            started = time.time()
            with log.open("xb") as out, err.open("xb") as error:
                process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=out, stderr=error, start_new_session=True)
                entry.update(argv=argv, pid=process.pid, pgid=process.pid, started=started)
                write(ROOT / (f"{index:02d}.started.json"), entry)
                while process.poll() is None:
                    free = shutil.disk_usage(BASE).free
                    entry["minimumFreeBytes"] = min(entry.get("minimumFreeBytes", free), free)
                    if time.time() - started > 180 or free < 2 * 1024**3:
                        entry["stopReason"] = "OWNED_METADATA_TIME_OR_DISK_LIMIT"
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(timeout=10)
                        except ProcessLookupError:
                            process.wait(timeout=10)
                        break
                    time.sleep(0.5)
                entry.update(exitCode=process.returncode, elapsedSeconds=time.time()-started)
            entry.update(stdoutSHA256=digest(log), stderrSHA256=digest(err))
            write(ROOT / (f"{index:02d}.command.json"), entry)
            require(process.returncode == 0, "original_authenticated_module_download_failed")
            value = json.loads(log.read_text())
            require(value["Path"] == row["path"] and value["Version"] == row["version"]
                    and value["GoModSum"] == row["goModSum"] and not value.get("Error"),
                    "downloaded_module_identity_or_authenticated_checksum_changed")
            require(path.is_file() and digest(path) == row["goModSHA256"], "downloaded_metadata_bytes_changed")
            entry.update(actualGoModSHA256=digest(path), actualGoModSum=value["GoModSum"])
            print(json.dumps({"module": row["path"], "result": "PASS_EXACT_AUTHENTICATED_METADATA"}), flush=True)
        for row in review["modules"]:
            path = CACHE / "cache/download" / row["path"] / "@v" / (row["version"] + ".mod")
            require(path.resolve() == path and digest(path) == row["goModSHA256"], "final_metadata_readback_changed")
        require(digest(PRIOR / "evidence/receipt.json") == PRIOR_SHA and digest(review_path) == REVIEW_SHA,
                "original_evidence_changed_during_recovery")
        result["result"] = "PASS_EIGHT_ORIGINAL_AUTHENTICATED_METADATA_ENTRIES_RESTORED"
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "reason": str(error)}
        raise
    finally:
        result["freeBytesAfter"] = shutil.disk_usage(BASE).free
        write(ROOT / "receipt.json", result)
        print(json.dumps({"result": result["result"], "receiptSHA256": digest(ROOT / "receipt.json"),
                          "failure": result.get("failure")}), flush=True)

if __name__ == "__main__":
    main()
