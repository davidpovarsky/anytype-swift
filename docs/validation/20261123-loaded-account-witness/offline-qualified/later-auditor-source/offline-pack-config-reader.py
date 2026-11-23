import pathlib,hashlib,json,subprocess,gzip,stat,os
P=pathlib.Path("/mnt/development/projects/git-mirrors/anytype-swift.git/objects/pack/pack-d4a3bc7cad22923baea8797453958b68ed82ed1a.pack")
C=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
st=P.lstat();assert stat.S_ISREG(st.st_mode) and not P.is_symlink()
metadata={k:str(getattr(st,k)) for k in ("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns","st_blocks")}
version=subprocess.run(["git","--version"],capture_output=True,timeout=10)
settings=[]
for name in ("core.packedGitWindowSize","core.packedGitLimit","core.deltaBaseCacheLimit"):
 r=subprocess.run(["git","-C",str(C),"config","--show-origin","--get-all",name],capture_output=True,timeout=10)
 settings.append({"key":name,"returncode":r.returncode,"stdout":r.stdout.decode(),"stderr":r.stderr.decode()})
docs=[]
for p in (pathlib.Path("/usr/share/man/man1/git-config.1.gz"),pathlib.Path("/usr/share/man/man5/git-config.5.gz")):
 if not p.is_file():continue
 raw=p.read_bytes();text=gzip.decompress(raw).decode();lines=text.splitlines();sections=[]
 for key in ("packedGitWindowSize","packedGitLimit","deltaBaseCacheLimit"):
  hits=[i for i,l in enumerate(lines) if key in l]
  for i in hits[:3]:sections.append({"key":key,"line":i+1,"text":"\n".join(lines[max(0,i-1):i+32])})
 docs.append({"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"sections":sections})
print(json.dumps({"read_only":True,"pack_path":str(P),"pack_metadata":metadata,"pack_payload_read":False,"git_version":{"returncode":version.returncode,"stdout":version.stdout.decode(),"stderr":version.stderr.decode()},"configured_values":settings,"installed_documentation":docs,"vm_max_map_count":pathlib.Path("/proc/sys/vm/max_map_count").read_text().strip(),"no_git_status_or_graph_execution":True},sort_keys=True))
