"""Owned diagnostic of public UIKit hit testing; no tap, source capture or native engine request."""
import hashlib, json, subprocess, time
from pathlib import Path
import lldb

MAIN = "a0158826af42d9fb36d4faa2caca2bd01d1f01916aaeadce79e40d4581f5a2a2"
IMAGE = "dcb8ac76d496f524b6c0715b5b699242c5a877173e850ce4ab3a6cfec6d8014b"
EXPRESSION = r"""({
    NSMutableArray *pinkhaWindows = [NSMutableArray array];
    for (UIWindow *pinkhaWindow in [UIApplication sharedApplication].windows) {
        if (!pinkhaWindow.isKeyWindow || pinkhaWindow.isHidden) continue;
        CGRect pinkhaBounds = pinkhaWindow.bounds;
        NSMutableDictionary *pinkhaRow = [NSMutableDictionary dictionaryWithDictionary:@{
            @"class": NSStringFromClass([pinkhaWindow class]),
            @"frame": NSStringFromCGRect(pinkhaWindow.frame),
            @"bounds": NSStringFromCGRect(pinkhaBounds),
            @"hidden": @(pinkhaWindow.isHidden), @"alpha": @(pinkhaWindow.alpha),
            @"interaction": @(pinkhaWindow.isUserInteractionEnabled)
        }];
        if (pinkhaBounds.origin.x == 0 && pinkhaBounds.origin.y == 0 &&
            pinkhaBounds.size.width == 1032 && pinkhaBounds.size.height == 1376) {
            UIView *pinkhaHit = [pinkhaWindow hitTest:CGPointMake(516,174) withEvent:nil];
            NSMutableArray *pinkhaChain = [NSMutableArray array];
            for (UIView *pinkhaView = pinkhaHit; pinkhaView != nil && pinkhaChain.count < 40; pinkhaView = pinkhaView.superview) {
                [pinkhaChain addObject:@{
                    @"class": NSStringFromClass([pinkhaView class]),
                    @"frame": NSStringFromCGRect(pinkhaView.frame),
                    @"bounds": NSStringFromCGRect(pinkhaView.bounds),
                    @"windowBounds": NSStringFromCGRect([pinkhaView convertRect:pinkhaView.bounds toView:pinkhaWindow]),
                    @"hidden": @(pinkhaView.isHidden), @"alpha": @(pinkhaView.alpha),
                    @"interaction": @(pinkhaView.isUserInteractionEnabled)
                }];
            }
            pinkhaRow[@"hitTestPerformed"] = @YES;
            pinkhaRow[@"hitChain"] = pinkhaChain;
            NSMutableArray *pinkhaSiblings = [NSMutableArray array];
            for (UIView *pinkhaView in pinkhaHit.superview.subviews) {
                if (pinkhaSiblings.count >= 40) break;
                [pinkhaSiblings addObject:@{
                    @"class": NSStringFromClass([pinkhaView class]),
                    @"frame": NSStringFromCGRect(pinkhaView.frame),
                    @"windowBounds": NSStringFromCGRect([pinkhaView convertRect:pinkhaView.bounds toView:pinkhaWindow]),
                    @"hidden": @(pinkhaView.isHidden), @"alpha": @(pinkhaView.alpha),
                    @"interaction": @(pinkhaView.isUserInteractionEnabled)
                }];
            }
            pinkhaRow[@"hitSuperviewChildren"] = pinkhaSiblings;
        } else {
            pinkhaRow[@"hitTestPerformed"] = @NO;
        }
        [pinkhaWindows addObject:pinkhaRow];
    }
    NSData *pinkhaJSON = [NSJSONSerialization dataWithJSONObject:@{
        @"pointX": @516, @"pointY": @174, @"keyWindows": pinkhaWindows
    } options:NSJSONWritingSortedKeys error:NULL];
    (const char *)[[[NSString alloc] initWithData:pinkhaJSON encoding:NSUTF8StringEncoding] UTF8String];
})"""

