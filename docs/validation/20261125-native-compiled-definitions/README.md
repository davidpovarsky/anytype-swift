# Actual compiled resolver descriptors — native capture and Swift readback

Date: 2026-11-25.

## Source and accepted result

- Shared Swift reader product: `26ca6a30c8da4bcffc9b9987c951985842235757`, based on C `2093f722018d3ef0f1813a1a302d8dba43628e7a`.
- Qualified Heart source: `5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5`, extending `a2916b27eaa16fc291f438fe620b3d09bc0a85e0`.
- Exact native delta: eight paths; `native-source-a2916-to-5e8f9.patch`, 35,658 bytes, SHA-256 `2b34a87f54acd9394900af817bb4df21f0713c679e306cbbcc927c5bccfd4104`.
- Native exported Service signatures and the `pinkha_loaded_account_witness` build tag remain the same. The combined producer owner must incorporate this qualified source delta and generate its next exact runtime profile; existing `70fb5342...` app proofs remain bound to their original source.

The actual native source capture now retains the compiled resolver definitions it really used. Each is an original native `Relation` or `ObjectType`, with its generated protobuf bytes and a hash-bound JSON view. These entries are separate from captured account trees and objects. They do not invent a source object identity or destination permission.

The native checkpoint also retains and revalidates this bounded descriptor set after a fresh real account/session/ACL/native-source read. Captured schema overrides retain priority. Colliding captured identities cannot silently fall back to the compiled table. Missing or changed native descriptors are refused.

The Swift bundle reader verifies each new member, complete ordered identity census, native message kind, key, path, digest, size, raw-protobuf/JSON binding and aggregate bounds. It preserves original descriptor bytes and unknown descriptor fields. A historical bundle that contains only fallback names receives an explicit missing-descriptor issue; the reader never fills old evidence from a newer runtime.

## Actual native qualification

The final run `job_43f7db3da1cd` returned PASS/exit 0 in 19.10 seconds (18.595 seconds inside the controller). It executed three descriptor methods plus the affected existing real loaded-account checkpoint method. All four top-level methods passed, including nine descriptor subcases; no failures or skips.

Complete original log: `/Users/m1/builds/anytapy-migration-default-final-20261125/evidence-native-compiled-5e8f9ce4ec78-attempt3/original-native-go-test.jsonl`.

SHA-256: `a014f77f3129e562627d172594e9344d9ba30b7f1a12b45f50b76115d91429ae`, 1,831,985 bytes. The full native debug log remains private. The public evidence below retains the original result, launch data and selected original Go JSON events with a complete-log hash and path.

The checks exercised:

- The seven actual compiled relation definitions used by the original 156-object source, plus the actual compiled Page type. Native protobuf decode and native generated JSON decode both equal the full original model.
- Absent, explicit null and empty-string optional defaults remain distinct.
- Nested native struct/map defaults preserve every value while repeated resolution keeps the first exact captured wire representation.
- Changed bytes, JSON, receipt hashes, message kinds, keys, duplicate identity and order are rejected.
- An actual captured property overrides its compiled counterpart. Ambiguous captured identities remain rejected.
- A real LocalOnly native account capture produced 143 objects and 144 native trees, including six actual compiled definitions and twelve descriptor members.
- The original real checkpoint method still checks nil/zero checkpoint refusal, unregistered native sessions, revoked full sessions, cancellation, fresh full-session reauthorization and actual source-row mutation. The added control verifies the exact private produced member bytes and rejects a changed compiled-descriptor checkpoint after a fresh native authority read.

All 2,579 tracked native source members matched before and after execution. The original qualified native module replacement, Go 1.27.4 toolchain path and transformed pinned Darwin Tantivy dependency were reused. No combined native producer or file/T2/default suite was duplicated. The narrow run used two Go workers and a 2 GiB Go memory limit, with a measured 512 MiB compiler/test allowance plus 16 MiB fixture estimate and a 2 GiB emergency free-space stop. Minimum observed free space was 3,508,895,744 bytes; no resource stop fired.

## Actual native-to-Swift interoperability

The original produced source bundle was copied read-only to a private Oracle evidence directory. No account store, seed or private credential was transferred.

| Original artifact | SHA-256 |
| --- | --- |
| Native source manifest | `04b9309e1b96918c47d1b00eed6b1a76b2e13432636a0aba77706f2f69082994` |
| Private fixture identity context | `f68679409eaf93676b346eed7e2e9bd31146674956c634081268f36303f527b9` |
| Original private transfer archive | `7c8e69f2cd9fd546e532725c285d2188448b677007503afe040bcdf85f2b9bdc` |

The native bundle is 300 files / 1,418,012 bytes including its manifest. Its 299 declared original members include all object protobuf/JSON pairs, the opaque native source witness, and twelve compiled-definition members. The transfer receipt hashes every original file; source bytes were checked before and after copying.

