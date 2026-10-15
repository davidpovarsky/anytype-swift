# Pinkha on Anytype — Schema Versioning

All Pinkha metadata payloads are explicitly versioned and forward-compatible.

## 1. Space Manifest (`schemaVersion: 1`)

Stored as an internal Anytype Object:

```json
{
  "schemaVersion": 1,
  "parentPropertyId": "rel_parent_xyz",
  "orderPropertyId": "rel_order_xyz",
  "documentAssociationsPropertyId": "rel_assoc_xyz",
  "folderTypeId": "type_folder_xyz",
  "bookFolderTypeId": "type_bookfolder_xyz",
  "registeredDocumentTypes": {
    "chiddush": "type_chiddush_xyz",
    "article": "type_article_xyz",
    "research": "type_research_xyz"
  }
}
```

## 2. Document Torah Associations (`version: 1`, compatibility codec)

The existing wire shape remains decodable and deterministically encodable:

```json
{
  "version": 1,
  "items": [
    {
      "id": "assoc_1",
      "kind": "ref",
      "role": "context",
      "providerID": "sefaria",
      "externalID": "Genesis.1.1",
      "canonicalKey": "בראשית א:א",
      "labelHe": "בראשית א:א",
      "labelEn": "Genesis 1:1"
    }
  ]
}
```

This scalar JSON shape is **not** selected as T2's canonical persistence backend.
Heart replaces the scalar value, so two stale read/modify/write clients can lose
one another's additions. Unknown future versions fail before a write; unknown V1
fields and item IDs survive a decode/re-encode cycle.

## 3. Torah Source Quote (`version: 1`, compatibility codec)

The legacy wire shape remains readable:

```json
{
  "version": 1,
  "providerID": "sefaria",
  "externalID": "Bava_Kamma.2a.1",
  "canonicalKey": "בבא קמא ב.",
  "labelHe": "בבא קמא דף ב ע\"א",
  "labelEn": "Bava Kamma 2a",
  "readOnly": true
}
```

It is not written to a block by T2. Whole `BlockSetFields` replacement can also
erase unrelated concurrently updated fields, and actual quote block creation is
owned by T4.

## 4. Rich Source Quote Provenance (`version: 2`, portable codec)

V2 adds an optional `provenance` object with an explicit UTC capture timestamp,
provider/canonical reference, raw reference-provider response, the complete
`TorahTextDocument` (including original raw provider JSON and version/license),
and UTF-16 excerpt offset/length. The codec sorts keys and uses RFC 3339 UTC
timestamps with fractional seconds. V1 remains unchanged and no missing field is
invented during migration.

## 5. T2 persistence status

No manifest version or native storage schema is installed in T2. The audited
client API exposes neither compare-and-swap for scalar details/fields nor a
client-supplied idempotent identity for ordinary created objects. The proposed
future schema is immutable native association-operation records with stable
client operation IDs and an indexed Space/target lookup, but it remains blocked
until Heart exposes the missing primitive and it passes disposable real
middleware plus two-client/offline convergence tests. See
`torah-integration/ADR-T2-STORAGE-CONCURRENCY.md`.
