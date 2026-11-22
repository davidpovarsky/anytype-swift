import pathlib,hashlib,json,os,datetime,runpy
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-final-20261122")
assert hashlib.sha256((out/"INPUTS.json").read_bytes()).hexdigest()=="ef6b5d2758ad78da46e6c152f16d41f050ff478832b41e0cb4db618ed53b0f69"
assert hashlib.sha256((out/"run_controls.py").read_bytes()).hexdigest()=="fa38adc2e3a99268b83341070812a1bc5bf21ed3f0c17a87084b28010c78747d"
review=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\selected-space-final-controls-review\ROOT_REVIEW.json")
assert hashlib.sha256(review.read_bytes()).hexdigest()=="86fe254ec7f4aac95b54c40e1a9df61f8a0e29f2a1947366248faad2d4fe2e97"
assert not (out/"ACTUAL_STARTED.json").exists() and not (out/"EXECUTION.json").exists()
(out/"ACTUAL_STARTED.json").write_bytes((json.dumps({"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"launcher_pid":os.getpid(),"input_sha256":"ef6b5d2758ad78da46e6c152f16d41f050ff478832b41e0cb4db618ed53b0f69","runner_sha256":"fa38adc2e3a99268b83341070812a1bc5bf21ed3f0c17a87084b28010c78747d","root_review_sha256":"86fe254ec7f4aac95b54c40e1a9df61f8a0e29f2a1947366248faad2d4fe2e97","outer_timeout_seconds":1500,"prior_tests_replayed":False},indent=2)+"\n").encode())
(out/"launch_once.py").write_bytes(pathlib.Path(__file__).read_bytes())
runpy.run_path(str(out/"run_controls.py"),run_name="__main__")