"""Verify original corrected runtime/source proof; never install or execute native code."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "Tools/PinkhaNativeDerived"))
import download_heart_runtime as download
import heart_runtime_profile as profiles
import install_verified_heart as installer

work = root / "build/verify-original-44943967103"
work.mkdir(parents=True, exist_ok=False)
evidence = work / "evidence"
evidence.mkdir()
args = argparse.Namespace(
    runtime_profile=profiles.CORRECTED, source_run_id="44943967103",
    expected_app_branch="codex/chatgpt-wave15-shared-20261121",
    repository="davidpovarsky/anytype-swift", app_source=root, work=work, evidence=evidence)
profile = profiles.select(args.runtime_profile)
started = time.time()
receipt = dict(status="NOT_RUN", producer_run_id=args.source_run_id, native_test_executions=0,
               architecture_recheck="NOT_RUN_WINDOWS", app_installation="NOT_RUN", simulator="NOT_RUN")
try:
    download.fetch_corrected(args, profile)
    inventory = profiles.verify_source(profile, args.patch.read_bytes(), args.inventory.read_bytes())
    with tarfile.open(args.archive) as packed:
        entries = [entry for entry in packed.getmembers() if entry.name == "PinkhaNativeHeartBuild.json"]
        profiles.require(len(entries) == 1 and entries[0].isfile(), "Original runtime receipt is ambiguous")
        raw = packed.extractfile(entries[0]).read()
    producer, downloaded = installer.original_proof(args, profile, raw, inventory)
    build = json.loads(raw)
    marker = profiles.validate_build(profile, build, inventory, args.source_run_id, producer)
    from build_t5_r15_runtime import EXPECTED_SLICES
    slices = build["binary_slices"]
    profiles.require(len(slices) == 3 and {(v["path"],v["architecture"]) for v in slices} == EXPECTED_SLICES
                     and all(v["marker"] == marker and profiles.is_sha(v["sha256"]) for v in slices),
                     "Original producer architecture proof is incomplete")
    receipt.update(status="ORIGINAL_ARTIFACT_SOURCE_PROOF_PASS_APPLE_RECHECK_NOT_RUN",
                   producer=producer, patch_sha256=profile.patch_sha256,
                   inventory_sha256=profile.inventory_sha256, expected_app_get_version=profile.version,
                   artifacts={k: {field: value[field] for field in ("id","name","digest","size_in_bytes")}
                              for k,value in downloaded["artifacts"].items()},
                   payload_sha256=downloaded["payload_sha256"],
                   original_native_fixture_proof=build["native_attachment_fixtures"],
                   original_producer_binary_slices=slices,
                   runtime_build_receipt_sha256=profiles.digest_bytes(raw),
                   source_composition=inventory["correction_provenance"])
except BaseException as error:
    receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
finally:
    receipt["wall_seconds"] = time.time() - started
    (evidence / "original-verification.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf8")
print(json.dumps({k:v for k,v in receipt.items() if k not in {"original_native_fixture_proof","source_composition","original_producer_binary_slices"}}))
raise SystemExit(0 if receipt["status"].startswith("ORIGINAL_ARTIFACT_SOURCE_PROOF_PASS") else 1)
