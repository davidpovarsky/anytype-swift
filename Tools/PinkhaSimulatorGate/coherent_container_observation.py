"""Retain original fresh-container lookup outcome without changing its gate."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

TIMEOUT_SECONDS = 30


def run_lookup(argv, evidence):
    """One unchanged30-second query; timeout or errors remain the same errors."""
    evidence = Path(evidence)
    result = None
    primary = None
    stdout = stderr = b""
    started = time.monotonic()
    observation = {"scope": "BEFORE_FIRST_APP_INSTALL_LOOKUP_ONLY",
        "argv": argv, "timeout_seconds": TIMEOUT_SECONDS,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "INTERRUPTED", "container_absence_proved": False,
        "owned_group_absence_proved": False, "product_methods_executed": 0}
    try:
        result = subprocess.run(argv, capture_output=True, timeout=TIMEOUT_SECONDS)
        stdout, stderr = result.stdout, result.stderr
        observation.update(status="RETURNED", return_code=result.returncode)
        return result
    except BaseException as error:
        primary = error
        if isinstance(error, subprocess.TimeoutExpired):
            stdout, stderr = error.stdout or b"", error.stderr or b""
            observation.update(status="TIMED_OUT", error_type="TimeoutExpired")
        elif isinstance(error, OSError):
            observation.update(status="OS_ERROR", error_type="OSError",
                errno=error.errno if type(error.errno) is int else None)
        else:
            observation.update(status="INTERRUPTED", error_type=type(error).__name__)
        raise
    finally:
        try:
            for name, raw in [("stdout", stdout), ("stderr", stderr)]:
                if not isinstance(raw, bytes):
                    raise TypeError("lookup output is not original bytes")
                path = evidence / ("fresh-container-lookup." + name)
                with path.open("xb") as stream:
                    stream.write(raw)
                observation[name] = {"path": path.name, "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest()}
            observation.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                elapsed_seconds=max(0.0, time.monotonic() - started))
            path = evidence / "fresh-container-lookup.observation.json"
            with path.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(observation, sort_keys=True, indent=2) + "\n")
        except Exception as recording_error:
            if primary is None:
                raise
            primary.add_note("Lookup observation could not be recorded: " + type(recording_error).__name__)
