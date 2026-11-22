# Prepared migration Apple runtime candidate

This is a separate opt-in source candidate for the native runtime identity
`v0.5.0-pinkha.prepared.1`. The current default v9 manifest, version and
workflows are unchanged. Apple build, linkage and the managed-HTTP Swift
journey must produce their own original evidence before this candidate is
accepted on Apple. No public file capability is enabled.

## Exact source composition

Apply the two final full patches once to clean checkouts at Any
`88fae2e5ae7d0f46d6707567a3123081faa8de9a` and SDK
`854df54cdadd76006ae823cbd1b1d923138356d0`. The SDK annotated v0.8.0 tag
object is separately bound to `b161a0475479bbe7d9d693bc496c6fdd90c3969b`.
These full patches already contain every preceding overlay; applying them
over an existing v9/v10/prepared checkout is incorrect.

The immutable composition order is:

| Repository | First retained layer | Second layer | Final layer |
| --- | --- | --- | --- |
| Any | v10 authorized-operation-read candidate, including every v9 delta | Frozen prepared object/root/bootstrap/block v1 | One new actual inline-file SDK fixture |
| SDK | Exact v9 native receipt/current-authority overlay, also used by v10 | Frozen native PREPARED-byte ledger and object/block commit route | Native-only original inline-file route and private payload guard |

The six exact input patch hashes are in `transfer/composition-summary.json`.
The separately frozen object/block bundle SHA-256 is
`95777bc294903b1bd5dede421a80af6e949a85e2d1e2de41d1e2f77a4d054ff0`.
The separately frozen inline bundle SHA-256 is
`1bdb3178f1d46743923a2e42e6f14baab010140b181bc37a455cae24ebab2890`.

The complete source overlay contains 62 Any paths and 61 SDK paths.
The composition receipt binds their actual Git blobs, native LF SHA-256
hashes, staged effective Git trees and full-patch hashes. It additionally
compares all 635 Any and 653 SDK Go/module files against the final tested
native source census. Native source-copy CRLF metadata from earlier Windows
worktrees is retained at its original scope; the final candidate uses exact
tested Linux LF bytes and matching canonical Git blobs.

## Current default and later v10 retention

The current default v9 source manifest has Git blob
`2605591addfbd1d9b467da72c37963b48e4a8365` and SHA-256
`15906eb27afea68cc7ec99242bffd6a8ea69517edb608a4421cce90c9a99a070`.
This is also the exact default manifest digest named by the later v10
candidate. The report `retained-default-and-v10-coverage.json` records every
path individually.

| Source set | Original paths | Byte-identical original Git blobs | Explicitly extended paths | Removed paths | Added paths |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current default Any v9 | 49 | 47 | 2 | 0 | 13 |
| Later Any v10 | 54 | 52 | 2 | 0 | 8 |
| Current default / later SDK v9 | 41 | 36 | 5 | 0 | 20 |

The two extended existing Any paths are `internal/editor/api.go` and
`internal/server/handlers_pinkha.go`. The former extracts the existing
creation batch encoding into a pure shared function; ordinary position
allocation and current-writer routing remain in their original caller.
The latter retains the v10 authorized-operation-read route/capability and
adds registration of the prepared migration routes. The original ordinary
current-writer creation route was separately exercised in the frozen
object/block qualification.

The five extended existing SDK paths are the native commit guard, object
implementation, object API, native object store and its current-writer
guard. Their prepared-object/block changes belong to the frozen v1 bundle.
The inline layer changes only the native commit guard among those existing
files. Its private payload mode is explicit; the ordinary encrypted token
still requires the original read key, and incoming historical replay keeps
its original early-return path. Seven directly affected existing guard
controls passed after the inline branch was added. No any-sync or any-store
overlay is added.

## Evidence reuse and outstanding acceptance

The native object/block bundle retains 25 new controls and one existing
route control at its original source scope. The inline bundle retains
12 new controls and seven directly affected existing guard controls.
These are component counts with possible reused guard coverage, not a new
aggregate claim that every historical control was rerun against this final
candidate. The exact source census and narrow guard requalification justify
reuse. Original passing logs, the initial isolated modfile failure and the
pre-correction passing cascade probe remain unchanged.

Prepared object/block HTTP APIs are present. The optional inline-file native
service has no public HTTP or Swift file route. `file: 0` and
`networkVerified: false` remain mandatory. Original inline content is bound
to 0–4095 bytes; large blobs, variants, derived owners and status subscription
publication are outside this slice. No full-Space snapshot/census fence,
full migration acceptance, physical power-loss claim or file network proof
is introduced by source composition.

The main manifest is deliberately a candidate and records Apple build and
consumer acceptance as pending. `testedEffectiveTree` is the legacy build
contract field for the exact composed staged tree. It does not imply an
Apple test ran. The root agent owns the manifest-driven native-version
selection in `prepare_native_runtime.py`, producer dispatch, consumer
execution and publication.
