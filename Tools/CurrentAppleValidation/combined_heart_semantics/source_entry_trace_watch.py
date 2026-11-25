"""Find one newly launched app in the admitted owned simulator, then observe it."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    path = Path(sys.argv[1])
    config = json.loads(path.read_bytes())
    observer = Path(config["observer"])
    if hashlib.sha256(observer.read_bytes()).hexdigest() != config["observerSHA256"]:
        raise ValueError("Frozen LLDB observer differs")
    prefix = str(Path.home() / "Library/Developer/CoreSimulator/Devices" / config["device"]) + "/"
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline and not Path(config["stopFile"]).exists():
        rows = subprocess.check_output(["ps", "-axo", "pid=,comm="], text=True, timeout=10).splitlines()
        matches = []
        for row in rows:
            fields = row.strip().split(None, 1)
            if len(fields) != 2:
                continue
            pid, executable = fields
            if (pid.isdecimal() and int(pid) not in config["excludePIDs"]
                    and executable.startswith(prefix) and executable.endswith("/Anytype.app/Anytype")):
                matches.append((int(pid), executable))
        if len(matches) > 1:
            raise ValueError("Ambiguous owned app process")
        if matches:
            config["pid"], config["executable"] = matches[0]
            actual = path.with_name("lldb-attached-config.json")
            actual.write_text(json.dumps(config, sort_keys=True, indent=2) + "\n")
            actual.chmod(0o600)
            # No app launch, activation or target expression is performed here.
            argv = ["xcrun", "lldb", "--no-lldbinit", "--batch",
                    "-o", "settings set symbols.enable-external-lookup false",
                    "-o", "command script import " + str(observer),
                    "-o", "script source_entry_trace_lldb.run(lldb.debugger, " + repr(str(actual)) + ")"]
            return subprocess.call(argv)
        time.sleep(0.2)
    raise RuntimeError("No newly launched owned application was observed")


if __name__ == "__main__":
    raise SystemExit(main())
