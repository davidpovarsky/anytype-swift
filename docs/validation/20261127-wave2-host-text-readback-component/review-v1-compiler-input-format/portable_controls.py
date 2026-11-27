"""Pure offhost controls for new result qualification. No Swift, HTTP or process call."""
from pathlib import Path
import ast
import hashlib
import json
import os
import re
import shutil
import stat
import time

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'inputs/run_component.py'
EXPECTED='7e012aa794fd336e0c37b111013195d191ea5ae9622e0256b2dfec21387bb720'
METHODS=('testCanonicalEquivalentTextReadbackCannotCertifyWriteOrMintUndo','testExactUnicodeTextReadbackRetainsVerifiedReceiptAndExactInverse')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
module=ast.parse(raw)
selected=[node for node in module.body if isinstance(node,ast.FunctionDef) and node.name in {'xctest_result','fixture_directories','qualify_fixtures'}]
assert len(selected)==3
OUT=HERE/'portable-controls1';OUT.mkdir()
ns={'Path':Path,'json':json,'os':os,'re':re,'stat':stat,'METHODS':METHODS,'SUITE':'NativeTextEditReadbackHTTPTests'}
exec(compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec'),ns)
marker='pinkha-anchor://v1/c3BhY2U/b2JqZWN0/00000000-0000-0000-0000-000000000001'
source=lambda body:'[Before '+body+' after]('+marker+')'
pairs=[(source('\u00e9'),source('e\u0301')),(source('\u05e9\u05b8\u05c1'),source('\u05e9\u05c1\u05b8'))]
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False)+'\n')
def make(name):
 root=OUT/name;(root/'tmp').mkdir(parents=True)
 dirs=[]
 for i,(before,requested,reply) in enumerate((a,b,c) for a,b in pairs for c in (a,b)):
  d=root/'tmp'/f'pinkha-host-text-readback-synthetic-{i}';d.mkdir(mode=0o700);d.chmod(0o700);dirs.append(d)
  write(d/'config.json',{'before':before,'requested':requested,'reply':reply})
  write(d/'fixture-start.json',{'pid':100000+i,'scope':'controlled-loopback-not-native'})
  write(d/'fixture-exit.json',{'pid':100000+i,'stopReason':'stdin-eof','patches':1})
  write(d/'port.json',45000+i)
  write(d/'dispatch.json',[{'method':'PATCH','path':'/v1/spaces/space/objects/object/editor/editor_blocks/blocks/block','body':{'set':{'text':requested},'unset':[],'ifVersion':'editor-v1','ifStartedAt':'run1'},'textUTF8':list(requested.encode())}])
  write(d/'last-markdown-response.json',{'content':reply,'version':'editor-v2'})
  write(d/'last-query-response.json',{'records':[{'id':'block','type':'paragraph','text':reply,'_ver':{'text':'editor-v2'},'nav':{'parentId':'','pos':'A'}}],'total':1,'hasNext':False})
  write(d/'patch-acknowledgement.json',{'recordIds':['block'],'versionId':'native-write-v2','engineStartedAt':'run1','editorVersion':'editor-v2'})
  (d/'stderr.log').write_bytes(b'')
 ns['ROOT']=root
 lines=[f"Test Case 'NativeTextEditReadbackHTTPTests.{m}' {s}" for m in METHODS for s in ('started','passed')]
 lines+=['Executed 2 tests, with 0 failures (0 unexpected) in0.1seconds']
 lines +=['Host text readback fixture evidence: '+str(d) for d in dirs]
 return dirs,'\n'.join(lines)+'\n'
def rejects(action):
 try:action()
 except AssertionError:return
 raise AssertionError('Malformed synthetic evidence was accepted')
results=[];started=time.monotonic()
def record(name,fn):
 t=time.monotonic()
 try:fn();results.append({'name':name,'status':'PASS','seconds':time.monotonic()-t})
 except BaseException as error:results.append({'name':name,'status':'FAIL','error':repr(error)});raise

def valid():
 _,log=make('valid');assert ns['xctest_result'](log)['XCTestCases']==2;assert len(ns['qualify_fixtures'](log))==4
record('valid_source_shape_two_cases_four_synthetic_vectors',valid)
def zero():
 _,log=make('zero');rejects(lambda:ns['xctest_result']('Test run with 0 tests passed after0.0seconds\n'))
record('zero_swift_testing_footer_is_not_two_xctest_cases',zero)
def extra():
 _,log=make('extra');rejects(lambda:ns['xctest_result'](log+"Test Case 'NativeSnapshotTests.oldMethod' started\n"))
record('unexpected_original_method_is_rejected',extra)
def wrongbytes():
 dirs,log=make('wrongbytes');d=dirs[1];q=json.loads((d/'last-query-response.json').read_text());cfg=json.loads((d/'config.json').read_text());q['records'][0]['text']=cfg['before'];write(d/'last-query-response.json',q);rejects(lambda:ns['qualify_fixtures'](log))
record('canonical_equivalent_wrong_raw_query_bytes_are_rejected',wrongbytes)
def missingeof():
 dirs,log=make('missing-eof');d=dirs[0];end=json.loads((d/'fixture-exit.json').read_text());end['stopReason']='deadline';write(d/'fixture-exit.json',end);rejects(lambda:ns['qualify_fixtures'](log))
record('deadline_exit_cannot_replace_owned_stdin_eof',missingeof)
receipt={'schema':'pinkha-host-two-method-portable-controls/v1','status':'PASS_SYNTHETIC_CONTROLS_ONLY','sourceSHA256':EXPECTED,'controls':results,'seconds':time.monotonic()-started,'SwiftCalls':0,'HTTPFixtureInvocations':0,'NativeCalls':0,'OracleCalls':0,'MacCalls':0,'actualXCTestCasesRun':0,'syntheticIDsAreNotProcessObservations':True,'actualProducerFormatCompatibility':'Still requires actual Swift/XCTest execution; examples are synthetic source-shape controls only.'}
write(OUT/'result.json',receipt);print(json.dumps(receipt,indent=2))
