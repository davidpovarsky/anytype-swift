from pathlib import Path,PurePosixPath
import json,hashlib,base64,zipfile,io,subprocess,datetime,time

root=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-native-followups-20261122')
transfer=json.loads((root/'publishing-source-bae494.transfer.json').read_text(encoding='utf-8'))
raw=base64.b64decode(transfer['zip_base64'],validate=True)
assert len(raw)==transfer['bytes'] and hashlib.sha256(raw).hexdigest()==transfer['sha256']
out=root/'publishing-source-bae494';assert not out.exists();out.mkdir()
(root/'publishing-source-bae494.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    for member in z.infolist():
        p=PurePosixPath(member.filename)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in member.filename
        target=out.joinpath(*p.parts);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(z.read(member))
checkpoint=json.loads((out/'CHECKPOINT_MANIFEST.json').read_text(encoding='utf-8'))
for f in checkpoint['files']:
    assert hashlib.sha256((out/f['path']).read_bytes()).hexdigest()==f['sha256']
m=json.loads((out/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
assert m['combined_patch']['sha256']=='bae4945918224d3afd259829745032eba2f3b82cfa0d47eadc6473d46ded2c4c'
assert hashlib.sha256((out/m['combined_patch']['path']).read_bytes()).hexdigest()==m['combined_patch']['sha256']
assert len(m['files'])==10
for f in m['files']:
    for folder,key in [('source','source_sha256'),('base','base_sha256')]:
        assert hashlib.sha256((out/folder/f['path']).read_bytes()).hexdigest()==f[key]
command=[r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE',
         '-frontend','-parse','-target','arm64-apple-ios27.0-simulator','-D','DEBUG']
command += [str(out/'source'/f['path']) for f in m['files']]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
p=subprocess.run(command,capture_output=True,timeout=120)
report={'scope':'Only ten complete changed Swift files; actual Swift syntax with simulator target. No Apple SDK module typecheck, linked service/Invocation execution, Lib, or Native publishing.',
        'base_commit':m['base_commit'],'patch_sha256':m['combined_patch']['sha256'],'archive_sha256':transfer['sha256'],
        'checkpoint':str(out),'inputs':m['files'],'command':command,'compiler_processes':1,
        'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'duration_s':time.monotonic()-t,'exit_code':p.returncode,
        'stdout':p.stdout.decode('utf-8','replace'),'stderr':p.stderr.decode('utf-8','replace'),
        'apple_typecheck':'NOT_RUN','native':'NOT_RUN'}
(out/'validation/PARSE_RESULT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
control=root/'publishing-controls-bae494-r2/RESULT.json'
if control.is_file():
    (out/'validation/CONTROL_RESULT.json').write_bytes(control.read_bytes())
print(json.dumps(report))
raise SystemExit(p.returncode)
