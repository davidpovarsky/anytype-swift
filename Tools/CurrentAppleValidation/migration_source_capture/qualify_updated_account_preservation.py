from pathlib import Path
import hashlib,json,sqlite3,sys,subprocess,os,base64
sys.path.insert(0,"/Users/m1/builds/pinkha-c-heart-source-ui-20261125/control-current5ffff")
import retain_owned_heart_account as r
base=Path("/Users/m1/builds/pinkha-c-heart-source-ui-20261125")
root=base/"observed-update-preservation3";root.mkdir(mode=0o700);os.umask(0o077)
orig=Path("/Users/m1/builds/e-combined-current-20261125/sources-current5c05-continuation1/private/owned-account-originals")
cur=base/"current9d-observer-attempt1/private/owned-account-originals"
integrity=base/"observed-update-preservation1/sqlite-readonly-backup-integrity-failure.json"
assert hashlib.sha256(integrity.read_bytes()).hexdigest()=="85e7710d595696c54bf1bbf6d96f39502222819f9d55942c05641dd302aa8189"
damage=json.loads(integrity.read_bytes());sourcep={}
for label,p in [("original",orig),("current",cur)]:
 expected=json.loads((p/"keychains-before.json").read_bytes());actual=r.inventory(p/"keychains")
 changed={k for k in expected if actual.get(k)!=expected[k]}
 assert set(actual)==set(expected) and changed=={"keychain-2-debug.db-shm"},label+" source delta"
 assert actual["keychain-2-debug.db-shm"]==damage[label]["differences"]["changed"]["keychain-2-debug.db-shm"]["after"],label+" recorded SHM delta"
 assert all(actual[n]==expected[n] for n in ["keychain-2-debug.db","keychain-2-debug.db-wal"]),label+" DB WAL unchanged"
 cp=root/(label+"-keychains");subprocess.run(["cp","-cRp",str(p/"keychains"),str(cp)],check=True)
 assert r.inventory(cp)==actual,label+" private copy equality"
 def normal(x):return {"bytes":len(x),"base64":base64.b64encode(x).decode()} if isinstance(x,bytes) else x
 con=sqlite3.connect("file:"+str(cp/"keychain-2-debug.db")+"?mode=ro",uri=True);tables={}
 for table in ["genp","inet","cert","keys"]:
  cols=[x[1] for x in con.execute("PRAGMA table_info("+table+")")]
  rows=list(con.execute("SELECT * FROM "+table+" WHERE agrp=? ORDER BY rowid",("J3NXTX3T5S.io.anytype.app",)))
  raw=json.dumps({"columns":cols,"rows":[[normal(v) for v in row] for row in rows]},sort_keys=True,separators=(",",":")).encode()
  tables[table]={"count":len(rows),"schemaSHA256":hashlib.sha256(json.dumps(cols).encode()).hexdigest(),"allColumnRowsSHA256":hashlib.sha256(raw).hexdigest()}
 con.close();sourcep[label]=tables
 assert r.inventory(p/"keychains")==actual,label+" original source unchanged after copied SQL"
owned="74E63AAC-1CE6-44C1-8FE7-E39946D45D5A"
g0=r.inventory(orig/"shared-app-groups"/owned);g1=r.inventory(cur/"shared-app-groups"/owned);assert g0==g1,"actual app group equality"
assert sourcep["original"]==sourcep["current"] and sourcep["current"]["genp"]["count"]==1,"logical app keychain equality"
a=json.loads((orig/"application-data-before.json").read_bytes());b=json.loads((cur/"application-data-before.json").read_bytes())
removed=sorted(set(a)-set(b));assert len(removed)==9 and set(b)<=set(a) and all(b[k]==a[k] for k in b),"persistent app data equality"
assert all(x.startswith("Library/SplashBoard/Snapshots/io.anytype.app - {DEFAULT GROUP}/") and x.endswith(".ktx") for x in removed)
proof={"protocol":"pinkha-observed-app-update-preservation-v1","status":"PASS_EXACT_PERSISTENT_APP_DATA_NOT_UI_ACCEPTANCE",
"originalBackupSHA256":hashlib.sha256((orig/"retention.json").read_bytes()).hexdigest(),
"currentBackupSHA256":hashlib.sha256((cur/"retention.json").read_bytes()).hexdigest(),
"historicalBackupSHMChangedByEarlierReadOnlySQLite":True,"observedSHMMutationReceiptSHA256":hashlib.sha256(integrity.read_bytes()).hexdigest(),
"originalDBAndWALHashesUnchanged":True,"allLaterSQLiteQueriesUseNewPrivateCopies":True,
"originalAppEntries":len(a),"preservedAppEntries":len(b),"removedOriginalOSSnapshotPaths":removed,
"addedAppEntries":0,"changedAppEntries":0,"ownedGroupIdentifier":"group.io.anytype.app.dev",
"ownedGroupEntries":len(g0),"ownedGroupByteModeEquality":True,"appKeychain":sourcep["current"],
"exactLogicalAppKeychainEquality":True,"sourceAdmissionPromoted":False}
p=root/"receipt.json";p.write_text(json.dumps(proof,sort_keys=True,indent=2)+"\n")
print(json.dumps({"preservationReceipt":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"value":proof}),flush=True)
prior=base/"current9d-observer-attempt1";new=base/"current9d-observer-update-custody1";new.mkdir(mode=0o700)
for rel in ["evidence/execution.json","commands/final-private-sandbox-container/result.json","commands/final-private-sandbox-container/original.log"]:
 q=new/rel;q.parent.mkdir(parents=True,exist_ok=True,mode=0o700);q.write_bytes((prior/rel).read_bytes())
(new/"private").mkdir(mode=0o700)
subprocess.run(["cp","-cRp",str(prior/"private/final-sandbox-originals"),str(new/"private/final-sandbox-originals")],check=True)
execution="650eface152f478724e3d3930226ddc6868febebfbb0ad74e3f87a03106b08f0"
assert hashlib.sha256((new/"evidence/execution.json").read_bytes()).hexdigest()==execution
backup=r.retain(new,execution)
for label in ["application-data","shared-app-groups","keychains","device-preferences"]:
 assert json.loads((new/"private/owned-account-originals"/(label+"-before.json")).read_bytes())==json.loads((cur/(label+"-before.json")).read_bytes()),label+" live remains exact original post-install seal"
receipt={"protocol":"pinkha-post-diagnostic-fresh-live-custody-v1","status":"PASS_FRESH_CURRENT_LIVE_CUSTODY_NOT_ACCEPTANCE",
"originalExecutionRoot":str(prior),"originalExecutionSHA256":execution,
"historicalKeychainSHMDiagnosticMutationReceiptSHA256":hashlib.sha256(integrity.read_bytes()).hexdigest(),
"liveFourScopesEqualOriginalRecorded57feManifest":True,"privateAccount":backup,
"retentionSHA256":hashlib.sha256((new/"private/owned-account-originals/retention.json").read_bytes()).hexdigest(),
"devicePlistSHA256":hashlib.sha256((new/"private/owned-account-originals/device.plist").read_bytes()).hexdigest(),
"persistentAppDataProofSHA256":hashlib.sha256(p.read_bytes()).hexdigest()}
q=new/"evidence/custody-completion.json";q.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print(json.dumps({"freshCustody":str(new),"receiptSHA256":hashlib.sha256(q.read_bytes()).hexdigest(),"retentionSHA256":receipt["retentionSHA256"],"plistSHA256":receipt["devicePlistSHA256"]}))
