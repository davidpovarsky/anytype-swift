"""Independent read-only accounting for four new loaded-account native controls."""
import hashlib
import json
import pathlib
import re
import stat

METHODS = [
 "TestLoadedAccountWitnessBindsActualAccountSessionAndHead",
 "TestLoadedAccountWitnessRefusesUnboundSessionsAndLoadFallback",
 "TestLoadedAccountWitnessACLAndSessionCancellationReleaseActualLocks",
 "TestLoadedAccountWitnessRejectsForeignOwnerStoredHeadAndStoppedApp",
]
LABELS = ["authorized","after-refusals","after-cancellation","restored-head"]
AUTHORITY = "heart-owned-local-store-v1"
REQUIRED_GATE_FRAMES = [
 "github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage.(*storageService).lockSpace",
 "github.com/anyproto/anytype-heart/space/spacecore/storage/anystorage.(*LocalSnapshotCapability).AcquireWitnessLease",
 "github.com/anyproto/anytype-heart/core/pinkha/localstorewitness.CaptureNativeOwned",
 "github.com/anyproto/anytype-heart/core/application.(*Service).CaptureLoadedAccountWitness",
]
OBSERVATIONS = [
 {"realLocalOnlyAccount":True,"realMnemonicFullSession":True,"actualNativeOwnedStore":True,
  "actualHeldACLHeadJoin":True,"productionDestinationCalls":0},
 {"wrongAccountRefused":True,"unregisteredTokenRefused":True,"wrongSigningKeyRefused":True,
  "refusedRegisteredScopes":["limited","json-api"],"trackedAppAssociationValuesRefused":2,
  "actualLifecycleWriterBusyRefused":True,"actualSessionMutexBusyRefused":True,
  "canceledRequestRefused":True,"missingSpaceInventoryUnchanged":True,
  "normalCloseSessionRevoked":True,"appLinkMintFlowExercised":False},
 {"actualACLWriterBusyRefused":True,"concreteACLForwarderRefused":True,
  "concreteSpaceForwarderRefused":True,"copiedLeaseOperationsRefused":3,
  "zeroLeaseCloseRefused":True,"genuineLeaseClosedThenReacquired":True,
  "canceledRealLeaseReleased":True,"actualNativeGateHeldByFixture":True,
  "sessionLockPassedBeforeNativeGate":True,"contextObserverPreservedOriginalChannel":True,
  "actualApplicationReadLockObservedHeld":True,"normalSessionCloseCompleted":True,
  "cancellationPreserved":True,"actualGateHolderUnaffected":True},
 {"actualCurrentNativeOwnerAccepted":True,"differentNativeProviderRefused":True,
  "foreignProviderOpenedStore":False,"actualStoredHeadMismatchRefused":True,
  "exactOriginalStoredHeadRestored":True,"sourceFixtureOnlyMutation":True},
]

