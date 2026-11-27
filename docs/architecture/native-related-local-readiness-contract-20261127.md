# Native Any local-Space claims and related-result readiness

## Qualified scope

This document records the current native Any contract and the actual missing functional proof completed on 2026-11-27. It does not introduce a new endpoint or change production source.

The qualification covers the complete **locally available signed claims dataset** for one exact account and Space, plus the completeness of a canonical related-source query over that dataset. A successful local snapshot is not a statement that every remote peer has delivered its latest changes. It also does not certify arbitrary document bodies or the separate Heart per-document index.

Native binary SHA256: `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636`.
The unchanged 1,594-file source manifest is `12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c`, Any commit `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81`, SDK commit `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`.

Original functional receipt:
`/var/lib/pinkha-w1-engine-contracts-20261127/native-related-functional1/result.json`,
SHA256 `9e26b39507fcaf32fed97cc10f9ad8ff23e0c7a6f35fcde993ae831d6ea59f9c`.
Its exact public copy, response proofs, and manifest are under
`docs/validation/20261127-wave1-native-related-readiness/`.

## Routes and completeness

All routes are scoped beneath `/v1/spaces/{spaceId}/pinkha`.

| Route | Scope | Meaning on success |
| --- | --- | --- |
| `GET /claims?limit=N` | Entire installed native claims root | Every locally available signed row, including logical variants and predecessors, from one current-authority snapshot. `complete:true` concerns this bounded raw dataset. |
| `GET /objects/{objectId}/claims?limit=N` | One object's logical closure | Explicit `scope:"object-logical-closure"` and target identity. This may be complete for that closure while other objects have additional claims. It cannot substitute for the entire Space snapshot. |
| `GET /related?identity=...&limit=N` | One exact canonical source identity across the Space | Eligible related targets, semantic coverage, conflicts, and a native readiness generation. Completeness requires the semantic coverage/readiness checks below. |

The full claims limit is 1–10,000 records, with a 16 MiB encoded snapshot bound. Related query limits are 1–1,000 targets, with native candidate and target-fold bounds. Overflow returns HTTP409 `pinkha.read_limit`; it does not return a truncated success prefix. Invalid limits return HTTP400 `pinkha.invalid_request`. Candidate drift between discovery and the authoritative snapshot returns `pinkha.snapshot_changed` and must be treated as an unsuccessful read.

A raw claims snapshot can remain complete while semantic readiness is incomplete. An opaque operation is still valid signed history and remains in the full dataset; it must not silently disappear just because the current semantic projector cannot interpret its payload.

## Related-result readiness

A related response uses `contract:"pinkha-torah-native-v1"`, version1, the exact requested identity, targets, conflicting targets, `unsupportedClaimsPresent`, semantic `coverage`, and:

```json
{
  "version": 1,
  "state": "ready-local-snapshot",
  "generation": "<64 lowercase hexadecimal characters>"
}
```

`ready-local-snapshot` is valid only with `coverage:"complete"`, no conflicting targets, and no unsupported claims. Unsupported payloads yield `coverage:"incomplete-unsupported-payload"` and `state:"incomplete"`. Conflicts or pending observations yield `incomplete-conflict-or-pending`; consumers must preserve the independent unsupported flag when both conditions exist.

The native implementation first uses the index to declare dependency trees. It repeats candidate discovery, current target eligibility, block-path checks, and the signed fold inside a native read snapshot holding the required trees and current ACL. A new eligible candidate outside the declared dependency set causes explicit refusal. The generation hashes the native read stamp, contract, and exact target-input rows. The SDK stamp includes the ACL head, store generation, and sorted tree heads.

The generation is opaque. It can remain identical after a new process opens unchanged stored state, as observed in this qualification. It is neither an account identifier nor a process lease, remote convergence token, monotonic clock, or future write authorization.

The unsupported-row check is Space-wide: a valid opaque claim on an unrelated object invalidates semantic completeness for the queried source. The current conservative check includes retained unsupported signed history; this qualification does not claim that removing a live opaque association makes unsupported history disappear.

## Consumer obligations for Wave2 and Wave3

