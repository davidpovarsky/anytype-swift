"""Observational breakpoints for one exact owned original Heart binary.

Loaded by LLDB, never by the application. No target expressions, function calls,
register writes, selections, menu dismissal or engine requests are performed.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import lldb

IMAGE = "6877f3588c1d016402a1e8f63ace53de67100e1d14997fd8bbef99eaa51c7b60"
MAIN = "1bd7422d7eabf6129d2f87f3bfda1539e07e958a5783e54866a33dde6c840e8e"
POINTS = {
    0x348960: ("source-action-built-entry", None),
    0x34b888: ("source-action-handler-entry", None),
    0x34b8dc: ("source-action-coordinator-loaded", "x0"),
    0x346e4c: ("open-sources-entry", None),
    0x347270: ("capture-inactive-admitted", None),
    0x3472cc: ("editor-loaded", "x0"),
    0x34736c: ("model-loaded", "x8"),
    0x347408: ("presented-controller-result", "x0"),
    0x34753c: ("no-presented-controller-admitted", None),
    0x3475d4: ("window-result", "x0"),
    0x3477e8: ("document-is-handling-result", "w0"),
    0x347880: ("document-is-opened-result", "w0"),
    0x3478e0: ("source-session-result", "x0"),
    0x347920: ("source-session-admitted", None),
    0x34b94c: ("source-task-entry", None),
    0x347d08: ("present-message-entry", None),
}
STATE = None
OUTPUT = None
LABELS = {}


def save():
    data = json.dumps(STATE, sort_keys=True, indent=2).encode() + b"\n"
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_bytes(data)
    temporary.chmod(0o600)
    temporary.replace(OUTPUT)


def observe(frame, location, internal_dict):
    started = time.monotonic()
    try:
        label, register = LABELS[location.GetBreakpoint().GetID()]
        if len(STATE["events"]) >= 128:
            STATE["capacityReached"] = True
            return False
        row = {"stage": label, "at": time.time(), "threadID": frame.GetThread().GetThreadID()}
        if register:
            value = frame.FindRegister(register)
            if not value.IsValid() or value.GetError().Fail():
                raise RuntimeError("Register unavailable: " + register)
            # Presence/Boolean is enough to distinguish each existing guard.
            # Do not export account data, pointers or target objects.
            row["register"] = register
            row["isZero"] = value.GetValueAsUnsigned() == 0
        row["callbackMilliseconds"] = (time.monotonic() - started) * 1000
        STATE["events"].append(row)
        save()
    except BaseException as exc:
        STATE["observationErrors"].append(type(exc).__name__ + ": " + str(exc))
        save()
    return False


def run(debugger, config_path):
    global STATE, OUTPUT, LABELS
    config = json.loads(Path(config_path).read_bytes())
    OUTPUT = Path(config["output"])
    device, pid = config["device"], config["pid"]
    owned = Path.home() / "Library/Developer/CoreSimulator/Devices" / device
    executable = Path(config["executable"])
    if not executable.is_relative_to(owned) or executable.name != "Anytype" or executable.parent.name != "Anytype.app":
        raise ValueError("Not the exact owned simulator app")
    command = subprocess.check_output(["ps", "-p", str(pid), "-o", "comm="], text=True, timeout=5).strip()
    if command != str(executable):
        raise ValueError("Owned process changed before attach")
    dylib = executable.with_name("Anytype.debug.dylib")
    for path, expected in ((executable, MAIN), (dylib, IMAGE)):
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Original executable bytes changed")
    STATE = {"protocol": "pinkha-heart-source-entry-image-offset-observation-v1",
             "status": "STARTING", "pid": pid, "device": device,
             "originalImageSHA256": IMAGE, "originalMainSHA256": MAIN,
             "binding": config["binding"], "extraEngineCalls": 0,
             "targetExpressions": 0, "targetRegisterWrites": 0,
             "menuDismissals": 0, "fixtureDeadlineChanges": 0,
             "maximumEvents": 128, "capacityReached": False,
             "events": [], "observationErrors": [], "breakpoints": [],
             "startedAt": time.time(), "diagnosticOnly": True}
    save()
    process = None
    debugger.SetAsync(True)
    for setting in ("settings set symbols.enable-external-lookup false",
                    "settings set target.process.stop-on-sharedlibrary-events false"):
        result = lldb.SBCommandReturnObject()
        debugger.GetCommandInterpreter().HandleCommand(setting, result)
        if not result.Succeeded():
            raise ValueError(result.GetError())
    try:
        target = debugger.CreateTarget(str(executable))
        listener = lldb.SBListener("owned-heart-source-observation")
        error = lldb.SBError()
        before = time.monotonic()
        process = target.AttachToProcessWithID(listener, pid, error)
        if error.Fail() or not process.IsValid():
            raise RuntimeError("Attach failed: " + str(error))
        STATE["attachMilliseconds"] = (time.monotonic() - before) * 1000
        matches = [m for m in target.modules if m.GetFileSpec().GetFilename() == "Anytype.debug.dylib"]
        if len(matches) != 1:
            raise ValueError("One actual loaded original app image required")
        module = matches[0]
        if str(module.GetFileSpec()) != str(dylib):
            raise ValueError("Loaded app module belongs to another path")
        for offset, definition in POINTS.items():
            address = module.ResolveFileAddress(offset)
            loaded = address.GetLoadAddress(target)
            if not address.IsValid() or loaded == lldb.LLDB_INVALID_ADDRESS:
                raise ValueError("Original image offset not loaded")
            breakpoint = target.BreakpointCreateByAddress(loaded)
            if breakpoint.GetNumLocations() != 1:
                raise ValueError("One exact breakpoint location required")
            LABELS[breakpoint.GetID()] = definition
            breakpoint.SetScriptCallbackFunction(__name__ + ".observe")
            breakpoint.SetAutoContinue(True)
            STATE["breakpoints"].append({"stage": definition[0], "fileOffset": hex(offset)})
        STATE["armedAt"] = time.time()
        STATE["status"] = "ARMED_NONBLOCKING_OBSERVER"
        save()
        error = process.Continue()
        if error.Fail():
            raise RuntimeError("Continue failed: " + str(error))
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline and not Path(config["stopFile"]).exists():
            event = lldb.SBEvent()
            if listener.WaitForEvent(1, event) and lldb.SBProcess.EventIsProcessEvent(event):
                state = lldb.SBProcess.GetStateFromEvent(event)
                if state in (lldb.eStateExited, lldb.eStateDetached):
                    STATE["processEndedAt"] = time.time()
                    break
                if state == lldb.eStateStopped and process.GetState() == lldb.eStateStopped:
                    # LLDB can publish the stop event before its automatic
                    # callback continuation completes. Resume only a positively
                    # identified breakpoint owned by this observer; never an
                    # exception, signal or unknown debugger stop.
                    reasons = []
                    stop_rows = []
                    for thread in process:
                        reason = thread.GetStopReason()
                        if reason in (lldb.eStopReasonNone, lldb.eStopReasonInvalid):
                            continue
                        ids = [thread.GetStopReasonDataAtIndex(i)
                               for i in range(0, thread.GetStopReasonDataCount(), 2)]
                        reasons.append(reason == lldb.eStopReasonBreakpoint and ids and all(i in LABELS for i in ids))
                        stop_rows.append({"threadID": thread.GetThreadID(), "reason": reason,
                                          "ownedBreakpointIDs": ids if reason == lldb.eStopReasonBreakpoint else []})
                    STATE.setdefault("stopNotifications", []).append({"at": time.time(), "threads": stop_rows})
                    if reasons and all(reasons):
                        error = process.Continue()
                        if error.Fail() and process.GetState() != lldb.eStateRunning:
                            STATE["observationErrors"].append("Owned breakpoint continuation failed: " + str(error))
                            break
                    elif process.GetState() == lldb.eStateStopped:
                        STATE["observationErrors"].append("Unowned process stop; detached without inspection")
                        break
        STATE["status"] = ("OBSERVER_FAILED_NOT_PRODUCT_RESULT" if STATE["observationErrors"]
                           else "OBSERVATION_FINISHED_NOT_ACCEPTANCE")
    except BaseException as exc:
        STATE["status"] = "OBSERVER_FAILED_NOT_PRODUCT_RESULT"
        STATE["observationErrors"].append(type(exc).__name__ + ": " + str(exc))
    finally:
        if process and process.IsValid() and process.GetState() not in (lldb.eStateExited, lldb.eStateDetached):
            error = process.Detach(False)
            STATE["detachedAndResumed"] = error.Success()
            if error.Fail():
                STATE["observationErrors"].append("Detach failed: " + str(error))
        STATE["finishedAt"] = time.time()
        save()
