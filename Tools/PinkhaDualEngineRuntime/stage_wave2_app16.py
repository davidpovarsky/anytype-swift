"""Stage the preserved a089 App16 source in the released warm compiler workspace."""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, stat, subprocess, sys, time

BASE = Path("/Users/m1/development/anytype-d-active-20261125")
ROOT = BASE / "main16-wave2-20261127"
PREVIOUS = BASE / "main15"
SOURCE = BASE / "main14/source"
APP_DERIVED = BASE / "main14/app-derived"
EXPECTED = "a089ff29a5c0a7e415aac800844505f099a5561d"
OLD = "379ca3568f247d2fc218ed63df24796d461713c0"
MANIFEST = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
ORIGINAL_RECEIPT_SHA = "0f0a1241dc76b6585a42866f5d129ea8f5aaa722addc74873245ebe71a09b735"
ORIGINAL_INVENTORY_SHA = "d4846f9c640dcb03e56626425ec0ec5649496de885ed464d5258cdfb9431424b"

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    with path.open("x") as handle:
        os.chmod(path, 0o600)
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

def inventory(root):
    require(root.resolve() == root and not root.is_symlink(), "canonical inventory root required")
    rows = {}
    for path in sorted(root.rglob("*")):
        row = {"mode": stat.S_IMODE(path.lstat().st_mode)}
        if path.is_symlink():
            row.update(kind="symlink", target=os.readlink(path))
        elif path.is_dir():
            row.update(kind="directory")
        elif path.is_file():
            row.update(kind="file", bytes=path.stat().st_size, sha256=sha(path))
        else:
            raise ValueError("unsupported workspace member " + str(path))
        rows[str(path.relative_to(root))] = row
    return rows

def compact(rows):
    return [{key: row[key] for key in ("path", "kind", "bytes", "sha256") if key in row}
            if row["kind"] == "file" else {key: row[key] for key in ("path", "kind", "target")}
            for name, item in rows.items() for row in [dict(item, path=name)]
            if row["kind"] in ("file", "symlink")]

def git(*args):
    p = subprocess.run(["git", "-C", str(SOURCE), *args], capture_output=True, text=True, timeout=60)
    require(p.returncode == 0, "git failed: " + p.stderr[-1000:])
    return p.stdout

