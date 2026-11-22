# Any native editor responder handoff

## Observed failure and repair

Run `45031455896` built the native App and UI runner successfully at
`ef06a2c438104d1b47a715319bb78d31348edc04`. The original paragraph trace records
native creation, readback publication, and return from `addParagraph`. The
following accessibility query timed out before editor input.

The original spindump has SHA-256
`7a95235c01425c10644bcb8a781ce966bc84e75ba9ecc6271f8d0fc7f5c5f5ff`.
All 266 samples of the affected main/diffing thread contain
`updateUIViewController → render → diffable apply completion →
AnyNativeFocusCoordinator.readinessChanged` at the `becomeFirstResponder` call.
The thread consumed 4.925 CPU seconds during the five-second sample. UIKit
frames then recurse beneath that call. The Swift source-level recursion guard
does not prevent UIKit from being reentered while its snapshot update is still
on the stack.

The repair coalesces actual layout, attachment, and key-window events and
delivers one focus attempt on the next main-queue turn. Delivery is bound to a
unique intent and delivery ID. Owner, version, source, mounted scope, visibility,
and editability are still validated by the existing coordinator immediately
before using UIKit. New input, cancellation, and replacement invalidate the
queued handoff. Native refusal still requires a real attachment or key-window
event; there is no timer, polling, or layout-driven retry.

Both actual mounted editor request sites use `attemptImmediately: false`.
The direct synchronous coordinator method remains available to its existing
component fixtures, but actual controller layout/attachment/reveal callbacks
use the deferred delivery. The six original focus tests remain byte-identical.
Their key-window test already awaits the next turn after `makeKeyAndVisible`.

This is a source repair backed by an observed stack. Successful Apple component
execution and the unchanged real native editor journey are still required to
prove the repair resolves the product failure.

## Exact scope and validation

`ANY_NATIVE_FOCUS_HANDOFF_FILES.json` pins six owned source files, their original
Git blobs where applicable, and their new hashes. `SOURCE_IMPACT.json` names
the eight retained methods and the ten methods requiring actual execution.
The extracted 4,607-byte `AnyNativeTextView` declaration remains byte-identical
to the original producer. The old renderer, composition, Markdown, model, and
package dependency closure remains protected by the original reuse verifier.

Five new Python admission controls passed. They reject altered embedded text
view code, unreviewed focus/controller/dependency changes, changed case names,
old-fourteen relabeling, wrong counts, skips, duplicates, wrong simulator
identity, and a mismatched retained subset. Swift 6.3.3 on Windows accepted the
three Swift files in frontend parse mode. That is grammar validation only;
UIKit was neither typechecked nor executed there.

The required fresh Apple profile is `ui-ios-focus-handoff`, exactly ten
methods: six existing `AnyNativeFocusLifecycleTests` plus four new
`AnyNativeFocusHandoffTests`. The latter include an actual table diffable
snapshot completion, coalesced/reentrant events, owner/version/cancellation and
replacement checks, and native refusal followed by key-window readiness.

## Workflow calls

The subset verifier accepts the same flags as the original reuse command:

```sh
python3 Tools/AnyEnginePort/reuse_uikit_unaffected_eight.py \
  --evidence "$ORIGINAL_UIKIT_EVIDENCE" \
  --producer-commit 96173b0afc6b360c8f780ae70c6c80042fda98da \
  --producer-run 44942212731 \
  --consumer-simulator "$FOCUS_EVIDENCE/simulator.json" \
  --consumer-xcode-version "$FOCUS_EVIDENCE/xcode-version.txt" \
  --reviewed-source-changes Tools/AnyEnginePort/reviews/uikit14-unexecuted-source-changes-20261122.json \
  --output "$FOCUS_EVIDENCE/ui-ios-reuse.json"
```

It first verifies the complete original fourteen-method evidence. The new
receipt uses `scope=verified_prior_uikit_subset_reuse`, `status=VERIFIED_REUSE`,
`originalExecutedCount=14`, `reusedCount=8`, `testsExecutedThisRun=0`, and
`fullAcceptance=false`. The six affected methods are explicitly listed as not
reused. Original evidence is copied byte for byte to
`reused-ui-ios-unaffected-eight/`; its original fourteen counts are retained.
Two exact before/after Git-blob pairs and the embedded text-view digest qualify
the new repair. Other changes still go through the unchanged original
per-file review; there is no new directory exception.

After executing only the two focus suites and extracting the actual xcresult
summary and test tree:

```sh
python3 Tools/AnyEnginePort/verify_focus_handoff_execution.py \
  --udid "$OWNED_FOCUS_SIMULATOR" \
  --summary "$FOCUS_EVIDENCE/ui-focus-handoff-test-counts.json" \
  --tests "$FOCUS_EVIDENCE/ui-focus-handoff-test-methods.json" \
  --output "$FOCUS_EVIDENCE/ui-focus-handoff-named-execution.json"
```

The fresh verifier defaults the retained receipt to
`output.parent/ui-ios-reuse.json`; `--retained-eight PATH` can override it.
It requires that receipt to qualify the current consumer and binds its digest
into the new result. Actual summary/test-tree digests, test sources, changed
production sources, verifier sources, and the protected source tree are
recorded. Exactly ten passed methods on the owned arm64 iOS 27+ simulator are
required, with zero failures, skips, or unexpected cases. This receipt does not
replace the native entry, follow-up, or archive acceptance gates.
