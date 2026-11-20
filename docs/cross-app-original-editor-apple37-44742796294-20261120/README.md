# Apple37 — authenticated original editor component result

## Outcome and scope

GitHub run **44742796294**, attempt **1**, completed successfully on the immutable
CI commit **a298c556a36913bfec3eaa81165487fe742559a6** and branch
**codex/otzaria-original-editor-owned-apple-v2-reviewed-20261120**.
Its original application source is **dfb9d6240def89ace58d12293cac9e5ad5968078**.

The downloaded artifact was authenticated against GitHub's size and SHA-256.
The exact original result gates from that commit were replayed on the retained
raw summary and test tree. A separate read-only query of the original xcresult
SQLite database corroborated all named executions.

| Original suite | Declared and actually passed |
| --- | ---: |
| PreparedEditorPageDocumentTests | 6 |
| TextServiceHandlerInjectionTests | 5 |
| EditorLocalEventPublisherTests | 5 |
| EditorDocumentWriteOwnerTests | 8 |
| PreparedEditorLifetimeTests | 8 |
| EditorDocumentOwnedTableTests | 5 |
| **Total** | **37** |

There were **0 failed and 0 skipped selected tests**, **0 TestIssues** and
**0 SkipNotices**. The result tree contains exactly those 37 unique cases; the
SQLite database contains 37 TestCases and 37 successful TestCaseRuns. Its 111
destination/configuration aggregate rows are projections of those executions,
not 111 additional tests.

This run also executed the existing **74 Mac host-gate controls**, all passing
with no skips, including both POSIX child-process/termination controls. The
remaining dispatcher jobs were skipped because this workflow selected the
original-editor profile; they are not additional executed acceptance.

**This proves component execution on controlled original document/service
fixtures, and a build of the original Anytype app. It does not prove mounted
block-editing UI, a Maktabah editor consumer, durable annotation integration,
live-account writes, physical hardware, or product performance.** The six later
BlockService test cases selected by Apple43 are outside this source/result.

## Actual Apple environment and build

- Xcode 27.0, build 27A266a; Apple Swift 6.4
  (swiftlang-6.4.0.34.1, clang-2100.3.34.1).
- One owned arm64 iOS Simulator: iPad Pro 13-inch (M5), iOS 27.0, build 24A434.
- Original project and scheme: Anytype.xcodeproj / Anytype.
- Original configuration: Debug-Anytype.
- Original build-for-testing, strict codesign verification, and
  test-without-building all exited 0. No local rerun or rebuild was performed
  during this evidence review.
- Build command ran 13:53:40–14:38:53 UTC; strict signature verification ended
  14:38:56; test-without-building ended 14:40:08; final receipt ended 14:40:21.

The retained CI receipt records these actual product digests:

| Observed product | SHA-256 |
| --- | --- |
| Anytype executable | d17f5f85c8b50e91b6138e6b60e8f7b037c1a8131e952cae46ed873fc250c6b6 |
| AnytypeTests executable | 3a70e9823c156f15dd15c25b4e35ba5d6de68a1d838875a60d1b530a6fb987ff |
| Original xctestrun | 373447929a84a3fbda7b3d20ef834656123b3377cbaf5440a155a85799f7d38b |

Those are authenticated CI observations. The app/framework binaries were not
downloaded again and were not rehashed locally.

## Source and dependency preservation

The review independently matched all **five application tree IDs** to the
immutable GitHub commit and original profile, and all **six complete test files**
to their canonical Git blobs and pinned SHA-256 values. Twenty original
source/gate/input files were retained byte-for-byte and remained unchanged during
the replay. The original selection, preflight and final receipts agree on the
same run, attempt and checkout.

All **44 actual SwiftPM pins** equal the source lock entries, with no added,
removed or changed pin. The recorded actual TorahInspectorKit and Swift AI SDK
checkouts equal their original pins, including the Kit's package and project
declarations.

