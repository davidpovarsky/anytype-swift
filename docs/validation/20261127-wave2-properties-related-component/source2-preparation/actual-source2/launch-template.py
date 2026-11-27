import argparse,hashlib,json,pathlib,subprocess
parser=argparse.ArgumentParser()
parser.add_argument('--coordination-story',required=True)
args=parser.parse_args()
assert args.coordination_story.isdecimal() and len(args.coordination_story)==16
root=pathlib.Path('/var/lib/pinkha-wave2-properties-related-lifetime-source2-20261127')
runner=root/'inputs/run_component.py'
assert not runner.is_symlink()
assert hashlib.sha256(runner.read_bytes()).hexdigest()=='1e4bf0b6fe7ad5bc0005513aaad0d2b7429dde623592355f4f774420184f54f5'
assert not (root/'attempt1').exists(), 'Never rerun an existing attempt'
argv=['/usr/sbin/runuser','-u','ubuntu','-g','chatgpt-agent','--','/usr/bin/python3',str(runner),'--attempt','attempt1','--coordination-story',args.coordination_story]
r=subprocess.run(argv,capture_output=True,text=True,timeout=340)
print(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}),flush=True)
raise SystemExit(r.returncode)

