# Real-Mac Hanlin fixture TLS correction

The actual D run 45425747246 built the current NativeApp and UI runner successfully, then failed in provider preparation before any of its six UI methods started. The owned fixture child was alive but the explicit-CA readiness connection never passed.

An isolated reproduction on the same Homebrew Python 3.12.16 / OpenSSL 3.5.9 captured certificate verification error 18, "self-signed certificate". The old root and leaf used the same subject name. The repaired generator gives the root and leaf distinct names and includes explicit leaf subject-key and authority-key identifiers. Certificate verification, hostname checks, and TLS policy are unchanged.

The two existing HTTPS controls passed on the real Mac: an untrusted root is rejected, the explicitly supplied CA succeeds, and an incorrect hostname is rejected. The production fixture start also returned FIXTURE_READY. Production stop confirmed the exact owned child exited and its listener closed, then the private material was removed. No host trust was installed and no simulator or Apple product test was credited.

Source fixture SHA256: d0ca3d250d2dba3555b8cc65c48d0ffc8d95ae9b015b9da30e094f3bbb1e0d81. The original failed reproduction is retained in before.json; after.json and controls.log contain the successful bounded follow-up.

The common and Page154 helper trees are rebound only for this reviewed certificate change and the seven additive independent-member ACL transport fixture files. Product trees and all previously accepted test method selections are unchanged. Page run45428221422 remains a failed source-admission attempt with zero builds and zero tests.
