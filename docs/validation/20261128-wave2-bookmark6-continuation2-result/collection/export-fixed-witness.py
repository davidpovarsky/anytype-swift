import os,stat,hashlib,json,sys,base64
p='/mnt/development/projects/evidence/pinkha-wave2-bookmark6-continuation2-result-20261128/original-continuation2/immutable-witness-final.json'
off=int(sys.argv[1]);assert off in (0,48000,96000,144000,192000)
def ident(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
a=os.lstat(p);assert stat.S_ISREG(a.st_mode)
fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
try:
 assert ident(a)==ident(os.fstat(fd)); b=b''
 while True:
  q=os.read(fd,65536)
  if not q:break
  b+=q;assert len(b)<=165571
 assert ident(a)==ident(os.fstat(fd))==ident(os.lstat(p))
finally:os.close(fd)
assert len(b)==165571 and hashlib.sha256(b).hexdigest()=='0aa487dbec19529488c52f0e5de31e8006e88cc3e1a680feff310ac5032405a2'
assert hashlib.sha1(b'blob 165571\0'+b).hexdigest()=='0b850d62f84467226aa66c7e5247afa7423d7833'
s=base64.b64encode(b).decode();part=s[off:off+48000]
print(json.dumps({'status':'PASS_EXACT_FIXED_WITNESS_EXPORT','bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'base64Characters':len(s),'offset':off,'chunkCharacters':len(part),'data':part,'children':0,'writes':0,'processQueries':0,'signals':0,'atimePreservationClaim':False},separators=(',',':')))
