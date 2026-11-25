# Closed diagnostics for the actual source-capture failure

The unchanged App6f1194 and corrected original UI3396 reached the real source-review action, then the source-capture path failed. Its original XCTest remains one failure. No source bundle or whole-space migration was accepted.

This change adds an opt-in observer to the existing source adapter. It records a closed phase, result, numeric error code, a fixed native-error classification and grant booleans. It never serializes identity, mnemonic, token, native payload, dynamic error domain or error description. The observer has no native callback and cannot authorize source/destination writes. Its files are private0600 under the existing0700 source root, with at most128 ordered records. Production Release never enables it; DEBUG requires both the explicit observer flag and the disposable-simulator flag. The actual UI method only adds that launch flag; all original identity, census, two-capture/two-close and semantic-admission assertions remain unchanged.

Qualification is bounded to two new controls: arbitrary NSError content/domain redaction with a known native checkpoint reason, and concurrent bounded recording/private permissions. The actual final Linux Swift execution passed2/2 with0failures and0skips. Original App adapter syntax parsing also passed. Apple compilation and a real source-capture call with the observer are still pending. This is diagnostic qualification, not source acceptance.

The first attempt ran under a different UID from the existing root-owned C cache and stopped before tests. The second corrected owner run compiled the observer but found a new test-only dictionary-subscript line-break error. Both original failures are preserved. The final attempt changes only that test expression, retains the same observer/App source hashes and passes both controls.

The existing native session, cancellation, cleanup, checkpoint and semantic gates are unchanged. No retry or fallback is introduced; the same original error is rethrown.
