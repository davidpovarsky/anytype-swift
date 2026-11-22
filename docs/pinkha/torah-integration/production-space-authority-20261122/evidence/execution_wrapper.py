import pathlib,subprocess,sys,hashlib,json,time
root=pathlib.Path.cwd();packet=root/'docs/pinkha/torah-integration/production-space-authority-20261122/controls';runner=packet/'run_controls.py';manifest=packet/'INPUTS.json'
assert hashlib.sha256(runner.read_bytes()).hexdigest()=='2233778a816eccf62b3b598d832d55ad413f11021e247e66c727cd0b66e712b3'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='ec5f6d491381c3835ccb4e4913ae14ae1cc8d253d238c8149f3819b9db3e38b8'
result=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-spaceview-authority-controls-20261122')
assert not result.exists(), 'Refusing duplicate execution'
command=[sys.executable,str(runner),'--result-directory',str(result)]
print(json.dumps({'command':command,'wrapper_pid':__import__('os').getpid(),'status':'STARTING_FIRST_EXECUTION'}),flush=True)
p=subprocess.run(command,cwd=root,timeout=540)
print(json.dumps({'returncode':p.returncode,'result_directory':str(result)}),flush=True)
raise SystemExit(p.returncode)