def main():
    config_path = Path(sys.argv[1])
    require(sha(config_path) == sys.argv[2], "staging input digest mismatch")
    config = json.loads(config_path.read_bytes())
    require(config["sourceCommit"] == EXPECTED and config["priorSource"] == OLD, "unexpected source transition")
    bundle = ROOT / "source-inputs/source.bundle"
    require(sha(bundle) == config["bundleSHA256"], "exact reviewed source bundle required")
    require(ROOT.is_dir() and ROOT.resolve() == ROOT, "canonical stage root required")
    evidence = ROOT / "source-staging1"
    evidence.mkdir(mode=0o700)
    outcome = {"status": "FAIL", "started": time.time(), "sourceCommit": EXPECTED,
               "controllerSHA256": sha(Path(__file__)), "applicationBuilds": 0, "nativeBuilds": 0, "tests": 0}
    try:
        require(git("rev-parse", "HEAD").strip() == OLD and git("status", "--porcelain") == "", "App15 source must be clean")
        prior_receipt = PREVIOUS / "build15-ui-continuation1/receipt.json"
        prior_inventory = PREVIOUS / "build15-ui-continuation1/products-all.json"
        require(sha(prior_receipt) == ORIGINAL_RECEIPT_SHA and sha(prior_inventory) == ORIGINAL_INVENTORY_SHA, "original producer evidence mismatch")
        receipt = json.loads(prior_receipt.read_bytes())
        require(receipt["sourceCommit"] == OLD and receipt["originalAppProductsPreserved"] is True, "original App15 lineage mismatch")
        require(sha(PREVIOUS / "build15/source-before.json") == "b4fd4069ed3846797bde854caef134c4c7343e475ade555f8daffc34e8a3dc38", "original compiler source receipt digest mismatch")
        original_sources = json.loads((PREVIOUS / "build15/source-before.json").read_bytes())
        require(original_sources["commit"] == OLD, "original source identity mismatch")
        for name, row in original_sources["files"].items():
            p = SOURCE / name
            require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], "original compile input differs: " + name)
        for index, derived in enumerate((APP_DERIVED, PREVIOUS / "ui-derived")):
            database = derived / "Build/Intermediates.noindex/XCBuildData/build.db"
            if database.exists():
                p = subprocess.run(["/usr/sbin/lsof", "-nP", str(database)], capture_output=True, text=True, timeout=15)
                write(evidence / ("cache-owner-" + str(index) + ".json"), {"path": str(database), "exitCode": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
                require(p.returncode == 1 and not p.stdout and not p.stderr, "compiler cache still has an owner")
        free = shutil.disk_usage(ROOT).free
        require(free >= 3 * 1024**3, "insufficient headroom for APFS preservation and stage metadata")
        retained = ROOT / "retained-App15"
        retained.mkdir(mode=0o700)
        original_source = inventory(SOURCE)
        write(evidence / "original-source-inventory.json", original_source)
        native_before = inventory(SOURCE / "Dependencies/Middleware/Lib.xcframework")
        source_manifest = SOURCE / "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json"
        require(sha(source_manifest) == MANIFEST, "native source manifest differs")
        products = json.loads(prior_inventory.read_bytes())
        product_pins = {}
        copy_mask = os.umask(0)
        try:
            subprocess.run(["/bin/cp", "-cRp", str(SOURCE), str(retained / "source")], check=True, timeout=240)
            require(inventory(retained / "source") == original_source == inventory(SOURCE), "original source preservation differs")
            for kind, data in products.items():
                expected_root = APP_DERIVED if kind == "app-derived" else PREVIOUS / "ui-derived"
                original = expected_root / "Build/Products"
                require(data["base"] == str(original), "unexpected original product path")
                current = inventory(original)
                require(compact(current) == data["entries"], "original App15 product inventory differs: " + kind)
                target = retained / (kind + "-Products")
                subprocess.run(["/bin/cp", "-cRp", str(original), str(target)], check=True, timeout=180)
                require(inventory(target) == current == inventory(original), "product preservation differs: " + kind)
                index_path = evidence / (kind + "-original-inventory.json")
                write(index_path, current)
                product_pins[kind] = {"original": str(original), "retained": str(target), "inventorySHA256": sha(index_path), "entries": len(current)}
            write(evidence / "original-preservation.json", {"status": "PASS_ORIGINAL_SOURCE_AND_PRODUCTS_BYTES_MODES_LINKS", "source": str(SOURCE), "retainedSource": str(retained / "source"), "sourceInventorySHA256": sha(evidence / "original-source-inventory.json"), "products": product_pins, "originalProducerSHA256": ORIGINAL_RECEIPT_SHA})
            require(git("rev-parse", "HEAD").strip() == OLD and git("status", "--porcelain") == "", "source changed before checked update")
            for index, derived in enumerate((APP_DERIVED, PREVIOUS / "ui-derived")):
                database = derived / "Build/Intermediates.noindex/XCBuildData/build.db"
                if database.exists():
                    owner = subprocess.run(["/usr/sbin/lsof", "-nP", str(database)], capture_output=True, text=True, timeout=15)
                    write(evidence / ("cache-owner-before-checkout-" + str(index) + ".json"), {"path": str(database), "exitCode": owner.returncode, "stdout": owner.stdout, "stderr": owner.stderr})
                    require(owner.returncode == 1 and not owner.stdout and not owner.stderr, "compiler cache acquired another owner during preservation")
            git("bundle", "verify", str(bundle))
            git("fetch", str(bundle), config["bundleRef"])
            git("checkout", "--detach", EXPECTED)
            require(git("rev-parse", "HEAD").strip() == EXPECTED and git("rev-parse", "HEAD^{tree}").strip() == config["sourceTree"] and git("status", "--porcelain") == "", "exact clean App16 source required")
            require(inventory(SOURCE / "Dependencies/Middleware/Lib.xcframework") == native_before, "native dependency changed")
            require(sha(source_manifest) == MANIFEST, "native manifest changed")
            subprocess.run(["/bin/cp", "-cRp", str(PREVIOUS / "native-materialization-8ac"), str(ROOT / "native-materialization-8ac")], check=True, timeout=60)
            require(inventory(PREVIOUS / "native-materialization-8ac") == inventory(ROOT / "native-materialization-8ac"), "native provenance copy differs")
            subprocess.run(["/bin/cp", "-cRp", str(PREVIOUS / "ui-derived"), str(ROOT / "ui-derived")], check=True, timeout=180)
        finally:
            os.umask(copy_mask)
        require(inventory(retained / "source") == original_source, "preserved App15 source changed")
        for kind in product_pins:
            require(inventory(retained / (kind + "-Products")) == json.loads((evidence / (kind + "-original-inventory.json")).read_bytes()), "preserved products changed")
        require(git("rev-parse", "HEAD").strip() == EXPECTED and git("status", "--porcelain") == "", "source changed during stage")
        outcome.update(status="PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED",
                       sourceRoot=str(SOURCE), appDerived=str(APP_DERIVED), uiDerived=str(ROOT / "ui-derived"),
                       tree=config["sourceTree"], priorSource=OLD, sourceManifestSHA256=MANIFEST,
                       originalPreservationSHA256=sha(evidence / "original-preservation.json"),
                       originalIntermediatesAndPackagePathsReused=True, freeBytesBefore=free,
                       inputSHA256=sha(config_path))
    except BaseException as exc:
        outcome["error"] = {"type": type(exc).__name__, "reason": str(exc)}
        raise
    finally:
        outcome["finished"] = time.time()
        outcome["freeBytesAfter"] = shutil.disk_usage(ROOT).free
        write(evidence / "receipt.json", outcome)
        print(json.dumps(outcome))

if __name__ == "__main__":
    main()
