import json,os,stat
from pathlib import Path
paths=["/mnt/development/projects/evidence","/mnt/development/projects/evidence/pinkha-w1-semantic131-attempt1-20261128"]
rows=[]
for name in paths:
 p=Path(name); s=p.lstat()
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
 try:
  f=os.fstat(fd)
  rows.append({"path":name,"mode":oct(stat.S_IMODE(s.st_mode)),"uid":s.st_uid,"gid":s.st_gid,"dev":s.st_dev,"ino":s.st_ino,"euid":os.geteuid(),"physical":p.resolve()==p,"descriptorMatches":(f.st_dev,f.st_ino,f.st_mode,f.st_uid,f.st_gid)==(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid)})
 finally: os.close(fd)
print(json.dumps({"schema":"pinkha-custody-directory-mode-failure-observation-v1","rows":rows,"changes":0,"children":0},sort_keys=True))
