# Reviewed compiled-definition source composition

The native successor manifest is `0aed35f4909e543a2b0c26f7f9f31fccf8143a8f2cb1d18c7a786c99d4a34fdf`; the exact
26,010,395-byte archive has SHA256 `10bda802b7f6191852f98238696b2f04fd1fd82e3ac23fc444e9743b8ef05fcd`.
The original archive remains retained. The eight-path delta and every predecessor
blob are recorded in source-delta.json. The composition script retains its exact
source and verified both the original and final archive inventories.

Native donor: `5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5`.
Actual original Go qualification log: `a014f77f3129e562627d172594e9344d9ba30b7f1a12b45f50b76115d91429ae`.
Actual original Swift/native reader log: `848ae082fec6e17c7bcf92071a852a34bc21e1b9ed078f4306fe82106e1d8690`.
The owner C retains their original logs and qualification receipts.

This checkpoint also stages the already-authenticated eight-module checksum
evidence for a fresh producer. That prevents replaying the old setup failure
without changing any source/module identity or admitting new missing checksums.
Both the unified runtime Swift profile and the independent shared T5 profile
bind the new exact manifest. Existing 70fb acceptance controllers and evidence
are intentionally unchanged.

Current qualification is source composition and reuse of explicitly hashed
dependency metadata only. No Apple build or migration completion is claimed
for the new manifest in this checkpoint.
