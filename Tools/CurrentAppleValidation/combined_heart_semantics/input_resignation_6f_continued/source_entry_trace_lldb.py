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

IMAGE = "ff2bd487138cb856b15d2bdb5ae798db9166e20933bd744f1a25ef7bc2bf70f1"
MAIN = "990d1e7117af5c491099b45ac1ae8a70b883d22089e8871e7994ef5f06dc6bd5"
# Exact 6f1194 symbols/disassembly identify x0 as sourceAction's textView
# argument and x20 as Swift resignFirstResponder's self. No target expression,
# guessed UIKit-private symbol, or address from an older image is admitted.
POINTS = {
    0x34d280: ("source-action-attempt-entry", None),
    0x350964: ("source-action-handler-entry", None),
    0x1c71ab4: ("editor-present-entry", None),
    0x9a71bc: ("selected-input-resign-entry", None),
}
STATE = None
OUTPUT = None
LABELS = {}
SOURCE_INPUT = None


def save():
    data = json.dumps(STATE, sort_keys=True, indent=2).encode() + b"\n"
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_bytes(data)
    temporary.chmod(0o600)
    temporary.replace(OUTPUT)


def observe(frame, location, internal_dict):
    global SOURCE_INPUT
    started = time.monotonic()
    try:
        label, register = LABELS[location.GetBreakpoint().GetID()]
        if label == "source-action-attempt-entry":
            source = frame.FindRegister("x0")
            if not source.IsValid() or source.GetError().Fail() or not source.GetValueAsUnsigned():
                raise ValueError("Actual source input register is unavailable")
            SOURCE_INPUT = source.GetValueAsUnsigned()
        selected_input = label == "selected-input-resign-entry"
        if selected_input:
            source = frame.FindRegister("x20")
            if not source.IsValid() or source.GetError().Fail():
                raise ValueError("Actual selected resignation self is unavailable")
            if SOURCE_INPUT is None or source.GetValueAsUnsigned() != SOURCE_INPUT:
                return False
        if label == "editor-present-entry" and SOURCE_INPUT is None:
            return False
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
        if selected_input:
            row["sameOriginalSourceInput"] = True
        if label in ("editor-present-entry", "selected-input-resign-entry"):
            frames = []
            thread = frame.GetThread()
            for index in range(min(thread.GetNumFrames(), 24)):
                item = thread.GetFrameAtIndex(index)
                address = item.GetPCAddress()
                module = address.GetModule()
                line = item.GetLineEntry()
                frames.append({
                    "index": index,
                    "function": item.GetFunctionName() or item.GetSymbol().GetName(),
                    "module": module.GetFileSpec().GetFilename() if module.IsValid() else None,
                    "fileAddress": hex(address.GetFileAddress()),
                    "sourceFile": line.GetFileSpec().GetFilename() if line.IsValid() else None,
                    "sourceLine": line.GetLine() if line.IsValid() else None,
                })
            row["readOnlyCallStack"] = frames
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
    STATE = {"protocol": "pinkha-heart-selected-input-resignation-stack-v1",
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
                    if not reasons:
                        # This is the observed auto-continue transition: LLDB
                        # publishes eStateStopped while every thread already
                        # has no stop reason. There is no target stop to resume.
                        # Consume the following state event without inventing
                        # an exception or detaching before the requested action.
                        STATE["transientAutomaticContinuations"] = STATE.get("transientAutomaticContinuations", 0) + 1
                        continue
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
