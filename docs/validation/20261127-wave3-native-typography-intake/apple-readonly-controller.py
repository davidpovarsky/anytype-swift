#!/usr/bin/env python3
"""Bounded Apple resource GET refresh with original-key OpenSSL auth fallback.

No files are written on Mac. Credentials and raw CMS remain in memory.
Only sanitized resource facts are emitted; this cannot select an identity.
"""
import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
HELPER = Path('/Users/m1/builds/_preflight/miniapps-owner-signing-20261125T222254Z/verified-source/audit_release_resources.py')
HELPER_SHA = '7e32c559616e9525ab630ce2fde5924037323a679ec3e2c893f0274b3e2480da'
MAP = HELPER.parent.parent / 'verified-release-signing-map.json'
EXPECTED_MAP_SHA = 'e3bb406527d152e18b5870fa7f412561eb0f5e716d537ed6af9cce4328a7e3f9'
APP = '6839398256'
BUNDLE_RECORD = 'KTRM7V4TCD'
BUNDLE = 'io.anytype.app.NA6HPWARQ2'
MAIN_PROFILE = '9RF3H8H69R'
TEAM = 'NA6HPWARQ2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sanitized_item(item, allowed):
    return {'id': item.get('id'), 'type': item.get('type'),
            'attributes': {key: value for key, value in item.get('attributes', {}).items()
                           if key in allowed}}


def collection(response, allowed):
    data = response.get('data')
    assert isinstance(data, list) and len(data) <= 200
    return {'items': [sanitized_item(item, allowed) for item in data],
            'complete': not bool(response.get('links', {}).get('next')),
            'pagingTotal': response.get('meta', {}).get('paging', {}).get('total')}


"""Existing-key ES256 adapter for the original fixed-origin Apple GET helper.

JWS uses the two fixed-width integers, not ASN.1 DER:
https://www.rfc-editor.org/rfc/rfc7515.html#appendix-A.3.2
No key, signature or token is printed or written by this adapter.
"""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import subprocess
import time


def auth_require(condition, reason):
    if not condition:
        raise ValueError(reason)


def es256_der_to_jws(signature):
    """Strict P-256 ECDSA DER to the required 64-byte R||S encoding."""
    auth_require(isinstance(signature, bytes) and 8 <= len(signature) <= 72,
                 'ES256_SIGNATURE_LENGTH')
    auth_require(signature[0] == 0x30 and signature[1] == len(signature) - 2,
                 'ES256_CANONICAL_SEQUENCE')
    offset, values = 2, []
    for _ in range(2):
        auth_require(offset + 2 <= len(signature) and signature[offset] == 0x02,
                     'ES256_INTEGER_TAG')
        length = signature[offset + 1]
        offset += 2
        auth_require(1 <= length <= 33 and offset + length <= len(signature),
                     'ES256_INTEGER_LENGTH')
        encoded = signature[offset:offset + length]
        offset += length
        auth_require(encoded[0] < 0x80 and
                     (length == 1 or encoded[0] != 0 or encoded[1] >= 0x80),
                     'ES256_CANONICAL_POSITIVE_INTEGER')
        value = int.from_bytes(encoded, 'big')
        auth_require(0 < value < int('ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551', 16),
                     'ES256_SCALAR_RANGE')
        values.append(value.to_bytes(32, 'big'))
    auth_require(offset == len(signature), 'ES256_TRAILING_BYTES')
    return b''.join(values)


class OriginalKeyES256:
    calls = 0

    @classmethod
    def encode(cls, payload, key, algorithm, headers):
        auth_require(algorithm == 'ES256' and
                     headers == {'kid': os.environ['ASC_KEY_ID'], 'typ': 'JWT'},
                     'EXISTING_ES256_HEADER_REQUIRED')
        auth_require(set(payload) == {'iss', 'iat', 'exp', 'aud'} and
                     payload['iss'] == os.environ['ASC_ISSUER_ID'] and
                     payload['aud'] == 'appstoreconnect-v1' and
                     type(payload['iat']) is int and type(payload['exp']) is int and
                     payload['exp'] == payload['iat'] + 600 and
                     abs(time.time() - payload['iat']) <= 60,
                     'ORIGINAL_BOUNDED_APPLE_CLAIMS_REQUIRED')
        key_path = Path(os.environ['ASC_KEY_PATH']).expanduser()
        info = key_path.stat()
        auth_require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
                     info.st_mode & 0o077 == 0 and info.st_size <= 16384,
                     'EXISTING_PRIVATE_KEY_RESOURCE_REQUIRED')
        auth_require(hmac.compare_digest(key_path.read_bytes(), key),
                     'ORIGINAL_CONFIGURED_KEY_MISMATCH')

        def url64(raw):
            return base64.urlsafe_b64encode(raw).rstrip(b'=')

        head = {'alg': algorithm, **headers}
        signing_input = url64(json.dumps(head, separators=(',', ':')).encode()) + b'.' + \
                        url64(json.dumps(payload, separators=(',', ':')).encode())
        cls.calls += 1
        response = subprocess.run(['/usr/bin/openssl', 'dgst', '-sha256', '-sign', str(key_path)],
            input=signing_input, capture_output=True, timeout=10)
        auth_require(response.returncode == 0, 'EXISTING_KEY_TOKEN_SIGN_FAILED')
        after = key_path.stat()
        stable = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        auth_require(all(getattr(after, field) == getattr(info, field) for field in stable) and
                     hmac.compare_digest(key_path.read_bytes(), key),
                     'ORIGINAL_CONFIGURED_KEY_CHANGED')
        return (signing_input + b'.' + url64(es256_der_to_jws(response.stdout))).decode('ascii')