def require(value,reason):
    if not value:raise ValueError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def same_typed(actual,expected):
    if type(actual) is not type(expected):return False
    if isinstance(expected,dict):
        return set(actual)==set(expected) and all(same_typed(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):
        return len(actual)==len(expected) and all(same_typed(a,b) for a,b in zip(actual,expected))
    return actual==expected

def strict(raw):
    def pairs(values):
        result={}
        for key,value in values:
            require(key not in result,"duplicate_json_key");result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite_json")))

def private_dir(path):
    value=path.lstat()
    require(stat.S_ISDIR(value.st_mode) and not path.is_symlink() and path.resolve()==path and
            stat.S_IMODE(value.st_mode) in (0o700,0o2700) and value.st_uid==1001,
            "private_directory_mode_or_origin")

def private_file(path,maximum):
    before=path.lstat()
    require(stat.S_ISREG(before.st_mode) and not path.is_symlink() and path.resolve()==path and
            stat.S_IMODE(before.st_mode)==0o600 and before.st_uid==1001 and before.st_nlink==1 and
            0<before.st_size<=maximum,"private_file_shape")
    raw=path.read_bytes();after=path.lstat()
    fields=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
    require(all(getattr(before,k)==getattr(after,k) for k in fields),"private_file_changed")
    return raw,{"sha256":sha(raw),"bytes":len(raw),"mode":stat.S_IMODE(after.st_mode)}

def safe_receipt(r):
    fixed={"Version":"native-localstore-witness-v1","Encoding":"anyenc-v1.0.3-decoded-value-roundtrip-v1",
           "Authority":AUTHORITY,"InventoryScope":"registered-native-collections-only",
           "NativeBindingScope":"space-state-acl-settings-roots-only"}
    hashes={"OwnerSHA256","SpaceSHA256","SpaceHeaderSHA256","WitnessSHA256"}
    numbers={"Generation","Collections","Rows","EncodedValueBytes"}
    booleans={"LocalDecodedRowsComplete":True,"NativeSnapshotProofRequired":True,
              "NativeIdentityCensusRequired":True,"HasNativeSourceAdmission":False,"PermitsDestinationWrites":False}
    require(type(r) is dict and set(r)==set(fixed)|hashes|numbers|set(booleans)|{"CollectionCoverage"},
            "native_receipt_shape")
    require(all(same_typed(r[k],v) for k,v in fixed.items()),"native_receipt_fixed_scope")
    require(all(type(r[k]) is bool and r[k] is v for k,v in booleans.items()),"native_receipt_authority")
    require(all(type(r[k]) is str and re.fullmatch(r"[0-9a-f]{64}",r[k]) for k in hashes),"native_receipt_hash")
    require(all(type(r[k]) is int and r[k]>=0 for k in numbers) and r["Generation"]>0,"native_receipt_counts")
    coverage=r["CollectionCoverage"]
    require(type(coverage) is list and len(coverage)==r["Collections"] and 0<len(coverage)<=64,
            "native_receipt_coverage")
    for item in coverage:
        require(type(item) is dict and set(item)=={"NameSHA256","Rows","EncodedValueBytes","UnresolvedCollection"},
                "native_receipt_collection_shape")
        require(type(item["NameSHA256"]) is str and re.fullmatch(r"[0-9a-f]{64}",item["NameSHA256"]) and
                type(item["Rows"]) is int and item["Rows"]>=0 and
                type(item["EncodedValueBytes"]) is int and item["EncodedValueBytes"]>=0 and
                type(item["UnresolvedCollection"]) is bool,"native_receipt_collection_types")
    require(sum(v["Rows"] for v in coverage)==r["Rows"] and
            sum(v["EncodedValueBytes"] for v in coverage)==r["EncodedValueBytes"],"native_receipt_totals")
    return r

def decoded(data):
    nodes=0
    def at(pos,depth):
        nonlocal nodes
        nodes+=1
        require(nodes<=100000 and depth<=64 and pos<len(data),"native_value_bounds")
        tag=data[pos];pos+=1
        if tag in (1,4,5):return (tag,None),pos
        if tag==2:
            require(pos+8<=len(data),"native_number_bounds")
            return (tag,data[pos:pos+8]),pos+8
        if tag==3:
            end=data.find(b"\0",pos);require(end>=pos,"native_string_bounds")
            return (tag,data[pos:end]),end+1
        if tag==8:
            require(pos+4<=len(data),"native_binary_header")
            size=int.from_bytes(data[pos:pos+4],"big");pos+=4
            require(pos+size<=len(data),"native_binary_bounds")
            return (tag,data[pos:pos+size]),pos+size
        if tag in (6,7):
            values=[]
            while True:
                require(pos<len(data),"native_container_bounds")
                if data[pos]==0:return (tag,tuple(values)),pos+1
                if tag==7:
                    end=data.find(b"\0",pos);require(end>=pos,"native_key_bounds")
                    key=data[pos:end]
                    if key==bytes([31]):key=b""
                    value,pos=at(end+1,depth+1);values.append((key,value))
                else:
                    value,pos=at(pos,depth+1);values.append(value)
        raise ValueError("native_encoding_tag")
    value,end=at(0,0);require(end==len(data),"native_value_trailing_bytes")
    return value

def unique(value,key):
    require(value[0]==7,"native_row_not_object")
    values=[v for k,v in value[1] if k==key]
    return values[0] if len(values)==1 else None

def string(value):
    return value[1] if value is not None and value[0]==3 else None

class NativeFrames:
    def __init__(self,data):
        require(type(data) is bytes and 0<len(data)<=64<<20,"native_frame_size")
        self.data,self.at=data,0
    def frame(self):
        require(self.at+8<=len(self.data),"native_frame_length")
        count=int.from_bytes(self.data[self.at:self.at+8],"big");self.at+=8
        require(count<=64<<20 and self.at+count<=len(self.data),"native_frame_bounds")
        value=self.data[self.at:self.at+count];self.at+=count;return value
    def number(self,low,high):
        raw=self.frame();require(len(raw)==8,"native_uint64_frame")
        value=int.from_bytes(raw,"big");require(low<=value<=high,"native_uint64_bound")
        return value

def one_row(collections,name,identity):
    rows=[row for row in collections.get(name,[]) if row["identity"]==(3,identity)]
    require(len(rows)==1,"native_unique_string_row")
    return rows[0]["value"]

def private_native_frame(raw,receipt):
    r=safe_receipt(receipt);require(sha(raw)==r["WitnessSHA256"],"native_frame_receipt_digest")
    f=NativeFrames(raw)
    require(f.frame()==b"pinkha-localstore-witness-v1" and f.frame()==r["Encoding"].encode() and
            f.frame()==AUTHORITY.encode(),"native_frame_header")
    owner,space=f.frame(),f.frame()
    require(len(owner)==32 and space and sha(owner)==r["OwnerSHA256"] and sha(space)==r["SpaceSHA256"],
            "native_frame_identity")
    require(f.number(1,(1<<64)-1)==r["Generation"],"native_generation")
    count=f.number(1,64);require(count==r["Collections"],"native_collection_count")
    collections,names,totals={},[],{"rows":0,"bytes":0,"empty":0}
    for index in range(count):
        name,count_rows=f.frame(),f.number(0,10000)
        require(name and (not names or names[-1]<name),"native_collection_order");names.append(name)
        rows,identities,value_bytes=[],[],0
        for _ in range(count_rows):
            identity_raw,value_raw=f.frame(),f.frame()
            require(len(identity_raw)<=1<<20 and len(value_raw)<=1<<20,"native_row_byte_bound")
            require(not identities or identities[-1]<identity_raw,"native_identity_order");identities.append(identity_raw)
            identity,value=decoded(identity_raw),decoded(value_raw)
            require(unique(value,b"id")==identity,"native_typed_identity_preserved")
            value_bytes+=len(value_raw);rows.append({"identity":identity,"value":value})
        collections[name]=rows;coverage=r["CollectionCoverage"][index]
        require(sha(name)==coverage["NameSHA256"] and count_rows==coverage["Rows"] and
                value_bytes==coverage["EncodedValueBytes"],"native_collection_accounting")
        totals["rows"]+=count_rows;totals["bytes"]+=value_bytes;totals["empty"]+=int(count_rows==0)
    require(f.at==len(raw) and totals["rows"]==r["Rows"]<=10000 and
            totals["bytes"]==r["EncodedValueBytes"]<=16<<20,"native_full_frame_accounting")
    require(len(collections.get(b"state",[]))==1,"native_single_state")
    state=one_row(collections,b"state",space)
    header,acl,settings=unique(state,b"e"),string(unique(state,b"a")),string(unique(state,b"s"))
    require(header is not None and header[0]==8 and header[1] and sha(header[1])==r["SpaceHeaderSHA256"],
            "native_space_header_hash")
    require(acl and settings and acl!=settings and acl!=space,"native_state_root_binding")
    head=one_row(collections,b"heads",acl);one_row(collections,b"heads",settings);one_row(collections,acl,acl)
    settings_root=one_row(collections,b"changes",settings)
    require(string(unique(settings_root,b"t"))==settings,"native_settings_root_owner")
    heads=unique(head,b"h")
    require(heads is not None and heads[0]==6 and len(heads[1])==1,"native_acl_single_head")
    head_id=string(heads[1][0]);require(head_id,"native_acl_head_string")
    deleted=[v for k,v in head[1] if k==b"d"]
    if deleted:
        require(len(deleted)==1 and deleted[0][0]==2 and
                deleted[0][1] in (b"\x80"+b"\0"*7,b"\x7f"+b"\xff"*7),"native_acl_head_deleted")
    for index,name in enumerate(names):
        require(r["CollectionCoverage"][index]["UnresolvedCollection"] is
                (name not in {b"state",b"heads",b"changes",b"_client",acl}),"native_unknown_accounting")
    return {"frameSHA256":r["WitnessSHA256"],"spaceSHA256":sha(space),"aclIdSHA256":sha(acl),
        "aclHeadSHA256":sha(head_id),"collections":count,"rows":totals["rows"],
        "emptyCollections":totals["empty"],"encodedValueBytes":totals["bytes"],
        "allCapturedRowsIndependentlyParsed":True,"rawValuesPublished":False,
        "semanticReconstruction":False,"hasNativeSourceAdmission":False,"permitsDestinationWrites":False}


def typed_fields(value,fixed,hashes,extra,reason):
    require(type(value) is dict and set(value)==set(fixed)|set(hashes)|set(extra),reason+"_shape")
    require(all(same_typed(value[k],v) for k,v in fixed.items()),reason+"_fixed")
    require(all(type(value[k]) is str and re.fullmatch(r"[0-9a-f]{64}",value[k]) for k in hashes),
            reason+"_hashes")
    return value

def account_receipt(value,frame):
    outer_fixed={
        "version":"loaded-account-native-witness-v1",
        "accountAuthority":"held-application-account-directory-lease-v1",
        "sessionAuthority":"validated-native-full-unassociated-session-v1",
        "accountSessionAuthorizedAtCapture":True,"nativeIdentityCensusRequired":True,
        "hasNativeSourceAdmission":False,"semanticCompleteness":False,
        "filePayloadCompleteness":False,"permitsDestinationWrites":False,
    }
    outer=typed_fields(value,outer_fixed,{"accountSHA256","accountDirectorySHA256"},{"source"},"account_receipt")
    inner_fixed={
        "version":"loaded-native-acl-witness-v1","localPermission":"owner",
        "alreadyLoaded":True,"aclReadAuthorizedAtCapture":True,"accountSessionAuthorized":False,
        "remoteFreshnessEstablished":False,"semanticCompleteness":False,
        "filePayloadCompleteness":False,"hasNativeSourceAdmission":False,"permitsDestinationWrites":False,
    }
    source=typed_fields(outer["source"],inner_fixed,
        {"accountSHA256","spaceSHA256","aclIdSHA256","aclHeadSHA256"},{"native"},"loaded_space_receipt")
    require(source["accountSHA256"]==outer["accountSHA256"],"actual_account_receipt_join")
    native=private_native_frame(frame,source["native"])
    for key in ("spaceSHA256","aclIdSHA256","aclHeadSHA256"):
        require(native[key]==source[key],"actual_captured_acl_join")
    return {"accountSHA256":outer["accountSHA256"],"accountDirectorySHA256":outer["accountDirectorySHA256"],
        "accountSessionAuthorizedAtCapture":True,"alreadyLoaded":True,
        "native":native,"semanticCompleteness":False,"filePayloadCompleteness":False,
        "hasNativeSourceAdmission":False,"permitsDestinationWrites":False}

def method_events(stdout,method):
    raw,original=private_file(stdout,8<<20)
    text=raw.decode("utf-8","strict")
    starts=re.findall(r"(?m)^=== RUN   (.+)$",text)
    terminals=re.findall(r"(?m)^--- (PASS|FAIL|SKIP): ([^\s]+) \(([^)\r\n]+)\)$",text)
    package=re.findall(r"(?m)^(PASS|FAIL)$",text)
    require(starts==[method] and len(terminals)==1 and terminals[0][:2]==("PASS",method) and
            re.fullmatch(r"\d+(?:\.\d+)?s",terminals[0][2]) is not None and package==["PASS"],
            "actual_named_native_method_pass_required")
    observations=re.findall(
        r"(?m)^\s+loaded_witness(?:_fixture)?_test\.go:\d+: LOADED_ACCOUNT_NATIVE_OBSERVATION "
        r"label=([a-z-]+) witness_sha256=([0-9a-f]{64}) frame_bytes=(\d+)$",text)
    require(len(observations)==1,"actual_single_native_observation_required")
    label,digest,size=observations[0]
    return {"method":method,"start":starts[0],"terminal":terminals[0][0],"package":package[0],
            "elapsed":terminals[0][2],"observation":{"label":label,"sha256":digest,"bytes":int(size)},
            "original":original}

def audit_method(root,stdout,method):
    require(method in METHODS,"fixed_method_only")
    index=METHODS.index(method);label=LABELS[index]
    private_dir(root);directory=root/method;private_dir(directory)
    safe_raw,safe_file=private_file(directory/(label+".json"),128<<10)
    frame,frame_file=private_file(directory/(label+".witness"),64<<20)
    completion_raw,completion_file=private_file(directory/"completion.json",128<<10)
    value=strict(safe_raw);completion=strict(completion_raw)
    require(type(value) is dict and set(value)==
            {"protocol","method","label","frameSHA256","frameBytes","receipt","observations"},
            "private_method_observation_shape")
    require(value["protocol"]=="loaded-account-native-acceptance-v1" and
            value["method"]==method and value["label"]==label,"private_method_identity")
    require(type(value["frameSHA256"]) is str and value["frameSHA256"]==sha(frame) and
            type(value["frameBytes"]) is int and value["frameBytes"]==len(frame),
            "private_method_frame_binding")
    expected=dict(OBSERVATIONS[index])
    observation=value["observations"]
    if index==2:
        require(type(observation) is dict and set(observation)==set(expected)|{"nativeGateCallsiteObservation"},
                "actual_native_gate_observation_shape")
        gate=observation["nativeGateCallsiteObservation"]
        require(type(gate) is dict and set(gate)=={"functions"} and type(gate["functions"]) is list and
                4<=len(gate["functions"])<=32 and all(type(v) is str for v in gate["functions"]) and
                all(v in gate["functions"] for v in REQUIRED_GATE_FRAMES),
                "actual_native_gate_callsite_frames")
        expected["nativeGateCallsiteObservation"]=gate
    require(same_typed(observation,expected),"actual_native_assertions")
    expected_completion={"method":method,"completed":True,"frames":[label]}
    if index==0:
        expected_completion.update(assertedSemanticCompleteness=False,assertedDestinationPermission=False)
    elif index==2:
        expected_completion["actualClosedACLRefused"]=True
    elif index==3:
        expected_completion.update(actualAccountStopCompleted=True,stoppedAppCaptureRefused=True,
                                   stoppedNativeOwnerRefused=True)
    require(same_typed(completion,expected_completion),"actual_method_completion")
    events=method_events(stdout,method)
    require(events["observation"]=={"label":label,"sha256":sha(frame),"bytes":len(frame)},
            "actual_raw_log_private_frame_join")
    receipt=account_receipt(value["receipt"],frame)
    require(receipt["native"]["frameSHA256"]==value["frameSHA256"],"actual_native_safe_private_join")
    return {"schema":"loaded-account-native-method-audit-v1","status":"PASS",
        "method":method,"label":label,"actual_named_events":events,
        "private_originals":{"observation":safe_file,"native_frame":frame_file,"completion":completion_file},
        "receipt":receipt,"exact_typed_assertions":True,"exact_completion":True,
        "all_native_rows_and_collections_accounted":True,
        "test_only_callsite_observation":index==2,
        "session_closer_already_blocked_claim":False,
        "old_methods_replayed":0,"raw_private_values_published":False,
        "semanticCompleteness":False,"filePayloadCompleteness":False,
        "hasNativeSourceAdmission":False,"permitsDestinationWrites":False}
