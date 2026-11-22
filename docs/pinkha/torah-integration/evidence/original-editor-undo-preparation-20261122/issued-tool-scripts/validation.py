import pathlib,subprocess,json,hashlib,os,datetime,re
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-undo-inference-compile-20261122')
swift=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE')
runtime=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin')
source=(out/'UNDO_CANDIDATE.swift').read_bytes()
assert hashlib.sha256(source).hexdigest()=='0af702fce948504b2408ec043441e5252f914a52070dab07b7b1f50bfffe9250'
text=source.decode()
props=text[text.index('    private var undoPreparation:'):text.index('    var body: some View {')]
button=(out/'ORIGINAL_ASYNC_BUTTON.swift').read_text(encoding='utf8')
decl=next(l.strip() for l in button.splitlines() if l.strip().startswith('let prepareAction:'))
typ=decl.split(': ',1)[1]
assert typ=='(@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?'
probe='''import Foundation

// Fixture only: observes timing at the extracted property/type boundary.
// No SwiftUI, native owner, RPC, original AsyncButton body or UI is executed.
@MainActor
private final class PreparationModelProbe {
    var hasDocumentWriteOwner = false
    var preparedUndo = 0
    var preparedRedo = 0
    var executedUndo = 0
    var executedRedo = 0
    func prepareUndo() -> @MainActor @Sendable () async throws -> Void {
        preparedUndo += 1
        return { self.executedUndo += 1 }
    }
    func prepareRedo() -> @MainActor @Sendable () async throws -> Void {
        preparedRedo += 1
        return { self.executedRedo += 1 }
    }
}

@MainActor
private struct ExtractedPreparationProbe {
    let model: PreparationModelProbe
''' + props + '''
    // Exact original AsyncButton.prepareAction stored type.
    private func acceptedPreparation(_ value: '''+typ+''') -> '''+typ+''' {
        value
    }

    func observe() async throws {
        precondition(acceptedPreparation(undoPreparation) == nil)
        precondition(acceptedPreparation(redoPreparation) == nil)
        precondition(model.preparedUndo == 0 && model.preparedRedo == 0)
        print("PASS legacy owner absence returns nil without preparation")

        model.hasDocumentWriteOwner = true
        let undo = acceptedPreparation(undoPreparation)
        let redo = acceptedPreparation(redoPreparation)
        precondition(undo != nil && redo != nil)
        precondition(model.preparedUndo == 0 && model.preparedRedo == 0)
        precondition(model.executedUndo == 0 && model.executedRedo == 0)
        print("PASS obtaining typed properties defers preparation and operation")

        let preparedUndo = undo!()
        let preparedRedo = redo!()
        precondition(model.preparedUndo == 1 && model.preparedRedo == 1)
        precondition(model.executedUndo == 0 && model.executedRedo == 0)
        print("PASS invoking original-shaped preparation performs only synchronous preparation")

        try await preparedUndo()
        try await preparedRedo()
        precondition(model.preparedUndo == 1 && model.preparedRedo == 1)
        precondition(model.executedUndo == 1 && model.executedRedo == 1)
        print("PASS awaiting returned actions reaches deferred operations")
    }
}
@main
private struct ProbeMain {
    @MainActor static func main() async throws {
        try await ExtractedPreparationProbe(model: PreparationModelProbe()).observe()
    }
}
'''
probe_path=out/'ExtractedPreparationProbe.swift'
assert not probe_path.exists()
probe_path.write_bytes(probe.encode())
record={'schema':1,'candidate_sha256':hashlib.sha256(source).hexdigest(),'property_bytes_sha256':hashlib.sha256(props.encode()).hexdigest(),'original_async_button_sha256':hashlib.sha256((out/'ORIGINAL_ASYNC_BUTTON.swift').read_bytes()).hexdigest(),'original_preparation_type':typ,'probe_sha256':hashlib.sha256(probe_path.read_bytes()).hexdigest(),'scope':'Exact extracted properties and original stored closure type with explicit model timing probe; no SwiftUI, Owner, native RPC, original button body or UI execution. Full-file parse is syntax only.'}
(out/'PROBE_INPUTS.json').write_text(json.dumps(record,indent=2),encoding='utf8')
env=dict(os.environ);env['PATH']=str(runtime)+os.pathsep+str(swift.parent)+os.pathsep+env.get('PATH','');env['PYTHONUTF8']='1'
commands=[]
def run(label,args,timeout):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(args,cwd=out,env=env,capture_output=True,timeout=timeout)
 (out/(label+'.stdout.log')).write_bytes(p.stdout);(out/(label+'.stderr.log')).write_bytes(p.stderr)
 row={'label':label,'command':list(map(str,args)),'cwd':str(out),'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':p.returncode,'timeout_seconds':timeout,'timed_out':False,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()}
 commands.append(row);(out/'VALIDATION_EXECUTION.json').write_text(json.dumps(commands,indent=2),encoding='utf8')
 assert p.returncode==0,(label,p.stderr.decode('utf8','replace'))
 return p.stdout.decode('utf8','replace')
version=run('swift-version',[str(swift),'--version'],30)
run('whole-file-syntax',[str(swift),'-frontend','-parse',str(out/'UNDO_CANDIDATE.swift')],60)
binary=out/'ExtractedPreparationProbe.exe'
run('extracted-type-compile',[str(swift),'-swift-version','6','-strict-concurrency=complete','-parse-as-library',str(probe_path),'-o',str(binary)],180)
output=run('deferred-boundary',[str(binary)],30)
assert output.count('PASS ')==4
assert (out/'UNDO_CANDIDATE.swift').read_bytes()==source
result={'schema':1,'status':'PASS_SYNTAX_AND_EXTRACTED_TYPE_DEFERRED_BOUNDARY','observations':4,'candidate_sha256':record['candidate_sha256'],'properties_sha256':record['property_bytes_sha256'],'probe_sha256':record['probe_sha256'],'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'toolchain':version,'runtime_output':output,'limits':record['scope']}
(out/'VALIDATION_RESULT.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'result':result,'commands':commands}))
