# Explicit original validation helper admission

Attempt1 ended before simulator creation, native calls, or tests. Its original
FAIL receipt is 1ad0d2205a3e04dcab5b2fdcbdb280db617cc0b3888dbd827808fab7c2e0ade3.
The controller mistakenly looked up an original tool in the compiled App source
manifest, which correctly excludes that tool. No acceptance method ran.

The follow-up explicitly binds all 17 local Python helpers in the transitive
original import closure to Git commit 6f1194f9b8c9540dea1187826dda6a256777dbbf.
Original Git blob IDs, SHA-256, and byte counts are retained. Every helper is
checked before import and again after execution. The separate compiled App
source check and all original method/result/companion/native readback checks
remain intact. Build functions in imported modules are not invoked.
