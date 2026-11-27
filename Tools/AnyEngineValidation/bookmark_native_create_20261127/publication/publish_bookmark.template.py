#!/usr/bin/env python3
"""Publish exact optional Bookmark native source and actual public evidence.

Creates one isolated branch from accepted C21. No compiler, native account,
old-method replay, runtime worktree edit, C3 cache mutation or force push.
"""
import ast
import base64
import hashlib
import grp
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import sys
import time

HERE = Path(__file__).absolute().parent
PLAN_SHA = '__PLAN_SHA__'
LOCAL_SHA = '__LOCAL_SHA__'
VALIDATOR_SHA = '__VALIDATOR_SHA__'
READER_SHA = 'cc9ba9f74109468728612168a6ee923cd3206e268d4c7a33be18520dc464564d'
GIT_CHILD_GID = 1002
GIT_CHILD_EXEC = 'import os,sys; os.setegid(int(sys.argv[1])); os.execv("/usr/bin/git", ["/usr/bin/git"] + sys.argv[2:])'
REMOTE_COUNT = 7
LOCAL_COUNT = 52
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
BASE = '6b91db33d325f22b62d829051db203121c6cdb8e'
BASE_TREE = 'd544013fd818a5d0a7e7a59b569cf8f1a21b2d77'
BRANCH = 'codex/chatgpt-wave15-w1-bookmark-native-20261127'
COMMON = Path('/mnt/development/projects/git-mirrors/anytype-swift.git')
WORKTREE = Path('/mnt/development/projects/worktrees/anytype-bookmark-native-publish-20261127')
OUT = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-publication-20261127/attempt1')
CODE = 'Tools/AnyEngineValidation/bookmark_native_create_20261127/'
DOC = 'docs/validation/20261127-bookmark-native-create/'
MIB = 1024**2
ROOT_FLOOR = 2*1024**3
DEV_FLOOR = 512*MIB
EVIDENCE_CAP = 16*MIB
SOURCE_GIT_RESERVE = 64*MIB
CONTROLLER_SECONDS = 420
FINAL_SECONDS = 60


def require(value, message):
    if not value:
        raise AssertionError(message)


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def physical(path):
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(),
            'canonical physical public path required: '+str(path))


def read_public(path, maximum=8*MIB):
    physical(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size<=maximum,
            'bounded regular public file: '+str(path))
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno())==before, 'input identity changed')
        data = stream.read(maximum+1)
        require(os.fstat(stream.fileno())==before, 'input changed during read')
    require(path.lstat()==before and len(data)==before.st_size, 'input changed after read')
    return data


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive_bytes(path, data):
    physical(path)
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    physical(path.parent)
    with path.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.chmod(path, 0o644)
    fsync_directory(path.parent)
    require(read_public(path)==data, 'exact installed public bytes')


def tree(raw):
    result = {}
    for row in raw.split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split(' ')
        name = name.decode()
        require(name not in result, 'unique complete Git tree path')
        result[name] = (mode, kind, oid)
    return result


def safe_destination(name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path)==name and '..' not in path.parts,
            'safe publication-relative path')
    require(name.startswith((CODE, DOC)), 'only two new publication prefixes')
    return path


