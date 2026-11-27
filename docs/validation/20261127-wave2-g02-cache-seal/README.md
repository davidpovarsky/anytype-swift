# G02 correction: observe renewal of the original Native8ac local cache seal

This is a narrow source successor to `63fb8c03749f7bad44cc183c6d35503e1217a48c`. It corrects a source-level blocker identified by Wave3 in HQ51 comment `1220943874817094`: a valid document Word unlink changes `_pinkhaTorahCacheIntegrity`, but the first reader treated that field as stable. No G02 runtime failure was observed; the future consumer has remained closed. The original source, inverse, reviews and control attempts remain preserved in their original commits and evidence directories.

## Exact correction

Only `AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift` changes. Five reversible edits add a named seal key, a shape validator, validation at the existing per-document boundary, this fifth specific field in the comparison exceptions, and a required seal change after the existing exact Word-removal checks. The one hosted selector and its baseline/postflight phases remain unchanged.

Each actual document seal must be a native JSON String with exactly 64 UTF-8 bytes, each in ASCII `0`–`9` or `a`–`f`. Missing, null, scalar non-string, uppercase or non-ASCII representations fail. Baseline and postflight retain the entire raw seal inside the unchanged `NativeObject.fields` and `protobufDetailsJSON` receipts. Postflight requires the actual seals to differ. It also explicitly requires changed canonical bytes and their SHA-256 values after proving that only the selected document-scoped Word record was removed.

These are observations of an opaque native cache seal. They do not independently recompute or authenticate that seal, establish full-Space index freshness, or prove whole-store retention. The private native binding generation is not separately certified by this reader. The underlying canonical, projection and field comparisons remain the substantive Properties assertions.

## Why the original seal changes

The source of record is the retained Native8ac archive, SHA-256 `c70592e4ae160cbb5cb8eda3cb1caed08f727476a5c9fac7c207593cd9315830`, 26,130,845 bytes. Root extracted and independently verified `heart/core/pinkha/torahindex/recovery_cache.go`, 3,529 bytes, SHA-256 `325fb4f2b2abcbaa9afdc5bd32dd42f1c95b8fa524641d624bed9c309fe13352`; its exact bytes and custody receipt accompany this correction. The other six exact source files remain in the original `20261127-wave2-g02-native-readback/native8ac` evidence directory.

The original chain is explicit:

1. `torahindex.LocalDetails` resolves the native binding, clears prior local fields, and calls `project` for current editor details.
2. `project` calculates canonical-derived values and defers `sealCache` until those calculations finish.
3. `cacheProof` hashes the `pinkha-torah-cache-v2` domain prefix, native manifest generation and canonical key, selected identity/eligibility fields, every local projection output except the seal itself, and the exact canonical raw bytes. The original `hex.EncodeToString` returns lowercase hexadecimal.
4. `LocalKeys` includes `_pinkhaTorahCacheIntegrity`; `LocalDetails` returns it to the original smartblock adapter, which adds it to Object.Show local details.
5. The smartblock adapter may subsequently add AttachedProperties and null representations for empty attached Properties. Rehashing the final Swift Object.Show JSON would therefore not reproduce the original pre-adapter Go/protobuf seal input. No cross-language hash implementation is added.

The native source itself describes this seal as a disposable local cache check. Its authentication and transport semantics are unchanged.

## Comparison policy retained

| Field or record | Required baseline/postflight relationship |
| --- | --- |
| Canonical raw payload | Exactly the baseline document Word record is absent; all other records and unknown JSON values remain equal. |
| Canonical native digest | Equals SHA-256 of the observed canonical bytes in each phase; both bytes and digest change. |
| Word projection | The actual derived identities are empty after unlink; only the original engine's absent/null/empty-array zero-value representations are permitted. |
| Native label map | Exactly the selected Word identity is removed; every other entry remains equal. |
| Native cache seal | Actual String of 64 lowercase ASCII hex bytes in both phases; the two observed values differ. Raw values remain retained. |
| Source, Topic, block-only associations, other native fields | Existing exact comparisons remain unchanged. |
| Type, name, real Tag option and Tag Property | Existing identity/value comparisons remain unchanged; no seal exemption is applied to Tag objects. |
| Engine clocks | Only the already declared `lastModifiedDate`, `lastOpenedDate` and `lastUsedDate` exceptions remain; raw values stay retained and validated. |

Account, Space, the three original writing IDs and types, original fixture bytes, reserved type-switch exclusion, native directory identity, actual command/phase custody, and original PID/cold-open checks are unchanged. The full original 84,286-byte preparation prefix and every prior assertion are retained; reversing only the five recorded edits restores the exact `bd988815…` full source and `0f8623ee…` suffix.

## Validation and future admission

The independent editor contract and exact-successor source reviews are retained unchanged. `source-inverse.json` and `source-edits.json` bind the exact source correction. The final exact source passed Linux Swift syntax parsing (`-frontend -parse -swift-version 6`) in 1.523 seconds with exit 0 and an empty log. Its separate receipt is `swift-syntax-attempt1.json`, SHA-256 `dbe48e90e513bda59973a82fb30dc91056265ffa0bbb9a1e203a0d7e182485d4`. This is not Apple type checking, macro validation, Native execution, XCTest execution or visual acceptance.

The source chain requires this successor plus a separate exact control-pin update over `831a7dfb90164c55fa87c32273f2f61062d52c92`. Neither the old nor the corrected G02 source is part of the current `8f2c1171…` App. The four-stage consumer remains unconditionally closed until a separately qualified future shared product supplies both exact compiled G02 sources and all original admission evidence. This correction changes no Native engine or protobuf contract and performs no Native calls or Mac work.
