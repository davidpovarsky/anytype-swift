from pathlib import Path
import os,subprocess,json,hashlib,shutil,time
root=Path('/Users/m1/builds/pinkha-native-metadata-reverification-3-20261125')
root.mkdir(mode=0o700)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
review=json.loads("{\"hydratedGraphSHA256\":\"c269274808aefd941fd2a3148261557fd194afbbd205de40b78fb4905ccf78d7\",\"modules\":[{\"goModSHA256\":\"49a2d6c73f667dc0f46322a0d6acfcba14209bfb76ef7e622d61e1091962ff34\",\"goModSum\":\"h1:CzGEWj7cYgsdH8dAjBGEr58BoE7ScuLd+fwFZ44+/x8=\",\"path\":\"github.com/kballard/go-shellquote\",\"version\":\"v0.0.0-20180428030007-95032a82bc51\"},{\"goModSHA256\":\"f685f602902b89147afff934d92506c29a1fe6b6f032a7ee3595c2635ef721b7\",\"goModSum\":\"h1:c4eWIwlEGaxC/+H1VguhU4PHXNWDCDMUlWdIWl2j1gk=\",\"path\":\"lukechampine.com/uint128\",\"version\":\"v1.2.0\"},{\"goModSHA256\":\"8fde0b3151efcca9c77a152d18339ff1fa00964c14074ce5a7a17e1434405ff4\",\"goModSum\":\"h1:Ni4zjJYJ04CDOhG7dn640WGfwBzfE0ecX8TyMB0Fv0Y=\",\"path\":\"modernc.org/cc/v3\",\"version\":\"v3.41.0\"},{\"goModSHA256\":\"2c784aefd9f52f090b145663c106b8b114f68556f2ce3c9bd9c5ac70ddb329eb\",\"goModSum\":\"h1:Sg3fwVpmLvCUTaqEUjiBDAvshIaKDB0RXaf+zgqFu8I=\",\"path\":\"modernc.org/ccgo/v3\",\"version\":\"v3.17.0\"},{\"goModSHA256\":\"4af624009641d745f6db607200ad588ffc7ad1b1e3054dde703f78285cd12523\",\"goModSum\":\"h1:Wifvo4Q/qS/h1aRoC2TffcHsnxwTikmi1AuLANuucJQ=\",\"path\":\"modernc.org/ccorpus2\",\"version\":\"v1.5.4\"},{\"goModSHA256\":\"d30b9361d75d8a3df9959aead79e93fec1b593eb8f1cf975effb33d6993b8837\",\"goModSum\":\"h1:6r8o8DLJkAnOsQaGi8fMoi+Vt6LTbDaCrkUK729D8xM=\",\"path\":\"modernc.org/lex\",\"version\":\"v1.1.1\"},{\"goModSHA256\":\"df36bdfd59d881720b5a0b082f4193e328c7f5c3938635abe215da0b303adc44\",\"goModSum\":\"h1:tOajb8S4sdfOYitzCgXDFmbVJ/LE0v1fNJ7annTw36U=\",\"path\":\"modernc.org/lexer\",\"version\":\"v1.0.4\"},{\"goModSHA256\":\"afa6c34dcde8a1b95e90c649958bb41124fb0fe1b3e67e9f811d80f11195553b\",\"goModSum\":\"h1:RzTm5RwglF/6shsKoEivo8N91nQIoWtcWI7ns+zPyGA=\",\"path\":\"modernc.org/scannertest\",\"version\":\"v1.0.2\"}],\"proofReceiptSHA256\":\"524bd4225d2f42f6c27b9506f8304bd0b8cb05c151bd3cf1f1a128c522251903\",\"sourceGraphSHA256\":\"efde759bfd6207a764104b3d3d0fd8ca747779fc0f267fab6b19e7f0881a0a9b\"}")
receipt={'status':'FAIL','purpose':'FRESH_GO_SUMDB_REVERIFICATION_AFTER_ORIGINAL_EVIDENCE_PATH_LOSS','priorProofReceiptSHA256':review['proofReceiptSHA256'],'started':time.time(),'modules':[],'commands':[],'nativeBuilds':0,'sourceSumFilesModified':False}
try:
 assert shutil.disk_usage(root).free>2*1024**3+16*1024**2
 work=root/'command-workspace';work.mkdir(mode=0o700)
 (work/'go.mod').write_text('module pinkha.invalid/metadata-reverification\n\ngo 1.27.4\n\nrequire (\n'+''.join('\t'+row['path']+' '+row['version']+'\n' for row in review['modules'])+')\n')
 cache=root/'module-cache';cache.mkdir(mode=0o700)
 go='/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go'
 env=dict(os.environ,GOROOT='/Users/m1/toolchains/anytapy-go1.27.4/go',GOTOOLCHAIN='local',GOENV='off',GOWORK='off',GOMODCACHE=str(cache),GOPATH=str(root/'go-state'),GOCACHE='/Users/m1/caches/anytapy-go1.27.4-build',GOPROXY='https://proxy.golang.org',GOSUMDB='sum.golang.org',GOPRIVATE='',GONOPROXY='',GONOSUMDB='',GOFLAGS='',GOMAXPROCS='2')
 for i,row in enumerate(review['modules'],1):
  assert shutil.disk_usage(root).free>2*1024**3
  prefix=f'{i:02d}'
  argv=[go,'list','-mod=mod','-m','-json',row['path']]
  hydrationStarted=time.time();hydration=subprocess.run(argv,cwd=work,env=env,capture_output=True,timeout=60)
  hydrationOut=root/(prefix+'.hydrate.stdout.json');hydrationErr=root/(prefix+'.hydrate.stderr.log');hydrationOut.write_bytes(hydration.stdout);hydrationErr.write_bytes(hydration.stderr)
  receipt['commands'].append({'phase':'record-authenticated-checksum','argv':argv,'exitCode':hydration.returncode,'elapsedSeconds':time.time()-hydrationStarted,'stdoutSHA256':sha(hydrationOut),'stderrSHA256':sha(hydrationErr)})
  assert hydration.returncode==0,hydration.stderr.decode()
  sums=(work/'go.sum').read_text().splitlines();assert row['path']+' '+row['version']+'/go.mod '+row['goModSum'] in sums
  started=time.time();p=subprocess.run(argv,cwd=work,env=env,capture_output=True,timeout=60)
  out=root/(prefix+'.stdout.json');err=root/(prefix+'.stderr.log');out.write_bytes(p.stdout);err.write_bytes(p.stderr)
  receipt['commands'].append({'argv':argv,'exitCode':p.returncode,'elapsedSeconds':time.time()-started,'stdoutSHA256':sha(out),'stderrSHA256':sha(err)})
  assert p.returncode==0,p.stderr.decode()
  d=json.loads(p.stdout);assert d['Path']==row['path'] and d['Version']==row['version'] and d['GoModSum']==row['goModSum']
  mod=Path(d['GoMod']);assert mod.is_relative_to(cache) and sha(mod)==row['goModSHA256']
  shutil.copyfile(mod,root/(prefix+'.go.mod'))
  lookup=cache/'cache/download/sumdb/sum.golang.org/lookup'/(row['path']+'@'+row['version'])
  assert lookup.is_file() and (row['path']+' '+row['version']+'/go.mod '+row['goModSum']).encode() in lookup.read_bytes()
  receipt['modules'].append(dict(row,exitCode=0,stdoutSHA256=sha(out),stderrSHA256=sha(err),authenticatedLookupSHA256=sha(lookup)))
 assert len(receipt['modules'])==8
 receipt['status']='PASS'
except BaseException as e:
 receipt['error']=type(e).__name__+':'+str(e)
finally:
 receipt['finished']=time.time();receipt['freeBytesAfter']=shutil.disk_usage(root).free
 (root/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
 if receipt['status']=='PASS':
  updated={'modules':review['modules'],'proofReceiptSHA256':sha(root/'receipt.json'),'originalReviewSHA256':'69b2f056688a2c009becbcac53f4c546648ab415e2e32ec5545cd295cb5dc863','priorProofReceiptSHA256':review['proofReceiptSHA256'],'qualification':'SAME_EIGHT_PINNED_MODULES_FRESH_GO_SUMDB_VERIFICATION_NO_MODULE_SOURCE_CHANGE'}
  (root/'module-metadata-hydration.json').write_text(json.dumps(updated,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'status':receipt['status'],'receiptSHA256':sha(root/'receipt.json'),'modules':len(receipt['modules']),'error':receipt.get('error'),'reviewSHA256':sha(root/'module-metadata-hydration.json') if (root/'module-metadata-hydration.json').exists() else None,'freeBytesAfter':receipt['freeBytesAfter']}))
