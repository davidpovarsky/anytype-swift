"""Read one original native capture reply at the verified ARM64 decode boundary.

The caller supplies a fresh owned Simulator App PID. The only expression reads
the existing Foundation.Data value saved by the original function prologue;
it invokes Data.base64EncodedString(), never a product or native write method.
The process is detached in finally and receives no acceptance credit.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

SYMBOL = "$s16ProtobufMessages37PinkhaHeartSemanticAnchorAppliedReplyV6decode_7requestAC10Foundation4DataV_AA0cdeF7RequestVtKFZ"
PREFIX_SHA = "f160a3fe6031da0c1ca4f023006d336c752b32fd8b58c1eae478cede512bb1b8"
PREFIX_BYTES = 72
DATA_STACK_OFFSET = 0x3e0
CONTEXT = None


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def capture(frame, location, _):
    import lldb
    context = CONTEXT
    context["hits"] += 1
    try:
        context["phase"] = "validatingOwnedFrame"
        require(context["hits"] == 1, "one_capture_only")
        process = frame.GetThread().GetProcess()
        require(process.GetProcessID() == context["pid"], "owned_pid_changed")
        require(frame.GetPC() == context["breakpointAddress"], "decode_boundary_changed")
        stack = frame.FindRegister("sp").GetValueAsUnsigned()
        require(stack > 0 and stack % 16 == 0, "stack_alignment")
        address = stack + DATA_STACK_OFFSET
        error = lldb.SBError()
        memory = process.ReadMemory(address, 16, error)
        require(error.Success() and len(memory) == 16, "original_data_slot_unreadable")
        options = lldb.SBExpressionOptions()
        options.SetLanguage(lldb.eLanguageTypeSwift)
        options.SetTimeoutInMicroSeconds(5_000_000)
        options.SetIgnoreBreakpoints(True)
        options.SetUnwindOnError(True)
        options.SetTryAllThreads(False)
        options.SetStopOthers(True)
        expression = ("import Foundation\n"
            "UnsafePointer<Foundation.Data>(bitPattern: UInt(" + str(address) +
            "))!.pointee.base64EncodedString()")
        context["phase"] = "readingFoundationData"
        write(Path(context["work"]) / "reply-observation.json", context)
        result = frame.EvaluateExpression(expression, options)
        context["foundationReadSucceeded"] = result.GetError().Success()
        require(result.GetError().Success(), "foundation_read_expression:" + str(result.GetError())[:800])
        context["phase"] = "decodingReadSummary"
        summary = result.GetSummary()
        context["summaryLength"] = len(summary) if isinstance(summary, str) else None
        write(Path(context["work"]) / "reply-observation.json", context)
        require(isinstance(summary, str) and len(summary) <= 5_600_000, "bounded_data_summary_required")
        encoded = json.loads(summary)
        require(isinstance(encoded, str), "base64_string_required")
        raw = base64.b64decode(encoded, validate=True)
        require(0 < len(raw) <= 4_194_304 and base64.b64encode(raw).decode() == encoded,
                "canonical_bounded_reply_required")
        value = json.loads(raw)
        require(isinstance(value, dict) and value.get("protocolVersion") == 1
                and value.get("outcome") == "applied"
                and set(value) == {"protocolVersion", "outcome", "receipt", "responseEvent"},
                "actual_applied_reply_shape_required")
        reply_path = Path(context["work"]) / "private-original-capture-reply.json"
        with reply_path.open("xb") as output:
            output.write(raw)
        context.update({"status": "CAPTURED_ORIGINAL_REPLY", "replyBytes": len(raw),
                        "replySHA256": hashlib.sha256(raw).hexdigest(),
                        "privateReply": str(reply_path), "expressionIsReadOnlyFoundationData": True,
                        "capturedAt": time.time()})
    except BaseException as error:
        context["status"] = "OBSERVATION_FAILED"
        failure = {"type": type(error).__name__, "message": str(error)[:1000]}
        context.setdefault("firstFailure", {"phase": context.get("phase"), **failure})
        context.setdefault("error", failure)
    write(Path(context["work"]) / "reply-observation.json", context)
    return True


def observe_preflight(frame, location, _):
    import lldb
    context = CONTEXT
    try:
        process = frame.GetThread().GetProcess()
        require(process.GetProcessID() == context["pid"], "owned_preflight_pid_changed")
        stack = frame.FindRegister("sp").GetValueAsUnsigned()
        error = lldb.SBError()
        pointer = process.ReadUnsignedFromMemory(stack + 0x410, 8, error)
        require(error.Success() and pointer != 0, "original_preflight_pointer_required")
        options = lldb.SBExpressionOptions()
        options.SetLanguage(lldb.eLanguageTypeSwift)
        options.SetTimeoutInMicroSeconds(5_000_000)
        options.SetIgnoreBreakpoints(True)
        options.SetUnwindOnError(True)
        options.SetTryAllThreads(False)
        options.SetStopOthers(True)
        # The retained debug image omits a usable imported Swift module for the
        # nested generated response. Resolve its already-loaded runtime type and
        # read the exact Optional value; no native method or product write runs.
        # SwiftProtobuf.Message debugDescription is its complete text-format
        # serialization in this retained Debug image (including unknown fields).
        expression = ("import Foundation\n"
            "({ () -> String in\n"
            "let name = \"16ProtobufMessages11Anytype_RpcV6ObjectV4ShowV8ResponseV\"\n"
            "guard let resolved = _typeByName(name) else { return \"E_TYPE_MISSING\" }\n"
            "func read<T>(_ type: T.Type) -> String {\n"
            "guard let existing = UnsafePointer<T?>(bitPattern: UInt(" + str(pointer) +
            "))!.pointee else { return \"E_PREFLIGHT_NIL\" }\n"
            "return String(reflecting: existing)\n}\n"
            "return _openExistential(resolved, do: read)\n})()")
        value = frame.EvaluateExpression(expression, options)
        require(value.GetError().Success(), "preflight_read:" + str(value.GetError())[:1200])
        text = json.loads(value.GetSummary())
        require(isinstance(text, str) and text.startswith(
            "ProtobufMessages.Anytype_Rpc.Object.Show.Response:\n")
            and "objectView {" in text and len(text.encode()) <= 4_194_304,
            "bounded_original_preflight_text_serialization_required")
        raw = text.encode()
        path = Path(context["work"]) / "private-original-preflight.textproto"
        with path.open("xb") as stream:
            stream.write(raw)
        context["preflightObservation"] = {"status": "CAPTURED", "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "readOnlySerialization": True,
            "format": "original-SwiftProtobuf-Debug-textFormatString"}
    except BaseException as error:
        context["preflightObservation"] = {"status": "READ_FAILED",
            "type": type(error).__name__, "message": str(error)[:1400]}
    write(Path(context["work"]) / "reply-observation.json", context)
    return False


def observe_throw(frame, location, _):
    context = CONTEXT
    pc = frame.GetPC()
    context["validationThrow"] = context["qualifiedThrowAddresses"].get(str(pc), {"unqualifiedPC": pc})
    context["validationStack"] = [
        {"function": frame.GetThread().GetFrameAtIndex(i).GetFunctionName()}
        for i in range(min(12, frame.GetThread().GetNumFrames()))
    ]
    write(Path(context["work"]) / "reply-observation.json", context)
    return True


def main(debugger, configuration_path):
    import lldb
    global CONTEXT
    os.umask(0o077)
    config = json.loads(Path(configuration_path).read_bytes())
    context = {**config, "status": "ATTACHING", "hits": 0, "mode": "LOCAL_DIAGNOSTIC",
               "acceptanceCredit": 0, "startedAt": time.time(), "symbol": SYMBOL,
               "verifiedBoundaryOffset": PREFIX_BYTES, "dataStackOffset": DATA_STACK_OFFSET}
    CONTEXT = context
    process = None
    bp = None
    validation_bps = []
    try:
        require(set(config) == {"pid", "udid", "work", "appPath"}, "exact_configuration_required")
        require(isinstance(config["pid"], int) and config["pid"] > 1, "owned_pid_required")
        command = subprocess.run(["ps", "-p", str(config["pid"]), "-o", "command="],
                                 capture_output=True, text=True, check=True).stdout.strip()
        require(config["udid"].lower() in command.lower()
                and "/Anytype.app/Anytype" in command
                and "/CoreSimulator/Devices/" in command, "owned_app_process_required")
        debugger.SetAsync(False)
        summary_setting = lldb.SBCommandReturnObject()
        debugger.GetCommandInterpreter().HandleCommand(
            "settings set target.max-string-summary-length 5600000", summary_setting)
        require(summary_setting.Succeeded(), "supported_bounded_data_summary_required")
        context["maxStringSummaryLength"] = 5_600_000
        context["summaryBoundHostQualification"] = "bf8174b8a05e170f64d296fbe16f34427ca331c5"
        target = debugger.CreateTarget(str(Path(config["appPath"]) / "Anytype"))
        require(target.IsValid(), "original_app_target_required")
        error = lldb.SBError()
        context["attachStartedAt"] = time.time()
        process = target.AttachToProcessWithID(lldb.SBListener("page-native-reply"), config["pid"], error)
        require(error.Success() and process.IsValid(), "owned_attach_failed:" + str(error))
        mapping = json.loads((Path(__file__).parent / "boundaries.json").read_bytes())
        modules = [target.GetModuleAtIndex(i) for i in range(target.GetNumModules())]
        modules = [m for m in modules if m.GetFileSpec().GetFilename() == "ProtobufMessages"]
        require(len(modules) == 1, "one_original_protobuf_image_required")
        module = modules[0]
        decode = mapping.pop("decode")
        require(decode["symbol"] == SYMBOL and decode["prefix72SHA256"] == PREFIX_SHA,
                "qualified_decode_boundary_changed")
        address = module.ResolveFileAddress(decode["linkedAddress"]).GetLoadAddress(target)
        require(address != lldb.LLDB_INVALID_ADDRESS, "loaded_decode_address_required")
        raw = process.ReadMemory(address, PREFIX_BYTES, error)
        require(error.Success() and hashlib.sha256(raw).hexdigest() == PREFIX_SHA,
                "exact_original_decode_prologue_required")
        symbols = {}
        for key, row in mapping.items():
            start = module.ResolveFileAddress(row["linkedAddress"]).GetLoadAddress(target)
            require(start != lldb.LLDB_INVALID_ADDRESS, "qualified_validation_image_address:" + key)
            actual = process.ReadMemory(start, row["size"], error)
            require(error.Success() and hashlib.sha256(actual).hexdigest() == row["sha256"],
                    "original_validation_code_changed:" + key)
            symbols[key] = start
        context["qualifiedThrowAddresses"] = {}
        for key, row in mapping.items():
            for site in row["throwSites"]:
                destination = symbols[key] + site["offset"]
                context["qualifiedThrowAddresses"][str(destination)] = {"function": key, **site}
                observed = target.BreakpointCreateByAddress(destination)
                require(observed.IsValid() and observed.GetNumLocations() == 1, "qualified_throw_boundary")
                observed.SetScriptCallbackFunction(__name__ + ".observe_throw")
                validation_bps.append(observed)
        observed = target.BreakpointCreateByAddress(symbols["validatedEvent"] + 40)
        require(observed.IsValid() and observed.GetNumLocations() == 1, "qualified_preflight_boundary")
        observed.SetOneShot(True)
        observed.SetScriptCallbackFunction(__name__ + ".observe_preflight")
        validation_bps.append(observed)
        context["breakpointAddress"] = address + PREFIX_BYTES
        bp = target.BreakpointCreateByAddress(context["breakpointAddress"])
        require(bp.IsValid() and bp.GetNumLocations() == 1, "one_exact_boundary_required")
        bp.SetOneShot(True)
        bp.SetScriptCallbackFunction(__name__ + ".capture")
        context["breakpointsReadyAt"] = time.time()
        context["status"] = "WAITING_FOR_ORIGINAL_CAPTURE"
        write(Path(config["work"]) / "reply-observation.json", context)
        error = process.Continue()
        require(error.Success(), "owned_continue_failed:" + str(error))
        require(context["status"] == "CAPTURED_ORIGINAL_REPLY" and context["hits"] == 1,
                "original_reply_not_captured")
        error = process.Continue()
        require(error.Success(), "owned_validation_continue_failed")
        require(context.get("validationThrow"), "actual_validation_throw_not_captured")
    except BaseException as error:
        context["status"] = "OBSERVATION_FAILED"
        failure = {"type": type(error).__name__, "message": str(error)[:1000]}
        context.setdefault("firstFailure", {"phase": context.get("phase"), **failure})
        context.setdefault("error", failure)
    finally:
        for observed in validation_bps:
            observed.SetEnabled(False)
        if bp is not None and bp.IsValid():
            bp.SetEnabled(False)
        if process is not None and process.IsValid():
            error = process.Detach()
            context["detachSucceeded"] = error.Success()
            if not error.Success():
                context["status"] = "OBSERVATION_FAILED"
                context["detachError"] = str(error)[:500]
        context["finishedAt"] = time.time()
        write(Path(config["work"]) / "reply-observation.json", context)
