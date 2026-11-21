# Shared engines: integration and focused evidence reuse

## Integrated source

The owner requested one shared implementation for both engine applications and
completion of the outstanding work, without repeating unaffected successful
tests. The integration branch is codex/chatgpt-wave15-shared-20261121.

Merge 8a7cc666c5 combines the original Any branch at 31ae2e6389 and the active Heart
branch at a05088b988. Current Apple dispatch 44942212731 is bound to exact
96173b0afc6b360c8f780ae70c6c80042fda98da, not to a moving branch head.

The retained Heart and Any consumers use the same TorahInspectorKit revision
158acb295f832e96907cdadc813a1c2a4bb6a03c. Shared Torah and Hanlin presentation
extractions are retained. PinkhaKit now owns the serial local-text queue and
text-input render policy. Heart uses the queue and render policy; Any retains its
existing acknowledged-write/revision queue and consumes the same render policy.
Engine-specific native storage, authentication and observation adapters remain
separate because their underlying APIs differ.

The unchanged source-retention checker passed for 5,790 protected baseline files:
5,711 unchanged and 79 exact reviewed changes, including 39 files byte-identical to
the active Heart branch. The map pins every replacement/shared-source blob and
retains the original baseline. It is a source-retention result, not a behavioral
or release acceptance result.

## Original evidence is preserved, not relabelled

REUSE_LEDGER.json records the impact analysis and planned selected scopes.
The six original named-execution receipts under original-44695105165 are copied
byte-for-byte, retain producer 31ae2e6389, and are hash-pinned by the ledger.
The failed native UI and picker-observation receipts are preserved alongside
the passing runtime, Hanlin, UIKit and hosted-application receipts.

NATIVE_UI_ORIGINAL_COUNTS.json is a read-only safe projection of the original
summary/test-tree exports. Their complete hashes match the original failed
named receipt. It records all 11 methods: 2 passed, 9 failed, 0 skipped. It contains no
screenshots, recovery phrases or original user content. The private raw result
bundles remain outside the committed report.

The 115 UIKit passes include 11 marked-input/focus methods affected by the renderer
change. Those 11 are selected again with 3 new renderer cases. The 104 other passes
remain source-bound original evidence, not a claim that 118 tests ran in one new
execution. The 36 Hanlin and 9 hosted-application passes are reused after source
impact review. The unchanged patched native runtime retains its 3 original passes.

Native artifact reuse is explicitly authorized by original producer/run. The
installer verifies ancestry, byte-identical manifests/overlays, effective native
trees, pinned upstreams, archive/member hashes and platforms. It keeps the
original producer receipt and writes a separate consumer binding. Native binary
or test producer identities are never rewritten to the consuming Swift commit.

## Changed and unpassed checks selected

Run 44942212731 selects 14 Any UIKit methods, the 9 previously failed native UI
methods, and 10 Heart UIKit methods / 15 literal invocations. The archive-picker case
remains an observation gate; a complete Files export/import round trip is
separate outstanding acceptance. Mounted Heart editor/quote/Properties have a
fixed batch of 6 UI methods with 3 fresh native preparations and the original Properties
native postflight. Each lane owns separate simulator/account/Space data while
sharing one build.

The shared queue/render-policy unit proof (9 methods / 11 invocations, 0 failures)
is retained under 20261121-shared-editor-unit. Adapter-only follow-ups do not
change those pure sources, so that execution is not repeated. Focused gate
controller controls cover exact names, literal arguments, duplicate/missing
cases, failures and actual destination identity. These controls do not count
as Apple product tests.

## Active follow-up boundaries

Space.Close 44939797011 compiled and completed its four-process native account
baseline, then failed its first race; cold reopen did not run. Its original
failure is retained and is under diagnosis. The run is not a closure PASS.

The published r15 runtime 44393343388 predates the later native attachment fix.
The corrected r15candidate preserves the complete lookup-capable r15source and
adds the exact source correction tested in 44610974453. The original r14 / r15
binaries are not relabelled as corrected; a distinct verified runtime is required.

The actual Apple outcomes, mounted UI, archive round trip, full T2 matrix and
physical-device acceptance remain separate gates. No task is closed by this
source integration or evidence reuse ledger.