Swift job `job_223a278dd806` passed the exact actual-capture reader method, 1/1, zero failures/skips. Log SHA-256: `848ae082fec6e17c7bcf92071a852a34bc21e1b9ed078f4306fe82106e1d8690`. It verified 143 objects, 144 trees, all 299 declared members, the exact six descriptor identities, absent default-field presence, original manifest integrity and continued refusal to grant source/destination admission.

Before that actual readback, `job_fa62e37d906b` passed ten affected controls: nine bundle-membership controls plus the original real 156-object source diagnostic. Log SHA-256: `83433b938212c0d6bf4b57b63b0ed7bebe76f8e4cf2db72cffc429aced568dd8`. The original historical bundle's missing descriptors now remain explicit. The 143-object fixture does not replace or relabel the original 156-object source evidence.

These are eleven distinct Swift methods across the two runs. The actual native capture and Swift readback are interoperable component proof; they do not prove complete destination migration, app UI migration or fresh-process source restoration.

## Root causes fixed, failures preserved

1. Native candidate `86e58ae8bc3da2f13727b95f263d8e84a73aa451` failed because the pinned gogo generated `Relation` and `ObjectType` implementations explicitly reject `proto.Buffer` deterministic mode. Original log SHA-256: `f119525d81c4b37ae7ad9bd69e6883a46e10bd90495903aabe0c560065329dd7`. No candidate was admitted for delivery.

   The correction uses the actual original generated native marshaler. It retains the first captured protobuf bytes. The checkpoint independently validates those original bytes and their generated JSON view, then compares the full decoded native model to the actual current compiled registry. Native map encoding order therefore cannot be mistaken for a semantic change. Private receipt buffers are immutable copies, bounded to 16 MiB in total; deserialized scalar metadata cannot manufacture them.

2. Candidate `d6e7c08b7d3a56677355d1787196e999cbfcb462` passed the actual checkpoint and two descriptor methods, but the protobuf/JSON equivalence method caught another real defect: `EmitDefaults: true` rendered an absent optional `google.protobuf.Value` as JSON null. Native JSON decoding then created an explicit NullValue. Independent wire inspection confirmed that protobuf field 4 was absent in all six real source descriptors while the JSON field was present as null. Original log SHA-256: `d80dea43931a1c2ece5039ccd7a8ccc1726f1c0c4d2fa40c50badd16c4e10583`.

   The correction uses the original native JSON marshaler's omission of absent fields. It retains explicit null when the Value actually exists. The full native `proto.Equal` assertions remain unchanged and now pass, with additional absent/null/empty and nested-value controls.

No original failure/result was overwritten. The fresh final run supplied the final PASS.

## What the real 156-object source still requires

The unchanged original manifest is `cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4`. Its seven fallback names are not retroactively replaced with the newer capture's descriptors.

The current field-usage inventory shows that no fallback values occur on either of its two user pages:

| Compiled key | Actual current uses in the 156-object capture |
| --- | --- |
| analyticsSpaceId | One Widgets object |
| apiObjectKey | 126 relation definitions, 20 type definitions, four options |
| headerRelationsLayout | One type value; twenty type relation links |
| homepage | One Widgets object |
| migrationObjectContext | One Widgets object |
| orderId | Four options and one type |
| relationFormatIncludeTime | 120 relation definitions |

The inventory is retained with hashes and exact native type counts. This narrows the remaining adapters to actual schema, presentation and account/space-context behavior. Descriptor byte capture alone does not qualify those behaviors.

Task C remains open for complete source semantic admission and end-to-end destination/reopen comparison. Native layout mappings, read-only/derived source semantics, collections, original settings/history, and other remaining scope must be implemented or preserved through qualified native/shared contracts. The new target SDK reserves derived scope for its built-ins and rejects dynamic derived properties; the adapter must not convert old read-only definitions into writable shadows.

All native `HasNativeSourceAdmission`, `PermitsDestinationWrites` and full-space-completeness flags remain false. Existing independent-peer file, cold target reopen, prepared-executor and default/description proofs stay in their separate source-bound milestones.

## Retained locations

- Original private native capture: `/Users/m1/builds/anytapy-migration-default-final-20261125/private-source-capture-native-compiled-5e8f9ce4ec78-attempt3/`.
- Private read-only Oracle capture: `/mnt/development/projects/evidence/migration-final-20261125/compiled-definitions/private-native-compiled-capture-5e8f/`.
- Public proof source: `/mnt/development/projects/evidence/migration-final-20261125/compiled-definitions/`.
- Native source donor: `/mnt/development/projects/worktrees/anytype-heart-source-capture-bridge-20261125`.

The public evidence manifest below hashes every copied file. Private source contents, original account stores and full raw native debug logs remain excluded from Git. No GitHub Actions run is invented for these direct SentinelX executions.
