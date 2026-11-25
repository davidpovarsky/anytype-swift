# Heart source capture boundary: read-only review

Exact Heart source: `5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5`. The receipt pins all eight reviewed Git files. No product source was edited, no build or native call ran, and this is not acceptance evidence.

The exported mobile capture bridge supplies the account, space and private directory but leaves `Source.Limits` at the Go zero value. The application normalizer supplies the other bounded caps and file limits; it does not fill the local-store limits. Both the initial and final authority reads forward those limits unchanged. `CaptureNativeOwned` requires every limit to be positive and within its existing maximum, so it returns `ErrOwnership` before acquiring the snapshot lease once the preceding authority checks pass. The lower native test fixture explicitly supplies `DefaultLimits`, which explains why that fixture can pass while this bridge cannot reach the same read.

The full request-field audit found no second omitted required nonzero field: all five numeric space/file caps and the file-limit structure already have bounded defaults. Token, account, space, request ID and canonical private-directory checks remain required. Loaded-space, ACL, account and session checks are real runtime conditions; their successful execution is not inferred from source.

The original application failure remains the observed Go NSError1. Agent C owns the narrow request-construction correction and an actual-path regression. The new source must still pass native and application capture before any completion claim. Lower-layer bounds, authority checks and checkpoint validation must remain unchanged.
