"""Prepare the fixed exclusive Host source installer; execute no remote action."""
from pathlib import Path
import ast
import base64
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
QUAL = HERE / 'qualification'
INSTALL = HERE / 'installation'
INSTALL.mkdir(exist_ok=True)
OLD = HERE.parent / 'ordinary-upload-engine/install_component_sources_prepared3.template.py'
PARENT = '/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127'

def identity(raw):
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}

manifest_raw = (QUAL / 'bookmark-component-inputs.json').read_bytes()
manifest = json.loads(manifest_raw)
controller_raw = (QUAL / 'run_bookmark_components.py').read_bytes()
controller_sha = identity(controller_raw)['sha256']
manifest_sha = identity(manifest_raw)['sha256']
methods = manifest['expectedCounts']['methods']
files = {}
for row in manifest['preparedSources']:
    if row['sourceBase'] == 'bookmark-prepared1':
        data = (HERE / row['path']).read_bytes()
        assert identity(data) == {key:row[key] for key in ('bytes','sha256')}
        files[row['path']] = data
for name in ('run_bookmark_components.py', 'bookmark-component-inputs.json',
             'qualify_bookmark_crypto_c3.py', 'qualify_current_c3_crypto.py',
             'owned_swift_commands.py', 'crypto-header-source-manifest.json'):
    files['qualification/' + name] = (QUAL / name).read_bytes()
count = len(files)
assert count in (10, 11) and methods in (27, 31)
payload = {
    'status':'PREPARATION_PAYLOAD_ONLY_NOT_INSTALLED_COMPILED_OR_RUN',
    'preparedRoot':PARENT + '/prepared1', 'controllerSHA256':controller_sha,
    'inputManifestSHA256':manifest_sha, 'expectedComponentMethodCount':methods,
    'compiledExcludedNativeMethods':0, 'excludedNativeStatus':'NOT_RUN',
    'files':[dict(path=name, contentBase64=base64.b64encode(data).decode(), **identity(data))
             for name,data in sorted(files.items())],
}
payload_raw = (json.dumps(payload, sort_keys=True, indent=2) + '\n').encode()
(INSTALL / 'source-payload.json').write_bytes(payload_raw)
old = OLD.read_text()
source = old
def once(before, after):
    global source
    assert source.count(before) == 1, (before[:90], source.count(before))
    source = source.replace(before, after)

once('exclusive ordinary-upload source packet', 'exclusive Bookmark and recovery source packet')
once("PARENT = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127')", f"PARENT = Path({PARENT!r})")
once("PREPARED = PARENT/'prepared3'", "PREPARED = PARENT/'prepared1'")
once("OUT = PARENT/'prepared3-install-attempt1'", "OUT = PARENT/'prepared1-install-attempt1'")
once("CONTROL = 'Tools/AnyEngineValidation/ordinary_file_upload/'", "CONTROL = 'qualification/'")
once("EXPECTED_CONTROLLER = 'ee54cf07a4f21b53e6a9edec65145e621477c8f51017a54c589a4eccdd116b7e'", f"EXPECTED_CONTROLLER = '{controller_sha}'")
once("EXPECTED_MANIFEST = '74bf4e399ae6988fb9e12cebd544538e76b326636a1c2d8476dd3c556b43614f'", f"EXPECTED_MANIFEST = '{manifest_sha}'")
start = source.index('EXPECTED_PATHS = {')
end = source.index('\nMIB =', start)
source = source[:start] + 'EXPECTED_PATHS = {\n' + ''.join('    '+repr(name)+',\n' for name in sorted(files)) + '}\n' + source[end:]
once("    require(PARENT.is_dir() and not PREPARED.exists() and not OUT.exists(), 'exclusive prepared/install namespaces')", "    require(os.geteuid()==0 and os.uname().nodename=='torah-social', 'authorized Oracle host')\n    physical(PARENT.parent)\n    require(PARENT.parent.is_dir() and not os.path.lexists(PARENT), 'exclusive complete Host preparation namespace')")
once("payload['expectedComponentMethodCount']==35 and payload['compiledExcludedNativeMethods']==1", f"payload['expectedComponentMethodCount']=={methods} and payload['compiledExcludedNativeMethods']==0")
once("len(rows)==18 and len({row['path'] for row in rows})==18", f"len(rows)=={count} and len({{row['path'] for row in rows}})=={count}")
once("'exact eighteen source members'", "'exact fixed Host source members'")
source = source.replace("CONTROL+'run_upload_components.py'", "CONTROL+'run_bookmark_components.py'").replace("CONTROL+'upload-component-inputs.json'", "CONTROL+'bookmark-component-inputs.json'")
start = source.index('    require({name:len(values) for name,values in methods.items()}=={')
end = source.index('    OUT.mkdir(mode=0o700)', start)
counts = {key:len(values) for key,values in manifest['methods'].items()}
source = source[:start] + f'''    require({{name:len(values) for name,values in methods.items()}}=={counts!r},
            'exact named new Host suite sizes')
    require(len({{name+'.'+method for name,values in methods.items() for method in values}})=={methods},
            'exact distinct new methods; original upload35 not selected')
    require(manifest['expectedCounts']['httpFixtureInstances']==17 and
            manifest['expectedCounts']['httpRequests']==76 and
            manifest['expectedCounts']['objectCreatePOSTs']==0,
            'original finite Bookmark HTTP obligations')
    PARENT.mkdir(mode=0o700)
    physical(PARENT)
''' + source[end:]
retention_patch = (INSTALL / 'installer-final-retention.review.patch').read_bytes()
assert identity(retention_patch)['sha256'] == '2fd95d9aff4f94ec4575ee552289e85b3939a9af6083ba46148cd599cb47499e'
patch_lines = retention_patch.decode().splitlines(keepends=True)
cursor = 0
while cursor < len(patch_lines):
    if not patch_lines[cursor].startswith('@@ '):
        cursor += 1
        continue
    cursor += 1
    before, after = [], []
    while cursor < len(patch_lines) and not patch_lines[cursor].startswith('@@ '):
        line = patch_lines[cursor]
        if line.startswith((' ', '-')):
            before.append(line[1:])
        if line.startswith((' ', '+')):
            after.append(line[1:])
        cursor += 1
    old_block, new_block = ''.join(before), ''.join(after)
    assert source.count(old_block) == 1, 'reviewed retention patch must have one exact preimage'
    source = source.replace(old_block, new_block, 1)
template = source
(INSTALL / 'install_sources.template.py').write_text(template)
source = source.replace('__PAYLOAD_BASE64__', base64.b64encode(payload_raw).decode()).replace('__PAYLOAD_SHA256__', identity(payload_raw)['sha256'])
ast.parse(source)
(INSTALL / 'install_sources.py').write_text(source)
(INSTALL / 'source-install.review.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), template.splitlines(True), fromfile='actual-uploader35-installer.py', tofile='exclusive-new-host-installer.py')))
preparation = {'status':'SOURCE_ONLY', 'installer':identity(source.encode()),
    'template':identity(template.encode()), 'payload':identity(payload_raw),
    'controller':identity(controller_raw), 'manifest':identity(manifest_raw),
    'fileCount':count, 'totalSourceBytes':sum(map(len,files.values())),
    'methods':methods, 'files':{name:identity(raw) for name,raw in sorted(files.items())}}
(INSTALL / 'source-only-preparation.json').write_text(json.dumps(preparation, sort_keys=True, indent=2)+'\n')
print(json.dumps({key:value for key,value in preparation.items() if key!='files'}))
