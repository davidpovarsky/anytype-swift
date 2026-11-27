# Exact native witness companion for the current RTL profile

The published RTL profile successor `f74b5f2a09d02b7a2db91c1f526acea76b42f472`
contains profile `f16a1607…`. A complete consumer that uses that profile together
with `native_compiler_witness.py` must also use this paired witness successor.
The old witness `aaa40880…` correctly rejects a different complete RTL file,
even though the three compiler-validation functions themselves are unchanged.
The direct RTL lane and selected-source Core/Properties lanes are distinct;
this companion makes their exact shared helper dependency consistent.

The change is one literal: `RTL_PROFILE_SHA256` changes from the original
`80ebc560…` to exactly `f16a1607…`. It produces witness
`60fbe9557ad82cd9ee33016e7bd264ac55843c9b27b2eb3862a35481c0741967`.
The complete original witness restores through the inverse literal. Both of
its original function bodies remain byte-identical. The three function bodies
it extracts from the RTL module (`sha`, `_pinned_bytes`, `source_contract`) are
also byte-identical across the old and new RTL files.

The original rules still require an exact clean source commit, complete tracked
selected sources, canonical physical files, the admitted producer's own native
compilation proof, and actual `swiftc`/FileList/log witnesses. No hash alternative,
environment override, count waiver, assertion change or product shortcut is
added. This helper remains subordinate to successful common product admission.

The materializer pins the original witness and both complete RTL files. It
writes only into a fresh directory. Exact source inverses and the independent
review are retained. The unchanged portable witness tests were not replayed;
the verification here is complete source comparison and dependency wiring.
No native, compiler, Apple, XCTest or simulator operation was performed.

Future source freeze, producer receipt and common admission remain absent, and
readiness remains false. Wave3 must include both exact helper identities in a
separately reviewed complete consumer closure after a matching actual build.
The older Core13/Renderer3 and Torah consumer directories are not overwritten
by this companion packet.
