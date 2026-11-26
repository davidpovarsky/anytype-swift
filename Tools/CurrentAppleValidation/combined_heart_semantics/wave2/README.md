# Wave 2 Page154 controller profile

`prepare_wave2_page154_profile.py` prepares a new, immutable controller directory for the existing six Page154 methods. It consumes the finalized shared App16 intake maintained by the editor lane. It neither builds nor tests the application.

The complete shared App16 admission must be produced from the actual successful App/UI build. Its source is `a089ff29a5c0a7e415aac800844505f099a5561d`; its native manifest is `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`. The generated Page154 admission differs only by its controller SHA and the pinned copy of that canonical shared admission. At execution, the shared intake verifies the producer, runtime identities, source inventories, compiler inputs and every original product before any XCTest invocation.

## Retained original evidence

App15's original `preparation`, `mounted` and `linked-ui` stages passed. The original JSON-only attachment collector subsequently rejected a real PNG. Its failure remains recorded separately from the corrected typed collector `39cb1d84f78efb922b71dc55ccb371647c90296093e365452b1291ef854aacf6`.

The later `linked-native-enumerate` step ended with its original 180-second `OWNED_TIMEOUT`, without invoking the test. Its result SHA is `bcfa06bea94cc0ce89541dc3e165160d6574ce1c9f551c56857102a24d00a5e0`. Neither failure is replaced by preparing or running the new profile.

The retained fixture expired at Unix time `1795689170.211263`. Both the compiled application and the original validators enforce a 7200-second lifetime. The new execution therefore uses a fresh, disposable account and reruns the required preparation, mounted selection and link steps before continuing to the three incomplete stages. The expiry guard, original deadlines and original assertions remain unchanged. App16 also contains the editor focus correction, so the new UI evidence must be bound to that product.

## Preparing the profile

Run the preparer after the shared build and its canonical admission are complete. Provide absolute paths and actual SHA-256 values:

```sh
python3.12 -B prepare_wave2_page154_profile.py \
  --historical-controller-root /absolute/retained-original-control \
  --shared-controller /absolute/final-shared-control/combined_heart_semantics_current.py \
  --shared-controller-sha256 ACTUAL_FINAL_SHARED_CONTROLLER_SHA256 \
  --canonical-admission /absolute/final-shared-control/admission-app16.json \
  --canonical-admission-sha256 ACTUAL_SHARED_ADMISSION_SHA256 \
  --typed-helper /absolute/semantic_link_route_typed_attachments.py \
  --output /absolute/fresh-page154-control
```

The historical directory must contain the six exact files pinned in `ORIGINALS`. They come from the retained App15 controller and the published E donor `4488a43443cbb09e25f02ae593d8cc8cb3d2b470`. The preparer validates every byte, rejects an existing output directory, retains the original owned command lifecycle, and verifies a reversible delta for the Page154 controller and supervisor. It records unchanged stage/result/source/retention definitions in `prepared-profile.json`.

The only runtime profile changes are the canonical App16 admission/helper pins, an explicit source/controller check, and the already reviewed typed JSON/PNG attachment collector. The six method selectors, 180-second enumeration, 900-second execution, fixture lifetime and private-account retention are unchanged.

## Running after the shared Mac handoff

Use the generated supervisor with the SHA of the generated `admission-app16-page154.json`, a fresh execution root, and a separate fresh supervisor root:

```sh
python3.12 -B /absolute/fresh-page154-control/run_retained_heart_semantics_replacement.py \
  --admission /absolute/fresh-page154-control/admission-app16-page154.json \
  --admission-sha256 ACTUAL_GENERATED_ADMISSION_SHA256 \
  --root /absolute/fresh-page154-execution \
  --supervisor-root /absolute/fresh-page154-supervisor
```

Execution preserves original `xcresult` bundles, stdout, screenshots, independent native readback and account state. A failing test remains failed even when retention succeeds. Preparing a profile is not product acceptance; full E acceptance and physical-device coverage remain unclaimed. Inspect the actual UI screenshots after execution, alongside the native witnesses, before reporting the scenario accepted.
