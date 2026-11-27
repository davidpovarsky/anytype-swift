# Signed ACL and reader lifetime: actual 35-event qualification

The SDK authority and lifetime component tests passed on Oracle on
27 November 2026. This is component acceptance. The actual `Files.Open`
integration methods, corrected native product and original-pair HTTP checks
remain separate gates.

## Result and custody

| Item | Actual observation |
| --- | --- |
| Job | `job_3818d9c55187` |
| Time | 12:28:07–12:28:37 UTC |
| Controller elapsed | 29.606 seconds |
| Original command | 24.513 seconds, including compilation and selected tests |
| Top-level methods | 21 |
| Named subtests | 14 |
| Events | 35 runs, 35 passes, 0 skips |
| Packages | `internal/files/readguard`, `internal/anysyncx` |
| Owned groups | 2; both exit 0 and positively absent |
| Forced cleanup / errors | None |
| Peak owned allocation | 37,928,960 bytes |
| Retained account, key or database inputs | None |
| Native servers or previously accepted tests rerun | None |

The tests use synthetic signing identities and synthetic state. They verify
signed Reader and Guest access, removal, cached and pending readers, Seek,
changes of signed head/account/Space identity, revoke/restore ABA, retirement
of an account or Space, same-ID reload, preservation after failed `TryClose`,
cancellation, and the bounded private delivery buffer. The Reader.Close
contract remains precise: pending work is cancelled and withheld; a bounded
copy already admitted immediately before Close is not synchronously drained
by Reader.Close itself.

The complete public receipt is retained at:

`/mnt/development/projects/evidence/pinkha-w1-files-readguard-synthetic-20261127/attempt1/result.json`

Its exact SHA256 is
`68964e6db8802065ba69edad5614ec52cde3603b14f9628d65d808aa76563766`
and its length is 37,878 bytes. A byte-identical local copy is
`actual_signed35_receipt.json`.

The original Go JSON log has 36,794 bytes and SHA256
`3240337be6901b28bb4e2f8bfa6f3790a432dcd8b63f897e90528da92db43cb2`.
Both original command rows, all selected method events, all source identities,
the original log digest and the final closure observations are included in the
receipt. No private account files were inventoried or exported.

## Exact source and toolchain

| Boundary | SHA256 / identity |
| --- | --- |
| Original Any source manifest, 1,599 files | `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a` |
| Guard candidate manifest | `ac2f849e1ca2d7bda725c9c10b46af58d2ac39876a4abf26fa3ce37479d0d896` |
| Guard patch | `874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f` |
| Qualified SDK source manifest, 725 files | `d2fbd4f75d80e14c518f9ed84fac80ceda5f83e59bfb59108b308b745a845661` |
| Qualifier | `aa0680cfc3cb5a3c682d1f332d79b11c879cb0fc9ffad646b8284171d31a576c` |
| Unchanged process helper | `f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56` |
| Actual Go driver | `59c65090beeda377c09007eb8fae1c6aadf0a7b551e65ee13d461092d29e8005` |
| Actual compiler | `4070e0e743ba23672219a3687a1f9bfb489fa5c95bfb6584b4f33932339f92ef` |
| Actual linker | `c119b682a4c1ba107279fe3ec0f0317518e5d21900f1f75941528b65b8d47590` |

The observed driver was
`/mnt/development/toolchains/go1.27.4/go/bin/go`, version `go1.27.4`,
Linux arm64. Its version was observed in an owned metadata command. It was
not inferred from a directory name. The qualifier uses the already accepted
five-control lifecycle receipt `040ffa3f…`; those controls were not repeated.

All original SDK bytes, candidate bytes, admitted public inputs and the
725-member isolated source remained unchanged. The strict source assertions,
35-event selection, no-skip requirement and 2 GiB / 512 MiB live storage
floors were preserved.

## Still pending

This receipt does not assert an actual native `Files.Open` result. The two new
fresh-only SDK integration methods must pass before the shared native build.
That build must use the exact 1,607-member source union and its own immutable
product receipt. Both the root uploader proof and the fourteen original-pair
current-authority checks will consume that same product.

The prior original-pair canary result
`ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab`
remains a failure: the removed identity received HTTP 200 from the old
product. It was neither repeated nor relabeled by these component tests.
