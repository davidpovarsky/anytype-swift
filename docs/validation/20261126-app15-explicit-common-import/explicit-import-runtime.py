import sys
assert 'importlib.util' not in sys.modules
sys.dont_write_bytecode=True
sys.path.insert(0,'/Users/m1/development/anytype-e-active-20261125/main15/control-import-dependency1')
import combined_heart_semantics_current as c
a=c.decode(c.raw(c.Path('/Users/m1/development/anytype-e-active-20261125/main15/control-import-dependency1/admission379ca.json')))
assert c.importlib.util is sys.modules['importlib.util']
p=c.qualify_app15_runtime(a,c.Path(a['sourceRoot']))
print(c.json.dumps({'status':'PASS_FRESH_BARE_INTERPRETER_RUNTIME_SOURCE_QUALIFICATION','proof':p,'nativeCalls':0,'builds':0},sort_keys=True))
