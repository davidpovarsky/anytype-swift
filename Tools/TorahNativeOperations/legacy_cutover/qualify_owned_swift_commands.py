#!/usr/bin/env python3
"""Five actual Python process controls; no compiler or native account invocation."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import sys
import time
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def save(path, value):
    raw = (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    temporary = path.with_name(path.name+'.new')
    with temporary.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def main():
    if sys.flags.optimize:
        raise RuntimeError('acceptance assertions must remain enabled')
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--helper-sha',required=True)
    args=parser.parse_args()
    expected_parent=Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127')
    root=args.root
    assert root.parent==expected_parent and re.fullmatch(r'swift-lifecycle-controls[1-9][0-9]{0,2}',root.name)
    assert root.parent.resolve()==root.parent and not os.path.lexists(root)
    helper=Path(__file__).parent/'owned_swift_commands.py'
    assert helper.resolve()==helper and not helper.is_symlink()
    assert re.fullmatch('[a-f0-9]{64}',args.helper_sha) and digest(helper)==args.helper_sha
    spec=importlib.util.spec_from_file_location('qualified_owned_swift_commands',helper)
    owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
    os.umask(0o077);root.mkdir(mode=0o700)
    began=time.monotonic()
    result={'status':'FAIL','controllerSHA256':digest(Path(__file__)),'helperSHA256':args.helper_sha,
            'nativeInvocations':0,'compilerInvocations':0,'methods':[],'commands':[],'errors':[]}

    def guard():
        assert time.monotonic()-began<120,'bounded lifecycle control deadline'
        assert shutil.disk_usage('/').free>=2*1024**3,'unchanged root runtime floor'
        assert shutil.disk_usage(root).free>=512*1024**2,'unchanged development runtime floor'
        assert sum(p.stat().st_size for p in root.rglob('*') if p.is_file())<8*1024**2
        return None

    healthy='import signal; s=signal.pthread_sigmask(signal.SIG_BLOCK, []); assert signal.SIGTERM not in s and signal.SIGINT not in s; print("child signals unblocked")'
    sleeper='import time; time.sleep(60)'
    residual='import os, subprocess, sys; subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); os._exit(0)'
    try:
        guard()
        for name,child,expected in [('normal',healthy,None),
                ('started-journal-failure',sleeper,'injected started journal failure'),
                ('leader-exits-with-descendant',residual,'owned descendants outlived command leader'),
                ('controller-SIGTERM',sleeper,'owned Swift controller interrupted by signal '+str(signal.SIGTERM)),
                ('controller-SIGINT',sleeper,'owned Swift controller interrupted by signal '+str(signal.SIGINT))]:
            guard()
            # Reproduce inherited blocked termination signals before installing
            # the controller. The real child must independently receive defaults.
            signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
            owned.install_interrupt_handlers()
            def scenario_save(path,value):
                if path.name=='started.json' and name=='started-journal-failure':
                    raise OSError('injected started journal failure')
                save(path,value)
                if path.name=='started.json' and name.startswith('controller-'):
                    os.kill(os.getpid(),signal.SIGTERM if name.endswith('SIGTERM') else signal.SIGINT)
            error=None
            try:
                log,row=owned.run(root/name,[sys.executable,'-B','-c',child],root,dict(os.environ),15,
                                  guard,scenario_save,digest,result['commands'])
            except BaseException as caught:
                error=caught
            row=result['commands'][-1]
            assert row['processGroupAbsent'] and row['cleanupErrors']==[],row
            assert row['unreapedLeaderDuringGroupCleanup']
            if expected is None:
                assert error is None and row['exitCode']==0 and not row['forcedCleanup'] and row['signals']==[]
                assert log.read_text()=='child signals unblocked\n'
            else:
                assert error is not None and str(error)==expected,(name,error)
                assert row['originalError']['message']==expected
                assert row['forcedCleanup'] and row['signals']
                if name=='started-journal-failure':
                    assert row['originalError']['type']=='OSError'
                if name=='leader-exits-with-descendant':
                    assert row['exitCode']==0 and row['residualMembersAfterLeaderExit']
            result['methods'].append({'name':name,'status':'PASS','expectedFailure':expected,
                                      'retainedOriginalError':row.get('originalError'),'groupPositivelyAbsent':True})
            save(root/'result.json',result)
        assert len(result['methods'])==5 and len(result['commands'])==5
        assert digest(helper)==args.helper_sha
        result['status']='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
    except BaseException as error:
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        owned.ignore_interrupts()
        result['allOwnedGroupsPositivelyAbsent']=all(row.get('processGroupAbsent') for row in result['commands'])
        if not result['allOwnedGroupsPositivelyAbsent']:result['status']='FAIL_UNRESOLVED_OWNED_PROCESS_GROUP'
        result['seconds']=time.monotonic()-began
        result['freeAfter']={p:shutil.disk_usage(p).free for p in ['/','/mnt/development']}
        save(root/'result.json',result)
    print(json.dumps({'status':result['status'],'result':str(root/'result.json'),'sha256':digest(root/'result.json'),
                      'methods':len(result['methods']),'seconds':result['seconds'],'errors':result['errors']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
