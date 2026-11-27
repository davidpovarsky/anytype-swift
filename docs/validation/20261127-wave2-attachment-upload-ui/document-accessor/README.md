# Attachment intent-store accessor

This is a separate 204-byte insertion over the immutable Properties lifetime source commit `21d63bef8950f8b927f0d8d3b4b052758bc98fcb`. It is prepared for the Interfaces-owned attachment upload tranche; it is not a standalone product admission.

The internal `attachmentIntentStore(for:)` method first uses the original mounted owner/foreground/lifetime guard, then asks the existing recovery owner for its workspace-bound store. The existing document constructor already requires that recovery owner and checks its workspace. No Native, session, journal, attachment creation or persistence code is exposed or changed here.

The companion must provide `AnyNativeAttachmentIntentStore` and `AnyNativeLibraryRecovery.attachmentIntentStore(workspace:)`. Interfaces confirmed those exact signatures; root independently reviews this insertion before composition. The ordinary Library attachment path remains separately responsible for supplying its existing recovery owner, with missing ownership rejected.

`source.patch` and `source-inverse.json` prove that removing only this insertion restores every published Document byte (SHA-256 `f3b6b6bb5425d69d7eff09aecac9c82a5dfd125ed004c644126cb518e137c4a5`). The candidate is `7582d4ee5f6ae5a9ba06e371b4143a1f8db10afda7c213a7263559fe30559a1f`, 73,025 bytes. The lifetime source and its independent tests/reviews stay unchanged.

Swift compilation, component execution, Native calls and Apple/UI acceptance are **NOT_RUN**. No Oracle or Mac operation has been performed for this insertion.
