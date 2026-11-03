"""Capture real portable checks; Apple SDK and native engine checks are separate."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--evidence', required=True, type=Path)
parser.add_argument('--swift', action='store_true')
parser.add_argument('--only', choices=['go-unit','go-vet','go-fuzz','swift-focused'])
args=parser.parse_args()
module=Path(__file__).resolve().parent
root=module.parent.parent
args.evidence.mkdir(parents=True, exist_ok=True)
checks=[('go-unit', ['go','test','-count=1','-json','./...'],module),('go-vet',['go','vet','./...'],module),('go-fuzz',['go','test','-run=^$','-fuzz=FuzzProjectNeverMutatesOrReturnsPartialOnError','-fuzztime=20s','-parallel=2'],module)]
if args.swift or args.only=='swift-focused':
    checks.append(('swift-focused',['swift','test','--package-path','Modules/PinkhaKit','--jobs','2','--filter','Torah.*(DerivedQueryProjection|DocumentPropertyProjection|Canonical|Identity|Payload)'],root))
if args.only:
    checks=[check for check in checks if check[0]==args.only]
results=[]
for name,command,cwd in checks:
    with (args.evidence/(name+'.log')).open('w',encoding='utf-8') as stream:
        result=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,GOMAXPROCS='2'))
    results.append(dict(name=name,command=command,exit_code=result.returncode,status='PASS' if result.returncode==0 else 'FAIL'))
    print(json.dumps(results[-1]),flush=True)
    # A failed check remains visible and does not authorize bypassing its gate.
metadata=args.evidence/'portable-checks.json'
if args.only and metadata.exists():
    previous=json.loads(metadata.read_text(encoding='utf-8'))
    results=[result for result in previous if result['name']!=args.only]+results
metadata.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
raise SystemExit(int(any(result['exit_code']!=0 for result in results)))
