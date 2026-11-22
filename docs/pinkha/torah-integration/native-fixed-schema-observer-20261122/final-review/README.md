# Original native fixed-schema observer: final source composition

This dedicated control branch is based on the published Anytype integration
37f48119609747c01ee92cf597e4216f63b7bfa4. It preserves that application's source
trees and adds the frozen V5 Heart source packet, frozen R2 control packet and
their exact reviewed workflow. The observer remains a bounded historical
persisted observation; no schema repair, identity receipt, ledger writer or ACK
is enabled.

The 138-payload V5 and 112-payload R2 indexes remain byte-identical. The R2 packet
retains the earlier source/control history and the source-only disposable
composition proof. Its 33 native observer cases and 12 strict-decoder cases have
not run at this point. Root's complete control intake and the peer's bounded
runner review are retained here without altering either frozen packet.

GIT_PREFLIGHT_SUBMITTED.py is the submitted read-only preflight script; its
actual Sentinel result and parsed observations are retained separately. Root's
EXECUTED_ROOT_REVIEW.py is the exact executed script provided by root.
FINAL_REVIEW_INDEX.json indexes this review folder excluding the index itself.
CHANGED_PATHS.json names every path to be committed.

The scoped Git attributes preserve imported source/evidence bytes, including
original CRLF. They do not change product code or global Git configuration.
Existing push workflows select other branches; only the new dedicated native
schema workflow selects this branch. A normal push is withheld until root's
explicit final admission. No Go toolchain, dependency setup, build, test or
native runtime operation was executed during this Git composition.

The future runner retains owned process/deadline/cleanup receipts, exact source
and native-library closure and pre/post executable hashes. Executable bytes are
excluded from upload, so artifact review cannot independently rehash them.
Compile or source review alone cannot satisfy original editor, cross-app,
physical-device, release or schema-provisioning acceptance.
