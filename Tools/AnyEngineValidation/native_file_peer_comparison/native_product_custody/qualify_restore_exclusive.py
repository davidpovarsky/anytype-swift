#!/usr/bin/env python3
"""Run four disposable filesystem controls; never restore the actual native792."""
from pathlib import Path
import hashlib,json,os,platform,shutil,signal,subprocess,sys,time

OUT=Path(__file__).resolve().parent
CANDIDATE=OUT/'restore.py'
TEST=OUT/'test_restore_exclusive.py'
RESTORED=Path('/var/lib/pinkha-c-filesv2-20261126/acl-refresh-native1/any')
RAW=Path('/mnt/development/projects/evidence/pinkha-w1-network-native792-raw-20261127/any-79248a63132a0146')
CURRENT=Path('/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/any')
RAW_SHA='79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857'
CURRENT_SHA='0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07'
os.umask(0o077)
started=time.monotonic()
result={'protocol':'atomic-exclusive-native-restore-disposable-controls-v1','status':'RUNNING','testsExpected':4,'actualNativeRestoreCalls':0,'nativeProcesses':0,'accountOpens':0,'goBuilds':0,'swiftBuilds':0,'errors':[]}
p=None

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024**2),b''):h.update(data)
    return h.hexdigest()

def save():
    result['seconds']=round(time.monotonic()-started,3)
    tmp=OUT/'result.json.tmp'
    with tmp.open('w') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,OUT/'result.json')

def absent():
    try:os.killpg(p.pid,0)
    except ProcessLookupError:return True
    return False

def interrupted(*_):raise RuntimeError('owned disposable restore controls interrupted')

signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
# Claim the output before entering any cleanup or persistence path. A second
# invocation must fail here without touching its predecessor's receipt or
# reading native custody inputs. O_EXCL also rejects an existing symlink.
receipt_fd=os.open(OUT/'result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
os.close(receipt_fd)

try:
    assert sha(CANDIDATE)=='00bb2666c2af282d70dcba8f6092b978f61744f1dcc94e58631ff19d3f8df64c'
    assert sha(TEST)=='3525a82435a8791768582cef875c0bebf7e1820ec206e0d7c70f15a8889a120e'
    assert not RESTORED.exists() and not RESTORED.is_symlink()
    assert sha(RAW)==RAW_SHA and sha(CURRENT)==CURRENT_SHA
    assert shutil.disk_usage(OUT).free>=512*1024**2+1024**2
    result.update(candidateSHA256=sha(CANDIDATE),testsSHA256=sha(TEST),controllerSHA256=sha(Path(__file__)),python=sys.version,platform=platform.platform(),productCustodyBefore={'raw':RAW_SHA,'current':CURRENT_SHA,'restoredPathAbsent':True},resourcePolicy={'disposableFixtureBudgetBytes':1024**2,'evidenceAndTempOnDevelopment':True,'noNativeOrCompilerAdmissionUsed':True})
    tmp=OUT/'disposable-temp';tmp.mkdir()
    env=os.environ.copy();env.update(TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
    log_path=OUT/'tests.log'
    with log_path.open('xb') as log:
        p=subprocess.Popen([sys.executable,'-B',str(TEST)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        result['pid']=p.pid;save()
        deadline=time.monotonic()+60
        while p.poll() is None:
            assert time.monotonic()<deadline,'bounded disposable tests'
            assert log_path.stat().st_size<128*1024
            time.sleep(.05)
        p.wait()
    result.update(exitCode=p.returncode,ownedGroupAbsent=absent(),logSHA256=sha(log_path))
    text=log_path.read_text()
    assert p.returncode==0 and result['ownedGroupAbsent']
    rows=[line for line in text.splitlines() if line.startswith('test_')]
    assert len(rows)==4 and all(line.endswith(' ... ok') for line in rows)
    assert 'Ran 4 tests in ' in text and text.endswith('\nOK\n') and 'skipped' not in text.lower()
    assert not list(tmp.iterdir()),'all disposable fixtures cleaned by their owner'
    result['passedMethods']=rows
    result['status']='PASS_FOUR_DISPOSABLE_EXCLUSIVE_INSTALL_CONTROLS_NO_PRODUCT_RESTORE'
except BaseException as error:
    result.update(status='FAIL_DISPOSABLE_RESTORE_CONTROLS',error=repr(error))
finally:
    if p is not None:
        try:
            if p.poll() is None or not absent():
                result['forcedCleanup']=True
                if not absent():os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if not absent():os.killpg(p.pid,signal.SIGKILL)
                    p.wait(timeout=5)
                result['status']='FAIL_DISPOSABLE_RESTORE_CONTROLS'
            result['ownedGroupAbsent']=absent();assert result['ownedGroupAbsent']
        except BaseException as error:
            result['status']='FAIL_DISPOSABLE_RESTORE_CONTROLS';result['errors'].append({'cleanup':repr(error)})
    try:
        assert not RESTORED.exists() and not RESTORED.is_symlink()
        assert sha(RAW)==RAW_SHA and sha(CURRENT)==CURRENT_SHA
        assert sha(CANDIDATE)=='00bb2666c2af282d70dcba8f6092b978f61744f1dcc94e58631ff19d3f8df64c'
        assert sha(TEST)=='3525a82435a8791768582cef875c0bebf7e1820ec206e0d7c70f15a8889a120e'
        result['productsAndSourceUnchanged']=True
        result['actualRestoredNativePathStillAbsent']=True
    except BaseException as error:
        result['status']='FAIL_DISPOSABLE_RESTORE_CONTROLS';result['errors'].append({'finalCustody':repr(error)})
    save()
print(json.dumps({'status':result['status'],'result':str(OUT/'result.json'),'sha256':sha(OUT/'result.json'),'seconds':result['seconds']}))
raise SystemExit(0 if result['status'].startswith('PASS') else 1)