def main():
    began = time.time()
    result = {'schema': 'pinkha-apple-existing-resources-readonly-refresh-v1',
              'startedAt': datetime.now(timezone.utc).isoformat(),
              'appleMutations': 0, 'profileInstallations': 0, 'macFilesWritten': 0,
              'appSigningInvocations': 0, 'archives': 0, 'uploads': 0,
              'ownerFinalBundleChoice': 'NOT_DETERMINED_BY_RESOURCE_API',
              'portalMulticastRequest': {'id': 'XQ2TUWC284', 'currentStatus': 'UNKNOWN',
                                       'portalObserved': False},
              'requests': [], 'errors': [], 'profiles': []}
    raw_helper = HELPER.read_bytes()
    assert sha(raw_helper) == HELPER_SHA
    assert sha(MAP.read_bytes()) == EXPECTED_MAP_SHA
    assert os.environ['APPLE_TEAM_ID'] == TEAM
    # Compile only the three byte-identical original read-only definitions.
    names = {'AppleReadFailure', 'decode', 'apple_get'}
    tree = ast.parse(raw_helper.decode())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {node.name for node in nodes} == names
    namespace = dict(globals())
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(HELPER), 'exec'), namespace)
    original_get = ast.get_source_segment(raw_helper.decode(), next(n for n in nodes if n.name == 'apple_get'))
    auth_import = '    import jwt\n'
    auth_adapter = '    jwt = OriginalKeyES256\n'
    assert original_get.count(auth_import) == 1
    adapted_get = original_get.replace(auth_import, auth_adapter, 1)
    assert adapted_get.replace(auth_adapter, auth_import, 1) == original_get
    exec(compile(adapted_get, '<original-apple-get-with-existing-key-openssl-auth>', 'exec'), namespace)
    get = namespace['apple_get']
    result['authFallback'] = {'provider': 'existing-system-openssl-existing-configured-ES256-key',
        'originalGETSHA256': sha(original_get.encode()), 'adaptedGETSHA256': sha(adapted_get.encode()),
        'onlyGETAuthImportChanged': True, 'fixedOriginGETBoundsRedirectPolicyUnchanged': True,
        'newDependencies': 0, 'credentialRelocations': 0, 'credentialWrites': 0,
        'specification': 'https://www.rfc-editor.org/rfc/rfc7515.html#appendix-A.3.2'}
    # Reuse the configured original key only inside this process.
    os.environ['ASC_KEY_P8'] = base64.b64encode(Path(os.environ['ASC_KEY_PATH']).read_bytes()).decode()
    result['originalHelper'] = {'path': str(HELPER), 'sha256': HELPER_SHA,
        'functions': {n.name: sha(ast.get_source_segment(raw_helper.decode(), n).encode()) for n in nodes}}
    result['signingMap'] = {'path': str(MAP), 'sha256': EXPECTED_MAP_SHA}

    def request(label, path, params):
        row = {'label': label, 'method': 'GET', 'path': path, 'parameters': params,
               'startedAt': datetime.now(timezone.utc).isoformat()}
        result['requests'].append(row)
        if time.time() - began >= 240:
            row.update(status='NOT_INVOKED_AFTER_DEADLINE', error='READ_ONLY_DEADLINE')
            result['errors'].append({'label': label, 'error': 'READ_ONLY_DEADLINE'})
            return None
        try:
            response = get(path, params)
            row['status'] = 'SUCCESS'
            row['finishedAt'] = datetime.now(timezone.utc).isoformat()
            return response
        except BaseException as error:
            reason = str(error) if isinstance(error, namespace['AppleReadFailure']) else type(error).__name__
            row.update(status='FAILED', error=reason)
            result['errors'].append({'label': label, 'error': reason})
            return None

    app = request('existing-app', '/v1/apps/' + APP, {})
    if app is not None:
        result['app'] = sanitized_item(app['data'], {'name', 'bundleId', 'sku', 'primaryLocale'})
        result['candidateMatchesApp'] = result['app']['attributes'].get('bundleId') == BUNDLE
    builds = request('existing-app-builds', '/v1/builds', {'filter[app]': APP, 'limit': 200})
    if builds is not None:
        result['builds'] = collection(builds, {'version', 'uploadedDate', 'processingState',
            'expired', 'expirationDate', 'usesNonExemptEncryption', 'minOsVersion', 'lsMinimumSystemVersion'})
    bundle = request('existing-candidate-bundle', '/v1/bundleIds/' + BUNDLE_RECORD, {})
    if bundle is not None:
        result['bundle'] = sanitized_item(bundle['data'], {'name', 'identifier', 'platform', 'seedId'})
        result['candidateRecordIdentityMatches'] = result['bundle']['attributes'].get('identifier') == BUNDLE
    capabilities = request('existing-candidate-capabilities',
        '/v1/bundleIds/' + BUNDLE_RECORD + '/bundleIdCapabilities', {'limit': 200})
    if capabilities is not None:
        result['capabilities'] = collection(capabilities, {'capabilityType', 'settings'})
    profiles = request('existing-candidate-profiles', '/v1/bundleIds/' + BUNDLE_RECORD + '/profiles',
        {'limit': 200, 'fields[profiles]': 'name,profileType,profileState,uuid,expirationDate'})
    ids = [MAIN_PROFILE]
    if profiles is not None:
        result['profileList'] = collection(profiles, {'name', 'profileType', 'profileState', 'uuid', 'expirationDate'})
        active = [item['id'] for item in result['profileList']['items']
                  if item['attributes'].get('profileType') == 'IOS_APP_STORE'
                  and item['attributes'].get('profileState') == 'ACTIVE']
        result['allCurrentActiveMainProfilesWithinDecodeBound'] = len(active) <= 4 and result['profileList']['complete']
        ids.extend(i for i in active[:4] if i != MAIN_PROFILE)
    for profile_id in ids:
        response = request('existing-profile-' + profile_id, '/v1/profiles/' + profile_id,
            {'fields[profiles]': 'name,profileType,profileState,uuid,expirationDate,profileContent'})
        if response is None:
            continue
        item = response['data']
        profile = sanitized_item(item, {'name', 'profileType', 'profileState', 'uuid', 'expirationDate'})
        cms = base64.b64decode(item['attributes']['profileContent'], validate=True)
        assert len(cms) <= 2 * 1024 * 1024
        decoded = subprocess.run(['/usr/bin/security', 'cms', '-D', '-k', os.environ['APPLE_SIGNING_KEYCHAIN']],
            input=cms, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        profile.update(cmsSHA256=sha(cms), cmsBytes=len(cms), cmsDecodeExit=decoded.returncode)
        if decoded.returncode == 0:
            value = plistlib.loads(decoded.stdout)
            profile['decoded'] = {k: str(value[k]) if k == 'ExpirationDate' else value[k]
                                  for k in ('UUID', 'Name', 'ExpirationDate', 'TeamIdentifier', 'Entitlements')}
            profile['certificateSHA256'] = [sha(cert) for cert in value.get('DeveloperCertificates', [])]
            profile['requiredMulticastGranted'] = value['Entitlements'].get('com.apple.developer.networking.multicast') is True
            expected_identifier = TEAM + '.' + BUNDLE
            profile['candidateApplicationIdentifierMatches'] = value['Entitlements'].get('application-identifier') == expected_identifier
            profile['isDistribution'] = value['Entitlements'].get('get-task-allow') is False and not value.get('ProvisionedDevices')
        else:
            profile['cmsDecodeError'] = decoded.stderr.decode(errors='replace')[:1000]
            result['errors'].append({'label': 'cms-' + profile_id, 'error': 'CMS_DECODE_FAILED'})
        result['profiles'].append(profile)
    result['status'] = 'READ_ONLY_RESOURCE_OBSERVATION_COMPLETE_NOT_RELEASE_ACCEPTANCE' if not result['errors'] else 'READ_ONLY_RESOURCE_OBSERVATION_PARTIAL'
    result['apiTokenSigningOperations'] = OriginalKeyES256.calls
    result['finishedAt'] = datetime.now(timezone.utc).isoformat()
    result['seconds'] = round(time.time() - began, 3)
    assert sha(HELPER.read_bytes()) == HELPER_SHA and sha(MAP.read_bytes()) == EXPECTED_MAP_SHA
    os.environ.pop('ASC_KEY_P8', None)
    print(json.dumps(result, sort_keys=True))
    return 0 if not result['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
