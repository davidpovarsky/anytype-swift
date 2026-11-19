# Native properties, document Types and presentation preferences

`AnyNativePropertyStore` is the native Host boundary for ordinary properties,
document Type changes, collection membership and per-object property visibility.
It uses the live Any application's account/Space lease and the versioned Pinkha
native routes. The editor and association stores remain separate owners of their
respective canonical data.

## Read and presentation contract

`catalog(lease:)` returns bounded Type and Collection metadata, including hidden
definitions. Every document Type candidate is checked through the native
`canonical-editor-module-v1` policy. The visible list is presentation data; a
cached entry never authorizes a later write. The hidden built-in `page` Type is
intentionally a valid plain document.

`read(objectID:lease:catalog:)` returns the current Type, attached collection IDs,
the complete raw property row and its native full version, ordinary property
definitions, and the complete set of saved visibility keys. A supplied catalog
must belong to the same workspace, application generation and engine run.
Native target proof and an unchanged property-row bracket are required before
publication. Unknown and currently unattached namespaces remain in the raw row.

Each property key has an exact owner ID and property ID. The host receives
verified managed and hidden key/collection sets through
`AnyNativePropertyPolicy`; it does not infer internal fields from display names.
The verified hierarchy parent, position and folder fields remain managed by the
hierarchy controller, including membership in their owner collection. The
verified internal Note marker collection is also managed. `any.type`,
`any.collections` and `any.template` are not unrestricted value fields.

Source, Topic and Word are native derived association results. They are read
through `AnyGuardedTorahIndex`, outside the ordinary writable descriptor catalog.
They have no fabricated ordinary property IDs.

## Prepared writes and receipts

| Operation | Prepared command | Final native contract |
| --- | --- | --- |
| One ordinary property | `prepareSetValue` | Current writer, current descriptor kind/scope/membership and captured full property version |
| Change document Type | `prepareSetType` | The preceding checks plus the destination Type's current canonical editor declaration |
| Attach or detach an ordinary collection | `prepareAttachCollection` / `prepareDetachCollection` | Current membership and destination/current definition locks |
| Hide or show one field | `prepareVisibility` / `setVisibility` | The fixed presentation schema and a versioned update to its complete key set |

A prepared edit captures the original workspace, object, engine start time,
application generation, native full version, policy and relevant definitions.
It contains only the selected patch and its exact inverse; unrelated raw values
are never echoed into the write.

`apply(_:lease:authorize:)` repeats the current target, capability and definition
checks, and runs the real presentation authorization callback at dispatch.
The dedicated native route holds the target and relevant definition locks,
checks current native writer authority and performs the version precondition
through durable storage. The client's awaited prechecks are not an atomic
permission receipt.

The running engine must advertise `conditionalPropertiesSet=1`,
`conditionalMembershipSet=1` and `nativeDocumentTypePolicy=1`. A document Type
change additionally requires `nativeDocumentMembership=1`, whose final native
condition rejects a destination that lost its canonical editor declaration after
the picker was shown.

A successful native reply is followed by exact readback verification. A
`verifiedCurrent` receipt includes the new snapshot and a conditional Undo
prepared from the returned version. If the native operation was accepted but
readback cannot establish that version, the receipt remains explicitly
unverified and contains no Undo. The UI keeps its draft/prepared operation and
refreshes or reconciles; it must not replace it with a fresh unconditional write.
A stale precondition cannot be turned into an automatic retry.

Native numeric/date serialization is compared semantically without converting
large integer values through a lossy Double. The native millisecond precision of
date fields is handled explicitly. Unrecognized kinds and derived, local or
account-scoped descriptors are read-only.

## Visibility preserves stored content

The native fixed hidden collection is `pinkha_presentation_v1`, with one synced
array property `hiddenProperties` and
`xFormat.type = pinkha-property-visibility-v1`. The running engine must advertise
`nativePropertyPresentation=1` with the matching schema contract. Validation
uses the immutable IDs and declared schema, including built-in/hidden metadata.

Ordinary visibility keys use an unambiguous UTF-8 length frame:

```
property:v1:<owner-byte-count>:<owner-id>:<property-byte-count>:<property-id>
```

For example, `property:v1:3:any:4:name`. Derived display choices use
`derived:v1:pinkha-torah-native-v1:pinkhaSources` (or `pinkhaTopics` /
`pinkhaWords`); these are presentation choices, not writable business-property
identifiers.

There may be at most 512 distinct opaque keys of 1–4096 UTF-8 bytes each.
Unknown future keys are retained on hide/show. Removing a visibility key never
unsets a business value. Detaching an ordinary collection also retains its
native namespace values so reattachment can restore their display.

If the presentation collection is absent, `setVisibility` first attaches it
under the captured membership version, verifies that result, then prepares the
field update from the new version. If the second stage fails after verified
attachment, `visibilityAttachmentCompleted` identifies that partial outcome.
The caller refreshes; it must not imply rollback of the attachment.

## Executed validation

The source-bound component receipt is
`../PinkhaAnyEngine/Evidence/property-components-v1.json`:

- 13 property-store XCTest cases passed.
- 11 native block-creation Swift Testing cases passed.
- Zero failures or skips; production source manifest remained unchanged.

The real Swift/native receipt is
`../PinkhaAnyEngine/Evidence/native-property-client-runtime-v1.json`:

- 15 checks passed against the pinned v6 native binary.
- A newly allocated synthetic Page was changed to a custom document Type,
  undone and changed again, preserving its exact canonical body, child IDs and
  unknown style. New block creation used the explicit native policy while the
  legacy allowlist remained `["page"]`.
- Typed values, collection detach/reattach, visibility attach/hide/show, unknown
  future keys, derived display choices, conditional Undo and stale-version
  refusal were exercised through production Host APIs and actual native HTTP.
- The owned synthetic Page was deleted. The shared fixture's existing Type,
  Collection and documents were unchanged.
- Source, executable and native binary hashes remained unchanged during the
  run. The receipt contains their exact hashes and the build log hash.

That executable uses an explicitly scoped in-memory creation-metadata fixture
to allocate its temporary Page. It does not establish protected filesystem or
UIKit behavior. Those are covered by the separate Apple journal and native
application/UI lanes; this receipt does not substitute for them.
