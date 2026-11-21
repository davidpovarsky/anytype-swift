# Fixed retained-Heart remaining acceptance preset

`retained-heart-release` coalesces compilation for the three still-needed existing Release lanes. It keeps one same-job App/native build and its UI runner build, then executes each lane on a separately created OS27 iPad with a fresh native account/Space and app data container.

| Lane | Original UI methods | Native preparation | Native postflight |
| --- | ---: | ---: | ---: |
| editor | 3 | 1 | 0 |
| quote-drop | 1 | 1 | 0 |
| properties-set | 2 | 1 | 1 |
| Total | 6 | 3 | 1 |

The original selectors remain in `run_wave15_acceptance.py`. The new preset accepts its fixed name only; it has no arbitrary lane or method list. `remaining-release` remains the original six-lane, 15-UI profile with its native postflight.

The existing same-job gates are retained: exact source/ref/SHA admission, actual OS27 preflight, the verified r14 runtime, unchanged source/locks/build products, full code-carrier checks, actual live mapping, independent fresh device/account/Space/container evidence, original method selection and xcresults, Properties pre-open store proof and exact postflight, worker deadlines and owned cleanup. Batch admission now delegates to the common source identity guard, so the separately reviewed shared branch admission applies consistently.

A successful new preset qualifies only these six UI methods, three native preparations and the original Properties postflight. It cannot claim the six-lane profile, full T2, the full acceptance matrix, another engine, Hebrew/iPhone coverage, or release acceptance.

Dispatch after root review uses the existing manual dispatcher route `wave15-acceptance`, `acceptance_lane=retained-heart-release`, `acceptance_device=ipad`, `acceptance_language=en`, and the already verified Heart source run. This commit does not dispatch a run.

## Controller validation

Eleven focused controller controls passed on Linux: exact canonical selectors and unchanged six-lane plan; complete saved qualification for both fixed profiles; wrong-profile/count/postflight rejection; exactly one batch build with three fresh devices; delegation to common source admission before build; preservation of observed failures and the Properties installation budget; fixed-profile diagnostic projection and privacy. These are synthetic controller controls, not native simulator acceptance.
