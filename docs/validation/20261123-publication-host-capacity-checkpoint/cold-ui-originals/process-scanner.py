import pathlib,os,json,sys
targets=json.loads(sys.argv[1]); exclude=set(json.loads(sys.argv[2])); exclude.add(os.getpid())
pp=os.getpid()
while pp>1:
 exclude.add(pp)
 try:pp=int(pathlib.Path('/proc/'+str(pp)+'/stat').read_text().rsplit(')',1)[1].split()[1])
 except (FileNotFoundError,ValueError):break
denied=[];hits=[];seen=0
for d in pathlib.Path('/proc').iterdir():
 if not d.name.isdigit() or int(d.name) in exclude: continue
 pid=int(d.name);seen+=1
 def record(kind,s):
  for t in targets:
   if t in s: hits.append({'pid':pid,'kind':kind,'path':t});break
 for kind in ('cwd','root'):
  try: record(kind,os.readlink(d/kind))
  except (FileNotFoundError,ProcessLookupError):pass
  except PermissionError:denied.append([pid,kind])
 for kind in ('cmdline','maps'):
  try: record(kind,(d/kind).read_bytes().decode(errors='replace'))
  except (FileNotFoundError,ProcessLookupError):pass
  except PermissionError:denied.append([pid,kind])
 try:
  for f in (d/'fd').iterdir():
   try:record('fd',os.readlink(f))
   except (FileNotFoundError,ProcessLookupError):pass
   except PermissionError:denied.append([pid,'fd'])
 except (FileNotFoundError,ProcessLookupError):pass
 except PermissionError:denied.append([pid,'fd-directory'])
print(json.dumps({'uid':os.geteuid(),'processes':seen,'hits':hits,'denied':denied}))
