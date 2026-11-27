import argparse,hashlib,json,pathlib,subprocess
parser=argparse.ArgumentParser()
parser.add_argument('--coordination-story',required=True)
args=parser.parse_args()
assert args.coordination_story.isdecimal() and len(args.coordination_story)==16
root=pathlib.Path('/var/lib/pinkha-wave2-properties-related-lifetime-20261127')
runner=root/'inputs/run_component.py'
assert not runner.is_symlink()
assert hashlib.sha256(runner.read_bytes()).hexdigest()=='f0c459b34a20fdce78f4cbdf07988ac9c4976ba2cbce4daeb316a0dd7d88d42c'
assert not (root/'attempt1').exists(), 'Never rerun an existing attempt'
argv=['/usr/sbin/runuser','-u','ubuntu','-g','chatgpt-agent','--','/usr/bin/python3',str(runner),'--attempt','attempt1','--coordination-story',args.coordination_story]
r=subprocess.run(argv,capture_output=True,text=True,timeout=340)
print(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}),flush=True)
raise SystemExit(r.returncode)

