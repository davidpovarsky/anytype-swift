# Source-only publication handoff

The four existing paths listed in `candidate-manifest.json` are the entire source
change: two downstream Heart services, the existing repository test input, and
two literal replacement-blob values in the existing 145-row source map.
Everything else in this packet is new scoped evidence.

`README.md` and both final independent reviews are preserved exactly as reviewed.
`acceptance-handoff.json` describes the two methods / ten declared cases, original
hosted target, isolated suite selection, and actual work still required. No
compiler, test, source-gate, Native or Apple result is created by this packet.

The primary parent commit receipt and `source-custody/primary-source-manifest.json`
bind original App and pinned Factory sources. The latter provides exact immutable
Git URLs and blob identities instead of copying unchanged source or full third-party
documentation. The preparation-local paths inside retained reviews remain provenance
locators; they are not executable dependencies in this publication.

`review-v1` retains the original suffix, manifest, inverse, README and retention
manifest. `predecessor-retention.json` verifies how the original full test is recovered
from the parent prefix plus suffix, and how the original patch is recovered without
a redundant full copy. The initial peer finding and exact inspection failures remain
separate originals. Ownership and Modules-read inspection stops are not test failures
or evidence of a completed Modules-wide caller inventory.

Publication will use a new owned branch and one child of the exact reviewed parent.
Workflow/ref/tree checks and primary readback occur only after packet approval.
There are no Native, PBX, Package, runner, consumer, inventory or final-ref edits.
