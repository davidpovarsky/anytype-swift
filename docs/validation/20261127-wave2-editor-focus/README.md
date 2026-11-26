# Wave 2 editor: exact collection-layout focus gate

The source candidate remains 2fbc3e1a4a0e4dfa2f20e49f5c649900632bf764, inherited by the preserved a089ff29a5c0a7e415aac800844505f099a5561d base. This change adds a new build16 focus profile; it does not change the application or the historical build15 profile.

The prior App15 profile pinned the old 21-method / 32-case source. The fixed source adds collectionLayoutResumesOnlyCurrentUnattemptedFocus(superseded:), with false and true cases. The additive profile requires the exact new Swift source SHA256 and all 22 methods / 34 distinct cases. source_contract, validate_results and validate_enumeration remain byte-for-byte identical to their original build15 functions.

Four portable qualification methods passed. Their synthetic fixtures test the exact current source, old-source rejection, method and literal-case completeness, both new cases under missing/duplicate/failed/skipped mutations, and exact compiled selection. These are collector controls, not Apple or native editor acceptance. Attempt 1 failed because the synthetic model label did not satisfy the unchanged original iPad validator; that failed log and receipt are retained. Attempt 2 changes only that synthetic label and passes.

Pending runtime sequence: a source-bound shared build; the 22-method / 34-case focus suite; unchanged prepareRealApplicationState; then the original three editor UI methods plus testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen. Preserve prior App15 focus pass and actual preparation failure separately. Remaining iPhone/iPad, app/device language, light/dark and accessibility coverage must be reported from actual execution. Physical device remains NOT_RUN.
