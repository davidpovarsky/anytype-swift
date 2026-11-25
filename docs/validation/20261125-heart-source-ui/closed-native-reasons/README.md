# Closed native error reasons

Twenty additional diagnostic labels come from fixed literals in exact native source 5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5. The source file and blob hashes for every literal are in native-error-catalog.json. This diagnostic change does not modify native behavior, authorization, source admission or the actual capture result.

Three focused controls actually passed: unknown error text/domain redaction, bounded concurrent event storage/private permissions, and joined loaded-space/ACL/manifest reasons with an unknown native failure kept unclassified. The real native source-review failure remains failed in the sibling current5ffff-observed-native-failure receipt.

The first two qualification attempts failed before test execution because the cache owner was wrong and because the original compiled module cache alias was missing. Both failed command logs/results are preserved. The third attempt restored only the lane-owned cache alias after verifying no active users, retained the recreated alias directory without deleting files, and passed all three controls with the same product/test source hashes. The exact invocation, original log and producer are retained. This is portable Swift component qualification; actual Apple compilation and new native capture remain required.
