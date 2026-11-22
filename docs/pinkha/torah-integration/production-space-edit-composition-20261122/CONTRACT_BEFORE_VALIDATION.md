# Original source binding: additional Space edit restriction

Status: exact candidate applied on the isolated combined Participant/Space base, source reviewed; focused controls and native Apple acceptance are still pending. No runtime caller is changed.

## Existing authority, frozen generations

EditorDocumentWriteSourceBinding.requiringSpaceEditPermission(participant:spaceView:spaceId:) adds a restriction to an already bound operation. It first validates that original source binding and requires its already captured account token. Each opaque permission must match that exact original account source and token and the byte-exact requested Space.

The private copy preserves the original source lifetime, every existing capture, private account capture, optional parent owner (including nil), currentness closure and exact named-RPC restriction. It appends only the two captures returned by the original Participant and SpaceView permissions. It never reconstructs a capture from a current lifetime, fetches a replacement permission, or manufactures a parent owner.

The unchanged original SpacePermissions initializer evaluates its actual participant/SpaceView values. Its local-mode argument comes from the same original Container serverConfigurationStorage.currentConfiguration().middlewareNetworkMode expression. No caller Boolean decides permission. The native canEdit predicate allows writer/admin/owner in a regular Space and additionally requires owner for a legacy stream. Local mode affects other native fields and does not change native canEdit.

The completed binding is validated again before it is returned. Original performOperation/prepareDispatch then carry all captures through their existing per-RPC lease and admission/drain mechanism. The original committed-event binding remains account-scoped exactly as before; it is not a new annotation identity or write receipt.

## Limits of this component

SourceBinding has no destination Space field. This method therefore does not certify a host selection, runtime destination, annotation type, object identity, creation attempt, body application or acknowledgement. The later host must bind its actual selected destination to its source generation/currentness before exposing any production operation. An existing document Owner is not new-object creation authority.

No new public facade, constructor for the opaque permissions, native RPC, caller, bootstrap, schema registration, persistent mapping, outbox acknowledgement or framework route is enabled. Original Participant and Space source files and their published evidence are preserved. The producer retry remains on a separate frozen branch. This unused internal restriction does not enable a user-visible feature or remove existing Debug/simulator admission guards.

## Retirement and actual admission

Retirement before original permit.begin refuses a new native admission. If the existing admission wins, its already-admitted work may finish while retirement waits for the original captured lifetime drain. There is no claim of instantaneous cross-thread revocation or rollback.

The original SourceBinding performs a final validate after its awaited operation. It can therefore return rejected(.retired) after admitted work already occurred. A failed return is not proof of no side effect. Nothing here resets a durable creation fence, repeats native creation, marks an exchange applied or returns a current-owner receipt after retirement.

## Focused new validation plan

Ten new groups are planned, using complete unchanged actor declarations to obtain opaque permissions through their original publication methods, the full actual Owner/Lifetime/Operation/InvocationDispatchBinding, and the unchanged native SpacePermissions implementation. Existing decoded-input/DI/publisher/subscription probes will be reused with explicit limits; no native decoder, Combine, RPC queue, Heart or Apple behavior is inferred.

1. Original regular/legacy role matrix and local-mode independence.
2. Missing frozen account capture.
3. Different account source and equal-ID replacement generation.
4. Exact participant/view Space identity.
5. Existing source/additional captures/currentness and nil parent preservation.
6. Original inherited parent and named-RPC restrictions.
7. Participant role retirement between permit preparation and begin.
8. Space view retirement at the same original admission boundary.
9. Already-admitted capture drain and failed return after recorded probe side effect.
10. Restored permissions cannot revive an earlier composed binding.

The existing 16 participant controls, separate deinit control, 22 Space controls, 52 policy controls and Owner/SQLite packets will not be replayed. New raw failures, assertion changes and execution receipts will remain source-bound. Actual Apple compilation and production runtime integration remain independent open gates.

## Provenance and rollback

Base: d33a41338bd0a56326fd02c05977c10d1c4c7baa. One original file changes: Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift. The original private account and optional-parent boundary cannot be preserved by a downstream helper without exposing or reconstructing authority; the reviewed narrow member avoids that widening.

The exact inverse removes the new private copy initializer, internal composition method and Services import and recovers the original b0ae source bytes. All preexisting whitespace and comments remain unchanged. The initial proposal is retained; only newly added comments were removed before testing to follow the repository iOS guidelines. There is no stored-data migration.
