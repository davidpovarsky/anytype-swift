# Composer scope refinement

The semantic identifier is attached to the canonical composer component, not directly to its upstream TextField. The earlier direct-identifier candidate assumed propagation. This follow-up preserves the original candidate record and removes that assumption.

The helper collects real input roles from each identified composer scope itself and its descendants. It uses accessibility-bound XCUI elements and exact equality to avoid counting the same resolved input twice; there is no geometry, label or value-based deduplication. Multiple identified scope nodes are permitted, while exactly one distinct input is required.

Both scope and input readiness use the same30-second monotonic deadline. The class stops after assertion failure. Missing/ambiguous scopes cannot fall back to an unrelated global input. The final input must be enabled and hittable.

All source outside this one helper is byte-identical to the previous commit, including every retained method and all real consent, typing, provider and native assertions. Product and canonical Hanlin sources remain unchanged. Swift syntax passed;0 XCTest methods ran. Actual Apple execution remains required.
