import pathlib,subprocess,json,hashlib,zipfile,shutil,stat,datetime,re
run=45006133053
artifact=14747819041
head='7b594f6f28961258d81b0eb2e7a29c7b047bb1d2'
expected='c9e75bf524bb2fc4c9ed25e16153bb494009cb9ebfb7ac824bf6009aba183c98'
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-45006133053-failure')
assert not out.exists(), 'Owned artifact directory already exists; do not redownload'
out.mkdir()
(out/'download_and_diagnose.py').write_bytes(pathlib.Path(__file__).read_bytes())
(out/'GITHUB_ARTIFACTS.json').write_text("{\"total_count\":1,\"artifacts\":[{\"id\":14747819041,\"node_id\":\"MDg6QXJ0aWZhY3QxNDc0NzgxOTA0MQ==\",\"name\":\"Otzaria-Original-Editor-Framework-Evidence-7b594f6f28961258d81b0eb2e7a29c7b047bb1d2-45006133053-1\",\"size_in_bytes\":14871793,\"url\":\"https://api.github.com/repos/davidpovarsky/anytype-swift/actions/artifacts/14747819041\",\"archive_download_url\":\"https://api.github.com/repos/davidpovarsky/anytype-swift/actions/artifacts/14747819041/zip\",\"expired\":false,\"digest\":\"sha256:c9e75bf524bb2fc4c9ed25e16153bb494009cb9ebfb7ac824bf6009aba183c98\",\"created_at\":\"2026-11-22T09:27:41Z\",\"updated_at\":\"2026-11-22T09:27:41Z\",\"expires_at\":\"2026-12-06T09:27:40Z\",\"workflow_run\":{\"id\":45006133053,\"repository_id\":1289863025,\"head_repository_id\":1289863025,\"head_branch\":\"codex/otzaria-original-editor-framework-v11-host-reviewed-20261122\",\"head_sha\":\"7b594f6f28961258d81b0eb2e7a29c7b047bb1d2\"}}]}",encoding='utf8')
(out/'GITHUB_JOBS.json').write_text("{\"total_count\":1,\"jobs\":[{\"id\":137158035220,\"run_id\":45006133053,\"workflow_name\":\"Original editor framework external import and resources\",\"head_branch\":\"codex/otzaria-original-editor-framework-v11-host-reviewed-20261122\",\"run_url\":\"https://api.github.com/repos/davidpovarsky/anytype-swift/actions/runs/45006133053\",\"run_attempt\":1,\"node_id\":\"CR_kwDOTOG_cc8AAAAf70GHFA\",\"head_sha\":\"7b594f6f28961258d81b0eb2e7a29c7b047bb1d2\",\"url\":\"https://api.github.com/repos/davidpovarsky/anytype-swift/actions/jobs/137158035220\",\"html_url\":\"https://github.com/davidpovarsky/anytype-swift/actions/runs/45006133053/job/137158035220\",\"status\":\"completed\",\"conclusion\":\"failure\",\"created_at\":\"2026-11-22T09:09:12Z\",\"started_at\":\"2026-11-22T09:09:14Z\",\"completed_at\":\"2026-11-22T09:27:46Z\",\"name\":\"original-editor-framework\",\"steps\":[{\"name\":\"Set up job\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":1,\"started_at\":\"2026-11-22T09:09:14Z\",\"completed_at\":\"2026-11-22T09:09:15Z\"},{\"name\":\"Checkout exact reviewed source\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":2,\"started_at\":\"2026-11-22T09:09:15Z\",\"completed_at\":\"2026-11-22T09:09:23Z\"},{\"name\":\"Use the original native ARM64 Python contract\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":3,\"started_at\":\"2026-11-22T09:09:23Z\",\"completed_at\":\"2026-11-22T09:09:23Z\"},{\"name\":\"Bind original app sources resources packages and the additive target\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":4,\"started_at\":\"2026-11-22T09:09:23Z\",\"completed_at\":\"2026-11-22T09:09:34Z\"},{\"name\":\"Checkout the immutable original canonical Hanlin source\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":5,\"started_at\":\"2026-11-22T09:09:34Z\",\"completed_at\":\"2026-11-22T09:09:41Z\"},{\"name\":\"Prepare and verify the original SDK snapshot\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":6,\"started_at\":\"2026-11-22T09:09:41Z\",\"completed_at\":\"2026-11-22T09:09:42Z\"},{\"name\":\"Verify actual Xcode27 and create original owned OS27 simulators\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":7,\"started_at\":\"2026-11-22T09:09:42Z\",\"completed_at\":\"2026-11-22T09:09:58Z\"},{\"name\":\"Verify the recorded original Heart producer and exact binary slices\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":8,\"started_at\":\"2026-11-22T09:09:58Z\",\"completed_at\":\"2026-11-22T09:10:17Z\"},{\"name\":\"Approve only the exact reviewed Equatable compiler macro\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":9,\"started_at\":\"2026-11-22T09:10:17Z\",\"completed_at\":\"2026-11-22T09:10:18Z\"},{\"name\":\"Build the genuine framework and execute the separate binary consumer\",\"status\":\"completed\",\"conclusion\":\"failure\",\"number\":10,\"started_at\":\"2026-11-22T09:10:18Z\",\"completed_at\":\"2026-11-22T09:27:36Z\"},{\"name\":\"Restore only this run's exact macro approval afterimage\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":11,\"started_at\":\"2026-11-22T09:27:36Z\",\"completed_at\":\"2026-11-22T09:27:37Z\"},{\"name\":\"Preserve actual source input command build and runtime evidence\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":12,\"started_at\":\"2026-11-22T09:27:37Z\",\"completed_at\":\"2026-11-22T09:27:39Z\"},{\"name\":\"Upload source-bound framework acceptance evidence\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":13,\"started_at\":\"2026-11-22T09:27:39Z\",\"completed_at\":\"2026-11-22T09:27:41Z\"},{\"name\":\"Upload only the actually qualified simulator framework closure\",\"status\":\"completed\",\"conclusion\":\"skipped\",\"number\":14,\"started_at\":\"2026-11-22T09:27:41Z\",\"completed_at\":\"2026-11-22T09:27:41Z\"},{\"name\":\"Post Checkout the immutable original canonical Hanlin source\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":26,\"started_at\":\"2026-11-22T09:27:41Z\",\"completed_at\":\"2026-11-22T09:27:42Z\"},{\"name\":\"Post Use the original native ARM64 Python contract\",\"status\":\"completed\",\"conclusion\":\"skipped\",\"number\":27,\"started_at\":\"2026-11-22T09:27:42Z\",\"completed_at\":\"2026-11-22T09:27:42Z\"},{\"name\":\"Post Checkout exact reviewed source\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":28,\"started_at\":\"2026-11-22T09:27:42Z\",\"completed_at\":\"2026-11-22T09:27:43Z\"},{\"name\":\"Complete job\",\"status\":\"completed\",\"conclusion\":\"success\",\"number\":29,\"started_at\":\"2026-11-22T09:27:43Z\",\"completed_at\":\"2026-11-22T09:27:44Z\"}],\"check_run_url\":\"https://api.github.com/repos/davidpovarsky/anytype-swift/check-runs/137158035220\",\"labels\":[\"xcode-27\"],\"runner_id\":1000023292,\"runner_name\":\"GitHub Actions 1000023292\",\"runner_group_id\":0,\"runner_group_name\":\"GitHub Actions\"}]}",encoding='utf8')
gh=shutil.which('gh');assert gh
archive=out/'github-artifact-14747819041.zip'
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with archive.open('wb') as f:
    p=subprocess.run([gh,'api',f'repos/davidpovarsky/anytype-swift/actions/artifacts/{artifact}/zip'],stdout=f,stderr=subprocess.PIPE,timeout=150)
assert p.returncode==0, p.stderr.decode('utf-8','replace')[:2000]
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest==expected,(digest,expected)
assert archive.stat().st_size==14871793
def extract_safe(src,dest):
    with zipfile.ZipFile(src) as z:
        infos=z.infolist()
        assert len(infos)<=2500
        assert sum(x.file_size for x in infos)<=500_000_000
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
