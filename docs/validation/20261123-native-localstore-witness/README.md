# Native local-store witness: source candidate

This checkpoint contains a bounded fixture-owned native transaction witness candidate.
Compilation and product execution are NOT_RUN at this source commit.

The exact API, detached decoded-value codec, ownership boundary, native transaction
interleaving and six selected methods are frozen in
Tools/AnyEngineValidation/native_localstore_witness/PROTOCOL.md.
Source copies, original native source commits, inspected dependency ZIP bindings and
the explicit new Go1.27.4 ARM64/glibc profile are in source.json alongside it.

Native source: 74b5f2c844ac3879125888c538d5990af3db3cb8.
Original 862e98d16b6ae55207a41b53a036d8b7660a189a was reviewed before compilation:
its receipt initializer mismatch was repaired in one line, with zero tests or builds
on that original source. Pre-execution originals are retained separately.

The candidate preserves nativeSnapshotProofRequired and nativeIdentityCensusRequired.
hasNativeSourceAdmission=false and permitsDestinationWrites=false remain unconditional.
No production authorization adapter, whole semantic snapshot, file payload census,
Swift/App/mounted acceptance, remote replica completeness, or migration is claimed.
