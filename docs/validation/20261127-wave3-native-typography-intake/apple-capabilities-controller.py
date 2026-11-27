#!/usr/bin/env python3
"""Single GET correction; retains the prior HTTP400 and all successful reads."""
import ast
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
PARENT = Path('/Users/m1/sentinelx/uploads/pinkha-wave3-apple-readonly-refresh-4e59198f-20261127.py')
PARENT_SHA = '4e59198fcf81e0cace118a8b165fcdcc07ba6aa9e14ece03edf768f31e1b8f69'
assert hashlib.sha256(PARENT.read_bytes()).hexdigest() == PARENT_SHA
spec = importlib.util.spec_from_file_location('original_reviewed_apple_read', PARENT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert os.environ['APPLE_TEAM_ID'] == m.TEAM
helper_bytes = m.HELPER.read_bytes()
assert m.sha(helper_bytes) == m.HELPER_SHA
assert m.sha(m.MAP.read_bytes()) == m.EXPECTED_MAP_SHA
names = {'AppleReadFailure', 'decode', 'apple_get'}
nodes = [node for node in ast.parse(helper_bytes.decode()).body
         if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
assert {node.name for node in nodes} == names
namespace = dict(vars(m))
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(m.HELPER), 'exec'), namespace)
original = ast.get_source_segment(helper_bytes.decode(), next(node for node in nodes if node.name == 'apple_get'))
assert original.count('    import jwt\n') == 1
adapted = original.replace('    import jwt\n', '    jwt = OriginalKeyES256\n', 1)
assert adapted.replace('    jwt = OriginalKeyES256\n', '    import jwt\n', 1) == original
exec(compile(adapted, '<original-reviewed-GET-auth-adapter>', 'exec'), namespace)
result = {'schema': 'pinkha-apple-bundle-capabilities-narrow-correction-v1',
          'status': 'FAIL_READ_ONLY_OBSERVATION', 'startedAt': datetime.now(timezone.utc).isoformat(),
          'parentController': {'path': str(PARENT), 'sha256': PARENT_SHA},
          'controllerSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'originalHelperSHA256': m.HELPER_SHA, 'adaptedGETSHA256': m.sha(adapted.encode()),
          'request': {'method': 'GET', 'path': '/v1/bundleIds/KTRM7V4TCD/bundleIdCapabilities', 'parameters': {}},
          'priorAttempt': {'job': 'job_0228a015a193', 'error': 'HTTP_400', 'parameters': {'limit': 200},
                           'originalPreserved': True},
          'successfulPriorObservationsRepeated': 0, 'appleMutations': 0, 'appSigningInvocations': 0,
          'profileInstallations': 0, 'portalRequestStatus': 'UNKNOWN', 'errors': []}
try:
    os.environ['ASC_KEY_P8'] = base64.b64encode(Path(os.environ['ASC_KEY_PATH']).read_bytes()).decode()
    response = namespace['apple_get'](result['request']['path'], {})
    result['capabilities'] = m.collection(response, {'capabilityType', 'settings'})
    result['status'] = ('READ_ONLY_COMPLETE_CAPABILITY_OBSERVATION_NOT_GRANT_OR_RELEASE_ACCEPTANCE'
                        if result['capabilities']['complete'] else 'READ_ONLY_CAPABILITY_OBSERVATION_INCOMPLETE_PAGINATION')
except BaseException as error:
    reason = str(error) if isinstance(error, namespace['AppleReadFailure']) else type(error).__name__
    result['errors'].append({'type': type(error).__name__, 'error': reason})
finally:
    os.environ.pop('ASC_KEY_P8', None)
    result['apiTokenSigningOperations'] = m.OriginalKeyES256.calls
    result['finishedAt'] = datetime.now(timezone.utc).isoformat()
    result['originalHelperAndParentUnchanged'] = (m.sha(m.HELPER.read_bytes()) == m.HELPER_SHA and
                                                m.sha(PARENT.read_bytes()) == PARENT_SHA)
    if not result['originalHelperAndParentUnchanged']:
        result['status'] = 'FAIL_ORIGINAL_CHANGED'
    print(json.dumps(result, sort_keys=True))
sys.exit(0 if result['status'].startswith('READ_ONLY_COMPLETE_') else 1)
