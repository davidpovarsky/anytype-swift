import os, stat, json, hashlib, resource, signal, time, re
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
resource.setrlimit(resource.RLIMIT_CPU,(15,15))
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
signal.alarm(30)
started=time.monotonic()
ROOT='/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/lib/swift/linux'
NAMES=["Cxx","CxxStdlib","Dispatch","Distributed","Foundation","FoundationEssentials","FoundationInternationalization","FoundationNetworking","FoundationXML","Glibc","Observation","RegexBuilder","Runtime","Swift","SwiftOnoneSupport","Synchronization","Testing","XCTest","_Builtin_float","_Concurrency","_Differentiation","_FoundationCollections","_RegexParser","_StringProcessing","_TestDiscovery","_TestingInterop","_Testing_Foundation","_Volatile"]
TARGET='aarch64-unknown-linux-gnu'
CAP_FILE=64*1024*1024
CAP_TOTAL=256*1024*1024
CAP_INTERFACES=32*1024*1024
CAP_STDOUT=512*1024
def identity(s):
    return {k:getattr(s,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_blocks','st_atime_ns','st_mtime_ns','st_ctime_ns')}
def deadline():
    if time.monotonic()-started>25: raise RuntimeError('bounded observation deadline')
def stable(path,before,fd):
    if identity(os.fstat(fd))!=before or identity(os.lstat(path))!=before: raise RuntimeError('input changed: '+path)
dirs={}
for path in [ROOT]+[ROOT+'/'+n+'.swiftmodule' for n in NAMES]:
    deadline()
    st=os.lstat(path)
    if not stat.S_ISDIR(st.st_mode): raise RuntimeError('physical module directory required: '+path)
    dirs[path]=identity(st)
planned=[]
total=interface_total=0
for name in NAMES:
    for suffix in ('swiftmodule','swiftinterface'):
        path=ROOT+'/'+name+'.swiftmodule/'+TARGET+'.'+suffix
        try: st=os.lstat(path)
        except FileNotFoundError:
            planned.append({'moduleName':name,'path':path,'kind':suffix,'absent':True});continue
        if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_size<1 or st.st_size>CAP_FILE: raise RuntimeError('bounded ordinary input required: '+path)
        total+=st.st_size
        if suffix=='swiftinterface': interface_total+=st.st_size
        if total>CAP_TOTAL or interface_total>CAP_INTERFACES: raise RuntimeError('whole named input cap')
        planned.append({'moduleName':name,'path':path,'kind':suffix,'identity':identity(st)})
rows=[]
opened=0
for row in planned:
    deadline()
    if row.get('absent'):
        if os.path.lexists(row['path']): raise RuntimeError('absent input appeared')
        rows.append(row);continue
    path=row['path'];before=row['identity']
    fd=os.open(path,os.O_RDONLY|os.O_NOATIME|os.O_NOFOLLOW)
    try:
        if identity(os.fstat(fd))!=before: raise RuntimeError('opened identity mismatch')
        digest=hashlib.sha256();count=0;chunks=[]
        while True:
            deadline()
            part=os.read(fd,min(262144,before['st_size']+1-count))
            if not part: break
            count+=len(part)
            if count>before['st_size']: raise RuntimeError('input grew')
            digest.update(part)
            if row['kind']=='swiftinterface': chunks.append(part)
        if count!=before['st_size']: raise RuntimeError('input truncated')
        stable(path,before,fd)
        out={**row,'bytes':count,'sha256':digest.hexdigest(),'metadataUnchangedIncludingAtime':True}
        if row['kind']=='swiftinterface':
            body=b''.join(chunks).decode('utf-8')
            lines=body.splitlines()
            out['headerComments']=[x for x in lines[:12] if x.startswith('//')]
            out['importDeclarations']=[{'line':i+1,'text':x} for i,x in enumerate(lines) if re.search(r'(^|[ \t])import[ \t]+[A-Za-z_]',x)]
            if len(out['importDeclarations'])>512 or sum(len(x['text'].encode('utf-8')) for x in out['importDeclarations'])>32768: raise RuntimeError('bounded import declaration output')
        rows.append(out);opened+=count
    finally: os.close(fd)
for row in planned:
    deadline()
    if row.get('absent'):
        if os.path.lexists(row['path']): raise RuntimeError('absent input appeared')
    elif identity(os.lstat(row['path']))!=row['identity']: raise RuntimeError('final named input identity changed')
for path,before in dirs.items():
    if identity(os.lstat(path))!=before: raise RuntimeError('module directory metadata changed')
result={'schema':'pinkha-installed-explicit-system-module-input-observation-v1','status':'PASS_NAMED_PUBLIC_TOOLCHAIN_INPUT_OBSERVATION_ONLY','moduleCandidateCount':len(NAMES),'plannedLeafCount':len(planned),'openedBytes':opened,'rows':rows,'directories':[{'path':p,'identity':v,'metadataUnchangedIncludingAtime':True} for p,v in dirs.items()],'compilerInvocations':0,'children':0,'projectWrites':0,'cachePayloadsOpened':0,'completeDependencyClosureClaimed':False,'seconds':time.monotonic()-started}
encoded=json.dumps(result,sort_keys=True,separators=(',',':'))
if len(encoded.encode('utf-8'))>CAP_STDOUT: raise RuntimeError('bounded stdout')
print(encoded)
