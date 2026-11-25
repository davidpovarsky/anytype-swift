#!/usr/bin/env python3
"""Execute the five original real-native MiniApps cases in a frozen unified app."""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, os, plistlib, re, shutil, sys, time, traceback, uuid
from pathlib import Path
import run_prebuilt_native_ui as owned

METHODS = [
    "testMiniAppsNativeReplacementPreservesFormattingAndAcknowledgesAfterReadback",
    "testMiniAppsNativeReturnPreservesNewerContentAndCreatesOneDurableResultBlock",
    "testMiniAppsNativeFileReturnReadsExactStoredBytesBeforeAcknowledging",
    "testRetiredMiniAppsDocumentCannotWriteOrAcknowledgeItsNativeReturn",
    "testIssuedMiniAppsNativeMutationDoesNotAppendAfterLaterUserEdit",
]
TARGET = "AnytypeTests"
CLASS = "NativeDocumentPublicationTests"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-root",type=Path,required=True)
    parser.add_argument("--main-evidence",type=Path,required=True)
    parser.add_argument("--frozen-inputs",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    for path in (args.main_root,args.main_evidence,args.frozen_inputs,args.output):
        owned.require(path.is_absolute() and path.resolve()==path,"canonical_owned_path_required")
    owned.require(all(args.main_root in p.parents for p in (args.main_evidence,args.frozen_inputs,args.output)),
                  "one_explicit_owned_main_root_required")
    owned.require(not args.output.exists(),"refuse_existing_output")
    out=args.output;out.mkdir(mode=0o700);os.umask(0o077)
    source=args.frozen_inputs/"source"
    receipt={"status":"FAIL","applicationBuilds":0,"nativeLibraryBuilds":0,"uiBuilds":0,
             "testsExecuted":0,"scope":"actual_native_model_and_SDK_transport_not_companion_UI"}
    udid=None;products=None;expected=None;first=None;cleanup=[]
    try:
        record=json.loads((args.main_evidence/"receipt.json").read_bytes())
        frozen=json.loads((args.frozen_inputs/"receipt.json").read_bytes())
        owned.require(record["status"]=="PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
                      and record["testsExecuted"]==0 and record["sourceUnchanged"],"original_completed_build_required")
        owned.require(frozen["status"]=="PASS_EXACT_FROZEN_NATIVE_UI_INPUTS"
                      and frozen["sourceCommit"]==record["sourceCommit"]
                      and frozen["mainReceiptSHA256"]==owned.digest(args.main_evidence/"receipt.json"),
                      "exact_private_source_provenance_required")
        before=json.loads((args.main_evidence/"source-before.json").read_bytes())
        owned.require(before==json.loads((args.main_evidence/"source-after.json").read_bytes()),"unchanged_build_source")
        for name,row in before["files"].items():
            owned.require(owned.digest(source/name)==row["sha256"],"frozen_source_changed:"+name)
        manifests=json.loads((args.main_evidence/"products-all.json").read_bytes())
        owned.require(owned.digest(args.main_evidence/"products-all.json")==
                      record["completeProductsInventory"]["sha256"],"original_product_inventory_changed")
        original=Path(manifests["app-derived"]["base"]);expected=manifests["app-derived"]["entries"]
        owned.require(owned.inventory(original)==expected,"original_products_changed_before_clone")
        products=out/"products"
        owned.run(["cp","-cR",str(original),str(products)],out,"clone-products")
        owned.require(owned.inventory(products)==expected,"complete_product_clone_mismatch")
        template=products/"Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun"
        initial=plistlib.loads(template.read_bytes())
        owned.require(initial["__xctestrun_metadata__"]["FormatVersion"]==2
                      and len(initial["TestConfigurations"])==1,"original_format2_configuration_required")
        configuration=initial["TestConfigurations"][0]
        targets=[t for t in configuration["TestTargets"] if t.get("BlueprintName")==TARGET]
        owned.require(len(targets)==1 and configuration["IsEnabled"] is True,"one_original_host_target")
        target=targets[0]
        owned.require(target.get("IsAppHostedTestBundle") is True
                      and target.get("TestHostBundleIdentifier")=="io.anytype.app"
                      and not target.get("OnlyTestIdentifiers") and not target.get("SkipTestIdentifiers"),
                      "unmodified_original_app_host_target_required")
        _,raw=owned.run(["xcrun","simctl","list","runtimes","--json"],out,"runtimes")
        runtimes=[x for x in json.loads(raw)["runtimes"] if x.get("isAvailable") is True
                  and x.get("version")=="27.0" and "iOS" in x.get("name","")]
        owned.require(len(runtimes)==1,"one_original_ios27_runtime_required")
        name="PinkhaUnifiedNativeMiniApps-"+str(uuid.uuid4())
        _,raw=owned.run(["xcrun","simctl","create",name,
                        "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB",
                        runtimes[0]["identifier"]],out,"create-simulator")
        udid=str(uuid.UUID(raw.decode().strip())).upper()
        owned.write(out/"simulator.json",{"ownedUDID":udid,"name":name,"runtime":runtimes[0]["identifier"]})
        owned.run(["xcrun","simctl","boot",udid],out,"boot-simulator")
        owned.run(["xcrun","simctl","bootstatus",udid,"-b"],out,"bootstatus",timeout=180)
        _,raw=owned.run(["xcrun","simctl","getenv",udid,"SIMULATOR_ROOT"],out,"runtime-root")
        runtime_root=Path(raw.decode().strip())
        configured=copy.deepcopy(initial)
        selected=copy.deepcopy(target);selected["OnlyTestIdentifiers"]=[CLASS+"/"+name for name in METHODS]
        selected["SystemAttachmentLifetime"]="keepAlways";selected["UserAttachmentLifetime"]="keepAlways"
        configured["TestConfigurations"][0]["TestTargets"]=[selected]
        inverse=copy.deepcopy(configured);inverse["TestConfigurations"][0]["TestTargets"]=configuration["TestTargets"]
        owned.require(inverse==initial,"unexpected_native_test_descriptor_delta")
        injections={}
        for key in ("EnvironmentVariables","TestingEnvironmentVariables"):
            env=selected.get(key,{})
            if "DYLD_INSERT_LIBRARIES" in env:
                old=env["DYLD_INSERT_LIBRARIES"];parts=[]
                for item in old.split(":"):
                    if item.endswith("/libMainThreadChecker.dylib"):
                        actual=runtime_root/"usr/lib/libMainThreadChecker.dylib"
                        owned.require(actual.is_file(),"actual_runtime_checker_required");parts.append(str(actual))
                    else:parts.append(item)
                env["DYLD_INSERT_LIBRARIES"]=":".join(parts)
                injections[key]={"before":old,"after":env["DYLD_INSERT_LIBRARIES"]}
        def paths(value):
            if isinstance(value,str):return value.replace("__TESTROOT__",str(products))
            if isinstance(value,list):return [paths(x) for x in value]
            if isinstance(value,dict):return {k:paths(v) for k,v in value.items()}
            return value
        configured=paths(configured)
        descriptor=out/"Selected.xctestrun";descriptor.write_bytes(plistlib.dumps(configured,sort_keys=False))
        descriptor.chmod(0o600)
        owned.write(out/"descriptor-binding.json",{"originalSHA256":owned.digest(template),
            "copiedSHA256":owned.digest(descriptor),"originalInverseEqual":True,
            "selectedMethods":METHODS,"runtimeInjection":injections})
        receipt.update(sourceCommit=record["sourceCommit"],mainReceiptSHA256=owned.digest(args.main_evidence/"receipt.json"),
                       originalSourceSHA256=owned.digest(args.main_evidence/"source-before.json"),
                       frozenReceiptSHA256=owned.digest(args.frozen_inputs/"receipt.json"))
        plan=["xcodebuild","test-without-building","-xctestrun",str(descriptor),
              "-destination","platform=iOS Simulator,id="+udid,"-parallel-testing-enabled","NO",
              "-test-timeouts-enabled","YES","-default-test-execution-time-allowance","300",
              "-maximum-test-execution-time-allowance","300","-collect-test-diagnostics","never",
              "ARCHS=arm64","ONLY_ACTIVE_ARCH=YES","CODE_SIGN_IDENTITY=-","CODE_SIGNING_ALLOWED=YES",
              "CODE_SIGNING_REQUIRED=YES"]
        for method in METHODS:plan.append("-only-testing:"+TARGET+"/"+CLASS+"/"+method)
        enumeration=out/"enumeration.json"
        owned.run(plan+["-enumerate-tests","-test-enumeration-style","flat","-test-enumeration-format","json",
                        "-test-enumeration-output-path",str(enumeration)],out,"enumerate",timeout=180)
        contract=owned.original_module(source/"Tools/AnyEnginePort/native_ui_transition_contract.py","native_model_enumeration")
        label,enabled,disabled=contract.enumerated_identifiers(json.loads(enumeration.read_bytes()))
        expected_names={TARGET+"/"+CLASS+"/"+x for x in METHODS}
        normalize=lambda value: value[:-2] if value.endswith("()") else value
        owned.require({normalize(x) for x in enabled}==expected_names and not disabled,"exact_five_original_methods_required")
        owned.write(out/"selection.json",{"testPlan":label,"enabled":sorted(enabled),"disabled":[]})
        owned.run(plan+["-resultBundlePath",str(out/"Original.xcresult")],out,"execute",timeout=1800,allow_failure=True)
    except BaseException as exc:
        first={"type":type(exc).__name__,"reason":str(exc)}
        owned.write(out/"first-failure.json",{**first,"traceback":traceback.format_exc()})
    finally:
        issued=(out/"execute.command.json").is_file()
        receipt["testsExecuted"]=None if issued else 0
        receipt["testCommandIssued"]=issued
        result=out/"Original.xcresult"
        if result.is_dir():
            try:
                values={}
                for kind in ("summary","tests"):
                    _,raw=owned.run(["xcrun","xcresulttool","get","test-results",kind,
                        "--path",str(result),"--format","json"],out,"original-"+kind,cleanup=True)
                    values[kind]=json.loads(raw);owned.write(out/(kind+".json"),values[kind])
                parser=owned.original_module(source/"Tools/AnyEnginePort/verify_native_test_execution.py","native_model_results")
                cases=parser.test_cases(values["tests"])
                counts={k:values["summary"].get(k) for k in ("totalTestCount","passedTests","failedTests","skippedTests")}
                receipt.update(counts=counts,actualCases=cases,testsExecuted=counts["totalTestCount"])
                actual={re.sub(r"\(\)$","",key.split(CLASS+"/")[-1]) for key in cases}
                owned.require(counts=={"totalTestCount":5,"passedTests":5,"failedTests":0,"skippedTests":0}
                              and actual==set(METHODS) and all(v=="Passed" for v in cases.values()),
                              "five_original_native_methods_did_not_pass")
                devices=values["summary"]["devicesAndConfigurations"]
                owned.require(len(devices)==1 and devices[0]["device"]["deviceId"].upper()==udid
                              and devices[0]["device"]["architecture"]=="arm64","actual_result_device_mismatch")
            except BaseException as exc:cleanup.append({"phase":"original-results","reason":str(exc)})
        if udid is not None:
            try:
                _,raw=owned.run(["xcrun","simctl","get_app_container",udid,"io.anytype.app","data"],out,
                                "owned-sandbox",cleanup=True)
                sandbox=Path(raw.decode().strip())
                owned.require(sandbox.resolve()==sandbox and udid in sandbox.parts and sandbox.is_dir(),
                              "owned_sandbox_path_required")
                owned.run(["xcrun","simctl","shutdown",udid],out,"shutdown-simulator",cleanup=True)
                owned.run(["cp","-cR",str(sandbox),str(out/"private-native-sandbox")],out,
                          "retain-private-sandbox",cleanup=True)
                (out/"private-native-sandbox").chmod(0o700)
                data=Path(*sandbox.parts[:sandbox.parts.index(udid)+1])/"data"
                keychains=data/"Library/Keychains"
                if keychains.is_dir():
                    owned.require(not keychains.is_symlink() and keychains.resolve()==keychains,"owned_private_keychain_path")
                    owned.run(["cp","-cR",str(keychains),str(out/"private-owned-keychains")],out,
                              "retain-private-keychains",cleanup=True)
                    (out/"private-owned-keychains").chmod(0o700)
                owned.write(out/"private-retention.json",{"ownedUDID":udid,
                    "sandboxRetained":True,"keychainsRetained":(out/"private-owned-keychains").is_dir(),
                    "containsPrivateDisposableAccountData":True,"publishRawBytes":False})
            except BaseException as exc:cleanup.append({"phase":"private-retention","reason":str(exc)})
            try:owned.run(["xcrun","simctl","delete",udid],out,"delete-owned-simulator",cleanup=True)
            except BaseException as exc:cleanup.append({"phase":"delete-owned-simulator","reason":str(exc)})
        try:
            if products is not None and expected is not None:
                owned.require(owned.inventory(products)==expected,"frozen_test_products_changed")
            for name,row in before["files"].items():
                owned.require(owned.digest(source/name)==row["sha256"],"frozen_source_changed_after:"+name)
        except BaseException as exc:cleanup.append({"phase":"input-integrity","reason":str(exc)})
        receipt.update(firstFailure=first,diagnosticFailures=cleanup,ownedSimulator=udid,finished=time.time())
        receipt["status"]="PASS" if first is None and not cleanup and receipt.get("counts",{}).get("passedTests")==5 else "FAIL"
        owned.write(out/"receipt.json",receipt)
    owned.require(receipt["status"]=="PASS","actual_native_model_acceptance_failed")

if __name__=="__main__":main()
