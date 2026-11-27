"""One normal source-only publication, preserving every undeclared tree path."""
import base64
import hashlib
import grp
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import sys
import time
import zlib

PACKED_BASE64 = '__PAYLOAD__'
PACKED_SHA256 = '__PACKED_SHA__'
RAW_SHA256 = '__RAW_SHA__'
WORKTREE = Path('/mnt/development/projects/worktrees/anytype-engine-contracts-20261127')
COMMON = Path('/mnt/development/projects/git-mirrors/anytype-swift.git')
PARENT = 'e96ba072887e7581ed6de20fdd81e0897c83763d'
PARENT_TREE = '0f0f558354cb2ceb7ad840e952d1cd5dafcc9a23'
BRANCH = 'codex/chatgpt-wave15-w1-upload-recovery-20261127'
BEFORE_IMAGES = {'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeFileAttachmentCreator.swift': '78e5ecf7a1e1ad54225551a06a5616438a051befa0c9cfd5e113bd72daf26fee', 'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeObjectCreator.swift': 'deb279cc959d535f4264072043069112403475bb1a300288f4628a959f4ce95a', 'Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyNativeFileAttachmentCreatorTests.swift': 'a33c1ad2b18928fd9c665b4249dc5996136cf7d0e2d26f7fb7d756ef89b341c1', 'docs/architecture/ordinary-file-attachment-contract-20261127.md': '877f25249eea3ec03ee96d6d956b817326a1f349c6b95201ff44362687ef8ff3', 'Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyNativeFileUploadResponse.swift': '4e9cf26ed4344493a98a64556781215a4c34ee7d70fd41cdc59d6795668ba36a', 'Modules/PinkhaAnyEngine/Tests/PinkhaAnyEngineTests/AnyNativeFileUploadHTTPTests.swift': '14d27f18c4f81b812a2817f6c3943d0e4a9c0e8ef06e373427002449f64b59cb'}
FILE_COUNT = __FILE_COUNT__
OUT = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127/recovery-source-publication1')
MIB = 1024 * 1024
ALLOWANCE = 8 * MIB
SOURCE_ADMISSION = 32 * MIB
ROOT_FLOOR = 2 * 1024 * MIB
DEV_FLOOR = 512 * MIB
GIT_CHILD_GID = 1002
GIT_CHILD_EXEC = 'import os,sys; os.setegid(int(sys.argv[1])); os.execvp("git", ["git"] + sys.argv[2:])'
started = time.monotonic()
owned = None
owned_out = False
decoded = []
raw = None
helper_bytes = None
initial_controller = None
save_serial = 0
report = {'schema': 1, 'status': 'STARTED_SOURCE_ONLY', 'parent': PARENT, 'branch': BRANCH,
          'compiledMethods': 0, 'executedMethods': 0, 'declaredComponentMethods': 35,
          'commands': [], 'mutations': [], 'completionErrors': [], 'evidenceAllocationCapBytes': ALLOWANCE,
          'sourceAndGitAdmissionBytes': SOURCE_ADMISSION,
          'sourceAndGitAdmissionIsResourceReservationNotMeasuredGlobalGrowth': True}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, data):
    global save_serial
    path = Path(path)
    if not owned_out or not path.is_relative_to(OUT):
        raise RuntimeError('receipt must stay in the new owned evidence directory')
    encoded = (json.dumps(data, indent=2, sort_keys=True) + '\n').encode()
    if len(encoded) > MIB:
        raise RuntimeError('bounded source receipt exceeded')
    save_serial += 1
    temporary = path.with_name(path.name + '.next-' + str(save_serial))
    with temporary.open('xb') as output:
        output.write(encoded)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)

def allocated(path):
    total = path.lstat().st_blocks * 512
    for directory, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            total += (Path(directory) / name).lstat().st_blocks * 512
    return total

def free():
    return {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}

def observe():
    current = free()
    if current['root'] < ROOT_FLOOR or current['development'] < DEV_FLOOR:
        return 'unchanged live disk floor breached'
    if time.monotonic() - started > 300:
        return 'source publication controller deadline'
    if owned_out and allocated(OUT) > ALLOWANCE:
        return 'bounded evidence allocation exceeded'
    return None

