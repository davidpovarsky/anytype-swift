"""Produce a delta against already-approved Heart source; no source writes."""
from pathlib import Path
import argparse, difflib, hashlib, json, re, subprocess

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--heart-source',type=Path,required=True)
parser.add_argument('--full-patch',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
pin='d98420b1113536afd08cde6de9a5816f6d27ffff'
patch=args.full_patch.read_text(encoding='utf8').splitlines(keepends=True)
sections=[]
for line in patch:
    if line.startswith('diff --git '): sections.append([line])
    else: sections[-1].append(line)
result='';inventory=[]
for section in sections:
    path=section[0].strip().split(' b/',1)[1]
    if 'new file mode 100644\n' in section: baseline=[]
    else:
        baseline=subprocess.check_output(['git','-C',str(args.heart_source),'show',pin+':'+path]).decode('utf8').splitlines(keepends=True)
    rendered=[];offset=0;n=0
    while n<len(section):
        line=section[n]
        match=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',line)
        if not match:n+=1;continue
        start=max(0,int(match[1])-1)
        rendered.extend(baseline[offset:start]);offset=start;n+=1
        while n<len(section) and not section[n].startswith('@@ '):
            line=section[n]
            if line.startswith(' '):
                assert baseline[offset]==line[1:];rendered.append(line[1:]);offset+=1
            elif line.startswith('-'):
                assert baseline[offset]==line[1:];offset+=1
            elif line.startswith('+'):rendered.append(line[1:])
            n+=1
    rendered.extend(baseline[offset:])
    final=''.join(rendered)
    actual=(args.heart_source/path).read_text(encoding='utf8')
    if final==actual:continue
    result+='diff --git a/'+path+' b/'+path+'\n'
    result+=''.join(difflib.unified_diff(actual.splitlines(keepends=True),final.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
    inventory.append(dict(path=path,before_sha256=hashlib.sha256(actual.encode()).hexdigest(),after_sha256=hashlib.sha256(final.encode()).hexdigest()))
args.output.mkdir(parents=True,exist_ok=True)
data=result.encode()
(args.output/'native-heart-followup.patch').write_bytes(data)
(args.output/'native-heart-followup.json').write_text(json.dumps(dict(heart_sha=pin,patch_sha256=hashlib.sha256(data).hexdigest(),status='PENDING_EXACT_OWNER_APPROVAL_NOT_APPLIED',files=inventory),indent=2)+'\n')
print(json.dumps(dict(patch=str(args.output/'native-heart-followup.patch'),sha256=hashlib.sha256(data).hexdigest(),files=len(inventory))))
