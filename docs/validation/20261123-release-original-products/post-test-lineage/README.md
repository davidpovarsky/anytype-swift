# Explicit post-test source lineage

The attempt2 terminal recorded production source SHA256 573eb84a6cc1e5b4e01c341992505e863dda714b6a894b934bb5deadacdd3274. The final e712 production source is bed94e8e0a9b3f662f967a7a8d8bde87dad2ee5c6c05f380d40ad8a4c7c771ea.

The tested attempt2 source was not archived at test time. It has now been recovered by reversing the three explicitly recorded post-test edits and requiring byte identity to the exact SHA256 recorded by that original terminal. The recovered file is labelled recovered-by-exact-recorded-SHA; it is not represented as a contemporaneously archived file.

The exact diff changes only ContinuationOrigin.bind_intent, validate_intent, and restore. The first two add the exact original App/Products path binding and require containment under the current controller's build directory and the original App's build directory. The restore change only replaces the imported enumeration-only helper label with ORIGINAL_PRODUCTS_RESTORED_BEFORE_TESTS. It adds no execution, bypass, count or source relaxation.

The call-scope map proves that the five already exercised origin/carrier/runtime/descriptor/count guards and their relevant dependencies are unchanged between the recovered tested source and final production source. The full five existing test declarations also remain byte-identical.

One new focused control actually executed against the unchanged final e712 production source: exact current App/Products binding, wrong path fields, foreign App roots, and Products escaping the App/build directory are checked. It passed in 0.058 seconds. CI/Git verification is isolated as a collaborator in that path-only control; its production check remains unchanged. No prior control, product test or build was rerun.

Current qualification is six controller controls: five retained with explicit function/dependency lineage plus one new path control. This does not claim whole-archive restoration, real source-checkout preparation, simulator execution, or current shared App acceptance; those remain NOT_RUN.
