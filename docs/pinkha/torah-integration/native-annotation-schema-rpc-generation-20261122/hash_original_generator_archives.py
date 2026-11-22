import concurrent.futures,hashlib,json,pathlib,shutil,subprocess,time,zipfile
assets=json.loads("[{\"repo\":\"krzysztofzablocki/Sourcery\",\"id\":216564143,\"name\":\"sourcery-2.2.6.zip\",\"bytes\":44677397,\"executable_basename\":\"sourcery\"},{\"repo\":\"mgolovko/SwiftGen\",\"id\":244900649,\"name\":\"swiftgen-6.6.4-alpha.0-macos.zip\",\"bytes\":2969092,\"executable_basename\":\"swiftgen\"},{\"repo\":\"apple/swift-protobuf\",\"id\":301971212,\"name\":\"protoc-32.1.artifactbundle.zip\",\"bytes\":15654937,\"sha256\":\"3cfb7e13baac742c7f7ba2ff835d22356af18af2b8b7c4d630aacea5eb893fb3\",\"executable_basename\":\"protoc\"}]")
owned=pathlib.Path(r'C:\Users\DAVID\Code\otzaria-schema-rpc-tool-pins-20261122')
owned.mkdir(exist_ok=False)
gh=shutil.which('gh');assert gh
started=time.monotonic()
def one(asset):
 dest=owned/asset['name']
 with dest.open('xb') as out:
  r=subprocess.run([gh,'api',f"repos/{asset['repo']}/releases/assets/{asset['id']}",'-H','Accept: application/octet-stream'],stdout=out,stderr=subprocess.PIPE,timeout=120)
 if r.returncode:raise RuntimeError('Original release download failed for '+asset['name']+': '+r.stderr.decode(errors='replace')[:200])
 data=dest.read_bytes();h=hashlib.sha256(data).hexdigest()
 assert len(data)==asset['bytes'],(asset['name'],len(data))
 if 'sha256' in asset:assert h==asset['sha256']
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(set(z.namelist()))
  members=[]
  for name in z.namelist():
   path=pathlib.PurePosixPath(name)
   if path.name==asset['executable_basename'] or name.endswith('/info.json'):
    raw=z.read(name);members.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'magic_hex':raw[:4].hex()})
  assert members
  info_names=[n for n in z.namelist() if n.endswith('.artifactbundle/info.json')]
  artifact_info=json.loads(z.read(info_names[0])) if len(info_names)==1 else None
 row={'repository':asset['repo'],'asset_id':asset['id'],'file_name':asset['name'],'path':str(dest),'bytes':len(data),'sha256':h,'upstream_sha256_verified':asset.get('sha256'),'zip_crc':'PASS','binary_inventory':members,'artifact_info':artifact_info,'tools_executed':0}
 (owned/(asset['name']+'.receipt.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
 return row
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(one,a) for a in assets]
 for f in futures:rows.append(f.result())
receipt={'status':'ORIGINAL_RELEASE_ARCHIVES_HASHED_NOT_EXECUTED','owned_directory':str(owned),'seconds':round(time.monotonic()-started,3),'assets':rows,'scope':'Original pinned generator assets only. No installation, generator invocation, compilation, secret, native operation or CI dispatch.'}
(owned/'TOOL_ARCHIVES.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
