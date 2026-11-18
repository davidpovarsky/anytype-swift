# T5 revision pairing: component process proof

This tranche authors a controller and one shared Go fixture. **Native compilation and execution are NOT_RUN.** No build, download, CI or watcher is started by these files. The frozen backend r15 patch, 947 driver/reopen fixture, Swift helpers and integration files are unchanged.

The first feasible proof is two independently compiled **Go `spaceindex` test binaries**, run as four separate processes against the same controller-created disposable on-disk Space index: r14 create → r15 upgrade → r14 ordinary edit → r15 recover. It exercises synthetic `Details`/canonical association payloads, native projection/cache/index APIs and complete process exit. It creates no real editor blocks, account/CRDT state, transport or personal Space. Even successful execution returns `COMPONENT_STORE_PAIR_PASS`, with `full_F10=NOT_PROVEN`, export/Swift/UI gates open and feature disabled.

## Immutable identities and inputs

Both native source checkouts must be exact Heart `d98420b1113536afd08cde6de9a5816f6d27ffff` plus the appropriate reviewed patch. Source files must match every canonical inventory hash, and no changed/untracked source outside that inventory is accepted. Inventories are independently pinned by normalized SHA256, so an abbreviated or forged file list is rejected.

| Role | Patch SHA256 | Inventory SHA256 (LF) | Runtime capability |
|---|---|---|---|
| old r14 | `fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077` | `952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14` | 0 |
| new r15 | `5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2` | `f0e4a4c2d1b4c1baa11347362cfd18368ad272a8902b2beaf8de52270f809ee7` | 1 |

Binary bytes must match a declared SHA256, the exact revision marker and linked shared-fixture SHA. The r15 binary must additionally contain `pinkha-native-t5-lookup-v1-<r15 patch SHA>`; the r14 binary must not contain that full feature marker. Each phase checks and reports actual `vcs.GitCommit`, linked `vcs.GitSummary` and linked fixture SHA before opening any database. Artifact hashes and source inventories are rechecked before phases and after the complete sequence. These checks bind producer-declared artifacts and the prescribed build recipe; they are not a signature or independent build-provenance attestation. Preserve real producer build logs/receipts with these inputs.

## External build recipe — NOT EXECUTED here

The native integration owner may perform this only after the existing serialized lane permits it, using already available pinned dependencies. Do not automatically fetch SDKs/runtime archives or create another watcher.

1. Supply separate exact r14/r15 checkouts and their unchanged canonical patches/inventories. Use cached Go 1.26.5 and the already verified matching native/Tantivy library on the runner. Keep each build in an isolated Go workspace containing **only that Heart checkout**; do not override the old native packages with current `Modules/PinkhaHeart` sources.
2. Compute normalized LF SHA256 of `pair_phase_test.go`. Create a Go overlay JSON `{"Replace":{"<absolute Heart>/pkg/lib/localstore/objectstore/spaceindex/pinkha_t5_pair_phase_test.go":"<absolute repo>/Tools/PinkhaNativeDerived/compatibility_pairs/pair_phase_test.go"}}`. Refuse an existing destination; never copy over native source. The same fixture bytes must be used in both builds.
3. From each Heart checkout compile only the component test package, outside the source tree:

   ```text
   go test -c -p 1 -overlay <overlay.json>
     -tags "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"
     -ldflags "-X github.com/anyproto/anytype-heart/util/vcs.GitCommit=d98420b1113536afd08cde6de9a5816f6d27ffff
       -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=<summary>
       -X github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex.pairFixtureSHA=<fixture LF SHA256>"
     -o <external artifact path> ./pkg/lib/localstore/objectstore/spaceindex
   ```

   The displayed command wraps for readability; pass structured argv or real shell continuations. Old summary is `pinkha-native-derived-v1-<r14 patch SHA>`. New summary is `pinkha-native-derived-v1-<r15 patch SHA>-pinkha-native-t5-lookup-v1-<r15 patch SHA>`. Use `GOMAXPROCS=2`, `GOPROXY=off`, `GOTOOLCHAIN=local`, the isolated `GOWORK`, and the existing verified Tantivy link directory. Record actual commands, resolved dependencies, source hashes before/after, compiler exit, output binary SHA256 and linked markers. A compile failure is a real source/API finding; no native compile success is presumed.
