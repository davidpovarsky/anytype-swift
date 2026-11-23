# SDK-qualified kernel absence profile

This narrow follow-up adds only sdk06-qualified to the already-qualified kernel absence helper's fixed predicate. The helper, original owned-PGID checks, original ten-second deadline, numeric ps fallback and all other profile behavior stay unchanged.

The directly affected lifecycle fixture now supplies an explicit GROUP_EXISTS outcome: mocked signal zero returns success, the clock advances from 0 to 1 to 2 before the fallback begins at 3, and ps receives the original remaining seven seconds. The prior overall ten-second bound and late-zero rejection are retained.

The source is frozen before execution. Only that affected lifecycle method and one new SDK-qualified wiring method are scheduled. The other 17 composition controls and all nine original kernel controls will not rerun. Original 18-control history stays preserved with the new affected result distinguished from it. This source has no selector admission and cannot be used until the fixed composition addendum binds the actual new source and proof.

source-review.json preserves the exact predicate inverse, full original source snapshots, unchanged-function hashes and the fixture-only method boundary. There are no App/native source changes, product tests, framework builds or Mac dispatches in this scope.
