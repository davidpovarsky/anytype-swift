# Current qualification — 2026-11-27

The actual current8ac core registry, native signed Begin/import/Seal/unlink, account stop/reopen, and divergent-source retry refusal now pass. The exact 40-file source is in `native-core-current8ac-qualified.json`; the original receipt, complete native patch, failure history, and acceptance limits are in `docs/architecture/20261127-heart-cutover-native-core/README.md`. Generated RPC, new-process crash recovery, peer transport, and Apple activation remain separate gates. No application capability is enabled by this core qualification.

The earlier design/candidate description below is retained for context. Its historical source and open-gate list are superseded only where the dated qualification provides actual evidence.

# Heart legacy association cutover — typed protocol candidate

This directory is an implementation candidate. Its byte/identity component tests do not establish native ACL, peer synchronization, Swift integration, migration, or application acceptance. The current production v1 association tree and wire remain unchanged. No application capability is enabled by these files.

## Source authority

The native baseline is the complete 4,855-file unified source manifest 410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9. Its retained source archive SHA256 is eba6a0354006c9cfc363c4769bd08951d3b4be4ef3fa8a65eb0cde9b6376e008. It includes the original full Page154 overlay, the actual T2 native operation/ACL guards and the separately qualified source-capture default-limit correction.

The existing core/block/editor/torahops/native_host.go validator accepts exactly one Create in _pinkha_torah_claims_v1. New metadata must never be inserted into that v1 tree: older readers would reject its history. The cutover therefore requires a separate versioned native host and an explicit capability boundary. Existing real add/remove/replace claims, their author binding, their current/historical ACL checks and their physical IDs retain their original semantics.

## Retained source and deterministic identity

A Plan retains the exact native property key, a separate presence bit, and all original UTF-8 bytes. Missing, present-empty and differently formatted JSON are distinct. The shared Swift source codec must regenerate and compare the complete facts from those retained bytes, including unknown envelope/record/item fields, numeric precision, record identity, exact source location and semantic-anchor ownership. The Go contract retains these canonical fact bytes; it is not a second implementation of that source codec.

Plan identity includes exact Space/object owner and complete sorted fact bytes, but no actor, request ID, scheduling order or unrelated native tree head. A signed Begin separately retains the native target heads observed with that property under the actual target lease. The property remains unmodified after cutover and is never deleted as cleanup.

The import operation identity is deterministic per plan, fact and actual native author. Equal source facts written by different accounts do not silently become identical native operation bytes. Every original physical claim and change/creator/ACL receipt remains available. Explicit semantic coalescing is allowed only after complete canonical equality through the shared policy; divergent content and native conflicts remain visible.

## Separate durable phases

1. Explicitly prepare/approve the exact retained Plan. A native Begin checks current account lifetime, target/settings lease, current ACL, exact property and target heads, then appends immutable typed metadata in the new host.
2. Import each fact through the existing real v1 association append. Preserve frozen operation bytes and actual author; never generate a new identity to disguise a retry.
3. Append the Import metadata in the separate host only after independently reading the actual v1 claim and native receipt. The metadata names the physical claim, native change, original creator and captured ACL head. Its own signed author may be another authorized writer.
4. A Seal binds the complete fact-to-claim bindings and every observed immutable Import metadata identity. It revalidates exact property, current native authority and all references. A nonempty plan cannot be sealed without coverage of every fact.
5. Reads never begin, import, seal, delete, repair or migrate. A sealed read independently checks retained source/fact completeness and actual signed histories before presenting the existing v1 projection. The retained property is not unioned back into it.

There is deliberately no atomicity claim across the v1 operation tree and the versioned metadata tree. If the actual v1 append succeeds and the second phase is interrupted, the durable result is unfinished work. Resume must re-read and reuse that exact claim, keep the original failure/receipt, and finish metadata explicitly. A successful Seal is independent of later normal remove operations.

## Concurrency and older writers

The target lease is a local authority and serialization boundary, not a distributed lock. Two offline writers may sign independent Begin/import/Seal records for the same exact plan. Their signed provenance is retained; same-fact variants may be coalesced only by the explicit complete-canonical policy. A different property snapshot, owner, plan or claimed fact remains unresolved divergence.

An older writer may still change the retained property or the v1 operation tree. Such changes must be independently observed and preserved. A property change after Seal is an explicit conflict; it cannot silently reset the seal or restore legacy content. An imported variant arriving after another imported variant of the same fact was removed/replaced must remain a conflict, including an interrupted second-phase metadata append. Never treat arrival order, a local sequence number, one client's lock or a single complete seal as proof of global synchronization.

Every referenced import must be verified against actual immutable v1 history, not merely a caller-supplied receipt or an operation's self-declared author. Absent local history is unavailable, not proof of global emptiness. Permission or account retirement before/after await must refuse operations through the existing actual native lifetime/ACL/target gates.

## Remaining activation gates

- Separate native root/type/registry and typed metadata StoreState handler, preserving the v1 validator byte contract.
- Actual same-account target-property/heads reader and signed metadata author/ACL binding.
- Native receipt read and complete coverage/conflict/resume checks, including crashes between trees and late offline imports after unlink.
- Original protobuf/generator source changes and generated Swift/Go bridge, with explicit runtime profile identity.
- Shared Swift cutover planner/read policy and real Heart repository adapter; no read-side automatic writes.
- Actual independent writers, older native reader compatibility, account/ACL retirement, cold/offline reopening and application/UI acceptance on the new producer.

All those gates remain open until their actual results are retained. The pure contract tests only qualify bounded encoding, immutable ownership of request bytes, deterministic identities and complete provenance fields.
