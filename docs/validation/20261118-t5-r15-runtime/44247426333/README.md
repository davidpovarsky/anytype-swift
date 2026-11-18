# r15 build 44247426333: immutable input and mutable hydration

## Actual failure

- Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44247426333
- Published control source: `4f5cccfb17051d588b22ca412e2191c9d2db459a`.
- Actual result: **FAILURE** before gobind/gomobile compilation and before a verified r15 framework artifact.
- Error retained in `original/unpacked/runtime/runtime-build-result.json`: `Generated cache hydration changed its original module declarations`.
- Original artifact: `14404400415`, 377866 bytes; outer SHA-256 `de2d187c0f9bbc74e1bcef15b54d4b0e24675001679f9b0eaf2eace9f35c140b`.
- Inner archive SHA-256: `a56d66a558c817de3a92bf2d88041c07a5ee759c96beec6df0397b7c57db519c`.

The original archive was already downloaded by the parent. It was read in memory,
verified against that digest and preserved without another download. Both original
archives and all 19 inner members are retained byte for byte under `original/`.
The directory attributes disable newline conversion for raw evidence and the
separate actual metadata probe.

The preserved native graph has 882 modules. Pinned gomobile's flattened input
contains 868 require declarations and 14 replacements. The actual generated
selection contains 1070 modules including its main module. Replaying the existing
selected/downloaded checksum gate against the original logs verifies all 1069
remote dependencies. Relative to the original requirements, 38 selected versions
are higher; the generated graph also contains 201 additional module paths. This
is the generated graph, not a rewritten native source graph.

The failed archive does **not** contain its post-hydration go.mod. We therefore do
not claim the exact missing after-file bytes or assert that this observed gate was
caused by one particular requirement. The original manifest, selected versions,
complete download log, command records and failure are preserved.

## Confirmed Go behavior

An already installed `go1.26.5 windows/amd64` toolchain ran four metadata commands
against three newly authored local modules. No network, module ZIP download,
source compilation, native middleware, Apple framework or UI test was used.
The complete probe is 6918 bytes before this handoff's derived validation.

Under `GOWORK=off`, `GOPROXY=off`, `GOTOOLCHAIN=local` and
`GOFLAGS=-mod=readonly`, `go mod download -json all` changed the main requirement
on `example.test/b` from v1.0.0 to v1.1.0 to satisfy the other local module's
requirement. All non-require manifest fields remained unchanged. Actual before
and after files, command outputs, input declarations and the receipt are under
`metadata-probe/`. The new semantic guard accepts that observed metadata delta.

The pinned toolchain's `src/cmd/go/internal/modcmd/download.go` has SHA-256
`c31998a4c5d47e6e8205bda13a2abc1ef9c00944ada0e965053e4fa4af303ebf` and explicitly
writes go.mod. The Go project's own [download regression test](https://go.dev/src/cmd/go/testdata/script/mod_download.txt)
also covers updating go.mod when the `all` argument is supplied. The [module
reference](https://go.dev/ref/mod) explains graph selection and module declaration
updates. Thus readonly flags must not be treated as a protection against this
metadata command's writes.

This probe confirms the mutation mechanism on the exact Go version; it is not
execution of the original full generated graph or an Apple acceptance result.

## Narrow correction

The original gomobile seed remains immutable. Its existing byte-hash guard and
its canonical original manifest remain the authority for all three actual
pre-tidy architecture modules. The native checkout, reviewed patch, native go.mod,
gomobile sources, Go/toolchain pins, genproto pin/checksums and the original r14
builder are unchanged.

Only a new controller-owned copy named `generated-dependency-hydration` is passed
to `go mod download` and the subsequent selected-graph query. The copy must start
with the exact original seed bytes. The build records both original/hydrated raw
go.mod files and JSON manifests before accepting the resulting graph.

The new manifest gate allows only require versions equal to the independently
checksum-verified selected graph, plus selected indirect additions. It rejects
removed original requirements, directness changes, a new direct requirement,
unknown or duplicate declarations, and any change to module identity, Go version,
replacements, exclusions, tools or other non-require fields.

The before-tidy contract continues to use the unchanged original manifest. The
actual offline tidy/build launcher still permits only pruning of unused modules
from the verified selected graph, with identical versions, replacements and both
checksums. The correction does not copy hydrated requirements into gomobile's
original generated inputs and does not enable the App capability.

## Verification and remaining gate

`runtime-controls.log` and `validation.json` record **32 test functions / 93
subtests PASS**, zero failures, errors or skips. The additions check independent
copy ownership, exact original bytes, fresh-directory requirements, allowed MVS
changes and rejection of declaration drift. The same gate was also applied to
the actual small Go metadata probe. Python syntax and Git diff checks passed.
The replay against the failed build's original 1069 dependency receipts passed.

The original launcher SHA-256 remains
`d3e97a7a00f30bd68fac4ab4cf0063898231932c84bbecb2de9e9aa271aca5b9`;
the original r14 builder remains
`0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669`.

A corrected full Apple r15 build is **NOT_RUN** at this source handoff. The
same-source r14/r15 App pair, optional fifth Swift freshness phase and real T5 UI
remain **NOT_RUN** until their actual prerequisites pass. Product capability
remains **OFF**; no runtime, UI, full-Space, physical-device or release acceptance
is inferred from controller controls or the metadata probe.
