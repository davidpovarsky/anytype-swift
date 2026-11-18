# R08 follow-up: localized source chips cannot evade the retained-Note gate

Base source: 885a1bb5d8f146432a9aeafd93e92e632d07e8b3.
Root source review found that the retained-Note query still filtered labels by the English canonical reference. A Hebrew chip could therefore be missed.

R08 now requires zero source-chip buttons regardless of localized label, and the receipt must carry an exact integer sourceChipCount=0. The original retained-Note AX attachment is independently rejected if it contains any torah-document-source-chip- identifier. The fresh core Note originally had one canonical source and core unlinked it, so requiring absence of every source chip is within this fixture's known scope.

A concrete negative control appended a Hebrew Genesis source chip to the original AX fixture while its receipt still said sourceChipExists=false. The old gate accepted it; the new gate rejects it. Missing/nonzero/Boolean chip counts are also rejected.

Validation: 29 Python test functions, 139 subtest outcomes, zero failures/errors/skips, on Linux. These are synthetic parser/controller checks only. Swift compilation, actual Apple R08, VoiceOver and physical iPad remain NOT_RUN; visual review remains PENDING. The controller, core methods, runtime/account/appearance contracts and Kit dependency did not change.

Source hashes, complete controller log and validation counts are retained alongside this note. The original 885a handoff evidence remains unchanged.
