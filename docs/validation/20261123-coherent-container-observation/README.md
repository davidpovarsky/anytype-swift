# Preserve the original fresh-container lookup outcome

Original Release45111287072 reached readiness but timed out in the30-second get_app_container query before first install. Its TimeoutExpired partial streams were not retained. This bounded observation records that exact one query's argv, outcome, elapsed time and original separate stdout/stderr. It never retries, changes the30-second timeout, calls a different simulator API or treats timeout as absence.

The hook applies only to the explicit coherent profile. Other profiles retain their original subprocess call. Every successful result and every raised exception is returned or re-raised unchanged; failure to write diagnostic evidence cannot swallow the original failure. Existing NEGATIVE_UNCLASSIFIED/fresh-construction checks stay unchanged. A diagnostic receipt claims no container absence, process absence or product execution.

Exactly one new controller method covers returned-negative, unexpected-positive, timeout partial bytes, OS error and cancellation. It is frozen before execution; no old successful method will be rerun. The original Release failure remains a failure.
