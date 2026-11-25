# Verified private SwiftPM artifact relocation

The actual E6 attempt on SDK source 5dc61ab9 passed the strict 56-pin resolver
with no committed source or lock mutation. The subsequent full framework
command failed in build graph setup: copied workspace-state.json retained
absolute artifact paths under the donor's former producer-derived directory,
although the original artifacts were retained in producer-derived-preserved
and copied into the new owned cache.

This continuation preserves every failed E6 command, log and result bundle.
It does not grant SDK or editor acceptance.

The optional donor-cache path now verifies all 18 declared artifact directory
inventories (17 remote artifacts and the already admitted original native Lib)
against the retained original bytes, including file hashes, sizes, modes and
safe symlink targets. Only the private workspace-state paths are relocated.
Both metadata beforeimage and afterimage and every artifact inventory are saved
in the current evidence directory. The private copied PIF cache is retained as
evidence so Xcode regenerates its absolute-path metadata. No donor file or
qualified product is changed or removed.

After strict package resolution, every absolute path in the active SwiftPM
workspace state must exist within the current owned source/build root. The
normal full current-source framework build, exact API graph and binary-only
English/Hebrew external consumer gates still determine acceptance.
