# Independent source review: native core 05c2f6d

Reviewed source: Anytype
`05c2f6d4f391a5b9d3dab7efa2987afd887a5f65`.
This is a source/evidence review, with no new native test, framework build,
native pin change, or application capability activation.

## Exact source proof

All 40 source files were fetched from the immutable commit's original overlay
and independently matched against the qualified manifest's byte sizes and
SHA256 values. `git apply --reverse --check` and reverse application of
`8064231fada75e7a16ef54cf8314a80bb2e9eaade7eb2352423c3cbf4cba2501` succeeded
in a separate local review copy. All 16 resulting original files matched both
the overlay's original-replacement records and the original native8ac manifest.
All 24 declared new files were removed by that reverse application. The small
derived `native-cutover-core-source-proof.json` records these checks.

Original controller receipt
`cd70d52b57795cab7ad6b94f396177213ba140d6e7cf31f14aed93fe5b897b82`, assertion
proof `674c67e4837217686bcdc0c8ecc116212baeedbf323a8e5180aa8dd28d4475b1`, and
qualified manifest `0ea2bbfff9fd1faef02337ae247bb6706c5517c971d1346b762467b854782a20`
were independently hashed. Their original accepted scope is one Linux ARM64
native core registry test with actual same-process account retirement/reopen.

## Reviewed behavior and conclusion

No source blocker was found in the inspected factory/registry, private-root,
source-lease, native host, currentness/idempotency, or original-v1 append paths.

- The factory uses the authoritative requested smart-block type before Init
  assigns its source. The separate metadata type/root is explicitly registered;
  generic create/import/export and ordinary mutation paths remain refused.
- Native source authority comes from held account/settings/document objects.
  The source token checks the real object/cache/tree/ACL identities, exact
  retained property bytes and native heads. An RPC cannot supply that token.
- The documented order is settings/document, metadata tree, v1 tree, current
  ACL. The already-held read ACL is checked without recursive acquisition.
  The mandatory storage guard reacquires current write authority at commit.
- Source divergence or conflict is rejected before idempotent receipt lookup,
  while unchanged frozen retries remain valid after a subsequent Seal.
- Metadata and original signed-v1 imports remain two explicit phases. Sealing
  checks complete frozen source coverage and the original signed receipts;
  an unlink does not erase the durable seal or resurrect retained legacy data.
- Native append results preserve actual committed metadata when a subsequent
  projection or authority check reports an error. This behavior is essential
  to reconciliation after a lost response.

## Required downstream dependencies

The five versioned RPC/generated mappings and Swift native bridge remain a
separate coherent delivery. In particular, append/import/association mappings
must preserve **the result plus the post-authority error**. They must not replace
an actual committed ChangeID/receipt with a zero result or infer safe retry from
an error or cancellation.

The four changed CutoverNativeHost regression methods still require their new
source execution; their older pass results do not qualify the changed checks.
New-process crash recovery, peer transport, Apple framework binding, the final
shared app, and UI remain distinct acceptance gates. Retained native8ac ABI
evidence is a baseline for composing this source, not acceptance of this delta.
