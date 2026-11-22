from pathlib import Path
import hashlib,json,subprocess,difflib,datetime,time
common=Path(r"C:\Users\DAVID\Code\anytype-original-annotation-metadata-20261122")
work=Path(r"C:\Users\DAVID\Code\anytype-original-held-read-20261122")
temp=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-held-read-implementation-20261122")
base="18ac6d39dfe76b12e5dead9627c831c6a88d073c"
branch="codex/otzaria-original-held-read-adapter-20261122"
path="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift"
types="\nstruct OriginalAnnotationHeldReadObservation: Sendable {\n    let objectView: Anytype_Model_ObjectView\n    let rootDetails: Google_Protobuf_Struct\n\n    fileprivate init(objectView: Anytype_Model_ObjectView,\n                     rootDetails: Google_Protobuf_Struct) {\n        self.objectView = objectView\n        self.rootDetails = rootDetails\n    }\n}\n\nenum OriginalAnnotationHeldReadOutcome<Value: Sendable>: Sendable {\n    case completed(Value)\n    case completedWithoutCurrentOwnership(Value, error: any Error)\n}\n\n@MainActor\nprivate final class OriginalAnnotationHeldReadCompletion<Value: Sendable> {\n    enum State {\n        case notCompleted\n        case completed(Value)\n    }\n\n    var state: State = .notCompleted\n}\n"
methods="\n    func withFreshNativeObservation<Value: Sendable>(\n        consume: @MainActor @Sendable (OriginalAnnotationHeldReadObservation) throws -> Value\n    ) async throws -> OriginalAnnotationHeldReadOutcome<Value> {\n        try validateOwnedRuntime()\n        let identity = requestedIdentity\n        let completion = OriginalAnnotationHeldReadCompletion<Value>()\n        do {\n            let value = try await session.owner.withExclusiveRead(\n                contextId: identity.objectID,\n                spaceId: identity.scope.space,\n                rpcNames: [\"ObjectShow\"]\n            ) { [self] in\n                try await validateOwnedRuntime()\n                let response = try await ClientCommands.objectShow(.with {\n                    $0.contextID = identity.objectID\n                    $0.objectID = identity.objectID\n                    $0.spaceID = identity.scope.space\n                }).invoke(qos: .userInitiated)\n                return try await consumeFreshNativeResponse(\n                    response, completion: completion, consume: consume\n                )\n            }\n            try validateOwnedRuntime()\n            return .completed(value)\n        } catch {\n            switch completion.state {\n            case .notCompleted:\n                throw error\n            case let .completed(value):\n                return .completedWithoutCurrentOwnership(value, error: error)\n            }\n        }\n    }\n\n    private func consumeFreshNativeResponse<Value: Sendable>(\n        _ response: Anytype_Rpc.Object.Show.Response,\n        completion: OriginalAnnotationHeldReadCompletion<Value>,\n        consume: @MainActor @Sendable (OriginalAnnotationHeldReadObservation) throws -> Value\n    ) throws -> Value {\n        try validateOwnedRuntime()\n        _ = try Self.strictDetails(response, requestedIdentity: requestedIdentity)\n        guard let root = response.objectView.details.first(where: {\n            $0.id.utf8.elementsEqual(requestedIdentity.objectID.utf8)\n        }) else {\n            throw OriginalAnnotationObjectReadbackError.wrongObject\n        }\n        let observation = OriginalAnnotationHeldReadObservation(\n            objectView: response.objectView, rootDetails: root.details\n        )\n        let value = try consume(observation)\n        completion.state = .completed(value)\n        try validateOwnedRuntime()\n        return value\n    }\n\n"
assert not work.exists() and not temp.exists()
temp.mkdir();(temp/"prepare-candidate.py").write_bytes(Path(__file__).read_bytes())
commands=[]
def git(args,cwd=work,timeout=90):
    t=time.monotonic();p=subprocess.run(["git",*args],cwd=cwd,capture_output=True,timeout=timeout)
    item={"command":["git",*args],"cwd":str(cwd),"exitCode":p.returncode,"elapsedSeconds":time.monotonic()-t,"stdoutBytes":len(p.stdout),"stdoutSHA256":hashlib.sha256(p.stdout).hexdigest(),"stderr":p.stderr.decode("utf-8","replace")}
    if len(p.stdout)<4096:item["stdout"]=p.stdout.decode("utf-8","replace")
    commands.append(item);(temp/"PREPARATION_COMMANDS.json").write_bytes((json.dumps(commands,indent=2)+"\n").encode())
    assert p.returncode==0,item
    return p.stdout
