#!/usr/bin/env python3
"""Prepare/build only an isolated one-shot HTTP watchdog Engine; never edits production."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, difflib, hashlib, importlib.util, json, os, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
V3=ROOT/"build/any-engine-port/http-trace-engine-v3-20261119-213528-034500/reusable-trace-engine-v3.json"
V3_SHA="823620ea96ab33feb9e26f0013bec018a7ec55acfe1631a212eb170575de8181"
BOUNDED=ROOT/"Tools/AnyEngineValidation/run_native_torah_probe.py"
BOUNDED_SHA="019bb3d4b20324c4a1e5987c602d6863b01770cd27553bf62dbc423f539336e4"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8",newline="\n")
def sources():
    base=ROOT/"Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine"
    return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob("*.swift"))}
SWIFT=r'''
// DIAGNOSTIC COPY ONLY. This API is intentionally absent from production.
// The ignored CLI copy arms it immediately after the unchanged hierarchy gate11.
public enum AnyHTTPDiagnosticWatchdog {
    public static func armAfterHierarchyGate11() {
        pinkhaWatchdogActivation.arm()
        pinkhaWatchdogEvent(phase: "armed", originalID: nil, path: nil)
    }
}

// Safety: all shared flags use lock. No original request is retried or cancelled.
private final class PinkhaWatchdogActivation: @unchecked Sendable {
    private let lock = NSLock()
    private var armed = false
    private var activated = false
    func arm() {
        lock.lock()
        armed = true
        lock.unlock()
    }
    func mayObserve() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return armed && !activated
    }
    func activateOnce() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        guard armed && !activated else { return false }
        activated = true
        return true
    }
}
private let pinkhaWatchdogActivation = PinkhaWatchdogActivation()

// Safety: mutable originalCompleted/fired/monitor state is exclusively locked.
// The detached control does not inherit cancellation from a business request.
// It only reads auth/health, never returns its result into the business call.
private final class PinkhaPendingHTTPObservation: @unchecked Sendable {
    private let lock = NSLock()
    private let request: URLRequest
    private let originalID: String
    private let freshSession: @Sendable () -> URLSession
    private var originalFinished = false
    private var fired = false
    private var monitor: Task<Void, Never>?

    private init(request: URLRequest, originalID: String,
                 freshSession: @escaping @Sendable () -> URLSession) {
        self.request = request
        self.originalID = originalID
        self.freshSession = freshSession
    }
    static func start(request: URLRequest, originalID: String,
                      freshSession: @escaping @Sendable () -> URLSession) -> PinkhaPendingHTTPObservation? {
        guard pinkhaWatchdogActivation.mayObserve(), request.httpMethod == "GET",
              request.httpBody == nil, request.url?.query == nil,
              ["/v1/auth", "/v1/health"].contains(request.url?.path ?? "") else { return nil }
        let observation = PinkhaPendingHTTPObservation(
            request: request, originalID: originalID, freshSession: freshSession)
        observation.startTimer()
        return observation
    }
    private func startTimer() {
        let task = Task.detached(priority: .utility) { [weak self] in
            do { try await Task.sleep(nanoseconds: 1_000_000_000) }
            catch { return }
            guard let self, self.activateIfPending() else { return }
            await self.runControl()
        }
        lock.lock()
        monitor = task
        lock.unlock()
    }
    private func activateIfPending() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        guard !originalFinished, pinkhaWatchdogActivation.activateOnce() else { return false }
        fired = true
        return true
    }
    func originalCompleted() {
        lock.lock()
        originalFinished = true
        let toCancel = fired ? nil : monitor
        if !fired { monitor = nil }
        lock.unlock()
        toCancel?.cancel()
    }
    private func controlCompleted() {
        lock.lock()
        monitor = nil
        lock.unlock()
    }
    private func runControl() async {
        let path = request.url?.path ?? ""
        pinkhaWatchdogEvent(phase: "activate", originalID: originalID, path: path)
        let controlSession = freshSession()
        defer {
            // This is only the new control session. The original remains untouched.
            controlSession.invalidateAndCancel()
            controlCompleted()
            pinkhaWatchdogEvent(phase: "closed", originalID: originalID, path: path)
        }
        var controlRequest = request
        // The sole configuration difference is the explicitly bounded control.
        // Headers (including any opaque managed token) are copied, never logged.
        controlRequest.timeoutInterval = 10
        pinkhaWatchdogEvent(phase: "begin", originalID: originalID, path: path)
        do {
            let (data, response) = try await controlSession.data(for: controlRequest)
            pinkhaWatchdogEvent(phase: "response", originalID: originalID, path: path,
                                response: response as? HTTPURLResponse, byteCount: data.count)
        } catch {
            // No localized description, arbitrary NSError data or payload is exported.
            pinkhaWatchdogEvent(phase: "transport-error", originalID: originalID, path: path)
        }
    }
}

private func pinkhaWatchdogEvent(phase: String, originalID: String?, path: String?,
                                response: HTTPURLResponse? = nil, byteCount: Int? = nil) {
    var event: [String: Any] = [
        "phase": phase,
        "timestampUnixMs": Int64((Date().timeIntervalSince1970 * 1000).rounded(.down))
    ]
    if let originalID { event["originalRequestID"] = originalID }
    if let path {
        event["method"] = "GET"
        event["path"] = path
    }
    if let byteCount { event["byteCount"] = byteCount }
    if let response {
        event["status"] = response.statusCode
        var framing: [String: String] = [:]
        if let value = response.value(forHTTPHeaderField: "Content-Length") {
            framing["Content-Length"] = value.utf8.count <= 20 && !value.isEmpty &&
                value.utf8.allSatisfy({ (48...57).contains($0) }) ? value : "invalid"
        }
        if let value = response.value(forHTTPHeaderField: "Transfer-Encoding") {
            let value = value.lowercased().trimmingCharacters(in: .whitespaces)
            framing["Transfer-Encoding"] = ["chunked", "identity", "gzip", "deflate"].contains(value) ? value : "other"
        }
        if let value = response.value(forHTTPHeaderField: "Connection") {
            let value = value.lowercased().trimmingCharacters(in: .whitespaces)
            framing["Connection"] = ["close", "keep-alive"].contains(value) ? value : "other"
        }
        event["framing"] = framing
    }
    if let data = try? JSONSerialization.data(withJSONObject: event, options: [.sortedKeys]) {
        var line = Data("ANY_HTTP_WATCHDOG ".utf8)
        line.append(data)
        line.append(Data([10]))
        FileHandle.standardError.write(line)
    }
}
'''
def prepare():
    if sha(V3)!=V3_SHA:raise RuntimeError("v3 manifest drift")
    v3=json.loads(V3.read_text(encoding="utf-8"))
    if sources()!=v3["originalEngineSourceManifest"]:raise RuntimeError("Production source drift")
    if sha(BOUNDED)!=BOUNDED_SHA:raise RuntimeError("Bounded helper drift")
    oldwork=(ROOT/v3["compiledFiles"]["PinkhaAnyEngine.o"]["path"]).parent
    v3receipt=json.loads((oldwork/"build-receipt.json").read_text(encoding="utf-8"))
    work=ROOT/"build/any-engine-port"/("http-watchdog-engine-v4-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    (work/"Modules").mkdir(parents=True,exist_ok=False)
    for relative,expected in v3["copiedEngineSourceManifest"].items():
        source=oldwork/"EngineSources"/relative
        if sha(source)!=expected:raise RuntimeError("v3 copied source drift")
        target=work/"EngineSources"/relative
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
    client=work/"EngineSources/AnyHTTPClient.swift"
    original=client.read_text(encoding="utf-8")
    needle='''        do { (data, response) = try await session.data(for: request) }
        catch {
            pinkhaDiagnosticHTTPTrace'''
    replacement='''        let diagnosticWatchdog = PinkhaPendingHTTPObservation.start(
            request: request, originalID: diagnosticID) {
                URLSession(configuration: self.session.configuration,
                           delegate: RejectRedirects(), delegateQueue: nil)
            }
        defer { diagnosticWatchdog?.originalCompleted() }
        do {
            (data, response) = try await session.data(for: request)
            diagnosticWatchdog?.originalCompleted()
        }
        catch {
            diagnosticWatchdog?.originalCompleted()
            pinkhaDiagnosticHTTPTrace'''
    if original.count(needle)!=1:raise RuntimeError("Exact raw-await insertion not found")
    modified=original.replace(needle,replacement)+SWIFT
    client.write_text(modified,encoding="utf-8",newline="\n")
    patch=work/"AnyHTTPClient.watchdog-v4.diff"
    patch.write_text("".join(difflib.unified_diff(original.splitlines(keepends=True),modified.splitlines(keepends=True),fromfile="v3/AnyHTTPClient.swift",tofile="v4/AnyHTTPClient.swift")),encoding="utf-8",newline="\n")
    manifest={p.relative_to(work/"EngineSources").as_posix():sha(p) for p in sorted((work/"EngineSources").rglob("*.swift"))}
    changed=[p for p,h in manifest.items() if v3["copiedEngineSourceManifest"].get(p)!=h]
    if changed!=["AnyHTTPClient.swift"]:raise RuntimeError("Unexpected changes")
    rebase=lambda command:[v.replace(str(oldwork),str(work)) for v in command]
    record={"schemaVersion":1,"status":"PREPARED_SOURCE_ONLY","scope":"one_shot_same_process_fresh_session_watchdog",
        "createdAt":now(),"v3ProvenancePath":V3.relative_to(ROOT).as_posix(),"v3ProvenanceSHA256":sha(V3),
        "runnerPath":Path(__file__).relative_to(ROOT).as_posix(),"runnerSHA256":sha(Path(__file__)),
        "boundedRunnerPath":BOUNDED.relative_to(ROOT).as_posix(),"boundedRunnerSHA256":sha(BOUNDED),
        "originalEngineSourceManifest":sources(),"copiedEngineSourceManifest":manifest,
        "changedFromV3":changed,"cachedModuleManifest":v3receipt["cachedModuleManifest"],
        "compilerSHA256":v3receipt["compilerSHA256"],"compilerCommand":rebase(v3["compilerCommand"]),
        "modulewrapCommand":rebase(v3["modulewrapCommand"]),"diagnosticPatch":patch.relative_to(ROOT).as_posix(),
        "diagnosticPatchSHA256":sha(patch),"originalRequestTimeoutSeconds":30,"controlRequestTimeoutSeconds":10,
        "watchdogDelaySeconds":1,"maximumActivations":1,"businessResultsUseControlResponse":False,
        "productionSourceChanged":False,"businessAssertionsChanged":False,"buildOnly":True,"executedNativeChecks":0}
    dump(work/"prepared.json",record)
    print(json.dumps({"status":record["status"],"work":str(work),"preparedSHA256":sha(work/"prepared.json"),
        "runnerSHA256":record["runnerSHA256"],"patchSHA256":sha(patch),"copiedClientSHA256":sha(client)},indent=2))
def build(work):
    work=Path(work).resolve()
    if work.parent!=ROOT/"build/any-engine-port" or not work.name.startswith("http-watchdog-engine-v4-"):
        raise RuntimeError("Unexpected work path")
    prepared=work/"prepared.json"
    record=json.loads(prepared.read_text(encoding="utf-8"))
    if record["status"]!="PREPARED_SOURCE_ONLY":raise RuntimeError("Not a prepared source")
    if (work/"build-receipt.json").exists():raise RuntimeError("Never overwrite a previous attempt")
    if sha(Path(__file__))!=record["runnerSHA256"] or sha(BOUNDED)!=record["boundedRunnerSHA256"]:raise RuntimeError("Runner drift")
    if sources()!=record["originalEngineSourceManifest"]:raise RuntimeError("Production drift")
    if any(sha(work/"EngineSources"/p)!=h for p,h in record["copiedEngineSourceManifest"].items()):raise RuntimeError("Copy drift")
    if any(sha(ROOT/p)!=h for p,h in record["cachedModuleManifest"].items()):raise RuntimeError("Cached module drift")
    compiler=Path(record["compilerCommand"][0])
    if sha(compiler)!=record["compilerSHA256"]:raise RuntimeError("Compiler drift")
    if shutil.disk_usage(ROOT).free<1024**3:raise RuntimeError("Less than1GiB free")
    spec=importlib.util.spec_from_file_location("bounded_torah_runner",BOUNDED)
    bounded=importlib.util.module_from_spec(spec);spec.loader.exec_module(bounded)
    env=dict(os.environ);env["PATH"]=str(compiler.parent)+os.pathsep+env.get("PATH","")
    record.update(status="RUNNING_BUILD_ONLY",startedAt=now(),preparedSHA256=sha(prepared))
    output=work/"build-receipt.json";log=work/"build.log"
    dump(output,record);ok=False;stage="engine_compile"
    try:
        with log.open("wb") as f:code=bounded.bounded(record["compilerCommand"],cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT,seconds=120)
        record["engineCompileExitCode"]=code
        if code:raise RuntimeError("Engine compile failed")
        stage="modulewrap"
        with log.open("ab") as f:code=bounded.bounded(record["modulewrapCommand"],cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT,seconds=30)
        record["modulewrapExitCode"]=code
        if code:raise RuntimeError("Modulewrap failed")
        record["compiledFiles"]={}
        for relative in ["PinkhaAnyEngine.o","PinkhaAnyEngine.swiftmodule.o","Modules/PinkhaAnyEngine.swiftmodule","Modules/PinkhaAnyEngine.swiftdoc","Modules/PinkhaAnyEngine.swiftsourceinfo"]:
            path=work/relative
            if path.is_file():record["compiledFiles"][relative]={"path":path.relative_to(ROOT).as_posix(),"sha256":sha(path),"bytes":path.stat().st_size}
        ok=all(p in record["compiledFiles"] for p in ["PinkhaAnyEngine.o","PinkhaAnyEngine.swiftmodule.o"])
    except Exception as error:record["failure"]={"stage":stage,"kind":type(error).__name__}
    record.update(sourceStable=sources()==record["originalEngineSourceManifest"],
        copiedSourcesStable=all(sha(work/"EngineSources"/p)==h for p,h in record["copiedEngineSourceManifest"].items()),
        cachedModulesStable=all(sha(ROOT/p)==h for p,h in record["cachedModuleManifest"].items()),
        compilerUnchanged=sha(compiler)==record["compilerSHA256"],
        runnerUnchanged=sha(Path(__file__))==record["runnerSHA256"],boundedRunnerUnchanged=sha(BOUNDED)==record["boundedRunnerSHA256"],
        buildLog=log.relative_to(ROOT).as_posix(),buildLogSHA256=sha(log),finishedAt=now())
    stable=all(record[k] for k in ["sourceStable","copiedSourcesStable","cachedModulesStable","compilerUnchanged","runnerUnchanged","boundedRunnerUnchanged"])
    record["status"]="PASS_BUILD_ONLY" if ok and stable else "FAIL"
    dump(output,record)
    if record["status"]=="PASS_BUILD_ONLY":
        manifest={k:record[k] for k in ["originalEngineSourceManifest","copiedEngineSourceManifest","compiledFiles","compilerCommand","modulewrapCommand"]}
        manifest.update(schemaVersion=1,buildReceipt=output.relative_to(ROOT).as_posix(),buildReceiptSHA256=sha(output),
            diagnosticPatch=record["diagnosticPatch"],diagnosticPatchSHA256=record["diagnosticPatchSHA256"],
            changedEngineFiles=record["changedFromV3"],scope=record["scope"])
        dump(work/"reusable-watchdog-engine-v4.json",manifest)
    print(json.dumps({"status":record["status"],"buildReceipt":str(output),"buildReceiptSHA256":sha(output),
        "engineCompileExitCode":record.get("engineCompileExitCode"),"modulewrapExitCode":record.get("modulewrapExitCode"),
        "sourceStable":record["sourceStable"],"cachedModulesStable":record["cachedModulesStable"],
        "reusableManifestSHA256":sha(work/"reusable-watchdog-engine-v4.json") if (work/"reusable-watchdog-engine-v4.json").exists() else None},indent=2))
    if not ok:print(log.read_text(encoding="utf-8",errors="replace")[-12000:])
    return 0 if record["status"]=="PASS_BUILD_ONLY" else 1
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--prepare",action="store_true")
    choice.add_argument("--build")
    a=parser.parse_args()
    return prepare() if a.prepare else build(a.build)
if __name__=="__main__":sys.exit(main())
