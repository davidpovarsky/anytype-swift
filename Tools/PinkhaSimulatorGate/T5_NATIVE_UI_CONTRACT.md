# T5 current-Space Inspector UI acceptance

## Scope and status

This is an optional, real native UI lane after the same-source Apple r14/r15
account compatibility pair and its fifth host freshness phase. The default
four-phase and optional five-phase pair keep their existing behavior.

Source and controller controls are ready. Native preparation, Apple compilation,
the new UI methods and visual acceptance are **NOT_RUN**. Python controls use
synthetic metadata only and cannot count as native, runtime or UI acceptance.
The product lookup capability stays **OFF**. Both paired App builds already use
the identical test-only `PINKHA_NATIVE_T5_LOOKUP_V1` compile flag.

The Kit dependency is `3beb271230ba104f0cad741984403568f1ee9980`. It adds stable
related-row/unlink identifiers and an additive `noteActionUnlinksSource` option
that defaults to false. Anytype opts in in its Session alongside all six Kit
pins. Other hosts keep their existing Delete behavior. The parent integration
owns that Session change, dependency pins and the UI project's source registration.

## Entry and account boundaries

The reusable workflow adds `include_native_ui: false`. Its CLI option is
`--include-native-ui`, which requires `--include-freshness`. UI begins only after
two App builds, five distinct native processes and five exact named tests pass,
with eleven bounded host freshness observations and complete native secret scans.

Before UI, `continue_with_native_ui` writes an independent `pair-result.json`,
records its SHA-256 and leaves its original pair counts intact. A UI failure or
cancellation cannot turn that pair proof into a UI pass or overwrite the pair
result. The overall route fails when requested UI fails. A successful automated
UI lane reports `T5_NATIVE_UI_PASS_VISUAL_REVIEW_PENDING`; manual visual review
remains an explicit next acceptance step.

The pair simulator is shut down. Its final ledger must match the actual fifth
process's `nextLedgerSHA256` before UI and remain byte-identical afterwards. The
controller never boots, clears or mutates that paired account for UI work.

UI owns a newly created simulator whose name, UUID, type, OS runtime and absence
from the original inventory are checked. No App data container may exist before
installation. The fresh container, native account, Space and root hash must be
different from the pair. The controller shuts down only this owned UI simulator;
it does not delete simulators, account stores, caches or user data.

## Reuse of actual App products

The retained `new/Products` App and native XCTest products come from the exact
same published source as the pair. Source SHA, runtime version, flags, Hanlin
snapshot, Kit pin and installed executable-carrier hashes remain bound to the
original r15 build. The App is not rebuilt for UI.

Only the independent existing UI-runner project is built. The original UI
project must include `PinkhaT5NativeAcceptanceUITests.swift`, and its bytes must
remain unchanged. The retained and installed App executable hashes are checked
before preparation and after the UI runner build and actual UI execution.

Every selected xctestrun is written with a unique `UI27-T5-` filename beside its
original Products configuration, preserving `__TESTROOT__`. Only the selected
target receives explicit `OnlyTestIdentifiers`, an empty `SkipTestIdentifiers`
and the existing environment injection. The original xctestrun is untouched.
CLI selection and the nonzero original XCTest case/count gate independently
require the intended methods. No host route or UI action is bypassed.

## Native preparation

`TorahT5UIAcceptancePreparationTests/prepareFreshNativeUIFixture` runs once through
the existing AnytypeTests bundle against the actual r15 middleware. It creates a
fresh local-only account using real Wallet/Auth services, installs the Note type,
bootstraps the real schema and creates two Spaces. The public fixture contains
no wallet credentials. Both credentials are masked in invocation logs and saved
only in a private job-owned file for the publication scan.

The primary Space has five expected current-source targets:

| Role | Actual native object | Association and expected navigation |
|---|---|---|
| Page | Page | Exact canonical document source; open document |
| Note | Note | Exact canonical document source; open Note |
| Writing | Bootstrapped writing type | Exact canonical document source; open document |
| Block | Page with 24 leading paragraphs | Block-only source; open distant associated block |
| Quote | Page with 24 leading paragraphs | `sourceQuote` block; open distant quote block |