assert git(["rev-parse","HEAD"],common).decode().strip()==base
assert not git(["status","--porcelain=v1","--untracked-files=all"],common)
upstream=git(["ls-remote","https://github.com/anyproto/anytype-swift.git","refs/heads/develop"],common).decode().strip()
assert len(upstream.split())==2
assert subprocess.run(["git","show-ref","--verify","--quiet","refs/heads/"+branch],cwd=common).returncode==1
before=git(["show",base+":"+path],common)
assert hashlib.sha256(before).hexdigest()=="0d007b5d2ee2bab38218cbdc36b0385f17b8ee95d8579ddaa23626081c602526"
text=before.decode()
old_token="Anytype_Rpc.ObjectShow.Response";new_token="Anytype_Rpc.Object.Show.Response"
assert text.count(old_token)==1 and new_token not in text
corrected=text.replace(old_token,new_token)
type_marker="/// A narrow read adapter for an already prepared original object."
method_marker="    private func validateOwnedRuntime() throws {"
assert corrected.count(type_marker)==1 and corrected.count(method_marker)==1
candidate=corrected.replace(type_marker,types+"\n"+type_marker).replace(method_marker,methods+method_marker).encode()
assert candidate.decode().replace(types+"\n","",1).replace(methods,"",1).replace(new_token,old_token)==text
patch="".join(difflib.unified_diff(text.splitlines(True),candidate.decode().splitlines(True),fromfile="a/"+path,tofile="b/"+path)).encode()
(temp/"PREIMAGE.swift").write_bytes(before);(temp/"CANDIDATE.swift").write_bytes(candidate);(temp/"HELD_READ.patch").write_bytes(patch)
git(["worktree","add","-b",branch,str(work),base],common,timeout=180)
assert git(["rev-parse","HEAD"]).decode().strip()==base
assert not git(["status","--porcelain=v1","--untracked-files=all"])
checked=(work/path).read_bytes()
assert checked==before or checked.replace(b"\r\n",b"\n")==before
(work/path).write_bytes(candidate)
assert git(["diff","--name-only"]).decode().splitlines()==[path]
git(["diff","--check"])
result={"schemaVersion":1,"status":"CANDIDATE_FROZEN_NOT_EXECUTED","base":base,"upstreamDevelop":upstream.split()[0],"branch":branch,"worktree":str(work),"path":path,"preimageBytes":len(before),"preimageSHA256":hashlib.sha256(before).hexdigest(),"candidateBytes":len(candidate),"candidateSHA256":hashlib.sha256(candidate).hexdigest(),"patchSHA256":hashlib.sha256(patch).hexdigest(),"newCommentsRemovedOnly":True,"oldChange":"Exactly one old strictDetails parameter type token: Anytype_Rpc.ObjectShow.Response -> actual generated Anytype_Rpc.Object.Show.Response","oldBodiesAndCommentsUnchanged":True,"inverseRecoversOriginalExact":True,"sourceUncommitted":True,"parseCompileTests":"NOT_RUN","timestampUTC":datetime.datetime.now(datetime.timezone.utc).isoformat()}
(temp/"CANDIDATE_RECEIPT.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
print(json.dumps(result))
