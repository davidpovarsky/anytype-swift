# Native file content reader — 25 November 2026

Product source: **93dbe7501aa79c0eccc0d94db0a9d8a7362d70fa**.
Seven focused HTTP/private-output controls passed, zero failures and zero skips,
in 5.466 seconds (8.443 seconds including the incremental build). The original
passing log SHA-256 is
ae5d699f9fd6bdfce9f3aedde79484ae36fcadbac6896ff9ba97037931b51291.

## Product behavior

AnyHTTPClient.readFileContentDigest reads the original native file-content
endpoint using 1 MiB Range requests and incremental SHA-256. A serial response
delegate bounds buffered bytes before append, including responses without a
Content-Length. Account, caller authorization and cancellation are checked
around every request. The reader checks response URL, native range, exact
length and stored MIME, and refuses redirects.

downloadFileContent uses the same reader. It exclusively creates a new 0600
file relative to an open descriptor for an existing private directory. It
refuses an existing path, symlink or public parent. A provided plaintext hash
must match before the file is committed; failures remove only that newly
created output. It returns a digest, without persisting a runtime URL or
control capability. The existing JSON/status request methods were
unchanged by this additive implementation.

## Actual qualification scope

The tests use an explicitly labeled adversarial HTTP component fixture,
including managed-control authorization. They cover a 2 MiB + 17 byte roundtrip,
empty files, precise Range206 bytes, digest mismatch, account switch, authority
withdrawal, file permissions and preservation of existing files. Invalid range,
MIME, length, ignored Range, redirects, declared huge length and chunked overflow
are refused.

This is transport/private-output component proof. It does not prove an Apple
app flow, native file custody, or complete Heart-to-Any migration. The separate
real native file/peer proof remains in
../20261125-migration-native-file-peers/. The new destination verifier must
receive its own native qualification before being accepted.

## Original failures retained

The first attempts exposed relocated-cache ownership/lock paths, stale absolute
precompiled module paths, a test-only Swift type-checking expression, and the
new Python fixture inheriting a blocked termination signal from a Swift worker.
The original results and logs are retained unchanged. Only this lane's inactive
reproducible compiler output was rebuilt; dependency sources were retained. The
fixture now unblocks its own signals so ordinary cleanup terminates it. No
product/test assertion was removed or relaxed.

source-qualification.json binds the exact three tested source-file hashes.
failure-index.json records every earlier attempt and the source of the
infrastructure failures. The pass log, command and result are copied byte for
byte from the original Oracle evidence.
