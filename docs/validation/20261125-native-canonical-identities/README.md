# Canonical native object, space and type identities

Product commit: 42fe14feb71f25a9f7ac1c73c0e9b628defca32a.

The original native self-id, space-id and type definitions now map to Any's
existing id, spaceId and managed any.type fields. The adapter requires the
complete original definition bytes and exact native descriptor. Source space
and type relations additionally bind their actual captured target-Type object
to the same manifest. Labels or caller-supplied type IDs cannot substitute.

Present source identity values must agree byte-for-byte with the current
source object, space or resolved Type. They are consumed as identity semantics,
never copied into native property-write payloads. The existing native migration
verifier independently compares every target object's root id, spaceId and
any.type. Presentation uses only the exact native descriptors and keeps
derived identity fields and type membership read-only in generic property edits.
Source creation/modification dates and authors were not aliased or overwritten.

## Actual qualification

Thirteen distinct affected methods are qualified: ten unchanged passes from
attempt1 and three focused passes from attempt2 after fixing a collision between
two synthetic fixture IDs. The original attempt1 remains12PASS/1FAIL/0SKIP.
The followup is3PASS/0FAIL/0SKIP. All product files are byte-identical between
runs; only the private helper's generated test ID prefix changed, and its exact
inverse reconstructs the original test-file hash.

The original156-snapshot reader passed the three new captured bindings against
the original20Types/126relations/4options. Its original native capture method
remains failed; this is a reader/semantic comparison, not source authority.
No new native process, Apple build, whole-source admission or destination
migration acceptance is claimed here. Live native descriptor/reopen checks are
pending recovery of the previously retained CLI, now observed absent.

All current full-source blockers and original raw source recovery are preserved.
