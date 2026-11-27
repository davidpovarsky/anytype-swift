# Attachment list metadata projection

This is a separate downstream correction over published upload source `f731e30409b7b479d9ed5e87280624485c181da8`. It is **source preparation only**; no test, compiler, Native, UI, simulator, physical-device or storage acceptance is claimed.

## Concrete mismatch

The original list-row initializer required `name` and `mime` to be present and used byte limits 1024 and 255. The published e96 typed native metadata reader permits the two fields to be absent and preserves received values with resolved-name and MIME byte limits 16384 and 1024. A legal unnamed or longer-metadata response could therefore be refused by the Attachments list after the Host had accepted it.

The change is confined to `AnyNativeAttachment.init(_:objectID:)`: absence uses the existing empty-name behavior and empty-MIME `application/octet-stream` fallback. A present null, number, boolean, array or object still fails the original invalid-metadata error. The exact byte bounds increase to 16384/1024. The original file ID, object ID, size, cached/durable, root CID, content comparison and scope checks remain intact.

Every byte outside the row initializer is unchanged. In particular, there is no transport change, MIME spelling normalization, name replacement, MiniApps call-site change, UI identifier change, upload/recovery change, authorization change, or new inline-field guard. The native owner is still confirming the exact original FilesV2 list's inline-field requiredness. This source does not infer that answer from the upload metadata carrier.

`source-inverse.json` restores the complete f731 source. `source-binding.json` ties that preimage to its actual GitHub source readback and the unchanged published e96 metadata authority. The correction stays separate from the upload source so the two changes remain independently reviewable.

## Declared regression coverage

The new `AnyNativeAttachmentMetadataTests` calls the actual production row initializer; it does not substitute a decoder or create a Native fixture. Its conditional envelope matches the production type (`canImport(UIKit) && canImport(HanlinMiniAppsBridge)`).

| Method | Declared cases | Boundary |
|---|---:|---|
| `omittedAndEmptyMetadataPreserveExistingFallbackAndContentComparison()` | 1 | Missing and empty values; supplied spelling; existing name/MIME/root content comparison |
| `nativeMetadataByteBoundsAreAcceptedButNotExceeded(field:)` | 2 | Exact name/MIME byte limits and one byte above; multibyte Hebrew name |
| `presentWrongTypesAndInvalidIdentitySizeOrStateRemainRejected(invalidCase:)` | 10 | Present null/wrong types; invalid file ID/foreign object; size; required state |

Total: **3 methods / 13 declared cases, all NOT_RUN**. W3 must include the new original-target `PinkhaAnyUITests` source in the actual compiler inventory and execute it against the matching future App. No existing suite is replayed or granted new acceptance by this source packet.
