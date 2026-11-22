# Focused related-read package qualification

The manual route `related-read-authority-packages` runs four independent steps
on one native ARM64 Xcode27 host, at the final immutable application source and
TorahInspectorKit `511454e49450cb2581ddf77f644146ff3e30dbef`.

| Step | Fixed selection | Required original result |
| --- | --- | --- |
| Kit | Authority, affected cache refresh, and panel request state | 15 named methods, 17 actual argument cases |
| Any package | Typed current-authority error mapping | 3 named methods, 4 actual argument cases |
| Shared presentation | Document owner retirement/reactivation | 1 named method |
| R05 | Real provider resolver to shared selection and both query identities | Existing exact-one XCTest and xUnit gate |

The selection contract is
`docs/architecture/related-read-authority-20261121/test-profiles.json`.
The Kit step additionally reads its own committed selection contract. New
controller tests use a fixture copied from that Kit selection declaration;
synthetic event streams in those Python controls are never product test results.

The three Swift Testing steps record ABI version-0 JSON Lines. Qualification
requires actual method start and passing end records, the exact named argument
start/end pair for each parameter value, passing suite/run closure, no extra
executed method, and no failure, known issue, skip or cancellation. Descriptor
IDs are opaque; the gate binds each function to its declared name and exact
module/file identity. Aggregate counts or source declarations alone cannot pass.
Each step also binds the source commit, selected source hashes, unchanged package
lock, actual checked-out Kit commit, original test log and event stream hashes.

The original stream structure and verbose named argument messages are based on
the upstream [Swift Testing JSON ABI](https://github.com/swiftlang/swift-testing/blob/cfa4315124309e9951b6e7b3e9b66c7e92aea60c/Documentation/ABI/JSON.md)
and its [event recorder](https://github.com/swiftlang/swift-testing/blob/cfa4315124309e9951b6e7b3e9b66c7e92aea60c/Sources/Testing/Events/Recorder/Event.HumanReadableOutputRecorder.swift).
The [encoded event boundary](https://github.com/swiftlang/swift-testing/blob/cfa4315124309e9951b6e7b3e9b66c7e92aea60c/Sources/Testing/ABI/Encoded/ABI.EncodedEvent.swift)
elides case start/end events for a nonparameterized method in a single iteration;
those methods therefore require their function terminal without invented case
events. Parameterized methods require their actual named case terminals.
The controller requests the supported SwiftPM `--event-stream-output-path` and
`--event-stream-version 0` flags explicitly. Unexpected formats fail and preserve
the originals for diagnosis; there is no count-only fallback.

Each resolve/test command uses the existing owned process-group executor and
bounded quiescence verifier. Cancellation is latched while cleanup completes;
the next profile cannot begin after an unproved cleanup. Original command and
ownership receipts accompany the untouched log and event stream. A zero process
exit is explicitly labelled as awaiting test qualification, never as a test pass.

R05 keeps its own controller, one selected method, raw XCTest result and xUnit
receipt. This route changes no R05 acceptance rule. The shared-session and R05
steps use the same unmodified Presentation package `.build` directory, so SwiftPM
may reuse compatible compilation outputs. Each original verbose build log is
retained. Sharing a job does not itself establish that an output was reused;
the independent Kit and Any graphs are not labelled a single build.

Heart's separate typed mapping (2 methods /3 cases) belongs to the already-needed
SDK Debug app build, and is intentionally absent here. No simulator, native ACL,
whole-index completeness, App runtime or live Sefaria server result is claimed by
these package receipts. Historical provider, native, UIKit and other passing
methods are not selected again.

Before this route, the main Xcode lock may be regenerated only through the
existing `heart-dependency-resolution` resolve-only route and reviewed as actual
Xcode output. This controller never relaxes tracked-source or lock admission.
