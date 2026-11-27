#!/usr/bin/env python3
"""Read-only qualification of failed Host2 attempt1; no compiler, process probe, or retry."""
from pathlib import Path
import os,sys,json,hashlib,stat,runpy,time,shutil,traceback
sys.dont_write_bytecode=True
root=Path('/mnt/development/projects/evidence/pinkha-wave2-host-text-readback-20261127')
expected='2287f91526496a1fa4b5fc749fb83b9a6b20d2a19196cb0c1e1e9fbc68b2e05f'
started=time.monotonic()
def sha(b):return hashlib.sha256(b).hexdigest()
receipt_path=root/'attempt1/receipt.json'
raw=receipt_path.read_bytes()
assert len(raw)==6470 and sha(raw)==expected
old=json.loads(raw)
assert old['status']=='FAIL' and old['safeToReleaseRuntimeSlot'] is False
assert old['ownedCleanup']['status']=='PASS_OWNED_GROUP_ABSENT'
assert old['ownedCleanup']['absenceEvidence']['status']=='ABSENT_ESRCH'
assert old['ownedCleanup']['processGroup']==1405860 and old['ownedCleanup']['errors']==[]
assert old['processExit']==-15 and old['retainedFixtureFiles']==[]
assert old['nativeCalls']==0 and old['AppleCalls']==0
assert (root/'attempt1/stdout.original.log').read_bytes()==b''
assert (root/'attempt1/stderr.original.log').read_bytes()==b''
sys.path.insert(0,str(root/'inputs'))
driver=root/'inputs/run_component.py'
assert sha(driver.read_bytes())=='cb85418882d403318e786dae2564bbd2c4a2313be622a39139b84fb67090dce0'
ns=runpy.run_path(str(driver),run_name='host2_read_only_retention')
before=json.loads((root/'attempt1/source-inputs-before.json').read_bytes())
final=json.loads((root/'attempt1/source-inputs-final.json').read_bytes())
assert ns['source_inventory'](root/'inputs/component')==before==ns['source_inventory'](root/'component')
assert final=={'inputs':before,'compiledCopy':before}
ns['cleanup_custody']()
ns['pinned'](root/'inputs/whole-source-closure.json',ns['SOURCE_CLOSURE_SHA'])
ns['pinned'](root/'inputs/retained-crypto-closure.json',ns['CRYPTO_SHA'])
copies_raw=(root/'attempt1/actual-dependency-copies.json').read_bytes()
assert len(copies_raw)==81909 and sha(copies_raw)=='e4c11a159f322634c3c32c7555f71d4a9b420e4eb7841e6154f77b907e65602c'
copies=json.loads(copies_raw);assert len(copies)==102
ns['verify_crypto'](copies)
assert root.resolve(strict=True)==root and stat.S_IMODE(root.stat().st_mode)==0o700
alias=root/'xdg-config/swiftpm/cache';target=root/'xdg-cache/org.swift.swiftpm'
assert alias.is_symlink() and os.readlink(alias)==str(target)
assert target.resolve(strict=True)==target and target.is_dir() and not target.is_symlink()
total=root.lstat().st_blocks*512;links=[];file_count=0
for base,dirs,files in os.walk(root,followlinks=False):
 for name in dirs+files:
  p=Path(base)/name;s=p.lstat();total+=s.st_blocks*512
  if stat.S_ISLNK(s.st_mode):
   assert p==alias and os.readlink(p)==str(target) and p.resolve(strict=True)==target,str(p)
   links.append({'path':str(p),'target':str(target),'inode':s.st_ino,'allocatedBytes':s.st_blocks*512})
  elif stat.S_ISREG(s.st_mode):file_count+=1
  else:assert stat.S_ISDIR(s.st_mode),str(p)
assert len(links)==1
memory={line.split(':',1)[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapFree:'))}
sample={'atUTC':ns['owned_process'].now(),'rootFreeBytes':shutil.disk_usage('/').free,'developmentFreeBytes':shutil.disk_usage(root).free,'ownedAllocatedBytes':total,'memAvailableBytes':memory['MemAvailable'],'swapFreeBytes':memory['SwapFree']}
ns['require_budget'](sample)
assert receipt_path.read_bytes()==raw
assert time.monotonic()-started<30
result={'schema':'host2-failed-attempt1-read-only-retention/v1','status':'PASS_FAILED_ATTEMPT_RETENTION_AND_SLOT_RELEASE','originalReceipt':str(receipt_path),'originalReceiptSHA256':expected,'originalStatus':'FAIL','originalSafeToReleaseRuntimeSlot':False,'priorOwnedGroupAbsenceReused':old['ownedCleanup']['absenceEvidence'],'historicalGroupProbes':0,'children':0,'compilerCommands':0,'testsExecuted':0,'fixturesStarted':0,'sourceInventoriesUnchanged':True,'all102CryptoOriginalsAliasesAndCopiesUnchanged':True,'exactActualPrivateSymlink':links,'censusRegularFiles':file_count,'resourceSample':sample,'budget':old['budget'],'safeToReleaseRuntimeSlot':True,'seconds':round(time.monotonic()-started,3),'noProductAcceptanceClaim':True,'errors':[]}
print(json.dumps(result,sort_keys=True))

