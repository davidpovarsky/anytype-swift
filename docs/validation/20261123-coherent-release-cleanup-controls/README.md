# Original coherent Release cleanup failure and bounded repair

Original run: https://github.com/davidpovarsky/anytype-swift/actions/runs/45095838065
Original source: d254a4a1ccd9288f585ff9374088cbaf965b36b4.
Repair base: 3fb3defb40c02de9af4ca880e27520595c0ce5ba.

## Original outcome

The App/native and UI runner builds completed and were archived before admission.
The first editor lane stopped in OWNED_SIMULATOR_READINESS before bootstatus,
test enumeration or any product method. The original owned simctl boot command
returned zero; the subsequent numeric ps quiescence query exhausted its existing
cleanup observation window. The projected command recorded TimeoutExpired after
a 2-second probe. It did not record its retry observations, so no exact original
probe count is inferred.

The original nested audit rejected that failed projection before independently
rechecking its pinned owned command. The outer worker group subsequently had an
actual zero-member observation; that cannot establish another nested group's
state. Final simulator cleanup queried the first exact owned UUID for 118.308042
seconds, then its delete command timed out after 20 seconds. Its deletion outcome
was uncertain. The original batch remains FAIL with zero actual product methods.

The original boot command, projected failure, readiness report, cleanup report
and worker-failure summary are retained here. The complete original evidence is
the exact GitHub artifact 14786515753 (829,528,196 bytes, SHA-256
a35f701fdf32977c0c9f605be9ee70fe424c754dcdd47c5321c85e00e3733ea4).
The worker summary explicitly binds the complete original worker member digest;
it does not replace that original record.

## Narrow controller change

Only the explicit coherent-heart-release readiness adapter and nested cleanup
audit opt into a single numeric ps query that can consume the remaining original
10-second deadline. Other callers retain their 2-second probe maximum. Actual
zero live non-zombie members are still required. No timeout proves quiescence.

The T5 command projection now preserves the original cleanup exception text and
each recorded probe timeout. It pins the unchanged owned command as before.

The nested audit validates each projection's exact basename, original file hash,
PID, argv, cwd, return code and termination identity before rechecking each unique
original group once. A failed earlier projection remains a failed earlier
projection. A later zero-member observation establishes cleanup only. Audit
failures now preserve their partial evidence rather than losing the reason.

Only a coherent delete timeout may trigger reconciliation of the same previously
validated nonbaseline UUID. A scoped query must actually show absence, or must
revalidate the exact name/type/runtime/availability and stable state before one
bounded idempotent delete retry. Query failure, foreign identity, another timeout,
nonzero retry or exhausted deadline stays failed. The original 180-second total
cleanup deadline is never reset; late query/retry returns cannot qualify cleanup.

No application, Swift module, native source, test selector, native fixture,
framework archive algorithm, build-reuse admission, source-retention map or
workflow was changed.

## Controls and their provenance

The original new-controls attempt passed 13 methods. A subsequent review added
a late-return deadline check and one new method. Only the five affected new
methods plus the new method were executed again. Six affected existing methods
were also checked: the three ordinary 2-second ps controls, original readiness
sequence, original nested receipt guard and original cleanup remaining-budget
guard.

The existing nested fixture initially failed because its synthetic projection
omitted the actual command's PID/argv/cwd/termination linkage. That failed log is
retained. The fixture was completed with those exact synthetic identities; only
that failed method was rerun and passed. Product guard behavior was not weakened.

There are 14 distinct new passing controls and 6 distinct affected existing
passing controls. These are controller fixtures, not Apple product acceptance.
No Apple build, product method or previously qualified native suite was run.

## Original Products restorability

The independent audit streamed both original archives and verified every member,
mode, byte count and SHA-256 against the original manifests:

| Archive | Compressed bytes | Entries | Regular files | Directories | Links |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native/App | 845,684,125 | 5,211 | 3,798 | 1,413 | 0 |
| UI runner | 1,522,647 | 30 | 15 | 15 | 0 |

The native archive retains 161 executable regular files, the original v2 native
descriptor, and the 11,477-entry source-input map. The UI archive retains two
executable regular files and its original v1 descriptor. Every member is a
regular file or directory, with no link or special-file extraction dependency.

This establishes exact structural restorability. It does not admit those d254
products against changed source or qualify their unexecuted methods. Both
descriptors contain the original machine's iOS 27.0 MainThreadChecker cryptex
path; any future copied descriptor must independently bind the selected live
runtime while preserving all other injection and selection rules.

## Remaining boundary

The original failed run is unchanged. A future execution requires root review,
source/carrier compatibility admission, exact original archive restoration and
owned destination cleanup. Full Release acceptance and cache publication remain
unqualified until actual required methods and cleanup pass.
