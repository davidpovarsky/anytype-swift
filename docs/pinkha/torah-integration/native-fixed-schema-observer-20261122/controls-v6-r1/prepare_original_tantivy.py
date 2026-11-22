#!/usr/bin/env python3
"""Invoke only the exact original Tantivy fetch function in an owned finite child."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--heart", required=True, type=Path)
    parser.add_argument("--helper", required=True, type=Path)
    parser.add_argument("--helper-sha256", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if sha(args.helper) != args.helper_sha256:
        raise RuntimeError("original helper bytes differ")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("reviewed_original_heart_setup", args.helper)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    result = original.fetch_tantivy(args.heart.resolve(), "darwin-arm64")
    if sha(args.helper) != args.helper_sha256:
        raise RuntimeError("original helper changed")
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
