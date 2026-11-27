import ast,hashlib,json,os,pathlib,signal,subprocess,sys,time

ROOT=pathlib.Path('/var/lib/pinkha-c-filesv2-20261126')
SOURCE=ROOT/'recover_retained_acl.py'
OUT=ROOT/'retained-recovery-controller-gate1';OUT.mkdir(mode=0o700,exist_ok=False)
source=SOURCE.read_bytes();tree=ast.parse(source)
gate=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='native_close_gate')
namespace={};exec(compile(ast.Module(body=[gate],type_ignores=[]),str(SOURCE),'exec'),namespace)
accepted=namespace['native_close_gate']
result={'protocol':'actual-subprocess-retained-controller-cleanup-gate-v1','status':'RUNNING','controllerSHA256':hashlib.sha256(source).hexdigest(),'nativeEngineRuns':0,'actualFilesV2Acceptance':False,'tests':[]}
leader=None;positive=None;child=None
def absent(pgid):
    try:os.killpg(pgid,0);return False
    except ProcessLookupError:return True
def child_identity(pid):
    p=pathlib.Path('/proc')/str(pid);v=(p/'stat').read_text().split()
    return {'pid':pid,'pgid':os.getpgid(pid),'session':os.getsid(pid),'startTicks':v[21]}
try:
    child_code='import signal,time; signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT}); time.sleep(60)'
    leader_code='import os,sys,pathlib,json,signal,subprocess; signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT}); p=subprocess.Popen([sys.executable,"-c",sys.argv[2]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); pathlib.Path(sys.argv[1]).write_text(json.dumps({"pid":p.pid,"pgid":os.getpgrp()}))'
    leader=subprocess.Popen([sys.executable,'-c',leader_code,str(OUT/'child.json'),child_code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    assert leader.wait(timeout=5)==0
    record=json.loads((OUT/'child.json').read_text());assert record['pgid']==leader.pid
    child=child_identity(record['pid']);assert child['pgid']==child['session']==leader.pid
    row={'exitCode':leader.returncode,'groupPositivelyAbsent':absent(leader.pid),'forcedKill':False}
    assert row['exitCode']==0 and row['groupPositivelyAbsent'] is False
    assert accepted([row]) is False
    result['tests'].append({'name':'exit_zero_leader_with_actual_live_child_is_rejected','status':'PASS','observed':row,'leaderPID':leader.pid,'childIdentity':child})
    assert child_identity(child['pid'])==child
    os.killpg(leader.pid,signal.SIGTERM)
    end=time.monotonic()+5
    while not absent(leader.pid):
        assert time.monotonic()<end,'owned fixture group did not exit';time.sleep(.05)
    result['negativeFixtureGroupPositivelyAbsent']=True
    positive=subprocess.Popen([sys.executable,'-c','pass'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    assert positive.wait(timeout=5)==0
    row={'exitCode':positive.returncode,'groupPositivelyAbsent':absent(positive.pid),'forcedKill':False}
    assert row['groupPositivelyAbsent'] is True and accepted([row]) is True
    result['tests'].append({'name':'actual_clean_zero_exit_and_absent_group_is_accepted','status':'PASS','observed':row,'leaderPID':positive.pid})
    assert accepted([]) is False and accepted([{'exitCode':0,'forcedKill':False}]) is False
    result['tests'].append({'name':'empty_or_missing_group_evidence_is_rejected','status':'PASS'})
    assert SOURCE.read_bytes()==source
    result['status']='PASS_CONTROLLER_PROCESS_GATE_ONLY'
except BaseException as e:result.update(status='FAIL_CONTROLLER_PROCESS_GATE',error=repr(e))
finally:
    for process in [positive,leader]:
        if process is not None and process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
    if child is not None and pathlib.Path('/proc',str(child['pid'])).exists():
        try:
            if child_identity(child['pid'])==child:os.killpg(child['pgid'],signal.SIGTERM)
        except ProcessLookupError:pass
    result['allOwnedGroupsPositivelyAbsent']=all(absent(p.pid) for p in [positive,leader] if p is not None)
    if not result['allOwnedGroupsPositivelyAbsent']:result['status']='FAIL_CONTROLLER_PROCESS_GATE'
    (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
raise SystemExit(0 if result['status']=='PASS_CONTROLLER_PROCESS_GATE_ONLY' else 1)