The sourceQuote text is explicitly synthetic fixture content. This lane proves
native discovery and navigation of an already persisted sourceQuote. Actual
provider search, insertion, drag/drop, undo/redo and quote provenance keep their
existing separate real-provider UI lanes.

Three additional documents must not appear: a different verse, a different
provider, and the exact same source in the other Space. Native canonical
readbacks, live block reachability and the real related-document service must
yield exactly the five expected identities. Coverage remains
`indexedTargetsOnly` with `indexFreshnessUnverified`, never `spaceWide`.

## Actual UI methods and observations

`PinkhaT5NativeAcceptanceUITests/testCurrentSpaceRowsAndExactBlockNavigation`
collects seven observations. The actual source chip and Inspector are used from
Page, Note and writing documents to verify the same exact five related rows.
For each of the block/sourceQuote targets, ordinary document entry first proves
that the first paragraph is visible and the distant target is not hittable.
Then an actual Inspector row tap must display the exact object and target block,
with its actual persisted text hittable on screen.

`PinkhaT5NativeAcceptanceUITests/testAddNoteEditOpenUnlinkAndRetainAfterRelaunch`
collects six observations. It taps the real Add Note action, identifies the
new editor object, types a body through the native text view, returns through
the actual Back control, and opens the new sixth row through Inspector. The
row's real context menu must offer Unlink source and remove only the link.
After terminating and relaunching the App, the source list stays at five rows.
Ordinary navigation to the retained Note must show the same typed body without
a source chip; focusing the actual text view must reveal the keyboard.

The UI suite is English-only and simulator-only. Other display modes, Hebrew
RTL, VoiceOver, physical iPad, cancellation/permission edge cases, full-Space
freshness and the remaining R01-R09 criteria remain separate open acceptance.

## Evidence and failure behavior

One exact preparation method and two exact UI methods must pass with zero
failed/skipped cases on the selected arm64 OS27 device. Original XCTest summaries
and test trees are parsed; names or status labels supplied by a fixture cannot
substitute for executed tests.

The two UI receipts are bound to source SHA, run ID, unique token, Space, coverage
and exact ordered observations. Thirteen original screenshots and thirteen
accessibility snapshots must be attached to the correct actual XCTest methods.
Observed App PIDs distinguish the two UI methods and the Note relaunch; the
preparation PID must also be distinct. Installed executable bytes stay unchanged
through those lifetimes; per-lifetime vmmap identity is not claimed.

Only an explicit allowlist of original logs, summaries, test trees, fixture,
receipts, screenshots and accessibility snapshots may be published. Before any
copy, every candidate is checked against both disposable credentials in UTF-8,
UTF-16LE and UTF-16BE. Symlinks, path escapes, raw xcresults, `.app` bundles and
`secrets.json` are rejected. Missing credentials or a leak withhold all private
UI evidence and fail UI acceptance. Account data and raw xcresults remain private.

The controller reuses the pair's bounded owned-process runner. KeyboardInterrupt
from execution, cleanup or evidence publication is recorded as cancellation and
re-raised after final receipt handling. Private original diagnostics remain
available locally; a cancellation cannot be silently returned as PASS.

## Validation recorded for this source

The source handoff records **20 Python test functions / 80 subtests, zero failures,
errors or skips**, on Linux. These are controller and evidence rejection controls,
including both xctestrun layouts, original-path preservation, exact source/test
identity, unrelated simulator rejection, offscreen-to-visible assertions,
Note retention, all credential encodings, all-before-copy publication and
cancellation at cleanup/publication. The independent pair receipt is checked
before and after successful, failed and cancelled optional UI.

Root reviewed both Swift fixtures; the SDK agent independently reviewed the
helper/evidence contract and the two concrete fixes. No local Swift compilation
was attempted during the Windows disk/RAM incident. Native preparation, the two
UI methods and visual acceptance still require their actual Apple run.
