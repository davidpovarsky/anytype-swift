#!/usr/bin/env python3
"""Run source-bound canonical archive and integration contracts on the package's own cache."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,subprocess,sys
sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace")
ROOT=Path(__file__).resolve().parents[2]
def manifest():
    result={}
    for module in ("PinkhaAnyEngine","PinkhaAnyIntegration","PinkhaKit"):
        base=ROOT/"Modules"/module
        files=list((base/"Sources").rglob("*.swift"))+[base/"Package.swift"]
        if (base/"Package.resolved").exists(): files.append(base/"Package.resolved")
        if module=="PinkhaAnyIntegration": files+=list((base/"Tests").rglob("*.swift"))
        for path in sorted(files):
            result[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--swift",default="swift")
    args=ap.parse_args()
    before=manifest()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    evidence=ROOT/"docs/any-engine-port/evidence/20261119"
    evidence.mkdir(parents=True,exist_ok=True)
    logfile=evidence/f"canonical-archive-integration-{stamp}.log"
    command=[args.swift,"test","--jobs","2"]
    env=dict(os.environ)
    if Path(args.swift).is_absolute(): env["PATH"]=str(Path(args.swift).parent)+os.pathsep+env.get("PATH","")
    failure=None
    with logfile.open("w",encoding="utf-8") as output:
        try:
            result=subprocess.run(command,cwd=ROOT/"Modules/PinkhaAnyIntegration",env=env,
                                  stdout=output,stderr=subprocess.STDOUT,text=True,timeout=900)
            exitcode=result.returncode
        except Exception as error:
            exitcode=-1
            failure=type(error).__name__+": "+str(error)
    after=manifest()
    log=logfile.read_text(encoding="utf-8",errors="replace")
    counts=re.findall(r"Test run with (\d+) tests?(?: in \d+ suites)? passed",log)
    count=int(counts[-1]) if counts else 0
    required=["Actual PinkhaKit domain on the Any operation bridge","Canonical native archive transport",
        "opaquePayloadBytesAndUnknownNumbersRoundTripWithoutLocalFields",
        "explicitMappingPreservesEachEnvelopeAndOriginalArchiveForAudit",
        "removedHistoryIsArchivedWithoutResurrectingItsAssociation",
        "foreignCollisionRemainsAuditableButCannotBeImportedAsSuccess",
        "missingObservedHistoryCannotProduceACompleteImportPlan",
        "unreachableBlockHistoryIsPreservedAndRequiresExplicitResolution",
        "unknownEnvelopeFieldsAndDuplicateKeysAreRejectedWithoutDroppingBytes",
        "duplicateLiveAssociationIdentityAcrossPayloadsFailsBeforeAnyWrites",
        "wholeImportPreflightAndRetryDoNotDuplicateAcceptedClaims",
        "scopedReadDoesNotExportLateDataAfterOwnerRevocation",
        "reviewExposesExactBlockAndInternalNoteMappings",
        "contradictoryInternalNoteMetadataIsNeverSuggestedAsAValidMapping",
        "payloadLocationCannotDisagreeWithItsArchivedOperation"]
    found=all(name in log for name in required)
    skipped=bool(re.search(r"(?:Test .*skipped|with \d+ tests? skipped)",log))
    passed=exitcode==0 and before==after and count==107 and found and not skipped
    receipt={"schemaVersion":1,"status":"PASS" if passed else "FAIL",
        "exitCode":exitcode,"expectedTests":107,"passedTests":count,"failure":failure,
        "requiredSuitesAndTestsPresent":found,"skipsDetected":skipped,
        "sourceStable":before==after,"sourceManifest":before,
        "command":command,"cwd":"Modules/PinkhaAnyIntegration",
        "log":logfile.relative_to(ROOT).as_posix(),
        "logSHA256":hashlib.sha256(logfile.read_bytes()).hexdigest(),
        "scope":"Portable complete integration suite, including 13 canonical archive transport and 6 native document policy tests. No Apple UI, native HTTP archive roundtrip or full Heart database migration claim."}
    receiptfile=logfile.with_suffix(".json")
    receiptfile.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k!="sourceManifest"},indent=2))
    if not passed:print("\n".join(log.splitlines()[-90:]))
    return 0 if passed else 1
if __name__=="__main__":sys.exit(main())
