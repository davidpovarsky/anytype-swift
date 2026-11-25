# Original native MiniApps methods in the unified application

The original `NativeDocumentPublicationTests.swift` is referenced directly by
`AnytypeTests`; there is no copied fixture or additional application product.
The five existing MiniApps methods keep their real native operations, original
readback and durable acknowledgement assertions. All other method bodies remain
byte-identical. The only fixture change selects the exact qualified combined
runtime under `PINKHA_DUAL_ENGINE_RUNTIME`, and preserves the original native
profile otherwise. No assertion accepts the runtime merely because it is linked.

The test target declares the five existing Any package products explicitly.
`PINKHA_ANY_NATIVE_ARTIFACT=verified-unified-v1` resolves the existing runtime
through the same ProtobufMessages/Lib binding used by the main app. There is no
second Go binary. The next shared `build-for-testing` must compile this target;
no Apple compilation or runtime acceptance is claimed by this source review.
