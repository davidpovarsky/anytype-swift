# AnyCrypto generated framework export repair — 2026-11-21

## Current status

Portable source controls passed **163/163**, with zero skips, errors or failures. All six original test files and all 143 original identities/assertions are unchanged. Twenty new controls cover the specific export mutation boundary, native-tool failures, distribution isolation and complete read-only diagnostics. Synthetic tool fixtures grant **zero native signing, Apple build, editor UI or consumer runtime credit**.

Parent: `7fb63538482265e703e462d8a8066402641d1b07`.
Isolated branch: `codex/otzaria-original-editor-package-seal-20261121`.
This preparation has not been pushed or dispatched.

## Observed failure and source scope

Original v7 run44830592801 built the original framework successfully and passed its143 source controls. The actual next strict command on AnyCryptoSwift_4B7B7B8889D5B5C4_PackageProduct.framework exited1: code has no resources but signature indicates they must be present. Its exported closure contained only the128048-byte executable and784-byte Info.plist. The framework build log contains linking and plist processing, with no bundle CodeSign step.

The existing Amplitude constrained export signer succeeded in that same run. Therefore the recorded blocker is specific packaging, not evidence of a missing codesign capability or missing private identity. This repair uses the same genuine owned-export ad-hoc command; it never signs the producer or bypasses strict verification.

Exactly four downstream CI/test files change: one new isolated signer/diagnostic helper, one new20-case control file, a narrow integration in the existing driver, and the exact-identity runner extended143→163. Original app sources, Modules, project, resources, package pins, Amplitude helper, consumer, SDK, Heart and workflow are unchanged.

## Exact mutation boundary and Native-unverified assumptions

Only the exact generated AnyCrypto product from PackageFrameworks, at the original any-crypto-swift revision0d7429888f8ec60d1730341ff1122d5ddf0ff1ab, is eligible. Original producer/export bytes must match. Both must first reproduce the exact observed native strict failure. A different diagnostic or an already valid signature refuses signing.

The original executable must be thin ARM64 MH_DYLIB with the exact install name and iOS Simulator platform. Its signature must occupy terminal LINKEDIT. The new signature offset and all load-command shapes stay exact. Every executable/nonsignature LINKEDIT byte is compared, with only20 bytes of allocation-size fields masked: LINKEDIT virtual size, LINKEDIT file size, and signature allocation size. The new virtual size must use16KiB native allocation rounding. Only the ad-hoc three-slot signing envelope, with empty requirements/CMS and no entitlement slot, is admitted. Slack is limited to31bytes and must preserve the exact prior bytes or zero extension. The code limit remains the unchanged original prefix boundary.

These layout/allocation assumptions are deliberately fail-closed and **not Native-proven for this generated product** by the portable controls. They draw on the existing observed Apple signing route; a different actual shape must retain evidence and fail for review. The actual native strict verifier remains responsible for complete code-page/resource validation.

All original file kinds, modes, owner/group, flags and extended attributes must remain unchanged; no mode is silently normalized. Info.plist remains byte-identical. Only the executable signature allocation changes and a new_CodeSignature/CodeResources is added. The source producer is observed again after signing and verification. Before/after executable and resource bytes are retained, including failure. Complete distribution inventories prohibit any unrelated file-byte change or added/removed file. The original per-framework strict check, public symbol-graph check, separate consumer build, embedded-byte checks, runtime observations, final SDK/source checks and cleanup remain mandatory.

## Diagnose all generated products in one run

Before the first framework acceptance stop, a read-only diagnostic pass executes strict verification and signature display on every generated PackageProduct export. Expected tool failures are recorded for each product, then the original acceptance loop still enforces its unchanged fail-closed checks. No other product is repaired.

The diagnostic compares original/export closures before and after each command and captures bounded exact pre-sign files plus CodeDirectory display metadata. Its status is OBSERVED_ONLY_NOT_QUALIFIED and cannot grant consumer acceptance. The existing evidence packager carries these attachments; no qualified framework artifact or new publication route is introduced. Retention is capped at16MiB total. The seven v7 closures total 6464616 bytes, so all fit that cap; exceeding the cap records hashes and an explicit bytes-not-retained reason.

V7 retained no executable/CodeDirectory bytes or strict result for the later six PackageProducts. Their status remains **NOT_RUN_UNVERIFIED**. Absence of CodeResources alone is not classified as a defect. V7_PACKAGE_PRODUCT_OBSERVATIONS.json records the exact observed file inventories and the limit of the historical evidence. The new small unqualified attachments permit subsequent isolated packaging diagnosis without rebuilding2238 Swift inputs; they cannot stand in for the full exported consumer closure.

## Original Host and route check

Live relevant refs still identify v7 as the newest published original framework route. Published Host076fc7c7 and owned Apple-v2a298c556 are ancestors of v7. The Host handoff records83 Foundation controls and11 syntax parses, with actual Apple typecheck, native mounting, editor input and Maktabah/live save NOT_RUN. The public framework facade still exposes inspectResources() only. Active shared-editor/shared worktrees belong to a separate route, were read only, and were not substituted. HOST_HANDOFF_AUDIT.json records this boundary.

## Exact source-fixture verification and retained failed attempt

The first local163-case run passed153 and failed10 because git archive exported CRLF text for the PBX and installer fixtures. That attempt remains intact. No original assertion was changed. All24 baseline inputs were then retrieved using raw git cat-file blob bytes and independently matched to immutable7fb Git blobs, SHA256 and lengths. The original binary package archive was already byte-exact and was not fetched again. With the same candidate behavior and canonical fixtures, the exact163-case runner passed completely. RESULT.json binds all tested candidate bytes and the original fixture inventory; both runs and raw logs are retained as deterministic gzip.

## Admission before any future Apple run

The candidate is intentionally **NOT_ADMITTED** by the unchanged v7 workflow/profile. It has no usable new trigger until Root freezes a reviewed successor route. Preserve the historical v7 ref. A new exact branch requires only these existing identity bindings, without weakening any gate:

1. Bind the workflow push branch, job ref and EXPECTED_APP_BRANCH to the chosen reviewed successor. Keep140-minute job/120-minute build-step budgets and existing commands.
2. Bind framework_profile.py BRANCH and framework_profile.json branch to that same name.
3. Append that one exact branch to the original Heart installer's consumer choice list. No Heart source, archive, protocol or signing changes.
4. Advance the complete installer inverse's predecessor from v6 to v7 in framework_profile.py and its existing test's two literals; bind original_heart_installer_blob to the exact current7fb installer blob 8f619427a9dfa7f0adfd4af26aa958642af0c4f8. Preserve every existing assertion.
5. Freeze one exact commit and verify the actual checkout branch, GITHUB_REF, GITHUB_WORKFLOW_REF, GITHUB_SHA, run identity, immutable input blobs, original trees and package lock through the unchanged source-observation contract before Native execution.

No such activation edits were made in this preparation. Native signing/strict verification, complete consumer execution and editable Host acceptance remain open.

The exact unified patch is retained as deterministic CANDIDATE.patch.gz so its required blank-context spaces remain intact.
