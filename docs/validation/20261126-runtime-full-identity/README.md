# Exact native and Swift runtime identity

The original App14 build at `76f59f1e838991d1bbc7a07ecd08c6a2f15915c7` remains a successful build. Its actual original Drag UI method failed before native account creation; no drag behavior was exercised. The original UI showed the application/engine version mismatch and disabled both account creation and restore.

The compiled `PinkhaUnifiedRuntimeProfile` had the correct11619 manifest/version suffix but still expected Any commit `cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3` and build date `2026-11-25`. Both original successful native linker commands actually set commit `41c07bd32e95a54824a3d3c5d592accf5074ab68` and date `2026-11-26`. The retained native source constructs the full string through Mobile.Version → embedded.Version → version.String. The strict Swift equality check is unchanged.

`runtime_identity.py` now derives the manifest, source commit and date from one closed contract. It checks the exact consumer profile, both successful original Apple-slice commands/receipts, five unique linker assignments, target, package/tag closure and the pinned native version construction sources. This is a static source/receipt gate; it does not execute MobileVersion or establish application acceptance.

## Actual focused qualification

Thirteen Python controls passed with zero failures/skips. They reject the exact original compiled App76 profile, accept an in-memory corrected historical profile against both actual11619 linker receipts, and refuse wrong consumer commit/date/manifest, duplicate assignments, mismatched actual linker commit/date, wrong target, failed bind, changed native formatter, missing device slice, and reuse of11619 binaries for the future8ac consumer. No App/native compiler or native API was invoked by these controls. `result.json` retains every case and exact original source-before/after hashes.

The production candidate changes only the profile constants/construction and the corresponding T5 runtime manifest pin. `profile-source-delta.json` records complete-file inverse checks. Runtime startup equality, lifecycle, account authority and UI assertions are unchanged. The future profile requires Any8fbd/SDKc1fd, manifest8ac and date2026-11-26. Native slices and actual application qualification for that candidate remain pending.

The separate native producer candidate derives its actual linker flags through this same helper and records the complete expected native string. It refuses to run until the original mixed-peer permission-boundary qualification is pinned. The following main-app producer must additionally call `qualify_application` on the pinned assembly inputs before starting Xcode; source/receipt checks do not substitute for the original actual UI/account readiness check.

## Original failures and retention

Original Drag execution SHA `5fdaf8b6b3d282e6c040964fca71fe1018d80fad8805cd1c8f76b3bc0327b48b`:1 failed method,0passed,0skipped. Original213 entries including xcresult/logs/movie were retained offhost in archive `8f7fea3fec349f8826526efbb26a828932d624a30023a81cff641127f9296264`; verified retention `f129848142abdf35b21905c880daf8728e64e721a3cc2ac0eb97cea385ad7223`. This is not a full simulator-account backup claim.

Separate Heart MiniApps App14 attempt1 execution `2ce146a369cb38b79e1b449cdc929449fc5e5259d2c117af1a8b0c978f1860a5` failed in enumeration after360s, followed by EPERM, with0test commands/0methods. Its later independent kernel observations found owned groups41438/44255/53318 absent with zero signals; originalFAIL remains unchanged. Account retention/continuation is a separate gate.
