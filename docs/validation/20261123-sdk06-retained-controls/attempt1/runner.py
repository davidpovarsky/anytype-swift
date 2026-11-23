import json,os,sys,unittest
from pathlib import Path
e=Path(os.environ['PINKHA_RETAINED_CONTROL_EVIDENCE'])
events=(e/'events.jsonl').open('w')
class Results(unittest.TextTestResult):
 def startTest(self,test):
  events.write(json.dumps({'event':'START','method':test.id()})+'\n');events.flush();super().startTest(test)
 def addSuccess(self,test):
  events.write(json.dumps({'event':'PASS','method':test.id()})+'\n');events.flush();super().addSuccess(test)
 def addFailure(self,test,error):
  events.write(json.dumps({'event':'FAIL','method':test.id()})+'\n');events.flush();super().addFailure(test,error)
 def addError(self,test,error):
  events.write(json.dumps({'event':'ERROR','method':test.id()})+'\n');events.flush();super().addError(test,error)
suite=unittest.defaultTestLoader.loadTestsFromName('test_sdk06_retained_controls')
assert suite.countTestCases()==4
result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)
paths=sorted(set(str(Path(value.__file__).resolve()) for value in sys.modules.values() if getattr(value,'__file__',None) and str(Path(value.__file__).resolve()).startswith(os.environ['PINKHA_RETAINED_CONTROL_ROOT']+'/')))
(e/'loaded-repo-modules.json').write_text(json.dumps(paths,indent=2)+'\n')
events.close()
sys.exit(0 if result.wasSuccessful() else 1)
