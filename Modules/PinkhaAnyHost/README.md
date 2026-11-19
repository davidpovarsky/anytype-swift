# Pinkha native Any host

This module owns one new-engine account/Space session and native document I/O.
It does not activate the old Heart application or claim whole-app parity.

- A session leases work against one account, Space, generation and engine
  `startedAt`. Revoke cancels and drains outstanding work before runtime switch.
- Complete bounded native block snapshots retain IDs and unknown style data,
  reconstruct deterministic depth-first order, and expose unreachable blocks.
  Text export refuses incomplete or oversized selections and labels native
  **inline Markdown** honestly; it does not masquerade as stripped plain text.
- Interactive text and RTL/alignment changes use a compiled native conditional
  block patch. Whole-document Markdown replacement is not an editor adapter:
  its diff can recreate block IDs and detach existing associations.
- Native block writes require BOTH `ifVersion` and `ifStartedAt`. The native
  extension validates all patch operations before dispatch and uses the SDK's
  atomic `IfUnchangedSince` under the object's write lock.
- Undo/redo operates on only the original edited fields and uses the exact
  version produced by the write. A concurrent edit or engine restart refuses
  the operation. Unknown style fields and block identities are left intact.
- Stock Any v0.5.0 intentionally refuses the extra conditional fields. There is
  no unconditional fallback, fake capability bit, or client-side CAS claim.
- Permission/readability checks accompany I/O; these are not proof of a
  cross-object transaction or a native UI/selection owner.

The source overlay implementing conditional blocks is built and tested against
the pinned native engine separately. Host tests and a compiled probe are recorded
with source hashes; no physical-device/UI acceptance is implied.
