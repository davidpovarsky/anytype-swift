#!/usr/bin/env python3
"""Retain exact original main/native-UI build inputs before another increment.

All copies are private APFS clones. No app, test, simulator or native command
is executed; the two original build receipts remain the only build authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def inventory(root):
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            rows.append({"path": str(path.relative_to(root)), "kind": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            rows.append({"path": str(path.relative_to(root)), "kind": "file",
                         "bytes": path.stat().st_size, "sha256": digest(path)})
    return rows


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--main-evidence", type=Path, required=True)
    parser.add_argument("--ui-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, main, ui, out = args.main_root, args.main_evidence, args.ui_build, args.output
    require(all(p.is_absolute() and p.resolve() == p for p in (root, main, ui, out)),
            "canonical owned paths required")
    require(all(root in p.parents for p in (main, ui, out)) and not out.exists(),
            "fresh output in one owned root required")
    require(shutil.disk_usage(root).free > int(2.5 * 1024**3), "measured clone allowance and emergency floor")
    source = root / "source"
    record = json.loads((main / "receipt.json").read_bytes())
    runner = json.loads((ui / "receipt.json").read_bytes())
    require(record["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and record["sourceUnchanged"] is True and record["testsExecuted"] == 0,
            "original complete successful App and UI builds required")
    require(runner["status"] == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE" and runner["exitCode"] == 0
            and runner["testsExecuted"] == 0 and runner["sourceCommit"] == record["sourceCommit"]
            and runner["mainReceiptSHA256"] == digest(main / "receipt.json"),
            "exact main-bound successful native UI build required")
    require(digest(main / "source-before.json") == digest(main / "source-after.json"), "original sources changed")
    before = json.loads((main / "source-before.json").read_bytes())
    require(before["commit"] == record["sourceCommit"] and before["status"] == "", "clean original source required")
    require(subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
            == record["sourceCommit"], "actual original source commit changed")
    for name, row in before["files"].items():
        require(digest(source / name) == row["sha256"], "actual source changed: " + name)
    for phase in ("app", "ui"):
        require(record[phase]["exitCode"] == 0 and digest(main / phase / "original.log") ==
                record[phase]["logSHA256"], "original build result or log changed")
    require(digest(ui / "original-build.log") == runner["logSHA256"], "original runner log changed")
    require(digest(main / "products-all.json") == record["completeProductsInventory"]["sha256"],
            "original complete product manifest changed")
    products = json.loads((main / "products-all.json").read_bytes())
    require(digest(ui / "products-all.json") == runner["completeProductsInventory"]["sha256"],
            "original native UI product manifest changed")
    runner_products = ui / "derived/Build/Products"
    require(inventory(runner_products) == json.loads((ui / "products-all.json").read_bytes()),
            "actual runner products changed")
    for kind in ("app-derived", "ui-derived"):
        require(inventory(Path(products[kind]["base"])) == products[kind]["entries"], "actual original products changed")
    app_root = Path(products["app-derived"]["base"])
    app = app_root / "Debug-Anytype-iphonesimulator/Anytype.app"
    prefix = "Debug-Anytype-iphonesimulator/Anytype.app/"
    app_inventory = [dict(x, path=x["path"][len(prefix):]) for x in products["app-derived"]["entries"] if x["path"].startswith(prefix)]
    require(inventory(app) == app_inventory, "actual app closure differs")
    out.mkdir(mode=0o700)
    os.umask(0o022)
    result = {"status": "FAIL", "sourceCommit": record["sourceCommit"],
              "runnerSourceCommit": runner.get("runnerSourceCommit"),
              "controllerSHA256": digest(Path(__file__).resolve()),
              "mainReceiptSHA256": digest(main / "receipt.json"),
              "uiReceiptSHA256": digest(ui / "receipt.json"),
              "sourceBeforeSHA256": digest(main / "source-before.json"),
              "applicationBuilds": 0, "nativeBuilds": 0, "testsExecuted": 0, "copies": []}
    try:
        pairs = [(source, out / "source"), (app_root, out / "app-products"),
                 (Path(products["ui-derived"]["base"]), out / "complete-ui-products"),
                 (app, out / "Anytype.app")]
        for origin, destination in pairs:
            require(shutil.disk_usage(root).free > 2 * 1024**3, "owned clone emergency floor")
            started = time.time()
            command = ["cp", "-cRp", str(origin), str(destination)]
            process = subprocess.run(command, check=True, capture_output=True, timeout=300)
            result["copies"].append({"argv": command, "exitCode": process.returncode,
                                     "elapsedSeconds": time.time() - started})
        for name, row in before["files"].items():
            require(digest(out / "source" / name) == row["sha256"] == digest(source / name),
                    "source clone or original changed: " + name)
        require(subprocess.check_output(["git", "-C", str(out / "source"), "rev-parse", "HEAD"], text=True).strip()
                == record["sourceCommit"], "copied source Git identity differs")
        for name, original_kind in (("app-products", "app-derived"), ("complete-ui-products", "ui-derived")):
            require(inventory(out / name) == products[original_kind]["entries"] ==
                    inventory(Path(products[original_kind]["base"])), "original or cloned product changed")
        require(inventory(out / "Anytype.app") == app_inventory == inventory(app), "original or cloned app changed")
        require(inventory(runner_products) == json.loads((ui / "products-all.json").read_bytes()),
                "original native UI products changed during freeze")
        result.update(status="PASS_EXACT_FROZEN_NATIVE_UI_INPUTS", sourceFileCount=len(before["files"]),
                      appFileCount=len(app_inventory), allOriginalProductsUnchanged=True,
                      appProductsFileCount=len(products["app-derived"]["entries"]),
                      completeUIProductsFileCount=len(products["ui-derived"]["entries"]),
                      nativeUIProductsManifestSHA256=digest(ui / "products-all.json"))
    except BaseException as exc:
        result["firstFailure"] = {"type": type(exc).__name__, "reason": str(exc)}
        raise
    finally:
        result["finished"] = time.time()
        result["freeBytesAfter"] = shutil.disk_usage(root).free
        write(out / "receipt.json", result)
        print(json.dumps({k: v for k, v in result.items() if k != "copies"}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
