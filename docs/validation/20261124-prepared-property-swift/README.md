# Swift prepared property update adapter — 24 November 2026

Six new wire component methods passed against source e760b61f79527e70e78a81a28dcc17d7492d1447. The immutable request uses the exact native property-update contract from SDK98f6b0363202164f53a7bdd7512515b0f2855172 / Any8592894d444fda0d7dfedb5519b1a7b70230feb5. These tests do not claim native execution or Apple/UI acceptance.

The adapter binds one source key and original revision to an immutable signed update intent. Its receipt requires the same account, Space, store, plan, source bytes, destination object and single record. A lost commit acknowledgement resumes the original signed change by status without another POST. Changed signed IDs and terminal modified/deleted/obsolete results cannot allocate replacement objects or overwrite fields. Store identity, advertised capability and caller authority are rechecked at dispatch boundaries.

Preparation accepts bounded non-null SET values only; it refuses membership/template replacement fields, invalid field keys and unbounded payloads. Native schema and descriptor checks remain authoritative. It never obtains a fresh revision automatically for a known intent. The future coordinator must persist the immutable specification before dispatch and retain it across application restarts.

Qualification: 6 methods, 0 failures, 0 skips; build89.68s, test0.035s. Source bytes remained unchanged. See component-proof.json for exact hashes and original Sentinel job. Native destination qualification and future combined source→destination execution are separate evidence sets.