4. Fill `manifest.template.json` with actual schema-1 `old` and `new` entries, each containing absolute `binary`, `source`, `inventory`, `patch`, plus `binary_sha256` and shared `fixture_sha256`. Use two distinct executable files. The supplied template deliberately contains missing prerequisites and cannot pass preflight; no current manifest contains actual binary artifacts.
5. On a POSIX native runner, call:

   ```text
   python3 run_pairs.py --manifest <actual manifest.json> --workspace <fresh nonexistent disposable directory>
   ```

   The workspace parent must exist. The controller never deletes/reuses a workspace, never accepts an existing DB, and preserves failure receipts/logs. Actual native execution is explicitly refused on Windows; Windows validation in this tranche is stdlib control testing only.

## Process/DB and sentinel contract

The controller selects exactly `TestTorahCompatibilityPairPhase`, once per phase, with a fresh report nonce/PID check and one named passing test, no skip/failure. Processes run in separate POSIX sessions with wall-clock and 8 GiB disk-reserve guards. The next phase starts only after exit code 0, completed `wait`, an empty process group, fresh report validation and explicit native store/provider closure. A timeout, live descendant, missing report/test, changed artifact or invalid sentinel fails the attempt and stops the sequence; only that owned process group is killed.

The first phase requires an empty controller-owned DB directory. Later phases require the existing nonempty `objectstore/test/objects.db`. The native fixture checks a controller ownership token and confines DB/report paths before opening. No phase recreates or imports a replacement database. The r14 return performs one ordinary synthetic title edit; canonical payloads remain untouched.

Each report carries canonical-byte SHA256 for the manifest and both document payloads, including unknown root/record/item fields; stable public projection sentinels; ready flags; cache proofs; and observed private row versions. All canonical/public sentinels must match the first phase. Each revision transition must actually complete recovery/recompute and change both cache proofs. r15 phases additionally prove version 1, private document+block membership, narrow public membership and actual sparse-index EXPLAIN. Old phases never issue the expanded query. Stale persisted version 1 on an old runtime is allowed as an observation and grants **no** runtime capability.

Common APIs were inspected from exact pinned `spaceindex/fixture.go`, `spaceindex/store.go`, `anystoreprovider/provider.go`, `database/filter.go` and [`util/vcs/vcs.go`](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/util/vcs/vcs.go), and both frozen patches (`nativeTorah`, `LastRecoveryStats`, `Identity`, public/cache keys). The shared fixture references only keys/APIs present in r14; new private keys are string literals. This is source inspection, not compiled compatibility evidence.

## Remaining F10/export/Swift gates

The component fixture cannot call actual editor/account `ObjectExport`. It explicitly reports `export_status=NOT_RUN_COMPONENT_NO_RPC` and `swift_pairing_status=NOT_RUN`. The controller rejects a component report claiming either PASS. It never sanitizes a source export to manufacture a successful sentinel.

Full product pairing still requires a separately source-verified **existing-account reopen/shutdown recipe** for this pinned SDK, two packaged/verified runtime artifacts, and a fresh product-created disposable account/Space. Do not create a new account each phase and call it the same database; do not treat this component-only DB as an app wallet. In that harness, obtain real `ObjectExport` JSON and Protobuf snapshots from each revision, parse real snapshot Details, preserve canonical/unknown/block data and the approved ordinary edit, and assert private lookup/version/cache fields are absent from exports. Include actual export bytes/hashes and linked runtime identity. Any old-runtime promotion/leakage is a failing gate, not a reason to strip fields in the verifier. Current `compatibility/roundtrip_test.go` demonstrates real export/import calls but creates separate accounts/Spaces and therefore is not a same-DB pairing proof.

For **new Swift + old runtime**, verified runtime capability must decide expanded availability. A persisted manifest/row private version 1 or a non-error/empty native filter result cannot grant capability. The real consumer must expose explicit unavailable or documented document-only coverage with block/quote/freshness limitations; it must not show a successful full-coverage zero. Test after a new→old downgrade that left observed version 1, using the actual new Swift consumer and old packaged runtime. This tranche verifies the control contract only; it executes no Swift/runtime pairing or UI.

**Execution gate recorded once:** missing independently built/verified r14/r15 component binaries with shared-fixture SHA, their exact source/build receipts and a POSIX native lane; product export/account-reopen recipe and packaged Swift/runtime artifacts are additional gates. Tomer owns the serialized native lane and subsequent real evidence handoff. No polling, download, second run/watch or owner-permission request is needed here. Feature remains `DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF`; T5/F10 remain open.

## Local control checks

```text
py -3 -B -m unittest discover -s Tools/PinkhaNativeDerived/compatibility_pairs -p test_controls.py -v
```

Synthetic report/process mocks exercise rejection/control paths only. They never execute a native binary or generate a native PASS receipt. Native fixture syntax is checked with `gofmt`; native typecheck/compilation and actual four-process execution remain NOT_RUN until the external artifacts/lane are supplied.
