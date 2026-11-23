import pathlib,hashlib,json,gzip,shutil,subprocess,os
git=pathlib.Path(shutil.which("git"));raw=git.read_bytes();st=git.lstat()
B=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-offline-completion1/current-source-before.json.gz")
b=B.read_bytes();assert hashlib.sha256(b).hexdigest()=="2a5d9b30dbde12e7dc8e489b7935a005d21ac316840f3374ba706a653a32cd7b"
v=json.loads(gzip.decompress(b))
p=subprocess.run(["dpkg-query","-W","-f",chr(36)+"{Package} "+chr(36)+"{Version}\n","git"],capture_output=True,timeout=10)
print(json.dumps({"git":{"path":str(git),"resolved":str(git.resolve()),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"metadata":{k:str(getattr(st,k)) for k in ("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")}},"installed_package":{"returncode":p.returncode,"stdout":p.stdout.decode(),"stderr":p.stderr.decode()},"current_source_before":{"controller_commit":v["controller_commit"],"records":len(v["records"]),"record_names":list(v["records"]),"actual_loaded_python":v["actual_loaded_python"],"compressed_sha256":hashlib.sha256(b).hexdigest()},"fixed_ancillary_total_read_budget":16777216,"no_state_audit_run":True},sort_keys=True))
