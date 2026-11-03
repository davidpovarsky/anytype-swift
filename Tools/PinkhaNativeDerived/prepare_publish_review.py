"""Inventory this isolated feature for scoped owner review. Never stages/commits."""
from pathlib import Path
import difflib,hashlib,json,subprocess

root=Path(__file__).resolve().parents[2]
out=root/'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/publish'
out.mkdir(parents=True,exist_ok=True)
def git(*args):return subprocess.check_output(['git','-C',str(root),*args]).decode('utf8')
paths=set(git('diff','--name-only').splitlines())
paths.update(['.github/workflows/torah-inspector-ipados27.yml',
    'Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/Filters/List/SetFiltersListViewModel.swift'])
tracked=set(git('ls-files').splitlines())
new=git('ls-files','--others','--exclude-standard').splitlines()
for path in new:
    if path=='Modules/PinkhaKit/Package.resolved':continue
    if '__pycache__' in path or '/.build/' in path:continue
    relevant=path.startswith(('Anytype/Sources/Pinkha/','AnyTypeTests/Pinkha/TorahNativeDerived',
        'Modules/PinkhaHeart/','Tools/PinkhaNativeDerived/','Tools/TorahNativeDerivedSpike/'))
    relevant=relevant or path in [
        '.github/workflows/pinkha-native-derived.yml',
        'Modules/PinkhaKit/Sources/PinkhaKit/Schema/TorahNativePropertySchema.swift',
        'Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahDerivedQueryProjection.swift',
        'Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/TorahDerivedQueryProjectionTests.swift',
        'Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/TorahNativeSchemaProvisionerTests.swift',
        'Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Fixtures/derived-query-golden.json']
    relevant=relevant or (path.startswith('docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/') and '/publish/' not in path)
    if relevant:paths.add(path)
baseline_paths=sorted(paths & tracked)
batch=subprocess.check_output(['git','-C',str(root),'cat-file','--batch'],input=('\n'.join('HEAD:'+path for path in baseline_paths)+'\n').encode())
baseline={};offset=0
for path in baseline_paths:
    end=batch.index(b'\n',offset);header=batch[offset:end].split();size=int(header[-1]);offset=end+1
    baseline[path]=batch[offset:offset+size].decode('utf8');offset+=size+1
inventory=[];patch=''
for path in sorted(paths):
    content=(root/path).read_bytes().replace(b'\r\n',b'\n')
    inventory.append(dict(path=path,sha256=hashlib.sha256(content).hexdigest(),bytes=len(content)))
    is_tracked=path in tracked
    before=baseline[path] if is_tracked else ''
    after=content.decode('utf8')
    if before==after:continue
    patch+='diff --git a/'+path+' b/'+path+'\n'
    if not is_tracked:patch+='new file mode 100644\n'
    patch+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+path if is_tracked else '/dev/null',tofile='b/'+path))
data=patch.encode()
(out/'native-source-publish.patch').write_bytes(data)
meta=dict(branch=git('branch','--show-current').strip(),base_sha=git('rev-parse','HEAD').strip(),status='REVIEW_ONLY_NOT_STAGED_OR_COMMITTED',patch_sha256=hashlib.sha256(data).hexdigest(),files=inventory)
(out/'source-inventory.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(patch=str(out/'native-source-publish.patch'),sha256=meta['patch_sha256'],files=len(inventory))))
