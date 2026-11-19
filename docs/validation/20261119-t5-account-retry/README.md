# T5 R07: stopped-account error and recovery

The source and portable controls are reviewed. Actual Apple build and execution
are still required. This change does not complete T5 or enable product lookup.

The separately selected Swift test calls the entire existing pagination test
body once, then retains one production related-documents service while it
observes success, an actual stopped-account ObjectSearch error, and success
after restoring the same existing account. It preserves the complete original
28,741-byte test file as an exact prefix and keeps the original pagination route.

The tail requires two real AccountStop calls with removeData false, two restores
of the original account, nine unchanged directory identity observations, and
unchanged baseline receipt and private credential bytes. Successful results are
derived from fresh native reads, including the original deleted-block state.
The failed query must propagate BAD_INPUT with the original native description;
it cannot pass as an empty successful result.

The expected 45 search attempts are the calls recorded at the production
service boundary: 36 in the original body and nine in the tail. Independent
candidate polling and native readback operations are additional diagnostics;
45 is not the total number of every ObjectSearch invocation in the process.
These are expected counts until a real source-bound run passes.

## Independent root review

The root session reviewed the appended Swift implementation, original native
error source, controller, qualification rules, negative controls, and workflow
routing. All 47 portable controls passed again, including the original 26.
Python syntax, workflow YAML, and workflow shell syntax passed. The separately
recorded Swift check is grammar only; UIKit typechecking and native execution
have not occurred for this change.

Eighteen current source-path checks confirmed the candidate bases and unchanged
supporting production code. The validation helper was checked separately. The
only rebase is the dispatcher, onto commit
4b5d9f0e44b3d1ab368d9ecf5d513a0aed4db047, retaining the published Space.Close route.
The other six candidate files remain identical to the frozen agent candidate.
The original candidate manifest and source review are retained as provenance;
the root manifest describes the exact files being published.

## Execution boundary

The run consumes the original r15 runtime from successful run 44393343388. Its
artifacts were available and unexpired when checked. No r14/r15 approval,
runtime identity, pair assertion, or product capability is replaced.

Network outage behavior, UI error presentation, whole-index completeness,
physical-device acceptance, corrected attachment-runtime acceptance, and
original-old-runtime compatibility remain outside this test's acceptance.
Raw native results, account data, and credentials remain in private job storage;
only the existing allowlisted, fully credential-scanned proof may be uploaded.
