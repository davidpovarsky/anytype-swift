import sys
assert 'importlib.util' not in sys.modules
sys.dont_write_bytecode=True
sys.path.insert(0,'/Users/m1/development/anytype-e-active-20261125/main15/control-42b036')
import combined_heart_semantics_current as c
a=c.decode(c.raw(c.Path('/Users/m1/development/anytype-e-active-20261125/main15/control-42b036/admission379ca.json')))
try:
 c.qualify_app15_runtime(a,c.Path(a['sourceRoot']))
except AttributeError as e:
 assert str(e)=="module 'importlib' has no attribute 'util'"
 print(c.json.dumps({'status':'EXPECTED_ORIGINAL_MISSING_IMPORT_FAILURE','error':str(e),'nativeCalls':0,'builds':0}))
else: raise AssertionError('original missing dependency unexpectedly succeeded')
