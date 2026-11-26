"""Continue four original source methods on the exact sealed App14 account.

The original preparation/mounted PASS and first-menu failure remain separate
originals. No account is created/restored and no fixture deadline is changed.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import time
import traceback

sys.dont_write_bytecode = True
import combined_heart_semantics_replacement as c
import retain_owned_heart_account as account
import direct_menu_ui_profile as ui_profile

CORE = "4c64b23e605970cc636b012aa79a66ab4766c66bf323ca7299d9d7fc9caaaf6c"
RETENTION = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
SOURCE = "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
ADMISSION = "3891392dd8ba546d1e9f9b46d850d646d154fd8e91e3979a04008315410aaad0"
PRIOR = Path("/Users/m1/development/anytype-e-active-20261125/main14/fresh-native11619-attempt2")
PRIOR_EXECUTION = "88e4922567b07215067fafc5072ccdc0251fea2d60b3721938c3d5bceeecafe5"
PRIOR_BACKUP = "180b37d0c4c718fdcd4539843a5ce279ec3c8376c8d4ead0fcce7cb6c30cb262"
ORIGINAL_FIXTURE = "bddb0844a4314fb00fe348943d0340aa09fe77653a21279387ff2ced2a244c2e"
ORIGINAL_PLIST = "ed2972bf30a5999f90b4c12258de77542529d7218a2d6cf7ae0c77e5a41cc27e"
DEVICE = "2DB40043-F2BF-4D7D-86EE-B56E9640B039"
UI_ADMISSION = "42459c51512d1ac3f2bbc7f7ea45049aa6136f4c07bfdc2066e0b4e9343ad938"
UI_PROFILE = "cfe6e3a9ec6a93417050e076071ac0704774391d3be2fd9d9923cd8e62bd7f07"

CUSTODY = PRIOR.parent / "direct-menu-continuation1"
CUSTODY_EXECUTION = "cf0c3add72771a5540a026c98e665afbd6a9f887237fc4f5ca6a3316f8e3624d"
CUSTODY_BACKUP = "edc062aeec58156bb805aae76cdea5d8443f1e6f0ce30b0f8f4f9f1264cf738f"
CUSTODY_PLIST = "1bb2fe60d9cd48b1da33c0a0127cc2d0087db8bae0e3c75cdf06c48d708834e2"
CUSTODY_COMPLETION = "7bd4f893993378dd9557ba5b9494aff4633686c82e46f0f37f25b8767b22f554"

CURRENT_CUSTODY = PRIOR.parent / "direct-menu-continuation2"
CURRENT_CUSTODY_EXECUTION = "265a52e2c6e8f21efb0dbcdda0778f02a5ba0835358b8778eb408c3f78bb5042"
CURRENT_CUSTODY_BACKUP = "8c17100136edb75a6db54240503b0801a5b827cf70d40ddc94d01353e5beff71"
CURRENT_CUSTODY_PLIST = "ccdb1b7f32a932a45d28c363a2f2204bceae83b02caf92b834ad6680c54db17f"
CURRENT_CUSTODY_COMPLETION = "a0ffe58b3433279fc5ca047f0e3f7e3e33e9c1eb3d03bc6ad500e3e35db3e106"


LATEST_CUSTODY = PRIOR.parent / "direct-menu-continuation3"
LATEST_CUSTODY_EXECUTION = "8988311d245e0efea62ef04aca7ce03bb3953d9f140ceb3de89a701c329a52fb"
LATEST_CUSTODY_BACKUP = "7590f78afd7ae64d32a59b87fd61d3eedad240a15bbec8f604f2860fa48b79f8"
LATEST_CUSTODY_PLIST = "f93a0766eb22c55ef9b7c89d6b42d39ffc9dd7cbb11d20c72fd3c4555500fdfc"
LATEST_CUSTODY_COMPLETION = "341a528c0c8129fc800c16ff108afca0a3e2186443929ea63d89876db9fd365d"

LONG_PRESS_CUSTODY = PRIOR.parent / "long-press-menu-continuation1"
LONG_PRESS_CUSTODY_EXECUTION = "f251cf30a90fe4af041b0d4f9632a5c9ea6696b9fe1549f3316b3bbc013e5279"
LONG_PRESS_CUSTODY_BACKUP = "40a4697cb2b6d565353cff5ad789636dd436f931ec60f1e0ddea0d8438d48b83"
LONG_PRESS_CUSTODY_PLIST = "38e37c324483062792cb0276438e540f58542d84813dfeb468451e9572eaa367"
LONG_PRESS_CUSTODY_COMPLETION = "e979680e8627bba4e2cdd99bdb2135a82fc3c808b3a372234be8e611f5c25caa"

# These aliases let the entire four-stage execution/verification sequence remain
# byte-exact to the reviewed original controller. No predicate is rewritten.
require, app_file, decode, sha, write = c.require, c.app_file, c.decode, c.sha, c.write
continuation_ui, continuation_native, STAGES = c.continuation_ui, c.continuation_native, c.STAGES
CAPTURE, REOPEN = c.CAPTURE, c.REOPEN


def admit_prior(admission):
    path = PRIOR / "evidence/execution.json"
    require(c.digest(path) == PRIOR_EXECUTION, "Exact original App14 result required")
    prior = decode(c.raw(path))
    require(prior["status"] == "FAIL" and prior["sourceCommit"] == admission["sourceCommit"] == SOURCE
            and prior["controllerSHA256"] == CORE and prior["nativeManifestSHA256"] == c.MANIFEST
            and prior["heartOverlaySHA256"] == c.OVERLAY and prior["ownedSimulator"] == DEVICE,
            "Original source/native/owned device identity differs")
    require(set(prior["stages"]) == {"preparation", "mounted", "linked-ui"}
            and all(prior["stages"][name]["status"] == "PASS"
                    and prior["stages"][name]["testInvoked"] is True for name in ("preparation", "mounted"))
            and prior["stages"]["linked-ui"]["status"] == "FAIL"
            and prior["stages"]["linked-ui"]["testInvoked"] is True,
            "Original two passes and actual first-menu failure may not be reclassified")
    for name in ("preparation", "mounted"):
        folder = PRIOR / "evidence" / name
        log = PRIOR / "commands" / (name + "-test") / "original.log"
        actual = c.qualify_execution(decode(c.raw(folder / "summary.json")),
            decode(c.raw(folder / "tests.json")), STAGES[name], DEVICE, log)
        require(decode(json.dumps(actual).encode()) == prior["stages"][name]["actual"]
                and c.digest(log) == prior["stages"][name]["command"]["logSHA256"]
                and prior["stages"][name]["command"]["exitCode"] == 0,
                "Original named actual pass/stdout changed")
        c.qualify_enumeration(decode(c.raw(folder / "enumeration.json")), STAGES[name])
    failed = prior["stages"]["linked-ui"]
    require(failed["command"]["exitCode"] == 65
            and failed["command"]["logSHA256"] == "13ca9aa5fb5a028c6c09c29832e4e30f7b2677aa5b55e375faf9f0955ad2dbdc"
            and c.digest(PRIOR / "commands/linked-ui-test/original.log") == failed["command"]["logSHA256"],
            "Original actual failed UI stdout must remain exact")
    summary = decode(c.raw(PRIOR / "evidence/linked-ui/summary.json"))
    require(summary["totalTestCount"] == summary["failedTests"] == 1
            and summary["passedTests"] == summary["skippedTests"] == 0
            and len(summary["testFailures"]) == 1
            and summary["testFailures"][0]["testIdentifierString"] ==
                "SemanticAnchorPage154MountedUITests/testExistingSemanticAnchorSourceLinkEditAndColdReopen()"
            and "source-menu-not-ready" in summary["testFailures"][0]["failureText"],
            "Original failure must remain a single actual first-menu failure")
    trace_path = PRIOR / "evidence/linked-ui/private-attachments/E910C0D0-0E4B-48FB-8D5D-D1244F53800E.json"
    require(c.digest(trace_path) == "e6be11e5ddbde9201e827dc01a72eb0ff5f18c1af6ff2930fb16ecfbb5189e2f",
            "Original zero-action menu trace changed")
    trace = decode(c.raw(trace_path))
    require(trace["protocol"] == "pinkha-semantic-source-menu-v1" and trace["status"] == "FAIL"
            and trace["sourceActionTaps"] == trace["nextPageTaps"] == 0
            and all(trace[k] == v for k, v in prior["binding"].items()),
            "Original menu trace does not bind this failed execution")
    require(not any((PRIOR / "commands" / (name + "-test") / "started.json").exists()
                    for name in ("linked-native", "unlinked-ui", "unlinked-native")),
            "An unreported later original method was invoked")
    cleanup = prior["cleanup"]
    require(cleanup["status"] == "PASS" and cleanup["errors"] == []
            and cleanup["ownedSimulatorDeleted"] is False
            and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
            and all(row.get("absentAtOriginalExit") is True and row.get("historicalGroupReprobed") is False
                    for row in cleanup["groups"]), "Original owned cleanup is incomplete")
    require(c.digest(PRIOR / "private/final-sandbox-originals" / c.FIXTURE) == ORIGINAL_FIXTURE
            and c.digest(PRIOR / "private/owned-account-originals/device.plist") == ORIGINAL_PLIST,
            "Original fixture/private device metadata changed")
    return prior


def admit_failed_controller(prior):
    path = CUSTODY / "evidence/execution.json"
    require(c.digest(path) == CUSTODY_EXECUTION, "Exact zero-method controller failure required")
    failed = decode(c.raw(path))
    require(failed["status"] == "FAIL" and failed["controllerSHA256"] ==
            "f3db3ec62767e641f03bd956191c1733a3d52f3a432655232f80ceea09a3e6ce"
            and failed["coreControllerSHA256"] == CORE and failed["sourceCommit"] == SOURCE
            and failed["nativeManifestSHA256"] == c.MANIFEST and failed["heartOverlaySHA256"] == c.OVERLAY
            and failed["ownedSimulator"] == DEVICE and failed["binding"] == prior["binding"]
            and failed["stages"] == {} and failed["actualInvocationStartedEvidence"] == {}
            and failed["actualMethodsInvokedInThisContinuation"] == 0
            and failed["firstFailure"] == {"type": "ValueError", "message": "scoped command label required"},
            "Prior controller failure scope or exact original binding changed")
    require(failed["uiDerivative"]["uiReceiptSHA256"] ==
            "fb360a5f9764f27de59d4004170c9ca5996da0d189b2d2d798142ccd2c730691"
            and failed["uiDerivative"]["uiTestChangeCommit"] == "813f4f03edf2d965b4167cab5966fa6d3857f97e",
            "Failed continuation did not use the admitted UI-only producer")
    require(failed["originalFixtureSHA256"] == ORIGINAL_FIXTURE
            and failed["priorExecutionSHA256"] == PRIOR_EXECUTION
            and failed["priorBackupSHA256"] == PRIOR_BACKUP
            and failed["originalFixtureExpiryUnix"] ==
                decode(c.raw(PRIOR / "private/final-sandbox-originals" / c.FIXTURE))["createdAt"] + 978307200 + 7200,
            "Prior failure changed the original prepared fixture or deadline")
    require(not any(CUSTODY.glob("commands/*-test/started.json"))
            and not any(CUSTODY.glob("commands/*-enumerate/started.json")),
            "A test or enumeration was invoked by the failed continuation")
    cleanup = failed["cleanup"]
    require(cleanup["status"] == "PASS" and cleanup["errors"] == []
            and cleanup["ownedSimulatorDeleted"] is False
            and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
            and all(row.get("absentAtOriginalExit") is True
                    and row.get("historicalGroupReprobed") is False for row in cleanup["groups"]),
            "Failed continuation did not drain its owned processes")
    for name, row in prior["finalPrivateSandbox"]["files"].items():
        current = failed["finalPrivateSandbox"]["files"][name]
        require(current == row, "Original mounted witness status changed in the zero-method continuation")
        if row["status"] == "COPIED_ORIGINAL":
            require(c.digest(CUSTODY / "private/final-sandbox-originals" / name) == row["sha256"],
                    "Retained current witness bytes differ from original mounted acceptance")
    completion_path = CUSTODY / "evidence/retention-completion.json"
    require(c.digest(completion_path) == CUSTODY_COMPLETION
            and c.digest(CUSTODY / "private/owned-account-originals/retention.json") == CUSTODY_BACKUP
            and c.digest(CUSTODY / "private/owned-account-originals/device.plist") == CUSTODY_PLIST,
            "Exact post-failure full private custody is required")
    completion = decode(c.raw(completion_path))
    require(completion["executionSHA256"] == CUSTODY_EXECUTION
            and completion["devicePlistSHA256"] == CUSTODY_PLIST
            and completion["privateAccount"] == decode(c.raw(CUSTODY / "private/owned-account-originals/retention.json"))
            and completion["fullEAcceptance"] is False,
            "Post-failure custody may not reclassify acceptance")
    return {"executionSHA256": CUSTODY_EXECUTION, "backupSHA256": CUSTODY_BACKUP,
            "devicePlistSHA256": CUSTODY_PLIST, "methodsInvoked": 0,
            "status": "RETAINED_ORIGINAL_CONTROLLER_FAILURE_NOT_ACCEPTANCE"}

def admit_failed_witness_copy(prior, predecessor):
    path = CURRENT_CUSTODY / "evidence/execution.json"
    require(c.digest(path) == CURRENT_CUSTODY_EXECUTION, "Exact zero-method controller failure required")
    failed = decode(c.raw(path))
    require(failed["status"] == "FAIL" and failed["controllerSHA256"] ==
            "25d860048c24002632b25cdc2721d1ca769b13ced95a587f974f83bf1f2fcfa4"
            and failed["coreControllerSHA256"] == CORE and failed["sourceCommit"] == SOURCE
            and failed["nativeManifestSHA256"] == c.MANIFEST and failed["heartOverlaySHA256"] == c.OVERLAY
            and failed["ownedSimulator"] == DEVICE and failed["binding"] == prior["binding"]
            and failed["stages"] == {} and failed["actualInvocationStartedEvidence"] == {}
            and failed["actualMethodsInvokedInThisContinuation"] == 0
            and failed["currentCustody"] == predecessor
            and failed["firstFailure"] == {"type": "FileExistsError", "message":
                "[Errno 17] File exists: '" + str(CURRENT_CUSTODY / "private/pinkha-semantic-page154-mounted-capture.json") + "'"},
            "Prior controller failure scope or exact original binding changed")
    require(failed["uiDerivative"]["uiReceiptSHA256"] ==
            "fb360a5f9764f27de59d4004170c9ca5996da0d189b2d2d798142ccd2c730691"
            and failed["uiDerivative"]["uiTestChangeCommit"] == "813f4f03edf2d965b4167cab5966fa6d3857f97e",
            "Failed continuation did not use the admitted UI-only producer")
    require(failed["originalFixtureSHA256"] == ORIGINAL_FIXTURE
            and failed["priorExecutionSHA256"] == PRIOR_EXECUTION
            and failed["priorBackupSHA256"] == PRIOR_BACKUP
            and failed["originalFixtureExpiryUnix"] ==
                decode(c.raw(PRIOR / "private/final-sandbox-originals" / c.FIXTURE))["createdAt"] + 978307200 + 7200,
            "Prior failure changed the original prepared fixture or deadline")
    require(not any(CURRENT_CUSTODY.glob("commands/*-test/started.json"))
            and not any(CURRENT_CUSTODY.glob("commands/*-enumerate/started.json")),
            "A test or enumeration was invoked by the failed continuation")
    cleanup = failed["cleanup"]
    require(cleanup["status"] == "PASS" and cleanup["errors"] == []
            and cleanup["ownedSimulatorDeleted"] is False
            and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
            and all(row.get("absentAtOriginalExit") is True
                    and row.get("historicalGroupReprobed") is False for row in cleanup["groups"]),
            "Failed continuation did not drain its owned processes")
    for name, row in prior["finalPrivateSandbox"]["files"].items():
        current = failed["finalPrivateSandbox"]["files"][name]
        require(current == row, "Original mounted witness status changed in the zero-method continuation")
        if row["status"] == "COPIED_ORIGINAL":
            require(c.digest(CURRENT_CUSTODY / "private/final-sandbox-originals" / name) == row["sha256"],
                    "Retained current witness bytes differ from original mounted acceptance")
    completion_path = CURRENT_CUSTODY / "evidence/retention-completion.json"
    require(c.digest(completion_path) == CURRENT_CUSTODY_COMPLETION
            and c.digest(CURRENT_CUSTODY / "private/owned-account-originals/retention.json") == CURRENT_CUSTODY_BACKUP
            and c.digest(CURRENT_CUSTODY / "private/owned-account-originals/device.plist") == CURRENT_CUSTODY_PLIST,
            "Exact post-failure full private custody is required")
    completion = decode(c.raw(completion_path))
    require(completion["executionSHA256"] == CURRENT_CUSTODY_EXECUTION
            and completion["devicePlistSHA256"] == CURRENT_CUSTODY_PLIST
            and completion["privateAccount"] == decode(c.raw(CURRENT_CUSTODY / "private/owned-account-originals/retention.json"))
            and completion["fullEAcceptance"] is False,
            "Post-failure custody may not reclassify acceptance")
    return {"executionSHA256": CURRENT_CUSTODY_EXECUTION, "backupSHA256": CURRENT_CUSTODY_BACKUP,
            "devicePlistSHA256": CURRENT_CUSTODY_PLIST, "methodsInvoked": 0,
            "status": "RETAINED_ORIGINAL_CONTROLLER_FAILURE_NOT_ACCEPTANCE"}


def admit_failed_direct_selection(prior, predecessor):
    path = LATEST_CUSTODY / "evidence/execution.json"
    require(c.digest(path) == LATEST_CUSTODY_EXECUTION, "Exact original direct-selection failure required")
    failed = decode(c.raw(path))
    require(failed["status"] == "FAIL" and failed["controllerSHA256"] ==
            "bad5bd86fbb037db43c54c2cf2e6a145bfae8157b9012f12a5cf02351e7872e4"
            and failed["coreControllerSHA256"] == CORE and failed["sourceCommit"] == SOURCE
            and failed["nativeManifestSHA256"] == c.MANIFEST and failed["heartOverlaySHA256"] == c.OVERLAY
            and failed["ownedSimulator"] == DEVICE and failed["binding"] == prior["binding"]
            and set(failed["stages"]) == {"linked-ui"}
            and failed["actualMethodsInvokedInThisContinuation"] == 1
            and set(failed["actualInvocationStartedEvidence"]) == {"linked-ui"}
            and failed["currentCustody"] == predecessor
            and failed["firstFailure"] == {"type": "ValueError", "message": "linked-ui actual method failed"},
            "Original actual failed method or custody changed")
    stage = failed["stages"]["linked-ui"]
    require(stage["status"] == "FAIL" and stage["testInvoked"] is True
            and stage["command"]["exitCode"] == 65 and stage["command"]["ownedGroupPresentAfterExit"] is False
            and stage["command"]["logSHA256"] == "e56ba02679a0e35b8b601dfd29b61065abfef148eec605c17c57f2720c63a6bc"
            and c.digest(LATEST_CUSTODY / "commands/linked-ui-test/original.log") == stage["command"]["logSHA256"]
            and c.digest(LATEST_CUSTODY / "commands/linked-ui-test/started.json") ==
                failed["actualInvocationStartedEvidence"]["linked-ui"]["sha256"],
            "Original actual failed UI command/start/stdout changed")
    summary_path = LATEST_CUSTODY / "evidence/linked-ui/summary.json"
    require(c.digest(summary_path) == "cc7f0465510a1a8ec7c6e579c08ec4881bd6589533bedae1adfefb7432c1049c",
            "Original actual failed UI summary changed")
    summary = decode(c.raw(summary_path))
    require(summary["totalTestCount"] == summary["failedTests"] == 1
            and summary["passedTests"] == summary["skippedTests"] == 0
            and len(summary["testFailures"]) == 1
            and summary["testFailures"][0]["testIdentifierString"] ==
                "SemanticAnchorPage154MountedUITests/testExistingSemanticAnchorSourceLinkEditAndColdReopen()"
            and "source-menu-not-ready" in summary["testFailures"][0]["failureText"],
            "Original direct-selection failure is not the exact actual method")
    trace_path = LATEST_CUSTODY / "evidence/linked-ui/private-attachments/4DA35AD9-7DCB-431E-8D8E-50E4427DA306.json"
    require(c.digest(trace_path) == "ee2e74a6ed699f1892e3518f00360681e049a191e477dd5f9d23dfdb7b34bf7f",
            "Original zero-action menu trace changed")
    trace = decode(c.raw(trace_path))
    require(trace["protocol"] == "pinkha-semantic-source-menu-v1" and trace["status"] == "FAIL"
            and trace["sourceActionTaps"] == trace["nextPageTaps"] == 0
            and all(trace[k] == v for k, v in prior["binding"].items())
            and failed["uiDerivative"]["uiReceiptSHA256"] ==
                "fb360a5f9764f27de59d4004170c9ca5996da0d189b2d2d798142ccd2c730691"
            and failed["uiDerivative"]["uiTestChangeCommit"] == "813f4f03edf2d965b4167cab5966fa6d3857f97e",
            "Original failed UI source or zero-action trace changed")
    require(failed["originalFixtureSHA256"] == ORIGINAL_FIXTURE
            and failed["priorExecutionSHA256"] == PRIOR_EXECUTION and failed["priorBackupSHA256"] == PRIOR_BACKUP
            and failed["originalFixtureExpiryUnix"] ==
                decode(c.raw(PRIOR / "private/final-sandbox-originals" / c.FIXTURE))["createdAt"] + 978307200 + 7200,
            "Original prepared fixture or expiry changed")
    require(not any((LATEST_CUSTODY / "commands" / (name + "-test") / "started.json").exists()
                    for name in ("linked-native", "unlinked-ui", "unlinked-native")),
            "An unreported later original method was invoked")
    cleanup = failed["cleanup"]
    require(cleanup["status"] == "PASS" and cleanup["errors"] == []
            and cleanup["ownedSimulatorDeleted"] is False
            and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
            and all(row.get("absentAtOriginalExit") is True and row.get("historicalGroupReprobed") is False
                    for row in cleanup["groups"]), "Original failed UI cleanup is incomplete")
    for name, row in prior["finalPrivateSandbox"]["files"].items():
        require(failed["finalPrivateSandbox"]["files"][name] == row,
                "Original mounted witness status changed after direct selection")
        if row["status"] == "COPIED_ORIGINAL":
            require(c.digest(LATEST_CUSTODY / "private/final-sandbox-originals" / name) == row["sha256"],
                    "Original mounted witness bytes changed after failed selection")
    completion_path = LATEST_CUSTODY / "evidence/retention-completion.json"
    require(c.digest(completion_path) == LATEST_CUSTODY_COMPLETION
            and c.digest(LATEST_CUSTODY / "private/owned-account-originals/retention.json") == LATEST_CUSTODY_BACKUP
            and c.digest(LATEST_CUSTODY / "private/owned-account-originals/device.plist") == LATEST_CUSTODY_PLIST,
            "Exact current failed UI full-account custody required")
    completion = decode(c.raw(completion_path))
    require(completion["executionSHA256"] == LATEST_CUSTODY_EXECUTION
            and completion["devicePlistSHA256"] == LATEST_CUSTODY_PLIST
            and completion["privateAccount"] == decode(c.raw(LATEST_CUSTODY / "private/owned-account-originals/retention.json"))
            and completion["fullEAcceptance"] is False, "Failed UI custody cannot become acceptance")
    return {"executionSHA256": LATEST_CUSTODY_EXECUTION, "backupSHA256": LATEST_CUSTODY_BACKUP,
            "devicePlistSHA256": LATEST_CUSTODY_PLIST, "methodsInvoked": 1,
            "status": "RETAINED_ORIGINAL_DIRECT_SELECTION_UI_FAILURE_NOT_ACCEPTANCE"}

def admit_failed_long_press(prior, predecessor):
    path = LONG_PRESS_CUSTODY / "evidence/execution.json"
    require(c.digest(path) == LONG_PRESS_CUSTODY_EXECUTION, "Exact original long-press failure required")
    failed = decode(c.raw(path))
    require(failed["status"] == "FAIL" and failed["controllerSHA256"] ==
            "082deabb3da5dc630694621bd941404a644856339c48c9a706d80578e48d723d"
            and failed["coreControllerSHA256"] == CORE and failed["sourceCommit"] == SOURCE
            and failed["nativeManifestSHA256"] == c.MANIFEST and failed["heartOverlaySHA256"] == c.OVERLAY
            and failed["ownedSimulator"] == DEVICE and failed["binding"] == prior["binding"]
            and set(failed["stages"]) == {"linked-ui"}
            and failed["actualMethodsInvokedInThisContinuation"] == 1
            and set(failed["actualInvocationStartedEvidence"]) == {"linked-ui"}
            and failed["currentCustody"] == predecessor
            and failed["firstFailure"] == {"type": "ValueError", "message": "linked-ui actual method failed"},
            "Original actual failed method or custody changed")
    stage = failed["stages"]["linked-ui"]
    require(stage["status"] == "FAIL" and stage["testInvoked"] is True
            and stage["command"]["exitCode"] == 65 and stage["command"]["ownedGroupPresentAfterExit"] is False
            and stage["command"]["logSHA256"] == "c2b13c8bb71ec7db38fc0f3acdef90972b7b7f642be93eefe0c53fe0a290d898"
            and c.digest(LONG_PRESS_CUSTODY / "commands/linked-ui-test/original.log") == stage["command"]["logSHA256"]
            and c.digest(LONG_PRESS_CUSTODY / "commands/linked-ui-test/started.json") ==
                failed["actualInvocationStartedEvidence"]["linked-ui"]["sha256"],
            "Original actual failed UI command/start/stdout changed")
    summary_path = LONG_PRESS_CUSTODY / "evidence/linked-ui/summary.json"
    require(c.digest(summary_path) == "dff0d0d66adcdf6886df5d77e7761778c825f080fc4027af6ff7186894eafbbb",
            "Original actual failed UI summary changed")
    summary = decode(c.raw(summary_path))
    require(summary["totalTestCount"] == summary["failedTests"] == 1
            and summary["passedTests"] == summary["skippedTests"] == 0
            and len(summary["testFailures"]) == 1
            and summary["testFailures"][0]["testIdentifierString"] ==
                "SemanticAnchorPage154MountedUITests/testExistingSemanticAnchorSourceLinkEditAndColdReopen()"
            and "source-menu-not-ready" in summary["testFailures"][0]["failureText"],
            "Original long-press failure is not the exact actual method")
    trace_path = LONG_PRESS_CUSTODY / "evidence/linked-ui/private-attachments/FA4CEB75-B085-4A14-A4E6-66D319C4B737.json"
    require(c.digest(trace_path) == "fdbe5032b040c0ffb4ef493906783ac04b672406efcdaa1a02b76b7579211bc1",
            "Original zero-action menu trace changed")
    trace = decode(c.raw(trace_path))
    require(trace["protocol"] == "pinkha-semantic-source-menu-v1" and trace["status"] == "FAIL"
            and trace["sourceActionTaps"] == trace["nextPageTaps"] == 0
            and all(trace[k] == v for k, v in prior["binding"].items())
            and failed["uiDerivative"]["uiReceiptSHA256"] ==
                "28d3bc506c76b4e537f7de97c9b95ce8087a7079de9d6f5f8ad00f476a0fff2a"
            and failed["uiDerivative"]["uiTestChangeCommit"] == "bfc5646efcaea558190ae5aa55d76b13fe5624d5",
            "Original failed UI source or zero-action trace changed")
    require(failed["originalFixtureSHA256"] == ORIGINAL_FIXTURE
            and failed["priorExecutionSHA256"] == PRIOR_EXECUTION and failed["priorBackupSHA256"] == PRIOR_BACKUP
            and failed["originalFixtureExpiryUnix"] ==
                decode(c.raw(PRIOR / "private/final-sandbox-originals" / c.FIXTURE))["createdAt"] + 978307200 + 7200,
            "Original prepared fixture or expiry changed")
    require(not any((LONG_PRESS_CUSTODY / "commands" / (name + "-test") / "started.json").exists()
                    for name in ("linked-native", "unlinked-ui", "unlinked-native")),
            "An unreported later original method was invoked")
    cleanup = failed["cleanup"]
    require(cleanup["status"] == "PASS" and cleanup["errors"] == []
            and cleanup["ownedSimulatorDeleted"] is False
            and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
            and all(row.get("absentAtOriginalExit") is True and row.get("historicalGroupReprobed") is False
                    for row in cleanup["groups"]), "Original failed UI cleanup is incomplete")
    for name, row in prior["finalPrivateSandbox"]["files"].items():
        require(failed["finalPrivateSandbox"]["files"][name] == row,
                "Original mounted witness status changed after long press")
        if row["status"] == "COPIED_ORIGINAL":
            require(c.digest(LONG_PRESS_CUSTODY / "private/final-sandbox-originals" / name) == row["sha256"],
                    "Original mounted witness bytes changed after failed selection")
    completion_path = LONG_PRESS_CUSTODY / "evidence/retention-completion.json"
    require(c.digest(completion_path) == LONG_PRESS_CUSTODY_COMPLETION
            and c.digest(LONG_PRESS_CUSTODY / "private/owned-account-originals/retention.json") == LONG_PRESS_CUSTODY_BACKUP
            and c.digest(LONG_PRESS_CUSTODY / "private/owned-account-originals/device.plist") == LONG_PRESS_CUSTODY_PLIST,
            "Exact current failed UI full-account custody required")
    completion = decode(c.raw(completion_path))
    require(completion["executionSHA256"] == LONG_PRESS_CUSTODY_EXECUTION
            and completion["devicePlistSHA256"] == LONG_PRESS_CUSTODY_PLIST
            and completion["privateAccount"] == decode(c.raw(LONG_PRESS_CUSTODY / "private/owned-account-originals/retention.json"))
            and completion["fullEAcceptance"] is False, "Failed UI custody cannot become acceptance")
    return {"executionSHA256": LONG_PRESS_CUSTODY_EXECUTION, "backupSHA256": LONG_PRESS_CUSTODY_BACKUP,
            "devicePlistSHA256": LONG_PRESS_CUSTODY_PLIST, "methodsInvoked": 1,
            "status": "RETAINED_ORIGINAL_LONG_PRESS_UI_FAILURE_NOT_ACCEPTANCE"}

def admit_shutdown_account(commands, prior):
    directory = LONG_PRESS_CUSTODY / "private/owned-account-originals"
    c.require(c.digest(directory / "retention.json") == LONG_PRESS_CUSTODY_BACKUP, "Exact original account seal required")
    backup = c.decode(c.raw(directory / "retention.json"))
    c.require(backup["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
              and backup["executionSHA256"] == LONG_PRESS_CUSTODY_EXECUTION and backup["device"] == DEVICE
              and backup["fixtureDeadlineChanged"] is False and backup["restoredFixtures"] == 0,
              "Original backup identity/scope differs")
    log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], "admit-owned-shutdown", 30)
    matches = [row for row in c.decode(c.raw(log))["devices"].get(c.RUNTIME, []) if row.get("udid") == DEVICE]
    c.require(len(matches) == 1 and matches[0]["state"] == "Shutdown"
              and matches[0]["name"] == "E-Combined-Heart-" + prior["binding"]["nonce"]
              and matches[0]["deviceTypeIdentifier"] == c.DEVICE, "Exact original owned shutdown device required")
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    c.require(device_root.resolve() == device_root and device_root.is_dir()
              and c.digest(device_root / "device.plist") == c.digest(directory / "device.plist"),
              "Original device metadata changed since seal")
    def identity(path):
        entry = os.lstat(path)
        c.require(path.resolve() == path and not stat.S_ISLNK(entry.st_mode), "Owned root became an alias")
        return (entry.st_dev, entry.st_ino, entry.st_mode)
    root_identity = identity(device_root)
    plist_identity = identity(device_root / "device.plist")
    plist_sha256 = c.digest(directory / "device.plist")
    def require_same_shutdown(stage):
        c.require(device_root.resolve() == device_root and device_root.is_dir()
                  and identity(device_root) == root_identity
                  and identity(device_root / "device.plist") == plist_identity
                  and c.digest(device_root / "device.plist") == plist_sha256,
                  "Original sealed device was replaced or its metadata changed")
        log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], stage, 30)
        rows = [row for row in c.decode(c.raw(log))["devices"].get(c.RUNTIME, []) if row.get("udid") == DEVICE]
        c.require(len(rows) == 1 and rows[0]["state"] == "Shutdown"
                  and rows[0]["name"] == "E-Combined-Heart-" + prior["binding"]["nonce"]
                  and rows[0]["deviceTypeIdentifier"] == c.DEVICE,
                  "The sealed owned device changed state during admission")
        for label, live in roots.items():
            expected = root_identities[label]
            if expected is None:
                c.require(not live.exists() and not live.is_symlink(), "Absent account root appeared")
            else:
                c.require(identity(live) == expected, "Original private account root was replaced")
    command_root = LONG_PRESS_CUSTODY / "commands/final-private-sandbox-container"
    command = c.decode(c.raw(command_root / "result.json"))
    c.require(command["argv"] == ["xcrun", "simctl", "get_app_container", DEVICE, "io.anytype.app", "data"]
              and command["status"] == "PASS_COMMAND" and command["exitCode"] == 0
              and command["logSHA256"] == c.digest(command_root / "original.log"),
              "Original observed app container command differs")
    app = Path(c.raw(command_root / "original.log").decode().strip())
    c.require(app.resolve() == app and app.parent == device_root / "data/Containers/Data/Application",
              "Original account container is not canonical")
    roots = {"application-data": app, "shared-app-groups": device_root / "data/Containers/Shared/AppGroup",
             "keychains": device_root / "data/Library/Keychains", "device-preferences": device_root / "data/Library/Preferences"}
    root_identities = {name: identity(live) if live.exists() else None for name, live in roots.items()}
    for name, live in roots.items():
        require_same_shutdown("admit-before-" + name)
        row = backup["scopes"][name]
        if row["status"] == "NOT_PRESENT":
            c.require(not live.exists() and not live.is_symlink(), "An absent owned scope appeared")
            require_same_shutdown("admit-after-absent-" + name)
            continue
        manifest = directory / (name + "-before.json")
        c.require(c.digest(manifest) == row["manifestSHA256"], "Original account manifest changed")
        expected = c.decode(c.raw(manifest))
        c.require(account.inventory(live) == expected == account.inventory(directory / name),
                  "The live original account or sealed backup changed")
        require_same_shutdown("admit-after-" + name)
    require_same_shutdown("admit-final-original-shutdown")
    return {"status": "EXACT_SEALED_ORIGINAL_SHUTDOWN_ACCOUNT", "backupSHA256": LONG_PRESS_CUSTODY_BACKUP,
            "devicePlistSHA256": plist_sha256, "deviceRootIdentityUnchanged": True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--controller-sha256", required=True)
    parser.add_argument("--ui-admission", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o022)  # Preserve original product modes inside the private root.
    own = Path(__file__).resolve().parent
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon required")
    require(c.digest(Path(__file__)) == args.controller_sha256 and c.digest(Path(c.__file__)) == CORE
            and c.digest(Path(account.__file__)) == RETENTION,
            "Exact reviewed continuation, core and private retention required")
    require(args.admission.is_absolute() and args.admission.resolve() == args.admission
            and c.digest(args.admission) == ADMISSION, "Exact original App14 E admission required")
    admission = decode(c.raw(args.admission))
    require(admission["controllerSHA256"] == CORE and admission["sourceCommit"] == SOURCE
            and admission["nativeManifestSHA256"] == c.MANIFEST and admission["heartOverlaySHA256"] == c.OVERLAY,
            "Actual combined source/runtime admission differs")
    selection_helper = own / "replacement_selection_observation.py"
    require(c.digest(selection_helper) == c.REPLACEMENT_SELECTION_OBSERVATION_HELPER,
            "Exact reviewed passive selection observation required")
    route_helper = own / "semantic_link_route_observation.py"
    require(c.digest(route_helper) == c.SEMANTIC_LINK_ROUTE_HELPER, "Exact original real-link observer required")
    require(c.digest(Path(ui_profile.__file__)) == UI_PROFILE and c.digest(args.ui_admission) == UI_ADMISSION,
            "Exact reviewed UI-only pairing required")
    ui_admission = decode(c.raw(args.ui_admission))
    inverse = copy.deepcopy(ui_admission)
    require("directMenuUIOverride" in inverse, "Explicit changed UI provenance required")
    inverse.pop("directMenuUIOverride")
    inverse["products"]["ui"] = admission["products"]["ui"]
    require(inverse == admission, "Only exact derivative UI products/profile may differ")
    ui_proof = ui_profile.qualify(c, ui_admission, Path(admission["sourceRoot"]),
                                 decode(c.pinned(admission["producerReceipt"])))
    prior = admit_prior(admission)
    predecessor = admit_failed_controller(prior)
    previous_custody = admit_failed_witness_copy(prior, predecessor)
    direct_custody = admit_failed_direct_selection(prior, previous_custody)
    custody = admit_failed_long_press(prior, direct_custody)
    require(args.root.is_absolute() and args.root.parent == PRIOR.parent
            and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
            "Fresh separately owned continuation root required")
    args.root.mkdir(mode=0o700)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", c.raw(args.admission))
    c.write_bytes(evidence / "original-preparation-execution.json", c.raw(PRIOR / "evidence/execution.json"))
    commands = c.Commands(args.root / "commands", args.root)
    built = {}; boot_owned = False
    binding = prior["binding"]
    device = DEVICE
    result = {"status": "FAIL", "protocol": "pinkha-app14-original-mounted-direct-menu-four-stage-continuation-v1",
              "executionEnvironment": "SentinelX-owned-Mac", "sourceCommit": SOURCE,
              "controllerSHA256": args.controller_sha256, "coreControllerSHA256": CORE,
              "observationHelperSHA256": c.OBSERVATION_HELPER,
              "nativeManifestSHA256": c.MANIFEST, "heartOverlaySHA256": c.OVERLAY,
              "ownedSimulator": DEVICE, "binding": binding, "stages": {},
              "priorExecutionSHA256": PRIOR_EXECUTION, "priorBackupSHA256": PRIOR_BACKUP,
              "currentCustody": custody,
              "originalPreparationReused": {"path": str(PRIOR), "actual": prior["stages"]["preparation"]["actual"],
                                            "executedInThisContinuation": False},
              "originalMountedReused": {"path": str(PRIOR), "actual": prior["stages"]["mounted"]["actual"],
                                        "executedInThisContinuation": False},
              "originalLinkedUIFailureRetained": True, "uiDerivative": ui_proof,
              "appBuilds": 0, "nativeBuilds": 0, "uiBuilds": 0, "factoryMethodsExecuted": 0,
              "preparationMethodsReexecuted": 0, "fixtureRestorations": 0, "fixtureDeadlineChanges": 0,
              "newSimulatorsCreated": 0, "fullEAcceptance": False, "physicalDevice": "NOT_RUN",
              "startedAt": time.time()}
    try:
        result["accountAdmission"] = admit_shutdown_account(commands, prior)
        product_mask = os.umask(0)
        try:
            result["sourceAdmission"], built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
            original_ui = built["ui"]["products"]
            original_ui.rename(args.root / "original-complete-ui-products")
            ui_row = ui_admission["products"]["ui"]
            ui_manifest = decode(c.pinned(ui_row["manifest"]))
            require(c.inventory(Path(ui_row["root"])) == ui_manifest, "Original derivative UI products changed")
            destination = args.root / "ui-products"
            commands.run(["cp", "-cR", ui_row["root"], str(destination)], "clone-direct-menu-ui", 180)
            require(c.inventory(destination) == ui_manifest, "Derivative UI clone differs")
            descriptor = destination / ui_row["descriptorRelativePath"]
            require(descriptor.parent == destination and c.digest(descriptor) == ui_row["descriptorSHA256"],
                    "Actual derivative descriptor changed")
            built["ui"] = {"products": destination, "inventory": ui_manifest, "copies": {},
                           "descriptor": descriptor, "originalSelection": ui_row["originalSelection"]}
        finally:
            os.umask(product_mask)
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        c.common = importlib.import_module("contracts")
        native = c.native = importlib.import_module("consumer_contract")
        mounted = c.mounted = importlib.import_module("mounted_contract")
        boundary = c.boundary = importlib.import_module("page154_boundary")
        policy = importlib.import_module("page154_contract")
        warning = importlib.import_module("warning_profile")
        specialized = importlib.import_module("combined_heart_observations_gateway")
        require(c.digest(Path(specialized.__file__)) == c.OBSERVATION_HELPER
                and specialized.COMBINED_VERSION == c.VERSION and specialized.ORIGINAL_OVERLAY == c.OVERLAY,
                "Exact original combined observation authority required")
        native.binding(binding)
        fixture_raw = c.raw(PRIOR / "private/final-sandbox-originals" / c.FIXTURE)
        require(sha(fixture_raw) == ORIGINAL_FIXTURE, "Original prepared fixture changed")
        fixture = decode(fixture_raw)
        mounted.fixture(fixture, binding)
        result["originalFixtureSHA256"] = ORIGINAL_FIXTURE
        result["originalFixtureCreatedAt"] = fixture["createdAt"]
        result["originalFixtureExpiryUnix"] = fixture["createdAt"] + 978307200 + 7200
        # Claim cleanup ownership before boot: a post-exit infrastructure error
        # must still shut down this positively admitted original device.
        boot_owned = True
        commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-owned-device", 60)
        commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-owned-boot", 180)
        actual_fixture = c.app_file(commands, DEVICE, private, c.FIXTURE, "original-live-fixture", 65536)
        require(actual_fixture == fixture_raw, "Live original prepared fixture differs after boot")
        mounted.fixture(decode(actual_fixture), binding)
        # All original mounted witnesses must remain byte-identical after the failed menu.
        prior_witnesses = private / "original-mounted-witnesses"
        prior_witnesses.mkdir(mode=0o700)
        for witness_index, filename in enumerate((c.CAPTURE, c.REOPEN, *boundary.FILES.values())):
            expected = c.raw(PRIOR / "private/final-sandbox-originals" / filename, boundary.MAXIMUM)
            actual = app_file(commands, DEVICE, prior_witnesses, filename, "preserve-prior-" + str(witness_index), boundary.MAXIMUM)
            require(actual == expected and sha(expected) == prior["finalPrivateSandbox"]["files"][filename]["sha256"],
                    "Original mounted witness changed since the actual pass")
        base = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            base["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        def run(name, additions):
            require(name in ("linked-ui", "linked-native", "unlinked-ui", "unlinked-native"),
                    "Only the four original source stages are allowed")
            mounted.fixture(fixture, binding)
            kind = "app" if STAGES[name].startswith("AnytypeTests/") else "ui"
            value = c.stage(commands, evidence, name, built[kind], app, binding, device, dict(base, **additions))
            result["stages"][name] = value
            require(value["status"] == "PASS", name + " actual method failed")

        ui_env = {"PINKHA_SEMANTIC_MOUNTED_TESTING": "1", "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": fixture_raw.decode()}
        capture_raw = app_file(commands, device, private, CAPTURE, "preserve-capture", 65536)
        reopen_raw = app_file(commands, device, private, REOPEN, "preserve-reopen", 65536)
        capture, reopen = decode(capture_raw), decode(reopen_raw)
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        witness = capture.get("nativeBoundaryEvidence")
        require(isinstance(witness, dict) and witness.get("protocolVersion") == 1 and witness.get("extraNativeCalls") == 0
                and witness.get("source") == "actual-client-call-results" and set(witness["files"]) == set(boundary.FILES), "original three native boundaries required")
        boundaries = {}
        for role, filename in boundary.FILES.items():
            row = witness["files"][role]
            require(row["filename"] == filename, "native boundary filename differs")
            payload = app_file(commands, device, private, filename, "preserve-boundary-" + role.lower(), boundary.MAXIMUM)
            require(len(payload) == row["bytes"] and sha(payload) == row["sha256"], "native boundary original hash differs")
            boundaries[role] = payload
        result["nativeBoundaryComparison"] = boundary.verify(boundaries, fixture, capture, native, mounted)
        require(result["nativeBoundaryComparison"]["projectionFieldCount"] == 9, "full original nine-field projection required")
        result["originalAttachments"] = policy.mounted_attachments(PRIOR / "evidence/mounted/private-attachments", device, capture, reopen, binding, warning)
        write(evidence / "actual-mounted-qualified.json", {"binding": binding, "mounted": result["mountedProof"], "boundary": result["nativeBoundaryComparison"]})
        source_env = {"PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256": sha(fixture_raw)}
        for key, payload in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = payload.decode()
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = sha(payload)
        previous, previous_raw = None, None
        for phase in ("linked", "unlinked"):
            if previous_raw is not None:
                source_env["PINKHA_SEMANTIC_SOURCE_LINKED_READBACK_SHA256"] = sha(previous_raw)
            run(phase + "-ui", dict(ui_env, **source_env, PINKHA_SEMANTIC_SOURCE_UI_PHASE=phase))
            ui_raw, ui_origin = policy.attachment(evidence / (phase + "-ui") / "private-attachments", "heart-semantic-source-ui-" + phase,
                                                STAGES[phase + "-ui"], device, maximum=65536)
            result[phase + "UIProof"] = continuation_ui(decode(ui_raw), phase, fixture, capture, capture_raw, reopen_raw)
            import semantic_link_route_observation as route_observation
            require(Path(route_observation.__file__).resolve() == route_helper.resolve(), "Foreign real-link route observer")
            result[phase + "RealLinkRouteProof"] = route_observation.qualify_routes(
                c, policy, evidence / (phase + "-ui") / "private-attachments",
                STAGES[phase + "-ui"], device, phase, binding)
            if phase == "linked":
                import replacement_selection_observation as selection_observation
                require(Path(selection_observation.__file__).resolve() == selection_helper.resolve(),
                        "Foreign passive selection observation module")
                result["replacementSelectionProof"] = selection_observation.qualify_selection(
                    c, policy, commands, evidence, private, device, fixture, binding)
            native_env = dict(source_env, PINKHA_SEMANTIC_SOURCE_READBACK_PHASE=phase,
                              PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_JSON=ui_raw.decode(), PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_SHA256=sha(ui_raw))
            run(phase + "-native", native_env)
            native_raw = app_file(commands, device, private, "pinkha-semantic-source-" + phase + "-native-readback.json", "preserve-" + phase + "-readback")
            attached, origin = policy.attachment(evidence / (phase + "-native") / "private-attachments", "heart-semantic-source-native-" + phase,
                                                 STAGES[phase + "-native"], device, maximum=65536)
            value = decode(native_raw)
            proof = continuation_native(value, decode(attached), native_raw, phase, fixture, capture, fixture_raw, capture_raw, reopen_raw, ui_raw, previous)
            result[phase + "NativeProof"] = proof
            write(evidence / (phase + "-independent-native-qualified.json"), proof)
            previous, previous_raw = value, native_raw

        require(set(result["stages"]) == {"linked-ui", "linked-native", "unlinked-ui", "unlinked-native"}
                and all(row["status"] == "PASS" and row["testInvoked"] is True for row in result["stages"].values()),
                "All four actual continuation methods are required")
        result["status"] = "PASS_FOUR_ACTUAL_METHODS_WITH_ORIGINAL_PREPARATION_AND_MOUNTED"
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        errors = []
        if boot_owned:
            try:
                # The original preparation already ran the actual application.
                # A later stage exception cannot make this account optional.
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, DEVICE,
                    private / "final-sandbox-originals", application_invoked=True)
            except BaseException as exc: errors.append({"phase": "private-retention", **c.error(exc)})
            try:
                _, stopped = commands.run(["xcrun", "simctl", "shutdown", DEVICE], "shutdown-owned-device", 60,
                                           checked=False, capacity=False)
                require(stopped["exitCode"] == 0, "Owned shutdown failed")
            except BaseException as exc: errors.append({"phase": "shutdown", **c.error(exc)})
        try:
            result["finalProducts"] = {name: c.product_integrity(row) for name, row in built.items()}
            if built:
                for name, expected in c.HELPERS.items():
                    require(c.digest(args.root / "helpers" / name) == expected, "Original pure helper changed")
        except BaseException as exc: errors.append({"phase": "product-helper-integrity", **c.error(exc)})
        groups = []
        for group in commands.groups:
            if group in commands.absent_groups:
                groups.append({"pgid": group, "absentAtOriginalExit": True, "historicalGroupReprobed": False})
                continue
            try:
                present = c.Commands.present(group)
                groups.append({"pgid": group, "present": present})
                if present: errors.append({"phase": "owned-group-still-present", "pgid": group})
            except BaseException as exc: errors.append({"phase": "owned-group-state-unavailable", "pgid": group, **c.error(exc)})
        result["cleanup"] = {"status": "PASS" if not errors else "FAIL", "errors": errors, "groups": groups,
            "ownedSimulatorDeleted": False, "ownedSimulatorRetainedForRecovery": DEVICE}
        if errors: result["status"] = "FAIL"
        invoked = {name for name, row in result["stages"].items() if row.get("testInvoked") is True}
        started_evidence = {}
        for name in ("linked-ui", "linked-native", "unlinked-ui", "unlinked-native"):
            started = args.root / "commands" / (name + "-test") / "started.json"
            if started.is_file():
                invoked.add(name)
                started_evidence[name] = {"sha256": c.digest(started), "selector": STAGES[name]}
        result["actualMethodsInvokedInThisContinuation"] = len(invoked)
        result["actualInvocationStartedEvidence"] = started_evidence
        result["finishedAt"] = time.time()
        write(evidence / "execution.json", result)
    seal = {"status": "NOT_SEALED", "executionSHA256": c.digest(evidence / "execution.json"),
            "originalPreparationExecutionSHA256": PRIOR_EXECUTION, "fullEAcceptance": False}
    if boot_owned and result["cleanup"]["status"] == "PASS":
        try:
            seal["privateAccount"] = account.retain(args.root, seal["executionSHA256"])
            seal["retentionSHA256"] = c.digest(private / "owned-account-originals/retention.json")
            seal["devicePlistSHA256"] = c.digest(private / "owned-account-originals/device.plist")
            seal["status"] = "SEALED_FOUR_STAGE_CONTINUATION_ACCOUNT_NOT_FULL_E"
        except BaseException as exc: seal["firstFailure"] = c.error(exc)
    write(evidence / "retention-completion.json", seal)
    print(json.dumps({"status": result["status"], "actualStages": {k:v["status"] for k,v in result["stages"].items()},
                      "firstFailure": result.get("firstFailure"), "retention": seal["status"]}, sort_keys=True))
    return 0 if result["status"] == "PASS_FOUR_ACTUAL_METHODS_WITH_ORIGINAL_PREPARATION_AND_MOUNTED" and seal["status"] == "SEALED_FOUR_STAGE_CONTINUATION_ACCOUNT_NOT_FULL_E" else 1


if __name__ == "__main__":
    raise SystemExit(main())
