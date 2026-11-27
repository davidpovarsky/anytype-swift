# Exact native-only Linux dependency

The retained original Linux arm64 archive was rejected by Go before the actual core test because it contains excluded LLVM metadata. The original failed core build remains FAIL with zero test/account invocation.

The qualified LLVM18 tool removed only .llvmbc and .llvmcmd marked SHF_EXCLUDE. All 836 original ELF object members, native sections (including flags, content and alignment), 198,933 native symbols, 457,934 relocation targets and COMDAT relationships remain equal under the complete semantic inventory. Only exact local metadata section/mapping symbols are excluded from that equality. The original archive is unchanged. Go's LTO guard is not disabled.

The preceding GNU objcopy derivative was refused because it changed native relocation-section flags and section order; that failed derivative and its original inventories remain retained. The LLVM derivative passes the unchanged strict equality gate. This proof is dependency equivalence only: zero native tests, zero accounts, zero App or Apple slice builds.

The real core successor independently repeats the full original/derived native comparison, binds both exact artifact hashes and actual transform receipt, and preserves the original source/codec/account/test assertions. Its 1.25 GiB incremental estimate reuses the cache from the actual 291-second failed compile; the original live 2 GiB emergency floor remains. No capacity recovery is attributed to this lane.

The reviewed partial-history test remains unchanged: both empty Seal lists are canonical, while a still-pending native import must be refused by the actual host as incomplete. A metadata ClaimID is the full 64-hex/64-hex identity, not a 32-hex RecordID.
