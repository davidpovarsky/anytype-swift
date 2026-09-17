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

## 2. Document Torah Associations (`version: 1`)

Stored in `pinkha.torahAssociations` property:

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

## 3. Torah Source Quote Block (`version: 1`)

Stored in `pinkha.torah.sourceQuote.v1` block field:

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
