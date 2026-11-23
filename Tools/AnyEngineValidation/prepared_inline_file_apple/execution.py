"""Recorded bounded commands using the retained owned-process-group wrapper."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import signal
import sys

import contract


def command_json(path):
    contract.require(path.stat().st_size <= 16 * 1024**2, "Command JSON exceeds its bound")
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    documents, end = [], 0
    for match in re.finditer(r"(?m)^[\[{]", text):
        if match.start() < end:
            continue
        try:
            value, count = decoder.raw_decode(text[match.start():])
        except ValueError:
            continue
        documents.append(value)
        end = match.start() + count
    contract.require(len(documents) == 1 and isinstance(documents[0], dict), "Ambiguous or missing command JSON")
    return documents[0]


def process_wrapper(control):
    sys.path.insert(0, str(control / "Tools/TorahNativeOperations"))
    import run_account_lifecycle
    return run_account_lifecycle.run_process


class Commands:
    def __init__(self, control, evidence, receipt, *, process=None):
        self.control, self.evidence, self.receipt = control, evidence, receipt
        self.path = evidence / "receipt.json"
        self.process = process or process_wrapper(control)

    def __call__(self, argv, name, *, cwd=None, env=None, timeout=900):
        contract.require(re.fullmatch(r"[a-z0-9-]+", name), "Unsafe command evidence name")
        started = datetime.now(timezone.utc)
        entry = dict(name=name, argv=list(map(str, argv)), status="RUNNING", timeout_seconds=timeout,
                     started_at=started.isoformat())
        self.receipt["commands"].append(entry)
        contract.save(self.path, self.receipt)
        log = self.evidence / (name + ".log")
        try:
            entry["pid"] = self.process(entry["argv"], cwd or self.control, env or os.environ.copy(), log, timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as error:
            entry.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                         error_type=type(error).__name__, error=str(error))
            raise
        finally:
            finished = datetime.now(timezone.utc)
            entry.update(finished_at=finished.isoformat(), elapsed_seconds=(finished - started).total_seconds())
            if log.is_file():
                entry.update(log=log.name, log_bytes=log.stat().st_size, log_sha256=contract.digest(log))
            contract.save(self.path, self.receipt)
        return log


def run_stage(args, action, *, process=None):
    args.evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status="NOT_RUN", app_sha=args.expected_app_sha,
                   run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
                   commands=[], started_at=datetime.now(timezone.utc).isoformat())
    handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    cancelled = False
    def cancel(number, _):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in handlers:
        signal.signal(number, cancel)
    try:
        contract.artifact_name(receipt["run_id"], receipt["run_attempt"], args.expected_app_sha)
        action(args, receipt, Commands(args.control, args.evidence, receipt, process=process))
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                       error_type=type(error).__name__, error=str(error))
        receipt.setdefault("primary_failure", dict(error_type=type(error).__name__, error=str(error)))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        contract.save(args.evidence / "receipt.json", receipt)
        for number, handler in handlers.items():
            signal.signal(number, handler)
    print(json.dumps({"status": receipt["status"], "source": args.expected_app_sha,
                      "receipt": str(args.evidence / "receipt.json")}))
    return int(receipt["status"] not in (contract.PASS, contract.BUILD_PASS))
