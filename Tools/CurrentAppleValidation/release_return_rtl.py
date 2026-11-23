"""One new Release App/test build: Return3 and the unresolved real RTL preparation."""
from __future__ import annotations
import os
import sys
import contracts as c
import current_execution as driver

PROFILE = "release-return-rtl"

def prepare_library(commands, work, evidence):
    receipt_dir = evidence / "heart"
    receipt_dir.mkdir(mode=0o700)
    commands.run([sys.executable, "-B", "Tools/PinkhaNativeDerived/download_heart_runtime.py",
                  "--runtime-profile", c.HEART["profile"], "--source-run-id", c.HEART["run"],
                  "--app-source", str(driver.ROOT), "--expected-app-branch", os.environ["GITHUB_REF_NAME"],
                  "--work", str(work / "heart-originals"), "--evidence", str(receipt_dir)],
                 "install-original-heart", 1800)
    receipt = driver.read(receipt_dir / "heart-installation.json")
    expected = {"status": "PASS", "source_run_id": c.HEART["run"], "patch_sha256": c.HEART["patch"],
                "inventory_sha256": c.HEART["inventory"], "app_source_sha": commands.context["sourceCommit"],
                "runtime_profile": c.HEART["profile"], "heart_build_receipt_sha256": c.HEART["originalBuildReceipt"],
                "installed_fixture": False, "target_architecture": "arm64", "target_environment": "simulator"}
    c.require(all(receipt.get(k) == v for k, v in expected.items())
              and receipt["producer"]["source_sha"] == c.HEART["source"]
              and receipt["build_producer"]["run_id"] == c.HEART["originalBuildRun"],
              "fixed_production_heart_origin_changed")
    library = driver.ROOT / "Dependencies/Middleware"
    return {"path": str(library), "files": driver.inventory(library), "nativeBuildInvocations": 0,
            "installationReceiptSHA256": driver.digest(receipt_dir / "heart-installation.json"),
            "originalProducer": c.HEART, "currentAppSource": commands.context["sourceCommit"],
            "cLoadedAccountWitnessIncluded": False}

def provider(commands, operation, device, evidence):
    c.require(operation in ("prepare", "verify", "cleanup"), "unexpected_provider_operation")
    return {"status": "NOT_APPLICABLE", "operation": operation}

if __name__ == "__main__":
    raise SystemExit(driver.main(PROFILE, prepare_library, provider))