def run(debugger, config_path):
    config = json.loads(Path(config_path).read_bytes())
    output = Path(config["output"])
    executable = Path(config["executable"])
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / config["device"]
    if executable.resolve() != executable or not executable.is_relative_to(owner) or executable.name != "Anytype":
        raise ValueError("Exact owned installed app required")
    if subprocess.check_output(["ps", "-p", str(config["pid"]), "-o", "comm="], text=True, timeout=5).strip() != str(executable):
        raise ValueError("Owned app process changed")
    for path, pin in ((executable, MAIN), (executable.with_name("Anytype.debug.dylib"), IMAGE)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin: raise ValueError("Original ca7 binary changed")
    result = {"protocol": "pinkha-owned-uikit-hit-test-diagnostic-v1", "status": "STARTING",
              "diagnosticOnly": True, "pid": config["pid"], "device": config["device"],
              "mainSHA256": MAIN, "imageSHA256": IMAGE, "normalAppLaunches": 1,
              "explicitNativeEngineCalls": 0, "sourceCaptureCalls": 0, "taps": 0,
              "fixtureDeadlineChanges": 0, "targetExpressions": 0,
              "expressionSHA256": hashlib.sha256(EXPRESSION.encode()).hexdigest(),
              "startedAt": time.time()}
    process = None
    try:
        debugger.SetAsync(True)
        command = lldb.SBCommandReturnObject()
        debugger.GetCommandInterpreter().HandleCommand("settings set symbols.enable-external-lookup false", command)
        if not command.Succeeded(): raise ValueError(command.GetError())
        target = debugger.CreateTarget(str(executable))
        listener = lldb.SBListener("pinkha-owned-uikit-hit-test")
        error = lldb.SBError()
        process = target.AttachToProcessWithID(listener, config["pid"], error)
        if error.Fail() or not process.IsValid(): raise RuntimeError("Attach failed: " + str(error))
        module = [m for m in target.modules if m.GetFileSpec().GetFilename() == "Anytype.debug.dylib"]
        if len(module) != 1 or str(module[0].GetFileSpec()) != str(executable.with_name("Anytype.debug.dylib")):
            raise ValueError("Wrong loaded original app image")
        threads = [t for t in process if t.GetQueueName() == "com.apple.main-thread"]
        if len(threads) != 1: raise ValueError("Exact UIKit main queue required")
        thread = threads[0]
        process.SetSelectedThread(thread)
        frame = thread.GetFrameAtIndex(0)
        if not frame.IsValid(): raise ValueError("Actual main frame unavailable")
        options = lldb.SBExpressionOptions()
        options.SetLanguage(lldb.eLanguageTypeObjC_plus_plus)
        options.SetPrefix("@import UIKit;")
        options.SetTimeoutInMicroSeconds(5_000_000)
        options.SetUnwindOnError(True)
        options.SetIgnoreBreakpoints(True)
        options.SetTryAllThreads(True)
        options.SetStopOthers(True)
        result["mainQueueSelected"] = True
        result["targetExpressions"] = 1
        result["evaluationStartedAt"] = time.time()
        value = frame.EvaluateExpression(EXPRESSION, options)
        result["evaluationFinishedAt"] = time.time()
        if value.GetError().Fail(): raise RuntimeError("UIKit expression failed: " + str(value.GetError()))
        address = value.GetValueAsUnsigned()
        if not address: raise RuntimeError("UIKit diagnostic returned no JSON")
        error = lldb.SBError()
        text = process.ReadCStringFromMemory(address, 65536, error)
        if error.Fail(): raise RuntimeError("UIKit JSON read failed: " + str(error))
        observation = json.loads(text)
        if len(observation["keyWindows"]) != 1 or observation["keyWindows"][0]["hitTestPerformed"] is not True:
            raise ValueError("Original portrait key-window geometry differs")
        result["observation"] = observation
        result["status"] = "UIKIT_HIT_TEST_OBSERVED_NOT_ACCEPTANCE"
    except BaseException as exc:
        result["status"] = "DIAGNOSTIC_FAILED_NOT_PRODUCT_RESULT"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if process and process.IsValid() and process.GetState() not in (lldb.eStateExited, lldb.eStateDetached):
            error = process.Detach(False)
            result["detachedAndResumed"] = error.Success()
            if error.Fail():
                result["status"] = "DIAGNOSTIC_FAILED_NOT_PRODUCT_RESULT"
                result["detachError"] = str(error)
        result["finishedAt"] = time.time()
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        output.chmod(0o600)
