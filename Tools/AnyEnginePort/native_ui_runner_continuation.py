#!/usr/bin/env python3
"""Dedicated no-build continuation for the exact previously built UI runner."""
from __future__ import annotations
import argparse
import json
import native_ui_transition as transition
import native_ui_transition_contract as contract
import native_ui_runner_reuse as reuse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("restore", "execute", "final"))
    parser.add_argument("--stage", choices=tuple(contract.STAGES))
    args = parser.parse_args()
    reference = reuse.reference()
    if args.operation == "execute":
        contract.require(args.stage is not None, "stage_required")
        result = transition.execute(args.stage, restored_runner=reference)
    else:
        contract.require(args.stage is None, "stage_only_for_execution")
        result = reuse.restore() if args.operation == "restore" else transition.final(restored_runner=reference)
    print(json.dumps({"status": result["status"], "profile": reuse.PROFILE,
                      "currentBuilds": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
