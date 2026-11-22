import os,pathlib,subprocess,json,hashlib,datetime,shutil
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-annotation-metadata-20261122")
packet=repo/"docs/pinkha/torah-integration/production-native-metadata-20261122/controls"
proof=packet/"provenance";proof.mkdir(parents=True,exist_ok=True)
temp=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\omd-20261122")
assert not temp.exists(),"Owned metadata execution directory already exists; inspect instead of overwrite"
temp.mkdir()
dep=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\omd-protobuf-20261122")
assert not dep.exists(),"Dependency directory already exists; inspect immutable checkout before reuse"
ref="b854e7f3f59690134bcabdef88527b61517d5ab5"
pin="c6fe6442e6a64250495669325044052e113e990c"
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,obj):p.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode())
commands=[]
def cmd(label,args,cwd,timeout):
 t=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.Popen(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:out,err=p.communicate(timeout=timeout);timed=False
 except subprocess.TimeoutExpired:
  subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
  out,err=p.communicate(timeout=30);timed=True
 (proof/(label+".stdout")).write_bytes(out);(proof/(label+".stderr")).write_bytes(err)
 row={"label":label,"args":args,"cwd":str(cwd),"started_at":t,"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"pid":p.pid,"exit_code":p.returncode,"timed_out":timed,"stdout_sha256":sha(out),"stderr_sha256":sha(err)}
 commands.append(row);put(proof/"DEPENDENCY_COMMANDS.json",commands)
 assert p.returncode==0 and not timed,row
 return out
product=repo/"Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift"
assert sha(product.read_bytes())=="21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5"
bak=product.with_name(product.name+".bak.20261122-081457-935424")
assert bak.is_file() and bak.read_bytes()==b""
backup=temp/"provenance";backup.mkdir()
moved=backup/bak.name
assert not moved.exists()
shutil.move(str(bak),str(moved));assert moved.read_bytes()==b"" and not bak.exists()
put(proof/"BACKUP_MOVE.json",{"original":str(bak),"retained":str(moved),"bytes":0,"sha256":sha(b""),"source_sha256_unchanged":sha(product.read_bytes()),"move_only_exact_owned_file":True})
lockpath="Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
lock=cmd("original-lock",["git","show",ref+":"+lockpath],repo,30)
assert sha(lock)=="86546dd98acc5d0414c4c10c0b79f82bda02b06c3687d64481547d9ad0368e5a"
locked=json.loads(lock);entries=locked["pins"] if "pins" in locked else locked["object"]["pins"]
entry=[e for e in entries if e.get("identity")=="swift-protobuf" or e.get("package")=="SwiftProtobuf"]
assert len(entry)==1 and entry[0]["state"]["revision"]==pin
dep.mkdir()
cmd("dependency-init",["git","init"],dep,30)
cmd("dependency-crlf",["git","config","core.autocrlf","false"],dep,30)
cmd("dependency-remote",["git","remote","add","origin","https://github.com/apple/swift-protobuf.git"],dep,30)
cmd("dependency-fetch",["git","fetch","--depth","1","origin",pin],dep,240)
cmd("dependency-checkout",["git","checkout","--detach","FETCH_HEAD"],dep,60)
head=cmd("dependency-head",["git","rev-parse","HEAD"],dep,30).decode().strip()
assert head==pin
assert not cmd("dependency-status",["git","status","--porcelain","--untracked-files=all"],dep,30)
tree=cmd("dependency-tree",["git","rev-parse","HEAD^{tree}"],dep,30).decode().strip()
manifest=(dep/"Package.swift").read_bytes()
swiftc=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
swift=swiftc.with_name("swift.exe")
assert swift.is_file() and swiftc.is_file()
version=cmd("swift-version",[str(swift),"--version"],repo,30).decode()
helptext=cmd("swift-test-help",[str(swift),"test","--help"],repo,30).decode()
result={"status":"EXACT_DEPENDENCY_CHECKOUT_PREPARED_NO_TESTS_EXECUTED","base":ref,"lock_path":lockpath,"lock_sha256":sha(lock),"pin_entry":entry[0],"dependency_path":str(dep),"dependency_head":head,"dependency_tree":tree,"dependency_package_sha256":sha(manifest),"swift_path":str(swift),"swift_sha256":sha(swift.read_bytes()),"swiftc_path":str(swiftc),"swiftc_sha256":sha(swiftc.read_bytes()),"swift_version":version,"product_sha256":sha(product.read_bytes()),"owned_temp":str(temp),"test_execution":False}
put(proof/"DEPENDENCY_PREPARATION.json",result)
print(json.dumps({"preparation":result,"dependency_package":manifest.decode(),"swift_test_flags":[l for l in helptext.splitlines() if any(k in l for k in ["skip-build","xunit","swift-testing","filter","scratch","jobs","enable-xctest","disable-xctest"])]}),flush=True)
