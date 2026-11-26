import ast,copy,hashlib,json,sys
from pathlib import Path
root=Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
d=root/'Tools/CurrentAppleValidation/combined_heart_semantics/build14'
sys.path[:0]=[str(d),str(root/'Tools/Hanlin'),str(root/'Tools/PinkhaSimulatorGate'),str(root/'Tools/PinkhaNativeDerived'),str(root/'Tools/AnyEnginePort'),str(root/'Tools/CurrentAppleValidation')]
import focus_lifecycle_profile as focus
import combined_t5_pending_gateway as pending
contract=focus.source_contract(root)
assert contract['expected_methods']==19 and contract['declared_cases']==29
def require(c,m):
 if not c:raise ValueError(m)
control=(d/'combined_host_acceptance_current.py').read_text();tree=ast.parse(control)
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['invocation_selectors','exact_enumeration']]
ns={'require':require,'NATIVE':'AnytypeTests'}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-new-selector-functions>','exec'),ns)
selectors=contract['compiled_identifiers']
assert ns['invocation_selectors'](selectors,contract)==['AnytypeTests/TextBlockFocusLifecycleTests']
payload={'errors':[],'values':[{'testPlan':'AnytypeTests','enabledTests':[{'identifier':s} for s in selectors],'disabledTests':[]}]}
ns['exact_enumeration'](payload,selectors)
cases={'wholeAffectedFocusSource19Methods29Cases':'PASS_SOURCE_CONTROL','exactFocusCompiledEnumeration':'PASS_PURE_CONTROL'}
for name,mutate in [('missingMethod',lambda c:c['compiled_identifiers'].pop()),('wrongSourceHash',lambda c:c.update(source_sha256='0'*64)),('wrongCaseCount',lambda c:c.update(declared_cases=3)),('foreignSuite',lambda c:c['compiled_identifiers'].__setitem__(0,'AnytypeTests/Other/test()'))]:
 c=copy.deepcopy(contract);mutate(c)
 try:ns['invocation_selectors'](c['compiled_identifiers'],c)
 except (ValueError,KeyError,AssertionError):cases[name]='PASS_REQUIRED_REFUSAL'
 else:raise AssertionError(name)
for name,mutate in [('missingCompiled',lambda x:x['values'][0]['enabledTests'].pop()),('extraCompiled',lambda x:x['values'][0]['enabledTests'].append({'identifier':'AnytypeTests/Other/test()'})),('disabledSelected',lambda x:x['values'][0]['disabledTests'].append(x['values'][0]['enabledTests'][0]))]:
 value=copy.deepcopy(payload);mutate(value)
 try:ns['exact_enumeration'](value,selectors)
 except (ValueError,KeyError,AssertionError):cases[name]='PASS_REQUIRED_REFUSAL'
 else:raise AssertionError(name)
expected='pinkha-dual-runtime-v1-11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b'
assert pending.expected_runtime_version()==expected
for profile in ['r15','dual-engine-runtime','',None]:
 try:pending.expected_runtime_version(profile)
 except RuntimeError as error:
  assert str(error)=='Exact combined pending profile required'
 else:raise AssertionError('foreign runtime profile')
cases['fourForeignRuntimeProfiles']='PASS_REQUIRED_REFUSAL'
print(json.dumps({'status':'PASS_ADDITIVE_SOURCE_SELECTION_CONTROLS_NOT_APPLE_ACCEPTANCE','cases':cases,'focusSource':contract,'actualAppleTests':0,'engineCalls':0,'simulatorsCreated':0},indent=2,sort_keys=True))