The original SDK materializer/validator ran against Hanlin commit
**116cc6be0654a5d11bc56ba00e0310031107ee36** and recorded all **407 files**.
The unchanged original driver revalidated the installed snapshot before and
after the build/test sequence. Its retained snapshot SHA-256 is
**bcbcdeff5d88123fed26201feee00f7af06019d2dfe39e9537fe59eff48a6534**.
This review verifies that source-bound record and the original guard execution;
it does not claim a new local rebuild or independent local rehash of 407 absent
dependency files.

The original Heart input remained the exact r14 producer:

- Producer run 44203168617 at b5dc53b799a70269b8082734106d8cd30a99fc44.
- Artifact 14383247626, Pinkha-Universal-Verified-Heart-r14,
  264982619 bytes, GitHub ZIP SHA-256
  7ac88836edc2ee9ff0c7d8cb8943b8e968f0c73b2b94752ba27cebc241c69996.
- Inner archive SHA-256
  7aa836e081740b99e7e26485fd7f1845fc3ea99fa2331b2ab99330675a4c590f.
- Original patch SHA-256
  fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077.

The exact original Heart metadata gate passed again against the retained
producer/artifact records. The original source inventory equals the build
receipt; the original CI installation verified its file inventory and three
thin-architecture slice rows before use, then the original build driver checked
the installed bytes again. The actual app and test-host runtime copies both
reported the same original marker. This run did not rebuild or replace Heart.

## Warnings and limits

The raw build log has **2656 lines containing warning:**, representing **564
distinct message strings** after removing their prefixes. These counts are log
observations, not a count of independent defects. All raw lines and messages
are retained in WARNINGS.json.gz, and the unmodified build log is inside the
original artifact. The test summary's runtimeWarnings array is empty.

A name-based filter over the new editor files found 18 warning lines: 10 lines
for five imported Protobuf types in TextServiceHandlerInjectionTests.swift:107
(repeated compiler diagnostics), plus eight type-check duration warnings.
No warning-free claim is made. These observations did not change the selected
tests, original source, acceptance oracle or successful process exits.

## Immutable artifact and verification

| Evidence | Value |
| --- | --- |
| Artifact ID | 14637726161 |
| GitHub artifact bytes | 783402 |
| GitHub artifact SHA-256 | 1d76bd6c090b66c315ed96c356e406a61e2fe0522e4da24992419111cfdbcb48 |
| Inner evidence ZIP bytes | 819126 |
| Inner evidence ZIP SHA-256 | c446bced8049249e2f649dbfbf1e2fc7dad39446004442946291634e5379715f |
| Verified inner raw files | 128, including the complete xcresult |
| Result replay | Both complete original Python modules, no altered test/count gate |

The outer ZIP is retained unchanged. RAW_FILES.json hashes every uncompressed
inner member, including command logs, original xcresult, raw test JSON, source
selection, SDK snapshot and Heart receipts. The decoded original GitHub job log
is losslessly compressed separately and contains the 74 actual host controls.

ORIGINAL_GATE_SOURCE.zip contains the 20 canonical Git inputs, their authenticated
blob index and replay_original_gate.py. To reproduce the read-only review,
extract that source ZIP, the outer artifact and its inner ZIP (the latter into
an extracted directory); expand job-136310407305.log.gz beside the source folder,
then run python3 -B replay_original_gate.py with GITHUB_RECEIPTS.json beside it.
The script does not invoke Xcode, Swift, a simulator or a native write.

The first local result replay already passed the same 37-case and Heart gates.
The final replay additionally retained the complete original project file and
checked the second Kit pin explicitly. Its earlier 19-input result is preserved
in the source ZIP under review-attempts; it is not another Apple execution.
An unsupported direct-job metadata GET and an initial incorrect workflow filename
lookup are retained as collection notes, distinct from build/test results.

No source, workflow, package pin, test, frozen branch or original result was
modified to produce this report. The Windows host remained offline; all
collection and publication used the existing GitHub connection and local
read-only evidence processing.

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44742796294
Job: https://github.com/davidpovarsky/anytype-swift/actions/runs/44742796294/job/136310407305
