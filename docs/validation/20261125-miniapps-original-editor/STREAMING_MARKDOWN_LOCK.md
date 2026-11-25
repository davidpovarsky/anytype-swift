# Exact StreamingMarkdown dependency continuation

The real native SDK attempt on source `0ae997abd5184b6afb93bf41203f0559fd1e8c6a`
stopped in strict package resolution, before the original framework compiler.
`SDK-Evidence-4/execution.json` records the failure. It does not establish
framework, external consumer, or editor acceptance.

The already reviewed Hanlin source
`5aaa4471924aec0fbf086e68feb08fa10d9f01c8` requires StreamingMarkdown
`5cbb4b6c950051f98f02a0b0ae56756f5174a9b8` in
`Packages/HanlinPresentationSDK/Package.swift`. The previous 52-pin lock still
contained `6bde022876ef4af738c154b3d5c871984ef76195`.

This change replaces that single revision, preserves the other 51 pin records
byte for byte, and updates the exact reviewed lock blob in the framework profile.
The upstream Package.swift was read from both exact GitHub revisions: both have
Git blob `c6a424823b556158c18541300121e1706e35d320` and SHA-256
`9a6d87007499587933bbd04e3edf9aadb4bfceba91c3b1914bfc383e96f7aa8e`.
Its transitive dependency requirements are identical.

The cumulative package review now describes the ten distinct pins changed from
its historical base, including the current core continuation `3f38f130`.
The previous adoption receipts remain in the profile unchanged.
Automatic package resolution remains disabled. The native resolver, complete
framework link, actual exported API and binary-only English/Hebrew consumer
gates must run with this committed lock before a new distribution is admitted.
The 282-member API, original Swift source, generated inputs and native ABI inputs
are unchanged by this lock correction.
