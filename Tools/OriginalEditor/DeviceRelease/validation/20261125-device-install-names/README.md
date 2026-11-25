# Device Release install-name validation — 2026-11-25

The actual optimized 8ae85a64 original framework compiler completed successfully.
Postbuild then reached the original install-name reader, whose qualified SDK
version admits only platform 7 (iOS Simulator). The device framework correctly
contains platform 2. This is a validator platform mismatch, not a compiler or
runtime failure.

release_install_names.py pins the complete qualified original reader by SHA-256
and executes that exact AST in a separate module. For iphoneos only, the one
final platform predicate and its diagnostic are specialized to platform 2.
The entire remaining parser, bounded load-command checks, strong install-name
references, rpaths, unaliased file opening, framework identity, and consumer
checks are unchanged. Simulator operation uses the unchanged original AST.
No observed platform, Mach-O bytes, or prefix digest is normalized.

The complete Release driver differs only in two imports and two explicit
platform/source arguments. The postbuild continuation separately binds the
original compiler driver hash and the reviewed postbuild driver hash. The
original compiler execution UUID, qualified SDK source, command outputs, and
earlier failed evidence remain authoritative and unchanged. Resume from the
original Device292 evidence into a fresh postbuild evidence/work directory.

Validation: 11 meaningful parser/admission controls passed. Separate read-only
inspection of the actual 136,606,376-byte device framework and actual
232,499,808-byte Debug Simulator framework accepted their respective real
platforms and rejected the opposite platform. The full raw observations and
digests are retained beside this document. These controls and binary reads
provide no new compiler, device execution, or native UI acceptance credit.

The historical ownership-timeout continuation is outside this fix and is not
the current execution path. No frozen source, upstream product implementation,
qualified helper, compiler flag, signing entitlement, or acceptance objective
was changed. Source classification: downstream-owned release tooling.
