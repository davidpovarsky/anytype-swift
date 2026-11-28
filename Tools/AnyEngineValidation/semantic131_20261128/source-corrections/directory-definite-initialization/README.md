# One-row definite-initialization correction

This data-only source graph composes the exact W3 correction from commit `73a7d25658c18aa9cb846dd578e064f058b9a981` onto the frozen foundation131 graph. It includes no new runnable controller and does not change Oracle attempt3.

The real Mac C20 compilation failed at `AnyNativeImportedDefinitionDirectory.swift:325`: the initializer's filter closure captured `self.source` before `unresolvedSourceDefinitionIDs` was initialized. The correction reads the identical immutable `preservation.source` argument in the two expressions. Exactly two `preservation.` prefixes add 26 bytes; the full inverse restores the original 22,948-byte f870 body. No validation, merge membership, ordering or public API changes.

The corrected graph contains the same 131 whole files, 127 production files and four test files. Its source total is 1,652,947 bytes (1,550,601 production + 102,346 test). Exactly one Git-supplied source row changes; all 101 physical rows and the other 29 Git inputs are whole-JSON equal. The original20 selectors, all four complete test bodies, fixture inputs and resource/ownership contracts are unchanged.

`SOURCE_GRAPH.json` is a separately named data schema. It keeps the original foundation's lineage metadata explicitly historical and carries the corrected source rows and unchanged contracts separately. Existing Oracle controllers do not admit its new graph hash. The distinct128/129 Ordinary14 graphs are excluded.

Root and C independently reviewed the two-prefix correction. The complete posted Mac failure handoff is preserved with the receipt/log hashes; this packet does not claim a new independent physical Mac log read. The original failed run and both Oracle failures remain unchanged. W3 owns its corrected Mac continuation and retained build. No corrected typecheck, method execution, native acceptance or App equivalence is claimed here.
