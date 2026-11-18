# Original r15 build failure44225433140

Original GitHub artifact14393753945 was downloaded once and its full SHA-256 and size matched the API digest. The outer ZIP, inner ZIP and all23 inner files are preserved unchanged. The exact failure is gomobile init attempting gobind@latest under GOPROXY=off, after pinned gomobile and gobind compile and source/module verification. Heart bind, Apple slices, AppGetVersion and Swift tests were not reached. See verified-summary.json and original-evidence/runtime/gomobile-init.log.
