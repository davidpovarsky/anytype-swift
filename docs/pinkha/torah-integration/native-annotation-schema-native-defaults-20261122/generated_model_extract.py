import hashlib,json,pathlib,re,subprocess
root=r'C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122'
ref='d98420b1113536afd08cde6de9a5816f6d27ffff'
path='pkg/lib/pb/model/models.pb.go'
r=subprocess.run(['git','-C',root,'show',ref+':'+path],capture_output=True,timeout=15)
assert r.returncode==0, r.stderr.decode(errors='replace')[:400]
b=r.stdout
assert len(b)==1180139 and hashlib.sha256(b).hexdigest()=='1e7bea1584323e3d69fb7a9f1cbe0815ab274cc1b847508b3c3c6feb9a4ad99d'
blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();assert blob=='5a07a9a96731786a6fb849ab56002c735b10aba2'
s=b.decode(); excerpts=[]
for label,pat in [('BlockRestrictions declaration',r'(?ms)^type BlockRestrictions struct \{.*?^\}'),('Block declaration',r'(?ms)^type Block struct \{.*?^\}'),('BlockRestrictions Unmarshal',r'(?ms)^func \(m \*BlockRestrictions\) Unmarshal\(dAtA \[\]byte\) error \{.*?^\}'),('Block Unmarshal',r'(?ms)^func \(m \*Block\) Unmarshal\(dAtA \[\]byte\) error \{.*?^\}')]:
 match=re.search(pat,s);assert match is not None,label
 text=match.group();start=s.count('\n',0,match.start())+1
 if 'Unmarshal' in label:
  idx=text.rfind('\n\t\tdefault:');assert idx>=0,label
  start+=text[:idx+1].count('\n');text=text[idx+1:]
 excerpts.append({'label':label,'start_line':start,'text':text})
p='pkg/lib/pb/model/protos/models.proto';rr=subprocess.run(['git','-C',root,'show',ref+':'+p],capture_output=True,timeout=10);assert rr.returncode==0
pro=rr.stdout.decode();opts=[{'line':i,'text':line} for i,line in enumerate(pro.splitlines(),1) if 'unrecognized' in line or 'goproto_sizecache' in line or 'goproto_unkeyed' in line]
print(json.dumps({'repository':'anyproto/anytype-heart','ref':ref,'path':path,'bytes':len(b),'git_blob':blob,'sha256':hashlib.sha256(b).hexdigest(),'excerpts':excerpts,'proto_options':{'path':p,'bytes':len(rr.stdout),'git_blob':hashlib.sha1(b'blob '+str(len(rr.stdout)).encode()+b'\0'+rr.stdout).hexdigest(),'sha256':hashlib.sha256(rr.stdout).hexdigest(),'lines':opts},'execution':'git show only; no generator, Go compilation or test'}))
