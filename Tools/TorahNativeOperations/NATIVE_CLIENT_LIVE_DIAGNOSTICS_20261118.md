# Same-run native-client diagnostics

This change adds observability to the current bootstrap fixture. It does not
change native production code, acceptance assertions, retries, deadlines,
private-root availability checks, target fetch context, or App capability.
Offline/conflict/reopen remains isolated and is not dispatched by this change.

## Producer and publication boundary

The current CI controller records a fixed stage before its existing operations.
After its existing owned-container cleanup and secret-scanned publication, it
reads only the two newly published `native.log` files from that execution. Each
file must be regular, non-symlinked, bounded, and match the publication's SHA256
over the exact bytes parsed. There is no archive, download, historical-run,
account-store, or external-source input to the diagnostic decoder.

The finalizer emits a small GitHub `notice` with fixed enums and booleans only.
The existing workflow already runs the controller directly on the CI host, so
the notice reaches that job's check annotations without a workflow change.
The check's existing run/attempt/source metadata identifies the execution;
the diagnostic itself contains no IDs, paths, error text, payload, or counts.
The exact decoder hash is checked by the native-client fixture manifest.

Logs are withheld from the decoder unless cleanup and secret scanning succeeded.
Malformed markers and changed/missing files produce fixed unavailable states.
Decoder, serialization and ordinary output errors cannot change the controller
result or promote a failure. A closed stdout is covered by the ordinary-exception
guard rather than escaping finalization.
KeyboardInterrupt reaches the controller's existing cancellation finalizer;
the notice is diagnostic only and never authorizes acceptance.

## Observation meaning

The Go fixture logs the code, snapshot presence, and result of the existing
readiness predicate immediately after the same ReadTarget response. This also
records valid intermediate responses that previously ended in an unclassified
timeout. No additional native read, storage probe, or readiness decision occurs.
Unknown numeric wire codes are replaced by a fixed label.

The decoder separately reports the last observed native error's existing
`errors.Is` flags. Those flags are not asserted to belong to the last wire
observation. Context flags explicitly describe the outer RPC context, not the
child context used for the ordinary target lookup. A READY observation is only
one predicate result; it is not a final two-client or full T2 acceptance result.

## Validation scope

The local Python run passed 26 controls with no failures or skips: 14 existing
controls and twelve focused diagnostics/finalization controls. The first local attempt exposed
an outdated expected count (13 rather than 17) in one existing control; only that
expected count was corrected before the successful run.

Independent review then found that a closed stdout raises ValueError, outside
the original OSError-only output guard. The final correction covers ordinary
serialization/output exceptions and adds an actual closed-stream regression
with unchanged FAIL/CANCELLED receipts. KeyboardInterrupt and SystemExit during
serialization or output still propagate. The pre-correction source and local
21-control result were retained separately; they are superseded by this result.

The subsequent finalization correction avoids chmod when an entry already has
its exact 0644/0755 publication mode. A mode change is allowed only for the
current process owner; an incorrectly permissioned foreign entry, symlink, or
unsupported file type still fails. Ordinary permission and receipt-write errors
are retained separately from the original controller error, force failure, and
do not suppress the fixed notice. The final checkpoint precedes normalization:
the actual JSON writer atomically replaces the receipt with a new 0600 inode
under umask 077. If writing or normalization fails, one additional checkpoint
records FAIL (or preserves CANCELLED), then the replacement receipt's own mode
is checked. This bounded failure checkpoint cannot restore success. If its
permission change also fails, the controller still returns failure and emits
the fixed diagnostic; it does not claim readable publication.
BaseException cancellation still reaches the existing outer guard.

Both independent reviewers caught the superseded normalization-before-write
ordering. Its source and 25-control result are preserved separately. The final
26-control run includes the actual atomic JSON writer under umask 077, checking
the final on-disk mode and content after success, original failure/cancellation,
one failed receipt chmod, and persistent receipt chmod failure. Previously
completed command results and the original error class remain unchanged.

The workflow's build uses Docker without a user override and the client stage
runs on the host. Unconditional chmod of inherited evidence is therefore a
concrete unsafe finalization path under mixed ownership. The latest failed CI
metadata does not prove that this exception occurred. No held image-user or
ownership receipt was available. Controls use actual local modes/symlinks plus
injected foreign UID and filesystem errors; an actual cross-UID execution is
NOT_RUN. No elevation or mutation of unrelated files was attempted.

Three new named Go subcases plus their top-level method are required by the
existing native-controls gate, increasing expected pass events from 13 to 17.
They exercise invalid/unknown codes, private-field omission, and observation
without response mutation. These Go cases, formatting, compilation and the
fresh two-client execution remain NOT_RUN until the normal repository CI or
authorized in-place formatter runs them. No historical raw CI data was read.