Use the exact active account, Space, engine/runtime source contract, and current consumer lease. Do not carry a readiness result across account/Space changes, lease retirement, engine replacement, or a new process merely because its digest matches.

For a related UI result that requires additional document metadata:

1. Read the native related response under current authority.
2. Refuse a complete-result claim if coverage is incomplete or any required input is unsupported, conflicted, missing, or over a bound.
3. Fetch the bounded metadata for those exact targets.
4. Re-read the same related query under the same active scope and require complete coverage, the same generation, and the same targets/semantic input identities before delivering the enriched result.
5. Recheck the consumer lease after asynchronous work. A changed generation or scope invalidates the whole composite result; do not publish a partial list as complete.

The existing `AnyGuardedTorahIndex` is the typed consumer of the indexed related route. `AnyGuardedTorahClaimsRepository` distinguishes full-Space snapshots from object-local closures. The runtime proof here exercises the native related HTTP route and the existing compiled Swift full-Space repository through `PinkhaAnyEngineProbe`; it is not a new UI or Apple-client acceptance result.

`canSafelyUnlink` is current-snapshot eligibility only. Any subsequent mutation still requires the exact signed operation identity, current write authority, and target-tree commit fence. Do not replace those checks with a previous read token. No adapter may silently fall back to generic stock queries, invent unsupported semantic mappings, rewrite opaque history, or broaden an object closure into a Space-wide claim.

## Actual functional evidence

The run reused a qualified retained semantic account archive on a new owned private copy. The original account/archive and the accepted 182-operation migration were unchanged. All native phases ran with OS syscall-level outbound denial, `NoNewPrivs=1`, `Seccomp=2`, zero local/global/network peers, and the same exact account and Space.

| Phase | Actual observation |
| --- | --- |
| Original local state | Three signed claims and one eligible related target. Existing compiled Swift repository read exactly those three claim IDs. |
| New canonical target | One fresh page and one signed canonical operation. Full snapshot grew to four claims; related targets grew to two, with a changed readiness generation. Repeated unchanged query returned identical bytes. |
| Object closure | The original object's closure still had three claims and explicitly declared its object scope, while the full Space had four. |
| Bound refusal | Related limit1 against two targets and full-Space limit3 against four rows both returned HTTP409 `pinkha.read_limit`, without success records, targets, or a readiness token. |
| Unrelated opaque target | A second fresh page and one valid signed opaque operation. Full snapshot contained all five claims, including `unsupported-opaque`; the same two canonical targets remained, but global semantic coverage became incomplete and its generation changed. |
| Crash and cold reopen | Actual SIGKILL of native PID3118221; a different native PID3118375 opened the same owned store under OS denial. All five native rows were byte-equivalent, semantic coverage remained incomplete, and the compiled Swift repository read exactly the same five claim IDs. |
| Cleanup and provenance | All eight native/Probe process groups positively absent; all source files, Probe binary, original archive and runtime configuration unchanged. |

The native run completed in 9.064 seconds. It made two page creations, two signed association appends, and the two explicit bundle-ensure calls performed by the existing Probe append path. These are recorded before dispatch and in the actual receipt. It did not replay the original migration or issue a replacement account, invite, grant, or engine build.

The already compiled Probe SHA256 is
`034a594b7e77ae13566a52b400f5535c4bf1aa045630b9b1da9b18aa8d9a2e40`.
Its complete Swift package source closure matched the accepted component receipt
`25a6c48dfb95dec2689682bdf80da6798dabb1a670f769f740e2357de7c8882e`,
and the retained original build log witnesses the Probe product. No Swift, Go, or Apple compiler was run for this qualification.

## Remaining boundaries

This tranche does not claim remote-peer convergence, mixed-version network requalification, concurrent-writer race injection, new ACL-revocation coverage, Heart whole-Space readiness, a public Apple bridge, UI/visual acceptance, or release readiness. Existing accepted evidence for unchanged boundaries remains separate and is not replayed or relabeled. Heart's per-document index needs its own authoritative-head/transaction/projection proof; that work is owned by the cutover lane.

The live two-target, five-claim owned test account is retained with its failed-coverage opaque record for exact future work. Private account files and native diagnostic logs remain at their original private evidence paths and are not included in this public handoff.