def physical(path):
    if not path.is_absolute():
        raise RuntimeError('absolute path required')
    current = Path('/')
    for part in path.parts[1:]:
        current /= part
        if current.exists() or current.is_symlink():
            if current.is_symlink():
                raise RuntimeError('physical publication path contains alias')

def tree(raw):
    result = {}
    for line in raw.split(b'\0'):
        if not line:
            continue
        meta, path = line.split(b'\t', 1)
        mode, kind, obj = meta.decode().split(' ')
        result[path.decode()] = (mode, kind, obj)
    return result

def command(label, args, timeout=30):
    argv = ['/usr/bin/python3', '-B', '-c', GIT_CHILD_EXEC, str(GIT_CHILD_GID),
            '--no-optional-locks', '-c', 'safe.directory=' + str(WORKTREE),
            '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(WORKTREE)] + args
    logfile, row = owned.run(OUT / ('command-%02d-%s' % (len(report['commands']) + 1, label)),
        argv, str(WORKTREE), environment, timeout, observe, save, digest, report['commands'])
    return logfile.read_bytes()

def ordinary_reader_command(label, args, timeout=30):
    argv = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent'] + args
    logfile, row = owned.run(OUT / ('command-%02d-%s' % (len(report['commands']) + 1, label)),
        argv, str(COMMON), environment, timeout, observe, save, digest, report['commands'])
    return logfile.read_bytes()

try:
    if sys.flags.optimize or os.geteuid() != 0 or os.uname().nodename != 'torah-social':
        raise RuntimeError('authorized Oracle host and enabled assertions required')
    if grp.getgrnam('chatgpt-agent').gr_gid != GIT_CHILD_GID:
        raise RuntimeError('existing intended shared repository group changed')
    os.umask(0o077)
    sys.dont_write_bytecode = True
    initial_controller = Path(__file__).read_bytes()
    if len(initial_controller) > 8 * MIB:
        raise RuntimeError('bounded publication controller')
    report['controllerSHA256'] = hashlib.sha256(initial_controller).hexdigest()
    physical(WORKTREE)
    physical(COMMON)
    physical(OUT)
    initial = free()
    if initial['root'] < ROOT_FLOOR + SOURCE_ADMISSION or initial['development'] < DEV_FLOOR + SOURCE_ADMISSION:
        raise RuntimeError('fresh source allowance not available')
    report['initialFreeBytes'] = initial
    OUT.mkdir(parents=True, exist_ok=False)
    owned_out = True
    packed = base64.b64decode(PACKED_BASE64, validate=True)
    if hashlib.sha256(packed).hexdigest() != PACKED_SHA256:
        raise RuntimeError('compressed payload identity mismatch')
    if len(packed) > 4 * MIB:
        raise RuntimeError('bounded compressed source payload')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(packed, 4 * MIB + 1)
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or len(raw) > 4 * MIB or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise RuntimeError('bounded source payload mismatch')
    payload = json.loads(raw)
    (OUT / 'original-payload.json').write_bytes(raw)
    helper_bytes = base64.b64decode(payload['helperBase64'], validate=True)
    if hashlib.sha256(helper_bytes).hexdigest() != payload['helperSHA256'] or payload['helperSHA256'] != 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56':
        raise RuntimeError('qualified process owner changed')
    helper = OUT / 'owned_swift_commands.py'
    helper.write_bytes(helper_bytes)
    spec = importlib.util.spec_from_file_location('owned_source_publication', helper)
    candidate_owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate_owner)
    owned = candidate_owner
    owned.install_interrupt_handlers()
    environment = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1')
    if command('head', ['rev-parse', 'HEAD']).decode().strip() != PARENT:
        raise RuntimeError('own worktree head changed')
    if command('tree', ['rev-parse', 'HEAD^{tree}']).decode().strip() != PARENT_TREE:
        raise RuntimeError('parent full tree changed')
    if command('status', ['status', '--porcelain=v1', '--untracked-files=all']):
        raise RuntimeError('own worktree is not clean')
    if command('common', ['rev-parse', '--git-common-dir']).decode().strip() != str(COMMON):
        raise RuntimeError('canonical common Git directory differs')
    if command('shared-repository-policy', ['config', '--get', 'core.sharedRepository']).decode().strip() != 'group':
        raise RuntimeError('original shared repository group policy changed')
    hook_dir = Path(command('hooks-path', ['rev-parse', '--path-format=absolute', '--git-path', 'hooks']).decode().strip())
    physical(hook_dir)
    active_hooks = [p.name for p in hook_dir.iterdir() if not p.name.endswith('.sample') and p.is_file() and os.access(p, os.X_OK)] if hook_dir.exists() else []
    if active_hooks:
        raise RuntimeError('unreviewed active Git hooks prevent bounded source-only publication')
    if command('branch-absent', ['for-each-ref', '--format=%(refname)', 'refs/heads/' + BRANCH]):
        raise RuntimeError('new branch already exists')
    auth = ['-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!sudo -n -u ubuntu /usr/local/bin/gh auth git-credential']
    if command('remote-branch-absent', auth + ['ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH], 60):
        raise RuntimeError('new remote branch already exists')
    for ordinal, (name, expected_sha) in enumerate(sorted(BEFORE_IMAGES.items()), 1):
        original = command('original-source-%02d' % ordinal, ['show', PARENT + ':' + name])
        if hashlib.sha256(original).hexdigest() != expected_sha:
            raise RuntimeError('original replacement before-image changed: ' + name)
    before = tree(command('complete-parent-tree', ['ls-tree', '-r', '-z', PARENT]))
    files = payload['files']
    if len(files) != FILE_COUNT or len({row['path'] for row in files}) != FILE_COUNT:
        raise RuntimeError('finite source manifest changed')
    expected = dict(before)
    additions = []
    decoded = []
    for row in files:
        rel = PurePosixPath(row['path'])
        if rel.is_absolute() or '..' in rel.parts or str(rel) != row['path'] or row['mode'] != '100644' or row['type'] != 'blob':
            raise RuntimeError('invalid source path or mode')
        data = base64.b64decode(row['contentBase64'], validate=True)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if len(data) != row['size'] or hashlib.sha256(data).hexdigest() != row['sha256'] or blob != row['gitBlob']:
            raise RuntimeError('source member identity changed')
        target = WORKTREE / row['path']
        physical(target)
        if row['path'] not in BEFORE_IMAGES:
            if row['path'] in before or target.exists():
                raise RuntimeError('new source would replace existing work')
            additions.append(row['path'])
        else:
            if row['path'] not in before or not target.is_file() or digest(target) != BEFORE_IMAGES[row['path']]:
                raise RuntimeError('physical original before-image differs')
        decoded.append((row, data, target))
        expected[row['path']] = ('100644', 'blob', blob)
    if not set(BEFORE_IMAGES) <= {row['path'] for row in files}:
        raise RuntimeError('all six exact replacements required')
    command('create-owned-branch', ['switch', '-c', BRANCH, PARENT])
    report['mutations'].append('created-new-owned-branch')
    for row, data, target in decoded:
        target.parent.mkdir(parents=True, exist_ok=True)
        physical(target.parent)
        mode = 'wb' if row['path'] in BEFORE_IMAGES else 'xb'
        with target.open(mode) as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(target, 0o644)
        if digest(target) != row['sha256']:
            raise RuntimeError('installed source readback mismatch')
    report['mutations'].append('installed-exact-scoped-source-files')
    command('stage-exact-source', ['add', '--sparse', '--'] + [row['path'] for row in files])
    candidate_tree = command('write-tree', ['write-tree']).decode().strip()
    candidate_listing = command('complete-candidate-tree', ['ls-tree', '-r', '-z', candidate_tree])
    if tree(candidate_listing) != expected:
        raise RuntimeError('full candidate tree or undeclared source changed')
    candidate_listing_identity = {'bytes': len(candidate_listing),
                                  'sha256': hashlib.sha256(candidate_listing).hexdigest()}
    report['candidateTreeListing'] = candidate_listing_identity
    changed = set(command('changed-paths', ['diff', '--cached', '--name-only', '-z', PARENT]).decode().strip('\0').split('\0'))
    if changed != {row['path'] for row in files}:
        raise RuntimeError('staged path scope differs')
    command('normal-diff-check', ['diff', '--cached', '--check'])
    command('normal-commit', ['-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com', 'commit', '-m', 'Drain upload delegates and preserve scoped recovery receipts'], 60)
    report['mutations'].append('normal-commit-created')
    commit = command('committed-head', ['rev-parse', 'HEAD']).decode().strip()
    parents = command('commit-parent', ['show', '-s', '--format=%P', 'HEAD']).decode().strip()
    actual_tree = command('committed-tree', ['rev-parse', 'HEAD^{tree}']).decode().strip()
    if parents != PARENT or actual_tree != candidate_tree or command('final-status', ['status', '--porcelain=v1', '--untracked-files=all']):
        raise RuntimeError('commit identity or final clean tree mismatch')
    report.update(commit=commit, tree=actual_tree, candidateManifestSHA256=payload['candidateManifestSHA256'],
                  fileCount=len(files), sourceBytes=sum(row['size'] for row in files), fullTreePreserved=True)
    report['installedSourceAllocatedBytes'] = sum(target.lstat().st_blocks * 512 for _, _, target in decoded)
    new_objects = command('new-objects', ['rev-list', '--objects', '--no-object-names', PARENT + '..HEAD']).decode().splitlines()
    if not new_objects or len(new_objects) > 1000 or len(set(new_objects)) != len(new_objects):
        raise RuntimeError('bounded unique new reachable object closure required')
    loose_total = 0
    ordinary_reader_inputs = []
    packed_reader_ids = []
    for object_id in new_objects:
        if len(object_id) != 40 or any(c not in '0123456789abcdef' for c in object_id):
            raise RuntimeError('invalid new object identity')
        object_path = COMMON / 'objects' / object_id[:2] / object_id[2:]
        physical(object_path)
        if object_path.exists():
            info = object_path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise RuntimeError('new reachable loose object is not a unique regular file')
            loose_total += info.st_blocks * 512
            ordinary_reader_inputs.append({'path': str(object_path), 'bytes': info.st_size,
                                           'sha256': digest(object_path)})
        else:
            # A reachable object may already live only in an existing pack.
            # The ordinary actor must read its complete Git content as well.
            packed_reader_ids.append(object_id)
    report['reachableNewCommitLooseObjectsAllocatedBytes'] = loose_total
    report['reachableNewCommitObjectCount'] = len(new_objects)
    if loose_total + report['installedSourceAllocatedBytes'] + allocated(OUT) > SOURCE_ADMISSION:
        raise RuntimeError('declared source, reachable objects and evidence exceed source reservation')
    own_ref = COMMON / 'refs' / 'heads' / BRANCH
    physical(own_ref)
    if own_ref.read_bytes() != (commit + '\n').encode():
        raise RuntimeError('exact owned normal branch reference changed')
    ordinary_reader_inputs.append({'path': str(own_ref), 'bytes': own_ref.stat().st_size,
                                   'sha256': digest(own_ref)})
    reader_script = '''import hashlib,json,os,re,stat,subprocess,sys
from pathlib import Path
assert os.getuid()==1001 and os.getegid()==1002
assert len(sys.argv)==2 and len(sys.argv[1].encode())<=60*1024
request=json.loads(sys.argv[1]);rows=request['files']
assert 1<=len(rows)<=1001
common=Path(request['repository'])
assert str(common)=='/mnt/development/projects/git-mirrors/anytype-swift.git'
assert common.resolve()==common and common.is_dir()
assert re.fullmatch('[0-9a-f]{40}',request['commit'])
assert 0<request['tree']['bytes']<=8*1024**2
assert re.fullmatch('[0-9a-f]{64}',request['tree']['sha256'])
assert sum(row['bytes'] for row in rows)<=32*1024**2
for row in rows:
 p=Path(row['path']);assert p.resolve()==p and not p.is_symlink()
 assert p.is_relative_to(common/'objects') or p==Path(request['ref'])
 assert 0<=row['bytes']<=8*1024**2
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as stream:
  before=os.fstat(stream.fileno());assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==row['bytes']
  data=stream.read(row['bytes']+1);after=os.fstat(stream.fileno())
  assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
 assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
packed=request['packedObjectIDs'];assert len(packed)<=1000 and len(set(packed))==len(packed)
assert all(re.fullmatch('[0-9a-f]{40}',value) for value in packed)
expected_blobs=request['expectedPackedBlobs']
assert set(expected_blobs)<=set(packed)
children=[];packed_rows=[]
git=['git','--no-optional-locks','-c','safe.directory='+str(common),'-c','gc.auto=0',
     '-c','maintenance.auto=false','-C',str(common)]

def git_stream(role,arguments,consume,stdin=None):
 # This child inherits the unchanged f9de owner's session/group. The worker
 # never signals or probes a historical child PID; exceptional descendants
 # remain owned by the supervisor's unreaped leader until group cleanup.
 child=subprocess.Popen(git+arguments,stdin=stdin,stdout=subprocess.PIPE,
                         start_new_session=False,close_fds=True,restore_signals=True)
 row={'role':role,'exitCode':None,'stdoutEOF':False,'sameOwnedGroup':False}
 children.append(row)
 try:
  assert os.getpgid(child.pid)==os.getpgrp()
  row['sameOwnedGroup']=True
  consume(child.stdout)
  assert child.stdout.read(1)==b'', 'complete child Git stdout EOF required'
  row['stdoutEOF']=True
  child.stdout.close()
  code=child.wait(timeout=5)
  row['exitCode']=code
  assert code==0, 'ordinary child Git must exit normally'
 except BaseException:
  print(json.dumps({'ordinaryChildGitFailure':row},sort_keys=True),file=sys.stderr)
  raise
 finally:
  child.stdout.close()

def read_exact(stream,count):
 parts=[];remaining=count
 while remaining:
  part=stream.read(min(65536,remaining))
  assert part, 'short Git content stream'
  parts.append(part);remaining-=len(part)
 return b''.join(parts)

def consume_objects(stream):
 total=0
 for wanted in packed:
  header=stream.readline(257)
  assert len(header)<=256 and header.endswith(b'\\n')
  fields=header[:-1].decode('ascii').split(' ')
  assert len(fields)==3 and fields[0]==wanted
  kind=fields[1];assert kind in ('blob','tree','commit','tag')
  assert re.fullmatch('0|[1-9][0-9]*',fields[2])
  size=int(fields[2]);assert size<=8*1024**2
  total+=size;assert total<=32*1024**2
  object_hash=hashlib.sha1((kind+' '+str(size)).encode()+b'\\0')
  content_hash=hashlib.sha256();remaining=size
  while remaining:
   data=read_exact(stream,min(65536,remaining));remaining-=len(data)
   object_hash.update(data);content_hash.update(data)
  assert read_exact(stream,1)==b'\\n'
  assert object_hash.hexdigest()==wanted, 'packed Git object identity differs'
  body={'bytes':size,'sha256':content_hash.hexdigest()}
  if kind=='blob':
   assert wanted in expected_blobs and body==expected_blobs[wanted], 'exact declared source blob required'
  else:
   assert wanted not in expected_blobs
  packed_rows.append({'objectID':wanted,'type':kind,**body})

if packed:
 # A bounded anonymous descriptor avoids pipe write/read deadlock and creates
 # no file in a repository, account, source directory or shared temp location.
 ids=('\\n'.join(packed)+'\\n').encode('ascii');assert len(ids)<=41000
 descriptor=os.memfd_create('pinkha-published-object-ids',os.MFD_CLOEXEC)
 try:
  remaining=memoryview(ids)
  while remaining:
   written=os.write(descriptor,remaining);assert written>0;remaining=remaining[written:]
  os.lseek(descriptor,0,os.SEEK_SET)
  git_stream('exact-packed-object-content',['cat-file','--batch'],consume_objects,descriptor)
 finally:
  os.close(descriptor)

tree_result={}
def consume_tree(stream):
 hasher=hashlib.sha256();count=0
 while True:
  data=stream.read(65536)
  if not data:break
  count+=len(data);assert count<=request['tree']['bytes']
  hasher.update(data)
 tree_result.update(bytes=count,sha256=hasher.hexdigest())
 assert tree_result==request['tree'], 'ordinary complete candidate tree differs'

git_stream('complete-candidate-tree',['ls-tree','-r','-z',request['commit']],consume_tree)
print(json.dumps({'uid':os.getuid(),'effectiveGid':os.getegid(),'exactFilesRead':len(rows),
 'bytes':sum(row['bytes'] for row in rows),'allOriginalHashesMatch':True,
 'packedObjects':packed_rows,'packedBodiesSHA1Verified':True,
 'packedBlobPayloadsSHA256Verified':True,'candidateTree':tree_result,
 'childGitCommands':children},sort_keys=True))
'''
    packed_blob_inputs = {row['gitBlob']: {'bytes': row['size'], 'sha256': row['sha256']}
                          for row in files if row['gitBlob'] in packed_reader_ids}
    reader_request = {'repository': str(COMMON), 'ref': str(own_ref), 'commit': commit,
                      'files': ordinary_reader_inputs, 'packedObjectIDs': packed_reader_ids,
                      'expectedPackedBlobs': packed_blob_inputs, 'tree': candidate_listing_identity}
    reader_argument = json.dumps(reader_request, separators=(',', ':'), ensure_ascii=True)
    if len(reader_argument.encode()) > 60 * 1024 or len(reader_script.encode()) > 16 * 1024:
        raise RuntimeError('bounded ordinary-reader argv below the single-argument limit')
    reader = json.loads(ordinary_reader_command('ordinary-reader-new-closure-and-tree',
        ['/usr/bin/python3', '-B', '-c', reader_script, reader_argument]))
    expected_reader_base = {'uid': 1001, 'effectiveGid': 1002, 'exactFilesRead': len(ordinary_reader_inputs),
                            'bytes': sum(row['bytes'] for row in ordinary_reader_inputs), 'allOriginalHashesMatch': True,
                            'packedBodiesSHA1Verified': True, 'packedBlobPayloadsSHA256Verified': True,
                            'candidateTree': candidate_listing_identity}
    if any(reader.get(key) != value for key, value in expected_reader_base.items()):
        raise RuntimeError('existing ordinary reader did not verify the exact newly published bytes')
    packed_results = reader.get('packedObjects', [])
    if [row.get('objectID') for row in packed_results] != packed_reader_ids:
        raise RuntimeError('ordinary reader packed object set differs')
    for row in packed_results:
        if row['type'] == 'blob' and {key: row[key] for key in ('bytes', 'sha256')} != packed_blob_inputs.get(row['objectID']):
            raise RuntimeError('ordinary reader packed source blob differs')
    expected_child_roles = (['exact-packed-object-content'] if packed_reader_ids else []) + ['complete-candidate-tree']
    if reader.get('childGitCommands') != [{'role': role, 'exitCode': 0, 'stdoutEOF': True, 'sameOwnedGroup': True}
                                        for role in expected_child_roles]:
        raise RuntimeError('ordinary reader child Git commands lack exact normal EOF/exit closure')
    report['ordinaryReaderVerification'] = dict(reader, fullTreeUnchanged=True,
        fullTreeSHA256=candidate_listing_identity['sha256'], gitChildEffectiveGid=GIT_CHILD_GID,
        readerRequestBytes=len(reader_argument.encode()), readerRequestSHA256=hashlib.sha256(reader_argument.encode()).hexdigest(),
        completeNewObjectCount=len(new_objects), packedObjectCount=len(packed_reader_ids),
        originalSharedRepositoryPolicy='group', noDirectoryRefConfigPermissionChanges=True)
    command('normal-push', auth + ['push', 'origin', 'HEAD:refs/heads/' + BRANCH], 90)
    report['mutations'].append('normal-push-completed')
    remote = command('remote-head-readback', auth + ['ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH], 60).decode().split()
    if remote != [commit, 'refs/heads/' + BRANCH]:
        raise RuntimeError('exact remote ref readback differs')
    report['status'] = 'PASS_NORMAL_SCOPED_SOURCE_PUBLICATION_ONLY'
except BaseException as error:
    report['status'] = 'FAIL_SOURCE_PUBLICATION_PRESERVED'
    report['error'] = {'type': type(error).__name__, 'message': str(error)}
finally:
    # f9de has already joined each exact child before restoring these handlers.
    # Latch absence from that ledger; do not probe historical PID identities.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if owned is not None:
        owned.ignore_interrupts()
    final_deadline = time.monotonic() + 60
    def final_guard():
        if time.monotonic() >= final_deadline:
            raise RuntimeError('bounded final verification deadline')
        current = free()
        if current['root'] < ROOT_FLOOR or current['development'] < DEV_FLOOR:
            raise RuntimeError('unchanged final live disk floor breached')
        if owned_out and allocated(OUT) > ALLOWANCE:
            raise RuntimeError('bounded final evidence allocation exceeded')
        return current
    def final_error(phase, error):
        report['completionErrors'].append({'phase': phase, 'type': type(error).__name__, 'message': str(error)})
    try:
        report['allOwnedGroupsAbsent'] = all(row.get('processGroupAbsent') is True for row in report['commands'])
        report['allOwnedGroupsClosedNormally'] = all(
            row.get('processGroupAbsent') is True and row.get('exitCode') == 0 and
            not row.get('forcedCleanup') and not row.get('signals') and not row.get('cleanupErrors')
            for row in report['commands'])
        if not report['allOwnedGroupsAbsent']:
            raise RuntimeError('an owned group lacks positive terminal absence')
        if report['status'].startswith('PASS_') and (not report['commands'] or not report['allOwnedGroupsClosedNormally']):
            raise RuntimeError('successful publication requires every original command to close normally')
    except BaseException as error:
        final_error('latched-owned-command-closure', error)
    try:
        report['finalFreeBytes'] = final_guard()
        if initial_controller is not None and Path(__file__).read_bytes() != initial_controller:
            raise RuntimeError('original controller changed during publication')
        if helper_bytes is not None and (OUT / 'owned_swift_commands.py').read_bytes() != helper_bytes:
            raise RuntimeError('qualified original command owner changed')
        if raw is not None and (OUT / 'original-payload.json').read_bytes() != raw:
            raise RuntimeError('original public source payload changed')
        for row, data, target in decoded:
            final_guard()
            if target.read_bytes() != data or stat.S_IMODE(target.lstat().st_mode) != 0o644:
                raise RuntimeError('final exact published source differs: ' + row['path'])
        report['publishedSourceUnchangedAtCompletion'] = bool(decoded)
        if owned_out:
            report['evidenceAllocatedBytesBeforeReceipt'] = allocated(OUT)
    except BaseException as error:
        final_error('final-resources-and-exact-source', error)
    if report['completionErrors']:
        report['status'] = 'FAIL_SOURCE_PUBLICATION_PRESERVED'
    report['seconds'] = time.monotonic() - started
    if owned_out:
        try:
            save(OUT / 'result.json', report)
            print(json.dumps({'status': report['status'], 'receiptPath': str(OUT / 'result.json'),
                              'receiptSHA256': digest(OUT / 'result.json'), 'commit': report.get('commit'),
                              'tree': report.get('tree'), 'allOwnedGroupsAbsent': report.get('allOwnedGroupsAbsent'),
                              'error': report.get('error'), 'completionErrors': report['completionErrors']}))
        except BaseException as error:
            final_error('terminal-receipt-retention', error)
            report['status'] = 'FAIL_SOURCE_PUBLICATION_PRESERVED'
            print(json.dumps(report))
    else:
        print(json.dumps(report))
if report['status'].startswith('FAIL'):
    sys.exit(1)
