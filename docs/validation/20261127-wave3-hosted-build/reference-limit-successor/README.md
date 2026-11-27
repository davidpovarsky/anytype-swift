# Registered dispatcher reference limit repair

The original GitHub dispatch at 2026-11-27 07:08:14 UTC stopped with HTTP 422 before any workflow run. The original response is retained byte for byte as dispatch-976.original.json (SHA256 f934f6da2f13734117347733e3842b3bfcc281494dff17ed367ae1be3f71c6b3). GitHub reported 51 referenced workflows against its limit of 50.

A recursive read of every actual job-level reusable reference found **50** distinct references in the original dispatcher at 654e7d835994c030f650b967c4ab10bb9ed0b639, and **52** at the failed candidate 976a83783fe93aa5de845f0613c5f137a47c9c68. The reported server count is not used as a complete graph inventory. No referenced original workflow calls another reusable workflow.

This successor places the two new job bodies directly into the already registered dispatcher. Each has its original runner, permissions, timeout, concurrency group, steps, exact control/source admission and artifact retention. Only the job name, route predicate, plan input names, and workflow-to-job permission/concurrency placement change. Both original reusable templates remain byte-identical and unreferenced. No original route, job or capability is removed.

The original dispatcher is restored byte for byte by removing the two added route choices, two input definitions and two inline job blocks. Each inline job reverses exactly to its original candidate976 template. The recursive reference set is now exactly the original 50 paths. The exact proof and patch are adjacent to this file.

All four Python controller/test file hashes remain unchanged. The original 15 portable controls are reused; no Python tests, Apple compiler, simulator test, native build, signing or workflow dispatch ran during this source correction. Successful GitHub dispatch and original native export remain separate runtime gates owned by the root integration agent.