def main():
    require(not sys.flags.optimize, 'qualification assertions must remain enabled')
    require(os.geteuid()==0 and os.uname().nodename=='torah-social', 'fixed authorized Oracle host')
    require(grp.getgrnam('chatgpt-agent').gr_gid==GIT_CHILD_GID, 'existing shared Git group identity')
    os.umask(0o077)
    for path in (HERE, COMMON, WORKTREE, WORKTREE.parent, OUT, OUT.parent):
        physical(path)
    require(COMMON.is_dir() and WORKTREE.parent.is_dir(), 'existing canonical Git parents')
    require(not os.path.lexists(WORKTREE) and not os.path.lexists(OUT), 'exclusive new source worktree and receipt')
    OUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    physical(OUT.parent)
    OUT.mkdir(mode=0o700, exist_ok=False)
    # Reserving result before try/finally prevents a repeated invocation from
    # replacing any earlier evidence. All subsequent saves stay in this root.
    with (OUT/'result.json').open('xb') as stream:
        stream.write(b'{}\n'); stream.flush(); os.fsync(stream.fileno())
    fsync_directory(OUT)
    began = time.monotonic()
    serial = 0
    owned_worktree = False
    inputs = {}
    content = {}
    descriptor = None
    final_mode = False
    final_began = None
    report = {
        'protocol': 'pinkha-bookmark-native-create-source-publication-v1',
        'status': 'RUNNING', 'baseCommit': BASE, 'branch': BRANCH,
        'commands': [], 'mutationLedger': [], 'errors': [], 'completionErrors': [],
        'compilerInvocations': 0, 'nativeInvocations': 0, 'testMethodsReexecuted': 0,
        'privateAccountInputs': 0, 'existingWorktreeWrites': 0, 'forcePushes': 0,
        'resetOperations': 0, 'controlledRootOutputPaths': [],
        'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
            'rootAdmissionReserveBytes': 32*MIB, 'developmentAdmissionReserveBytes': SOURCE_GIT_RESERVE+EVIDENCE_CAP,
            'evidenceCapBytes': EVIDENCE_CAP, 'sourceGitReserveBytes': SOURCE_GIT_RESERVE,
            'sourceGitReserveIsNotMeasuredGlobalGrowth': True,
            'controllerSeconds': CONTROLLER_SECONDS, 'finalSeconds': FINAL_SECONDS,
            'requiredOuterTimeoutSeconds': 540},
    }

    def allocated(path):
        if not path.exists():
            return 0
        physical(path)
        total = path.lstat().st_blocks*512
        for folder, directories, files in os.walk(path, followlinks=False):
            for name in directories+files:
                member = Path(folder)/name
                require(not member.is_symlink(), 'owned publication tree has no aliases')
                total += member.lstat().st_blocks*512
        return total

    def save(path, value):
        nonlocal serial
        require(path.is_relative_to(OUT), 'owned evidence destination')
        physical(path.parent)
        encoded = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
        require(len(encoded)<=4*MIB, 'bounded source publication receipt')
        serial += 1
        temporary = path.with_name(path.name+'.next-'+str(serial))
        with temporary.open('xb') as stream:
            stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)

    def checkpoint():
        save(OUT/'result.json', report)

    def guard(admission=False):
        elapsed = time.monotonic()-(final_began if final_mode else began)
        require(elapsed<(FINAL_SECONDS if final_mode else CONTROLLER_SECONDS), 'bounded publication phase')
        free = {name: shutil.disk_usage(path).free for name,path in [('root','/'),('development','/mnt/development')]}
        require(free['root']>=ROOT_FLOOR+(32*MIB if admission else 0), 'unchanged root floor and explicit reserve')
        require(free['development']>=DEV_FLOOR+(SOURCE_GIT_RESERVE+EVIDENCE_CAP if admission else 0),
                'unchanged development floor and explicit reserve')
        size = allocated(OUT)
        require(size<=EVIDENCE_CAP, 'bounded owned publication evidence')
        report['peakOwnedEvidenceBytes'] = max(size, report.get('peakOwnedEvidenceBytes', 0))
        if owned_worktree:
            require(allocated(WORKTREE)<=SOURCE_GIT_RESERVE, 'bounded isolated sparse source worktree')
        return free

    def observe():
        try:
            guard()
        except BaseException as error:
            return str(error)
        return None

    def pin(path, wanted, maximum=8*MIB, size=None):
        data = read_public(path, maximum)
        actual = identity(data)
        require(actual['sha256']==wanted and (size is None or actual['bytes']==size), 'fixed public source pin: '+str(path))
        inputs[str(path)] = {'identity': actual, 'maximum': maximum}
        return data

    def digest(path):
        return hashlib.sha256(read_public(Path(path), 16*MIB)).hexdigest()

    def git(label, arguments, cwd=COMMON, seconds=30):
        argv = ['/usr/bin/python3', '-B', '-c', GIT_CHILD_EXEC, str(GIT_CHILD_GID), '--no-optional-locks', '-c', 'safe.directory='+str(cwd),
                '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(cwd)]+arguments
        log, row = owned.run(OUT/('%02d-%s' % (len(report['commands'])+1,label)),
            argv, str(cwd), environment, seconds, observe, save, digest, report['commands'])
        checkpoint()
        return read_public(log, 16*MIB)

    def textgit(label, arguments, cwd=COMMON, seconds=30):
        return git(label, arguments, cwd, seconds).decode().strip()

    def mutate(label, arguments, cwd=COMMON, seconds=60):
        item = {'action': label, 'state': 'dispatching'}
        report['mutationLedger'].append(item); checkpoint()
        try:
            result = git(label, arguments, cwd, seconds)
        except BaseException:
            item['state'] = 'failed-or-unknown-effects-preserved-no-retry'; checkpoint()
            raise
        item['state'] = 'command-completed'; checkpoint()
        return result

    try:
        own = Path(__file__).absolute()
        report['controller'] = identity(read_public(own))
        inputs[str(own)] = {'identity': report['controller'], 'maximum': 8*MIB}
        helper_path = HERE/'owned_swift_commands.py'
        pin(helper_path, HELPER_SHA, size=9527)
        spec = importlib.util.spec_from_file_location('qualified_read_authority_publication_owner', helper_path)
        owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
        owned.install_interrupt_handlers()
        environment = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_NOSYSTEM='1')
        report['initialFreeBytes'] = guard(True)
        plan_raw = pin(HERE/'PUBLICATION_PLAN.json', PLAN_SHA)
        local_raw = pin(HERE/'LOCAL_PUBLIC_FILES.json', LOCAL_SHA)
        plan = json.loads(plan_raw); local = json.loads(local_raw)
        require(plan['protocol']=='pinkha-bookmark-native-create-publication-plan-v1' and
                plan['branch']==BRANCH and plan['expectedHead']==BASE and plan['worktree']==str(WORKTREE),
                'fixed source publication branch and parent')
        require(len(plan['remotePublicCopies'])==REMOTE_COUNT and
                len(plan['localPublicFiles'])==LOCAL_COUNT and len(local)==LOCAL_COUNT,
                'exact frozen public source and evidence members')
        module_path = HERE/'validate_public_evidence.py'; pin(module_path,VALIDATOR_SHA)
        module_spec = importlib.util.spec_from_file_location('bookmark_public_evidence',module_path)
        evidence_validator = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(evidence_validator)
        reader_script = pin(HERE/'ordinary_reader_worker.py',READER_SHA,size=5477).decode()
        for item in plan['remotePublicCopies']:
            safe_destination(item['destination'])
            require(item['destination'] not in content and item['maximumBytes']==2*MIB, 'unique bounded public source')
            content[item['destination']] = pin(Path(item['source']), item['sha256'], item['maximumBytes'], item.get('bytes'))
            guard()
        for item in plan['localPublicFiles']:
            name = item['destination']; safe_destination(name)
            require(name not in content and name in local, 'unique local public document')
            value = local[name]; data = base64.b64decode(value['base64'], validate=True)
            expected = {'bytes': item['bytes'], 'sha256': item['sha256']}
            require(identity(data)==expected=={key:value[key] for key in expected}, 'exact prepared public document')
            content[name] = data
        require(len(content)==REMOTE_COUNT+LOCAL_COUNT and sum(map(len,content.values()))<4*MIB, 'fixed finite public payload')
        for name,data in content.items():
            if name.endswith('.py'):
                ast.parse(data, filename=name)
            elif name.endswith('.json'):
                json.loads(data)
        report['qualifiedPacket'] = evidence_validator.validate(content,CODE,DOC)
        content[DOC+'publication-inputs.json'] = plan_raw
        descriptor = {'protocol':'pinkha-bookmark-native-create-public-file-set-v1','baseCommit':BASE,
            'inputPlanSHA256':PLAN_SHA,'localPublicPayloadSHA256':LOCAL_SHA,
            'nativeExecutableCopiedToGit':False,'privateAccountFiles':0,
            'files':{name:identity(data) for name,data in sorted(content.items())}}
        content[DOC+'FILES.json'] = (json.dumps(descriptor,sort_keys=True,indent=2)+'\n').encode()
        require(len(content)==REMOTE_COUNT+LOCAL_COUNT+2, 'frozen public members plus plan and descriptor')
        report['publicFileCount'] = len(content)
        report['publicBytes'] = sum(map(len,content.values()))
        require(textgit('canonical-repository',['rev-parse','--absolute-git-dir'])==str(COMMON), 'canonical Git mirror')
        require(textgit('existing-shared-policy',['config','--get','core.sharedRepository'])=='group', 'existing shared Git group policy unchanged')
        require(textgit('object-format',['rev-parse','--show-object-format'])=='sha1', 'exact Git object format')
        require(textgit('base-commit',['rev-parse',BASE+'^{commit}'])==BASE and
                textgit('base-tree',['rev-parse',BASE+'^{tree}'])==BASE_TREE, 'exact accepted C21 parent commit and full tree')
        require(textgit('existing-worktree-config',['config','--type=bool','--default','false','--get','extensions.worktreeConfig'])=='true',
                'existing per-worktree configuration required without shared conversion')
        require(not textgit('configured-hooks',['config','--default','','--get','core.hooksPath']), 'unreviewed custom Git hooks refuse publication')
        hooks = COMMON/'hooks'; physical(hooks)
        require(not hooks.exists() or not any(p.is_file() and not p.name.endswith('.sample') and os.access(p,os.X_OK) for p in hooks.iterdir()),
                'unreviewed executable Git hooks refuse publication')
        require(not textgit('local-branch-absent',['for-each-ref','--format=%(refname)','refs/heads/'+BRANCH]), 'new owned local branch')
        auth = ['-c','remote.origin.mirror=false','-c','credential.helper=!sudo -n -u ubuntu /usr/local/bin/gh auth git-credential']
        require(not textgit('remote-branch-absent',auth+['ls-remote','--heads','origin','refs/heads/'+BRANCH],seconds=60), 'new owned remote branch')
        parent_tree = tree(git('complete-parent-tree',['ls-tree','-r','-z',BASE]))
        require(not any(name.startswith((CODE,DOC)) for name in parent_tree), 'both publication prefixes are new')
        expected = dict(parent_tree)
        for name,data in content.items():
            require(name not in expected, 'only new public files')
            oid = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            expected[name] = ('100644','blob',oid)
        mutate('create-isolated-worktree',['worktree','add','--no-checkout','-b',BRANCH,str(WORKTREE),BASE],seconds=60)
        owned_worktree = True
        require(textgit('new-common-repository',['rev-parse','--git-common-dir'],WORKTREE)==str(COMMON), 'isolated worktree repository')
        require(textgit('new-owned-head',['rev-parse','HEAD'],WORKTREE)==BASE, 'initial owned worktree retains exact base')
        mutate('sparse-new-prefixes',['sparse-checkout','set','--no-cone','--','/'+CODE,'/'+DOC],WORKTREE,60)
        # --no-checkout can leave this newly owned index empty even after sparse
        # patterns are configured. Populate it once from the fixed base before
        # any public file is installed; no existing worktree/index is reset.
        mutate('initialize-new-owned-index',['read-tree','-mu',BASE],WORKTREE,60)
        require(textgit('initial-owned-index-tree',['write-tree'],WORKTREE)==
                textgit('exact-base-tree',['rev-parse',BASE+'^{tree}']), 'initial owned index is the complete base tree')
        require(not git('new-clean-status',['status','--porcelain=v1','--untracked-files=all'],WORKTREE), 'new sparse base is clean')
        installation = {'action':'install-exact-public-files','state':'dispatching','count':len(content)}
        report['mutationLedger'].append(installation); checkpoint()
        for name,data in sorted(content.items()):
            guard(); exclusive_bytes(WORKTREE/name, data)
        installation['state']='completed'; checkpoint()
        mutate('stage-two-prefixes',['add','--sparse','--',CODE,DOC],WORKTREE)
        candidate = textgit('candidate-tree',['write-tree'],WORKTREE)
        candidate_listing = git('complete-candidate-tree',['ls-tree','-r','-z',candidate],WORKTREE)
        candidate_listing_identity = identity(candidate_listing)
        require(tree(candidate_listing)==expected,
                'entire candidate tree preserves every undeclared file')
        changed = set(git('staged-paths',['diff','--cached','--name-only','-z',BASE],WORKTREE).decode().strip('\0').split('\0'))
        require(changed==set(content), 'only the exact declared new files are staged')
        text_paths = sorted(name for name in content if name.endswith(('.py','.go','.md','.json')))
        git('source-format-check',['diff','--cached','--check','--']+text_paths,WORKTREE)
        # Exact original logs and patch bytes are preserved by SHA, not edited
        # to satisfy a whitespace checker for newly authored source files.
        for name,data in content.items():
            require(read_public(WORKTREE/name)==data, 'all candidate bytes remain exact')
        mutate('normal-commit',['-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','commit','-m',
            'Qualify guarded Bookmark creation and bodyless crash recovery'],WORKTREE,60)
        commit = textgit('committed-head',['rev-parse','HEAD'],WORKTREE)
        report['commit']=commit; report['tree']=candidate; checkpoint()
        require(textgit('single-parent',['show','-s','--format=%P','HEAD'],WORKTREE)==BASE and
                textgit('committed-tree',['rev-parse','HEAD^{tree}'],WORKTREE)==candidate,
                'ordinary single-parent exact-tree commit')
        require(not git('clean-committed-worktree',['status','--porcelain=v1','--untracked-files=all'],WORKTREE), 'committed isolated worktree is clean')
        new_objects = textgit('new-reachable-objects',['rev-list','--objects','--no-object-names',BASE+'..HEAD'],WORKTREE).splitlines()
        require(new_objects and len(new_objects)<=1000 and len(set(new_objects))==len(new_objects), 'bounded unique new reachable object closure')
        loose = 0; ordinary_reader_inputs=[]; packed_reader_ids=[]
        for oid in new_objects:
            require(re.fullmatch(r'[0-9a-f]{40}',oid) is not None, 'new Git object ID')
            path=COMMON/'objects'/oid[:2]/oid[2:]; physical(path)
            if path.exists():
                info=path.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_nlink==1, 'unique regular newly reachable Git object')
                loose+=info.st_blocks*512
                ordinary_reader_inputs.append({'path':str(path),'bytes':info.st_size,'sha256':digest(path)})
            else: packed_reader_ids.append(oid)
        report['reachableNewLooseObjectsAllocatedBytes']=loose
        report['ownedWorktreeAllocatedBytes']=allocated(WORKTREE)
        require(loose+allocated(WORKTREE)+allocated(OUT)<=SOURCE_GIT_RESERVE, 'owned source, reachable loose objects and evidence fit reserve')
        own_ref=COMMON/'refs'/'heads'/BRANCH; physical(own_ref)
        require(read_public(own_ref)==(commit+'\n').encode(), 'exact newly published branch ref')
        ordinary_reader_inputs.append({'path':str(own_ref),'bytes':own_ref.stat().st_size,'sha256':digest(own_ref)})
        packed_blob_inputs={hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest():identity(data)
                            for data in content.values()}
        packed_blob_inputs={key:value for key,value in packed_blob_inputs.items() if key in packed_reader_ids}
        reader_request={'repository':str(COMMON),'ref':str(own_ref),'commit':commit,
                        'files':ordinary_reader_inputs,'packedObjectIDs':packed_reader_ids,
                        'expectedPackedBlobs':packed_blob_inputs,'tree':candidate_listing_identity}
        reader_argument=json.dumps(reader_request,separators=(',',':'),ensure_ascii=True)
        require(len(reader_argument.encode())<=60*1024 and len(reader_script.encode())<=16*1024,
                'bounded existing ordinary-reader arguments')
        log,row=owned.run(OUT/('%02d-ordinary-reader-new-closure-and-tree' % (len(report['commands'])+1)),
            ['sudo','-n','-u','ubuntu','-g','chatgpt-agent','/usr/bin/python3','-B','-c',reader_script,reader_argument],
            str(COMMON),environment,30,observe,save,digest,report['commands'])
        checkpoint(); reader=json.loads(read_public(log))
        expected_reader={'uid':1001,'effectiveGid':1002,'exactFilesRead':len(ordinary_reader_inputs),
                         'bytes':sum(row['bytes'] for row in ordinary_reader_inputs),'allOriginalHashesMatch':True,
                         'packedBodiesSHA1Verified':True,'packedBlobPayloadsSHA256Verified':True,
                         'candidateTree':candidate_listing_identity}
        require(all(reader.get(key)==value for key,value in expected_reader.items()), 'ordinary reader verifies exact full candidate tree and new closure')
        packed_results=reader.get('packedObjects',[])
        require([row.get('objectID') for row in packed_results]==packed_reader_ids, 'ordinary reader exact packed object IDs')
        for row in packed_results:
            if row['type']=='blob':
                require({key:row[key] for key in ('bytes','sha256')}==packed_blob_inputs.get(row['objectID']), 'ordinary reader exact packed source bytes')
        expected_roles=(['exact-packed-object-content'] if packed_reader_ids else [])+['complete-candidate-tree']
        require(reader.get('childGitCommands')==[{'role':role,'exitCode':0,'stdoutEOF':True,'sameOwnedGroup':True} for role in expected_roles],
                'ordinary reader nested Git normal EOF and exit')
        report['ordinaryReaderVerification']=dict(reader,fullTreeUnchanged=True,
            completeNewObjectCount=len(new_objects),packedObjectCount=len(packed_reader_ids),
            gitChildEffectiveGid=GIT_CHILD_GID,readerWorkerSHA256=READER_SHA,
            readerRequestBytes=len(reader_argument.encode()),readerRequestSHA256=hashlib.sha256(reader_argument.encode()).hexdigest(),
            noDirectoryRefConfigPermissionChanges=True)
        for path,admitted in inputs.items():
            require(identity(read_public(Path(path),admitted['maximum']))==admitted['identity'], 'public input unchanged before push')
        mutate('normal-explicit-ref-push',auth+['push','origin','HEAD:refs/heads/'+BRANCH],WORKTREE,90)
        remote = textgit('published-ref-readback',auth+['ls-remote','--heads','origin','refs/heads/'+BRANCH],WORKTREE,60).split()
        require(remote==[commit,'refs/heads/'+BRANCH], 'exact independently read published ref')
        report['fullUndeclaredGitTreePreserved']=True
        report['changedPaths']=sorted(changed)
        report['status']='PASS_NORMAL_PUBLICATION_OF_BOOKMARK_NATIVE_13_AND_BODYLESS_PROOF'
    except BaseException as error:
        report['status']='FAIL_PRESERVED_WITHOUT_RESET_OR_RETRY'
        report['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        for number in (signal.SIGTERM,signal.SIGINT):
            signal.signal(number,signal.SIG_IGN)
        report['allStartedOwnedGroupsPositivelyAbsent']=all(row.get('processGroupAbsent') is True for row in report['commands'])
        final_mode=True; final_began=time.monotonic()
        try:
            for path,admitted in inputs.items():
                guard()
                require(identity(read_public(Path(path),admitted['maximum']))==admitted['identity'], 'public input unchanged at completion')
            report['publicInputsUnchanged']=True
            if report['status'].startswith('PASS_'):
                require(report['commands'] and report['allStartedOwnedGroupsPositivelyAbsent'] and
                        all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in report['commands']),
                        'all Git command groups closed normally')
                for name,data in content.items():
                    guard(); require(read_public(WORKTREE/name)==data, 'published source file unchanged')
                report['publishedFilesUnchanged']=True
            report['freeAfter']=guard()
        except BaseException as error:
            report['status']='FAIL_PRESERVED_WITHOUT_RESET_OR_RETRY'
            report['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
        report['seconds']=round(time.monotonic()-began,3)
        checkpoint()
        print(json.dumps({'status':report['status'],'result':str(OUT/'result.json'),
            'sha256':digest(OUT/'result.json'),'commit':report.get('commit'),
            'allStartedOwnedGroupsPositivelyAbsent':report['allStartedOwnedGroupsPositivelyAbsent'],
            'errors':report['errors'],'completionErrors':report['completionErrors']}))
    if not report['status'].startswith('PASS_'):
        raise SystemExit(1)


if __name__=='__main__':
    main()
