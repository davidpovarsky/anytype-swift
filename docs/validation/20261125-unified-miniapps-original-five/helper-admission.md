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

Attempt2 also stopped before simulator creation or tests. Original FAIL receipt:
97b606025896db0fd15671e026db3f6f53845a673a05e67fad86481fb48bc149.
Its actual Info.plist contains an empty PinkhaNativeAppGroup value, with SHA-256
a45f89151806d0e490c1e02043d4b9ddae6999884aeec78e10e644cedf9aa19c.
Original TargetsConstants explicitly ignores the empty override and uses the
Debug group.io.anytype.app.dev fallback. The follow-up admits that exact empty
compiled field, preserves the actual embedded native/shared entitlement checks,
and leaves the original native preparation runtime equality assertion intact.
No App/Info.plist, signing entitlement, group, or native test was modified.
