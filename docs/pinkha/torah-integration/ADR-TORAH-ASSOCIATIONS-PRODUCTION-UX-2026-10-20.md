# ADR — Torah associations as normal native editor UX

Date: 2026-10-20  
Status: Accepted for isolated feature branch; device acceptance pending

## Context

Physical iPad testing found that block associations appeared after restart while
document associations did not appear, mutation required a disposable-trial
activation wall, linked blocks could not open the real Inspector Sheet, and
several labels ignored the app language.

The canonical v2 payload already stores document and block records together in
one native document property. Document records have `blockId == nil`; block
records have the exact block ID. Native mutations are serialized per document
and verified by readback.

## Decision

1. Keep one canonical native property and its v1/v2 lossless codec. Do not add a
   second store, migrate user data or rewrite on read.
2. Replace the session's mutable optional block target with an explicit
   `{spaceId, objectId, scope}` context. Load one record snapshot, index block
   records in memory, and accept an asynchronous result only when both request
   identity and context still match.
3. Remove every trial activation control and hidden opt-in guard. Genuine
   native permissions, target existence, Space isolation, serialized mutation,
   future-version refusal, readback, conflict and uncertain-write states remain.
4. Attach a UIKit custom accessory to linked editor cells. Its one-tap action
   opens a single REF in the existing Kit `.torahInspectorSheet`; multiple or
   typed items use the scoped management chooser. No text-view or collection
   double-tap recognizer is introduced.
5. Treat locale as presentation state. Persist both provider labels and stable
   identity, render via effective SwiftUI locale, and reconfigure accessories
   on locale change. Existing editable quote bodies are never migrated; new
   quote bodies omit the locale-dependent citation suffix.
6. Derive a Hebrew segment reference only for a provider-backed, simple
   two-level numeric section. Hebrew numerals include 15/16 exceptions and
   punctuation. Daf, ranges and deeper schemas fall back instead of fabrication.
7. Pin Anytype Core/UI consumption to one immutable Kit revision. Keep bundle
   identifier `com.gloiiire.anytype.torahtrial` so a compatibly re-signed IPA can
   update the existing sandbox in place.

## Root cause and evidence

The host previously launched unstructured refresh tasks from
`presentSearch(targetBlockId:)`. Each task later read the same mutable target and
assigned a shared `currentAssociations` array. Switching block → document (or
the reverse) could therefore display a late result from the old scope. Repository
codec and target-isolation tests show the native scalar model already preserves
both record kinds. The regression test delays the old block response and proves
it cannot replace a newer document context after the change.

This is a code-based diagnosis of a host routing/display race. It is not proof
that every prior physical-device write reached middleware; the owner must repeat
force-close/relaunch and canonical readback checks on the authenticated iPad.

## Consequences and limits

- Cell rendering uses an in-memory document snapshot, not one `ObjectShow` call
  per row.
- A single linked verse opens exact section + preferred segment in relationship
  mode. Topics and words are never cast to verse selections.
- Existing links and unknown payload fields are retained without migration.
- Independent cross-device scalar merge remains unproven. This limitation is
  documented, but is not exposed as a user activation gate.
- Apple SDK, SwiftUI and UIKit verification is authoritative only on Xcode CI;
  authenticated physical-device behavior remains owner acceptance work.
