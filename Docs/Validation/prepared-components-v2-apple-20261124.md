# Prepared native components V2 — actual Apple acceptance

The single new component journey passed on the dedicated Mac at 2026-11-24 20:25:12 UTC. Original XCTest evidence records **1 method passed, 0 failed, 0 skipped**. This is one test containing the component checks below; the internal phases are not additional tests.

## Source and artifact

- Actual app/controller: `3fb2ab3715173741cd4baabe01d588bade294891`.
- Actual Any: `cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3`; SDK: `e195f6c07a053c6588e39ffe72ee4fc44cf3d953`.
- Native version: `v0.5.0-pinkha.prepared.components.2`.
- Native manifest SHA256: `816a4385bc980cf4865db752a137ef96a54cdb56caf89099d33e0c5f0f78daf0`.
- Native archive SHA256: `d2b501b1d196789d9a03e85ba2bde7c4c9446f63047339645842a6cbbd5ac4cb`.
- Compiler: verified Go1.27.4, Xcode27.0/27A266a, actual iPad Air 13-inch M4 ARM64 Simulator iOS27.2/24B8117.
- Producer local UUID: `a0c1a508-a1ed-4de8-8072-722401da2c51`. Build uses the preserved shared compiler cache, two Go workers and 6GiB GOMEMLIMIT; it executed zero tests.
- Consumer local UUID: `ffa9f5d3-f9dd-4019-b963-623befb77c91`.
- Original consumer receipt SHA256: `1e24393b7ca2cb88ec7d628aa16267ff74a073b02d56e0fe8b04c475b284fed2`.

## Actual exercised behavior

The selected method is `AnyPreparedComponentsV2RuntimeTests/testManagedDefinitionsDeferredPropertiesAndFullFilesSurviveReopen`.

It creates five actual native definition plans: a custom type, collection, an atomic six-record part with two datasets/fields/index, and type-owned and collection-owned properties. It reads the compiled schema through ordinary APIs in all three runtime generations. It creates two documents of the custom type and two editor blocks. The collection property is absent from immutable creation, then set through the actual managed Swift durable-property wrapper using the original native revision; both signed SET identities are preserved across status/commit and both reopens.

Two full files of **4096 and 2097152 bytes** are prepared, reconciled after native store reopening, committed, then read byte-for-byte over ordinary native HTTP. Both files retain their original reserved file/object/change/root identities, metadata, Unicode filenames, MIME, sizes and plaintext hashes. The final journey has three distinct runtime generations, three owner generations, two orderly reopens, six document readbacks and four full plaintext content readbacks.

Original XCTest summary/test tree and the exact observation attachment were exported without rebuilding products. Source and compiled product inventories match before/after. The owned simulator shut down and deleted successfully within 3.70 seconds; independent device inventory and process checks show no residue. All 41 exported evidence members were independently verified byte-for-byte after transfer to Oracle. The original XCTest and component auditor were then readmitted from those original bytes on Oracle. No account credential or synthetic Actions identity was used in the evidence.

## Preserved failures and practical limits

The original V1 actual XCTest failed at collection property creation with `type.not_a_type`; its original receipt, artifact, source and preceding bootstrap failures remain preserved. The V2 native fixes were independently qualified by two focused Linux HTTP methods, retaining their earlier failed attempt. The original V1 test is not relabeled as passing.

This qualifies the coherent native artifact and public Swift wrappers for the exercised component journey. It does **not** establish whole-Space semantic mapping/completion, source history replay, network synchronization, physical-device validation, an OS-process crash or injected lost acknowledgement. Earlier independent Linux crash controls retain separate provenance.

The sibling JSON receipt records the exact hashes, counts, scopes and original paths. Complete Mac xcresults/products remain in `/Users/m1/builds/anytapy-prepared-components-v2-3fb2ab37`; verified exported originals are in `/mnt/development/projects/evidence/prepared-components-v2-20261124/apple-originals`.
