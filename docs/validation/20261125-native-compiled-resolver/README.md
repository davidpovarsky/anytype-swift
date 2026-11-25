# Captured native compiled property resolver

The source catalog now includes the compiled Relation descriptors that the real native resolver captured. They keep their original protobuf and generated JSON bytes and have a distinct registry identity. They are never synthesized as source snapshots, native heads or destination objects.

Actual qualification: **6/6 Swift controls passed, zero failures and zero skips**. Five controls exercise scalar defaults, absent/empty/false/zero/null Value distinction, strict known-field types, retained future fields, captured override precedence, ambiguity refusal and digest invalidation. The sixth rereads the immutable actual native5e8 capture (143 snapshots,144 trees,6 compiled descriptors,299 original members) and verifies all original descriptor bytes and native semantic flags. No native capture, Go test, Apple build or destination write was repeated.

Captured property overrides continue to take priority. If the captured key is ambiguous, lookup refuses instead of falling back to the compiled registry. Catalog fingerprints include both original descriptor hashes. Old catalogs with no compiled descriptors retain their v1 fingerprint contract and lookup behavior. Unknown descriptor fields remain explicit source issues.

The parser implements the actual generated Relation proto3 scalar defaults. The optional protobuf Value never receives a fabricated default. ReadOnly and ReadOnlyRelation remain separate. Compiled _br identifiers cannot enter the native object lookup namespace.

Initial infrastructure attempts remain preserved. The first stopped during manifest compilation because the process identity did not own the existing compiler cache. A subsequent attempt did not launch because the root-volume guard fired. A third stopped during dependency compilation at the unrelated root reserve. Only the fourth result is PASS: all compiler/temp/module/manifest caches were routed to the C-owned project volume, with measured writable-growth and emergency guards. The verified relocation preserved6,923 original cache entries and never moved source/evidence/private accounts.

This closes typed resolver handling only. The original156 capture still lacks its original compiled bytes; nothing is grafted into it. Compiled type descriptors, context/layout semantics, derived provenance, history, complete full-source destination coverage, and actual source UI acceptance retain their existing limitations. No source or destination admission gate was weakened. C remains open.
