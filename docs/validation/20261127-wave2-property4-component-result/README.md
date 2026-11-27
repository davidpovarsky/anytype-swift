# Property4: actual Linux component result

The four new `NativePropertyStoreTests` XCTest methods passed in one authorized Linux component run. The original runner receipt reports `PASS_FOUR_XCTEST_METHODS_PROPERTY_COMPONENT_ONLY`, exit 0, no errors and a safely released execution slot. This packet retains the actual result; its preparation does not execute the tests again.

The product source is `937a8167700481b71c3c2eeb8771634d2c6bbc4f`, with Store SHA256 `c653fa8489f7f9dc7d835d57ab4ec27be0bc46e189a29d226524d81e70e6db48` and complete test-file SHA256 `7ff24aed7ce350c368d9d5d5f31439c3c87566353842013948912001082492ca`. The unchanged preparation is `7e2c09a81434e287b2f3b434ccb1be141a1f1b99`. Its source files, input packet, controller, limits and historical preparation statements remain intact. [Preparation links](preparation-links.json) give their exact existing repository paths and hashes.

## Executed scope and outcome

The selected class compiled with all 17 declared methods. Only these four new methods ran; the original 13 were not selected. Looped fixture rows inside a method are not additional XCTest cases.

| Exact XCTest method in `PinkhaAnyHostTests.NativePropertyStoreTests` | Actual result | Logged method duration |
|---|---|---:|
| `testNestedStringAndKeyReadbackRequiresExactUTF8BeforeCreatingUndo` | PASS | 0.023 s |
| `testPropertyReceiptRetainsDocumentedNativeNormalizationAndUnsetRules` | PASS | 0.022 s |
| `testPropertyValueComparisonUsesTheExistingCanonicalDepthLimit` | PASS | 0.102 s |
| `testStringReadbackRequiresExactUTF8BeforeCreatingUndo` | PASS | 0.010 s |

The original XCTest suite summary is **4 tests, 0 failures, 0 unexpected failures, 0.158 seconds**. The verbose compiler log records **55.57 seconds** for the build; the runner records **58.703 seconds**; the enclosing job records **59.51 seconds**, from `2026-11-27T19:16:21.684030+00:00` to `2026-11-27T19:17:21.198735+00:00`. These are separate measurements, not alternative test durations. See [raw stdout](original-attempt/stdout.original.log), [raw stderr](original-attempt/stderr.original.log), [original receipt](original-attempt/receipt.json) and [original job notification](custody/original-job-notification.json).

The methods exercise the actual PropertyStore prepare, accepted-fence, materialize and receipt path with typed local fixtures: exact UTF-8 string and composite-key/value matching, permitted numeric/date/null/signed-zero behavior, and the existing depth limit. They do not perform HTTP apply/readback. No old Host2 method or HTTP fixture, Native engine operation, Apple test, mounted Properties journey or account operation ran. This result does not establish native serialization, account authority, persistence, mounted UI behavior, or admission of another product build.

## Actual compiler and dependency evidence

The original receipt contains all seven actual SwiftDriver argument lists and log lines, complete FileList text and hashes, output-map values and hashes, emitted-module hashes, object/source records, and both generated-input witnesses. The raw compiler log is retained separately and unchanged.

| Actual module | Object source inputs |
|---|---:|
| `TorahInspectorCore` | 8 |
| `PinkhaKit` | 12 |
| `PinkhaAnyEngine` | 15 |
| `PinkhaAnyIntegration` | 15 |
| `PinkhaAnyHost` | 27 |
| `PinkhaAnyHostTests` | 2: complete test file and generated test anchor |
| `PinkhaAnyHostTests_test_runner` | 1: generated test entry point |
| **Total** | **80: 77 whole production files, 1 complete test file, 2 generated inputs** |

There were no production-source body changes for the component. The source inventories before and after compilation are byte-identical; both original files are retained. The final inventory separately binds the immutable input copies and compiled copies. [Dependency custody](original-attempt/actual-dependency-copies.json) retains the 102 exact Crypto import/header/object identities and paths, totaling 19,775,715 logical bytes. This run does not replay or grant new acceptance to earlier dependency, Host2 or uploader test suites.

The full stderr includes a verbose Package manifest command line labelled `warning:`. No warning-free build claim is made, and no diagnostic is removed or rewritten.

## Original limits, closure and coordination

The unchanged command used jobs 2, no parallel test execution and a 300-second internal limit. Its original whole-owned-tree cap was 268,435,456 bytes, with a 1,048,576-byte final-evidence reserve; resource floors were 2,147,483,648 root bytes, 536,870,912 Development bytes and 536,870,912 available-memory bytes, plus the original 33,554,432-byte admission margin.

The receipt reports a maximum sampled owned allocation of **174,280,704 bytes**, minimum root free space of **2,356,305,920 bytes** and minimum Development free space of **7,314,071,552 bytes**. All original [resource samples](original-attempt/resource-samples.json) are retained. These observations do not constitute a whole-host filesystem audit.

The original cleanup observed its owned process group absent with `ABSENT_ESRCH` at `2026-11-27T19:17:20.842884+00:00`, and the original receipt sets `safeToReleaseRuntimeSlot=true`. That group is historical and closed; packet preparation performs no further process query or signal. [Dispatch custody](custody/dispatch.json) retains the explicit W1 grant, its diagnosis correction, upload hashes, readback and start. [Terminal-release custody](custody/terminal-release-comment.json) records the release to W1. The fixed launcher is also preserved; no controller or execution behavior is changed here.

## Original evidence and inspection history

The ten actual attempt files total **691,955 bytes** and are copied byte-for-byte once under `original-attempt/`. The raw final receipt is the single 370,302-byte file with SHA256 **`e025fbaf18eb23442d5bceba216874422795fabd34d9eb1eb0a0f28cac830d28`**. [Artifact index](artifact-index.json) records every original size/hash. The two identical before/after inventories remain separate because they are distinct original records.

The first post-run receipt read refused the receipt under an 80,000-byte inspection guard. Its exact [failure envelope](custody/first-read-size-guard-failure.json) is retained. This was an evidence-inspection failure after execution, not a test/compiler failure or another execution attempt. Root subsequently acquired the full receipt and all ten files through lossless, hash-verified transfer. [Transfer provenance](transfer-provenance.json) retains exact envelope hashes and metadata plus local decoded-byte comparisons; bulky encoded transfer bodies and the duplicate local receipt alias are not copied into this packet.

The [independent actual-result review](reviews/interfaces-independent-actual-review.json) accepted the four-case result, original source/dependency custody, actual compiler closure, resource records and original cleanup without rerunning the runner, tests or controls. Its earlier [local source-key inspection stop](reviews/interfaces-inspection-attempt1.json) is retained separately; that Package.swift grouping error was not an execution failure.

The [root actual-result review](reviews/root-actual-evidence-review.json) independently accepts the same four-method component scope and retains the exact original outcome. `result-summary.json` is a derived index, never a replacement for the original receipt. Final bundle review and any later publication custody are recorded separately. Assembling this packet changed no product, source, controller, limit or earlier preparation document and performed no Git publication, remote operation or runtime action.
