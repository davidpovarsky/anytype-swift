# Optional native index freshness proof

## Scope and invocation

The existing account route keeps its four-process compatibility contract and 24
actual JSON/Protobuf exports. The reusable workflow
`.github/workflows/pinkha-t5-account-pairs.yml` adds the boolean input
`include_freshness`, default `false`. The root dispatcher may expose
`t5_component=index-freshness` by calling this workflow with that input set to
`true`. The producer does not edit the shared dispatcher.

The additional mode runs the same hash-bound native test method once more in a
fifth, separately launched r15 process, after all four compatibility processes
have closed successfully. It selects the original synthetic account and Space,
preserves the original account-key and state-file hashes, and first verifies
the original canonical payloads, ordinary r14 title edit, and real block
sentinels. It does not create another account, Space, object, or block.

The source remains Heart `d98420b1113536afd08cde6de9a5816f6d27ffff` and the
reviewed r14/r15 patch inventories from App source
`947fbde24d5657d0e1229f45bb3993648884a8a1`. No production Heart or Swift
code, patch inventory, dependency pin, or product flag changes.

## Actual fifth-process observations

The test writes through the actual native RPC adapter and queries the native
index **before** opening the updated object with `ObjectShow`. There is no
explicit projection/reindex helper or Swift cache invalidation. This is a
native external-write boundary; it does not claim a second networked client.

| Observation | Native operation and required result |
| --- | --- |
| Document reference update | Move Genesis 3:3 to 3:4; old membership disappears, new private and public membership appears. |
| Document unlink | Remove the canonical record; document remains live and both memberships disappear. |
| Display-label alias | Change Hebrew/English labels; canonical identity and memberships stay unchanged. |
| Provider separation | Move the provider while retaining the textual canonical key; memberships move to the new provider only. |
| Block reference update | Change the Note's block reference; private membership moves, public document-only membership stays narrow. |
| Note/block unlink | Remove the Note's block record; Note and original block remain live. |
| Source-quote update | Change the quote's reference; private membership moves. |
| Source-quote unlink | Remove the quote record; original document and block remain live. |
| Foreign record Space | A mismatched canonical Space cannot produce private or public membership. |
| Foreign record object | A canonical record targeting another object cannot grant membership to its container. |
| Malformed canonical JSON | Membership disappears and live details explicitly report malformed/unready. |
| Archive cycle | Archive removes membership; unarchive restores it and the original canonical bytes. |
| Type cycle | Actual Page-to-Note-to-Page changes preserve canonical membership and return actual distinct type IDs. |
| Block target deletion | The native canonical candidate remains, while the actual live block graph proves the target is unreachable. |
| Source-quote target deletion | The same distinction is measured for a quote target. |
| Object deletion | The deleted document disappears from the index and returns a specific native not-found/deleted response. |

The first eleven probes each restore the exact original canonical payload,
including unknown fields, before continuing. The type cycle may legitimately
change ordinary Page/Note presentation. The last three probes intentionally
mutate only the disposable account after compatibility/export acceptance.

## Receipt and evidence boundaries

A successful request retains `phase_reports` as the original four reports and
adds a separate `freshness_report`. It requires two actual ELF binaries, five
distinct native PIDs and nonces, five named passing invocations without skips,
and the original 24 exports. The fifth report contains exactly sixteen named
observations, native RPC counters, actual canonical payload bytes and hashes,
and actual live graph nodes. Python independently derives reachability from
those graph nodes and checks the expected membership changes.

Exactly 22 canonical writes, two archive calls, two type changes, two block
deletes and one object delete are allowed in the fifth process. New fixture
creation, exports, unrelated RPCs or explicit reindex calls are rejected. The
actual account stop and cleared-application response are required before
`AppShutdown`; its unconditional acknowledgement alone is insufficient.

Evidence publication keeps the existing all-candidates-before-copy secret
scan. Only requested fifth-phase JSON/text logs are added to the allowlist;
the account directory, key, mnemonic inventory and private work remain excluded.
The existing native binaries are retained separately for inspection.

## Acceptance limits

`PASS_NATIVE_RPC_MUTATIONS` proves only the declared observations on these
three indexed synthetic targets. Coverage stays `indexedTargetsOnly`,
`space_wide_freshness=NOT_PROVEN`,
`host_target_exclusion_status=NOT_RUN_SWIFT_HOST`, and
`swift_pairing_status=NOT_RUN`. The App's live-graph exclusion and navigation
still require real Apple/Swift evidence. The native index intentionally does
not traverse the editor graph; a deleted block can leave a canonical index
candidate that the App must reject using fresh `ObjectShow` data.

The product feature flag stays disabled. The Python rejection tests and Go
formatter/parser do not count as native execution.
