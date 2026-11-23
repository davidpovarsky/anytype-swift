# Consolidated CI observer

Four independent gh watchers stopped after the shared GitHub core API quota returned HTTP403. Those are observer failures, not CI outcomes. Their original logs remain in their original diagnostic directories. The Page154 first window had separately reached its own timeout while CI remained queued.

After the recorded reset, a single bounded observer verified all four exact run IDs, source commits, branches and attempt numbers in one API response. It reads the current run list once per120 seconds, retains original API responses and atomic target snapshots, and backs off to the actual reset on another rate-limit response. Only terminal runs produce terminal receipts; it never dispatches, reruns, cancels or labels absent CI outcomes. Original terminal artifact/audit ownership is unchanged.

Sentinel job: job_741112953517. Actual working journal: /mnt/development/projects/diagnostics/anytype-consolidated-ci-observer-20261123. This source copy records the first observer window; subsequent immutable polls stay in that journal. The observation loop is bounded3300 seconds. An owned stop-observer file stops only this observer, never GitHub CI.
