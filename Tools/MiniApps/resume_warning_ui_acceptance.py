#!/usr/bin/env python3
"""Continue four original MiniApps methods after actual preparation and UI navigation failure.

The old failed run remains failed. The successful native preparation is independently
qualified and reused from its unchanged, sealed account; no source fixture is replayed.
Only the complete original UI runner has the reviewed ordinary Warning navigation.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import signal
import stat
import subprocess
import sys
import time
import traceback
import uuid

BASE=Path("/Users/m1/builds/pinkha-unified-miniapps-20261125")
PRIOR=BASE/"heart-five-attempt4"
UI=BASE/"warning-ui-a3e3-build1"
SEAL=Path("/Users/m1/builds/pinkha-c-heart-source-ui-20261125/d-miniapps-prepared-ui-account-seal1")
PRIOR_SHA="144b17e9892ec99056771a5ec9417f8bdc5d2101863ace71f99f0fc0c3b5ca47"
CONTROL_SHA="62574ac6c02151b22309dcf093f062ff21a670d88db31c472de27521f1a2fd8e"
SEAL_SHA="9816e5828b056636475776f215008c6c95db303d2f463ab9dd44d31a3de4f0bb"
SEAL_ADMISSION="f8c32aa8ff4dd6bab6cc64ae00d24b4c1cea7e324aef24fb6898834ce712b1cd"
RETAINER_SHA="7e5403af17d629341644729c420877c56a58b18bc7077d67ef9c573c994b8fd6"
UI_RECEIPT="516cb74c53e3c6e5e202cedc0fb7a15cf21133241e7b94f75c4a290ff0ddfb28"
UI_SOURCE="a3e3b21455e7ff517d34b0b16c897fed8845fc22"
SOURCE="6f1194f9b8c9540dea1187826dda6a256777dbbf"
CORE_SHA="7adb3118bbf584d6475f1bffc483c2055994ce50ac3031471226762df23dc501"
ADMISSION_SHA="82ede074604e6ac8e80f631dfd2d61e4f19fc54cd0a5a68c482fda6bc310e697"
BUNDLE="io.anytype.app"
DEVICE="026E9F43-C4AF-4087-B300-8870B82FAFA4"

def require(value,message):
    if not value: raise RuntimeError(message)
def sha(value):return hashlib.sha256(value).hexdigest()
def raw(path,bound=16*1024**2):
    path=Path(path);require(path.is_file() and not path.is_symlink() and path.stat().st_size<=bound,"bounded original regular input required")
    return path.read_bytes()
def pinned(path,digest):
    value=raw(path);require(sha(value)==digest,"original pinned bytes changed: "+str(path));return value
def write(path,value):
    with path.open("x") as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write("\n")
    path.chmod(0o600)
def module(path,name,digest):
    pinned(path,digest);sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value

def admit_ui(core,original_source,root,evidence,commands):
    receipt=json.loads(pinned(UI/"evidence/receipt.json",UI_RECEIPT))
    require(receipt["protocol"]=="pinkha-miniapps-original-warning-ui-producer-v1" and
            receipt["status"]=="PASS_COMPLETE_UI_BUILD_ONLY_NOT_ACCEPTANCE" and
            receipt["appSourceCommit"]==SOURCE and receipt["uiSourceCommit"]==UI_SOURCE and
            receipt["appBuilds"]==receipt["nativeBuilds"]==receipt["testsExecuted"]==0 and
            receipt["originalAppSourceUntouched"] is True and receipt["sourceFiles"]==12,
            "actual source-bound complete UI-only producer required")
    command=receipt["uiCommand"]
    require(command["status"]=="PASS_COMMAND" and command["exitCode"]==0 and
            command["ownedGroupPresentAfterExit"] is False and "build-for-testing" in command["argv"],
            "original successful complete UI build command required")
    log=UI/"commands/build-complete-ui/original.log"
    if not log.exists():
        matches=[p for p in (UI/"commands").glob("*/original.log") if core.digest(p)==command["logSHA256"]]
        require(len(matches)==1,"one original exact UI build log required");log=matches[0]
    require(core.digest(log)==command["logSHA256"] and b"** TEST BUILD SUCCEEDED **" in raw(log,16*1024**2),
            "original UI success marker required")
    proof=json.loads(pinned(UI/"evidence/source-proof.json",receipt["sourceProofSHA256"]))
    require(proof["appSourceCommit"]==SOURCE and proof["uiSourceCommit"]==UI_SOURCE and
            proof["tree"]=="9639d746210c17820d67152641baed79a9e49d0d" and
            proof["exactInverseRestoresOriginal"] is True and proof["originalAssertionsRemoved"]==0 and
            len(proof["files"])==12,"exact complete original UI source proof required")
    changed="PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift"
    require(proof["onlyChangedSource"]==changed,"only real warning navigation may differ")
    for name,binding in proof["files"].items():
        value=raw(UI/"ui-source"/name);before=raw(original_source/name)
        require(len(value)==binding["bytes"] and sha(value)==binding["sha256"] and
                sha(before)==binding["originalSHA256"] and
                hashlib.sha1(b"blob "+str(len(value)).encode()+b"\0"+value).hexdigest()==binding["gitBlob"],
                "compiled UI source Git/byte binding changed")
        if name!=changed:require(value==before,"another original UI file changed")
        else:
            require(sha(value)=="19728bf3a2fc56451ae3a3cbd2b9850847898ed4324e86518942f358147a36ec" and
                    sha(before)=="a91c52db975b108deddb7f0a71180083a1ee1c65aaaeef58a70ec181e99b6985",
                    "reviewed exact warning navigation required")
            start=value.index(b"        // A real qualified custom middleware may present the original safety\n")
            end=value.index(b"        let ready = source.descendants(matching: .any).matching(NSPredicate(\n",start)
            require(value[:start]+value[end:]==before,"all original assertions must remain byte-identical")
    generator=json.loads(pinned(UI/"evidence/generator.json",receipt["generatorSHA256"]))
    require(generator["originalFileSHA256"]=="7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0",
            "original full UI generator required")
    manifest=json.loads(pinned(UI/"evidence/products.json",receipt["productManifestSHA256"]))
    original=Path(receipt["productRoot"])
    require(original==UI/"derived/Build/Products" and core.inventory(original)==manifest,
            "original full UI products changed")
    destination=root/"warning-ui-products"
    commands.run(["cp","-cRp",str(original),str(destination)],"clone-warning-ui-products",120)
    require(core.inventory(destination)==manifest and core.inventory(original)==manifest,"complete UI clone differs")
    descriptor=destination/receipt["descriptorRelativePath"]
    require(descriptor.parent==destination and core.digest(descriptor)==receipt["descriptorSHA256"]==
            "05312fa8af79b5091b0343085dbc6b68df99e0b96ebd0624d75210d9446f0b5a","exact built original UI descriptor required")
    decoded=plistlib.loads(raw(descriptor));target=decoded["PinkhaStage1AcceptanceUITests"]
    require(target.get("OnlyTestIdentifiers",[])==[],"complete unselected original UI runner required")
    write(evidence/"warning-ui-admission.json",{"appSourceCommit":SOURCE,"uiSourceCommit":UI_SOURCE,
        "receiptSHA256":UI_RECEIPT,"sourceProofSHA256":receipt["sourceProofSHA256"],
        "completeUIProductManifestSHA256":receipt["productManifestSHA256"],"allOriginalAssertionsUnchanged":True})
    return {"products":destination,"inventory":manifest,"copies":{},"descriptor":descriptor,"originalSelection":[]}

def admit_prior(core,host,retainer,evidence):
    previous=json.loads(pinned(PRIOR/"evidence/execution.json",PRIOR_SHA))
    require(previous["protocol"]=="pinkha-unified-miniapps-original-five-v1" and previous["status"]=="FAIL" and
            previous["sourceCommit"]==SOURCE and previous["controllerSHA256"]==CONTROL_SHA and
            previous["coreSHA256"]==CORE_SHA and previous["admissionSHA256"]==ADMISSION_SHA and
            previous["ownedSimulator"]==DEVICE and previous["ownedSimulatorRetention"]=="Shutdown" and
            previous["ownedGroupsRemaining"]==[] and previous["errors"]==[] and previous["builds"]==0 and
            previous["testsExecuted"]==previous["testCommandsInvoked"]==2 and
            [x["status"] for x in previous["methods"]]==["PASS","FAIL"],"actual original prepare PASS/UI FAIL required")
    expected_counts=[{"totalTestCount":1,"passedTests":1,"failedTests":0,"skippedTests":0},
                     {"totalTestCount":1,"passedTests":0,"failedTests":1,"skippedTests":0}]
    for label,counts,exit_code in zip(("prepare","return-ui"),expected_counts,(0,65)):
        d=PRIOR/"evidence"/label;summary=json.loads(raw(d/"summary.json"));tree=json.loads(raw(d/"tests.json"))
        require({k:summary[k] for k in counts}==counts,"original actual method counts changed")
        command=json.loads(raw(PRIOR/"commands"/(label+"-test")/"result.json"))
        require((PRIOR/"commands"/(label+"-test")/"started.json").is_file() and
                command["exitCode"]==exit_code and command["ownedGroupPresentAfterExit"] is False and
                command==previous["methods"][0 if label=="prepare" else 1]["command"] and
                core.digest(PRIOR/"commands"/(label+"-test")/"original.log")==command["logSHA256"],
                "actual original method command custody changed")
        if label=="prepare":
            host.validate_results(summary,tree,{"PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument"},DEVICE)
            require(b"** TEST EXECUTE SUCCEEDED **" in raw(PRIOR/"commands/prepare-test/original.log"),"actual preparation success required")
    custody=json.loads(pinned(SEAL/"original-admission.json",SEAL_ADMISSION))
    sealed=SEAL/"private/owned-account-originals"
    receipt=json.loads(pinned(sealed/"retention.json",SEAL_SHA))
    require(custody["executionSHA256"]==receipt["executionSHA256"]==PRIOR_SHA and
            custody["device"]==receipt["device"]==DEVICE and
            receipt["status"]=="PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE" and
            receipt["extraEngineCalls"]==receipt["restoredFixtures"]==0 and
            receipt["fixtureDeadlineChanged"] is False and len(receipt["lifecycleChecks"])==6,
            "exact original four-scope seal required")
    device_root=Path.home()/"Library/Developer/CoreSimulator/Devices"/DEVICE
    app=Path(previous["privateAppContainer"])
    roots={"application-data":app,"shared-app-groups":device_root/"data/Containers/Shared/AppGroup",
           "keychains":device_root/"data/Library/Keychains","device-preferences":device_root/"data/Library/Preferences"}
    def identity(p):
        require(p.resolve()==p and not p.is_symlink(),"owned original root must be canonical")
        x=p.lstat();return (x.st_dev,x.st_ino,x.st_mode)
    require(app.parent==device_root/"data/Containers/Data/Application","original owned App container required")
    identities={label:identity(p) for label,p in roots.items()};identity_before=identity(device_root)
    plist=device_root/"device.plist";plist_identity=identity(plist)
    require(core.digest(plist)==custody["devicePlistSHA256"]==
            "b5f4d3507b5a4161f1fd898dcfd445986a61cfe532a3272977f80885e1491dd3" and
            raw(plist)==raw(sealed/"device.plist"),"same actual original device metadata required")
    def state():
        current=json.loads(subprocess.check_output(["xcrun","simctl","list","devices","--json"],timeout=30))
        rows=[dict(x,runtime=k) for k,v in current["devices"].items() for x in v if x.get("udid")==DEVICE]
        require(len(rows)==1,"same owned device required");row=rows[0];creation=custody["creation"]
        require(row["state"]=="Shutdown" and row["name"]==creation["name"] and row["runtime"]==creation["runtime"] and
                row["deviceTypeIdentifier"]==creation["deviceType"],"original device must remain Shutdown")
        return row
    live=state();manifests={}
    require(set(receipt["scopes"])==set(roots),"all four original scopes required")
    for label,p in roots.items():
        row=receipt["scopes"][label];require(row["status"]=="PRESERVED_ORIGINAL_BYTES_AND_MODES","sealed original scope required")
        manifest=json.loads(pinned(sealed/(label+"-before.json"),row["manifestSHA256"]))
        require(retainer.inventory(p)==manifest==retainer.inventory(sealed/label),"live and sealed original private bytes/modes differ")
        require(identity(p)==identities[label],"original private root replaced during admission")
        manifests[label]=row["manifestSHA256"]
    require(state()==live and identity(device_root)==identity_before and identity(plist)==plist_identity and
            core.digest(plist)==custody["devicePlistSHA256"] and
            all(identity(path)==identities[label] for label,path in roots.items()),
            "original device or any of its four private roots changed during admission")
    fixture=json.loads(raw(app/"Library/Application Support/miniapps-native-fixture.json"))
    require(fixture==json.loads(raw(PRIOR/"evidence/private-native-fixture.json")) and
            fixture["sourceSHA"]==SOURCE and fixture["runID"]==previous["localExecutionID"],
            "exact actual original native preparation fixture required")
    receipts=app/"Library/Application Support/MiniAppsReceipts"
    require(not receipts.exists() or not list(receipts.glob("*/*.json")),"no prior result application may be replayed")
    write(evidence/"prior-preparation-and-custody.json",{"originalExecutionSHA256":PRIOR_SHA,
        "originalPreparationCounts":expected_counts[0],"originalFailedUICounts":expected_counts[1],
        "originalFailureReclassified":False,"nativePreparationReplayed":False,"sealSHA256":SEAL_SHA,
        "sealAdmissionSHA256":SEAL_ADMISSION,"device":DEVICE,"devicePlistSHA256":custody["devicePlistSHA256"],
        "scopeManifests":manifests,"fixtureSHA256":core.digest(app/"Library/Application Support/miniapps-native-fixture.json"),
        "fixtureExpiryField":"none in the original preparation contract; no deadline was changed"})
    return previous,custody,app,fixture

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for label in ("root","core","admission","original-controller","retainer"):
        parser.add_argument("--"+label,type=Path,required=True)
    args=parser.parse_args()
    require(all(p.is_absolute() and p.resolve()==p for p in vars(args).values()),"canonical paths required")
    require(not args.root.exists() and args.root.parent==BASE,"fresh owned continuation root required")
    original=module(args.original_controller,"original_miniapps_failure_control",CONTROL_SHA)
    retainer=module(args.retainer,"reviewed_miniapps_private_custody",RETAINER_SHA)
    core=module(args.core,"original_miniapps_combined_product_control",CORE_SHA)
    admission=json.loads(pinned(args.admission,ADMISSION_SHA))
    require(admission["sourceCommit"]==SOURCE and not admission.get("menuPagingUIOverride"),"original App admission required")
    root=args.root;root.mkdir(mode=0o700);os.umask(0o022)
    evidence=root/"evidence";evidence.mkdir(mode=0o700)
    commands=original.command_custody_class(core)(root/"commands",root)
    outcome={"protocol":"pinkha-unified-miniapps-warning-continuation-v1","status":"FAIL",
        "controllerSHA256":sha(raw(Path(__file__).resolve())),"priorControllerSHA256":CONTROL_SHA,
        "coreSHA256":CORE_SHA,"admissionSHA256":ADMISSION_SHA,"sourceCommit":SOURCE,"uiSourceCommit":UI_SOURCE,
        "uiProducerReceiptSHA256":UI_RECEIPT,"priorExecutionSHA256":PRIOR_SHA,"priorAccountSealSHA256":SEAL_SHA,
        "companionSourceCommit":original.PRODUCER,"companionManifestSHA256":original.PRODUCER_MANIFEST,
        "builds":0,"nativePreparationReplays":0,"fixtureResets":0,"methods":[],"testsExecuted":0,
        "testCommandsInvoked":0,"errors":[],"physicalSharing":"NOT_PROVEN_BY_SIMULATOR"}
    udid=None;app_container=None;built=None;primary=None;old_ui=None
    def interrupted(number,_frame):raise RuntimeError("owned continuation interrupted by signal "+str(number))
    for number in (signal.SIGINT,signal.SIGTERM):signal.signal(number,interrupted)
    try:
        proof,built,app=core.admit_and_clone_products(admission,root,evidence,commands)
        write(evidence/"original-app-and-ui-admission.json",proof)
        source=Path(admission["sourceRoot"]);before=json.loads(core.pinned(admission["sourceBefore"]))
        for relative,binding in original.ORIGINAL_HELPERS.items():
            value=raw(source/relative);require(len(value)==binding["bytes"] and sha(value)==binding["sha256"],"original helper changed")
        sys.path[:0]=[str(root/"helpers/Tools/CurrentAppleValidation"),str(source/"Tools/MiniApps"),
                      str(source/"Tools/Hanlin"),str(source/"Tools/PinkhaNativeDerived")]
        core.common=importlib.import_module("contracts")
        selection=importlib.import_module("selection");host=importlib.import_module("run_host_tests")
        for value in (selection,host):
            path=Path(value.__file__).resolve();require(source in path.parents and
                core.digest(path)==original.ORIGINAL_HELPERS[str(path.relative_to(source))]["sha256"],"foreign validator refused")
        old_ui=built["ui"];built["ui"]=admit_ui(core,source,root,evidence,commands)
        local_producer=importlib.import_module("local_producer")
        helper=Path(local_producer.__file__).resolve()
        require(source in helper.parents and core.digest(helper)==original.ORIGINAL_HELPERS[
            str(helper.relative_to(source))]["sha256"],"foreign companion validator refused")
        manifest=PRIOR/"original-companion/producer-manifest.json"
        pinned(manifest,original.PRODUCER_MANIFEST)
        pin={"execution_origin":"local-mac","run_id":None,"revision":original.PRODUCER,
             "repository":"davidpovarsky/hanlin-ai","bundle_id":"com.itorah.hanlinminiapps",
             "local_manifest_path":str(manifest),"local_manifest_sha256":original.PRODUCER_MANIFEST}
        producer=local_producer.admit(source,root/"companion",evidence,pin)
        previous,custody,app_container,fixture=admit_prior(core,host,retainer,evidence)
        write(evidence/"private-native-fixture.json",fixture)
        udid=DEVICE;name=custody["creation"]["name"];run_id=previous["localExecutionID"]
        outcome.update(ownedSimulator=udid,localExecutionID=run_id)
        commands.run(["xcrun","simctl","boot",udid],"boot",120)
        commands.run(["xcrun","simctl","bootstatus",udid,"-b"],"bootstatus",180)
        environment={"PINKHA_SIMULATOR_UI_DISPOSABLE":"1","PINKHA_MINIAPPS_NATIVE_TESTING":"1",
            "GITHUB_SHA":SOURCE,"GITHUB_RUN_ID":run_id,"GITHUB_RUN_ATTEMPT":"1",
            "PINKHA_MINIAPPS_NATIVE_GROUP":original.NATIVE_GROUP,"PINKHA_MINIAPPS_SOURCE_BUNDLE":BUNDLE}
        METHODS=original.METHODS
        ORIGINAL_HELPERS=original.ORIGINAL_HELPERS
        def data_container(label):
            nonlocal app_container
            log,_=commands.run(["xcrun","simctl","get_app_container",udid,BUNDLE,"data"],label,30)
            path=Path(raw(log,4096).decode().strip())
            require(path==app_container and path.resolve()==path and path.is_dir(),"original installed App container changed")
            return path
        data_container("postboot-original-container")
        for label,bundle,original_app in (("source",BUNDLE,app),
                ("companion","com.itorah.hanlinminiapps",Path(producer["app"]))):
            log,_=commands.run(["xcrun","simctl","get_app_container",udid,bundle,"app"],
                               "installed-"+label+"-bundle",30)
            installed=Path(raw(log,4096).decode().strip())
            device_root=Path.home()/"Library/Developer/CoreSimulator/Devices"/udid
            require(installed.is_dir() and installed.resolve()==installed and
                    installed.is_relative_to(device_root/"data/Containers/Bundle/Application"),
                    "installed executable must belong to this original simulator")
            expected_tree=core.inventory(original_app);installed_tree=core.inventory(installed)
            # Installation can normalize POSIX modes. Preserve its exact actual
            # metadata separately; every path, kind, binary/data byte and link
            # must still match the admitted original producer. No signing or
            # installed-mode equivalence is inferred from this content check.
            content=lambda rows:{k:{key:value for key,value in v.items() if key!="mode"}
                                 for k,v in rows.items()}
            require(content(expected_tree)==content(installed_tree),"installed original App or companion bytes differ")
            write(evidence/("installed-"+label+"-inventory.json"),installed_tree)
            write(evidence/("installed-"+label+"-content-binding.json"),{
                "allOriginalPathsKindsBytesAndLinksEqual":True,"installedPath":str(installed),
                "originalPath":str(original_app),"installedInventorySHA256":core.digest(
                    evidence/("installed-"+label+"-inventory.json")),
                "actualModeDifferences":{k:{"original":expected_tree[k]["mode"],"installed":v["mode"]}
                    for k,v in installed_tree.items() if v["mode"]!=expected_tree[k]["mode"]},
                "newInstallations":0,"signingQualification":False})
        def test(index, extra=None):
            label, target, method = METHODS[index]
            native = target == "AnytypeTests"
            item = built["app" if native else "ui"]
            directory = evidence / label
            directory.mkdir(mode=0o700)
            stage = {"status": "FAIL", "testInvoked": False, "target": target, "method": method, "errors": []}
            stage_error = None
            try:
                core.product_integrity(item)
                actual_selector = target + "/" + selection.selector(target, method)
                descriptor, binding = core.bind_descriptor(item, app, actual_selector,
                                                          dict(environment, **(extra or {})))
                path = item["products"] / ("MiniApps-" + label + ".xctestrun")
                with path.open("xb") as stream:
                    stream.write(descriptor)
                os.chmod(path, 0o600)
                item["copies"][path.name] = {"kind": "file", "bytes": len(descriptor),
                                              "mode": 0o600, "sha256": sha(descriptor)}
                write(directory / "descriptor-binding.json", binding)
                listing = directory / "enumeration.json"
                argv = ["xcodebuild", "test-without-building", "-xctestrun", str(path),
                        "-destination", "platform=iOS Simulator,id=" + udid,
                        "-parallel-testing-enabled", "NO", "-only-testing:" + actual_selector,
                        "-collect-test-diagnostics", "never"]
                commands.run(argv + ["-enumerate-tests", "-test-enumeration-style", "flat",
                                     "-test-enumeration-format", "json", "-test-enumeration-output-path", str(listing)],
                             label + "-enumerate", 360)
                stage["enumeration"] = selection.validate_enumeration(json.loads(raw(listing)), target, method)
                core.product_integrity(item)
                require(core.digest(path) == sha(descriptor), "enumerated descriptor changed")
                log, result = commands.run(argv + ["-resultBundlePath", str(directory / "original.xcresult")],
                                           label + "-test", 600, checked=False)
                stage["command"] = result
                require(result["status"] == "PASS_COMMAND", "actual original method command failed")
            except BaseException as exc:
                stage_error = exc
                stage["firstFailure"] = {"type": type(exc).__name__, "reason": str(exc)}
            original = directory / "original.xcresult"
            if original.is_dir():
                for kind in ("summary", "tests"):
                    try:
                        log, _ = commands.run(["xcrun", "xcresulttool", "get", "test-results", kind,
                                               "--path", str(original), "--format", "json"],
                                              label + "-" + kind, 120, capacity=False)
                        data = raw(log)
                        value = json.loads(data)
                        if kind == "summary":
                            stage["originalCounts"] = {k: value.get(k) for k in
                                ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
                        (directory / (kind + ".json")).write_bytes(data)
                        os.chmod(directory / (kind + ".json"), 0o600)
                    except BaseException as exc:
                        stage["errors"].append({"phase": kind, "reason": str(exc)})
                try:
                    commands.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(original),
                                  "--output-path", str(directory / "private-attachments")],
                                 label + "-attachments", 180, capacity=False)
                except BaseException as exc:
                    stage["errors"].append({"phase": "attachments", "reason": str(exc)})
            try:
                core.product_integrity(item)
                if stage_error is None and not stage["errors"]:
                    summary = json.loads(raw(directory / "summary.json"))
                    tree = json.loads(raw(directory / "tests.json"))
                    require({k: summary.get(k) for k in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
                            == {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0},
                            "exact one original method with no skip/failure required")
                    stage["actual"] = host.validate_results(summary, tree, {method}, udid)
                    require(b"** TEST EXECUTE SUCCEEDED **" in raw(root / "commands" / (label + "-test") / "original.log", 64*1024**2),
                            "original successful test stdout required")
                    stage["status"] = "PASS"
            except BaseException as exc:
                stage["errors"].append({"phase": "original-result", "reason": str(exc)})
            stage["testInvoked"] = (root / "commands" / (label + "-test") / "started.json").is_file()
            write(directory / "result.json", stage)
            outcome["methods"].append(stage)
            outcome["testCommandsInvoked"] += int(stage["testInvoked"])
            actual_count = stage.get("originalCounts", {}).get("totalTestCount")
            if type(actual_count) is int and actual_count >= 0:
                outcome["testsExecuted"] += actual_count
            require(stage["status"] == "PASS", "original MiniApps stage failed: " + label)
        ui_env = {"PINKHA_MINIAPPS_FIXTURE_JSON": json.dumps(fixture, ensure_ascii=False),
                  "PINKHA_MINIAPPS_SOURCE_BUNDLE": BUNDLE, "PINKHA_MINIAPPS_SOURCE_SCHEME": "anytype"}
        test(1, ui_env)
        directory = data_container("returned-container") / "Library/Application Support/MiniAppsReceipts"
        journals = [json.loads(raw(p)) for p in directory.glob("*/*.json")]
        journals = [x for x in journals if x.get("completed")]
        require(len(journals) == 2, "two actual completed warm/cold receipts required")
        ordered = []
        for key in ("returnedText", "coldReturnedText"):
            matches = [x for x in journals if [i.get("text") for i in x.get("additions", [])] == [fixture[key]]]
            require(len(matches) == 1 and len(matches[0]["insertedBlocks"]) == 1, "complete actual insertion receipt required")
            ordered.append(matches[0])
        request_ids = [str(uuid.UUID(x["requestID"])) for x in ordered]
        require(len(set(request_ids)) == 2, "distinct real callback request IDs required")
        write(evidence / "private-completed-host-receipts.json", ordered)
        callbacks = dict(PINKHA_MINIAPPS_REQUEST_ID=request_ids[0], PINKHA_MINIAPPS_COLD_REQUEST_ID=request_ids[1])
        test(2, dict(ui_env, **callbacks))
        test(3, callbacks)
        readback = json.loads(raw(data_container("readback-container") / "Library/Application Support/miniapps-native-readback.json"))
        require(readback["status"] == "NATIVE_HEART_READBACK_PASS" and readback["sourceSHA"] == SOURCE
                and readback["requestIDs"] == request_ids, "actual native cold readback differs")
        write(evidence / "private-native-readback.json", readback)
        test(4)
        adapter = json.loads(raw(data_container("adapter-container") / "Library/Application Support/miniapps-native-adapter-readback.json"))
        require(adapter["status"] == "NATIVE_MINIAPPS_ADAPTER_PASS" and adapter["sourceSHA"] == SOURCE
                and adapter["runID"] == run_id and adapter["producerRoundTrips"] == 0
                and adapter["preservedOutputCount"] == 1 and adapter["nativeAttachmentCount"] == 1,
                "actual native selected/file adapter receipt differs")
        for key in ("replacementPreservedBlockID", "replacementPreservedTree", "nativeMarksPreserved",
                    "replayPreservedNewerText", "conflictPreservedNewerText", "nativeAttachmentUploaded",
                    "nativeAttachmentByteReadback", "nestedTableSelectionCaptured",
                    "nestedTableReplacementPersisted", "expiredSelectionDidNotFallback"):
            require(adapter[key] is True, "original native adapter assertion missing: " + key)
        write(evidence / "private-native-adapter-readback.json", adapter)
        require(all(core.digest(source / name) == row["sha256"] for name, row in ORIGINAL_HELPERS.items()),
                "original Git-bound validator changed during execution")
        require(all(core.digest(source / name) == row["sha256"] for name, row in before["files"].items()),
                "compiled source closure changed")
        core.product_integrity(old_ui)
        outcome.update(status="PASS_FOUR_ORIGINAL_REMAINING_MINIAPPS_METHODS",actualCompanionInvocations=2,
                       reusedOriginalNativePreparation=1,actualUIMethods=2,nativeReadback=1,nativeAdapter=1)
    except BaseException as exc:
        primary=exc;outcome["firstFailure"]={"type":type(exc).__name__,"reason":str(exc)}
        (evidence/"private-failure-traceback.txt").write_text(traceback.format_exc())
        (evidence/"private-failure-traceback.txt").chmod(0o600)
    finally:
        if udid is not None:
            if app_container is None:
                try:
                    log, _ = commands.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"],
                                          "final-app-container", 30, capacity=False)
                    app_container = Path(raw(log, 4096).decode().strip())
                except BaseException as exc:
                    outcome["errors"].append({"phase": "final-app-container", "reason": str(exc)})
            try:
                commands.run(["xcrun", "simctl", "shutdown", udid], "shutdown", 120, capacity=False)
            except BaseException as exc:
                outcome["errors"].append({"phase": "shutdown-command", "reason": str(exc)})
            try:
                log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], "shutdown-state", 30, capacity=False)
                devices = [d for ds in json.loads(raw(log))["devices"].values() for d in ds if d.get("udid") == udid]
                require(len(devices) == 1 and devices[0]["state"] == "Shutdown"
                        and devices[0]["name"] == name, "exact owned simulator not Shutdown")
                outcome["ownedSimulatorRetention"] = "Shutdown"
                if app_container is not None:
                    owned = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
                    require(app_container.is_dir() and app_container.resolve() == app_container
                            and not app_container.is_symlink() and owned in app_container.parents,
                            "final app container identity differs")
                    outcome["privateAppContainer"] = str(app_container)
            except BaseException as exc:
                outcome["errors"].append({"phase": "shutdown-state", "reason": str(exc)})
        if built is not None:
            for item in built.values():
                try:
                    core.product_integrity(item)
                except BaseException as exc:
                    outcome["errors"].append({"phase": "product-integrity", "reason": str(exc)})
        unresolved = []
        for group in commands.groups:
            # Never re-probe a positively reaped original group: its numeric ID
            # can later belong to an unrelated project.
            if group in commands.absent_groups:
                continue
            try:
                if commands.present(group):
                    unresolved.append(group)
                else:
                    commands.absent_groups.add(group)
            except BaseException as exc:
                unresolved.append(group)
                outcome["errors"].append({"phase": "owned-group-observation", "group": group, "reason": str(exc)})
        # Commands.run already stops its own live Popen on timeout/cancellation.
        # An unresolved historical group is retained as a failure requiring a
        # fresh ownership check, rather than signalling a possibly recycled ID.
        outcome["ownedGroupsRemaining"] = unresolved
        if outcome["errors"] or outcome["ownedGroupsRemaining"]:
            outcome["status"] = "FAIL"
        outcome["accountBackup"] = "PENDING_EXPLICIT_FOUR_SCOPE_RETENTION"
        write(evidence / "execution.json", outcome)
        print(json.dumps({"status": outcome["status"], "receipt": str(evidence / "execution.json"),
                          "sha256": sha(raw(evidence / "execution.json")), "ownedSimulator": udid}), flush=True)
    if primary is not None or outcome["status"] != "PASS_FOUR_ORIGINAL_REMAINING_MINIAPPS_METHODS":
        raise SystemExit(1)

if __name__=="__main__":main()
