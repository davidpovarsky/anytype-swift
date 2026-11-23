import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import cleanup

UDID = "DC20C505-8314-42B2-B90F-766F8E8260E7"


class OwnedCleanupReconciliationTests(unittest.TestCase):
    def exercise(self, *, shutdown="timeout", deletion="pass", inventory=None,
                 query="pass", delays=(30, .4, .2)):
        state = {"time": 0.0, "calls": []}
        receipt = {"owned_simulator": {"udid": UDID}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "inventory.log"
            path.write_text(json.dumps({"devices": {"runtime": []}} if inventory is None else inventory))
            def run(argv, name, *, timeout):
                index = len(state["calls"])
                state["calls"].append((argv, timeout))
                state["time"] += delays[index]
                outcome = (shutdown, deletion, query)[index]
                if outcome == "timeout":
                    raise subprocess.TimeoutExpired(argv, timeout)
                if outcome == "wrong-timeout":
                    raise subprocess.TimeoutExpired(["ps", "-axo", "pid=,pgid=,stat="], 2)
                if outcome == "error":
                    raise RuntimeError("preserved original command failure")
                return path
            cleanup.cleanup_owned_simulator(run, receipt, UDID, clock=lambda: state["time"])
        return receipt, state

    def test_original_success_path_needs_no_extra_command(self):
        receipt, state = self.exercise(shutdown="pass", delays=(.1, .1, .1))
        self.assertEqual(receipt["owned_simulator_cleanup_status"], "COMPLETE")
        self.assertEqual(len(state["calls"]), 2)
        self.assertNotIn("owned_simulator_cleanup_reconciliation", receipt)

    def test_exact_absence_recovers_cleanup_but_preserves_shutdown_failure(self):
        receipt, state = self.exercise()
        self.assertEqual(receipt["owned_simulator_cleanup_status"], "COMPLETE")
        self.assertEqual(receipt["owned_simulator_cleanup"]["shutdown"]["status"], "FAIL")
        self.assertEqual(receipt["owned_simulator_cleanup_reconciliation"]["status"],
                         "VERIFIED_ABSENT_AFTER_DELETE")
        self.assertEqual(state["calls"][2][0], ["xcrun", "simctl", "list", "devices", UDID, "-j"])
        self.assertLessEqual(state["calls"][2][1], 60 - 30.4)

    def test_present_or_unrelated_inventory_never_proves_absence(self):
        for observed in (UDID, "AA20C505-8314-42B2-B90F-766F8E8260E7"):
            receipt, _ = self.exercise(inventory={"devices": {"runtime": [{"udid": observed}]}})
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")

    def test_missing_or_malformed_inventory_never_proves_absence(self):
        for observed in ({}, {"devices": []}, {"devices": {"runtime": {}}}, {"devices": {}, "extra": True}):
            receipt, _ = self.exercise(inventory=observed)
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")

    def test_failed_delete_or_inventory_preserves_incomplete_status(self):
        for args in ({"deletion": "error"}, {"query": "error"}, {"query": "timeout"}):
            receipt, state = self.exercise(**args)
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")
            if args.get("deletion") == "error":
                self.assertEqual(len(state["calls"]), 2)

    def test_other_shutdown_failures_are_not_reconciled(self):
        for failure in ("error", "wrong-timeout"):
            receipt, state = self.exercise(shutdown=failure)
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")
            self.assertEqual(len(state["calls"]), 2)

    def test_original_total_budget_never_resets_for_confirmation(self):
        receipt, state = self.exercise(delays=(30, 30, .2))
        self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")
        self.assertEqual(len(state["calls"]), 2)
        self.assertEqual(receipt["owned_simulator_cleanup_reconciliation"]["status"], "NOT_PROVEN")

    def test_late_successful_delete_or_absence_never_completes_original_budget(self):
        for args in ({"shutdown": "pass", "delays": (.1, 60, .1)},
                     {"delays": (30, .4, 30)}):
            receipt, _ = self.exercise(**args)
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")
            self.assertFalse(receipt["owned_simulator_cleanup_budget"]["within_budget"])
            self.assertEqual(receipt["owned_simulator_cleanup"]["delete"]["status"], "PASS_EXIT_0")

    def test_mismatched_owner_prevents_every_command(self):
        def unexpected(*args, **kwargs):
            self.fail("No command may run for a mismatched owner")
        with self.assertRaises(ValueError):
            cleanup.cleanup_owned_simulator(unexpected, {"owned_simulator": {"udid": "other"}}, UDID)


if __name__ == "__main__":
    unittest.main()
