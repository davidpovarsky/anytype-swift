# Original compiler evidence in a postbuild continuation

The real device Release compiler succeeded in Device292-Evidence. The second
postbuild attempt correctly passed the device install-name gate, then refused
to collect graphs because it looked for the original execution descriptor under
the new continuation output directory.

The collector now accepts an explicit, disjoint original compiler-evidence root
only with a pinned postbuild-continuation receipt. The original execution UUID,
descriptor path/hash, compiler command, result-bundle path, output log, source,
target, optimized flags, full public/SPI emission and build-time file timestamps
remain checked against the actual original interval. New collected graph files
and their collection receipt go only into the fresh continuation directory.
No descriptor, command, result path, log, original graph or timestamp is rewritten.
The output records both original compiler and new collection identities.

Four original collector controls and ten continuation refusal controls pass.
Actual Mac validation then collected all11 original device compiler graphs
(101,608,612 bytes) with exact original provenance and unchanged original evidence.
This read/collection creates no new compiler, consumer, runtime or UI acceptance.
The first validation's missing original owner-environment refusal is preserved;
the successful second invocation used the original admit_original_owner routine
and its actual local execution descriptor, never synthetic CI identity variables.

The original Release driver changes only the explicit compiler_evidence argument;
ordinary direct builds keep their original evidence root. The continuation passes
the original root and pins the resulting entire reviewed driver hash. Qualified
SDK source8ae and its helper bytes remain unchanged.
