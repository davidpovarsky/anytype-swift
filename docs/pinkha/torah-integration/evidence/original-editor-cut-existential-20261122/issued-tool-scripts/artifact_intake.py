import pathlib,subprocess,json,hashlib,zipfile,shutil,stat,datetime,re
run=45000655252
artifact=14745639782
head='d8416b161ba7af42e8459d612a94f7591470513e'
expected='97580049a684eb31ba2ca59a21835f8cbb602ad40874fc3afbe44be62ea73069'
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-45000655252-failure')
assert not out.exists(), 'Owned artifact directory already exists; do not redownload'
out.mkdir()
gh=shutil.which('gh');assert gh
archive=out/'github-artifact-14745639782.zip'
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with archive.open('wb') as f:
    p=subprocess.run([gh,'api',f'repos/davidpovarsky/anytype-swift/actions/artifacts/{artifact}/zip'],stdout=f,stderr=subprocess.PIPE,timeout=150)
assert p.returncode==0, p.stderr.decode('utf-8','replace')[:2000]
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest==expected,(digest,expected)
assert archive.stat().st_size==1374949
def extract_safe(src,dest):
    with zipfile.ZipFile(src) as z:
        infos=z.infolist()
        assert len(infos)<=250
        assert sum(x.file_size for x in infos)<=100_000_000
        names=set()
        for x in infos:
            q=pathlib.PurePosixPath(x.filename)
            assert not q.is_absolute() and '..' not in q.parts and '\\' not in x.filename and ':' not in x.filename
            assert x.filename not in names;names.add(x.filename)
            assert not stat.S_ISLNK(x.external_attr>>16)
            assert not (x.flag_bits&1)
        bad=z.testzip();assert bad is None,bad
        dest.mkdir()
        z.extractall(dest)
        return [{'path':x.filename,'bytes':x.file_size} for x in infos]
outer=extract_safe(archive,out/'outer')
inner=[]
for x in (out/'outer').rglob('*.zip'):
    dest=out/('inner-'+str(len(inner)))
    members=extract_safe(x,dest)
    inner.append({'path':str(x.relative_to(out)),'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'members':members,'extracted':str(dest)})
diagnostics=[]
records=[]
for root in [out/'outer']+[pathlib.Path(x['extracted']) for x in inner]:
    for f in root.rglob('*'):
        if not f.is_file() or f.suffix.lower() not in ('.log','.txt','.json'):continue
        data=f.read_bytes()
        if f.suffix.lower()=='.json' and len(data)<100000:
            try:
                value=json.loads(data)
                records.append({'path':str(f.relative_to(out)),'content':value})
            except Exception:pass
        if f.suffix.lower() in ('.log','.txt'):
            for n,line in enumerate(data.decode('utf-8','replace').splitlines(),1):
                if re.search(r'(^|\s)(error:|fatal error:)|\*\* BUILD (FAILED|SUCCEEDED) \*\*|TEST (FAILED|SUCCEEDED)',line):
                    diagnostics.append({'path':str(f.relative_to(out)),'line':n,'text':line[:3000]})
summary={'run':run,'artifact':artifact,'head':head,'download_started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'outer_sha256':digest,'bytes':archive.stat().st_size,'outer_members':outer,'inner':inner,'diagnostics':diagnostics,'download_count':1}
(out/'ARTIFACT_RECEIPT.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
(out/'SMALL_JSON_RECORDS.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps({'run':run,'artifact':artifact,'outer_sha256':digest,'bytes':archive.stat().st_size,'outer_members':outer,'inner':[{'path':x['path'],'sha256':x['sha256'],'count':len(x['members']),'expanded':sum(m['bytes'] for m in x['members']),'members':x['members']} for x in inner],'diagnostics':diagnostics[:50],'json_paths':[x['path'] for x in records],'directory':str(out)},ensure_ascii=False))
