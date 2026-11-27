# Separate native editor Hanlin acceptance hook

This narrowly scoped future source change connects the published SDK helper to the existing native editor. It is based on typography commit `33e31c64ca9e35e258a4d64cfe8690b08a6cbc39` and is separate from the future block-menu/typography UI tests. The current shared App source `8f2c11713fb8a40ae13444104723666ffef68afe` is untouched.

Wave3 supplied the exact call contract in D comment `1220944170013821`. The helper was published in `680364279e08dc69d7d7eee8f6f13169ea8d0be4` and its exact blob `6098155a07a5dbafd10c9b380d8ccee8b8f0e8fd` was independently read unchanged from integrated commit `4fd8f76917178dc9257192526a2225ded128f83f`. The destination source must include that helper before this hook is compiled. This branch deliberately does not duplicate or alter the SDK helper.

## Change and preservation

Only the existing call to `AnyHanlinPresentation.present(...)` changes to `try await AnyHanlinPresentation.presentFromNativeEditor(...)`, passing the existing `presentation.client` as required by the published API. The helper retains the original default locale. No new import, environment setter, permission switch, fixture materializer or native write path is introduced in the editor.

The original `presentHanlin()` function is 1,262 bytes with SHA-256 `350a4b1c22e61427b7cccd1c347a9df5e77df5304e4564cee46a9c60a4e5a3cc`. The source inverse restores it and the complete typography editor byte-for-byte. Focus cancellation, weak-self Task, flush/pending-edit refusal, creation authority and services, error reporting, weak chat capture and mounted lifetime revoke/drain remain unchanged. The native source owner continues to validate actual mounted scope and account ownership.

## Conditional behavior

| Build/route | Source behavior of the published helper |
| --- | --- |
| Release, simulator or device | The conditional acceptance implementation is absent. The async helper immediately returns the original `present` factory result. |
| Debug on a device | The same ordinary factory route; simulator acceptance code is absent. |
| Debug simulator, no explicit Save acceptance request | Both `loadIfRequested` calls return nil; the helper returns the original factory result. |
| Debug simulator, preparation request | The original SDK helper validates the exact request and performs original mounted native reads under the current lease, then records real process/runtime/source evidence and presents the ordinary create-only host. |
| Debug simulator, fresh fixture | The helper requires the exact preparation receipt, same process/runtime/source, current native authority and creation workspace before the existing acceptance factory and original driver can run. |

These are **source projections**, not compiled or runtime results. The new editor call is async in every UIKit build because that is the SDK's published API. No claim of byte-identical Release machine code is made. The SDK conditional removes the special acceptance route; the original factory remains the ordinary behavior.

The existing request/fixture code enforces a 3,600-second lifetime, exact source/run/attempt/custody/native identities, same process and a single-use result directory. This hook changes none of those checks. They are distinct from Page154's unchanged 7,200-second fixture contract. Model transport may be fixtured only by the SDK-owned driver; native results, ACKs, permissions and full-body readback remain actual.

## Evidence and remaining gates

The source package records the exact editor inverse, actual helper/fixture/preparation/factory source hashes, conditional projections and independent source review. Historical waiting-contract metadata remains retained in the earlier preparation artifact; it is not rewritten as though the contract had already existed.

Apple compilation, full UI test compilation/enumeration, actual preparation, visible confirmation, native save/readback, visual review and physical-device acceptance remain **NOT_RUN** for this hook. No Mac, simulator, settings, compiler or component cache was touched. The separately published SDK baseline selector does not cover Stop, replacement, cold/lost ACK or full both-engine Save acceptance. Production Save activation, Release acceptance and distribution remain outside this source hook.

The original canonical 129-source preservation map is unchanged: this downstream PinkhaAnyUI source is outside that original map, as Wave3 explicitly established. Its exact source inverse and reviews are downstream evidence, not additions to the canonical map.
