import pathlib,json,subprocess,hashlib,os,time,signal,shutil
r=pathlib.Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
e=pathlib.Path("/mnt/development/projects/evidence/migration-final-20261125/torah-semantic-migration/controls-attempt2")
e.mkdir(mode=0o700,parents=True,exist_ok=False)
paths=["Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahMigration.swift","Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahSemanticAnchorMigration.swift","Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahSemanticTargetAccess.swift","Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift","Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyDestinationAnchoredText.swift","Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeTorahMigrationTargetAccess.swift","Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativeTorahSemanticMigrationTests.swift","Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativeSemanticAnchorMigrationTests.swift","Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyDestinationNativeTorahSemanticTests.swift"]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p:sha(r/p) for p in paths};(e/"source-before.json").write_text(json.dumps(before,indent=2)+"\n")
free=shutil.disk_usage("/tmp").free
assert free>128*1024**2+256*1024**2,"insufficient measured warmed Swift control headroom"
env=os.environ.copy();env.update(TMPDIR="/tmp/pinkha-c-swift-control-20261125",
 PINKHA_NATIVE_SOURCE_FIXTURE="/mnt/development/projects/evidence/native-json-source-fixture-45472745870",
 PINKHA_NATIVE_CUSTOM_SOURCE_FIXTURE="/mnt/development/projects/evidence/native-custom-source-fixture-45492064232",
 PINKHA_NATIVE_COMPILED_CAPTURE_FIXTURE="/mnt/development/projects/evidence/migration-final-20261125/compiled-definitions/private-native-compiled-capture-5e8f")
command=["/usr/local/bin/swift","test","--package-path",str(r/"Modules/PinkhaAnyHost"),"--scratch-path","/tmp/pinkha-c-swift-cache-20261125","--skip-update","--jobs","2","--filter","NativeTorahSemanticMigrationTests|NativeSemanticAnchorMigrationTests"]
(e/"command.json").write_text(json.dumps(command)+"\n")
started=time.monotonic();minimum=free;stopped=False
with (e/"original.log").open("wb") as log:
 p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  minimum=min(minimum,shutil.disk_usage("/tmp").free)
  if minimum<256*1024**2 or time.monotonic()-started>500:
   os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=20);stopped=True;break
  time.sleep(1)
 code=p.returncode
after={p:sha(r/p) for p in paths};(e/"source-after.json").write_text(json.dumps(after,indent=2)+"\n")
result={"returncode":code,"controllerStopped":stopped,"sourceUnchanged":before==after,"seconds":round(time.monotonic()-started,3),"logSHA256":sha(e/"original.log"),"minimumTemporaryFreeBytes":minimum,"warmIncrementalEstimateBytes":128*1024**2,"emergencyFreeBytes":256*1024**2}
(e/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result));print("\n".join((e/"original.log").read_text(errors="replace").splitlines()[-18:]))
raise SystemExit(0 if code==0 and before==after and not stopped else 1)
