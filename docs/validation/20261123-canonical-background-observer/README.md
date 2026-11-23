# Canonical Anytype native background and observer continuation — 23 November 2026

## Evidence and correction

The actual canonical consumer run [45135961459](https://github.com/davidpovarsky/anytype-swift/actions/runs/45135961459), source fa078feb6bd496689b812ccf00945dce60c03599, built the app and passed its original preparation method (23.124 seconds). Its one UI method failed the original background-state assertion. The authenticated outer artifact is 14804841664, 50,398,716 bytes, SHA-256 738ac36ffbed82377ec625f8febf452cf407a7dc172da3e058c0d3a3689e34fe.

The original XCTest log records Home delivery at 09:28:58.873–09:28:59.365 UTC, followed by an actual RunningForeground state at the 09:29:09.381 wait timeout. The exact last video frame shows SpringBoard, but its presentation timestamp cannot establish that the original background admission completed before the assertion. The collected driver file was only written on phase transitions and therefore could predate real scene notifications. No app crash or passing later authority checks are inferred.

## Original UI harness

HanlinNativeAcceptanceUITests.swift keeps the actual Home button action. If Anytype remains foreground, it may activate the already-running real SpringBoard process. All post-Home actions and state waiting share one monotonic 10-second admission window; the final background state is still required before returning to Anytype. Foreground admission remains 20 seconds. There is no synthetic notification, app termination, extra app launch, substitute process, or changed authority assertion.

Full-screen XCTest attachments and JSON state observations record the native transition. No Anytype UI/receipt query is issued between Home and background admission. Pre-Home receipt values are explicitly labeled as such. The independent review corrected the screenshot call to the original public XCUIScreen.main.screenshot() API and required an immediate deadline recheck before optional SpringBoard activation.

PinkhaHanlinNativeAcceptanceDriver.swift persists actual UIKit notification observations, time and scene activation state. It leaves the current phase, checks and invalidation behavior unchanged. A persistence error retains its first diagnostic failure and remains subject to the original final failure assertion. The original driver's 45-second background wait is unchanged.

preserved-assertions.json binds the exact original top-level UI method, the native lifecycle operation body (apart from its comment), all 22 required checks, scene keys and original post-return PID/authority assertions. Swift parse receipts are syntax checks only, not native compilation or acceptance.

## Actual observer budget

In the original authenticated run, fresh installed-source verification took 28.080363 seconds and mapping took 16.649737 seconds. They consumed 44.730100 seconds of the original 45-second mapping admission before a required final container query, leaving 0.269900 seconds. The successful final export's container query took 0.559869 seconds. These named operation durations do not attribute all elapsed time to any individual subprocess.

The production observer changes only MAPPING_SECONDS = 45 to 60 and its explanatory comment. The original 420-second observation deadline still caps mapping; ordinary IPC remains capped at 10 seconds. Fresh installed-source and code-carrier hashes, before/after fixture/session/PID checks, actual runtime mapping, cancellation, native selectors and final qualification are unchanged. The existing derived worker join bound follows the mapping constant from 50 to 65 seconds; no unbounded wait is introduced.

test_canonical_native_observer_budget.py invokes the actual production observer and retained fixture helpers with a controllable monotonic clock and mocked simulator operations. It executes none of the original 69 test methods. The captured-duration case failed against the original complete observer at SHA e7c844559fbc7680cd2dbbe7c1eebb0561ecfb2f10305bef0f9b85e95665922c, then passed against the minimal repair. Two new methods / five cases passed in 0.534 seconds:

- Captured operations reach final binding, preserving two fresh source verifications and the mapped PID.
- Exhausted mapping budget rejects binding.
- The original 420-second deadline still rejects late mapping despite the larger local budget.
- Cancellation during mapping rejects binding.
- A late process replacement rejects binding.

The deterministic traces are controller evidence only. They do not establish a live simulator mapping or Apple acceptance.

## Retained controls and immutable scope

The current 69-control catalog comprises 68 methods with retained original proofs (61 prior methods plus the original seven qualified observer methods), and one actually requalified affected method. That method explicitly asserted the old tuple (10, 420, 45); its expected mapping value was changed to 60 and exactly this method passed again in 0.258 seconds, retaining its actual observer, deadline-diagnostic, mapped-PID and no-extra-launch checks. No other original method was rerun. The prior named PASS logs, source snapshots and original failed run are unchanged. The updated admission first reverses the exact reviewed constant/comment delta and proves the complete reconstructed observer is byte-identical to the original qualified source. It then separately requires the new current-source timing qualification, exact named two-method PASS log, five hashed case traces and the retained before-failure evidence. The changed original method has its own new source-bound PASS; the other 68 methods retain exact bodies and applicable prior proof. It does not claim that the old seven methods ran on the new constant. The new timing controls used the unchanged fixture helpers before the affected original method's expectation was updated; the exact whole-file inverse proves that this assertion is the only later fixture-file change.

A fresh import-only closure contains the same 28 original controller modules plus the unchanged profile JSON as the 29th bound input; zero methods ran during this observation. Five affected admission controls passed in 2.170 seconds after the final 68-retained/1-requalified policy update, including rejection of unreviewed observer/guard changes, forged policy hashes, changed supplemental control/log/trace, changed original logs and linked proof files. Native methods executed now: zero. The two successful new behavioral methods are separate from the 69-current-method catalog. Their existing results were reused after proving their used fixture helpers unchanged.

## Ownership and remaining gate

All edits are isolated to codex/chatgpt-wave15-canonical-hanlin-20261123. The original native diagnostic driver and UI test were introduced by downstream commit b08033462f9721f3fed8725cae3bd2e12bac9e1b; no upstream Anytype product engine, protocol or Heart code is changed. Source retention keeps the original baseline and updates only the exact reviewed driver replacement blob.

The other SDK06 owner's branch was read once at 9cafd32811e50f4e883efb034888d7ce1e349c02. Its production observer remains the same original e7c84455 source; no newer mapping-budget fix was available. Coordination is recorded in SDK06 continuation story 1220783879797775. Its active selector work and 23/32+ACK scope remain with that owner.

The canonical SDK pin remains d49a4fd4115b8335105d2991bf74ab4d7f6aad2d; all selected SDK sources and products are unchanged by this harness correction. The original qualified runtime producer remains 45091223011; no rebuild or substitute runtime is claimed. Current app build, native preparation1, UI1 and actual runtime mapping remain separate required acceptance. A single failed-scope retry may run only after the coherent source-bound candidate is reviewed.
