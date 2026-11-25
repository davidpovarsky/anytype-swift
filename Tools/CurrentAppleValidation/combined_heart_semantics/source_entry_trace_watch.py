"""Find one newly launched app in the admitted owned simulator, then observe it."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def owned_app_pids(device):
    # Query only this simulator's launchd services. A host-wide process scan can
    # block on unrelated diagnostic processes and is unnecessary for ownership.
    rows = subprocess.check_output(["xcrun", "simctl", "spawn", device, "launchctl", "list"],
                                   text=True, timeout=20).splitlines()
    result = []
    for row in rows:
        fields = row.split(None, 2)
        if (len(fields) == 3 and fields[0].isdecimal() and int(fields[0]) > 0
                and fields[2].startswith("UIKitApplication:io.anytype.app[")):
            result.append(int(fields[0]))
    if len(result) > 1:
        raise ValueError("Ambiguous owned app launchd service")
    return result


def main():
    path = Path(sys.argv[1])
    config = json.loads(path.read_bytes())
    observer = Path(config["observer"])
    if hashlib.sha256(observer.read_bytes()).hexdigest() != config["observerSHA256"]:
        raise ValueError("Frozen LLDB observer differs")
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / config["device"]
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline and not Path(config["stopFile"]).exists():
        matches = [pid for pid in owned_app_pids(config["device"]) if pid not in config["excludePIDs"]]
        if matches:
            app = Path(subprocess.check_output(["xcrun", "simctl", "get_app_container", config["device"],
                                               "io.anytype.app", "app"], text=True, timeout=20).strip())
            if not app.is_relative_to(owner) or app.resolve() != app or app.name != "Anytype.app":
                raise ValueError("Owned installed app path differs")
            config["pid"], config["executable"] = matches[0], str(app / "Anytype")
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
