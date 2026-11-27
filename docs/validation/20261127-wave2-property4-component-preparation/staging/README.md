# Property4 immutable staging handoff

**Prepared locally; not uploaded, admitted or executed.** This packet stages exactly the reviewed84 inputs/1,098,479 bytes and replaces the stager interpreter with the unchanged reviewed `66f09e18…` runner. It adds no process manager, runtime retry, cache writer, account or Native operation. Root owns any eventual remote upload, resource admission and execution after the W1 runtime owner releases a window.

## Frozen artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `materialize_and_exec.py` | 9,982 | `2a7ef1c0d7f5957ef1194b27d34a5456d254b1d077f6e3eceda628925f236a1b` |
| `property4-inputs.json.gz` | 330,008 | `6ca564dc104259a8de2aa593ac28bad1b11e0059b8f52a1cdd4dee701449459a` |
| `property4-inputs.json.gz.base64` | 440,012 | `12e3d367b406481ced96b0fe5f85e127dd0290a74cd6141028a8e7c0e4cb9ab6` |
| Decompressed JSON | 1,499,805 | `b6a0e1b7e267986dc55bf1e2fd941174613890c088115789d29624d3a3a3c4c3` |
| Exact input packet inside payload | 18,317 | `66d0f3453087ac8df6a9bf54cf3bdcbc65f645934facfaaa91cc8fd703d81083` |

The gzip is the exact upload artifact; its base64 file encodes those same bytes without a newline. Gzip mtime is zero. The local readback decodes the gzip, packet and all84 file bodies and compares every body against the frozen local input. It does not execute the stager or controller. The payload contains only the84 inputs plus the packet manifest; outer documentation, reviews and publication evidence are not runtime inputs.

`stager-derivation.json` retains a full inverse to the actual prior Host2 source2 stager `e3c5f144126a35f40ebc78a75373baef73ab6877d7c1443c33caba167af59ebf`. Its five original helper bodies, resource floors, creation permissions and final `execv` pattern are retained. Changes comprise fixed source/payload identities, the current packet field names/counts, read-only dependency qualification and explicit launch cwd/PWD.

## Exclusive staging and preserved references

The only future root is:

`/mnt/development/projects/evidence/pinkha-wave2-property-text-readback-20261127`

It must not already exist, including as a dangling symlink. Its parent must be physical. The stager refuses absolute payload paths, parent traversal, normalized path substitutions, duplicate entries and any path outside the exact pinned inventory. New directories are owned0700; new regular files use exclusive creation, fsync and owned0600 permissions. Every new file must have one link, be physical and read back byte-exact. The final complete tree must contain only the84 expected input files and the top-level `inputs` directory. The payload itself must be an ordinary physical one-link file with the fixed size/hash and stable identity across reading.

The existing102-file Crypto manifest remains `10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c`. Before creating ROOT and again after input materialization, the stager checks its exact original physical artifacts, fresh-copy sources and already documented historical aliases. Those existing dependency aliases are read-only references, not aliases admitted into the new input tree. It checks each source's bytes/hash and stable physical identity, and requires both complete custody digests to match. It neither creates Crypto copies nor modifies reference permissions or ownership. Ordinary reads may advance access times; no access-time preservation claim is made. The reviewed runner still performs its own original dependency-copy and before/after checks if eventually executed.

The original disk admission remains root2GiB+32MiB and Development512MiB+256MiB+32MiB, checked before and after staging. The unchanged runner retains all memory, allocation, deadline and live-resource checks. Source custody does not establish that the77-file compilation fits inside the unchanged256MiB cap; a limit failure stops and remains evidence.

## Working directory and one attempt

Immediately before `execv`, the stager changes cwd to the fixed ROOT and sets `PWD` to that same exact string, then records both actual values. The unchanged runner launches Swift with its original `cwd=COMPONENT` and inherits `PWD=ROOT`. Its compiler qualifier requires actual `-working-directory ROOT`, matching the previous real Host2 compiler evidence. These source settings are not a substitute for the future actual compiler witness; an unexpected compiler directory remains a failure.

`one-shot-invocation.json` gives the fixed argv prefix and has no coordination story yet. The eventual owner must supply exactly one genuine16-digit release/coordination story after source publication/readback and root/peer review. The story records external scheduling; the stager cannot grant a runtime slot. It then uses the original300-second Swift command deadline and original owned-child cleanup, with exactly one attempt and no automatic retry. No external timeout process manager is added.

The fixed future uploads are named in `transport-manifest.json`:

- Payload: `/var/lib/sentinelx/uploads/pinkha-wave2-property4-inputs-6ca564dc104259a8.json.gz`
- Stager: `/var/lib/sentinelx/uploads/pinkha-wave2-property4-stage-2a7ef1c0d7f5957e.py`

The receipt identifies `937a8167700481b71c3c2eeb8771634d2c6bbc4f` as the published **product** source. The future preparation publication is an independent handoff binding to these exact artifact hashes; the stager does not mislabel the product commit as containing the as-yet-unpublished controller. Any materialization failure retains the partial owned root and prints its original error; an existing root cannot be reused by another invocation.
