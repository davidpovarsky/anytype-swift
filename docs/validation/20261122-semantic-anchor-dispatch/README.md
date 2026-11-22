# Additive semantic-anchor native dispatcher route

The manual dispatcher adds the single `semantic-anchor-native` route and its one reusable-workflow job. It calls `./.github/workflows/pinkha-semantic-anchor-native.yml` with `source_sha: ${{ github.sha }}`. All 47 prior route options and every prior job remain unchanged.

The baseline is canonical Git blob `d5784a0de876acd7a9048d6f05bd4475cb0dd1b2` at shared commit `58b9de8f7a26d798e18e301ad1ed8be14f2a8c14`. Its SHA-256 is `55c6c3f4648e76d9b4ea2213f5c28afdfd235415a6f9473cdc2f99952f7d64e4`. The candidate SHA-256 is `b048ecbbf3460f20211ce88b1daa62d12b369db49fb0a8602d02872e717ebef9`.

`DISPATCH_REVIEW.json` records the bounded static verification: removing the two precise insertions restores the complete original bytes, and removing the new route/job from the parsed YAML restores the complete original mapping. The exact new job condition, reusable-workflow path and source SHA input were checked. No product or old test was executed for this wiring.

After publishing this file together with the separately inventoried native CAS package, dispatch once from the authorized shared branch:

```sh
gh workflow run torah-inspector-ipados27.yml \
  --repo davidpovarsky/anytype-swift \
  --ref codex/chatgpt-wave15-shared-20261121 \
  --field route=semantic-anchor-native
```

Before dispatch, confirm the branch head is the intended published candidate commit. The resulting run title must be `Pinkha semantic-anchor-native · <that commit>`, and its `head_sha` must match. The reusable job checks out that exact SHA. Its artifact is `Pinkha-Semantic-Anchor-Native-<run>-<attempt>`.

This document records a dispatch recipe, not an executed run. Native package compilation and the nine new selected methods remain `NOT_RUN` until the resulting original CI evidence is qualified. The route retains the original five pure-contract and four controller checks; it does not rerun them, modify the 139-file production candidate, build a shipping framework, or enable the App capability.
