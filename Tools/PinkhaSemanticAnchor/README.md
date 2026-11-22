# Additive native semantic-anchor capture candidate

This candidate adds a typed Heart capture operation that compares the current text and every native mark under the current document lock before adding one internal link marker. It is not registered in generated RPC or exposed as an App capability. Legacy text editing, buffered typing, Undo and existing offset features keep their current paths.

## Source boundary

The base is Heart `d98420b1113536afd08cde6de9a5816f6d27ffff` plus the exact 139-file coherent patch qualified by native run `45026227924`. `native-source.json` lists nine additive Go files. None replaces a file in the qualified 139-file inventory; no original native source or generated wire is regenerated. The original patch SHA is `2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00` and inventory SHA is `05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0`.

| Added seam | Responsibility |
| --- | --- |
| `pkg/lib/pinkha/semanticanchor` | Versioned request/receipt, exact current text/all-mark comparison, bounded UTF-16 scalar ranges and canonical marker/digest rules |
| `core/block/editor/torahopsobject/semantic_anchor_lease.go` | Current native document/cache/tree and signed settings deletion checks; one-call, request-bound lease; native signed-storage acknowledgement |
| `core/block/editor/stext/pinkha_semantic_anchor.go` | Refuse pending native typing, compare snapshots under the lease, add only the new mark, use ordinary Apply and verify its actual post-state |
| `core/block/editor/pinkha_semantic_anchor.go` | Additive Page adapter to the native text component |
| `core/pinkha_semantic_anchor.go` | Typed native entry through the existing native writer application lifetime and current local write authority |

## Write and acknowledgement contract

The native entry obtains the existing writer application lifetime before loading the Space and target. It does not borrow a read-publication lease. The new lease follows application lifetime → settings → document lock order. Loading happens before the settings/document locks. Once locked, it verifies the actual cache identity, live tree/ACL/Space identity, native deletion state and signed settings deletion history. The target must be a reachable Page/Template text block in the complete bounded current document. The marker must not already exist in that document.

The text component refuses a pending `lastSetTextState` before invoking `NewStateCtx`; the existing flush hook discards Apply failures and cannot safely establish this new capture's precondition. It compares current text and the complete ordered native mark snapshot, including marks outside the selected range. It rejects existing links in the capture range and does not use an ordinary text overwrite as a surrogate for additive mark capture. The native contract validates scalar-safe UTF-16 boundaries; grapheme selection is the shared Swift capture layer's responsibility, and the Go contract does not claim a complete Unicode grapheme algorithm.

The document mutex and settings lease remain held through ordinary Apply, exact text/all-mark post-read, and the stored change witness. A native NewState hook cannot silently invalidate the precondition: both current and child state are checked again. Normal restrictions, events, hooks and Undo flags remain active. A nil Apply result alone cannot acknowledge success because the existing Apply path can return nil when an earlier hook aborts the write.

The post-read requires the planned text/all-mark state and a new native change ID. The witness reads actual native storage and heads, verifies the signed change's identity, author, parents, read key and current ACL head, and returns its SHA-256. Any post-Apply failure, mismatched state, missing durable witness or changed current authority is an uncertain result. The candidate does not blindly roll back a possibly committed native change.

The application lifetime is inherited from the existing native writer path. The ordinary native writer retains its own write-policy and ACL checks. This candidate does not add a new atomic ACL/storage transaction or claim knowledge of unreceived remote revocations. The stored signed-change witness verifies commit identity; complete production Page payload replay and reopen are separate required acceptance.

## Focused validation selection

Five pure standard-library contract methods already passed on Go 1.26.5/Linux. Their original JSON log and source receipt are in `retained-contract`. The controller verifies those exact bytes and methods without rerunning them.

The new native CI route compiles all three required packages before executing any method. It selects only the following new scopes:

| Package | New top-level methods | Expected terminal cases | Evidence scope |
| --- | ---: | ---: | --- |
| `core/block/editor/stext` | 4 | 14 | Actual text/state diff with controlled Apply and native-witness faults; pending edits, changed text/all marks, no-op/failed Apply, post-state and authority failures |
| `core/block/editor/torahopsobject` | 4 | 12 | Real signed native ACL/tree/storage with a controlled loaded-object/cache adapter; held/released locks, one-call lease, stored witness, signed downgrade, deletion/reachability/duplicate/cancel refusals |
| `core` | 1 | 1 | Invalid/cancelled typed entry rejects before requesting an account; the complete native typed entry compiles |

These nine methods are not a complete production Page/account/wire journey. No success is inferred before their real execution. Exact parent/child sets, package, pass count, missing cases, unexpected old methods, failures and skips are checked from Go `test2json` output. Previously completed package results are written immediately so a later failure has bounded reusable evidence.

Four new Python controller checks have passed once. The original raw log and 14-file source/input closure are committed under `docs/validation/20261122-semantic-anchor-native-candidate`. `retain_controller.py` reads and validates those original results in CI; it does not execute them again. Seven new Go files were parsed/formatted by the actual Windows Go toolchain; the two contract files were compiled by their original pure-contract execution. These checks do not claim that the three native packages have compiled.

## CI recipe and next gate

`.github/workflows/pinkha-semantic-anchor-native.yml` is a reusable workflow accepting the exact shared `source_sha`. The existing main dispatcher needs a dedicated call to this route before dispatch; no dispatcher file is included in this isolated package.

It uses the already qualified musl recipe: the fixed Go 1.26.5 Alpine image digest, `build-base`, the pinned Tantivy archive, unchanged native `go.mod`/`go.sum`, and the previously qualified genproto workspace replacement and checksums. It restores compatible `.t2-cache` compiled dependencies. Cache entries never replace source guards or count as executed test evidence. The local WSL environment does not have the required Heart native environment verified; its vips probe was missing and Docker integration was unavailable. This route avoids treating the successful pure standard-library controls as proof that the full native environment is ready.

The route applies the original frozen 139-file patch, invokes its existing exact source verifier, adds only the nine explicitly inventoried files, and then verifies the exact 148-file candidate before/after builds and execution. It preserves the original module graph. Candidate binaries use a separate `pinkha-semantic-anchor-native-candidate-v1-…` version, never the qualified production139 identity. No production Apple framework is built or installed.

The resulting artifact is `Pinkha-Semantic-Anchor-Native-<run>-<attempt>`. A successful receipt can claim only `PASS_NATIVE_SEMANTIC_ANCHOR_COMPONENT_AND_STORAGE_CONTROLS`, with nine new top-level methods and 27 terminal cases. Full Page Apply/reopen, concurrent real edits, account stop/select races, wire, both mounted engines, clipboard/split/merge/Undo and Apple acceptance remain open. The App capability stays off and EDITOR-02 remains incomplete.
