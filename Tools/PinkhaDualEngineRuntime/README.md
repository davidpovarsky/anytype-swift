# One native runtime for the shipping app

This producer builds Heart service/core and Any's original mobile bridge in one
gomobile invocation per platform slice. The generated Lib framework owns one Go
runtime. The shipping app reaches both engines through ProtobufMessages and must
not also link the standalone AnyLib framework.

## Current source closure

The current candidate source manifest is `410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9`
with 4,855 exact files. It succeeds the actually built 70f0 manifest. The only
production source delta is the C-qualified b745 exported capture constructor:
`heart/core/pinkha_native_source_capture.go` now supplies the existing bounded
default limits. The same original real-account bridge regression failed on the
predecessor and passed on b745; lower-layer invalid limits remain rejected.
Full Page154, compiled definitions, Any mobile gateway and all source/dependency
versions remain unchanged. These host results do not qualify either new Apple
slice or grant source migration admission.

Original module pins remain Heart `ea796999d648e27dcb7ad23a0bbd849d35fadc5a`,
Any `cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3`, Any Sync SDK
`e195f6c07a053c6588e39ffe72ee4fc44cf3d953`, and any-sync witness donor
`c005bd6cde8d8f8a6007c35f06894f3d89f9f07c`.
The complete Page154 source overlay stays byte-identical and separately bound to
`2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38`.
The runtime version identifies the complete current manifest; the old Page154
overlay hash retains its distinct provenance role.

## Dependencies and module graph

The two original Tantivy v1.0.6 iOS archives remain a separately hashed closure.
Only embedded legacy LLVM metadata is removed by the reviewed C helper. Actual
native code/data, symbols, relocation targets and platform commands must remain
identical; Go's LTO checks stay enabled. The Mac independently compares native
symbols before compilation.

The generated bridge compiles inside a private derivative of the original
four-module workspace. Its actual tidy output is retained. Every original
module path, version and available checksum is compared against the fresh full
workspace graph. Neither source modules nor the shared module cache are rewritten.

The old eight-module metadata evidence directory was lost. The new producer uses
an explicitly new actual Go/SumDB proof for the identical eight module versions,
checksums and cached bytes. Its original 16 commands and all signed lookup
responses remain retained; both earlier observer failures are preserved. This
does not reuse an old workspace graph: current source and generated bridge
module inventories must still compare exactly. Unknown changes fail.

## Execution and acceptance

Run `build_apple.py` on the Apple Silicon Mac with a fresh source-hash root,
the exact source/dependency archives and the committed controller files.
It records command logs, owned process groups, actual source/dependency/module
identities and the requested simulator or device slice. Both slices must have
the same current source identity before XCFramework assembly.
The producer verifies Heart, Any, capture, semantic and authorized-read exports,
the single Go symbol set and the actual generated Swift import surface.
It rechecks every source byte after compilation.

Disk admission uses original native archive sizes, exact source bytes and
explicit compiler/cache/output allowances. Each command samples real free
space and may stop only its owned process group at the 2GiB emergency floor.
Normal keyed Go caches are shared with coordinated native jobs; mutable
source/work/tmp roots and journals remain private.

The previous 70fb and 70f0 simulator/device slices passed actual build/link
qualification. Current shipping App/full UI builds still use frozen 70f0. The first original combined app and complete UI bundle also
built successfully at app source `6db4d065e007dc6c39ae510a77053f33b7de8247`.
Those retained results remain evidence for that previous source only.
The current native source requires its own two slice builds and affected
app/UI acceptance before final signing. Production shipping must retain the
dual-engine, T2, T5 and Page154 feature definitions while excluding DEBUG-only
launch fixtures. A successful native producer or app build alone is not
migration acceptance or a signed TestFlight release.

## Bounded original mobile gateway phase

`qualify_mobile_gateway.py` runs only the three unchanged original Any server
methods against the complete current four-module workspace, before Apple binding.
Its next-phase estimate uses the retained native Any host binary size, source byte
count, temporary/cache allowances and the existing 2 GiB emergency floor. It
retains original JSON test events, binary, source and complete module graph.

The Apple producer accepts `--gateway-proof-root` only for a completed same-manifest
phase. It rechecks all 4,855 source files, original outcomes and command logs, then
requires all 760 module records to be identical after only source-root relocation.
This reuses component evidence; it never substitutes for either Apple slice build
or application acceptance. The initial phase remains unqualified until actual
original test execution succeeds.
