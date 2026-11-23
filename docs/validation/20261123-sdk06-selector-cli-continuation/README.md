# SDK06: two new CLI enumeration hypotheses

## Original evidence and diagnosis

Run 45102030139 at controller source 12149b15c8775a7b334892a23fdc6260fae278f2 completed all four enumeration probes. Original artifact 14786396641 is verified by SHA256 e88b43d280473175cd9a6bf837b9aa720ca6fa7e55cd02d773caa60c5e6e29c0. Its complete original files remain under /mnt/development/projects/diagnostics/sdk06-enumeration-runtime-repair-20261123/original-14786396641.

The original immutable products belong to run 45087685319 at 7293e4fd0bcabdcdb643d5768b777b8e87ff1b73. That producer's compiled suite discovery enabled all 30 declarations. Neither a missing binary nor a missing test declaration explains the failure.

The separate-argv full-signature probe enabled the 15 requested nonparameterized declarations and left all eight requested parameterized declarations explicitly disabled. There were no unexpected enabled methods, and all seven exclusions remained disabled. The earlier producer's bare-method selection enabled the same 15 methods.

The three plist-only probe outputs are byte-identical: zero enabled and 939 disabled, including all requested methods. All four outputs have errors=[], plan AnytypeTests and command exit code 0. These are failed selector qualifications, with zero product tests and zero new builds. The existing strict validator correctly rejected every output.

## Bounded continuation

Only two new hypotheses are generated:

1. **suites-minus-seven-cli**: use the three suite CLI selectors that produced the original 30-method discovery, plus seven explicit CLI skip identifiers. Preserve the same suite inclusion and seven exclusions in the copied plist. Four exclusions are nonparameterized and three are parameterized; the latter are not assumed to work. The original exact-23 qualification must prove the resulting selection.
2. **parameter-signature-terminal-parens-cli**: pass the existing terminal-parentheses hypothesis on the CLI as well as in the copied plist. The prior attempt used only the plist and therefore did not test this CLI hypothesis. The 15 nonparameterized names remain exact; only the eight parameterized outbound names receive the additional terminal parentheses.

The CLI uses the original successful suite discovery's colon spelling. The controller does not repeat the old exact/separate/bare selector attempts. It does not invent a new plist identifier encoding.

The generated commands always contain exactly one -enumerate-tests action and use the immutable original products through a fresh copied descriptor. The individual 600-second and overall 2400-second limits remain unchanged. The candidate list is now required to contain exactly two entries.

## Preserved acceptance and source boundaries

The original selection contract, exact full-identifier validator, seven-exclusion check, expected 32 future argument cases, product archive identity, original descriptor hash, runtime-library normalization, restoration verification, and teardown are unchanged. Enumeration success would only qualify a selector; it is not a product test pass, a new accepted build, or authorization embedded in this controller to execute tests.

No workflow, shared validator, product source or test declaration was changed. Mechanical review confirms that only variants(), enumeration_command(), and the candidate-list wiring in execute() differ in the controller. The prior runtime controls remain byte-identical and were not rerun.

## Actual validation

Exactly two directly affected controller controls passed on Oracle: copied descriptors retain original bytes and all nonselection settings while preserving the exact selected/skipped identifiers; generated commands carry both new CLI hypotheses and cannot execute product tests or rebuild. Their original terminal output and source hashes are included here.

The other prior controls were not rerun. No Xcode enumeration, application build, product test or workflow dispatch was performed for these hypotheses. Their actual Xcode qualification remains NOT_RUN.
