# Unified native source 410b — bridge limits recovery

The new candidate is `410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9`.
It contains exactly 4,855 source files. Relative to the actually built 70f0 closure,
only `heart/core/pinkha_native_source_capture.go` changes. The C-qualified b745
constructor supplies `localstorewitness.DefaultLimits()` for the exported bridge;
callers cannot provide limits through that bridge. Lower-level invalid/partial/
excess limits remain refused. The unchanged real-account regression reproduced
zero-limit failure on the predecessor and passed on b745 with two real captures,
new full sessions, current checkpoints, releases and invalid-limit refusals.
Those host results qualify the narrow constructor; neither new Apple slice has
executed yet, and they do not grant full-source migration permission.

## Exact source and dependency recovery

The predecessor source directory had disappeared. All 4,855 original members were
recovered and individually checked against the existing 70f0 manifest, including
its exact original 26,596-byte `go.work.sum`. The earlier metadata-regenerated
sum did not match and was retained as a failed recovery; it is not used here.
The complete Page154 overlay, Any, SDK, sync witness, tags and module declarations
remain byte-identical. `composition.json` and `constructor.patch` record the
single source delta and unchanged native closures.

The two original Tantivy release archives were fetched at their original pinned
v1.0.6 digests. The qualified LLVM-metadata transform reproduced both original
native library outputs byte-for-byte, including their native code/data/symbol/
relocation semantic inventories. New transform receipts have new path provenance;
their archive is explicitly a new dependency closure. Mac native-symbol checks
remain required before compilation. No Go LTO guard is disabled.

The old eight-module checksum evidence directory also disappeared. The fresh
actual Go1.27.4/SumDB recovery authenticates the identical eight module versions,
go.mod bytes and h1 values. Its first metadata JSON may omit GoModSum until Go
persists the authenticated value; the next original Go invocation reads it back.
Both observer-timing failures are preserved. The successful 16 original commands,
all signed lookup responses, metadata, original stdout/stderr and receipt are in
`authenticated-proof-originals.tar.gz` (108 original files). No module source ZIP,
engine compile, source checksum mutation or version change occurred.
The new producer copies this actual recovery proof and still independently
compares every field in the fresh 760-module workspace and generated bridge graph.
Eight positive controls and three concrete unknown-module/version/byte refusals
passed. They do not replace native builds.

## Producer and scope

Space admission measures the exact prior same-platform unified 70f0 library,
source bytes, dependency extraction and explicit cache/compiler/output allowances.
It keeps its existing 2GiB emergency floor. The old missing standalone library is
not used as a size oracle. `--go-jobs` is chosen from current measured memory and
concurrent work; its default uses all host cores and GOMAXPROCS uses all cores.
The per-Go-process 2GiB limit is soft and preserves measured memory headroom.
Every selected setting is recorded. Original mobile gateway tests, all exported
interfaces, the one-Go-runtime symbol check, actual Swift import typecheck and
source-after equality are unchanged.

The current shipping App profile intentionally remains 70f0 until both new
Apple slices and affected app/API acceptance exist. No accepted old result is
relabelled as a 410b result. No simulator device, original Products, private
account or unrelated cache was removed for this candidate.
