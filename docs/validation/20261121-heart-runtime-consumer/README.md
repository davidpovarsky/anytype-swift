# Explicit corrected Heart runtime consumption

The retained Heart application can opt into `runtime_profile=r15-attachment-v1`
while the original `r14` remains the default. This choice propagates through
the dispatcher, simulator/host reusable workflows, artifact installation,
shared build, each fresh batch worker lane, built binary verification and the
actual mapped application PID. There is no inference from a filename or a
generic native marker, and no fallback to another runtime.

The corrected source is Heart
`d98420b1113536afd08cde6de9a5816f6d27ffff` with complete patch
`595f8142f00035da2fff4925c8fe125fa7cf36de9ae124b528a9d2130b2a9bf6`
and inventory
`a9c381a46a0003c34695f22232b57716096ec51b100bb8dae2a18b47148274d8`.
The immutable profile requires its complete derived, T5 lookup and attachment
version string in each binary architecture and observed process carrier.

## Original source-run proof

The corrected downloader reads the original successful GitHub producer run,
head, branch, attempt and explicit route. It requires exactly one named
runtime artifact and one matching proof artifact from that run. Both original
GitHub ZIP payloads must match their API SHA256 and size before extraction.

The installer compares the exact patch/inventory bytes retained by that
producer, the build receipt from both archives, and the producer's runtime
archive/receipt hashes. It replays the producer's original two-fixture native
log and requires that result to equal the retained fixture receipt and build
receipt. This replays evidence; it does not run the native tests again.

The native artifact still receives the complete file inventory and three
architecture checks. The installer refuses to overwrite an existing native
installation. Its receipt retains original producer and artifact identities
alongside the current consumer source.

The shared runtime observer validates the selected complete marker and
producer binding before mapping the supplied UI process. It retains those
fields with the actual PID, process start, installed executable hashes and
native carrier hashes. SDK06's existing observer uses this same path without
adding a probe launch. Batch workers preserve both the requested profile and
the original producer run across the parent/worker/lane boundaries.

## Validation scope

The focused controls use synthetic artifact and process fixtures. They check
the real download/admission functions and marker propagation without executing
native code, xcodebuild or a simulator. They reject altered ZIPs, mismatched
source/run/attempts, failed producer outcomes, missing/duplicate/foreign
artifacts, partial runtime markers, failed original native log records, changed
installed receipts/binaries and missing producer metadata.

Only impacted controls are selected by `harness.py`: 11 archive/profile
methods, 6 corrected-observer/CLI methods, 3 existing marker/launch methods and
2 worker propagation methods. Original outputs, exact source hashes and actual
completion status are retained in `result.json` and separate logs. These are
22 controller methods, not Apple or native acceptance.

Python source parsing and YAML parsing with duplicate-key rejection were also
checked. The explicit runtime input defaults to r14 in both reusable workflows;
all six retained dispatcher callers forward it. The existing
`retained-heart-release` batch preset and `shared-editor` host profile remain.

## Actual application acceptance

A passing controller check does not prove the corrected framework's
AppGetVersion, application linking, native account behavior or UI journeys.
The caller must supply the successful corrected runtime producer run ID and
select `runtime_profile=r15-attachment-v1` for pending editor, Properties,
quote and SDK06 runs. The exact original r14 paths remain available.

T5-specific runtime fixtures and production capability admission require their
separate explicit corrected-version extension before T5-enabled acceptance.
This consumer change does not enable the product lookup flag or relabel
compatibility with an unmodified legacy writer.
