"""Passive selection observation only; the actual compiled UI producer remains pinned separately."""
def qualify_selection(c, policy, commands, evidence, private, device, fixture, binding):
    import math
    import re
    directory = evidence / "linked-ui/private-attachments"
    selector = c.STAGES["linked-ui"]
    raw, origin = policy.attachment(directory, "heart-semantic-source-replacement-selection",
                                    selector, device, maximum=65536)
    value = c.decode(raw)
    c.require(set(value) == {"protocol", "sourceSHA", "runID", "runAttempt", "nonce",
                            "selectionStartedUptime", "beforeTypingUptime", "expectedUTF16Length",
                            "expectedTextSHA256", "realCommandA", "programmaticSelectionChanges"}
              and value["protocol"] == "heart-semantic-source-real-replacement-selection-v1"
              and all(value[key] == binding[key] == fixture[key] for key in ("sourceSHA", "runID", "runAttempt", "nonce"))
              and type(value["expectedUTF16Length"]) is int and value["expectedUTF16Length"] == 6
              and value["expectedTextSHA256"] == c.sha(b"Anchor") and value["realCommandA"] is True
              and type(value["programmaticSelectionChanges"]) is int and value["programmaticSelectionChanges"] == 0,
              "Actual original-method real keyboard selection witness differs")
    start, end = value["selectionStartedUptime"], value["beforeTypingUptime"]
    c.require(all(type(x) in (int, float) and math.isfinite(x) for x in (start, end))
              and 0 < start < end and end - start <= 20,
              "A bounded actual selection-to-typing interval is required")
    ax, ax_origin = policy.attachment(directory, "heart-semantic-source-replacement-selection-ax",
                                      selector, device, maximum=256 * 1024)
    text = ax.decode()
    app_pids = set(re.findall(r"Application, [^\n]*\bpid: (\d+)", text))
    focused = re.findall(r"[^\n]*TextView,[^\n]*value: Anchor, Keyboard Focused[^\n]*", text)
    c.require(len(app_pids) == len(focused) == 1, "Exactly one focused original Anchor input and actual App PID required")
    pid = int(next(iter(app_pids)))
    observed = c.app_file(commands, device, private, "pinkha-semantic-source-entry-" + str(pid) + ".json",
                          "preserve-real-replacement-native-selection", maximum=65536)
    trace = c.decode(observed)
    c.require(trace["protocol"] == "pinkha-heart-semantic-source-entry-observation-v1"
              and trace["processID"] == pid and all(trace[key] == binding[key] for key in binding)
              and trace["capacityReached"] is False and trace["originalMountedObserverEnabled"] is False
              and trace["extraEngineCalls"] == trace["selectionChanges"] == trace["menuDismissals"]
              == trace["automaticRetries"] == 0, "Passive native input observation identity/scope differs")
    events = trace["events"]
    c.require(1 <= len(events) < 64 and all(type(e.get("uptime")) in (int, float)
              and math.isfinite(e["uptime"]) for e in events)
              and all(events[i]["uptime"] <= events[i+1]["uptime"] for i in range(len(events)-1)),
              "Original chronological untruncated native events required")
    interval = [e for e in events if start <= e["uptime"] <= end]
    selection = [e for e in interval if e["stage"] == "source-menu-input"]
    c.require(len(selection) >= 1, "Actual native full selection must be observed before typing")
    identities = {e["state"]["inputIdentity"] for e in selection}
    c.require(len(identities) == 1, "Selection observations came from different UIKit inputs")
    selected = next(iter(identities))
    post_selection = [e for e in interval if e["uptime"] >= selection[0]["uptime"]]
    relevant = [e for e in post_selection if e["stage"].startswith("input-")
                or e["stage"] == "source-menu-input" or "inputIdentity" in e["state"]]
    c.require(relevant and not any(e["stage"] in ("input-resign-before", "input-resign-after-super",
                                                "coordinator-invalidate") for e in post_selection),
              "The selected input resigned or its owner retired before actual typing")
    states = [e["state"] for e in relevant]
    c.require(all(s.get("inputIdentity") == selected and s.get("firstResponder") is True
              and s.get("windowPresent") is True and s.get("editable") is True
              and type(s.get("selectedLength")) is int and s["selectedLength"] == 6 for s in states),
              "Input identity, focus or full original six-unit selection changed before typing")
    c.require(len([e for e in events if e["stage"] == "source-menu-handler" and e["uptime"] < start]) == 1
              and not any(e["stage"] == "source-menu-handler" for e in interval),
              "The selection preparation unexpectedly reopened Sources")
    visual, visual_origin = policy.attachment(directory, "heart-semantic-source-replacement-selection-visual",
                                              selector, device, maximum=2 * 1024**2)
    return {"status": "PASS_REAL_KEYBOARD_SELECTION_WITH_PASSIVE_NATIVE_RANGE",
            "selectionWitnessSHA256": c.sha(raw), "nativeObservationSHA256": c.sha(observed),
            "nativeObservationBytes": len(observed), "beforeTypingAXSHA256": c.sha(ax),
            "visualSHA256": c.sha(visual), "actualAppPID": pid, "focusedInputCount": 1,
            "nativeFullRangeObservations": len(selection), "fullUTF16Length": 6,
            "locationZeroEvidence": "INFERRED_FROM_NATIVE_FULL_LENGTH_AND_EXACT_FOCUSED_AX_VALUE",
            "realCommandA": True, "programmaticSelectionChanges": 0, "extraEngineCalls": 0,
            "originalMethodOutcomeAssertionsChanged": False}
